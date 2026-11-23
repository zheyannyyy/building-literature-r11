"""Aggregate recorded RQ decisions using r11 section 6."""

import re


def normalize(value):
    return re.sub(r"^排除\s*(EX0[1-8])$", r"排除 \1", value or "")


def conclusion(record):
    if record["general"] == "不符合":
        return "排除 " + record["exclusion"]
    if record["general"] == "待核":
        return "整篇待核"
    if "符合" in record["rq"]:
        return "纳入"
    return "整篇待核" if "待核" in record["rq"] else "排除 EX08"
