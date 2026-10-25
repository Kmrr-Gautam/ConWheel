from pathlib import Path
from PySide6.QtCore import Signal
from PySide6.QtWidgets import (QComboBox, QFileDialog, QHBoxLayout, QLabel, QPushButton, QTableWidget,
                               QTableWidgetItem, QVBoxLayout, QWidget, QProgressBar)
from ..core import format_registry as reg
from ..core.job_queue import JobQueue

class BatchWindow(QWidget):
    job_updated = Signal(int)
    def __init__(self, ctrl):
        super().__init__(); self.ctrl = ctrl; self.queue: JobQueue | None = None
        self.files: list[Path] = []; self.combos: list[QComboBox] = []
        lay = QVBoxLayout(self); h = QLabel("Batch Conversion"); h.setObjectName("h1"); lay.addWidget(h)
        self.t = QTableWidget(0, 4); self.t.setHorizontalHeaderLabels(["File", "Format", "Convert to", "Status"])
        self.t.setColumnWidth(0, 300); self.t.horizontalHeader().setStretchLastSection(True); lay.addWidget(self.t)
        self.bar = QProgressBar(); lay.addWidget(self.bar); self.summary = QLabel(""); self.summary.setObjectName("muted"); lay.addWidget(self.summary)
        row = QHBoxLayout()
        self.btns = {}
        for k, label, fn in (("add", "Add files…", self.add_dialog), ("rm", "Remove", self.remove), ("up", "Move up", lambda: self.move(-1)),
                             ("dn", "Move down", lambda: self.move(1)), ("dest", "Output folder…", self.pick_dest),
                             ("start", "Start", self.start), ("pause", "Pause", self.pause), ("cancel", "Cancel", self.cancel)):
            b = QPushButton(label); b.clicked.connect(fn); row.addWidget(b); self.btns[k] = b
        self.btns["start"].setObjectName("primary"); row.addStretch(); lay.addLayout(row)
        self.dest = ""; self.job_updated.connect(self._refresh_row)

    def add_files(self, paths):
        for p in map(Path, paths):
            det, convs = reg.options_for(p)
            r = self.t.rowCount(); self.t.insertRow(r); self.files.append(p)
            self.t.setItem(r, 0, QTableWidgetItem(p.name)); self.t.setItem(r, 1, QTableWidgetItem(det.fmt.upper() if det else "?"))
            cb = QComboBox(); [cb.addItem(c.target.upper(), c.target) for c in convs]; cb.setEnabled(bool(convs)); self.combos.append(cb)
            self.t.setCellWidget(r, 2, cb); self.t.setItem(r, 3, QTableWidgetItem("Ready" if convs else "Unsupported file"))
    def add_dialog(self):
        f, _ = QFileDialog.getOpenFileNames(self, "Add files"); self.add_files(f)
    def remove(self):
        r = self.t.currentRow()
        if r >= 0 and not self.queue: self.t.removeRow(r); del self.files[r]; del self.combos[r]
    def move(self, d):
        r = self.t.currentRow(); n = r + d
        if self.queue or not (0 <= r < len(self.files) and 0 <= n < len(self.files)): return
        paths = list(self.files); targets = [c.currentData() for c in self.combos]
        paths[r], paths[n] = paths[n], paths[r]; targets[r], targets[n] = targets[n], targets[r]
        self.files.clear(); self.combos.clear(); self.t.setRowCount(0); self.add_files(paths)
        for cb, t in zip(self.combos, targets):
            if t: cb.setCurrentIndex(max(0, cb.findData(t)))
        self.t.selectRow(n)
    def pick_dest(self):
        d = QFileDialog.getExistingDirectory(self, "Output folder"); self.dest = d or self.dest
    def start(self):
        if self.queue or not self.files: return
        self.queue = JobQueue(self.dest or self.ctrl.settings.default_output_dir or None, self.ctrl.options(),
                              on_update=lambda j: self.job_updated.emit(self.queue.jobs.index(j)))
        self.row_of = {}
        for i, (p, cb) in enumerate(zip(self.files, self.combos)):
            if cb.currentData(): self.queue.add(p, cb.currentData()); self.row_of[len(self.queue.jobs) - 1] = i
        self.queue.start()
    def _refresh_row(self, ji):
        if not self.queue: return
        j = self.queue.jobs[ji]; r = self.row_of[ji]
        self.t.setItem(r, 3, QTableWidgetItem({"running": f"{int(j.progress*100)}%", "done": "Done", "queued": "Queued"}.get(j.status, f"{j.status.title()}: {j.message}")))
        if j.status in ("done", "failed", "cancelled"):
            self.ctrl.history.add(j.src, j.target, j.output, j.status == "done", j.message)
        s = self.queue.summary(); fin = sum(s.values())
        self.bar.setValue(int(100 * fin / max(1, len(self.queue.jobs))))
        self.summary.setText(f"{s['done']} succeeded · {s['failed']} failed · {s['cancelled']} cancelled")
        if fin == len(self.queue.jobs): self.queue = None
    def pause(self):
        if self.queue:
            if self.btns["pause"].text() == "Pause": self.queue.pause(); self.btns["pause"].setText("Resume")
            else: self.queue.resume(); self.btns["pause"].setText("Pause")
    def cancel(self):
        if self.queue: self.queue.cancel()
