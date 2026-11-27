# FDM print-ready models

An agent skill for designing 3D models that print on an FDM printer without supports and without slicer alerts, and a command that checks an exported part against the rules.

It is for people who build parts in code with an AI agent (Python with manifold3d or trimesh, for example) and print them on a 0.4 mm nozzle. It is not a CAD tutorial and it does not control a printer.

The rules come from designing, slicing and printing a set of wooden-railway station models in one filament colour. Each number in the skill says whether it was measured on a real print or slice, or is an estimate. [EVIDENCE.md](EVIDENCE.md) lists the measured ones with their source. [VALIDATION.md](VALIDATION.md) records how the checks did on 118 real parts.

Pieces designed this way are used in [ChooChooCAD](https://woodentrain.world), a free planner that checks whether a wooden railway layout will close. Its [guide for contributors](https://github.com/raduuuuu/ChooChooCAD/blob/main/CONTRIBUTING.md#design-a-piece-to-print) says how a printed piece gets into its library.

## What you get

- **The skill** ([SKILL.md](skills/fdm-print-ready-models/SKILL.md)): design rules for sizes, inner corners, overhangs and bridges, top surfaces, the first layer, and what happens when someone switches supports on. Also mating parts: when glue is acceptable, what must hold up a connector on a raised level, and assembly instructions for every part. Plus how to check, package and report.
- **The check command**: one command per part, one verdict.

```
part.stl
  warn  Wide ceiling bridge that may sag: span 12.4 mm, 11.72 mm wide (limit 12.0 mm)  at x 127.6, y 85.0, z 45.1
  warn  Support would stand on the model: area 26.5 mm2, 8.2 mm above the surface it would stand on  at x 43.0, y 6.2, z 16.1
  info  6 bridges within limits (longest 17.8 mm); --verbose lists them
VERDICT: PASS (layer, post, slope, overhang angle, corner and support checks only; with 2 warnings; geometry only: the slicer check did not run; still to do by hand: raised ports, assembly instructions)
```

## Status: version 0.3.0

The command runs these seven checks (the skill counts slope and overhang angle as one). Two more, raised ports and assembly instructions, are done by hand, and every passing verdict names them:

| Check | What it finds |
|---|---|
| Layer | Features too thin to print, outlines that start in mid-air, flat ledges, bridges that are too long, bridge decks that stick out past their supports |
| Post | Overhangs carried only by thin posts; columns too tall for their width |
| Slope | Top surfaces too shallow to print as a closed skin |
| Overhang angle | Sloped undersides that are too flat |
| Corner | Sharp inner corners. A report for a person to read; it never fails a part |
| Support | Where supports would go if someone switches them on, and where one could not be pulled out |
| Slicer | A real slicer run: its longest bridging line over air, overhang walls printed in the air, and PrusaSlicer's own alerts |

The slicer check runs when PrusaSlicer is installed. OrcaSlicer works too, given three preset files exported from it. Without a slicer the verdict says "geometry only".

Findings that are judgment calls, such as a ramp that is meant to be shallow, can be recorded as intended in `<part>.exceptions.json`; the skill explains the format. Physical defects cannot be waived.

**Tested setup.** Bambu Lab X1 Carbon, 0.4 mm nozzle, 0.2 mm layers, PLA. The command takes `--nozzle` and `--layer` for other setups; limits that depend on the nozzle are then scaled and reported as warnings, because they were not measured. Section 7 of the skill says what to re-test on other printers and materials; that section is guidance, not measurement.

**Platforms.** The checks are tested on macOS and Linux. Windows is untested.

**What has and has not met a real part.** [VALIDATION.md](VALIDATION.md) has the detail. In short: every part of three printed models passes, and the roof that printed badly fails. Several failure paths have only been exercised by generated test shapes.

A worked example is in [examples/shelter](examples/shelter/).

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
uv run --no-project --python 3.12 --with-requirements skills/fdm-print-ready-models/scripts/requirements-slicer.txt skills/fdm-print-ready-models/scripts/check.py part.stl
```

`uv` builds a private environment with the pinned packages (numpy, trimesh, manifold3d, and shapely for the slicer check) the first time. Nothing is installed into your own Python.

Without uv:

```
python3 -m venv .venv
.venv/bin/pip install -r skills/fdm-print-ready-models/scripts/requirements-slicer.txt
.venv/bin/python skills/fdm-print-ready-models/scripts/check.py part.stl
```

Try it on the worked example: `examples/shelter/shelter.stl`.

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
| `geometry only: the slicer check did not run` | No slicer was found, or OrcaSlicer was found without preset files. Install PrusaSlicer, or pass `--orca-presets` |
| `the slicer exited with code …`, `could not confirm the slice ran` | The slicer itself failed. The run is INCOMPLETE; the message carries the slicer's last lines |
| `problem with the exceptions file` | The message says which entry and why. Fix the file; until then the run is INCOMPLETE |

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
