"""Focus-driven highlight behavior shared by every Tab-cycled list-like
widget (ListView in Market/UpgradeModal, OptionList/SelectionList in
Roast's builder panel and Farm's BeanPickerScreen).

Textual's own default keeps a *dimmed* highlight visible on a list's last
cursor position even after it loses focus, rather than clearing it — which
reads as ambiguous to a non-dev player switching panes with Tab (is that
item selected, or just where the cursor happened to be last?). To match
the "depth without friction" pillar, these subclasses make it a clean
binary instead: gaining focus auto-highlights the first item immediately
(no more needing to know an arrow key wakes the cursor up), and losing
focus clears the highlight outright rather than leaving a dim ghost of it.
"""

from __future__ import annotations

from textual.widgets import ListView, OptionList, SelectionList


class FocusHighlightListView(ListView):
    """ListView with auto-highlight-on-focus / clear-on-blur (see module
    docstring). Enter while still focused doesn't touch focus, so it
    doesn't trigger either branch here — the highlight only moves for an
    actual Tab in/out."""

    def watch_has_focus(self, value: bool) -> None:
        super().watch_has_focus(value)
        if value:
            self.sync_focus_highlight()
        else:
            self.index = None

    def sync_focus_highlight(self) -> None:
        """Highlight the first item if this list has focus but nothing is
        highlighted. watch_has_focus only fires on an actual focus
        transition, so a list that's already focused *before* it has any
        content (e.g. the very first widget at initial screen mount, which
        can be auto-focused before its data finishes loading) or that gets
        repopulated while it's already focused (a change elsewhere doesn't
        blur/refocus it) would otherwise stay stuck un-highlighted. Callers
        that repopulate a list's content should call this afterward."""
        if self.has_focus and self.index is None and len(self) > 0:
            self.index = 0


class _FocusHighlightOptionListMixin:
    """Shared by OptionList and SelectionList — both use `.highlighted`
    (SelectionList subclasses OptionList), not ListView's `.index`."""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        # OptionList.__init__ auto-highlights the first option immediately
        # when constructed with initial content (its own long-standing
        # default — Textual's own source even flags it with a "do we
        # always want this?" TODO), independent of focus. Undo that so
        # "no highlight until focused" holds regardless of whether a list
        # was built with content up front (e.g. level_list) or populated
        # later via add_option (e.g. bean_list).
        if not self.has_focus:
            self.highlighted = None

    def watch_has_focus(self, value: bool) -> None:
        super().watch_has_focus(value)
        if value:
            self.sync_focus_highlight()
        else:
            self.highlighted = None

    def sync_focus_highlight(self) -> None:
        # See FocusHighlightListView.sync_focus_highlight.
        if self.has_focus and self.highlighted is None and self.option_count > 0:
            self.highlighted = 0


class FocusHighlightOptionList(_FocusHighlightOptionListMixin, OptionList):
    pass


class FocusHighlightSelectionList(_FocusHighlightOptionListMixin, SelectionList):
    pass
