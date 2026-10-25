from __future__ import annotations
from .base import Conversion, ConversionError

def _have_fitz() -> bool:
    try:
        import fitz  # noqa
        return True
    except ImportError:
        return False

def _pdf_to_txt(src, out, o, cancel, progress):
    import fitz
    try:
        doc = fitz.open(src)
    except Exception as e:
        raise ConversionError(f"Could not open PDF: {e}") from e
    parts = []
    for i, page in enumerate(doc):
        parts.append(page.get_text())
        progress((i + 1) / max(1, len(doc)))
    text = "\n\f\n".join(parts).strip()
    if not text:
        raise ConversionError("This PDF has no extractable text (it may be scanned). OCR is not configured.")
    out.write_text(text + "\n", encoding="utf-8")

def conversions_for(fmt: str):
    if fmt != "pdf" or not _have_fitz():
        return []
    return [Conversion("pdf", "txt", "pymupdf", _pdf_to_txt, notes="Text only; layout, images and tables are not kept. "
                       "PDF to DOCX is not offered because layout cannot be reproduced reliably.")]
