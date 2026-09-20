"""Coffee strain definitions, loaded from data/beans.json.

Growth-stage ASCII art is shared across all beans (see models/plant_stages
below) rather than authored per strain — bean identity is conveyed by name
and the Farm screen's state-tier color, not unique art per variety.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass

from percolate.config import BEANS_PATH, PLANT_STAGES_PATH

# Growth is split into named stages for ASCII display purposes. Thresholds
# are fractions of total growth progress (see TimedProcess.progress).
STAGE_THRESHOLDS: list[tuple[str, float]] = [
    ("seed", 0.0),
    ("sprout", 0.15),
    ("growing", 0.5),
    ("ready", 1.0),
]


@dataclass
class Bean:
    id: str
    name: str
    growth_time: float  # seconds
    seed_cost: int
    raw_sell_value: int

    def stage_for_progress(self, progress: float) -> str:
        """Return the plant-stage key for a growth progress fraction."""
        stage = STAGE_THRESHOLDS[0][0]
        for name, threshold in STAGE_THRESHOLDS:
            if progress >= threshold:
                stage = name
        return stage

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> Bean:
        return cls(
            id=data["id"],
            name=data["name"],
            growth_time=data["growth_time"],
            seed_cost=data["seed_cost"],
            raw_sell_value=data["raw_sell_value"],
        )


def load_bean_registry(path=BEANS_PATH) -> dict[str, Bean]:
    with open(path, "r", encoding="utf-8") as f:
        raw = json.load(f)
    return {bean_id: Bean.from_dict(entry) for bean_id, entry in raw.items()}


def load_plant_stage_art(path=PLANT_STAGES_PATH) -> dict[str, list[str]]:
    """Shared, fixed-canvas, bottom-anchored ASCII art per growth stage.

    Each stage is a list of equal-length rows (Rich markup included) with a
    soil baseline as the last row, so a plot's cell size never changes as
    the plant grows through stages.
    """
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)
