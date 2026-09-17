# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository state

**Percolate** is a cozy, low-attention terminal coffee farm & roastery, built with [Textual](https://textual.textualize.io/) and Python 3.10+. `docs/overview.md` is the authoritative design/architecture doc — read it before making non-trivial changes; this file summarizes what's needed to be productive without re-deriving it.

No test suite, linter config, or CI exists in this repo yet.

**Setup / run:**
```bash
pip install -e .
percolate
```
or without installing: `python -m percolate.main`

**Dev mode** (time-skip and gold cheats for testing, off by default): set `PERCOLATE_DEV=1` before running. Adds bindings `[` (+15m), `]` (+6h), `g` (+1000g) that rewind `TimedProcess.started_at` rather than touching real time.

**Building a standalone executable:** `pip install -e ".[build]"` then `pyinstaller percolate.spec` (must build natively per-OS; PyInstaller can't cross-compile). Produces an onedir build at `dist/percolate/` — ship the whole folder, not just the executable. `config.PACKAGE_DIR` handles the frozen-vs-source path split (`sys._MEIPASS` when frozen) that both data-file loading and `PercolateApp._BASE_PATH` (Textual's CSS-path resolution) depend on.

State persists to `~/.config/percolate/state.json`, written via `Farm.save_to_disk()` after every mutating action (see `main.py`'s `action_quit` and dev-tool actions for the pattern) — there's no periodic autosave loop, so any new player-facing mutation should call `save_to_disk()` itself.

## Design pillars (govern implementation choices)

From `docs/overview.md` §1 — these should guide any new feature, not just visual polish:
- **No punishing mechanics.** Nothing decays or loses value from being left alone; a ready crop/roast earns nothing extra for sitting uncollected. Elapsed time past `duration` is a pure boolean gate (`TimedProcess.is_ready`), never a scaling bonus.
- **No urgency.** Growth/roast timers pace the experience; they don't reward min-maxing or punish absence (design targets a multi-day gap between check-ins working fine).
- **Ambient over interactive.** Farm/Roast screens should feel alive via slow ambient motion (`set_interval` on the order of seconds), not require input to feel alive.
- **Small and content-extensible, not deep.** New beans/ingredients/recipes/upgrades are meant to be added as JSON data (`percolate/data/*.json`), not by growing the mechanical surface area.

## Architecture

**Layering:** `models/` (pure dataclasses + game logic, no Textual imports) → `screens/` (Textual `Screen` subclasses that call into `app.farm`) → `main.py` (`PercolateApp`: screen router, global tick, theme/registry loading at startup). Content lives in `data/*.json`, loaded once at app startup into registries (`load_bean_registry`, `load_ingredient_registry`, etc.) and passed around as `dict[id, obj]`, not re-read per access.

**Timed-process engine** (`models/timed_process.py`): growing and roasting share one primitive — `TimedProcess(started_at, duration)` with `elapsed(now)`/`is_ready(now)`. `Plot` and `RoastBatch` each own an independent instance; there is no shared clock between them. When adding a new timed mechanic, compose this primitive rather than reimplementing offline-delta math.

**Farm as the single state container** (`models/farm.py`): `Farm` holds gold, plots, all inventories (seed/raw bean/ingredient/roasted-product), roast batches, owned upgrades, and discovered recipes, and is the only thing screens mutate through — screens don't touch `Plot`/`RoastBatch` internals directly except via `Farm`'s methods (`plant_bean`, `harvest_plot`, `start_roast`, `collect_roast`, `sell_product`, `apply_upgrade`, etc.). `Farm.to_dict`/`from_dict` is the full save-schema; extending persisted state means updating both directions plus a sensible `.get(..., default)` fallback for old save files (there's no migration system — backward-compat is handled ad hoc via defaults, see `from_dict`).

**Upgrade tiers are non-stacking**: owning tier N applies only tier N's effect (`Farm._current_tier_effect` indexes `tiers[tier - 1]`), not the sum of tiers 1..N. `owned_upgrades` and `upgrades_data` (from `data/upgrades.json`) are separate: the former is per-save progress, the latter is the tier definitions/costs.

**Economy pacing is deliberate, not incidental**: players start with gold for only a few cheap seeds and zero roast slots (`max_roast_slots()` returns 0 until the "roaster_slot" upgrade's first tier is bought) — the intended opening loop is buy→grow→sell-raw→save→unlock roaster. Similarly, `max_ingredients()` gates flavor slots behind the "infuser" upgrade. Don't short-circuit these gates when adding features; they're the game's only progression structure.

**Roast resolution** (`models/roast.py`'s `resolve_roast`): value is always compositional (bean value × `ROAST_BASE_MULTIPLIER` + ingredient values) and every combination is sellable — roast level is a naming/flavor choice, not a price lever. A curated match in `data/recipes.json` (bean + ingredients + roast level) overrides the generated name and applies a `bonus_multiplier` on top; it's a bonus layer, not a gate. When adding recipes/ingredients, preserve this "everything is valid, curated combos are just better" structure rather than introducing hard requirements.

**Upgrade modal is contextual, not a screen**: `screens/upgrade_modal.py`'s `UpgradeModal` is parameterized by which screen opened it (`u` on Farm → Farm Upgrades; `u` on Roast → Roaster Upgrades) rather than being routed to separately. Reuse this pattern instead of adding new screens for scoped shop-like UI.

**No `Footer`**: Textual's default binding-list footer is intentionally removed. Global screen-switch keys show as one muted `widgets.NAV_HINT` line; every other control is hinted inline next to what it acts on (e.g., a cursored plot shows `(enter) plant`). Follow this convention for new bindings rather than relying on the default footer or adding new chrome.

**Size-adaptive backdrop**: `FarmScreen`'s landscape art (`data/farmhouse.json`) picks between `compact`/`large` variants by polling terminal size on the existing tick — there's no dedicated resize-event plumbing, and ASCII art isn't meant to be dynamically rescaled, so new backdrop-style content should follow the same discrete-variant approach rather than trying to scale a single asset. The width threshold is derived from the large variant's own `width` field in `farmhouse.json` (plus 1 cell of padding per side) rather than a fixed constant, so it stays correct if that art is resized; the height threshold is still a fixed constant, `config.LARGE_BACKDROP_MIN_HEIGHT`.
