"""2D ASCII field: plot planting/harvesting.

Implements overview.md §4 (Aesthetic & Feel Guidelines) and the "2D ASCII
Field" from the screen routing map — plots are laid out spatially in a
grid, not as a linear list, with arrow-key cursor navigation.
"""

from __future__ import annotations

import time
from typing import ClassVar

from textual.app import ComposeResult
from textual.containers import Grid, ScrollableContainer, Vertical
from textual.screen import ModalScreen, Screen
from textual.widgets import Header, Label, OptionList, Static
from textual.widgets.option_list import Option

from percolate.backdrop_compositor import composite_backdrop, resolve_tiers
from percolate.config import UI_TICK_SECONDS
from percolate.focus_widgets import FocusHighlightOptionList
from percolate.screens.upgrade_modal import UpgradeModal
from percolate.widgets import NAV_HINT, apply_time_of_day, format_remaining


class BeanPickerScreen(ModalScreen[str | None]):
    """Modal: pick a bean strain (from owned seeds) to plant in the selected plot."""

    BINDINGS: ClassVar[list[tuple[str, str, str]]] = [("escape", "cancel", "Cancel")]

    def __init__(self, options: list[tuple[str, str]]) -> None:
        super().__init__()
        self._options = options

    def compose(self) -> ComposeResult:
        with Vertical(id="picker"):
            yield Label("Choose a seed to plant  (esc to cancel)")
            yield FocusHighlightOptionList(
                *[Option(label, id=opt_id) for opt_id, label in self._options]
            )

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        self.dismiss(event.option.id)

    def action_cancel(self) -> None:
        self.dismiss(None)


class PlotCell(Static):
    """One spatial cell in the field grid."""


class Backdrop(Static):
    """The non-interactive farm landscape scene behind the plot grid."""


class FarmScreen(Screen):
    # Must match .plot-cell / #field in percolate.tcss: cell width, the
    # horizontal grid-gutter, and #field's left+right padding respectively.
    # Used to work out how many cards fit per row as the window resizes.
    _CELL_WIDTH = 21
    _CELL_GUTTER = 2
    _FIELD_SIDE_PADDING = 4
    # Capped so the max plot count (8, via plot_expansion's tiers) always
    # lays out as a symmetrical 4x2 rather than however many columns happen
    # to fit a wide terminal (e.g. all 8 in one row).
    _MAX_COLUMNS = 4

    # Header shows "Farm — {gold}g" instead of just the app's "Percolate"
    # title — Screen.TITLE overrides the app title in Header, while leaving
    # sub_title unset keeps inheriting the gold readout from PercolateApp.
    TITLE = "Farm"

    BINDINGS: ClassVar[list[tuple[str, str, str]]] = [
        ("up", "move_up", "Up"),
        ("down", "move_down", "Down"),
        ("left", "move_left", "Left"),
        ("right", "move_right", "Right"),
        ("enter", "interact", "Plant / Harvest"),
        ("u", "show_upgrades", "Upgrades"),
        ("o", "toggle_outline", "Toggle plot outline"),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        with ScrollableContainer(id="backdrop_wrap", can_focus=False):
            yield Backdrop(id="backdrop")
        yield Static("(u) Upgrades", id="tint_bar", classes="tint-bar")
        yield Grid(id="field")
        yield Static(NAV_HINT, classes="nav-hint")

    def on_mount(self) -> None:
        self._cells: list[PlotCell] = []
        self._last_stage: list[str | None] = []
        self._columns = 1
        self._cursor = 0
        self._hide_outline = False
        self._build_field()
        self.refresh_plots()
        self._render_backdrop()
        self.call_after_refresh(self._center_on_house)
        apply_time_of_day(self.query_one("#tint_bar", Static))
        self.set_interval(UI_TICK_SECONDS, self.tick)

    def on_screen_resume(self) -> None:
        self.refresh_plots()
        self._sync_field_columns()
        self._render_backdrop()
        self.call_after_refresh(self._center_on_house)

    def tick(self) -> None:
        self.refresh_plots()
        self._sync_field_columns()
        apply_time_of_day(self.query_one("#tint_bar", Static))

    def _render_backdrop(self) -> None:
        tier_by_slot = resolve_tiers(
            self.app.farmhouse_data, self.app.farm, self.app.upgrades_data
        )
        composited = composite_backdrop(self.app.farmhouse_data, tier_by_slot)
        self.query_one("#backdrop", Backdrop).update(composited)

    def _center_on_house(self) -> None:
        # Default view centers on the house slot, per docs/north_star.md —
        # a no-op if "house" isn't in the current farmhouse_data.
        house = next(
            (s for s in self.app.farmhouse_data["slots"] if s["id"] == "house"), None
        )
        if house is None:
            return
        container = self.query_one("#backdrop_wrap", ScrollableContainer)
        target_x = house["col"] + house["width"] / 2 - container.size.width / 2
        target_y = house["row"] + house["height"] / 2 - container.size.height / 2
        container.scroll_to(x=max(0, target_x), y=max(0, target_y), animate=False)

    def _build_field(self) -> None:
        # Rebuilds recreate every PlotCell widget from scratch (grid.remove_children
        # + fresh instances), even for plots that already existed. So every cell
        # here is a just-mounted widget regardless of what state it previously
        # showed — each gets painted immediately below, with no fade, rather than
        # carrying over old _last_stage (which would wrongly mark it as "changed"
        # and trigger an animation on a widget that was mounted in this same tick).
        farm = self.app.farm
        grid = self.query_one("#field", Grid)
        grid.remove_children()

        count = len(farm.plots)
        self._columns = self._max_columns(count, self.size.width)
        grid.styles.grid_size_columns = self._columns

        self._cells = [PlotCell("", classes="plot-cell") for _ in range(count)]
        self._last_stage = [None] * count
        if self._cells:
            grid.mount(*self._cells)
            for index in range(count):
                self._paint_cell(index, animate=False)

        self._cursor = min(self._cursor, count - 1) if count else 0
        self._highlight_cursor()

    def _max_columns(self, count: int, available_width: int) -> int:
        """How many cards fit per row at the current window width.

        Cards keep a fixed size (like the roast screen's cards); it's the
        column *count* that adapts, wrapping fewer/more per row as the
        window is resized, capped by how many plots there actually are.
        """
        if count <= 0:
            return 1
        usable = max(0, available_width - self._FIELD_SIDE_PADDING)
        fits = max(
            1,
            (usable + self._CELL_GUTTER) // (self._CELL_WIDTH + self._CELL_GUTTER),
        )
        return max(1, min(count, fits, self._MAX_COLUMNS))

    def _sync_field_columns(self) -> None:
        """Recompute column count on resize (polled on the tick, like
        `_sync_backdrop` — see CLAUDE.md: no dedicated resize-event
        plumbing in this app)."""
        count = len(self._cells)
        if count == 0:
            return
        columns = self._max_columns(count, self.size.width)
        if columns == self._columns:
            return
        self._columns = columns
        self.query_one("#field", Grid).styles.grid_size_columns = columns
        self._cursor = min(self._cursor, count - 1)
        self._highlight_cursor()

    def _highlight_cursor(self) -> None:
        for index, cell in enumerate(self._cells):
            cell.set_class(index == self._cursor, "cursor")

    def _move(self, delta: int, same_row: bool = False) -> None:
        count = len(self._cells)
        if count == 0:
            return
        new_cursor = self._cursor + delta
        if same_row and new_cursor // self._columns != self._cursor // self._columns:
            return
        if not (0 <= new_cursor < count):
            return
        old_cursor = self._cursor
        self._cursor = new_cursor
        # Repaint just the two affected cells (not a full refresh) so the
        # cursored cell's inline "(enter) ..." hint moves immediately,
        # rather than waiting for the next tick. _paint_cell() replaces all
        # classes via set_classes(), so _highlight_cursor() must run after
        # it, not before — otherwise the "cursor" class it sets gets wiped
        # right back off.
        self._paint_cell(old_cursor, animate=False)
        self._paint_cell(self._cursor, animate=False)
        self._highlight_cursor()

    def action_move_up(self) -> None:
        self._move(-self._columns)

    def action_move_down(self) -> None:
        self._move(self._columns)

    def action_move_left(self) -> None:
        self._move(-1, same_row=True)

    def action_move_right(self) -> None:
        self._move(1, same_row=True)

    def _cell_content(self, index: int) -> tuple[str, str]:
        """Return (text, state) for a plot index from current farm state."""
        farm = self.app.farm
        beans = self.app.beans
        plant_stages = self.app.plant_stages
        now = time.time()
        plot = farm.plots[index]

        cursored = index == self._cursor

        if plot.is_empty:
            state = "empty"
            art_stage = "empty"
            header = f"Plot {index + 1}"
            art = plant_stages["empty"]
            footer = "(enter) plant" if cursored else "— empty —"
        else:
            bean = beans[plot.bean_id]
            progress = plot.progress(now)
            stage = bean.stage_for_progress(progress)
            art_stage = stage
            art = plant_stages[stage]
            header = f"Plot {index + 1}: {bean.name}"
            if plot.is_ready(now):
                state = "ready"
                footer = "READY  (enter)" if cursored else "READY"
            else:
                state = "early" if stage in ("seed", "sprout") else "mid"
                remaining = plot.process.duration - plot.process.elapsed(now)
                footer = f"{stage.upper()}  {format_remaining(remaining)}"

        text = header + "\n" + "\n".join(art) + "\n" + footer
        return text, state, art_stage

    def _paint_cell(self, index: int, animate: bool) -> None:
        cell = self._cells[index]
        text, state, art_stage = self._cell_content(index)
        cell.update(text)
        cell.set_classes(f"plot-cell state-{state}")

        # Fades on an actual growth-stage change (seed -> sprout -> growing
        # -> ready), tracked via the fine-grained art stage rather than the
        # coarser `state` color bucket used above — early -> mid used to be
        # the only bucket boundary crossed, so seed -> sprout never faded.
        # Explicitly excluded whenever either side is "empty": planting and
        # harvesting are immediate player actions, not passive growth, and
        # shouldn't get the slow fade (see playtest_notes.md).
        last_stage = self._last_stage[index]
        changed = (
            last_stage is not None
            and last_stage != art_stage
            and last_stage != "empty"
            and art_stage != "empty"
        )
        if animate and changed:
            cell.styles.opacity = 0.0
            cell.styles.animate("opacity", value=1.0, duration=1.2)
        else:
            cell.styles.opacity = 1.0
        self._last_stage[index] = art_stage

    def refresh_plots(self) -> None:
        farm = self.app.farm
        if len(self._cells) != len(farm.plots):
            self._build_field()

        for index in range(len(farm.plots)):
            self._paint_cell(index, animate=True)

        self._highlight_cursor()

    def action_interact(self) -> None:
        farm = self.app.farm
        if not farm.plots:
            return
        index = self._cursor
        now = time.time()
        plot = farm.plots[index]

        if plot.is_empty:
            owned_seeds = [
                (bean_id, f"{self.app.beans[bean_id].name} (own {count})")
                for bean_id, count in farm.seed_inventory.items()
                if count > 0
            ]
            if not owned_seeds:
                self.notify("No seeds — buy some at the Market.", severity="warning")
                return

            def handle_pick(bean_id: str | None, plot_index: int = index) -> None:
                if bean_id is None:
                    return
                bean = self.app.beans[bean_id]
                bonus = farm.growth_speed_bonus(self.app.upgrades_data)
                growth_time = bean.growth_time * (1 - bonus)
                try:
                    farm.plant_bean(
                        plot_index, bean, time.time(), growth_time=growth_time
                    )
                    farm.save_to_disk()
                except ValueError as exc:
                    self.notify(str(exc), severity="error")
                self.refresh_plots()

            self.app.push_screen(BeanPickerScreen(owned_seeds), handle_pick)
        elif plot.is_ready(now):
            farm.harvest_plot(index, now)
            farm.save_to_disk()
            self.refresh_plots()

    def action_show_upgrades(self) -> None:
        def handle_result(purchased: bool | None) -> None:
            if purchased:
                self.refresh_plots()
                self._render_backdrop()

        self.app.push_screen(
            UpgradeModal("Farm Upgrades", ["plot_expansion", "soil_quality"]),
            handle_result,
        )

    def action_toggle_outline(self) -> None:
        # Purely a viewing/screenshot preference (see playtest_notes.md) —
        # the cursor itself still moves and still gates (enter), only the
        # gold border cue is hidden. CSS-only: toggling a class on #field
        # overrides .plot-cell.cursor's border back to plain grey, so
        # _highlight_cursor's own "cursor" class logic doesn't need to
        # change at all.
        self._hide_outline = not self._hide_outline
        self.query_one("#field", Grid).set_class(
            self._hide_outline, "hide-cursor-outline"
        )
        self.notify(
            "Plot outline hidden" if self._hide_outline else "Plot outline shown"
        )
