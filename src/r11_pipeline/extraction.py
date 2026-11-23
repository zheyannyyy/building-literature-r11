"""Prepare a draft for Codex to populate from the full text."""
from .model import FIELDS, VERSION, require
from .project import plan


def paper_draft(project):
    current = plan(project)
    record_id = current.get("下一篇")
    require(record_id is not None, "没有待登记文献，请先检查或导出当前批次")
    title, doi = project.indexes[2][record_id][1][1:3]
    return {
        "id": record_id, "batch": current["下一批"], "title": title, "doi": doi,
        "version": VERSION, "access": None, "source": None, "source_type": None,
        "accessed_on": None, "materials": None, "general": None, "general_basis": None,
        "exclusion": None, "rq": [None] * 3, "rq_basis": [None] * 3,
        "gaps": [], "review": [], "evidence": dict.fromkeys(FIELDS), "visuals": [],
    }
