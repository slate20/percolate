"""Percolate's own color themes.

Two warm coffee-roastery palettes — roasted browns, crema gold, terracotta —
registered with Textual's theme system so built-in widgets (buttons, option
lists, selection highlights, scrollbars) match the hand-picked colors
already used throughout the custom ASCII art and CSS, instead of Textual's
default blue-accented dark theme.

Both are dark themes (`dark=True`) — "latte" is only a softer, lighter-roast
variant of "mocha", never a bright/light theme. Both are registered; whichever
is active is chosen in main.py, and either can be picked from the command
palette (ctrl+p) since Textual lists every registered theme there.
"""

from __future__ import annotations

from textual.theme import Theme

PERCOLATE_MOCHA = Theme(
    name="percolate-mocha",
    dark=True,
    background="#1b1410",
    surface="#241a14",
    panel="#2f2119",
    primary="#c9a13b",
    secondary="#a8643c",
    accent="#e0b84c",
    warning="#d98c3d",
    error="#b3503f",
    success="#7a9b5c",
    foreground="#ece0d1",
)

PERCOLATE_LATTE = Theme(
    name="percolate-latte",
    dark=True,
    background="#38322e",
    surface="#423c38",
    panel="#4b4540",
    primary="#caaf72",
    secondary="#b38366",
    accent="#dec58a",
    warning="#d1a26d",
    error="#b57b6d",
    success="#94aa83",
    foreground="#f3e9da",
)

PERCOLATE_THEMES = (PERCOLATE_MOCHA, PERCOLATE_LATTE)
