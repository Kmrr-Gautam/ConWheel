"""Application controller: wires UI, wheel, shortcut, tray, background workers."""
from __future__ import annotations
import sys
import threading
from pathlib import Path
from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal, QTimer
from PySide6.QtGui import QIcon, QCursor
from PySide6.QtNetwork import QLocalServer, QLocalSocket
from PySide6.QtWidgets import QApplication, QMessageBox, QSystemTrayIcon
from . import constants
from .config import History, Settings
from .converters.base import Options
from .core import format_registry as reg
from .core.conversion_manager import Result, convert
from .integrations import explorer_integration as ex
from .integrations.global_shortcut import GlobalShortcut
from .ui.conversion_dialog import ConversionDialog
from .ui.history_view import open_path
from .ui.main_window import MainWindow
from .ui.radial_wheel import RadialWheel

def app_file(*parts) -> Path:
    """Path inside the app package, both in development and in a PyInstaller bundle."""
    base = Path(sys._MEIPASS) / "app" if getattr(sys, "frozen", False) else Path(__file__).parent
    return base.joinpath(*parts)

def resource(*parts) -> Path:
    return app_file("resources", *parts)

class _Signals(QObject):
    progress = Signal(float); done = Signal(object); trigger = Signal(int, int); remote = Signal(list)

class _Worker(QRunnable):
    def __init__(self, fn, sig): super().__init__(); self.fn, self.sig = fn, sig
    def run(self): self.sig.done.emit(self.fn())

class Controller(QObject):
    SERVER = "conWheel-single-instance"
    def __init__(self, app: QApplication, start_hidden=False):
        super().__init__(); self.app = app; self.settings = Settings.load(); self.history = History()
        self.sig = _Signals(); self.pool = QThreadPool.globalInstance(); self.cancel_ev = threading.Event(); self.busy = False
        icon_path = resource("icons", "conWheel.ico"); self.icon = QIcon(str(icon_path)) if icon_path.exists() else QIcon()
        app.setWindowIcon(self.icon); app.setQuitOnLastWindowClosed(False)
        self.shortcut: GlobalShortcut | None = None
        self.main = MainWindow(self); self.wheel = RadialWheel()
        self.wheel.chosen.connect(self._wheel_chosen); self.wheel.cancelled.connect(lambda: None)
        self.pending: list[str] = []
        self.sig.trigger.connect(self.show_wheel_at); self.sig.done.connect(self._finished); self.sig.progress.connect(self._progress)
        self.sig.remote.connect(self._remote_paths)
        self.tray = None
        if QSystemTrayIcon.isSystemTrayAvailable():
            from .integrations.system_tray import Tray
            self.tray = Tray(self.icon, self); self.tray.show()
        self.shortcut: GlobalShortcut | None = None; self.apply_settings()
        self._collect = []; self._collect_timer = QTimer(self); self._collect_timer.setSingleShot(True); self._collect_timer.timeout.connect(self._flush_remote)
        self._start_server()
        if not start_hidden: self.main.show()

    # ---- single instance / explorer context menu ----------------------------
    @classmethod
    def send_to_running(cls, paths: list[str]) -> bool:
        s = QLocalSocket(); s.connectToServer(cls.SERVER)
        if not s.waitForConnected(300): return False
        s.write(("\n".join(paths) or "@show").encode("utf-8")); s.flush(); s.waitForBytesWritten(1000); s.disconnectFromServer(); return True
    def _start_server(self):
        QLocalServer.removeServer(self.SERVER); self.server = QLocalServer(self); self.server.listen(self.SERVER)
        self.server.newConnection.connect(self._on_conn)
    def _on_conn(self):
        c = self.server.nextPendingConnection(); c.waitForReadyRead(500)
        data = bytes(c.readAll()).decode("utf-8", "replace"); c.disconnectFromServer()
        self.sig.remote.emit([p for p in data.split("\n") if p])
    def _remote_paths(self, paths):
        if paths == ["@show"]: self.show_main(); return
        self._collect += paths; self._collect_timer.start(400)       # gather multi-select launches
    def _flush_remote(self):
        paths, self._collect = self._collect, []; self.show_wheel_for(paths)

    # ---- settings / shortcut -------------------------------------------------
    def apply_settings(self):
        s = self.settings
        if self.shortcut is None: self.shortcut = GlobalShortcut(lambda x, y: self.sig.trigger.emit(x, y), s.shortcut_modifiers, s.shortcut_button)
        self.shortcut.reconfigure(s.shortcut_modifiers, s.shortcut_button)
        if s.shortcut_enabled: self.shortcut.start(); self.shortcut.set_enabled(True)
        else: self.shortcut.set_enabled(False)
        if getattr(sys, "frozen", False):
            try: ex.set_launch_at_login(sys.executable, s.launch_at_startup)
            except OSError: pass
    def set_shortcut_enabled(self, on):
        self.settings.shortcut_enabled = on; self.settings.save(); self.apply_settings()
    def install_context_menu(self):
        ok = ex.install_context_menu(sys.executable if getattr(sys, "frozen", False) else str(Path(sys.argv[0]).resolve()))
        QMessageBox.information(self.main, "conWheel", "Context-menu entry added." if ok else "Context-menu integration is only available on Windows.")

    # ---- wheel flow ------------------------------------------------------------
    def show_main(self, page=None):
        self.main.show(); self.main.raise_(); self.main.activateWindow()
        if page: self.main.go(page)
    def convert_selected(self):
        pos = QCursor.pos(); self.show_wheel_at(pos.x(), pos.y())
    def show_wheel_at(self, x, y):
        paths = ex.get_selected_paths()
        if not paths:
            if self.tray: self.tray.showMessage("conWheel", "Couldn't read an Explorer selection. Select a file in Explorer first, "
                                                "use right-click → Convert with conWheel, or drag a file onto conWheel.", QSystemTrayIcon.Information, 5000)
            return
        self.show_wheel_for(paths, x, y)
    def show_wheel_for(self, paths, x=None, y=None):
        paths = [p for p in paths if Path(p).is_file()]
        if not paths: return
        det, convs = reg.options_for(paths[0])
        if len(paths) > 1:
            fmts = {(reg.options_for(p)[0] or None) and reg.options_for(p)[0].fmt for p in paths}
            if len(fmts) != 1 or None in fmts: self.main.batch.add_files(paths); self.show_main("batch"); return
        if not det or not convs:
            QMessageBox.information(None, "conWheel", f"{Path(paths[0]).name}: this file type has no available conversions.\n"
                                    "If you expected some, check Settings → Engines for missing components."); return
        self.pending = paths
        title = Path(paths[0]).name if len(paths) == 1 else f"{len(paths)} files"
        self.wheel.set_source(title, det.fmt, convs, [c.target for c in convs if c.recommended], self.settings.favorites)
        pos = QCursor.pos(); self.wheel.popup_at(x if x is not None else pos.x(), y if y is not None else pos.y())
    def _wheel_chosen(self, target):
        paths = self.pending
        if len(paths) > 1:
            self.main.batch.add_files(paths)
            for cb in self.main.batch.combos: cb.setCurrentIndex(max(0, cb.findData(target)))
            self.show_main("batch"); return
        self.convert_paths(paths, target, ask=True)

    # ---- conversion -----------------------------------------------------------------
    def options(self) -> Options:
        s = self.settings; return Options(s.image_quality, None, s.preserve_metadata, s.audio_bitrate_kbps, s.video_preset)
    def convert_paths(self, paths, target, dest=None, ask=False, ui=None):
        if self.busy: QMessageBox.information(self.main, "conWheel", "A conversion is already running."); return
        src = Path(paths[0]); _, convs = reg.options_for(src); conv = next((c for c in convs if c.target == target), None)
        opts, fname = self.options(), None; dest = dest or self.settings.default_output_dir or None
        if conv is None: QMessageBox.warning(self.main, "conWheel", "That conversion isn't available."); return
        if ask and (conv.lossy or conv.notes):
            dlg = ConversionDialog(src, conv, self.settings, self.main)
            if not dlg.exec(): return
            opts, dest, fname = dlg.result_options()
        overwrite = False
        if fname and dest:
            from .core.output_manager import resolve_output
            target_path = Path(dest) / fname
            if target_path.exists():
                if self.settings.ask_before_overwrite and QMessageBox.question(self.main, "conWheel", f"{target_path.name} already exists. Overwrite it?") == QMessageBox.Yes: overwrite = True
        self.cancel_ev = threading.Event(); self.busy = True; self._ui = ui; ev = self.cancel_ev
        job = lambda: convert(src, target, dest, opts, fname, overwrite, ev, lambda f: self.sig.progress.emit(f), self.settings.naming_template)
        if ui: ui.bar.setValue(0); ui.status.setText("Converting…")
        self.pool.start(_Worker(job, self.sig))
    def cancel_current(self): self.cancel_ev.set()
    def _progress(self, f):
        if getattr(self, "_ui", None): self._ui.bar.setValue(int(f * 100))
    def _finished(self, r: Result):
        self.busy = False; ui = getattr(self, "_ui", None)
        self.history.add(r.src, r.target, r.output, r.ok, r.message)
        if ui: ui.status.setText(("Saved: " + str(r.output)) if r.ok else r.message); ui.bar.setValue(100 if r.ok else 0)
        if self.tray and self.settings.notifications:
            self.tray.showMessage("conWheel", f"Saved {r.output.name}" if r.ok else f"Conversion failed: {r.message}", QSystemTrayIcon.Information if r.ok else QSystemTrayIcon.Warning, 4000)
        if r.ok:
            box = QMessageBox(self.main); box.setWindowTitle("Conversion complete"); box.setText(f"Saved {r.output.name}")
            o = box.addButton("Open file", QMessageBox.AcceptRole); f = box.addButton("Open folder", QMessageBox.ActionRole); box.addButton("Close", QMessageBox.RejectRole)
            box.exec()
            if box.clickedButton() is o: open_path(str(r.output))
            elif box.clickedButton() is f: open_path(str(r.output.parent))
            if self.settings.open_folder_after and box.clickedButton() is not f: open_path(str(r.output.parent))
        elif not r.cancelled: QMessageBox.warning(self.main, "Conversion failed", r.message)
    def quit(self):
        self.cancel_ev.set()
        if self.shortcut: self.shortcut.stop()
        if self.tray: self.tray.hide()
        self.app.quit()
