from __future__ import annotations
from pathlib import Path
from .validation import sanitize_filename, validate_dest_dir

def default_output_name(src: Path, target_ext: str, template: str = "{name}_converted") -> str:
    stem = template.format(name=src.stem)
    return sanitize_filename(f"{stem}.{target_ext}")

def resolve_output(dest_dir, filename: str, overwrite: bool = False) -> Path:
    """Never overwrite unless explicitly allowed; otherwise add ' (2)', ' (3)'..."""
    d = validate_dest_dir(dest_dir)
    filename = sanitize_filename(filename)
    p = d / filename
    if overwrite or not p.exists():
        return p
    stem, dot, ext = filename.rpartition(".")
    if not dot:
        stem, ext = filename, ""
    n = 2
    while True:
        cand = d / (f"{stem} ({n})" + (f".{ext}" if ext else ""))
        if not cand.exists():
            return cand
        n += 1
