from __future__ import annotations
from .documents import build

def conversions_for(src_fmt: str):
    if src_fmt in ("pptx", "ppt", "odp"):
        return build(src_fmt, ["pdf", "pptx", "odp"],
                     {"pdf": "Animations and transitions are not kept; slide order and size are."}, ("pdf",))
    return []
