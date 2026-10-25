from __future__ import annotations
import csv
import html
import io
import json
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from pathlib import Path
from .base import Conversion, ConversionError

def _read(src: Path, o) -> str:
    raw = src.read_bytes()
    for enc in (o.encoding, "utf-8-sig", "cp1252"):
        try:
            return raw.decode(enc)
        except (UnicodeDecodeError, LookupError):
            continue
    raise ConversionError("Could not decode the text file.")

def _write(out: Path, text: str):
    out.write_text(text, encoding="utf-8", newline="")

def _rows(text: str, delim: str):
    return list(csv.reader(io.StringIO(text, newline=""), delimiter=delim))

def _delim_convert(sd, td):
    def run(src, out, o, cancel, progress):
        rows = _rows(_read(src, o), sd)
        buf = io.StringIO()
        csv.writer(buf, delimiter=td, lineterminator="\n").writerows(rows)
        _write(out, buf.getvalue())
    return run

def _table_to_json(sd):
    def run(src, out, o, cancel, progress):
        rows = _rows(_read(src, o), sd)
        if not rows:
            raise ConversionError("The file has no rows.")
        head, body = rows[0], rows[1:]
        if len(set(head)) != len(head):
            raise ConversionError("Duplicate column names; cannot build JSON objects.")
        data = [dict(zip(head, r + [""] * (len(head) - len(r)))) for r in body]
        _write(out, json.dumps(data, ensure_ascii=False, indent=2))
    return run

def _json_to_table(td):
    def run(src, out, o, cancel, progress):
        try:
            data = json.loads(_read(src, o))
        except json.JSONDecodeError as e:
            raise ConversionError(f"Invalid JSON: {e}") from e
        if not (isinstance(data, list) and data and all(isinstance(r, dict) for r in data)):
            raise ConversionError("JSON must be a non-empty list of objects to become a table.")
        cols = []
        for r in data:
            for k in r:
                if k not in cols:
                    cols.append(k)
        buf = io.StringIO()
        w = csv.writer(buf, delimiter=td, lineterminator="\n")
        w.writerow(cols)
        for r in data:
            w.writerow(["" if r.get(c) is None else
                        (json.dumps(r[c], ensure_ascii=False) if isinstance(r.get(c), (dict, list)) else r.get(c))
                        for c in cols])
        _write(out, buf.getvalue())
    return run

def _to_el(parent, key, val):
    tag = "".join(c if (c.isalnum() or c in "_-") else "_" for c in str(key)) or "item"
    if tag[0].isdigit():
        tag = "_" + tag
    el = ET.SubElement(parent, tag)
    if isinstance(val, dict):
        for k, v in val.items():
            _to_el(el, k, v)
    elif isinstance(val, list):
        for v in val:
            _to_el(el, "item", v)
    elif val is not None:
        el.text = str(val) if not isinstance(val, bool) else str(val).lower()

def _json_to_xml(src, out, o, cancel, progress):
    try:
        data = json.loads(_read(src, o))
    except json.JSONDecodeError as e:
        raise ConversionError(f"Invalid JSON: {e}") from e
    root = ET.Element("root")
    if isinstance(data, dict):
        for k, v in data.items():
            _to_el(root, k, v)
    else:
        _to_el(root, "item", data) if not isinstance(data, list) else [_to_el(root, "item", v) for v in data]
    ET.indent(root)
    out.write_bytes(ET.tostring(root, encoding="utf-8", xml_declaration=True))

def _el_to_py(el):
    kids = list(el)
    if not kids:
        return el.text.strip() if el.text and el.text.strip() else ""
    if all(k.tag == "item" for k in kids):
        return [_el_to_py(k) for k in kids]
    d = {}
    for k in kids:
        v = _el_to_py(k)
        if k.tag in d:
            if not isinstance(d[k.tag], list) or not getattr(d, "_multi", None):
                d[k.tag] = [d[k.tag]] if not isinstance(d[k.tag], list) else d[k.tag]
            d[k.tag].append(v)
        else:
            d[k.tag] = v
    return d

def _xml_to_json(src, out, o, cancel, progress):
    try:
        root = ET.fromstring(src.read_bytes())   # stdlib parser; no external entities fetched
    except ET.ParseError as e:
        raise ConversionError(f"Invalid XML: {e}") from e
    _write(out, json.dumps({root.tag: _el_to_py(root)}, ensure_ascii=False, indent=2))

class _Strip(HTMLParser):
    def __init__(self):
        super().__init__(); self.parts = []; self.skip = 0
    def handle_starttag(self, t, a):
        if t in ("script", "style"): self.skip += 1
        if t in ("br", "p", "div", "li", "tr", "h1", "h2", "h3", "h4", "h5", "h6"): self.parts.append("\n")
    def handle_endtag(self, t):
        if t in ("script", "style") and self.skip: self.skip -= 1
        if t in ("p", "div", "li", "tr"): self.parts.append("\n")
    def handle_data(self, d):
        if not self.skip: self.parts.append(d)

def _html_to_txt(src, out, o, cancel, progress):
    p = _Strip(); p.feed(_read(src, o))
    import re
    text = re.sub(r"\n{3,}", "\n\n", "".join(p.parts)).strip() + "\n"
    _write(out, text)

def _txt_to_html(src, out, o, cancel, progress):
    text = _read(src, o)
    paras = "\n".join(f"<p>{html.escape(p).replace(chr(10), '<br>')}</p>"
                      for p in text.replace("\r\n", "\n").split("\n\n") if p.strip())
    _write(out, f'<!DOCTYPE html>\n<html><head><meta charset="utf-8"><title>{html.escape(src.stem)}</title></head>\n<body>\n{paras}\n</body></html>\n')

def _md_to_html(src, out, o, cancel, progress):
    import markdown
    body = markdown.markdown(_read(src, o), extensions=["tables", "fenced_code"])
    _write(out, f'<!DOCTYPE html>\n<html><head><meta charset="utf-8"><title>{html.escape(src.stem)}</title></head>\n<body>\n{body}\n</body></html>\n')

def _validate_json(src, o):
    try:
        json.loads(_read(src, o))
    except json.JSONDecodeError as e:
        raise ConversionError(f"Invalid JSON: {e}") from e

def conversions_for(fmt: str) -> list[Conversion]:
    C = Conversion
    L = []
    if fmt == "csv":
        L += [C("csv", "tsv", "builtin", _delim_convert(",", "\t"), keeps_metadata=False, recommended=True),
              C("csv", "json", "builtin", _table_to_json(","), notes="First row is used as field names.")]
    elif fmt == "tsv":
        L += [C("tsv", "csv", "builtin", _delim_convert("\t", ","), recommended=True),
              C("tsv", "json", "builtin", _table_to_json("\t"), notes="First row is used as field names.")]
    elif fmt == "json":
        L += [C("json", "csv", "builtin", _json_to_table(","), notes="Requires a list of objects; nested values are stored as JSON text."),
              C("json", "tsv", "builtin", _json_to_table("\t"), notes="Requires a list of objects."),
              C("json", "xml", "builtin", _json_to_xml)]
    elif fmt == "xml":
        L += [C("xml", "json", "builtin", _xml_to_json, notes="XML attributes are not preserved.")]
    elif fmt == "html":
        L += [C("html", "txt", "builtin", _html_to_txt, notes="Formatting is removed; only text is kept.")]
    elif fmt == "txt":
        L += [C("txt", "html", "builtin", _txt_to_html)]
    elif fmt == "md":
        L += [C("md", "txt", "builtin", lambda s, o, op, c, p: _write(o, _read(s, op)),
                notes="Markdown syntax is kept as plain text."),]
        try:
            import markdown  # noqa
            L.append(C("md", "html", "builtin", _md_to_html, recommended=True))
        except ImportError:
            pass
    return L
