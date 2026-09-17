# Percolate — Project Concept & Architecture Overview

`Percolate` is a cozy, low-attention terminal coffee farm & roastery, built with Textual and Python 3.10+. It runs in a terminal pane, saving state locally to disk and growing passively while you work. The Farm screen's full landscape backdrop wants a moderately sized pane to show in full detail; it degrades gracefully to a compact scene in a smaller or tiled pane (see §4), so it's still usable corner-of-the-screen small — just prettier with more room.

## 1. Design Philosophy

Percolate is not an engagement-optimized idle game. It's closer in spirit to `cbonsai`: something pleasant to glance at during a work microbreak, with a sense of quiet progression, that never demands attention.

This governs every other decision in this document:

- **No punishing mechanics.** Nothing decays, withers, or loses value from being left alone. The expected usage pattern is intermittent check-ins across a work day, then no interaction until the next work day (sometimes a multi-day weekend gap) — the game must be equally pleasant to open after 20 minutes or 3 days.
- **No urgency, no bonus for idling.** Growth timers exist to pace the experience, not to reward min-maxing. A crop or roast sitting `ready` and uncollected earns nothing extra; time elapsed only ever answers "is it ready yet?"
- **Ambient over interactive.** The Farm and Roast screens should feel alive at rest — slow, sparse motion — rather than needing input to feel engaging. Any "juice" belongs in ambient visual polish, not in mechanics that call for attention.
- **Small and content-extensible, not deep.** The architecture is a stable foundation that new beans, ingredients, recipes, and upgrades get added to over time as data. It intentionally does not grow into a full TUI strategy game or market sim.

## 2. Modular Directory & Package Layout

Functionality is split into dedicated submodules so new beans, recipes, or screens can be added without touching unrelated code:

```text
percolate/
├── percolate/
│   ├── __init__.py
│   ├── main.py               # App entry point, screen router, global tick loop
│   ├── config.py             # Global paths, defaults, and timing constants
│   ├── theme.py               # Percolate's custom Textual color themes
│   │                          #   (percolate-latte default, percolate-mocha)
│   │
│   ├── models/                # Pure data classes & game engine logic
│   │   ├── __init__.py
│   │   ├── timed_process.py  # Shared start/duration/is_ready primitive
│   │   ├── bean.py           # Coffee strain definitions + growth-stage timing
│   │   ├── plot.py           # Individual plot state — wraps TimedProcess for growing
│   │   ├── roast.py          # RoastBatch state — wraps TimedProcess for roasting, recipe resolution
│   │   └── farm.py           # State container (inventory, gold, upgrades, persistence)
│   │
│   ├── screens/               # Textual UI views
│   │   ├── __init__.py
│   │   ├── farm_screen.py    # Ambient ASCII field, plot planting/harvesting     [F]
│   │   ├── roast_screen.py   # Persistent recipe builder + ambient roaster art  [R]
│   │   ├── market_screen.py  # Plain buy/sell columns (seeds, ingredients,      [M]
│   │   │                     #   raw beans, roasted products)
│   │   └── upgrade_modal.py  # Contextual upgrade shop, opened with [U] from
│   │                         #   FarmScreen or RoastScreen (not its own screen)
│   │
│   └── data/                  # Content definitions (JSON registries)
│       ├── beans.json        # Coffee strain registry (growth stats)
│       ├── plant_stages.json # Shared ASCII art per growth stage (seed/sprout/growing/ready)
│       ├── roast_stages.json # Shared ASCII art per roaster state (idle..ready), steam frames
│       ├── farmhouse.json    # Farm screen backdrop scene (compact/large variants)
│       ├── ingredients.json  # Flavor add-ins purchasable at Market
│       ├── recipes.json      # Unlockable named roast recipes
│       └── upgrades.json     # Passive perks and tool upgrades
│
├── pyproject.toml            # Project metadata & dependencies
├── percolate.spec            # PyInstaller build spec (see README's "Building
│                             #   a standalone executable"); config.PACKAGE_DIR
│                             #   handles the frozen-vs-source path split
└── README.md
```

## 3. Core Systems

### A. Timed-Process Engine (`models/timed_process.py`)
Growing and roasting are mechanically the same shape: start a clock, wait, become ready. Rather than duplicating offline-delta math in two places, both processes compose a shared primitive:

```python
@dataclass
class TimedProcess:
    started_at: float
    duration: float

    def elapsed(self, now: float) -> float:
        return now - self.started_at

    def is_ready(self, now: float) -> bool:
        return self.elapsed(now) >= self.duration
```

`Plot` and `RoastBatch` each hold their **own independent** `TimedProcess` instance — a plot's clock and a roast batch's clock never share or block on each other. Sharing the math isn't the same as sharing the state.

`elapsed`/`is_ready` are used strictly as a boolean gate. Elapsed time past `duration` has no other effect — no bonus yield, no quality boost for waiting longer. Any yield or quality bonuses come exclusively from upgrades and recipes, never from idle time.

### B. Coffee Strain Registry (`models/bean.py` & `data/beans.json`)
Beans are defined externally in JSON rather than hardcoded into UI widgets. Each strain defines:
- **Growth Time**: target seconds to `ready`, in the **3–6 hour** range — long enough to witness growth stages progress across a work day, short enough to not require multi-day "overnight" tiers.
- **Seed Cost / Raw Sell Value**: seeds are bought at the Market (into a `seed_inventory`) and planting consumes one. Seed cost is always the cheapest rung — raw beans sell for noticeably more than their seed cost (a real profit for just growing), and roasting them is worth more still. This ordering (seed < raw < roasted) is the whole economy's backbone; see the Economy Pacing note below.

No `withered` stage — crops never lose value from being left uncollected.

```json
{
  "yirgacheffe": {
    "id": "yirgacheffe",
    "name": "Yirgacheffe",
    "growth_time": 14400,
    "seed_cost": 16,
    "raw_sell_value": 28
  }
}
```

**Economy pacing.** The player starts with only enough gold for a few seeds of the cheapest strain (Bourbon) and **no roaster** — `Farm.max_roast_slots()` returns 0 until the first "Roaster" upgrade tier is bought. The intended opening loop is buy seeds -> grow -> sell raw beans -> repeat until there's enough gold saved for a roaster; only then does the roasting/recipe layer (§C) open up. This gives the game an actual early goal instead of starting the player already able to do everything.

**Growth-stage ASCII art is shared across all beans**, not authored per strain — see `data/plant_stages.json` and §4. A bean's identity is conveyed by its name label and the plot's state-tier color, not unique art per variety; this keeps content authoring bounded (4 stage drawings total, not one set per strain) while still being cheap to override later since it's just data.

### C. Roasting System (`models/roast.py`, `screens/roast_screen.py`)
Harvested beans feed into a small recipe builder — this is the mechanical depth-add beyond the original farm-only concept, scoped deliberately as *profile selection*, not a live roasting simulation (no real-time temperature curves or timing input during the roast).

Recipe building is **sandboxed with a curated bonus overlay** — a deliberate hybrid to avoid two failure modes: a purely open sandbox collapses into players computing one "best value" combo and repeating it forever (no lasting discovery), while a purely curated/gated list has the same problem once the list is known, and makes any non-matching combo feel like a wasted roast (violates the no-punishment philosophy).

1. **Choose beans** from harvested inventory.
2. **Choose ingredients** — flavor add-ins bought from the Market (`data/ingredients.json`). Gated behind the **Infuser** upgrade (`Farm.max_ingredients()`): with no Infuser, roasts are plain (0 flavors); tier 1 allows 1 flavor per roast, tier 2 allows 2. This is a deliberate second progression gate on top of the Roaster itself — a plain roast is already a solid value bump over selling raw, so a new roaster-owner has an immediate simple win, and the recipe/flavor layer becomes its own thing to save up for next.
3. **Choose roast level** (e.g. light / medium / dark).
4. **Base value is always compositional** — computed from bean value (flat `ROAST_BASE_MULTIPLIER`, applied the same at every roast level) + ingredient values. Every combination is valid and sellable; nothing is ever "wrong." The product name is systematically generated: `"<bean> <roast_level> <flavor(s)>"`, e.g. *"Yirgacheffe Light Cinnamon-Vanilla"*. Roast level (light/medium/dark) is a flavor choice, not a price lever — it never changes value on its own; only a matching curated recipe does (step 5).
5. **Curated combos in `data/recipes.json` layer a bonus on top**, not a gate: if the chosen bean + ingredients + roast level matches a curated entry, the generated name is overridden with a special name and a value multiplier (e.g. 1.3–1.5x) is applied. This is the "aha" discovery moment — finding a specific combo that outperforms its raw compositional value.
6. Progression is soft-locked by cost alone: fancier beans and exotic ingredients cost more but have higher base sell value, so there's no unlock gate to fight against experimentation.
7. The roast batch runs on its own `TimedProcess`, independent of any plot's timer. Output becomes sellable inventory at the Market.

```json
{
  "smooth_medium": {
    "id": "smooth_medium",
    "name": "Smooth Medium Roast",
    "bean": "yirgacheffe",
    "ingredients": ["vanilla"],
    "roast_level": "medium",
    "bonus_multiplier": 1.35
  }
}
```

### D. Progressive Engagement & Upgrade Paths (`screens/upgrade_modal.py`)
Upgrades are a contextual modal, not their own screen: pressing `u` on the Farm screen opens **Farm Upgrades** (Plot Expansion, Soil Quality); `u` on the Roast screen opens **Roaster Upgrades** (Roaster, Roaster Efficiency, Infuser). Both reuse the same `UpgradeModal` class, parameterized by which `data/upgrades.json` entries it shows — upgrades are a "spend gold on a permanent perk" transaction like buying ingredients, but scoped to the screen they affect rather than routed through the Market. The Roaster upgrade's first tier is not "extra" — it's the player's first roaster, and the whole reason roasting is initially unavailable (see the Economy Pacing note in §B).
- **Plot Expansion**: grow the field from a 2x2 grid up to 3x3 or 4x4.
- **Soil Quality**: permanently speeds up bean growth rates across all plots (10% / 25% / 50%).
- **Roaster Upgrades**: additional roast batch slots, faster roast times.
- **Recipe Unlocks**: new named recipes become purchasable/discoverable, expanding what combinations produce premium products.

## 4. Aesthetic & Feel Guidelines (Farm & Roast Screens)

These two screens carry the "zen" of the app and are where visual craft belongs — everything else stays minimal by comparison.

- **Real multi-line ASCII art, on a fixed canvas, bottom-anchored.** Plots render actual plant drawings (`data/plant_stages.json`), not single-character placeholders. Every stage is authored on the same fixed width×height block with a shared soil baseline at the bottom row, so the plant visibly fills more of the canvas as it grows (small sprout near the soil → full bush at `ready`) without the plot's grid cell ever changing size between stages. Light Rich-markup accenting (green foliage, brown soil/trunk, red-brown cherries at `ready`) layers on top of the plot's state-tier color, which still governs the plain label/status text.
- **Stage-transition reveal, not snap.** When a plot or roast batch crosses into a new stage, reveal the new ASCII frame over ~1–2 seconds instead of swapping instantly. This is the one moment of motion; the rest of the time the screen sits still.
- **Color as the glanceable status signal.** Dim/desaturated for empty or early stages, warming color with progress, a distinct bright color for `ready`. State should be readable from color alone.
- **Sparse ambient motion between transitions.** A drifting leaf, a steam wisp, a slow color "breathing" pulse — low-frequency (`set_interval` on the order of seconds, not frames), keeping the screen alive without demanding attention or meaningful CPU.
- **Roasting as a visual set piece.** Beans shifting color (green → yellow → brown → dark) with rising steam/smoke during a roast is the strongest animation opportunity in the app — worth more polish than the field view.
- **Time-of-day tinting.** Subtle background/border color shift keyed to real wall-clock time (cooler mornings, warmer evenings) — free ambiance requiring no interaction.
- **Farm landscape backdrop, size-adaptive.** A non-interactive ASCII scene (`data/farmhouse.json`) sits above the plot grid in normal document flow, giving the Farm screen a sense of place rather than boxes floating in void. Two hand-authored variants — `compact` and `large` — are picked by polling the terminal's size on the existing tick (no dedicated resize-event plumbing); ASCII art doesn't downscale cleanly, so a smaller pane gets a simpler scene rather than a shrunk one.
- **A cohesive color theme, not Textual's default.** `theme.py` registers a custom warm coffee-roastery palette (roasted browns, crema gold, terracotta) as the app's active Textual theme, so built-in widget chrome (buttons, list selection highlights, focus rings) matches the hand-picked colors already used in the custom ASCII art and CSS, instead of clashing with Textual's default blue accent.
- **Control hints live inline, not in a footer.** Textual's default `Footer` lists every binding — including per-screen contextual ones — as loud key-chips; Percolate removes it in favor of a single slim, muted "which key switches screens" line (`widgets.NAV_HINT`), with everything else hinted right next to the control it affects (a cursored plot's own `(enter) plant`, a ready roast's `(c)`, a screen's tint bar showing `(u) Upgrades`).

## 5. UI Screen Routing Map

```text
                     ┌────────────────────────┐
                     │ PercolateApp            │
                     │ (Central App Engine)    │
                     └───────────┬─────────────┘
                                 │
              ┌──────────────────┼──────────────────┐
              ▼                  ▼                   ▼
      ┌───────────────┐  ┌───────────────┐   ┌─────────────────────┐
      │  FarmScreen    │  │  RoastScreen  │   │   MarketScreen       │
      │  (HotKey: [F]) │  │  (HotKey: [R])│   │  (HotKey: [M])       │
      ├────────────────┤  ├───────────────┤   ├──────────────────────┤
      │ • Ambient field│  │ • Persistent  │   │ Buy column:          │
      │ • Growth stages│  │   bean/flavor/│   │ • Buy Seeds          │
      │ • Plant/harvest│  │   level       │   │ • Buy Ingredients    │
      │ • [U] Farm     │  │   builder     │   │ Sell column:         │
      │   Upgrades     │  │ • Ambient     │   │ • Sell Raw Beans     │
      │   (modal)      │  │   roaster art │   │ • Sell Roasted       │
      │                │  │ • Recipe log  │   │   Products           │
      │                │  │ • [U] Roaster │   │                      │
      │                │  │   Upgrades    │   │                      │
      │                │  │   (modal)     │   │                      │
      └────────────────┘  └───────────────┘   └──────────────────────┘
```

`[U]` opens a contextual `UpgradeModal` scoped to the current screen (Farm
Upgrades vs. Roaster Upgrades) rather than routing to a shared screen —
Upgrades is a permanent-perk shop, mechanically similar to buying
ingredients, but scoped to whichever screen the perk affects. There's no
`Footer` listing bindings; global screen-switch keys (`f`/`r`/`m`/`q`) show
as one muted line per screen, and every other control is hinted inline next
to what it acts on (see §4).

## 6. Example Data Flow Architecture

Planting through selling flows through clean layers:
1. **Buy seed**: `MarketScreen` calls `app.farm.buy_seed(bean)`, adding to `seed_inventory`.
2. **Plant**: `FarmScreen` calls `app.farm.plant_bean(plot_id, bean_id)`, consuming one owned seed; the plot starts its own `TimedProcess`.
3. **Harvest**: once ready, harvesting moves raw beans into inventory.
4. **Roast**: `RoastScreen` builds a batch — bean + ingredients + roast level — via `app.farm.start_roast(...)`, which starts an independent `TimedProcess`.
5. **Sell**: once roasted, `MarketScreen` sells the resulting product (recipe-matched or baseline) for gold.
6. **Persist**: `app.farm.save_to_disk()` serializes state to `~/.config/percolate/state.json` after each mutation.
7. **Reactive Render**: Textual updates the affected `Static` widgets with new ASCII frames automatically, with stage transitions revealed per §4.
