"""Small ambient/decorative widgets shared by FarmScreen and RoastScreen.

These exist purely for overview.md §4 (Aesthetic & Feel Guidelines) — they
carry no game state and never affect gameplay. Kept deliberately sparse and
slow: a single drifting glyph, advanced once per caller-controlled tick.
"""

from __future__ import annotations

import json
import time

from textual.widgets import Static

from percolate.config import FARMHOUSE_PATH

# The only hints that apply everywhere, everywhere: which key switches to
# which screen. Rendered as one slim, muted line per screen instead of
# Textual's default Footer, which lists every binding (including each
# screen's own contextual actions) as loud key-chips. Screen-specific
# actions are hinted inline instead, next to the control they affect.
NAV_HINT = "f Farm    r Roast    m Market    h Help    q Quit"


def load_farmhouse_data(path=FARMHOUSE_PATH) -> dict:
    """Backdrop scene variants ("compact" / "large") for FarmScreen."""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


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


_TOD_CLASSES = ("tod-morning", "tod-midday", "tod-evening", "tod-night")


def time_of_day_class(now: float | None = None) -> str:
    hour = time.localtime(now if now is not None else time.time()).tm_hour
    if 5 <= hour < 11:
        return "tod-morning"
    if 11 <= hour < 17:
        return "tod-midday"
    if 17 <= hour < 22:
        return "tod-evening"
    return "tod-night"


def apply_time_of_day(widget: Static, now: float | None = None) -> None:
    """Swap the widget's tod-* class for the one matching the current hour."""
    current = time_of_day_class(now)
    for cls in _TOD_CLASSES:
        if cls != current:
            widget.remove_class(cls)
    widget.add_class(current)
