from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from openpyxl import Workbook

from r11_pipeline.evidence import save, validate
from r11_pipeline.extraction import paper_draft
from r11_pipeline.model import FIELDS, SHEETS, WIDTHS
from r11_pipeline.project import Project, batch_validation, manifest, plan
from r11_pipeline.reporting import export_batch, merge
from r11_pipeline.retrieval import fetch_pdf
from r11_pipeline.screening import conclusion


def write_template(path):
    book = Workbook()
    book.remove(book.active)
    for name in SHEETS:
        book.create_sheet(name)
    first, second, notes = book.worksheets
    for address in ("A2", "B4", "D4", "F4", "H4"):
        first[address] = 0
    notes_headers = [f"column{n}" for n in range(WIDTHS[2])]
    notes_headers[15:19] = ["清单序号", "人工分组", "交付批次", "批内序号"]
    for sheet, header, width in zip(book.worksheets, (7, 5, 20), WIDTHS):
        for col, value in enumerate(notes_headers if sheet == notes else range(width), 1):
            sheet.cell(header, col, value)
    order = 0
    for batch in range(1, 19):
        for batch_order in range(1, 50 if batch % 6 == 0 else 51):
            order += 1
            record_id = order * 2
            title = f"Synthetic title {order}"
            first.append([record_id, title, "待筛选"] + [None] * 5)
            second.append([record_id, title, "待筛选"] + [None] * 23)
            notes.append([record_id, title, None] + [None] * 6 +
                         ["manual decision"] + [None] * 5 +
                         [order, (batch - 1) // 6 + 1, batch, batch_order] + [None] * 5)
    book.save(path)
    book.close()


class PipelineTest(unittest.TestCase):
    def test_resume_and_workbook_roundtrip(self):
        with TemporaryDirectory() as folder:
            path = Path(folder)
            master = path / "master.xlsx"
            write_template(master)
            original = master.read_bytes()
            project = Project(master, path / "progress", path / "outputs")
            self.assertEqual(len(manifest(project)), 897)
            self.assertEqual(plan(project)["下一篇"], 2)
            draft = path / "draft.json"
            for record_id in project.batches[1]:
                record = paper_draft(project)
                self.assertEqual(record["id"], record_id)
                record.update(access="unavailable", source="Synthetic source", source_type="test",
                              accessed_on="2020-01-01", materials="No full text", general="待核",
                              general_basis="Full text unavailable", rq=["待核"] * 3,
                              rq_basis=["Full text unavailable"] * 3, gaps=["Need full text"],
                              evidence=dict.fromkeys(FIELDS, "待核"))
                if record_id == 2:
                    record["visuals"] = [{"status": "pending", "locator": "Fig. 1",
                                          "detail": "Missing page", "fields": ["quantitative"]}]
                    record["evidence"]["quantitative"] = 1
                    with self.assertRaisesRegex(ValueError, "quantitative"):
                        validate(project, 1, record)
                    record["evidence"]["quantitative"] = "待核"
                draft.write_text(json.dumps(record), encoding="utf-8")
                save(project, draft)
                if record_id == 2:
                    self.assertEqual(plan(project)["下一篇"], 4)
                    self.assertEqual(export_batch(project, 1, snapshot=True)["waiting"], 49)
            self.assertEqual(batch_validation(project, 1)["已登记"], 50)
            export_batch(project, 1, snapshot=False)
            self.assertEqual(plan(project)["下一批"], 2)
            merged = path / "merged.xlsx"
            self.assertEqual(merge(project, 1, merged)["entered"], 50)
            copied = Project(merged, project.state, project.deliveries)
            self.assertEqual(copied.indexes[2][2][1][9], "manual decision")
            self.assertEqual(master.read_bytes(), original)

    def test_one_pass_is_enough_when_general_eligibility_passes(self):
        self.assertEqual(conclusion({"general": "符合", "rq": ["不符合", "符合", "待核"]}), "纳入")
        self.assertEqual(conclusion({"general": "符合", "rq": ["不符合"] * 3}), "排除 EX08")


class DownloadTest(unittest.TestCase):
    def test_pdf_download_and_invalid_content(self):
        url = "https://example.org/paper.pdf"
        valid = b"%PDF-1.7\nsimulated content\n%%EOF\n"
        with TemporaryDirectory() as folder, patch("r11_pipeline.retrieval.build_opener") as opener:
            target = Path(folder) / "paper.pdf"
            response = BytesIO(b"<html>Sign in</html>")
            response.geturl = lambda: url
            opener.return_value.open.return_value = response
            with self.assertRaisesRegex(ValueError, "PDF"):
                fetch_pdf(url, target)
            self.assertFalse(target.exists())
            response = BytesIO(valid)
            response.geturl = lambda: url
            opener.return_value.open.return_value = response
            result = fetch_pdf(url, target)
            self.assertEqual(result["sha256"], sha256(valid).hexdigest())
            self.assertEqual(target.read_bytes(), valid)
            with self.assertRaises(FileExistsError):
                fetch_pdf(url, target)
