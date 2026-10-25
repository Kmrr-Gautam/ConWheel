from __future__ import annotations
import os
import re
from pathlib import Path

class ValidationError(Exception):
    pass

_RESERVED = {"con", "prn", "aux", "nul", *(f"com{i}" for i in range(1, 10)),
             *(f"lpt{i}" for i in range(1, 10))}
MAX_NAME = 180

def validate_source(path) -> Path:
    p = Path(path)
    if not p.exists():
        raise ValidationError(f"File not found: {p.name}")
    if not p.is_file():
        raise ValidationError(f"Not a file: {p.name}")
    if not os.access(p, os.R_OK):
        raise ValidationError(f"Cannot read file: {p.name}")
    if p.stat().st_size == 0:
        raise ValidationError(f"File is empty: {p.name}")
    return p

def sanitize_filename(name: str) -> str:
    """Strip path components and characters Windows rejects; keep Unicode."""
    name = name.replace("\\", "/").split("/")[-1]
    name = re.sub(r'[<>:"|?*\x00-\x1f]', "_", name).strip(" .")
    if name.split(".")[0].lower() in _RESERVED:
        name = "_" + name
    if len(name) > MAX_NAME:
        base, _, ext = name.rpartition(".")
        keep = MAX_NAME - len(ext) - 1
        name = (base[:keep] + "." + ext) if base else name[:MAX_NAME]
    return name or "converted"

def validate_dest_dir(path) -> Path:
    p = Path(path)
    if p.exists() and not p.is_dir():
        raise ValidationError("Output location is not a folder")
    try:
        p.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        raise ValidationError(f"Cannot create output folder: {e}") from e
    if not os.access(p, os.W_OK):
        raise ValidationError("Output folder is not writable")
    return p

def is_within(child: Path, parent: Path) -> bool:
    try:
        child.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False
