"""Read workbook identities, batch assignments and recorded progress."""
from collections import Counter
import json

from .evidence import validate
from .model import HEADERS, LABEL, STATUS, VERSION, require
from .reporting import index_sheet, read_book
from .screening import normalize


class Project:
    def __init__(self, master, state, deliveries):
        self.master, self.state, self.deliveries = master, state, deliveries
        sheets, self.headers = read_book(master)
        self.indexes = [index_sheet(sheet, header) for sheet, header in zip(sheets, HEADERS)]
        require(self.headers[2][15:19] == ("清单序号", "人工分组", "交付批次", "批内序号"),
                "03_说明 缺少规定的批次映射")
        ids = list(self.indexes[2])
        require(len(ids) == len(set(ids)) == 897 and all(set(index) == set(ids) for index in self.indexes),
                "三表须各含同一组 897 篇")
        self.batches = {}
        for record_id, (_, row) in self.indexes[2].items():
            batch = row[17]
            require(type(batch) is int and 1 <= batch <= 18, f"第 {record_id} 条的交付批次无效")
            require(row[16] == (batch - 1) // 6 + 1, f"第 {record_id} 条的人工分组无效")
            require((self.indexes[0][record_id][1][1], self.indexes[0][record_id][1][7]) == (row[1], row[2]), f"题录不一致：{record_id}")
            self.batches.setdefault(batch, []).append(record_id)
        require(set(self.batches) == set(range(1, 19)), "交付批次须覆盖 1–18")
        roster = []
        for batch in sorted(self.batches):
            ids = self.batches[batch]
            ids.sort(key=lambda record_id: self.indexes[2][record_id][1][18])
            orders = [self.indexes[2][record_id][1][18] for record_id in ids]
            size = 49 if batch % 6 == 0 else 50
            require(ids == sorted(ids) and orders == list(range(1, size + 1)), f"第 {batch} 批映射不一致")
            roster.extend(ids)
        require(roster == sorted(roster), "批次内外的 Record_ID 必须按升序排列")
        require([self.indexes[2][record_id][1][15] for record_id in roster] == list(range(1, 898)),
                "清单序号与批次映射不一致")

    def artifact(self, batch, suffix):
        return self.deliveries / f"{VERSION}_AI初步提取_第{batch:02d}批_{suffix}"

    def completed(self, batch):
        path = self.artifact(batch, f"{len(self.batches[batch])}篇.xlsx")
        if not path.exists():
            return None
        sheets, headers = read_book(path)
        require(headers == self.headers, f"已交付表头有差异：{path}")
        indices = [index_sheet(rows, h) for rows, h in zip(sheets, HEADERS)]
        require(all(list(i) == self.batches[batch] for i in indices), f"已交付 ID 有差异：{path}")
        for record_id in self.batches[batch]:
            first, second, notes = (index[record_id][1] for index in indices)
            orig = self.indexes[2][record_id][1]
            require((first[1], first[7]) == notes[1:3] == orig[1:3] and notes[15:22] == orig[15:22],
                    f"已交付题录或分工有差异：{record_id}")
            overall = normalize(first[2])
            require(overall in {"纳入", "整篇待核", *(f"排除 EX0{x}" for x in range(1, 9))}
                    and overall == normalize(second[2])
                    and first[3:6] == (second[3], second[11], second[17])
                    and set(first[3:6]) <= STATUS and first[6] == LABEL and second[25],
                    f"已交付 AI 字段不完整或不一致：{record_id}")
        return indices

    def next_batch(self):
        return next((b for b in sorted(self.batches) if self.completed(b) is None), None)

    def records(self, batch):
        folder = self.state / f"batch-{batch:02d}"
        records = []
        if folder.is_dir():
            files = sorted(folder.glob("*.json"))
            for path in files:
                record = json.loads(path.read_text(encoding="utf-8-sig"))
                validate(self, batch, record)
                require(path.stem == f"{record['id']:04d}", f"文件名和 Record_ID 不一致：{path}")
                records.append(record)
        ids = [r["id"] for r in records]
        require(ids == self.batches[batch][:len(ids)], f"第{batch}批证据编号不连续，请先核对进度")
        return records


def plan(project):
    batch = project.next_batch()
    if batch is None:
        return {"已交付": list(range(1, 19)), "下一批": None}
    completed = project.records(batch)
    ids = project.batches[batch]
    groups = (len(ids) + 14) // 15
    step, extra = divmod(len(ids), groups)
    spans = []
    start = 0
    for index in range(groups):
        stop = start + step + (index < extra)
        remaining = ids[max(start, len(completed)):stop]
        if remaining:
            spans.append([
                {"id": x, "title": row[1], "doi": row[2], "source_hint": row[3],
                 "batch": batch, "batch_order": row[18]}
                for x in remaining for _, row in [project.indexes[2][x]]
            ])
        start = stop
    return {"已交付": list(range(1, batch)), "下一批": batch, "总数": len(ids),
            "已登记": [r["id"] for r in completed], "最后登记": completed[-1]["id"] if completed else None,
            "待核": [r["id"] for r in completed if r["gaps"]],
            "全文或材料未齐": [r["id"] for r in completed if r["access"] != "complete"],
            "下一篇": ids[len(completed)] if len(completed) < len(ids) else None,
            "小批次": spans}


def batch_validation(project, batch):
    ids = project.batches[batch]
    delivery = project.completed(batch)
    if delivery is not None:
        rows = [delivery[0][record_id][1] for record_id in ids]
        return {"批次": batch, "状态": "已交付，表头、ID、题录和 AI 字段已校验",
                "篇数": len(ids), "纳排统计": dict(Counter(normalize(row[2]) for row in rows)),
                "整篇待核 ID": [row[0] for row in rows if normalize(row[2]) == "整篇待核"],
                "有待核 RQ 的 ID": [row[0] for row in rows if "待核" in row[3:6]]}
    records = project.records(batch)
    return {"批次": batch, "状态": "逐篇证据已登记齐全" if len(records) == len(ids) else "登记未完成",
            "篇数": len(ids), "已登记": len(records), "未登记 ID": ids[len(records):],
            "有证据缺口的 ID": [record["id"] for record in records if record["gaps"]]}


def manifest(project):
    return [
        {"record_id": record_id, "list_order": row[15], "group": row[16],
         "batch": row[17], "batch_order": row[18]}
        for record_id, (_, row) in sorted(project.indexes[2].items())
    ]
