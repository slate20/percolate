"""Roasting: ingredients, curated recipes, and the roast batch process.

Recipe building is sandboxed with a curated bonus overlay: any bean +
ingredients + roast level combination is always valid and produces a
systematically-named product at a compositional base value. If the
combination happens to match a curated entry in data/recipes.json, the name
is overridden and a bonus multiplier is applied on top of the base value.
Nothing is ever an invalid or wasted roast.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field

from percolate.config import (
    INGREDIENTS_PATH,
    RECIPES_PATH,
    ROAST_BASE_MULTIPLIER,
    ROAST_STAGES_PATH,
)
from percolate.models.bean import Bean
from percolate.models.timed_process import TimedProcess

DEFAULT_ROAST_DURATION = 3600.0  # 1 hour, independent of any plot's clock


@dataclass
class Ingredient:
    id: str
    name: str
    cost: int
    value: int  # contribution to a roasted product's compositional value

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> Ingredient:
        return cls(
            id=data["id"], name=data["name"], cost=data["cost"], value=data["value"]
        )


@dataclass
class Recipe:
    id: str
    name: str
    bean: str
    ingredients: list[str]
    roast_level: str
    bonus_multiplier: float

    def matches(
        self, bean_id: str, ingredient_ids: list[str], roast_level: str
    ) -> bool:
        return (
            self.bean == bean_id
            and self.roast_level == roast_level
            and set(self.ingredients) == set(ingredient_ids)
        )

    @classmethod
    def from_dict(cls, data: dict) -> Recipe:
        return cls(
            id=data["id"],
            name=data["name"],
            bean=data["bean"],
            ingredients=list(data.get("ingredients", [])),
            roast_level=data["roast_level"],
            bonus_multiplier=data["bonus_multiplier"],
        )


@dataclass
class RoastResult:
    name: str
    value: int
    recipe_id: str | None


def load_ingredient_registry(path=INGREDIENTS_PATH) -> dict[str, Ingredient]:
    with open(path, "r", encoding="utf-8") as f:
        raw = json.load(f)
    return {i_id: Ingredient.from_dict(entry) for i_id, entry in raw.items()}


def load_recipe_registry(path=RECIPES_PATH) -> dict[str, Recipe]:
    with open(path, "r", encoding="utf-8") as f:
        raw = json.load(f)
    return {r_id: Recipe.from_dict(entry) for r_id, entry in raw.items()}


def load_roast_stage_art(path=ROAST_STAGES_PATH) -> dict[str, list[list[str]]]:
    """Fixed-canvas ASCII art for the roaster, keyed by state ("idle" through
    "ready"). Each state is a short list of near-identical frames (steam wisp
    position differs) so RoastScreen can alternate them for ambient motion
    without ever changing the cell's size — same technique as plant_stages."""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _generated_name(bean: Bean, ingredients: list[Ingredient], roast_level: str) -> str:
    parts = [bean.name, roast_level.title()]
    if ingredients:
        parts.append("-".join(i.name for i in ingredients))
    return " ".join(parts)


def resolve_roast(
    bean: Bean,
    ingredients: list[Ingredient],
    roast_level: str,
    recipes: dict[str, Recipe],
) -> RoastResult:
    base_value = bean.raw_sell_value * ROAST_BASE_MULTIPLIER + sum(
        i.value for i in ingredients
    )

    ingredient_ids = [i.id for i in ingredients]
    for recipe in recipes.values():
        if recipe.matches(bean.id, ingredient_ids, roast_level):
            return RoastResult(
                name=recipe.name,
                value=round(base_value * recipe.bonus_multiplier),
                recipe_id=recipe.id,
            )

    return RoastResult(
        name=_generated_name(bean, ingredients, roast_level),
        value=round(base_value),
        recipe_id=None,
    )


@dataclass
class RoastBatch:
    bean_id: str
    ingredient_ids: list[str] = field(default_factory=list)
    roast_level: str = "medium"
    process: TimedProcess = None  # type: ignore[assignment]

    def is_ready(self, now: float) -> bool:
        return self.process is not None and self.process.is_ready(now)

    def progress(self, now: float) -> float:
        if self.process is None:
            return 0.0
        return self.process.progress(now)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> RoastBatch:
        process = data.get("process")
        return cls(
            bean_id=data["bean_id"],
            ingredient_ids=list(data.get("ingredient_ids", [])),
            roast_level=data.get("roast_level", "medium"),
            process=TimedProcess.from_dict(process) if process else None,
        )
