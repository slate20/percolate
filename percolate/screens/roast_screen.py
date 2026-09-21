"""Roastery: persistent recipe builder + ambient roaster art + recipe log.

Sandboxed with a curated bonus overlay (see overview.md §3.C / models/roast.py):
any bean + ingredients + roast level is valid; a matching curated recipe just
adds a name override and value bonus on top.

Three-column layout, not a copy of the Farm screen's plot grid:
- Left: a persistent builder menu (bean / flavor / roast level), always
  visible rather than a modal chain — picks are made ahead of starting a roast.
- Center: the ambient "zen" element — real ASCII roaster art
  (data/roast_stages.json) per active slot, shifting green -> yellow -> brown
  -> dark -> ready with rising steam as the batch progresses (overview.md §4's
  "roasting as a visual set piece"). Roaster slots run larger than plots since
  there are always far fewer of them.
- Right: the accumulated recipe log — curated recipes the player has actually
  discovered are revealed; the rest stay "???" to preserve the discovery
  moment described in overview.md §3.C.
"""

from __future__ import annotations

import math
import textwrap
import time
from typing import ClassVar

from textual import events
from textual.app import ComposeResult
from textual.containers import Grid, Horizontal, Vertical, VerticalScroll
from textual.screen import Screen
from textual.widgets import Button, Header, Label, OptionList, SelectionList, Static
from textual.widgets.option_list import Option
from textual.widgets.selection_list import Selection

from percolate.config import UI_TICK_SECONDS
from percolate.focus_widgets import (
    FocusHighlightOptionList,
    FocusHighlightSelectionList,
)
from percolate.models.roast import DEFAULT_ROAST_DURATION, resolve_roast
from percolate.screens.upgrade_modal import UpgradeModal
from percolate.widgets import NAV_HINT, apply_time_of_day, format_remaining

ROAST_LEVELS = [("light", "Light"), ("medium", "Medium"), ("dark", "Dark")]


def _roast_state(progress: float, is_ready: bool) -> str:
    if is_ready:
        return "ready"
    if progress < 0.25:
        return "green"
    if progress < 0.5:
        return "yellow"
    if progress < 0.75:
        return "brown"
    return "dark"


class RoastCell(Static):
    """One roaster slot in the center field — click when READY to collect."""

    def __init__(self, index: int, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.index = index

    def on_click(self) -> None:
        screen = self.screen
        if isinstance(screen, RoastScreen):
            screen.collect_slot(self.index)


class RoastScreen(Screen):
    # Must match .roast-cell in percolate.tcss: card width (33) minus its
    # 1-column border on each side.
    _CARD_TEXT_WIDTH = 31

    # See FarmScreen.TITLE.
    TITLE = "Roasting"

    BINDINGS: ClassVar[list[tuple[str, str, str]]] = [
        ("s", "start_roast", "Start Roast"),
        ("c", "collect_ready", "Collect"),
        ("u", "show_upgrades", "Upgrades"),
        ("escape", "show_farm", "Farm"),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static("(u) Upgrades", id="tint_bar", classes="tint-bar")
        with Horizontal(id="roast_layout"):
            with Vertical(id="builder_panel"):
                # Same reasoning as MarketScreen's hint (see market_screen.py):
                # the builder panel's 4 fields rely on Textual's default
                # Tab-cycling focus, which isn't obvious to a non-dev player.
                yield Static(
                    "(tab) next field   (shift+tab) previous", classes="section-hint"
                )
                yield Label("Bean", classes="builder-heading")
                yield FocusHighlightOptionList(id="bean_list")
                yield Label("Flavor", id="flavor_heading", classes="builder-heading")
                yield FocusHighlightSelectionList(id="flavor_list")
                yield Label("Roast Level", classes="builder-heading")
                yield FocusHighlightOptionList(
                    *[Option(label, id=opt_id) for opt_id, label in ROAST_LEVELS],
                    id="level_list",
                )
                yield Label("", id="builder_status", classes="builder-status")
                yield Button("Start Roast (s)", id="start_button", variant="success")
            with Vertical(id="center_panel"):
                yield Grid(id="roaster_field")
            with Vertical(id="recipe_panel"):
                yield Label("Recipes", classes="builder-heading")
                yield VerticalScroll(id="recipe_list")
        yield Static(NAV_HINT, classes="nav-hint")

    def on_mount(self) -> None:
        self._cells: list[RoastCell] = []
        self._last_state: list[str | None] = []
        self._selected_bean_id: str | None = None
        self._selected_level: str | None = "medium"

        self._build_field()
        self.refresh_builder()
        self.refresh_batches()
        self._build_recipe_list()
        apply_time_of_day(self.query_one("#tint_bar", Static))
        self.set_interval(UI_TICK_SECONDS, self.tick)
        self.set_focus(self.query_one("#bean_list", OptionList))

    def on_screen_resume(self) -> None:
        self.refresh_builder()
        self.refresh_batches()

    def tick(self) -> None:
        self.refresh_batches()
        apply_time_of_day(self.query_one("#tint_bar", Static))

    def on_descendant_focus(self, event: events.DescendantFocus) -> None:
        # Bean and Roast Level aren't plain browsing lists — their
        # highlight is the only visual indicator of a persistent choice
        # (which bean/level the next roast uses), so on focus they should
        # show *that* selection rather than the generic "first item"
        # default the FocusHighlightOptionList mixin applies to every other
        # list. See playtest_notes.md.
        if event.widget.id in ("bean_list", "level_list"):
            self._sync_selection_highlight(event.widget.id)

    # --- Builder (left panel) -------------------------------------------

    def _sync_selection_highlight(self, widget_id: str) -> None:
        if widget_id == "bean_list":
            bean_list = self.query_one("#bean_list", OptionList)
            owned_bean_ids = [
                b_id
                for b_id, count in self.app.farm.raw_bean_inventory.items()
                if count > 0
            ]
            if self._selected_bean_id in owned_bean_ids:
                bean_list.highlighted = owned_bean_ids.index(self._selected_bean_id)
        elif widget_id == "level_list":
            level_list = self.query_one("#level_list", OptionList)
            level_ids = [opt_id for opt_id, _ in ROAST_LEVELS]
            if self._selected_level in level_ids:
                level_list.highlighted = level_ids.index(self._selected_level)

    def refresh_builder(self) -> None:
        farm = self.app.farm
        beans = self.app.beans
        ingredients = self.app.ingredients

        bean_list = self.query_one("#bean_list", OptionList)
        bean_list.clear_options()
        owned_bean_ids = [
            b_id for b_id, count in farm.raw_bean_inventory.items() if count > 0
        ]
        for bean_id in owned_bean_ids:
            count = farm.raw_bean_inventory[bean_id]
            bean_list.add_option(
                Option(f"{beans[bean_id].name} (own {count})", id=bean_id)
            )
        if self._selected_bean_id not in owned_bean_ids:
            self._selected_bean_id = owned_bean_ids[0] if owned_bean_ids else None
        # Only reassert the highlight while focused — clear_options() resets
        # it to None regardless, and if bean_list isn't focused it should
        # stay cleared (see FocusHighlightOptionList / on_descendant_focus)
        # rather than being force-shown independent of Tab focus.
        if bean_list.has_focus:
            self._sync_selection_highlight("bean_list")

        max_flavors = farm.max_ingredients(self.app.upgrades_data)
        flavor_heading = self.query_one("#flavor_heading", Label)
        if max_flavors == 0:
            flavor_heading.update("Flavor (need Infuser — u)")
        else:
            flavor_heading.update(f"Flavor (space/enter to toggle, max {max_flavors})")

        flavor_list = self.query_one("#flavor_list", SelectionList)
        flavor_list.clear_options()
        for ingredient in ingredients.values():
            have = farm.ingredient_inventory.get(ingredient.id, 0)
            if have > 0:
                flavor_list.add_option(
                    Selection(f"{ingredient.name} (own {have})", ingredient.id)
                )
        # Plain browsing list (no persistent-choice concept like bean/level
        # above) — the generic first-item default is fine here.
        flavor_list.sync_focus_highlight()

        self._update_status()

    def on_selection_list_selection_toggled(
        self, event: SelectionList.SelectionToggled
    ) -> None:
        flavor_list = event.selection_list
        max_flavors = self.app.farm.max_ingredients(self.app.upgrades_data)
        if (
            event.selection.value in flavor_list.selected
            and len(flavor_list.selected) > max_flavors
        ):
            flavor_list.deselect(event.selection.value)
            if max_flavors == 0:
                self.notify("Buy an Infuser (u) to add flavors.", severity="warning")
            else:
                self.notify(
                    f"Infuser only allows {max_flavors} flavor(s) per roast.",
                    severity="warning",
                )

    def _current_ingredients(self) -> list:
        flavor_list = self.query_one("#flavor_list", SelectionList)
        return [self.app.ingredients[i] for i in flavor_list.selected]

    def _update_status(self) -> None:
        status = self.query_one("#builder_status", Label)
        if self._selected_bean_id is None:
            status.update("Harvest beans on the Farm screen first.")
            return
        if self._selected_level is None:
            status.update("Choose a roast level.")
            return

        bean = self.app.beans[self._selected_bean_id]
        ingredients = self._current_ingredients()
        preview = resolve_roast(
            bean, ingredients, self._selected_level, self.app.recipes
        )
        flavor = ", ".join(i.name for i in ingredients) or "plain"
        discovered = "✓ curated" if preview.recipe_id else ""
        status.update(
            f"{bean.name}, {self._selected_level}, {flavor}\n"
            f"-> {preview.name}: ~{preview.value}g {discovered}"
        )

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        if event.option_list.id == "bean_list":
            self._selected_bean_id = event.option.id
        elif event.option_list.id == "level_list":
            self._selected_level = event.option.id
        self._update_status()

    def on_selection_list_selected_changed(
        self, event: SelectionList.SelectedChanged
    ) -> None:
        self._update_status()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "start_button":
            self.action_start_roast()

    def action_start_roast(self) -> None:
        farm = self.app.farm
        if self._selected_bean_id is None:
            self.notify("Choose a bean first.", severity="warning")
            return
        if self._selected_level is None:
            self.notify("Choose a roast level first.", severity="warning")
            return
        capacity = farm.max_roast_slots(self.app.upgrades_data)
        if capacity == 0:
            self.notify(
                "No roaster yet — buy one from Upgrades (u).", severity="warning"
            )
            return
        if len(farm.roast_batches) >= capacity:
            self.notify("All roaster slots are busy.", severity="warning")
            return

        bean = self.app.beans[self._selected_bean_id]
        ingredients = self._current_ingredients()
        bonus = farm.roast_speed_bonus(self.app.upgrades_data)
        duration = DEFAULT_ROAST_DURATION * (1 - bonus)
        try:
            farm.start_roast(
                bean, ingredients, self._selected_level, duration, time.time()
            )
            farm.save_to_disk()
            self.notify(f"Roasting {bean.name}...")
        except ValueError as exc:
            self.notify(str(exc), severity="error")
            return

        self.refresh_builder()
        self.refresh_batches()

    # --- Roaster field (center panel) ------------------------------------

    def _capacity(self) -> int:
        return self.app.farm.max_roast_slots(self.app.upgrades_data)

    def _build_field(self) -> None:
        # Same reasoning as FarmScreen._build_field: a rebuild recreates every
        # RoastCell from scratch, so every cell here is freshly mounted and
        # gets painted immediately with no fade, rather than carrying over a
        # stale _last_state that would wrongly read as "changed".
        grid = self.query_one("#roaster_field", Grid)
        grid.remove_children()

        count = self._capacity()
        self._columns = min(max(1, math.ceil(math.sqrt(count)) if count else 1), 3)
        grid.styles.grid_size_columns = self._columns

        if count == 0:
            self._cells = []
            self._last_state = []
            grid.mount(
                Static("No roaster yet.\n\n(u) Upgrades to build one.", id="no_roaster")
            )
            return

        self._cells = [RoastCell(i, "", classes="roast-cell") for i in range(count)]
        self._last_state = [None] * count
        grid.mount(*self._cells)
        for index in range(count):
            self._paint_cell(index, animate=False)

    def _cell_content(self, index: int) -> tuple[str, str]:
        farm = self.app.farm
        beans = self.app.beans
        ingredients = self.app.ingredients
        roast_stages = self.app.roast_stages
        now = time.time()

        if index >= len(farm.roast_batches):
            state = "idle"
            header = f"Slot {index + 1}"
            footer = "— empty —"
        else:
            batch = farm.roast_batches[index]
            bean = beans[batch.bean_id]
            batch_ingredients = [ingredients[i] for i in batch.ingredient_ids]
            # Same resolve_roast preview the builder panel uses (see
            # _update_status) — shows the curated name if this combo matches
            # a recipe, otherwise the generated "Bean Level Flavor" name, so
            # a slot's label always identifies exactly what's roasting.
            preview = resolve_roast(
                bean, batch_ingredients, batch.roast_level, self.app.recipes
            )
            progress = batch.progress(now)
            is_ready = batch.is_ready(now)
            state = _roast_state(progress, is_ready)
            header = self._wrap_header(f"Slot {index + 1}: {preview.name}")
            if is_ready:
                footer = "READY — click or (c)"
            else:
                remaining = batch.process.duration - batch.process.elapsed(now)
                footer = f"{format_remaining(remaining)} remaining"

        frames = roast_stages[state]
        frame = frames[int(now // UI_TICK_SECONDS) % len(frames)]
        # Blank line between header and art: breathing room so a wrapped
        # two-line name doesn't butt straight up against the roaster art.
        text = header + "\n\n" + "\n".join(frame) + "\n" + footer
        return text, state

    def _wrap_header(self, text: str) -> str:
        """Wrap a slot header to the card's text width instead of letting a
        long roast name (bean + level + flavors, or a curated recipe name)
        silently overflow — a plain Static doesn't reflow text on its own,
        it just clips whatever doesn't fit the widget's width. Capped at 2
        lines to match the card's art budget; recipes/beans/ingredients are
        content-extensible (see CLAUDE.md), so a future combo could in
        theory exceed that, hence the ellipsis fallback.
        """
        lines = textwrap.wrap(text, width=self._CARD_TEXT_WIDTH) or [text]
        if len(lines) > 2:
            lines = lines[:2]
            lines[-1] = lines[-1][: self._CARD_TEXT_WIDTH - 1].rstrip() + "…"
        return "\n".join(lines)

    def _paint_cell(self, index: int, animate: bool) -> None:
        cell = self._cells[index]
        text, state = self._cell_content(index)
        cell.update(text)
        cell.set_classes(f"roast-cell roast-{state}")

        changed = (
            self._last_state[index] is not None and self._last_state[index] != state
        )
        if animate and changed:
            cell.styles.opacity = 0.0
            cell.styles.animate("opacity", value=1.0, duration=1.2)
        else:
            cell.styles.opacity = 1.0
        self._last_state[index] = state

    def refresh_batches(self) -> None:
        if len(self._cells) != self._capacity():
            self._build_field()

        for index in range(len(self._cells)):
            self._paint_cell(index, animate=True)

        self._build_recipe_list()

    def collect_slot(self, index: int) -> None:
        farm = self.app.farm
        if index >= len(farm.roast_batches):
            return
        now = time.time()
        batch = farm.roast_batches[index]
        if not batch.is_ready(now):
            remaining = batch.process.duration - batch.process.elapsed(now)
            self.notify(f"Still roasting — {format_remaining(remaining)} left")
            return

        product = farm.collect_roast(
            index, self.app.beans, self.app.ingredients, self.app.recipes, now
        )
        farm.save_to_disk()
        self.notify(f"Collected: {product.name} ({product.value}g)")
        self.refresh_batches()

    def action_collect_ready(self) -> None:
        now = time.time()
        for index, batch in enumerate(self.app.farm.roast_batches):
            if batch.is_ready(now):
                self.collect_slot(index)
                return
        self.notify("Nothing ready yet.")

    def action_show_farm(self) -> None:
        self.app.action_show_screen("farm")

    def action_show_upgrades(self) -> None:
        def handle_result(purchased: bool | None) -> None:
            if purchased:
                self.refresh_batches()
                self.refresh_builder()

        self.app.push_screen(
            UpgradeModal(
                "Roaster Upgrades", ["roaster_slot", "roaster_speed", "infuser"]
            ),
            handle_result,
        )

    # --- Recipe log (right panel) -----------------------------------------

    def _build_recipe_list(self) -> None:
        recipes = self.app.recipes
        discovered = self.app.farm.discovered_recipes
        container = self.query_one("#recipe_list", VerticalScroll)
        container.remove_children()

        container.mount(Label(f"Discovered {len(discovered)}/{len(recipes)}"))
        for recipe in recipes.values():
            if recipe.id in discovered:
                bean_name = self.app.beans[recipe.bean].name
                flavor = ", ".join(
                    self.app.ingredients[i].name for i in recipe.ingredients
                )
                flavor = flavor or "plain"
                text = (
                    f"[gold]{recipe.name}[/]\n"
                    f"{bean_name} · {recipe.roast_level} · {flavor}\n"
                    f"x{recipe.bonus_multiplier}"
                )
            else:
                text = "[grey50]??? — undiscovered[/]"
            container.mount(Static(text, classes="recipe-entry"))
