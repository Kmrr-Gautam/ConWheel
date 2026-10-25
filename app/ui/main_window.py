from pathlib import Path
from PySide6.QtCore import Qt
from PySide6.QtGui import QDragEnterEvent, QDropEvent
from PySide6.QtWidgets import (QComboBox, QFileDialog, QHBoxLayout, QLabel, QListWidget, QMainWindow, QPushButton,
                               QProgressBar, QStackedWidget, QVBoxLayout, QWidget, QLineEdit, QTextEdit)
from ..constants import APP_NAME, APP_VERSION
from ..core import format_registry as reg
from .batch_window import BatchWindow
from .history_view import HistoryView
from .settings_window import SettingsWindow

PAGES = ["Home", "Convert Files", "Batch Conversion", "Conversion History", "Favorites", "Settings", "About conWheel"]

class DropLabel(QLabel):
    def __init__(self, on_files):
        super().__init__("Drag & drop files here\nor use Browse Files"); self.setObjectName("drop"); self.setAlignment(Qt.AlignCenter)
        self.setAcceptDrops(True); self.setMinimumHeight(170); self.on_files = on_files
    def dragEnterEvent(self, e: QDragEnterEvent):
        if e.mimeData().hasUrls(): e.acceptProposedAction(); self.setProperty("hover", True); self.style().polish(self)
    def dragLeaveEvent(self, e): self.setProperty("hover", False); self.style().polish(self)
    def dropEvent(self, e: QDropEvent):
        self.setProperty("hover", False); self.style().polish(self)
        self.on_files([u.toLocalFile() for u in e.mimeData().urls() if u.isLocalFile()])

class MainWindow(QMainWindow):
    def __init__(self, ctrl):
        super().__init__(); self.ctrl = ctrl; self.setWindowTitle(APP_NAME); self.resize(1020, 680)
        root = QWidget(); root.setObjectName("root"); self.setCentralWidget(root); lay = QHBoxLayout(root); lay.setContentsMargins(0, 0, 0, 0)
        self.side = QListWidget(); self.side.setObjectName("sidebar"); self.side.addItems(PAGES); lay.addWidget(self.side)
        self.stack = QStackedWidget(); lay.addWidget(self.stack, 1)
        self.stack.addWidget(self._home()); self.stack.addWidget(self._convert())
        self.batch = BatchWindow(ctrl); self.stack.addWidget(self.batch)
        self.history = HistoryView(ctrl); self.stack.addWidget(self.history)
        self.stack.addWidget(self._favorites()); self.settings_page = SettingsWindow(ctrl); self.stack.addWidget(self.settings_page)
        self.stack.addWidget(self._about())
        self.side.currentRowChanged.connect(self._page); self.side.setCurrentRow(0)
        self.src: Path | None = None

    def go(self, name):
        self.side.setCurrentRow({"home": 0, "convert": 1, "batch": 2, "history": 3, "favorites": 4, "settings": 5, "about": 6}[name])
    def _page(self, i):
        self.stack.setCurrentIndex(i)
        if i == 0: self.refresh_home()
        if i == 3: self.history.refresh()
        if i == 4: self.refresh_favs()

    def _wrap(self, *widgets):
        w = QWidget(); l = QVBoxLayout(w); l.setContentsMargins(28, 24, 28, 24); l.setSpacing(12)
        for x in widgets: l.addWidget(x) if not isinstance(x, tuple) else l.addLayout(x[0])
        return w, l
    def _h(self, t): h = QLabel(t); h.setObjectName("h1"); return h
    def _muted(self, t): m = QLabel(t); m.setObjectName("muted"); m.setWordWrap(True); return m

    def _home(self):
        w, l = self._wrap(self._h("conWheel"), self._muted("Convert files fast with a radial menu. Everything runs locally."),
                          DropLabel(self.on_files))
        row = QHBoxLayout()
        for t, f in (("Browse Files", self.browse), ("Browse Folder", self.browse_folder)):
            b = QPushButton(t); b.clicked.connect(f); row.addWidget(b)
        row.addStretch(); l.addLayout(row)
        self.sc_label = self._muted(""); self.eng_label = self._muted(""); self.recent = QLabel(""); self.recent.setObjectName("muted"); self.recent.setWordWrap(True)
        for x in (self.sc_label, self.eng_label, QLabel("Recent conversions"), self.recent): l.addWidget(x)
        l.addStretch(); self.home_layout = l; return w
    def refresh_home(self):
        c = self.ctrl; s = c.settings
        mods = "+".join(m.title() for m in s.shortcut_modifiers)
        self.sc_label.setText(f"Shortcut: {mods}+{s.shortcut_button.title()} Click — {'active' if c.shortcut and c.shortcut.status == 'active' else 'not active (' + (c.shortcut.status if c.shortcut else 'disabled') + ')'}")
        st = reg.engine_status(); self.eng_label.setText("Engines: " + "  ".join(f"{k} {'✔' if v['ok'] else '✖'}" for k, v in st.items()))
        self.recent.setText("\n".join(f"{Path(i['source']).name} → {i['target'].upper()}  {'✔' if i['ok'] else '✖'}" for i in c.history.items[:5]) or "None yet")

    def _convert(self):
        self.info = QLabel("No file selected"); self.info.setWordWrap(True); self.fmt_box = QComboBox(); self.note = self._muted("")
        self.dest_edit = QLineEdit(); self.dest_edit.setPlaceholderText("Output folder (blank = same as source)")
        self.go_btn = QPushButton("Convert"); self.go_btn.setObjectName("primary"); self.go_btn.clicked.connect(self._do_convert)
        self.cancel_btn = QPushButton("Cancel"); self.cancel_btn.clicked.connect(lambda: self.ctrl.cancel_current()); self.bar = QProgressBar(); self.status = self._muted("")
        self.fmt_box.currentIndexChanged.connect(self._fmt_changed)
        w, l = self._wrap(self._h("Convert Files"), self.info, self.fmt_box, self.note, self.dest_edit)
        row = QHBoxLayout(); row.addWidget(self.go_btn); row.addWidget(self.cancel_btn); row.addStretch(); l.addLayout(row); l.addWidget(self.bar); l.addWidget(self.status); l.addStretch()
        self.convs = []; return w

    def set_source(self, path):
        self.src = Path(path); det, self.convs = reg.options_for(self.src); self.fmt_box.clear(); self.status.setText("")
        if not det: self.info.setText(f"<b>{self.src.name}</b><br>Unsupported or unrecognised file type."); return
        sz = self.src.stat().st_size / 1024
        self.info.setText(f"<b>{self.src.name}</b><br>{det.fmt.upper()} · {det.kind} · {sz:,.0f} KB"
                          + ("<br><i>Note: the file extension does not match its real content.</i>" if det.extension_mismatch else ""))
        for c in self.convs: self.fmt_box.addItem(c.target.upper() + ("  ★" if c.recommended else ""), c.target)
        self.go("convert")
    def _fmt_changed(self):
        c = next((x for x in self.convs if x.target == self.fmt_box.currentData()), None)
        self.note.setText((c.notes if c else "") + (" Engine: " + c.engine if c else ""))
    def _do_convert(self):
        if self.src and self.fmt_box.currentData():
            self.ctrl.convert_paths([str(self.src)], self.fmt_box.currentData(), dest=self.dest_edit.text() or None, ui=self)

    def on_files(self, paths):
        paths = [p for p in paths if Path(p).is_file()]
        if len(paths) == 1: self.set_source(paths[0])
        elif paths: self.batch.add_files(paths); self.go("batch")
    def browse(self):
        f, _ = QFileDialog.getOpenFileNames(self, "Select files"); self.on_files(f)
    def browse_folder(self):
        d = QFileDialog.getExistingDirectory(self, "Select folder")
        if d: self.on_files([str(p) for p in sorted(Path(d).iterdir()) if p.is_file()])

    def _favorites(self):
        self.fav_list = QListWidget(); w, l = self._wrap(self._h("Favorites"), self._muted("Favorite formats appear first on the wheel. Double-click to remove."), self.fav_list)
        self.fav_add = QComboBox(); from ..constants import FORMAT_CATEGORY
        self.fav_add.addItems(sorted(FORMAT_CATEGORY)); b = QPushButton("Add favorite"); b.clicked.connect(self._add_fav)
        r = QHBoxLayout(); r.addWidget(self.fav_add); r.addWidget(b); l.addLayout(r); self.fav_list.itemDoubleClicked.connect(self._rm_fav); return w
    def refresh_favs(self): self.fav_list.clear(); self.fav_list.addItems(self.ctrl.settings.favorites)
    def _add_fav(self):
        t = self.fav_add.currentText(); f = self.ctrl.settings.favorites
        if t not in f: f.append(t); self.ctrl.settings.save()
        self.refresh_favs()
    def _rm_fav(self, it): self.ctrl.settings.favorites.remove(it.text()); self.ctrl.settings.save(); self.refresh_favs()

    def _about(self):
        t = QTextEdit(); t.setReadOnly(True)
        t.setHtml(f"<h2>{APP_NAME} {APP_VERSION}</h2><p>Radial file converter. All processing is local; no telemetry.</p>"
                  "<p>Engines: Pillow, FFmpeg, LibreOffice, PyMuPDF. See LICENSES.md for details.</p>")
        w, _ = self._wrap(self._h("About conWheel"), t); return w

    def closeEvent(self, e):
        if self.ctrl.settings.minimize_to_tray and self.ctrl.tray: e.ignore(); self.hide()
        else: self.ctrl.quit(); e.accept()
