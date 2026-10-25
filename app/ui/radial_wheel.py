"""Frameless translucent radial wheel. Geometry lives in wheel_geometry (unit-tested)."""
from __future__ import annotations
import math
from PySide6.QtCore import QEasingCurve, QPoint, QPointF, QPropertyAnimation, QRectF, Qt, Signal, Property
from PySide6.QtGui import QColor, QFont, QGuiApplication, QPainter, QPainterPath, QPen, QRadialGradient
from PySide6.QtWidgets import QWidget
from ..constants import CATEGORIES, COMMON_FORMATS, FORMAT_CATEGORY
from . import wheel_geometry as wg

ACCENT = QColor(77, 124, 255)

class RadialWheel(QWidget):
    chosen = Signal(str)       # target format key
    cancelled = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.StrongFocus)
        self.items: list[tuple[str, str]] = []     # (key, label)  key may be "@cat:Images" / "@more" / "@back"
        self.hover = -1
        self.title, self.subtitle = "", ""
        self._convs: list = []
        self._scale = 0.6
        self.anim = QPropertyAnimation(self, b"scaleFactor", self)
        self.anim.setDuration(140); self.anim.setEasingCurve(QEasingCurve.OutCubic)
        self.recommended: set[str] = set()
        self.favorites: set[str] = set()

    # animated property
    def _get(self): return self._scale
    def _set(self, v): self._scale = v; self.update()
    scaleFactor = Property(float, _get, _set)

    # ---- content -------------------------------------------------------
    def set_source(self, name: str, fmt: str, convs: list, recommended=(), favorites=()):
        self._convs = convs; self.title = name; self.subtitle = fmt.upper()
        self.recommended, self.favorites = set(recommended), set(favorites)
        self._show_root()

    def _show_root(self):
        targets = [c.target for c in self._convs]
        cats = {}
        for t in targets: cats.setdefault(FORMAT_CATEGORY.get(t, "Other"), []).append(t)
        if len(targets) <= wg.MAX_VISIBLE or len(cats) == 1:
            shown, more = wg.split_common(targets, lambda t: t in COMMON_FORMATS or t in self.favorites)
            self.items = [(t, t.upper()) for t in shown] + ([("@more", "More…")] if more else [])
            self._more = more
        else:
            self.items = [(f"@cat:{c}", c) for c in CATEGORIES if c in cats] + [(f"@cat:Other", "Other")] * ("Other" in cats)
        self._cats = cats
        self.hover = 0 if self.items else -1; self.update()

    def _show_list(self, keys, back=True):
        self.items = [(k, k.upper()) for k in keys] + ([("@back", "‹ Back")] if back else [])
        self.hover = 0; self.update()

    # ---- show near cursor ------------------------------------------------
    def popup_at(self, gx: int, gy: int):
        screen = QGuiApplication.screenAt(QPoint(gx, gy)) or QGuiApplication.primaryScreen()
        g = screen.geometry()
        d = wg.wheel_diameter(len(self.items) or 6, min(g.width(), g.height()))
        x, y = wg.clamp_to_screen(gx, gy, d, g.x(), g.y(), g.width(), g.height())
        self.setGeometry(x, y, d, d)
        self.show(); self.raise_(); self.activateWindow(); self.setFocus()
        self.anim.stop(); self.anim.setStartValue(0.6); self.anim.setEndValue(1.0); self.anim.start()

    # ---- painting --------------------------------------------------------
    def _geom(self):
        d = min(self.width(), self.height()); c = QPointF(self.width() / 2, self.height() / 2)
        return c, d / 2 * 0.96 * self._scale, d / 2 * 0.30 * self._scale

    def paintEvent(self, _):
        p = QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        c, R, r = self._geom(); n = len(self.items)
        p.setPen(Qt.NoPen); p.setBrush(QColor(20, 21, 26, 150)); p.drawEllipse(c, R + 6, R + 6)
        if n:
            step = 360 / n
            for i, (key, label) in enumerate(self.items):
                start = 90 - (i * step) - step / 2           # Qt angles: CCW from 3 o'clock
                path = QPainterPath()
                path.arcMoveTo(QRectF(c.x() - R, c.y() - R, 2 * R, 2 * R), start)
                path.arcTo(QRectF(c.x() - R, c.y() - R, 2 * R, 2 * R), start, -step)
                path.arcTo(QRectF(c.x() - r, c.y() - r, 2 * r, 2 * r), start - step, step)
                path.closeSubpath()
                hot = i == self.hover
                col = QColor(77, 124, 255, 230) if hot else QColor(38, 40, 48, 225)
                p.setPen(QPen(QColor(255, 255, 255, 28), 1.2)); p.setBrush(col); p.drawPath(path)
                mid = math.radians(i * step); rr = (R + r) / 2
                tx, ty = c.x() + rr * math.sin(mid), c.y() - rr * math.cos(mid)
                p.setPen(QColor("white") if hot else QColor(215, 218, 226))
                f = QFont("Segoe UI", max(8, int(R / 14)), QFont.DemiBold); p.setFont(f)
                p.drawText(QRectF(tx - 45, ty - 14, 90, 28), Qt.AlignCenter, label)
                if key in self.recommended:
                    p.setBrush(QColor(255, 196, 61)); p.setPen(Qt.NoPen); p.drawEllipse(QPointF(tx + 30, ty - 16), 3.5, 3.5)
        g = QRadialGradient(c, r); g.setColorAt(0, QColor(36, 38, 46, 245)); g.setColorAt(1, QColor(26, 27, 33, 245))
        p.setPen(QPen(QColor(255, 255, 255, 40), 1.2)); p.setBrush(g); p.drawEllipse(c, r - 4, r - 4)
        p.setPen(QColor("white")); p.setFont(QFont("Segoe UI", max(8, int(r / 6)), QFont.DemiBold))
        name = self.title if len(self.title) < 18 else self.title[:15] + "…"
        p.drawText(QRectF(c.x() - r, c.y() - r * .55, 2 * r, r * .6), Qt.AlignCenter, name)
        p.setPen(QColor(140, 146, 160)); p.setFont(QFont("Segoe UI", max(7, int(r / 8))))
        p.drawText(QRectF(c.x() - r, c.y() - r * .05, 2 * r, r * .4), Qt.AlignCenter, f"{self.subtitle}  ·  Esc to cancel")

    # ---- interaction -------------------------------------------------------
    def _index_at(self, pos):
        c, R, r = self._geom()
        return wg.segment_at(pos.x() - c.x(), pos.y() - c.y(), len(self.items), r, R + 8)

    def mouseMoveEvent(self, e):
        i = self._index_at(e.position())
        if i is not None and i != self.hover: self.hover = i; self.update()
    def mousePressEvent(self, e):
        if e.button() == Qt.RightButton: self._back_or_cancel(); return
        i = self._index_at(e.position())
        if i is None:                      # centre = cancel; outside ring = cancel
            self.close_wheel(); return
        self.hover = i; self._activate()
    def wheelEvent(self, e):
        self.hover = wg.step(self.hover, len(self.items), -1 if e.angleDelta().y() > 0 else 1); self.update()
    def keyPressEvent(self, e):
        k = e.key()
        if k in (Qt.Key_Right, Qt.Key_Down): self.hover = wg.step(self.hover, len(self.items), 1)
        elif k in (Qt.Key_Left, Qt.Key_Up): self.hover = wg.step(self.hover, len(self.items), -1)
        elif k in (Qt.Key_Return, Qt.Key_Enter): self._activate()
        elif k == Qt.Key_Escape: self.close_wheel()
        elif k == Qt.Key_Backspace: self._back_or_cancel()
        self.update()

    def _back_or_cancel(self):
        if any(k == "@back" for k, _ in self.items): self._show_root()
        else: self.close_wheel()

    def _activate(self):
        if not (0 <= self.hover < len(self.items)): return
        key, _ = self.items[self.hover]
        if key == "@back": self._show_root()
        elif key == "@more": self._show_list(self._more)
        elif key.startswith("@cat:"): self._show_list(self._cats.get(key[5:], []))
        else:
            self.hide(); self.chosen.emit(key)

    def close_wheel(self):
        self.hide(); self.cancelled.emit()
    def focusOutEvent(self, e):
        if self.isVisible() and not self.underMouse(): self.close_wheel()
        super().focusOutEvent(e)
