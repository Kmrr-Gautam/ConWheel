import os, sys
from pathlib import Path
from PySide6.QtWidgets import QAbstractItemView, QHBoxLayout, QLabel, QPushButton, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget

def open_path(p: str):
    if sys.platform == "win32": os.startfile(p)       # noqa
    else:
        import subprocess; subprocess.Popen(["xdg-open", p])

def reveal(p: str):
    if sys.platform == "win32":
        import subprocess; subprocess.Popen(["explorer", "/select,", str(Path(p))])
    else: open_path(str(Path(p).parent))

class HistoryView(QWidget):
    def __init__(self, ctrl):
        super().__init__(); self.ctrl = ctrl
        lay = QVBoxLayout(self); h = QLabel("Conversion History"); h.setObjectName("h1"); lay.addWidget(h)
        self.t = QTableWidget(0, 6); self.t.setHorizontalHeaderLabels(["Source", "To", "Destination", "Date", "Result", ""])
        self.t.setSelectionBehavior(QAbstractItemView.SelectRows); self.t.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.t.horizontalHeader().setStretchLastSection(True); self.t.setColumnWidth(0, 220); self.t.setColumnWidth(2, 260); lay.addWidget(self.t)
        row = QHBoxLayout()
        for label, fn in (("Open output", self.open_out), ("Open folder", self.open_folder), ("Retry", self.retry), ("Clear history", self.clear)):
            b = QPushButton(label); b.clicked.connect(fn); row.addWidget(b)
        row.addStretch(); lay.addLayout(row); self.refresh()
    def refresh(self):
        items = self.ctrl.history.items; self.t.setRowCount(len(items))
        for r, it in enumerate(items):
            for c, v in enumerate([Path(it["source"]).name, it["target"].upper(), it["output"], it["time"], "OK" if it["ok"] else f"Failed: {it['message']}"]):
                self.t.setItem(r, c, QTableWidgetItem(v))
    def _sel(self):
        r = self.t.currentRow(); return self.ctrl.history.items[r] if 0 <= r < len(self.ctrl.history.items) else None
    def open_out(self):
        it = self._sel()
        if it and it["ok"] and Path(it["output"]).exists(): open_path(it["output"])
    def open_folder(self):
        it = self._sel()
        if it and it["output"]: reveal(it["output"])
    def retry(self):
        it = self._sel()
        if it: self.ctrl.convert_paths([it["source"]], it["target"])
    def clear(self): self.ctrl.history.clear(); self.refresh()
