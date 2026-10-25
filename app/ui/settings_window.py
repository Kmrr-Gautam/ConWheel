from PySide6.QtWidgets import (QCheckBox, QComboBox, QFileDialog, QFormLayout, QGroupBox, QHBoxLayout, QLabel, QLineEdit,
                               QPushButton, QScrollArea, QSpinBox, QVBoxLayout, QWidget)
from ..core import format_registry as reg

class SettingsWindow(QScrollArea):
    def __init__(self, ctrl):
        super().__init__(); self.ctrl = ctrl; s = ctrl.settings; self.setWidgetResizable(True)
        w = QWidget(); self.setWidget(w); lay = QVBoxLayout(w); h = QLabel("Settings"); h.setObjectName("h1"); lay.addWidget(h)
        def box(title):
            g = QGroupBox(title); f = QFormLayout(g); lay.addWidget(g); return f
        f = box("General")
        self.startup = QCheckBox("Launch at Windows startup (asks nothing else; can be turned off here)"); self.startup.setChecked(s.launch_at_startup); f.addRow(self.startup)
        self.tray = QCheckBox("Minimize to system tray"); self.tray.setChecked(s.minimize_to_tray); f.addRow(self.tray)
        self.outdir = QLineEdit(s.default_output_dir); self.outdir.setPlaceholderText("Same folder as the source file")
        b = QPushButton("Browse…"); b.clicked.connect(lambda: self.outdir.setText(QFileDialog.getExistingDirectory(self, "Output folder") or self.outdir.text()))
        r = QHBoxLayout(); r.addWidget(self.outdir); r.addWidget(b); f.addRow("Default output folder", r)
        self.tpl = QLineEdit(s.naming_template); f.addRow("Output naming ({name} = original)", self.tpl)
        f = box("Shortcut")
        self.sc_on = QCheckBox("Enable global activation"); self.sc_on.setChecked(s.shortcut_enabled); f.addRow(self.sc_on)
        self.mods = {m: QCheckBox(m.title()) for m in ("ctrl", "alt", "shift", "win")}
        row = QHBoxLayout()
        for m, c in self.mods.items(): c.setChecked(m in s.shortcut_modifiers); row.addWidget(c)
        f.addRow("Modifiers", row)
        self.btn = QComboBox(); [self.btn.addItem(x.title(), x) for x in ("right", "middle", "left")]; self.btn.setCurrentIndex(self.btn.findData(s.shortcut_button)); f.addRow("Mouse button", self.btn)
        self.sc_status = QLabel(ctrl.shortcut.status if ctrl.shortcut else "inactive"); self.sc_status.setObjectName("muted"); f.addRow("Status", self.sc_status)
        note = QLabel("conWheel installs a low-level listener only to see whether the chosen modifier keys are held when you click the chosen mouse button. "
                      "It does not record, store or transmit any keystrokes or mouse activity."); note.setWordWrap(True); note.setObjectName("muted"); f.addRow(note)
        ctx = QPushButton("Add 'Convert with conWheel' to Explorer context menu"); ctx.clicked.connect(ctrl.install_context_menu); f.addRow(ctx)
        f = box("Conversion")
        self.q = QSpinBox(); self.q.setRange(10, 100); self.q.setValue(s.image_quality); f.addRow("Default image quality", self.q)
        self.ab = QComboBox(); [self.ab.addItem(f"{x} kbps", x) for x in (96, 128, 160, 192, 256, 320)]; self.ab.setCurrentIndex(max(0, self.ab.findData(s.audio_bitrate_kbps))); f.addRow("Audio bitrate", self.ab)
        self.vp = QComboBox(); [self.vp.addItem(x.title(), x) for x in ("small", "balanced", "quality")]; self.vp.setCurrentIndex(max(0, self.vp.findData(s.video_preset))); f.addRow("Video preset", self.vp)
        self.meta = QCheckBox("Preserve metadata where supported"); self.meta.setChecked(s.preserve_metadata); f.addRow(self.meta)
        self.ask = QCheckBox("Ask before overwriting files"); self.ask.setChecked(s.ask_before_overwrite); f.addRow(self.ask)
        self.openf = QCheckBox("Open output folder after conversion"); self.openf.setChecked(s.open_folder_after); f.addRow(self.openf)
        self.notif = QCheckBox("Show completion notifications"); self.notif.setChecked(s.notifications); f.addRow(self.notif)
        f = box("Engines"); self.eng = f; self.refresh_engines()
        rb = QPushButton("Re-check engines"); rb.clicked.connect(self.refresh_engines); f.addRow(rb)
        f = box("Privacy")
        p = QLabel("All conversions run locally on this computer. Files are never uploaded and no analytics are collected. "
                   "History stores file names and paths only, never file contents."); p.setWordWrap(True); f.addRow(p)
        c = QPushButton("Clear conversion history"); c.clicked.connect(lambda: ctrl.history.clear()); f.addRow(c)
        save = QPushButton("Save settings"); save.setObjectName("primary"); save.clicked.connect(self.save); lay.addWidget(save); lay.addStretch()
    def refresh_engines(self):
        for i in reversed(range(self.eng.rowCount())):
            lbl = self.eng.itemAt(i, QFormLayout.LabelRole)
            if lbl and lbl.widget() and lbl.widget().property("engine"):
                self.eng.removeRow(i)
        for name, st in reg.engine_status().items():
            l = QLabel(("✔ " + (st["version"] or "installed")) if st["ok"] else "✖ missing — " + st["help"]); l.setWordWrap(True)
            n = QLabel(name); n.setProperty("engine", True); self.eng.insertRow(0, n, l)
    def save(self):
        s = self.ctrl.settings
        s.launch_at_startup, s.minimize_to_tray, s.default_output_dir, s.naming_template = self.startup.isChecked(), self.tray.isChecked(), self.outdir.text(), self.tpl.text() or "{name}_converted"
        s.shortcut_enabled = self.sc_on.isChecked(); s.shortcut_modifiers = [m for m, c in self.mods.items() if c.isChecked()] or ["ctrl", "alt"]
        s.shortcut_button = self.btn.currentData(); s.image_quality = self.q.value(); s.audio_bitrate_kbps = self.ab.currentData(); s.video_preset = self.vp.currentData()
        s.preserve_metadata, s.ask_before_overwrite, s.open_folder_after, s.notifications = self.meta.isChecked(), self.ask.isChecked(), self.openf.isChecked(), self.notif.isChecked()
        s.save(); self.ctrl.apply_settings()
