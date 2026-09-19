# Percolate

A cozy, low-attention terminal coffee farm & roastery, built with [Textual](https://textual.textualize.io/) and Python 3.10+.

Plant beans, let them grow while you work, harvest and roast them into named coffee products, and sell them at market — all from a terminal pane that sits quietly in the corner of your screen. Nothing decays, nothing punishes you for walking away, and there's no urgency: check in for a minute or come back in three days, either way it's ready when you are.

## Download and run

Grab the latest build for your OS from the [Releases](../../releases) page — no Python install required. Each release is a zipped folder (onedir build); unzip it and run the `percolate` executable (`percolate.exe` on Windows) inside. Keep the whole folder together, not just the executable — it depends on the rest of the files alongside it.

### Running from source

```bash
pip install -e .
percolate
```

or, without installing:

```bash
python -m percolate.main
```

## Controls

| Key | Action |
| --- | --- |
| `f` | Farm screen |
| `r` | Roast screen |
| `m` | Market screen |
| `h` | Help |
| `q` | Quit (saves automatically) |

Control hints are shown inline, next to whatever they act on, rather than in a footer — e.g. the selected plot shows `(enter) plant`, a finished roast shows `(c)`, and each screen's tint bar shows `(u) Upgrades`. `u` opens a contextual upgrade shop for that screen (Farm Upgrades vs. Roaster Upgrades) instead of a separate screen. On the Market screen, Tab moves focus between the four buy/sell lists and Enter acts on the highlighted row.

State is saved to `~/.config/percolate/state.json` after every action.

## The loop

1. **Buy seeds** at the Market with starting gold.
2. **Plant and grow** them on the Farm screen — each plot runs its own multi-hour timer with ASCII growth stages (seed → sprout → growing → ready).
3. **Harvest and sell raw beans**, or save up for the Roaster upgrade to unlock roasting.
4. **Roast** harvested beans into named coffee — choose a bean, optional flavor ingredients, and a roast level; curated combinations in the recipe list earn a bonus over their base value.
5. **Sell roasted product** at the Market for more than raw beans ever fetch, and reinvest in upgrades (more plots, faster growth, more roast slots, more flavor slots).

Your farmhouse backdrop on the Farm screen evolves automatically as you unlock upgrades — a purely visual, no-pressure sense of progress (see `docs/north_star.md`).

## Theme

Percolate ships two custom warm coffee-roastery color themes — `percolate-latte` (default, softer/lighter) and `percolate-mocha` (darker, more saturated). Both are dark themes — neither is a bright/light theme. Switch between them, or any other built-in Textual theme, from the command palette (`ctrl+p`).

## Dev mode

Set `PERCOLATE_DEV=1` before launching to enable testing shortcuts (off by default, no effect on real time):

| Key | Action |
| --- | --- |
| `[` | Skip forward 15 minutes |
| `]` | Skip forward 6 hours |
| `g` | +1000 gold |

These rewind timer start times rather than touching the system clock, so they only affect Percolate's own state.

## Building a standalone executable

This is how the [Releases](../../releases) builds are produced, and you can do the same locally with [PyInstaller](https://pyinstaller.org) — no Python install needed to run the result afterward. PyInstaller can't cross-compile, so build on whichever OS you want an executable for (build on Windows for a `.exe`, on macOS/Linux for their native binary):

```bash
pip install -e ".[build]"
pyinstaller percolate.spec
```

This produces `dist/percolate/` — an entire folder (onedir build, not a single file) containing `percolate` (or `percolate.exe` on Windows) plus its bundled data/CSS/runtime. Ship the whole folder; the executable depends on the rest of it. Onedir was chosen over onefile because it starts instantly — no per-launch extraction to a temp directory — which matters for an app meant to be reopened many times through a work day.

State still saves to `~/.config/percolate/state.json` (or the OS equivalent) regardless of how it was launched.
