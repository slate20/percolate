# Percolate
<img width="1344" height="837" alt="image" src="https://github.com/user-attachments/assets/86da383e-a572-4168-8311-1a126fd98c17" />

Percolate is a cozy, low-attention coffee farm and roastery that lives in your terminal. Plant beans, let them grow while you go about your day, harvest and roast them into your own named coffee blends, sell them at the market, and watch your farm grow along the way as you progress!

There's no clock to race and nothing to lose by walking away. Nothing decays, nothing punishes you for stepping away, and there's no urgency: check in for a minute between tasks, or come back in three days — either way, it's exactly as ready as when you left it.

## Download and run

Grab the latest build for your OS from the [Releases](../../releases) page — no Python install required. Each release is a zip/tar folder (onedir build); extract it and run the `percolate` executable (`percolate.exe` on Windows) inside.

## Controls

| Key | Action |
| --- | --- |
| `f` | Farm screen |
| `r` | Roast screen |
| `m` | Market screen |
| `h` | Help |
| `q` | Quit (saves automatically) |

Control hints are shown inline, next to whatever they act on — e.g. the selected plot shows `(enter) plant`, a finished roast shows `(c)`, and each screen's tint bar shows `(u) Upgrades`. `u` opens a contextual upgrade shop for that screen (Farm Upgrades vs. Roaster Upgrades). On the Market screen, Tab moves focus between the four buy/sell lists and Enter acts on the highlighted row.

Progress is saved to `~/.config/percolate/state.json` after every action.

## The loop

1. **Buy seeds** at the Market with starting gold.
2. **Plant and grow** them on the Farm screen — each plot runs its own multi-hour timer with ASCII growth stages (seed → sprout → growing → ready).
3. **Harvest and sell raw beans**, or save up for the Roaster upgrade to unlock roasting.
4. **Roast** harvested beans — choose a bean, optional flavor ingredients, and a roast level; Discover curated combinations and you'll earn a bonus over their base value.
5. **Sell roasted product** at the Market for more than raw beans, and reinvest in upgrades (more plots, faster growth, more roast slots, more flavor slots).

Your farmhouse backdrop on the Farm screen evolves automatically as you unlock upgrades.

## Theme

Percolate ships two custom warm coffee-roastery color themes — `percolate-latte` (default, softer/lighter) and `percolate-mocha` (darker, more saturated). Both are dark themes — neither is a bright/light theme. Switch between them, or any other built-in Textual theme, from the command palette (`ctrl+p`).

## Development

### Running from source

```bash
pip install -e .
percolate
```

or, without installing:

```bash
python -m percolate.main
```

### Dev mode

Set `PERCOLATE_DEV=1` before launching to enable testing shortcuts (off by default, no effect on real time):

| Key | Action |
| --- | --- |
| `[` | Skip forward 15 minutes |
| `]` | Skip forward 6 hours |
| `g` | +1000 gold |

These rewind timer start times rather than touching the system clock, so they only affect Percolate's own state.

### Building a standalone executable

```bash
pip install -e ".[build]"
./build.sh      # Linux/WSL/macOS
.\build.ps1     # Windows
```

This is how the [Releases](../../releases) builds are produced. PyInstaller can't cross-compile, so build on whichever OS you want an executable for. The `build.sh`/`build.ps1` wrapper just runs `pyinstaller percolate.spec --distpath dist/<os> --workpath build/<os>` — the `--distpath`/`--workpath` flags keep builds for different platforms from overwriting each other when run against the same checkout (e.g. Windows + WSL), and have to be passed on the command line since PyInstaller reads its output location from internal config set before the spec file runs, not from anything settable inside the spec itself. It produces `dist/<os>/percolate/` — a whole folder (onedir build, not a single file) containing `percolate` (or `percolate.exe` on Windows) plus its bundled data/CSS/runtime. Ship the whole `percolate/` folder; the executable depends on the rest of it.

State still saves to `~/.config/percolate/state.json` (or the OS equivalent) regardless of how it was launched.
