from __future__ import annotations
import shutil
import tempfile
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional
from ..converters.base import Cancelled, ConversionError, Options
from . import format_registry
from .output_manager import default_output_name, resolve_output
from .validation import ValidationError, validate_dest_dir, validate_source

@dataclass
class Result:
    ok: bool
    src: Path
    target: str
    output: Optional[Path] = None
    message: str = ""
    cancelled: bool = False

def convert(src, target: str, dest_dir=None, options: Options | None = None,
            filename: str | None = None, overwrite: bool = False,
            cancel: threading.Event | None = None,
            progress: Callable[[float], None] | None = None,
            name_template: str = "{name}_converted") -> Result:
    """Convert one file. Never raises for expected failures; returns Result."""
    cancel = cancel or threading.Event()
    progress = progress or (lambda f: None)
    options = options or Options()
    try:
        src = validate_source(src)
    except ValidationError as e:
        return Result(False, Path(str(src)), target, message=str(e))
    det, convs = format_registry.options_for(src)
    if det is None:
        return Result(False, src, target, message="Unsupported or unrecognised file type.")
    conv = next((c for c in convs if c.target == target), None)
    if conv is None:
        return Result(False, src, target,
                      message=f"Converting {det.fmt.upper()} to {target.upper()} is not supported "
                              f"(or a required engine is missing).")
    try:
        dest = validate_dest_dir(dest_dir or src.parent)
        ext = "" if conv.target == "raw" else conv.target
        name = filename or (default_output_name(src, ext, name_template) if ext else src.stem)
        final = resolve_output(dest, name, overwrite)
    except ValidationError as e:
        return Result(False, src, target, message=str(e))
    work = Path(tempfile.mkdtemp(prefix="conwheel_"))
    tmp_out = work / ("out." + ext if ext else "out.bin")
    try:
        conv.func(src, tmp_out, options, cancel, progress)
        if cancel.is_set():
            raise Cancelled()
        if not tmp_out.exists() or tmp_out.stat().st_size == 0:
            raise ConversionError("The converter produced no output.")
        if final.exists() and not overwrite:                # race guard
            final = resolve_output(dest, final.name, False)
        shutil.move(str(tmp_out), str(final))
        progress(1.0)
        return Result(True, src, target, final, "Done")
    except Cancelled:
        return Result(False, src, target, message="Cancelled", cancelled=True)
    except ConversionError as e:
        return Result(False, src, target, message=str(e))
    except Exception as e:                                   # keep app alive
        return Result(False, src, target, message=f"Unexpected error: {type(e).__name__}: {e}")
    finally:
        shutil.rmtree(work, ignore_errors=True)
