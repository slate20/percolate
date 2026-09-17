# Percolate

A cozy, low-attention terminal coffee farm & roastery, built with [Textual](https://textual.textualize.io/).

See [`docs/overview.md`](docs/overview.md) for the design philosophy and architecture.

## Running

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
| `q` | Quit (saves automatically) |

Control hints are shown inline, next to whatever they act on, rather than in a footer — e.g. the selected plot shows `(enter) plant`, a finished roast shows `(c)`, and each screen's tint bar shows `(u) Upgrades`. `u` opens a contextual upgrade shop for that screen (Farm Upgrades vs. Roaster Upgrades) instead of a separate screen. On the Market screen, Tab moves focus between the four buy/sell lists and Enter acts on the highlighted row.

State is saved to `~/.config/percolate/state.json` after every action.

## Theme

Percolate ships two custom warm coffee-roastery color themes — `percolate-latte` (default, softer/lighter) and `percolate-mocha` (darker, more saturated). Both are dark themes — neither is a bright/light theme. Switch between them, or any other built-in Textual theme, from the command palette (`ctrl+p`).

## Building a standalone executable

Percolate can be packaged into a self-contained folder with [PyInstaller](https://pyinstaller.org) — no Python install needed to run it afterward. PyInstaller can't cross-compile, so build on whichever OS you want an executable for (build on Windows for a `.exe`, on macOS/Linux for their native binary):

```bash
pip install -e ".[build]"
pyinstaller percolate.spec
```

This produces `dist/percolate/` — an entire folder (onedir build, not a single file) containing `percolate` (or `percolate.exe` on Windows) plus its bundled data/CSS/runtime. Ship the whole folder; the executable depends on the rest of it. Onedir was chosen over onefile because it starts instantly — no per-launch extraction to a temp directory — which matters for an app meant to be reopened many times through a work day.

State still saves to `~/.config/percolate/state.json` (or the OS equivalent) regardless of how it was launched.
