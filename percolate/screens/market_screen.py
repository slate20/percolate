"""Market: buying on one side, selling on the other.

A plain utility screen on purpose (see percolate.tcss's header comment) — no
ambient art or tint here, that "zen" budget belongs to the Farm and Roast
screens. Four lists, split by transaction direction rather than stacked in
one column: Buy Seeds / Buy Ingredients on the left, Sell Raw Beans / Sell
Roasted Products on the right. Tab moves focus between lists; Enter
(ListView's default select) acts on the highlighted row — buy or sell one
unit. Upgrades live as contextual modals on the Farm and Roast screens now,
not here — they're a different kind of purchase (permanent perks, not
day-to-day trading).
"""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Header, Label, ListItem, ListView, Static

from percolate.focus_widgets import FocusHighlightListView
from percolate.widgets import NAV_HINT


class MarketScreen(Screen):
    # See FarmScreen.TITLE (farm_screen.py).
    TITLE = "Market"

    def compose(self) -> ComposeResult:
        yield Header()
        # Unlike Farm's bespoke arrow-key cursor, Market's four lists rely on
        # Textual's default Tab-cycling focus, which isn't obvious to a
        # non-dev player — see playtest_notes.md. Surfacing it here instead
        # of relying on discovery; a full bespoke nav pass (matching Farm's
        # model) is a bigger follow-up, noted in playtest_notes.md.
        yield Static(
            "(tab) switch between lists   (shift+tab) previous", classes="section-hint"
        )
        with Horizontal(id="market_columns"):
            with Vertical(id="buy_column"):
                yield Label("Buy Seeds  (enter to buy)")
                yield FocusHighlightListView(id="buy_seeds")
                yield Label("Buy Ingredients  (enter to buy)")
                yield FocusHighlightListView(id="buy_ingredients")
            with Vertical(id="sell_column"):
                yield Label("Sell Raw Beans  (enter to sell)")
                yield FocusHighlightListView(id="sell_beans")
                yield Label("Sell Roasted Products  (enter to sell)")
                yield FocusHighlightListView(id="sell_products")
        yield Static(NAV_HINT, classes="nav-hint")

    async def on_mount(self) -> None:
        self._buy_seed_ids: list[str] = []
        self._buy_ingredient_ids: list[str] = []
        self._sell_bean_ids: list[str] = []
        await self.refresh_market()

    async def on_screen_resume(self) -> None:
        await self.refresh_market()

    async def refresh_market(self) -> None:
        farm = self.app.farm
        beans = self.app.beans
        ingredients = self.app.ingredients

        buy_seeds = self.query_one("#buy_seeds", ListView)
        buy_seeds_index = buy_seeds.index
        await buy_seeds.clear()
        self._buy_seed_ids = list(beans.keys())
        await buy_seeds.extend(
            ListItem(
                Label(
                    f"{beans[bean_id].name} (own {farm.seed_inventory.get(bean_id, 0)}) "
                    f"— buy for {beans[bean_id].seed_cost}g"
                )
            )
            for bean_id in self._buy_seed_ids
        )
        self._restore_index(buy_seeds, buy_seeds_index, len(self._buy_seed_ids))

        buy_ingredients = self.query_one("#buy_ingredients", ListView)
        buy_ingredients_index = buy_ingredients.index
        await buy_ingredients.clear()
        self._buy_ingredient_ids = list(ingredients.keys())
        await buy_ingredients.extend(
            ListItem(
                Label(
                    f"{ingredients[ingredient_id].name} "
                    f"(own {farm.ingredient_inventory.get(ingredient_id, 0)}) "
                    f"— buy for {ingredients[ingredient_id].cost}g"
                )
            )
            for ingredient_id in self._buy_ingredient_ids
        )
        self._restore_index(
            buy_ingredients, buy_ingredients_index, len(self._buy_ingredient_ids)
        )

        sell_beans = self.query_one("#sell_beans", ListView)
        sell_beans_index = sell_beans.index
        await sell_beans.clear()
        self._sell_bean_ids = [
            b_id for b_id, count in farm.raw_bean_inventory.items() if count > 0
        ]
        if self._sell_bean_ids:
            await sell_beans.extend(
                ListItem(
                    Label(
                        f"{beans[bean_id].name} x{farm.raw_bean_inventory[bean_id]} "
                        f"— sell for {beans[bean_id].raw_sell_value}g each"
                    )
                )
                for bean_id in self._sell_bean_ids
            )
        else:
            await sell_beans.append(ListItem(Label("— none —")))
        self._restore_index(
            sell_beans, sell_beans_index, max(1, len(self._sell_bean_ids))
        )

        sell_products = self.query_one("#sell_products", ListView)
        sell_products_index = sell_products.index
        await sell_products.clear()
        if farm.roasted_inventory:
            await sell_products.extend(
                ListItem(Label(f"{product.name} — sell for {product.value}g"))
                for product in farm.roasted_inventory
            )
        else:
            await sell_products.append(ListItem(Label("— none —")))
        self._restore_index(
            sell_products, sell_products_index, max(1, len(farm.roasted_inventory))
        )

    def _restore_index(
        self, list_view: ListView, index: int | None, count: int
    ) -> None:
        # ListView.clear() always resets .index to None, dropping the
        # highlight until the player nudges an arrow key — see
        # playtest_notes.md. refresh_market() rebuilds every list on every
        # buy/sell, so without this the highlight would vanish on each
        # transaction. Mirrors the pattern UpgradeModal.refresh_upgrades
        # already uses for its own ListView.
        #
        # This must run after `await list_view.clear()` / `await
        # list_view.extend(...)` actually complete: those return
        # AwaitRemove/AwaitMount, and setting .index before they're awaited
        # reads/writes against a node list that hasn't finished settling —
        # .index ends up looking set while Textual's own highlighting logic
        # silently skips painting it, so the highlight still appears to
        # vanish. `count` is the already-known Python-side length rather
        # than len(list_view), which is equivalent once awaited but cheaper.
        #
        # Clamped rather than dropped when out of range: selling the last
        # unit of the currently-highlighted bean removes its row entirely,
        # shrinking the list below the old index — the highlight should
        # land on the new last row instead of disappearing outright.
        if index is None or count == 0:
            # Covers a list that's already focused (e.g. the very first
            # list at screen mount) but had nothing highlighted going into
            # this rebuild — see FocusHighlightListView.sync_focus_highlight.
            list_view.sync_focus_highlight()
            return
        list_view.index = min(index, count - 1)

    async def on_list_view_selected(self, event: ListView.Selected) -> None:
        farm = self.app.farm
        list_id = event.list_view.id

        if list_id == "buy_seeds" and self._buy_seed_ids:
            bean_id = self._buy_seed_ids[event.list_view.index]
            bean = self.app.beans[bean_id]
            try:
                farm.buy_seed(bean, 1)
                farm.save_to_disk()
                self.notify(f"Bought {bean.name} seed for {bean.seed_cost}g")
            except ValueError as exc:
                self.notify(str(exc), severity="error")

        elif list_id == "buy_ingredients" and self._buy_ingredient_ids:
            ingredient_id = self._buy_ingredient_ids[event.list_view.index]
            ingredient = self.app.ingredients[ingredient_id]
            try:
                farm.buy_ingredient(ingredient, 1)
                farm.save_to_disk()
                self.notify(f"Bought {ingredient.name} for {ingredient.cost}g")
            except ValueError as exc:
                self.notify(str(exc), severity="error")

        elif list_id == "sell_beans" and self._sell_bean_ids:
            bean_id = self._sell_bean_ids[event.list_view.index]
            bean = self.app.beans[bean_id]
            try:
                farm.sell_raw_bean(bean, 1)
                farm.save_to_disk()
                self.notify(f"Sold {bean.name} for {bean.raw_sell_value}g")
            except ValueError as exc:
                self.notify(str(exc), severity="error")

        elif list_id == "sell_products" and farm.roasted_inventory:
            index = event.list_view.index
            if index < len(farm.roasted_inventory):
                product = farm.sell_product(index)
                farm.save_to_disk()
                self.notify(f"Sold {product.name} for {product.value}g")

        await self.refresh_market()
        self.app.update_subtitle()
