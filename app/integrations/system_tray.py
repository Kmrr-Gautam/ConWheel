from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import QMenu, QSystemTrayIcon

class Tray(QSystemTrayIcon):
    def __init__(self, icon: QIcon, app_ctrl):
        super().__init__(icon)
        self.ctrl = app_ctrl
        m = QMenu()
        m.addAction("Open conWheel", app_ctrl.show_main)
        m.addAction("Convert selected file", app_ctrl.convert_selected)
        self.toggle = QAction("Shortcut enabled"); self.toggle.setCheckable(True)
        self.toggle.setChecked(app_ctrl.settings.shortcut_enabled)
        self.toggle.toggled.connect(app_ctrl.set_shortcut_enabled)
        m.addAction(self.toggle)
        m.addAction("Settings", lambda: app_ctrl.show_main("settings"))
        m.addAction("Check installed engines", lambda: app_ctrl.show_main("settings"))
        m.addSeparator(); m.addAction("Exit", app_ctrl.quit)
        self.setContextMenu(m); self.setToolTip("conWheel")
        self.activated.connect(lambda r: app_ctrl.show_main() if r == QSystemTrayIcon.Trigger else None)
