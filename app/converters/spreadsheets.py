from __future__ import annotations
from .documents import build

_NOTE = {"csv": "CSV keeps only the first worksheet's values; formulas, formatting, charts and extra sheets are lost.",
         "pdf": "Output is a fixed-layout print of the sheets; formulas are not kept."}

def conversions_for(src_fmt: str):
    if src_fmt in ("xlsx", "xls", "ods"):
        return build(src_fmt, ["xlsx", "ods", "csv", "pdf"], _NOTE, ("xlsx", "pdf"))
    if src_fmt in ("csv", "tsv"):
        return build(src_fmt, ["xlsx", "ods", "pdf"], {"pdf": _NOTE["pdf"]}, ("xlsx",))
    return []
