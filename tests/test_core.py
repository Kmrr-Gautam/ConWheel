import json, threading, unittest, zipfile, tarfile, io, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from tests.helpers import *
from app.core import file_detection as fd, format_registry as reg
from app.core.output_manager import resolve_output, default_output_name
from app.core.validation import sanitize_filename, validate_source, ValidationError
from app.core.conversion_manager import convert
from app.core.job_queue import JobQueue
from app.config import Settings, History
from app.converters.base import Options
from app.converters import documents, audio
from app.ui import wheel_geometry as wg
from app.integrations.shortcut_logic import ShortcutMatcher

HAS_FF = audio.ffmpeg() is not None
HAS_LO = documents.soffice() is not None

class Detection(unittest.TestCase):
    def test_png_and_mismatch(self):
        d = tmpdir(); p = make_png(d / "pic.jpg")           # PNG bytes, .jpg name
        det = fd.detect(p)
        self.assertEqual(det.fmt, "png"); self.assertTrue(det.extension_mismatch)
    def test_text_kinds(self):
        d = tmpdir()
        (d / "a.json").write_text('[{"a":1}]'); (d / "b.csv").write_text("a,b\n1,2\n"); (d / "c.txt").write_text("hello")
        self.assertEqual([fd.detect(d / n).fmt for n in ("a.json", "b.csv", "c.txt")], ["json", "csv", "txt"])
    def test_zip_variants(self):
        d = tmpdir(); p = d / "x.zip"
        with zipfile.ZipFile(p, "w") as z: z.writestr("a.txt", "x")
        self.assertEqual(fd.detect(p).fmt, "zip")
        q = d / "fake.docx"
        with zipfile.ZipFile(q, "w") as z:
            z.writestr("[Content_Types].xml", "<x/>"); z.writestr("word/document.xml", "<x/>")
        self.assertEqual(fd.detect(q).fmt, "docx")
    def test_binary_garbage_unknown(self):
        d = tmpdir(); p = d / "x.bin"; p.write_bytes(bytes(range(256)) * 4)
        self.assertIsNone(fd.detect(p))
    def test_tgz(self):
        d = tmpdir(); src = d / "f.txt"; src.write_text("hi")
        with tarfile.open(d / "a.tar.gz", "w:gz") as t: t.add(src, "f.txt")
        self.assertEqual(fd.detect(d / "a.tar.gz").fmt, "tgz")

class Registry(unittest.TestCase):
    def test_image_options_valid(self):
        d = tmpdir(); p = make_png(d / "a.png")
        det, convs = reg.options_for(p)
        t = {c.target for c in convs}
        self.assertIn("jpg", t); self.assertNotIn("png", t); self.assertNotIn("mp3", t); self.assertNotIn("pdf", t)
    def test_unknown_gives_none(self):
        d = tmpdir(); p = d / "x.bin"; p.write_bytes(b"\x00\x01" * 100)
        self.assertEqual(reg.options_for(p), (None, []))
    def test_csv_options_include_json_and_tsv(self):
        d = tmpdir(); p = d / "a.csv"; p.write_text("a,b\n1,2\n")
        self.assertTrue({"tsv", "json"} <= {c.target for c in reg.options_for(p)[1]})

class Naming(unittest.TestCase):
    def test_default_name(self):
        self.assertEqual(default_output_name(Path("/x/Report.docx"), "pdf"), "Report_converted.pdf")
    def test_never_overwrite(self):
        d = tmpdir(); (d / "a_converted.png").write_text("x")
        self.assertEqual(resolve_output(d, "a_converted.png").name, "a_converted (2).png")
        (d / "a_converted (2).png").write_text("x")
        self.assertEqual(resolve_output(d, "a_converted.png").name, "a_converted (3).png")
        self.assertEqual(resolve_output(d, "a_converted.png", overwrite=True).name, "a_converted.png")
    def test_sanitize_traversal_and_reserved(self):
        self.assertEqual(sanitize_filename("../../etc/passwd"), "passwd")
        self.assertEqual(sanitize_filename("..\\..\\evil.exe"), "evil.exe")
        self.assertTrue(sanitize_filename("CON.txt").startswith("_"))
        self.assertNotIn(":", sanitize_filename('a:b*c?.txt'))
    def test_long_name(self):
        self.assertLessEqual(len(sanitize_filename("x" * 400 + ".png")), 180)
        self.assertTrue(sanitize_filename("x" * 400 + ".png").endswith(".png"))

class ImageConv(unittest.TestCase):
    def test_png_to_jpg_flattens_alpha(self):
        from PIL import Image
        d = tmpdir(); p = make_png(d / "a.png")
        r = convert(p, "jpg", d)
        self.assertTrue(r.ok, r.message)
        im = Image.open(r.output); self.assertEqual(im.mode, "RGB"); self.assertEqual(r.output.name, "a_converted.jpg")
    def test_png_keeps_alpha_webp(self):
        from PIL import Image
        d = tmpdir(); r = convert(make_png(d / "a.png"), "webp", d)
        self.assertTrue(r.ok); self.assertIn("A", Image.open(r.output).getbands())
    def test_unicode_and_spaces(self):
        d = tmpdir(); p = make_png(d / "मेरी तस्वीर 写真 ñ.png")
        r = convert(p, "bmp", d); self.assertTrue(r.ok, r.message); self.assertTrue(r.output.exists())
    def test_existing_dest_not_overwritten(self):
        d = tmpdir(); p = make_png(d / "a.png"); (d / "a_converted.jpg").write_text("keep")
        r = convert(p, "jpg", d)
        self.assertTrue(r.ok); self.assertEqual((d / "a_converted.jpg").read_text(), "keep"); self.assertNotEqual(r.output.name, "a_converted.jpg")
    def test_corrupt_image(self):
        d = tmpdir(); p = d / "bad.png"; p.write_bytes(b"\x89PNG\r\n\x1a\n" + b"garbage" * 20)
        r = convert(p, "jpg", d); self.assertFalse(r.ok); self.assertTrue(r.message)
        self.assertEqual([f.name for f in d.iterdir() if f.suffix == ".jpg"], [])
    def test_unsupported_target_rejected(self):
        d = tmpdir(); r = convert(make_png(d / "a.png"), "mp3", d)
        self.assertFalse(r.ok); self.assertIn("not supported", r.message)
    def test_missing_and_empty_source(self):
        d = tmpdir(); self.assertFalse(convert(d / "nope.png", "jpg", d).ok)
        (d / "e.png").write_bytes(b""); self.assertFalse(convert(d / "e.png", "jpg", d).ok)

class TextData(unittest.TestCase):
    def test_csv_json_roundtrip(self):
        d = tmpdir(); (d / "a.csv").write_text("name,age\nÅsa,30\nBob,25\n", encoding="utf-8")
        r = convert(d / "a.csv", "json", d); self.assertTrue(r.ok, r.message)
        data = json.loads(r.output.read_text(encoding="utf-8")); self.assertEqual(data[0], {"name": "Åsa", "age": "30"})
        r2 = convert(r.output, "csv", d); self.assertTrue(r2.ok, r2.message)
        self.assertIn("Åsa,30", r2.output.read_text(encoding="utf-8"))
    def test_invalid_json_reports(self):
        d = tmpdir(); (d / "a.json").write_text('{"a": '); r = convert(d / "a.json", "csv", d)
        self.assertFalse(r.ok); self.assertIn("Invalid JSON", r.message)
    def test_json_to_xml_and_back(self):
        d = tmpdir(); (d / "a.json").write_text('{"x": {"y": 1}, "z": [1, 2]}')
        r = convert(d / "a.json", "xml", d); self.assertTrue(r.ok, r.message)
        r2 = convert(r.output, "json", d); self.assertTrue(r2.ok, r2.message)
        self.assertEqual(json.loads(r2.output.read_text())["root"]["x"]["y"], "1")
    def test_html_to_txt_strips_script(self):
        d = tmpdir(); (d / "a.html").write_text("<html><script>evil()</script><p>Hello <b>you</b></p></html>")
        r = convert(d / "a.html", "txt", d); t = r.output.read_text()
        self.assertIn("Hello you", t); self.assertNotIn("evil", t)

class Archives(unittest.TestCase):
    def test_zip_to_tgz_and_back(self):
        d = tmpdir(); z = d / "a.zip"
        with zipfile.ZipFile(z, "w") as f: f.writestr("dir/h.txt", "hello"); f.writestr("w.txt", "w")
        r = convert(z, "tgz", d); self.assertTrue(r.ok, r.message)
        with tarfile.open(r.output) as t: self.assertEqual(sorted(n for n in t.getnames() if n.endswith(".txt")), ["dir/h.txt", "w.txt"])
        r2 = convert(r.output, "zip", d); self.assertTrue(r2.ok, r2.message)
        with zipfile.ZipFile(r2.output) as f: self.assertEqual(f.read("dir/h.txt"), b"hello")
    def test_zip_slip_blocked(self):
        d = tmpdir(); z = d / "evil.zip"
        with zipfile.ZipFile(z, "w") as f: f.writestr("../../escape.txt", "x")
        r = convert(z, "tar", d); self.assertFalse(r.ok); self.assertIn("traversal", r.message)
        self.assertFalse((d.parent / "escape.txt").exists())
    def test_tar_slip_and_symlink_blocked(self):
        d = tmpdir(); t = d / "evil.tar"
        with tarfile.open(t, "w") as tf:
            info = tarfile.TarInfo("../esc.txt"); data = b"x"; info.size = 1; tf.addfile(info, io.BytesIO(data))
        r = convert(t, "zip", d); self.assertFalse(r.ok)
    def test_corrupt_zip(self):
        d = tmpdir(); p = d / "a.zip"; p.write_bytes(b"PK\x03\x04" + b"junk" * 50)
        det = fd.detect(p)
        self.assertTrue(det is None or not convert(p, "tar", d).ok)

@unittest.skipUnless(HAS_FF, "FFmpeg not installed")
class Media(unittest.TestCase):
    def test_wav_to_mp3_flac_opus(self):
        d = tmpdir(); w = make_wav(d / "s.wav")
        for t in ("mp3", "flac", "opus", "ogg", "m4a", "aac"):
            r = convert(w, t, d); self.assertTrue(r.ok, f"{t}: {r.message}")
            self.assertGreater(r.output.stat().st_size, 0)
    def test_video_conversions(self):
        d = tmpdir(); v = make_video(d / "v.mp4")
        for t in ("mkv", "webm", "mov", "avi", "gif", "mp3"):
            r = convert(v, t, d); self.assertTrue(r.ok, f"{t}: {r.message}")
    def test_progress_reaches_one(self):
        d = tmpdir(); seen = []; r = convert(make_wav(d / "s.wav"), "mp3", d, progress=seen.append)
        self.assertTrue(r.ok); self.assertEqual(seen[-1], 1.0)
    def test_cancel_cleans_temp(self):
        import glob, tempfile
        d = tmpdir(); v = make_video(d / "v.mp4"); ev = threading.Event(); ev.set()
        before = set(glob.glob(tempfile.gettempdir() + "/conwheel_*"))
        r = convert(v, "mkv", d, cancel=ev)
        self.assertFalse(r.ok); self.assertTrue(r.cancelled)
        self.assertEqual(set(glob.glob(tempfile.gettempdir() + "/conwheel_*")) - before, set())
        self.assertEqual([f for f in d.iterdir() if f.stem.endswith("_converted")], [])
    def test_corrupt_audio(self):
        d = tmpdir(); p = d / "bad.wav"; p.write_bytes(b"RIFF\x00\x00\x00\x00WAVE" + b"\x00" * 50)
        r = convert(p, "mp3", d); self.assertFalse(r.ok)

@unittest.skipUnless(HAS_LO, "LibreOffice not installed")
class Office(unittest.TestCase):
    def test_txt_to_pdf_and_docx(self):
        d = tmpdir(); (d / "n.txt").write_text("Hello office world\n")
        for t in ("pdf", "docx"):
            r = convert(d / "n.txt", t, d); self.assertTrue(r.ok, f"{t}: {r.message}")
        self.assertEqual(fd.detect(r.output).fmt, "docx")
    def test_docx_to_pdf_txt_odt(self):
        d = tmpdir(); (d / "n.txt").write_text("Round trip text\n")
        docx = convert(d / "n.txt", "docx", d).output
        for t in ("pdf", "odt", "rtf", "html", "txt"):
            r = convert(docx, t, d); self.assertTrue(r.ok, f"{t}: {r.message}")
        self.assertIn("Round trip text", convert(docx, "txt", d, filename="o.txt").output.read_text(errors="ignore"))
    def test_csv_to_xlsx_ods_pdf_and_back(self):
        d = tmpdir(); (d / "t.csv").write_text("a,b\n1,2\n3,4\n")
        x = convert(d / "t.csv", "xlsx", d); self.assertTrue(x.ok, x.message)
        self.assertEqual(fd.detect(x.output).fmt, "xlsx")
        for t in ("ods", "pdf", "csv"):
            r = convert(x.output, t, d); self.assertTrue(r.ok, f"{t}: {r.message}")
    def test_pptx_listed_only_with_lo(self):
        self.assertIn("pdf", {c.target for c in reg.conversions_for("pptx")})

class Queue(unittest.TestCase):
    def test_batch_summary_with_failure(self):
        d = tmpdir(); a = make_png(d / "a.png"); b = make_png(d / "b.png", alpha=False)
        out = d / "out"; q = JobQueue(out)
        q.add(a, "jpg"); q.add(b, "webp"); q.add(d / "missing.png", "jpg")
        q.start().join(30)
        self.assertEqual(q.summary(), {"done": 2, "failed": 1, "cancelled": 0})
        self.assertEqual(len(list(out.iterdir())), 2)
    def test_same_name_conflict_in_batch(self):
        d = tmpdir(); (d / "x").mkdir(); (d / "y").mkdir()
        make_png(d / "x" / "a.png"); make_png(d / "y" / "a.png")
        q = JobQueue(d / "out"); q.add(d / "x" / "a.png", "jpg"); q.add(d / "y" / "a.png", "jpg")
        q.start().join(30); self.assertEqual(q.summary()["done"], 2)
        self.assertEqual(len(set(j.output for j in q.jobs)), 2)
    def test_cancel_batch(self):
        d = tmpdir(); q = JobQueue(d / "out"); q.add(make_png(d / "a.png"), "jpg"); q.pause()
        t = q.start(); q.cancel(); t.join(10)
        self.assertEqual(q.jobs[0].status, "cancelled"); self.assertFalse((d / "out").exists() and any((d / "out").iterdir()))
    def test_pause_resume(self):
        d = tmpdir(); q = JobQueue(d / "out"); q.add(make_png(d / "a.png"), "jpg"); q.pause()
        t = q.start(); t.join(0.5); self.assertTrue(t.is_alive()); self.assertEqual(q.jobs[0].status, "queued")
        q.resume(); t.join(10); self.assertEqual(q.jobs[0].status, "done")

class SettingsHistory(unittest.TestCase):
    def test_settings_persist(self):
        p = tmpdir() / "s.json"; s = Settings(); s.theme = "light"; s.shortcut_modifiers = ["ctrl", "shift"]; s.save(p)
        s2 = Settings.load(p); self.assertEqual((s2.theme, s2.shortcut_modifiers), ("light", ["ctrl", "shift"]))
    def test_settings_corrupt_file_falls_back(self):
        p = tmpdir() / "s.json"; p.write_text("{not json"); self.assertEqual(Settings.load(p).theme, "dark")
    def test_history_add_clear_no_contents(self):
        p = tmpdir() / "h.json"; h = History(p); h.add("/a/b.png", "jpg", "/a/b_converted.jpg", True)
        self.assertEqual(History(p).items[0]["target"], "jpg"); self.assertEqual(set(History(p).items[0]), {"source", "target", "output", "ok", "message", "time"})
        h.clear(); self.assertEqual(History(p).items, [])

class Wheel(unittest.TestCase):
    def test_segments(self):
        self.assertEqual(wg.segment_at(0, -100, 4, 30), 0)     # up
        self.assertEqual(wg.segment_at(100, 0, 4, 30), 1)      # right
        self.assertEqual(wg.segment_at(0, 100, 4, 30), 2)      # down
        self.assertEqual(wg.segment_at(-100, 0, 4, 30), 3)     # left
        self.assertIsNone(wg.segment_at(5, 5, 4, 30)); self.assertIsNone(wg.segment_at(1, 1, 0, 30))
        self.assertEqual(wg.segment_at(1, -100, 8, 30), 0)
    def test_clamp_edges(self):
        self.assertEqual(wg.clamp_to_screen(5, 5, 300, 0, 0, 1920, 1080), (0, 0))
        self.assertEqual(wg.clamp_to_screen(1919, 1079, 300, 0, 0, 1920, 1080), (1620, 780))
    def test_step_wraps_and_more(self):
        self.assertEqual(wg.step(0, 5, -1), 4); self.assertEqual(wg.step(4, 5, 1), 0)
        shown, more = wg.split_common(list("abcdefghijkl"), lambda x: x in "abc")
        self.assertLessEqual(len(shown), wg.MAX_VISIBLE - 1 + 0); self.assertTrue(more)

class Shortcut(unittest.TestCase):
    def test_trigger_and_debounce(self):
        m = ShortcutMatcher(debounce=0.2)
        self.assertFalse(m.mouse_event("right", True))
        m.key_event("ctrl_l", True); m.key_event("alt_l", True)
        self.assertTrue(m.mouse_event("right", True)); self.assertFalse(m.mouse_event("right", True))
        self.assertFalse(m.mouse_event("left", True)); self.assertFalse(m.mouse_event("right", False))
    def test_disable_and_release(self):
        m = ShortcutMatcher(debounce=0); m.key_event("ctrl", True); m.key_event("alt", True)
        m.enabled = False; self.assertFalse(m.mouse_event("right", True))
        m.enabled = True; m.key_event("alt", False); self.assertFalse(m.mouse_event("right", True))

if __name__ == "__main__":
    unittest.main(verbosity=1)
