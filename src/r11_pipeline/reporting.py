"""Preserve the project workbook and export AI records to a copy."""
from collections import Counter
from datetime import date, datetime
from pathlib import Path
import re
from tempfile import TemporaryDirectory
from zipfile import ZipFile
from xml.etree import ElementTree as ET

from openpyxl import load_workbook
from openpyxl.utils import get_column_letter
from openpyxl.utils.datetime import to_excel

from .model import FIELDS, HEADERS, LABEL, SHEETS, WIDTHS, require
from .screening import conclusion, normalize

NAMESPACE = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
ET.register_namespace("", NAMESPACE)
ET.register_namespace("r", "http://schemas.openxmlformats.org/officeDocument/2006/relationships")


def read_book(path):
    workbook = load_workbook(path, read_only=True)
    try:
        require(workbook.sheetnames == SHEETS, f"工作表不匹配：{path}")
        sheets = [list(ws.iter_rows(values_only=True, max_col=width))
                  for ws, width in zip(workbook.worksheets, WIDTHS)]
        return sheets, [sheet[head - 1] for sheet, head in zip(sheets, HEADERS)]
    finally:
        workbook.close()


def index_sheet(sheet, header):
    entries = {}
    for index, row in enumerate(sheet[header:], header + 1):
        record_id = row[0]
        if record_id is None and not any(value is not None for value in row):
            continue
        require(type(record_id) is int and record_id not in entries, "有重复或无效的 Record_ID")
        entries[record_id] = (index, row)
    return entries


def cells_for(record):
    overall = conclusion(record)
    rq1, rq2, rq3 = record["rq"]
    ev = record["evidence"]
    lines = [f"{LABEL}｜{record['accessed_on']}｜{record['source_type']}",
             f"全文来源：{record['source']}", f"核查材料：{record['materials']}",
             f"通用资格 {record['general']}：{record['general_basis']}"]
    lines.extend(f"RQ{i}：{x}" for i, x in enumerate(record["rq_basis"], 1))
    lines.extend(f"图表 {v['locator']}（{v['status']}）：{v['detail']} {v.get('view', '')}".rstrip()
                 for v in record["visuals"])
    lines.extend(f"待核：{gap}" for gap in record["gaps"])
    if record.get("identity_note"):
        lines.append("题录核查：" + record["identity_note"])
    first = dict(zip(range(3, 8), [overall, rq1, rq2, rq3, LABEL]))
    second = dict(zip(range(2, 27), [
        ev.get("short", record["title"]), overall, rq1,
        *(ev[k] for k in FIELDS[:7]), rq2, *(ev[k] for k in FIELDS[7:12]),
        rq3, *(ev[k] for k in FIELDS[12:]), "\n".join(lines),
    ]))
    statuses = {"complete": "已获取全文", "partial": "全文或必要材料不完整", "unavailable": "未取得全文"}
    third = {4: record["source"], 5: statuses[record["access"]], 15: record["accessed_on"]}
    return first, second, third


def tag(name):
    return f"{{{NAMESPACE}}}{name}"


def replace_value(cell, value):
    for child in list(cell):
        cell.remove(child)
    if value is None:
        cell.attrib.pop("t", None)
        return
    if isinstance(value, (date, datetime)):
        value = to_excel(value)
    if isinstance(value, str):
        cell.set("t", "inlineStr")
        rich = ET.SubElement(cell, tag("is"))
        text = ET.SubElement(rich, tag("t"), {"{http://www.w3.org/XML/1998/namespace}space": "preserve"})
        text.text = value
    else:
        cell.set("t", "n")
        ET.SubElement(cell, tag("v")).text = str(value)


def finish_range(ref, end):
    return re.sub(r"(?<=\d):([A-Z]+)\d+$", rf":\g<1>{end}", ref)


def sheet_xml(content, index, rowmap, updates, counts):
    sheet = ET.fromstring(content)
    data = sheet.find(tag("sheetData"))
    header = HEADERS[index]
    for row in list(data):
        original = int(row.get("r"))
        if original <= header:
            continue
        if original not in rowmap:
            data.remove(row)
            continue
        row.set("r", str(rowmap[original]))
        for cell in row.findall(tag("c")):
            if original != rowmap[original]:
                require(cell.find(tag("f")) is None, "模板数据区有公式，须调整公式才能移动行")
            cell.set("r", re.sub(r"\d+$", str(rowmap[original]), cell.get("r")))
    data[:] = sorted(data, key=lambda row: int(row.get('r')))
    dest = {int(row.get('r')): row for row in data}
    for row_number, values in updates.items():
        row = dest[row_number]
        cells = {cell.get("r"): cell for cell in row.findall(tag("c"))}
        for column, value in values.items():
            address = f"{get_column_letter(column)}{row_number}"
            cell = cells.get(address)
            if cell is None:
                cell = ET.SubElement(row, tag("c"), {"r": address})
                cells[address] = cell
            replace_value(cell, value)
        row[:] = sorted(row, key=lambda c: (len(c.get("r")), c.get("r")))
    end = header + len(rowmap)
    for name, attribute in (("dimension", "ref"), ("autoFilter", "ref"), ("dataValidation", "sqref")):
        for node in sheet.iter(tag(name)):
            if node.get(attribute):
                node.set(attribute, " ".join(finish_range(ref, end) for ref in node.get(attribute).split()))
    if index == 0:
        cells = {cell.get("r"): cell for row in data for cell in row.findall(tag("c"))}
        c = f"C8:C{end}"
        for address, formula, value in (
            ("B4", f"COUNTA(A8:A{end})", counts["total"]),
            ("D4", f'COUNTA({c})-COUNTIF({c},"待筛选")', counts["entered"]),
            ("F4", f'COUNTIF({c},"待筛选")', counts["waiting"]),
            ("H4", f'COUNTIF({c},"整篇待核")', counts["pending"]),
        ):
            cell = cells[address]
            replace_value(cell, value)
            f = ET.Element(tag("f"))
            f.text = formula
            cell.insert(0, f)
        replace_value(cells["A2"], f"已登记 {counts['entered']}/{counts['total']} 篇。AI初步提取，待人工复核。")
    return ET.tostring(sheet, encoding="utf-8", xml_declaration=True)


def export_workbook(project, target, selected, edits):
    require(not target.exists(), f"输出已存在：{target}")
    rowmaps = [
        {index[record_id][0]: header + offset for offset, record_id in enumerate(selected, 1)}
        for index, header in zip(project.indexes, HEADERS)
    ]
    expected = []
    updates = []
    for index, head in enumerate(HEADERS):
        expected.append({})
        updates.append({})
        for offset, record_id in enumerate(selected, 1):
            row = list(project.indexes[index][record_id][1])
            patch = edits.get(record_id, ({}, {}, {}))[index]
            for column, value in patch.items():
                row[column - 1] = value
            expected[index][record_id] = tuple(row)
            if patch:
                updates[index][head + offset] = patch
    tally = Counter(row[2] for row in expected[0].values())
    counts = {"total": len(selected), "entered": len(selected) - tally["待筛选"],
              "waiting": tally["待筛选"], "pending": tally["整篇待核"]}
    target.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(dir=target.parent) as folder:
        staged = Path(folder) / target.name
        with ZipFile(project.master) as source, ZipFile(staged, "w") as output:
            for member in source.infolist():
                content = source.read(member)
                m = re.fullmatch(r"xl/(worksheets/sheet|tables/table)([123])\.xml", member.filename)
                if m:
                    part, number = m.groups()
                    index = int(number) - 1
                    if part == "worksheets/sheet":
                        content = sheet_xml(content, index, rowmaps[index], updates[index], counts)
                    else:
                        root = ET.fromstring(content)
                        end = HEADERS[index] + len(selected)
                        for node in (root, root.find(tag("autoFilter"))):
                            if node is not None:
                                node.set("ref", finish_range(node.get("ref"), end))
                        content = ET.tostring(root, encoding="utf-8", xml_declaration=True)
                output.writestr(member, content)
        sheets, headers = read_book(staged)
        require(headers == project.headers, "导出表头发生变化")
        for i, (rows, head) in enumerate(zip(sheets, HEADERS)):
            actual = {record_id: row for record_id, (_, row) in index_sheet(rows, head).items()}
            require(list(actual) == selected and actual == expected[i], f"导出第{i + 1}表的 ID 或数据不一致")
        require(not target.exists(), f"输出已存在：{target}")
        staged.rename(target)
    return counts


def export_batch(project, batch, snapshot):
    require(batch == project.next_batch(), "只能导出当前未交付批次")
    records = project.records(batch)
    ids = project.batches[batch]
    require(records and (snapshot or len(records) == len(ids)), "最终交付须覆盖本批全部 ID")
    suffix = f"进度_{len(records):02d}篇.xlsx" if snapshot else f"{len(ids)}篇.xlsx"
    output = project.artifact(batch, suffix)
    require(not output.exists(), f"输出已存在：{output}")
    tally = Counter(map(conclusion, records))
    next_id = (ids[len(records)] if len(records) < len(ids) else
               project.batches[batch + 1][0] if batch < 18 else None)
    stats = {"已登记": len(records), "全文材料完整": sum(r["access"] == "complete" for r in records),
             "全文或材料未齐": [r["id"] for r in records if r["access"] != "complete"],
             "初步纳入": tally["纳入"], "初步排除": sum(n for k, n in tally.items() if k.startswith("排除")),
             "整篇待核": tally["整篇待核"],
             **{f"RQ{i + 1}符合": sum(r["rq"][i] == "符合" for r in records) for i in range(3)},
             "下一篇": next_id}
    report = output.with_suffix(".md")
    notes = [f"# {output.stem}", "", LABEL, ""]
    notes.extend(f"- {key}：{value}" for key, value in stats.items())
    notes.extend(["", "## 待人工重点核查", ""])
    for record in records:
        for note in record["gaps"] + record.get("review", []) + [record.get("identity_note")]:
            if note:
                notes.append(f"- ID {record['id']}　{note}")
    report_body = "\n".join(notes) + "\n"
    report.parent.mkdir(parents=True, exist_ok=True)
    if report.exists():
        require(report.read_text(encoding="utf-8") == report_body, f"已有不同的进度记录：{report}")
    else:
        with report.open("x", encoding="utf-8") as file:
            file.write(report_body)
    counts = export_workbook(project, output, ids, {r["id"]: cells_for(r) for r in records})
    return {"工作簿": str(output), "进度及待核清单": str(report), **counts, **stats}


def merge(project, through, target):
    edits = {}
    for batch in range(1, through + 1):
        delivery = project.completed(batch)
        require(delivery is not None, f"第 {batch} 批的交付文件缺失")
        for record_id in project.batches[batch]:
            first, second, notes = (index[record_id][1] for index in delivery)
            edits[record_id] = (
                {**dict(enumerate(first[2:7], 3)), 3: normalize(first[2])},
                {**dict(enumerate(second[1:], 2)), 3: normalize(second[2])},
                {c: notes[c-1] for c in (4, 5, 15) if notes[c-1] not in (None, "")},
            )
    return {"总表": str(target), "已合并篇数": len(edits),
            **export_workbook(project, target, sorted(project.indexes[0]), edits)}
