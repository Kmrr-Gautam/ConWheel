import argparse
import sys

def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="conWheel")
    ap.add_argument("--convert", nargs="*", default=[], help="files to convert (used by the Explorer context menu)")
    ap.add_argument("--tray", action="store_true", help="start hidden in the system tray")
    ap.add_argument("files", nargs="*")
    a = ap.parse_args(argv)
    from PySide6.QtWidgets import QApplication
    from PySide6.QtCore import Qt
    from .constants import APP_NAME, APP_VERSION, ORG_NAME
    app = QApplication(sys.argv); app.setApplicationName(APP_NAME); app.setApplicationVersion(APP_VERSION); app.setOrganizationName(ORG_NAME)
    from .application import Controller, resource
    paths = [*a.convert, *a.files]
    if Controller.send_to_running(paths):          # already running: hand over and exit
        return 0
    from .application import app_file
    q = app_file("ui", "styles", "dark.qss")
    if q.exists(): app.setStyleSheet(q.read_text(encoding="utf-8"))
    ctrl = Controller(app, start_hidden=a.tray and not paths)
    if paths: ctrl.show_wheel_for(paths)
    return app.exec()

if __name__ == "__main__":
    sys.exit(main())
