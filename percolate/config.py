"""Global paths, defaults, and timing constants."""

from __future__ import annotations

import os
import sys
from pathlib import Path

# Dev-only cheat bindings (time skip, add gold) — off by default, never
# shown/active for a normal player. Enable with PERCOLATE_DEV=1.
DEV_MODE = os.environ.get("PERCOLATE_DEV") == "1"

# --- Persistence -----------------------------------------------------------

CONFIG_DIR = Path.home() / ".config" / "percolate"
STATE_PATH = CONFIG_DIR / "state.json"

# Bundled content registries (JSON), shipped alongside the package. When
# frozen by PyInstaller, bundled Python modules run out of an in-memory
# archive — `__file__` no longer points at a real path on disk — but data
# files added via the .spec's `datas` are extracted to `sys._MEIPASS`, so
# that's where to look instead.
if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
    PACKAGE_DIR = Path(sys._MEIPASS) / "percolate"
else:
    PACKAGE_DIR = Path(__file__).parent
DATA_DIR = PACKAGE_DIR / "data"
BEANS_PATH = DATA_DIR / "beans.json"
INGREDIENTS_PATH = DATA_DIR / "ingredients.json"
RECIPES_PATH = DATA_DIR / "recipes.json"
UPGRADES_PATH = DATA_DIR / "upgrades.json"
PLANT_STAGES_PATH = DATA_DIR / "plant_stages.json"
FARMHOUSE_PATH = DATA_DIR / "farmhouse.json"
ROAST_STAGES_PATH = DATA_DIR / "roast_stages.json"

# --- Farm screen backdrop ---------------------------------------------------

# Below this terminal height, the Farm screen shows the compact backdrop
# instead of the full detailed scene. (Width has no fixed constant — it's
# derived from the large art's own width in farmhouse.json, see
# FarmScreen._sync_backdrop.)
LARGE_BACKDROP_MIN_HEIGHT = 40

# --- Farm defaults -----------------------------------------------------------

# Just enough to buy a handful of the cheapest seed and start the buy-grow-sell
# loop; no roaster yet — that's the first thing to save up for.
DEFAULT_STARTING_GOLD = 30
DEFAULT_PLOT_COUNT = 3

# --- Roasting ----------------------------------------------------------------

# Flat value-add for turning a raw bean into a roasted product, applied the
# same regardless of which roast level was chosen. Roast level is a flavor
# choice, not a price lever — the only thing that should move roasted value
# further is landing a curated recipe (see recipes.json's bonus_multiplier).
ROAST_BASE_MULTIPLIER = 1.5

# A curated recipe match multiplies the compositional base value by this
# range (the exact multiplier lives per-recipe in recipes.json).
DEFAULT_BONUS_MULTIPLIER = 1.35

# --- UI tick -------------------------------------------------------------

# How often the app re-checks timed processes for stage/ready changes.
# Kept low-frequency on purpose — this is an ambient app, not a real-time one.
UI_TICK_SECONDS = 5.0
