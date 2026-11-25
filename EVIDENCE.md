# Evidence

Where each "(measured)" claim in the skill comes from. A claim without a row here is an estimate, however confident it sounds.

Setup for every row: Bambu Lab X1 Carbon, 0.4 mm nozzle, 0.2 mm layers, PLA, 3 walls. Parts are described generically; the models themselves are not in this repository. No photos yet (see TODOS.md).

## Real prints

Confirmed by the author as printed cleanly, or as failed, and measured afterwards on the exported geometry of the printed parts.

| Rule in the skill | What was printed | Result |
|---|---|---|
| Top surfaces: flat or at least 35 degrees | A roof at 19 degrees (an earlier version of a station roof) | Failed: loose rings with holes between them |
| | A roof at 35 degrees, about 4,400 mm2 | Clean |
| | A roof at 39 degrees, about 1,000 mm2 | Clean |
| Thin wall heads bridge well | Window heads 21.6 mm long in a 1.6 mm wall | Clean |
| | Heads 17.8 mm long in a 1.2 mm wall | Clean |
| | Heads 14.0 mm long in a 2.4 mm wall | Clean |
| Ceilings over 12 mm may sag | A ceiling 12.4 mm long and 11.7 mm wide | Clean. The check warns on it; the 12 mm limit is cautious |
| A ledge may stick out 2 mm | A 2.0 x 1.6 mm column starting beside the top of a bar, a 1.6 mm sideways step, on three parts | Clean |
| Slivers are not floating regions | A roof whose geometry has five outlines 139 mm long and 0.02 mm wide | Clean. No slicer extrudes them |

All 23 parts of the printed set pass the layer check of version 0.1.0.

What the prints do not show:
- No bridge longer than 21.6 mm was printed. The 30 mm hard limit is an estimate.
- No head in a wall thicker than 2.4 mm was printed at more than 10.4 mm. The 3 mm thin-wall limit is an estimate.
- Nothing between 19 and 35 degrees was printed.

## Slicer runs

Reported by the slicer (PrusaSlicer 2.x command line, no supports) while the models were being designed. Taken from the author's notes and the comments in the original check scripts; not re-run for this release.

| Rule in the skill | What the slicer reported |
|---|---|
| Posts of at least 4 mm and at most 8 times as tall as wide | Thinner or taller posts raise "Thin fragile part" |
| Walls carrying the end of a bridge: at least 2 mm | A bridge landing on a wall under 1.6 mm raises "Floating bridge anchors" |
| Slice with 3 walls | With 2 walls some alerts come back |
| A clean slicer run is not proof | The plates with the 19 degree roof above all sliced successfully in OrcaSlicer; the problem only showed on the print |

## Removed

- The original text said a thin wall head "prints fine even at 22 mm (measured)" without saying which part or whether it was a print or a slice. Its source could not be confirmed, so that sentence was replaced by the three printed cases above.
