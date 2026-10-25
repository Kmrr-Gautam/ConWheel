"""Pure-Python geometry for the radial wheel (no Qt), so it can be unit tested."""
from __future__ import annotations
import math

def segment_at(dx: float, dy: float, n: int, inner_radius: float, outer_radius: float | None = None) -> int | None:
    """Segment index under offset (dx, dy) from wheel centre; segment 0 is centred at 12 o'clock,
    indices increase clockwise. Returns None inside the centre hole (or outside outer radius)."""
    if n <= 0:
        return None
    r = math.hypot(dx, dy)
    if r < inner_radius or (outer_radius is not None and r > outer_radius):
        return None
    ang = math.degrees(math.atan2(dx, -dy)) % 360          # 0 = up, clockwise
    step = 360 / n
    return int(((ang + step / 2) % 360) // step)

def segment_center_angle(i: int, n: int) -> float:
    return i * 360 / n

def wheel_diameter(n: int, screen_min_side: int, dpr: float = 1.0) -> int:
    base = 360 + max(0, n - 6) * 18
    return int(min(base * dpr, screen_min_side * 0.8))

def clamp_to_screen(cx: float, cy: float, diameter: int, left: int, top: int, width: int, height: int):
    """Top-left position so the wheel stays fully on screen while staying as near the cursor as possible."""
    half = diameter / 2
    x = min(max(cx - half, left), left + width - diameter)
    y = min(max(cy - half, top), top + height - diameter)
    return int(x), int(y)

def step(index: int, n: int, delta: int) -> int:
    return (index + delta) % n if n else 0

MAX_VISIBLE = 8   # beyond this, extra formats move into a "More" segment
def split_common(items: list, is_common) -> tuple[list, list]:
    common = [i for i in items if is_common(i)]
    rest = [i for i in items if not is_common(i)]
    if len(items) <= MAX_VISIBLE:
        return items, []
    shown = (common or items)[:MAX_VISIBLE - 1]
    more = [i for i in items if i not in shown]
    return shown, more
