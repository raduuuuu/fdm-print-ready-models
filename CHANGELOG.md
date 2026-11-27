# Changelog

## Unreleased

Skill text only; the check command is unchanged.

- Glue is allowed where a joint without it would cost printability or strength. A glued joint keeps a locating feature and is named in the assembly instructions.
- Connectors on a raised level: a port above the table needs something to hold up the end of the piece that plugs in. A check done by hand on every model.
- Assembly instructions for every part that joins another, or the line "no assembly". Also checked by hand.
- Fixing a flaw: change the part that has it instead of adding a part, propose the smallest change, check before and after.
- A female socket on a raised level gets a floor built into the part as the first choice.
- A changed feature gets a close-up preview, before and after.

## 0.3.0 (2026-11-25)

All six checks are automated.

- Slicer check: runs PrusaSlicer or OrcaSlicer on the part, fails a bridging line over air longer than 30 mm or an overhang wall more than 2 mm out in the air, and reports PrusaSlicer's own alerts as warnings.
- Without a slicer the verdict says "geometry only".
- The check command is now given with `requirements-slicer.txt`, which adds the package the slicer check needs.

## 0.2.0 (2026-11-25)

Six of the seven checks are now automated. Only the slicer run is still done by hand.

- Post check: overhangs carried only by thin posts, and columns too tall for their width.
- Support prediction: where supports would go, and a failure where one could not be pulled out.
- The layer check now fails a bridge deck that sticks out past its supports.
- `--nozzle` and `--layer` for other setups: scaled limits, reported as warnings.
- Slope check: top surfaces too shallow to print, ignoring fillet bands and small patches.
- Overhang-angle check: sloped undersides flatter than 40 degrees fail, 40 to 45 warn.
- Corner report: sharp inner corners, listed for a person to judge.
- A worked example: `examples/shelter/`, a generator, its STL, a picture and its report.
- VALIDATION.md: how the checks did on 118 real parts.
- Intended exceptions: `<part>.exceptions.json` waives judgment findings, each with a reason shown on the verdict. Physical defects cannot be waived.

## 0.1.0 (2026-11-25)

First public version.

- The skill text: one bridge rule, the tested setup, angles measured from the bed, narrow fillets are not shallow roofs, a dated note on MakerWorld, and guidance for other printers and materials.
- `check.py`: one command, a verdict per part (FAIL, INCOMPLETE or PASS with exit codes 1, 2 and 0) and a JSON report.
- The layer check: features under 0.8 mm, outlines that start in mid-air, flat ledges over 2 mm, bridges over 30 mm, and a warning on ceilings over 12 mm.
- Limits in one file, with tables in SKILL.md generated from it.
- Installs as a Claude Code plugin.

Not yet automated: the post, slope, overhang-angle, corner, support and slicer checks.
