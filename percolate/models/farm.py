"""State container: inventory, gold, upgrades, persistence."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field

from percolate.config import (
    CONFIG_DIR,
    DEFAULT_PLOT_COUNT,
    DEFAULT_STARTING_GOLD,
    STATE_PATH,
    UPGRADES_PATH,
)
from percolate.models.bean import Bean
from percolate.models.plot import Plot
from percolate.models.roast import Ingredient, Recipe, RoastBatch, resolve_roast
from percolate.models.timed_process import TimedProcess


def load_upgrades_data(path=UPGRADES_PATH) -> dict:
    """Upgrades are plain tiered data, consulted by Farm's effect helpers
    and rendered directly by UpgradesScreen — no dataclass wrapper needed."""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


@dataclass
class RoastedProduct:
    name: str
    value: int
    recipe_id: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> RoastedProduct:
        return cls(
            name=data["name"], value=data["value"], recipe_id=data.get("recipe_id")
        )


@dataclass
class Farm:
    gold: int = DEFAULT_STARTING_GOLD
    plots: list[Plot] = field(default_factory=list)
    seed_inventory: dict[str, int] = field(default_factory=dict)
    raw_bean_inventory: dict[str, int] = field(default_factory=dict)
    ingredient_inventory: dict[str, int] = field(default_factory=dict)
    roast_batches: list[RoastBatch] = field(default_factory=list)
    roasted_inventory: list[RoastedProduct] = field(default_factory=list)
    owned_upgrades: dict[str, int] = field(default_factory=dict)
    discovered_recipes: set[str] = field(default_factory=set)

    # --- Farm / plots --------------------------------------------------

    def buy_seed(self, bean: Bean, quantity: int = 1) -> None:
        cost = bean.seed_cost * quantity
        if self.gold < cost:
            raise ValueError("Not enough gold for seed.")
        self.gold -= cost
        self.seed_inventory[bean.id] = self.seed_inventory.get(bean.id, 0) + quantity

    def plant_bean(
        self, plot_index: int, bean: Bean, now: float, growth_time: float | None = None
    ) -> None:
        plot = self.plots[plot_index]
        if not plot.is_empty:
            raise ValueError("Plot is already planted.")
        have = self.seed_inventory.get(bean.id, 0)
        if have < 1:
            raise ValueError("No seeds of that strain. Buy some at the Market.")
        self.seed_inventory[bean.id] = have - 1
        plot.plant(
            bean.id, growth_time if growth_time is not None else bean.growth_time, now
        )

    def harvest_plot(self, plot_index: int, now: float) -> str:
        plot = self.plots[plot_index]
        if not plot.is_ready(now):
            raise ValueError("Plot is not ready to harvest.")
        bean_id = plot.harvest()
        self.raw_bean_inventory[bean_id] = self.raw_bean_inventory.get(bean_id, 0) + 1
        return bean_id

    def sell_raw_bean(self, bean: Bean, quantity: int = 1) -> None:
        have = self.raw_bean_inventory.get(bean.id, 0)
        if have < quantity:
            raise ValueError("Not enough raw beans to sell.")
        self.raw_bean_inventory[bean.id] = have - quantity
        self.gold += bean.raw_sell_value * quantity

    # --- Market / ingredients -------------------------------------------

    def buy_ingredient(self, ingredient: Ingredient, quantity: int = 1) -> None:
        cost = ingredient.cost * quantity
        if self.gold < cost:
            raise ValueError("Not enough gold for ingredient.")
        self.gold -= cost
        self.ingredient_inventory[ingredient.id] = (
            self.ingredient_inventory.get(ingredient.id, 0) + quantity
        )

    # --- Roasting --------------------------------------------------------

    def start_roast(
        self,
        bean: Bean,
        ingredients: list[Ingredient],
        roast_level: str,
        duration: float,
        now: float,
    ) -> None:
        have_beans = self.raw_bean_inventory.get(bean.id, 0)
        if have_beans < 1:
            raise ValueError("No raw beans of that strain to roast.")
        for ingredient in ingredients:
            if self.ingredient_inventory.get(ingredient.id, 0) < 1:
                raise ValueError(f"Not enough {ingredient.name} to roast.")

        self.raw_bean_inventory[bean.id] = have_beans - 1
        for ingredient in ingredients:
            self.ingredient_inventory[ingredient.id] -= 1

        batch = RoastBatch(
            bean_id=bean.id,
            ingredient_ids=[i.id for i in ingredients],
            roast_level=roast_level,
            process=TimedProcess(started_at=now, duration=duration),
        )
        self.roast_batches.append(batch)

    def collect_roast(
        self,
        batch_index: int,
        beans: dict[str, Bean],
        ingredients: dict[str, Ingredient],
        recipes: dict[str, Recipe],
        now: float,
    ) -> RoastedProduct:
        batch = self.roast_batches[batch_index]
        if not batch.is_ready(now):
            raise ValueError("Roast batch is not ready to collect.")

        bean = beans[batch.bean_id]
        batch_ingredients = [ingredients[i_id] for i_id in batch.ingredient_ids]
        result = resolve_roast(bean, batch_ingredients, batch.roast_level, recipes)

        product = RoastedProduct(
            name=result.name, value=result.value, recipe_id=result.recipe_id
        )
        self.roasted_inventory.append(product)
        if result.recipe_id:
            self.discovered_recipes.add(result.recipe_id)

        del self.roast_batches[batch_index]
        return product

    def sell_product(self, product_index: int) -> RoastedProduct:
        product = self.roasted_inventory.pop(product_index)
        self.gold += product.value
        return product

    # --- Upgrades ----------------------------------------------------------

    def upgrade_tier(self, upgrade_id: str) -> int:
        return self.owned_upgrades.get(upgrade_id, 0)

    def apply_upgrade(self, upgrade_id: str, cost: int) -> None:
        if self.gold < cost:
            raise ValueError("Not enough gold for upgrade.")
        self.gold -= cost
        self.owned_upgrades[upgrade_id] = self.upgrade_tier(upgrade_id) + 1

    def expand_plots(self, count: int = 1) -> None:
        self.plots.extend(Plot() for _ in range(count))

    # --- Upgrade effects -----------------------------------------------------
    # Tiers are non-stacking: owning tier N applies only that tier's bonus,
    # not the sum of tiers 1..N.

    def _current_tier_effect(
        self, upgrade_id: str, upgrades_data: dict, key: str
    ) -> float:
        tier = self.upgrade_tier(upgrade_id)
        tiers = upgrades_data.get(upgrade_id, {}).get("tiers", [])
        if tier <= 0 or tier > len(tiers):
            return 0.0
        return tiers[tier - 1].get(key, 0.0)

    def growth_speed_bonus(self, upgrades_data: dict) -> float:
        return self._current_tier_effect(
            "soil_quality", upgrades_data, "growth_speed_bonus"
        )

    def roast_speed_bonus(self, upgrades_data: dict) -> float:
        return self._current_tier_effect(
            "roaster_speed", upgrades_data, "roast_speed_bonus"
        )

    def max_ingredients(self, upgrades_data: dict) -> int:
        return int(
            self._current_tier_effect("infuser", upgrades_data, "max_ingredients")
        )

    def max_roast_slots(self, upgrades_data: dict) -> int:
        # No free roaster to start — building the first one is the player's
        # first savings goal (see docs/overview.md's economy pacing).
        tier = self.upgrade_tier("roaster_slot")
        tiers = upgrades_data.get("roaster_slot", {}).get("tiers", [])
        return sum(t.get("slots_added", 0) for t in tiers[:tier])

    # --- Dev tools (PERCOLATE_DEV=1 only, see config.DEV_MODE) ----------------

    def debug_advance_time(self, seconds: float) -> None:
        """Rewind every active TimedProcess's start time, fast-forwarding
        growth/roasting for testing. Real time.time() is untouched."""
        for plot in self.plots:
            if plot.process is not None:
                plot.process.started_at -= seconds
        for batch in self.roast_batches:
            if batch.process is not None:
                batch.process.started_at -= seconds

    # --- Persistence ---------------------------------------------------------

    def to_dict(self) -> dict:
        data = asdict(self)
        data["discovered_recipes"] = sorted(self.discovered_recipes)
        return data

    @classmethod
    def from_dict(cls, data: dict) -> Farm:
        return cls(
            gold=data.get("gold", DEFAULT_STARTING_GOLD),
            plots=[Plot.from_dict(p) for p in data.get("plots", [])],
            seed_inventory=data.get("seed_inventory", {}),
            raw_bean_inventory=data.get("raw_bean_inventory", {}),
            ingredient_inventory=data.get("ingredient_inventory", {}),
            roast_batches=[
                RoastBatch.from_dict(b) for b in data.get("roast_batches", [])
            ],
            roasted_inventory=[
                RoastedProduct.from_dict(p) for p in data.get("roasted_inventory", [])
            ],
            owned_upgrades=data.get("owned_upgrades", {}),
            discovered_recipes=set(data.get("discovered_recipes", [])),
        )

    @classmethod
    def new_default(cls) -> Farm:
        return cls(plots=[Plot() for _ in range(DEFAULT_PLOT_COUNT)])

    def save_to_disk(self, path=STATE_PATH) -> None:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2)

    @classmethod
    def load_from_disk(cls, path=STATE_PATH) -> Farm:
        if not path.exists():
            return cls.new_default()
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return cls.from_dict(data)
