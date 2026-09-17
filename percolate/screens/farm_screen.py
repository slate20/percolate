"""2D ASCII field: plot planting/harvesting.

Implements overview.md §4 (Aesthetic & Feel Guidelines) and the "2D ASCII
Field" from the screen routing map — plots are laid out spatially in a
grid, not as a linear list, with arrow-key cursor navigation.
"""

from __future__ import annotations

import math
import time

from textual.app import ComposeResult
from textual.containers import Grid, Vertical
from textual.screen import ModalScreen, Screen
from textual.widgets import Header, Label, OptionList, Static
from textual.widgets.option_list import Option

from percolate.config import LARGE_BACKDROP_MIN_HEIGHT, LARGE_BACKDROP_MIN_WIDTH, UI_TICK_SECONDS
from percolate.screens.upgrade_modal import UpgradeModal
from percolate.widgets import NAV_HINT, apply_time_of_day


def _format_remaining(seconds: float) -> str:
    seconds = max(0, int(seconds))
    hours, remainder = divmod(seconds, 3600)
    minutes = remainder // 60
    if hours:
        return f"{hours}h {minutes}m"
    return f"{minutes}m"


class BeanPickerScreen(ModalScreen[str | None]):
    """Modal: pick a bean strain (from owned seeds) to plant in the selected plot."""

    BINDINGS = [("escape", "cancel", "Cancel")]

    def __init__(self, options: list[tuple[str, str]]) -> None:
        super().__init__()
        self._options = options

    def compose(self) -> ComposeResult:
        with Vertical(id="picker"):
            yield Label("Choose a seed to plant  (esc to cancel)")
            yield OptionList(*[Option(label, id=opt_id) for opt_id, label in self._options])

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        self.dismiss(event.option.id)

    def action_cancel(self) -> None:
        self.dismiss(None)


class PlotCell(Static):
    """One spatial cell in the field grid."""


class Backdrop(Static):
    """The non-interactive farm landscape scene behind the plot grid."""


class FarmScreen(Screen):
    BINDINGS = [
        ("up", "move_up", "Up"),
        ("down", "move_down", "Down"),
        ("left", "move_left", "Left"),
        ("right", "move_right", "Right"),
        ("enter", "interact", "Plant / Harvest"),
        ("u", "show_upgrades", "Upgrades"),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        yield Backdrop(id="backdrop")
        yield Static("(u) Upgrades", id="tint_bar", classes="tint-bar")
        yield Grid(id="field")
        yield Static(NAV_HINT, classes="nav-hint")

    def on_mount(self) -> None:
        self._cells: list[PlotCell] = []
        self._last_state: list[str | None] = []
        self._columns = 1
        self._cursor = 0
        self._backdrop_variant: str | None = None
        self._build_field()
        self.refresh_plots()
        self._sync_backdrop()
        apply_time_of_day(self.query_one("#tint_bar", Static))
        self.set_interval(UI_TICK_SECONDS, self.tick)

    def on_screen_resume(self) -> None:
        self.refresh_plots()
        self._sync_backdrop()

    def tick(self) -> None:
        self.refresh_plots()
        self._sync_backdrop()
        apply_time_of_day(self.query_one("#tint_bar", Static))

    def _sync_backdrop(self) -> None:
        width, height = self.size.width, self.size.height
        variant = (
            "large"
            if width >= LARGE_BACKDROP_MIN_WIDTH and height >= LARGE_BACKDROP_MIN_HEIGHT
            else "compact"
        )
        if variant == self._backdrop_variant:
            return
        self._backdrop_variant = variant
        data = self.app.farmhouse_data[variant]
        self.query_one("#backdrop", Backdrop).update("\n".join(data["art"]))

    def _build_field(self) -> None:
        # Rebuilds recreate every PlotCell widget from scratch (grid.remove_children
        # + fresh instances), even for plots that already existed. So every cell
        # here is a just-mounted widget regardless of what state it previously
        # showed — each gets painted immediately below, with no fade, rather than
        # carrying over old _last_state (which would wrongly mark it as "changed"
        # and trigger an animation on a widget that was mounted in this same tick).
        farm = self.app.farm
        grid = self.query_one("#field", Grid)
        grid.remove_children()

        count = len(farm.plots)
        self._columns = min(max(1, math.ceil(math.sqrt(count)) if count else 1), 4)
        grid.styles.grid_size_columns = self._columns

        self._cells = [PlotCell("", classes="plot-cell") for _ in range(count)]
        self._last_state = [None] * count
        if self._cells:
            grid.mount(*self._cells)
            for index in range(count):
                self._paint_cell(index, animate=False)

        self._cursor = min(self._cursor, count - 1) if count else 0
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
        self._highlight_cursor()
        # Repaint just the two affected cells (not a full refresh) so the
        # cursored cell's inline "(enter) ..." hint moves immediately,
        # rather than waiting for the next tick.
        self._paint_cell(old_cursor, animate=False)
        self._paint_cell(self._cursor, animate=False)

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
            header = f"Plot {index + 1}"
            art = plant_stages["empty"]
            footer = "(enter) plant" if cursored else "— empty —"
        else:
            bean = beans[plot.bean_id]
            progress = plot.progress(now)
            stage = bean.stage_for_progress(progress)
            art = plant_stages[stage]
            header = f"Plot {index + 1}: {bean.name}"
            if plot.is_ready(now):
                state = "ready"
                footer = "READY  (enter)" if cursored else "READY"
            else:
                state = "early" if stage in ("seed", "sprout") else "mid"
                remaining = plot.process.duration - plot.process.elapsed(now)
                footer = f"{stage.upper()}  {_format_remaining(remaining)}"

        text = header + "\n" + "\n".join(art) + "\n" + footer
        return text, state

    def _paint_cell(self, index: int, animate: bool) -> None:
        cell = self._cells[index]
        text, state = self._cell_content(index)
        cell.update(text)
        cell.set_classes(f"plot-cell state-{state}")

        changed = self._last_state[index] is not None and self._last_state[index] != state
        if animate and changed:
            cell.styles.opacity = 0.0
            cell.styles.animate("opacity", value=1.0, duration=1.2)
        else:
            cell.styles.opacity = 1.0
        self._last_state[index] = state

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
                    farm.plant_bean(plot_index, bean, time.time(), growth_time=growth_time)
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

        self.app.push_screen(
            UpgradeModal("Farm Upgrades", ["plot_expansion", "soil_quality"]), handle_result
        )
