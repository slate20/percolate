"""Help/quick-start guide, opened from anywhere via the global `h` binding
(see PercolateApp.action_show_help) — a plain Markdown viewer over static
copy in data/help_guide.md, not a screen with its own state or logic.
"""

from __future__ import annotations

from typing import ClassVar

from textual.app import ComposeResult
from textual.containers import VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Markdown

from percolate.config import HELP_GUIDE_PATH


def load_help_guide(path=HELP_GUIDE_PATH) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


class HelpModal(ModalScreen[None]):
    # "h" closes too, mirroring the key that opened it, so it isn't
    # re-intercepted by PercolateApp's own "h" binding and pushed again
    # on top of itself.
    BINDINGS: ClassVar[list[tuple[str, str, str]]] = [
        ("escape", "cancel", "Close"),
        ("h", "cancel", "Close"),
    ]

    def compose(self) -> ComposeResult:
        with VerticalScroll(id="help_picker"):
            yield Markdown(load_help_guide())

    def action_cancel(self) -> None:
        self.dismiss(None)
