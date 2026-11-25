# Validation

How the checks were tried on real parts, and what that does and does not show. The parts are private models and are not in this repository; this file records the method and the numbers. Last run: version 0.2.0, 2026-11-25.

## Reference sets

| Set | Parts | What they are |
|---|---|---|
| Printed | 23 | Every part of three models that the author printed cleanly. All must pass |
| Current | 3 | Newer exports of two of those models |
| Older | 46 | An earlier design generation of seven models, plus one model that was never printed. It contains geometry that was later redesigned |
| Roof failure | 46 | The generation whose 19 degree roof printed as loose rings, extracted from its print plates |

118 parts in all. Setup: 0.4 mm nozzle, 0.2 mm layers.

## Result with the six automated checks

| Set | Pass | Fail | Crashed |
|---|---|---|---|
| Printed | 23 | 0 | 0 |
| Current | 3 | 0 | 0 |
| Older | 37 | 9 | 0 |
| Roof failure | 39 | 7 | 0 |

- **Printed set:** no failure. It carries 33 warnings: 22 supports that would stand on the model (two parts), 10 small overhangs on thin posts (three parts) and one ceiling 12.4 mm long.
- **Roof failure set:** the 19 degree roof fails the slope check, which is the defect this set exists for. Five more parts fail it with roofs between 11 and 32 degrees. One part also fails with three thin features, and one with an underside at 7.5 degrees.
- **Older set:** the same six roofs fail. One part fails with a 32.6 mm bridge and four outlines that start in mid-air, one with a detached strip, and two with undersides that are too flat. None of these exists in the printed versions of those parts.

## Agreement with the original scripts

The layer, post, support and slope checks were ported from the scripts the models were designed with. On the older set, the port against the originals:

| Check | Original | Version 0.2 | Difference |
|---|---|---|---|
| Thin features and overhangs | — | identical at the original limits | none; compared on 49 parts |
| Bridges | 185 | 175 within limits, 9 ceiling warnings, 1 failure | the 30 mm limit (was 36) and the ceiling warning are new rules |
| Outlines starting in mid-air | 69 | 5 | 64 dropped on purpose, see below |
| Overhangs on thin posts, slender columns | 36 | 36 | none; identical findings on all 72 parts compared |
| Support patches | 142 (60 on the plate) | 142 (60 on the plate, 82 on the model, 0 enclosed) | none; same patches, area within 3 percent |
| Parts with a shallow roof | 7 | 6 | the seventh had only long fillet coves, which are no longer counted |

The 64 dropped "mid-air" outlines are two deliberate changes, each made after a printed part failed on it:
- outlines narrower than half a nozzle width, which no slicer extrudes (a roof that printed cleanly had five, each 139 mm long and 0.02 mm wide);
- outlines that touch the layer below along an edge, which are sideways steps and fall under the 2 mm ledge rule (three printed parts have a 1.6 mm step of this kind).

## Checks with no original to compare against

- **Overhang angle.** No finding on the printed set. Five failures on two older parts. Four of them are on the model that was never printed, at 11.8 degrees running out about 2.65 mm; the author's slicer run of that model raised no alert, so it is open which is right.
- **Bridge deck past its supports, enclosed supports, overhang on tall thin posts, slender column.** No real part triggers any of these. They are exercised by generated test shapes only.
- **Corner report.** It lists 2,013 sharp horizontal inner corners across 18 of the 23 printed parts. Those parts printed cleanly, so a long list is normal and is not a sign of a defect by itself. The report never changes the verdict.

## What this does not show

- Only three of the seven models were printed in their current form. The other four are known only from the older generation.
- The failure paths listed above have never met a real defect.
- Bridge, ledge, thin-wall and overhang thresholds are estimates (see EVIDENCE.md for what was measured).
- Everything comes from one printer, one nozzle and one material.
- The slicer check is not automated yet, and a clean slicer run would not have caught the 19 degree roof either.

## Speed

All 118 parts ran in 167 seconds on a laptop, the slowest part in 13.8 seconds.
