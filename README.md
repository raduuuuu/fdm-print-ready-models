# FDM print-ready models

An agent skill for designing 3D models that print on an FDM printer without supports and without slicer alerts, and a command that checks an exported part against the rules.

It is for people who build parts in code with an AI agent (Python with manifold3d or trimesh, for example) and print them on a 0.4 mm nozzle. It is not a CAD tutorial and it does not control a printer.

The rules come from designing, slicing and printing a set of wooden-railway station models in one filament colour. Each number in the skill says whether it was measured on a real print or slice, or is an estimate. [EVIDENCE.md](EVIDENCE.md) lists the measured ones with their source. [VALIDATION.md](VALIDATION.md) records how the checks did on 118 real parts.

## What you get

- **The skill** ([SKILL.md](skills/fdm-print-ready-models/SKILL.md)): design rules for sizes, inner corners, overhangs and bridges, top surfaces, the first layer, and what happens when someone switches supports on. Plus how to check, package and report.
- **The check command**: one command per part, one verdict.

```
part.stl
  warn  Wide ceiling bridge that may sag: span 12.4 mm, 11.72 mm wide (limit 12.0 mm)  at x 127.6, y 85.0, z 45.1
  info  6 bridges within limits (longest 17.8 mm); --verbose lists them
VERDICT: PASS (layer check only; with 1 warning; checks not run: post, slope, overhang angle, corner, support, slicer)
```

## Status: version 0.1.0

The skill describes six checks. This version automates the first one, the layer check: features too thin to print, outlines that start in mid-air, flat ledges, and bridges. The other five are done by hand as the skill describes, and every verdict line names them as not run.

Planned: the post, slope, overhang-angle, corner and support checks in 0.2, and a real slicer run (PrusaSlicer and OrcaSlicer) in 0.3.

**Tested setup.** Bambu Lab X1 Carbon, 0.4 mm nozzle, 0.2 mm layers, PLA. The command takes `--nozzle` and `--layer` for other setups; limits that depend on the nozzle are then scaled and reported as warnings, because they were not measured. Section 7 of the skill says what to re-test on other printers and materials; that section is guidance, not measurement.

**Platforms.** The checks are tested on macOS and Linux. Windows is untested.

**Known gap.** An overhang held on two sides is treated as a bridge even when part of it sticks out past those supports. A slicer run catches that case; the layer check does not yet.

## Install

### Claude Code plugin

```
/plugin marketplace add raduuuuu/fdm-print-ready-models
/plugin install fdm-print-ready-models@fdm-print-ready-models
```

Or from a shell: `claude plugin marketplace add raduuuuu/fdm-print-ready-models`, then `claude plugin install fdm-print-ready-models@fdm-print-ready-models`.

### By hand

Copy the folder `skills/fdm-print-ready-models/` into `~/.claude/skills/`. Other agents that read `SKILL.md` files can use the same folder; the check command is plain Python and does not depend on Claude Code.

## Run the checks yourself

The part must be an STL in print orientation: flat side on the bed, z up, sizes in millimetres.

With [uv](https://docs.astral.sh/uv/), from the repository root:

```
uv run --no-project --python 3.12 --with-requirements skills/fdm-print-ready-models/scripts/requirements.txt skills/fdm-print-ready-models/scripts/check.py part.stl
```

`uv` builds a private environment with the pinned packages (numpy, trimesh, manifold3d) the first time. Nothing is installed into your own Python.

Without uv:

```
python3 -m venv .venv
.venv/bin/pip install -r skills/fdm-print-ready-models/scripts/requirements.txt
.venv/bin/python skills/fdm-print-ready-models/scripts/check.py part.stl
```

Try it on the sample part: `tests/fixtures/known_good.stl`.

| Verdict | Exit code | Meaning |
|---|---|---|
| FAIL | 1 | At least one finding makes the part not print-ready |
| INCOMPLETE | 2 | The part could not be read, has an implausible size, or a check crashed |
| PASS | 0 | Nothing failed. The line names any warnings and every check that did not run |

Each part also gets `<part>.report.json` next to the STL: the position of every finding, the limits used, package versions and a fingerprint of the file. `--no-report` skips it, `--out` chooses the path, `--verbose` lists the findings that are information only.

## Troubleshooting

| What you see | What to do |
|---|---|
| `Missing Python packages` | Use the uv command above, or the three lines without uv. The message prints both |
| `could not check this part: mesh problem` | The STL is not a closed solid. Repair it in your CAD tool or slicer and export again |
| `implausible size … check the export units` | The part was exported in metres or inches. Export in millimetres |
| `Part is very small: check the export units` | Same cause, usually an inch export. Ignore it if the part really is under 5 mm |
| Many failures on a part that looks fine | The part is probably not in print orientation. Export it standing on the bed the way it will print |
| `Lowest point of the part is not at z = 0` | The part was exported at its assembled height. The checks still run; the warning is a reminder |
| `layer check only; checks not run: …` | Expected in 0.1.0. A pass covers the layer check and nothing else |

If a result looks wrong, open an issue and attach the `report.json`.

## Development

```
uv run --no-project --python 3.12 --with-requirements requirements-dev.txt pytest
```

- `scripts/limits.py` holds every number, how serious each kind of finding is and whether it may be waived. The checks only measure; `check.py` owns the verdict.
- The tables at the end of SKILL.md are generated: `check.py --update-skill-tables`. A test fails when the text and the code state different numbers.
- Do not add station models, logos or brand names to this repository. The tests scan for them and for personal folder paths.

## Licence

MIT. See [LICENSE](LICENSE).
