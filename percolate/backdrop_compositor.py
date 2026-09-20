"""Composites the Farm screen's fixed-canvas backdrop from named slot pieces.

Pure function module: no widget/state dependencies, so it's independently
testable and reusable once slots gain multiple selectable pieces (see
docs/north_star.md). Owns data/farmhouse.json's schema end to end.
"""

from __future__ import annotations

import json
import operator

from textual.content import Content

from percolate.config import FARMHOUSE_PATH


def load_farmhouse_data(path=FARMHOUSE_PATH) -> dict:
    """Canvas size + slot rectangles/art for the Farm screen backdrop."""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


_OPS = {
    ">=": operator.ge,
    "<=": operator.le,
    "==": operator.eq,
    ">": operator.gt,
    "<": operator.lt,
}


def _condition_met(value: int, condition: str) -> bool:
    for op, cmp in _OPS.items():
        if condition.startswith(op):
            return cmp(value, int(condition[len(op) :]))
    return value == int(condition)


def _apply_rules(context: dict[str, int], progression: dict) -> int:
    """First matching rule wins; falls back to `"default"` (0 if absent)."""
    for rule in progression.get("rules", []):
        if all(
            _condition_met(context.get(key, 0), cond)
            for key, cond in rule["if"].items()
        ):
            return rule["tier"]
    return progression.get("default", 0)


def resolve_tiers(data: dict, farm, upgrades_data: dict) -> dict[str, int]:
    """Work out each slot's current tier index from player progression.

    A slot's `"progression"` key says where its tier comes from:
      - absent/null: always tier 0 (static slot, e.g. sky).
      - {"upgrade": id}: `farm.upgrade_tier(id)` (0 if unowned).
      - {"from_upgrades": [id, ...], "combine": "rules", "rules": [...],
        "default": N}: builds a context of `{upgrade_id: tier}` and applies
        `_apply_rules` — e.g. "barn" needing both `roaster_slot` and
        `infuser` tiers to pick its art, which a single `"upgrade"` lookup
        can't express.
      - {"derived_from": [slot_id, ...], "combine": "sum" | "rules", ...}:
        combines those slots' own *resolved* tiers, e.g. "house" growing
        off both "barn" and "shed". Resolved in two passes (upgrade-sourced
        slots first, then slot-derived ones) so a derived slot can depend
        on another slot regardless of JSON ordering.

    `farm`/`upgrades_data` are duck-typed (no Farm import needed here) —
    `farm` just needs `.upgrade_tier(upgrade_id: str) -> int`.
    """
    tiers: dict[str, int] = {}
    slots_by_id = {slot["id"]: slot for slot in data["slots"]}

    for slot_id, slot in slots_by_id.items():
        progression = slot.get("progression")
        if not progression or "derived_from" in progression:
            continue
        if "upgrade" in progression:
            tiers[slot_id] = farm.upgrade_tier(progression["upgrade"])
        elif "from_upgrades" in progression:
            context = {u: farm.upgrade_tier(u) for u in progression["from_upgrades"]}
            tiers[slot_id] = _apply_rules(context, progression)

    for slot_id, slot in slots_by_id.items():
        progression = slot.get("progression")
        if not progression or "derived_from" not in progression:
            continue
        context = {dep: tiers.get(dep, 0) for dep in progression["derived_from"]}
        combine = progression.get("combine", "sum")
        if combine == "rules":
            tiers[slot_id] = _apply_rules(context, progression)
        else:
            tiers[slot_id] = sum(context.values())

    return tiers


def composite_backdrop(
    data: dict, tier_by_slot: dict[str, int] | None = None
) -> Content:
    """Paint every slot's art onto a blank canvas, sorted by z ascending,
    and return the whole thing as one multi-line Content for Static.update().

    `tier_by_slot` (typically from `resolve_tiers`) picks which of a slot's
    `pieces` to paint; missing/omitted entries default to tier 0, and an
    out-of-range tier clamps to the slot's highest authored piece.

    Each row is built as a `textual.content.Content` rather than a plain
    string, since two pieces can share a physical row (e.g. a house and a
    barn side by side) and Content tracks style spans independent of the
    text, so slicing/pasting by column index can't misalign them.

    Art is stored as *plain* text and colored via `Content.stylize`, not
    via inline markup (e.g. "[gold]...[/]") parsed by `Content.from_markup`:
    ASCII art routinely contains literal "[", "]" (window/door glyphs like
    "[]", ground-line "][") and trailing "\\" characters, all of which
    collide with markup's own tag syntax — brackets get misparsed as bogus
    tags, and a trailing "\\" immediately before an appended "[/]" forms an
    accidental escape sequence. `stylize` applies a style to a plain string
    directly with no parsing step, so there's nothing for art content to
    collide with. (Textual's own `Content`/`Style` are still used instead of
    `rich.text.Text`/`rich.style.Style` because they resolve color names
    through Textual's more permissive CSS-like parser — Rich's stricter
    parser rejects names like "gold" that this art relies on, only
    accepting numbered xterm variants such as "gold1".)
    """
    width, height = data["canvas"]["width"], data["canvas"]["height"]
    rows = [Content(" " * width) for _ in range(height)]
    tier_by_slot = tier_by_slot or {}

    for slot in sorted(data["slots"], key=lambda s: s["z"]):
        pieces = slot["pieces"]
        tier = min(tier_by_slot.get(slot["id"], 0), len(pieces) - 1)
        art = pieces[tier]["art"]
        color = slot.get("color")
        for line_index, line in enumerate(art):
            canvas_row = slot["row"] + line_index
            if 0 <= canvas_row < height:
                piece = Content(line).stylize(color) if color else Content(line)
                rows[canvas_row] = _paste(rows[canvas_row], piece, slot["col"])

    return Content("\n").join(rows)


def _paste(base_row: Content, piece: Content, col: int) -> Content:
    """Overwrite base_row's cells [col, col+len(piece)) with piece."""
    result = base_row[:col]
    if len(base_row) < col:
        result = result + Content(" " * (col - len(base_row)))
    result = result + piece
    result = result + base_row[col + len(piece) :]
    return result
