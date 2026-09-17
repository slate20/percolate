"""Contextual upgrade shop, opened as a modal from the screen it affects
(Farm Upgrades from FarmScreen, Roaster Upgrades from RoastScreen) rather
than living on its own screen — each caller only ever wants the subset of
data/upgrades.json relevant to it.
"""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Label, ListItem, ListView


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

    BINDINGS = [("escape", "cancel", "Close")]

    def __init__(self, title: str, upgrade_ids: list[str]) -> None:
        super().__init__()
        self._title = title
        self._upgrade_ids = upgrade_ids
        self._purchased = False

    def compose(self) -> ComposeResult:
        with Vertical(id="picker"):
            yield Label(f"{self._title}  (esc to close)")
            yield ListView(id="upgrade_list")

    def on_mount(self) -> None:
        self.refresh_upgrades()

    def refresh_upgrades(self) -> None:
        farm = self.app.farm
        upgrades_data = self.app.upgrades_data

        list_view = self.query_one("#upgrade_list", ListView)
        selected = list_view.index
        list_view.clear()

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
            list_view.append(ListItem(Label(text)))

        if selected is not None and selected < len(list_view):
            list_view.index = selected

    def on_list_view_selected(self, event: ListView.Selected) -> None:
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
        self.refresh_upgrades()

    def action_cancel(self) -> None:
        self.dismiss(self._purchased)
