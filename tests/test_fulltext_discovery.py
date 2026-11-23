"""Offline coverage for full-text metadata discovery; no real network access."""
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from types import SimpleNamespace

from r11_pipeline.fulltext_discovery import (
    clean_doi, discover_one, pdf_index, safe_source, select_ids,
    title_matches, write_reports,
)


class TestFulltextDiscovery(unittest.TestCase):
    def setUp(self):
        self.project = SimpleNamespace(indexes=[None, None, {
            12: (0, [12, "A methodology to design a knowledge-based tool for residential buildings simulation",
                     "10.1115/IMECE201550999"] + [None] * 14 + [1]),
            256: (0, [256, "Synthetic energy study", "10.1234/xyz"] + [None] * 14 + [4]),
            257: (0, [257, "Missing DOI study", None] + [None] * 14 + [4]),
        }], batches={1: [12], 4: [256, 257]})

    def test_doi_and_title(self):
        self.assertEqual(clean_doi("https://doi.org/10.1115/IMECE201550999"), "10.1115/IMECE201550999")
        self.assertTrue(title_matches("Energy: a review", "Energy — A Review"))
        self.assertFalse(title_matches("Study A", "Unrelated building comfort research"))
        self.assertIsNone(safe_source({"landing_url": "http://not-secure.test/paper",
                                       "pdf_url": "javascript:alert(1)"}))

    def test_oa_results_and_identity_warning(self):
        urls = []

        def fake_client(url):
            urls.append(url)
            return {"doi": "https://doi.org/10.1115/IMECE2015-50999",
                    "display_name": "A methodology to design a knowledge-based tool for residential buildings simulation",
                    "best_oa_location": {"is_oa": True,
                                         "pdf_url": "https://repository.example/p.pdf",
                                         "landing_page_url": "https://repository.example/p"},
                    "locations": [{"is_oa": True, "pdf_url": "https://repository.example/p.pdf",
                                   "landing_page_url": "https://repository.example/p"}]}

        record = discover_one(self.project, 12, {}, client=fake_client)
        self.assertEqual(record["status"], "oa_candidate_pending_verification")
        self.assertEqual(len(record["oa_candidates"]), 1)
        self.assertTrue(record["identity_warnings"])
        self.assertEqual(len(urls), 1)

    def test_local_pdf_prevents_network_search(self):
        with TemporaryDirectory() as directory:
            folder = Path(directory)
            (folder / "0012.pdf").write_bytes(b"%PDF-1.4\n...\n%%EOF\n")

            def no_network(url):
                raise AssertionError("Network was accessed")

            record = discover_one(self.project, 12, pdf_index(folder), client=no_network)
            self.assertEqual(record["status"], "local_pdf_pending_identity_check")
            self.assertFalse(record["local_pdf_candidates"][0]["identity_verified"])

    def test_failure_does_not_mark_screened(self):
        def fail(url):
            raise RuntimeError("HTTP 403")

        record = discover_one(self.project, 256, {}, client=fail)
        self.assertEqual(record["status"], "manual_access_needed")
        self.assertEqual(len(record["errors"]), 1)
        missing = discover_one(self.project, 257, {}, client=fail)
        self.assertIn("无DOI", missing["errors"][0])

    def test_selection_and_no_overwrite(self):
        with TemporaryDirectory() as directory:
            path = Path(directory)
            queue = path / "queue.json"
            queue.write_text(json.dumps({"pending_ids": [257, 256, 257]}), encoding="utf-8")
            args = SimpleNamespace(batch=None, ids=None, ids_file=queue)
            self.assertEqual(select_ids(self.project, args), [257, 256])
            target = path / "report.json"
            report = discover_one(self.project, 257, {})
            csv_path = write_reports(target, [report])
            self.assertTrue(csv_path.exists())
            self.assertIn("record_id", csv_path.read_text(encoding="utf-8-sig"))
            with self.assertRaises(FileExistsError):
                write_reports(target, [report])


if __name__ == "__main__":
    unittest.main()
