"""Contextual upgrade shop, opened as a modal from the screen it affects
(Farm Upgrades from FarmScreen, Roaster Upgrades from RoastScreen) rather
than living on its own screen — each caller only ever wants the subset of
data/upgrades.json relevant to it.
"""

from __future__ import annotations

from typing import ClassVar

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Label, ListItem, ListView

from percolate.focus_widgets import FocusHighlightListView


def _describe_tier(tier_data: dict) -> str:
    if "plots_added" in tier_data:
        return f"+{tier_data['plots_added']} plots"
    if "growth_speed_bonus" in tier_data:
        return f"+{int(tier_data['growth_speed_bonus'] * 100)}% growth speed"
    if "slots_added" in tier_data:
        return f"+{tier_data['slots_added']} roaster slot"
    if "roast_speed_bonus" in tier_data:
        return f"+{int(tier_data['roast_speed_bonus'] * 100)}% roast speed"
    if "max_ingredients" in tier_data:
        return f"up to {tier_data['max_ingredients']} flavor(s) per roast"
    return ""


class UpgradeModal(ModalScreen[bool]):
    """Dismisses with True if a purchase was made, so the caller knows
    whether to refresh state an upgrade might affect (e.g. plot count)."""

    BINDINGS: ClassVar[list[tuple[str, str, str]]] = [("escape", "cancel", "Close")]

    def __init__(self, title: str, upgrade_ids: list[str]) -> None:
        super().__init__()
        self._title = title
        self._upgrade_ids = upgrade_ids
        self._purchased = False

    def compose(self) -> ComposeResult:
        with Vertical(id="picker"):
            # A ModalScreen has no app Header of its own, so the gold
            # readout that's normally in the Header's subtitle (see
            # FarmScreen.TITLE) needs its own header-adjacent element here —
            # upgrades are the one place a player spends gold without the
            # main Header visible to confirm they can afford it.
            with Horizontal(id="modal_header"):
                yield Label(f"{self._title}  (esc to close)", id="modal_title")
                yield Label("", id="modal_gold")
            yield FocusHighlightListView(id="upgrade_list")

    async def on_mount(self) -> None:
        await self.refresh_upgrades()
        self._update_gold()

    def _update_gold(self) -> None:
        self.query_one("#modal_gold", Label).update(f"{self.app.farm.gold}g")

    async def refresh_upgrades(self) -> None:
        farm = self.app.farm
        upgrades_data = self.app.upgrades_data

        list_view = self.query_one("#upgrade_list", ListView)
        selected = list_view.index
        await list_view.clear()

        items = []
        for upgrade_id in self._upgrade_ids:
            upgrade = upgrades_data[upgrade_id]
            tiers = upgrade["tiers"]
            current_tier = farm.upgrade_tier(upgrade_id)
            if current_tier >= len(tiers):
                text = f"{upgrade['name']} — MAXED (tier {current_tier})"
            else:
                next_tier = tiers[current_tier]
                text = (
                    f"{upgrade['name']} (tier {current_tier}) — "
                    f"next: {_describe_tier(next_tier)} for {next_tier['cost']}g"
                )
            items.append(ListItem(Label(text)))
        await list_view.extend(items)

        # See MarketScreen._restore_index (market_screen.py) for why this
        # must run after the clear/extend are awaited, and why it's clamped
        # rather than dropped when a purchase changes the option count.
        if selected is not None and items:
            list_view.index = min(selected, len(items) - 1)
        else:
            list_view.sync_focus_highlight()

    async def on_list_view_selected(self, event: ListView.Selected) -> None:
        farm = self.app.farm
        upgrades_data = self.app.upgrades_data

        upgrade_id = self._upgrade_ids[event.list_view.index]
        upgrade = upgrades_data[upgrade_id]
        tiers = upgrade["tiers"]
        current_tier = farm.upgrade_tier(upgrade_id)

        if current_tier >= len(tiers):
            self.notify(f"{upgrade['name']} is already maxed.", severity="warning")
            return

        next_tier = tiers[current_tier]
        try:
            farm.apply_upgrade(upgrade_id, next_tier["cost"])
        except ValueError as exc:
            self.notify(str(exc), severity="error")
            return

        if upgrade_id == "plot_expansion":
            farm.expand_plots(next_tier["plots_added"])

        farm.save_to_disk()
        self._purchased = True
        self.notify(f"Purchased {upgrade['name']} tier {current_tier + 1}")
        await self.refresh_upgrades()
        self._update_gold()

    def action_cancel(self) -> None:
        self.dismiss(self._purchased)
