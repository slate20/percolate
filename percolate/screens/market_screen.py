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

from percolate.widgets import NAV_HINT


class MarketScreen(Screen):
    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal(id="market_columns"):
            with Vertical(id="buy_column"):
                yield Label("Buy Seeds  (enter to buy)")
                yield ListView(id="buy_seeds")
                yield Label("Buy Ingredients  (enter to buy)")
                yield ListView(id="buy_ingredients")
            with Vertical(id="sell_column"):
                yield Label("Sell Raw Beans  (enter to sell)")
                yield ListView(id="sell_beans")
                yield Label("Sell Roasted Products  (enter to sell)")
                yield ListView(id="sell_products")
        yield Static(NAV_HINT, classes="nav-hint")

    def on_mount(self) -> None:
        self._buy_seed_ids: list[str] = []
        self._buy_ingredient_ids: list[str] = []
        self._sell_bean_ids: list[str] = []
        self.refresh_market()

    def on_screen_resume(self) -> None:
        self.refresh_market()

    def refresh_market(self) -> None:
        farm = self.app.farm
        beans = self.app.beans
        ingredients = self.app.ingredients

        buy_seeds = self.query_one("#buy_seeds", ListView)
        buy_seeds.clear()
        self._buy_seed_ids = list(beans.keys())
        for bean_id in self._buy_seed_ids:
            bean = beans[bean_id]
            owned = farm.seed_inventory.get(bean_id, 0)
            buy_seeds.append(
                ListItem(Label(f"{bean.name} (own {owned}) — buy for {bean.seed_cost}g"))
            )

        buy_ingredients = self.query_one("#buy_ingredients", ListView)
        buy_ingredients.clear()
        self._buy_ingredient_ids = list(ingredients.keys())
        for ingredient_id in self._buy_ingredient_ids:
            ingredient = ingredients[ingredient_id]
            owned = farm.ingredient_inventory.get(ingredient_id, 0)
            buy_ingredients.append(
                ListItem(Label(f"{ingredient.name} (own {owned}) — buy for {ingredient.cost}g"))
            )

        sell_beans = self.query_one("#sell_beans", ListView)
        sell_beans.clear()
        self._sell_bean_ids = [b_id for b_id, count in farm.raw_bean_inventory.items() if count > 0]
        for bean_id in self._sell_bean_ids:
            bean = beans[bean_id]
            count = farm.raw_bean_inventory[bean_id]
            sell_beans.append(
                ListItem(Label(f"{bean.name} x{count} — sell for {bean.raw_sell_value}g each"))
            )
        if not self._sell_bean_ids:
            sell_beans.append(ListItem(Label("— none —")))

        sell_products = self.query_one("#sell_products", ListView)
        sell_products.clear()
        for product in farm.roasted_inventory:
            sell_products.append(ListItem(Label(f"{product.name} — sell for {product.value}g")))
        if not farm.roasted_inventory:
            sell_products.append(ListItem(Label("— none —")))

    def on_list_view_selected(self, event: ListView.Selected) -> None:
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

        self.refresh_market()
