# North Star: Evolving Personal Farm (ASCII Header)

## Vision

Over time, every player’s farm should feel uniquely *theirs*.

Players begin with a simple, shared starting scene. As they progress — unlocking the roaster, infuser, extra plots, and other milestones — the farm header organically grows and can be further personalized. The long-term goal is for the Farm screen to become a quiet, living diorama of the player’s own coffee operation: something they enjoy simply looking at.

This is purely visual and emotional. It should never create pressure, optimization loops, or mechanical advantage.

## Design Principles

- **Same farmland, growing over time**  
  The overall scene remains recognizably the same piece of land. New buildings and elements appear as natural expansions rather than completely different layouts.

- **Fixed framework, modular pieces**  
  The header uses a fixed canvas size and a small set of positional slots. Players (and progression) can swap pieces within those slots, but cannot freely place or resize elements. This keeps the system attainable and visually coherent.

- **Optional & calm**  
  Customization is never required. A player who ignores it still sees their farm improve through progression. A player who enjoys tinkering can make theirs feel personal.

- **Low-attention friendly**  
  Changes should feel delightful when noticed, never demanding. No complex editors or frequent decisions.

## Proposed Technical Approach

### Fixed Canvas + Slots

- Define a single fixed-width (and roughly fixed-height) ASCII canvas for the entire farm header.
- Divide the canvas into named slots, for example:
  - `sky` / weather / time-of-day layer
  - `house` (main farmhouse / cabin)
  - `barn` / roastery building
  - `left_decor` / `right_decor`
  - `foreground` elements
  - `background` trees / hills
  - any other stable positions that make compositional sense

- Every modular piece is authored to fit exactly inside its slot (same dimensions and alignment rules).

### Progression + Customization Model

1. **Automatic evolution**  
   Key unlocks (first roaster, infuser, reaching N plots, etc.) automatically advance the “base” appearance of one or more slots. The farm visibly grows even if the player never opens a customization menu.

2. **Unlockable piece variants**  
   Gold (or other soft progression) unlocks alternative pieces for each slot (different house styles, barn variants, decorative objects, color treatments, etc.).

3. **Player choice (optional)**  
   Once multiple pieces are unlocked for a slot, the player can swap between them. Defaults can remain the progression-based versions so that non-customizers still see growth.

### Staging Plan (Recommended)

| Stage | Scope | Goal |
|-------|-------|------|
| 1     | Progression-only evolution | 3–5 distinct visual stages of the farm that unlock automatically. No player choice yet. Proves the “my farm is growing” feeling. |
| 2     | Limited modular pieces | Add 2–3 alternate pieces for the most important slots (house, barn). Simple swap UI. |
| 3     | Expanded cosmetics | More pieces, simple color/theme variants, small decorative objects. |
| 4     | Polish & expression | Weather, time-of-day, subtle animations, or seasonal touches if desired — still within the same slot framework. |

This path delivers emotional value early while keeping engineering risk low.

## Why This Fits Percolate

- Reinforces the “terminal toy” identity: the screen itself becomes more pleasant to leave open.
- Gives long-term players a gentle, non-pressured reason to keep returning (“I want to see how *my* farm looks now”).
- Stays true to the original cozy, low-attention roots — no new gameplay systems required.
- Creates a natural content pipeline (new ASCII pieces) that is independent of balance changes.

## Open Questions / Future Considerations

- Exact slot list and canvas dimensions (to be determined from current Farm screen layout).
- How aggressively to auto-upgrade vs. leave choice to the player.
- Whether color themes should be global or per-piece.
- Save format for selected pieces (should be trivial additions to `state.json`).

---

**Status**: Proposed north star – not committed scope.  
**Intent**: Capture the direction so it is not lost, while protecting the project from premature complexity.