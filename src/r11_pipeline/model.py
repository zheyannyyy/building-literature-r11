VERSION = "V2.1-r11"
LABEL = "AI初步提取（待人工复核）"
SHEETS = ["01_筛选结果", "02_参数证据", "03_说明"]
HEADERS = (7, 5, 20)
WIDTHS = (8, 26, 24)
FIELDS = (
    "params method key n_all n k r identification climate quantitative "
    "comparator coverage a b optimizer energy comfort o o_all"
).split()
STATUS = {"符合", "不符合", "待核"}


def require(condition, message):
    if not condition:
        raise ValueError(message)
