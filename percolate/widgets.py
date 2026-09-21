"""Small ambient/decorative widgets shared by FarmScreen and RoastScreen.

These exist purely for overview.md §4 (Aesthetic & Feel Guidelines) — they
carry no game state and never affect gameplay. Kept deliberately sparse and
slow: a single drifting glyph, advanced once per caller-controlled tick.
"""

from __future__ import annotations

import time

from textual.widgets import Static

from percolate.config import TOD_BUCKETS

# The only hints that apply everywhere, everywhere: which key switches to
# which screen. Rendered as one slim, muted line per screen instead of
# Textual's default Footer, which lists every binding (including each
# screen's own contextual actions) as loud key-chips. Screen-specific
# actions are hinted inline instead, next to the control they affect.
NAV_HINT = "f Farm    r Roast    m Market    h Help    q Quit"


class AmbientBar(Static):
    """A single glyph drifting across an otherwise blank line."""

    def __init__(self, glyphs: str, width: int = 30, **kwargs) -> None:
        super().__init__(**kwargs)
        self._glyphs = glyphs
        self._width = width
        self._position = 0
        self._glyph_index = 0

    def on_mount(self) -> None:
        self.advance()

    def advance(self) -> None:
        self._position = (self._position + 1) % self._width
        self._glyph_index = (self._glyph_index + 1) % len(self._glyphs)
        line = [" "] * self._width
        line[self._position] = self._glyphs[self._glyph_index]
        self.update("".join(line))


_TOD_CLASSES = tuple(f"tod-{name}" for name, _ in TOD_BUCKETS)


def time_of_day_bucket(now: float | None = None) -> str:
    """Which of the TOD_BUCKETS windows `now` falls into, by name."""
    hour = time.localtime(now if now is not None else time.time()).tm_hour
    bucket = TOD_BUCKETS[-1][0]
    for name, start_hour in TOD_BUCKETS:
        if hour >= start_hour:
            bucket = name
    return bucket


def time_of_day_class(now: float | None = None) -> str:
    return f"tod-{time_of_day_bucket(now)}"


def apply_time_of_day(widget: Static, now: float | None = None) -> None:
    """Swap the widget's tod-* class for the one matching the current hour."""
    current = time_of_day_class(now)
    for cls in _TOD_CLASSES:
        if cls != current:
            widget.remove_class(cls)
    widget.add_class(current)


def format_remaining(seconds: float) -> str:
    """Render a countdown as "Xh Ym" (or just "Ym" under an hour)."""
    seconds = max(0, int(seconds))
    hours, remainder = divmod(seconds, 3600)
    minutes = remainder // 60
    if hours:
        return f"{hours}h {minutes}m"
    return f"{minutes}m"
