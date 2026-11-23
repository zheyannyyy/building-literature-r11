"""Validate and save per-paper evidence."""
from datetime import date
import json
import re
from tempfile import TemporaryDirectory

from .model import FIELDS, STATUS, VERSION, require
from .reporting import cells_for


def has_text(value):
    return isinstance(value, str) and bool(value.strip())


def scalar(value):
    return (has_text(value) and not re.search(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", value)
            and len(value.encode("utf-16-le")) // 2 <= 32767) or (
                type(value) in (int, float) and 0 <= value < float("inf"))


def validate(project, batch, record):
    record_id = record["id"]
    require(type(record_id) is int and record_id in project.batches[batch], f"ID 不属于第 {batch} 批")
    require(record["batch"] == batch and record["version"] == VERSION, "批次或版本不一致")
    require((record["title"], record["doi"]) == project.indexes[2][record_id][1][1:3], "题名或 DOI 不一致")
    require(record["general"] in STATUS and record["access"] in {"complete", "partial", "unavailable"},
            "通用资格或访问状态无效")
    for key in ("source", "source_type", "materials", "general_basis"):
        require(has_text(record[key]), f"缺少 {key}")
    date.fromisoformat(record["accessed_on"])
    require(len(record["rq"]) == 3 and set(record["rq"]) <= STATUS, "三个 RQ 须分别判断")
    require(len(record["rq_basis"]) == 3 and all(map(has_text, record["rq_basis"])), "须记录三个 RQ 的理由")
    has_gap = (record["access"] != "complete" or record["general"] == "待核" or "待核" in record["rq"])
    require(isinstance(record["gaps"], list) and all(map(has_text, record["gaps"]))
            and (not has_gap or record["gaps"]), "请注明证据缺口")
    require((record["exclusion"] in {f"EX0{i}" for i in range(1, 8)}) if record["general"] == "不符合"
            else record["exclusion"] is None, "通用排除代码须对应 EX01–EX07")
    # Under the project SOP, unavailable full text cannot support an affirmative RQ.
    if record["access"] == "unavailable":
        require(record["general"] == "待核" and record["rq"] == ["待核"] * 3,
                "未取得目标全文时，保留通用资格及三个 RQ 为待核")
    evidence = record["evidence"]
    for key in FIELDS:
        require(scalar(evidence[key]), f"证据字段 {key} 无效，请使用显式值、NA、NR 或待核")
    for passed, keys in zip(record["rq"], (
        ("params", "method", "n"), ("identification", "climate", "quantitative", "coverage"),
        ("a", "b", "optimizer", "energy", "comfort"),
    )):
        if passed == "符合":
            require(all(evidence[k] not in {"NA", "NR", "待核"} for k in keys),
                    "RQ 符合时必须保存对应证据")
    if record["rq"][1] == "符合":
        require(evidence["comparator"] not in {"NR", "待核"},
                "RQ2 符合时须记录相关对照，对照确不适用时填 NA 并在依据中说明")
    require(isinstance(record["visuals"], list), "visuals 必须为数组")
    for visual in record["visuals"]:
        require(visual["status"] in {"checked", "pending"} and has_text(visual["locator"])
                and has_text(visual["detail"]) and visual["fields"] and isinstance(visual["fields"], list)
                and set(visual["fields"]) <= set(FIELDS + ["RQ1", "RQ2", "RQ3"]), "图表核对记录不完整")
        if visual["status"] == "checked":
            require(has_text(visual.get("view")), "已核对的图表须关联可定位原页")
        else:
            require(record["gaps"], "待核图表须记录证据缺口")
            for field in visual["fields"]:
                value = record["rq"][int(field[-1]) - 1] if field.startswith("RQ") else evidence[field]
                require(value == "待核", f"依赖待核图表的 {field} 须标记待核")
    for values in cells_for(record):
        require(all(scalar(value) for value in values.values()), f"第 {record_id} 篇存在无效或过长的 Excel 字段")


def save(project, draft):
    batch = project.next_batch()
    require(batch is not None, "全部批次已交付")
    record = json.loads(draft.read_text(encoding="utf-8-sig"))
    validate(project, batch, record)
    records = project.records(batch)
    ids = project.batches[batch]
    require(len(records) < len(ids) and record["id"] == ids[len(records)], "请保存计划中的下一篇")
    target = project.state / f"batch-{batch:02d}" / f"{record['id']:04d}.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(dir=target.parent) as folder:
        staged = Path(folder) / target.name
        staged.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        require(not target.exists(), f"已有逐篇证据：{target}")
        staged.rename(target)
    return {"已保存": str(target), "已登记": len(records) + 1,
            "下一篇": ids[len(records) + 1] if len(records) + 1 < len(ids) else None}
