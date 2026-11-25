---
name: "fdm-print-ready-models"
description: "Use when designing or generating 3D models (STL/3MF) meant for FDM printing, or making an existing model print-safe: design rules, checks, slicer projects and delivery."
---

# FDM print-ready models

Rules learned from designing, slicing and printing a set of wooden-railway station models in one filament colour. The target is a part that prints on a stock 0.4 mm nozzle at 0.2 mm layers, without supports, with no slicer alert, and that still behaves when somebody switches supports on.

**Tested setup.** Every number here comes from one setup: a Bambu Lab X1 Carbon, 0.4 mm nozzle, 0.2 mm layers, PLA. Section 7 says what to re-test on anything else.

**Measured or estimate.** Numbers marked (measured) came from a real slice or print; EVIDENCE.md in the repository lists each one with its source. Treat the rest as starting points and say so when you rely on them.

**Angles.** Every angle in this skill is measured from the bed: 0 degrees is flat, 90 degrees is a vertical wall. "Steeper" means closer to vertical. A slicer's support threshold uses the same reference: at a 30 degree threshold it supports undersides flatter than 30 degrees.

## 1. Workflow

1. Build the model from code (for example Python with manifold3d and trimesh), one script per model, so every rule is a constant or a helper and a fix can be re-run.
2. Keep a shared helper library for the print-safe building blocks (posts, braces, haunches, lettering, connectors). New features use the helpers so they pass from the start.
3. If a model has a multi-colour and a single-colour version, keep one script with a flag, and put what the single-colour build does differently next to the feature it changes.
4. Export every part in its print orientation, flat side on the bed, in millimetres.
5. Run the checks in section 4 on every exported part. Fix the design, not the slicer settings.
6. Render a preview picture and look at it before delivering.
7. Package for the slicer the recipient uses (section 5).

When a script change should not alter the geometry (a refactor), prove it by comparing the volume of old and new parts.

## 2. Design rules

### Sizes
- Nothing narrower than 0.8 mm (two extrusion lines). Thicken lettering strokes to 0.8 mm and open gaps in logos to a printable width. Drop detail that cannot reach it (minute strokes on a 10 mm clock dial).
- Free-standing posts: at least 2.4 mm, at most 12 times as tall as wide. To keep the slicer from calling them fragile: at least 4 mm and at most 8 times as tall as wide (measured). Posts that stand next to removable supports: at least 4 mm.
- Walls that carry the end of a bridge: at least 2 mm thick. A bridge landing on a wall under 1.6 mm raises a "floating bridge anchors" alert (measured).

### Inner corners: fillet them
A sharp inner (concave) corner concentrates stress and is where layers split and parts crack.
- **Horizontal inner corners are mandatory.** Wherever the corner's edge runs horizontally, such as a wall or post meeting a floor, deck, base plate or ledge, add a fillet. Layer lines run along this corner, so it is the weakest place on the part. Use a radius of about 1 to 2 mm, or as large as the detail allows.
- The corner report lists sharp inner edges of 2 mm or longer; shorter ones, such as engraved lettering, are left out.
- **Vertical inner corners are optional but preferred.** Where two walls meet and the edge runs vertically, add a fillet (0.5 to 1 mm is enough) unless it spoils the look or a mating part needs the square corner.
- Under a ceiling or overhang, where the corner faces down, use a 45 degree chamfer or haunch instead of a round fillet, because the first layers of a round fillet there are nearly flat overhang.
- Leave corners square only where another part has to seat against them, and say so in the notes.

### Overhangs and bridges
- Nothing starts in mid-air. Every layer outline rests on the layer below, or at least touches it. An outline that only touches is a sideways step and counts as a ledge.
- Overhangs at 45 degrees or steeper. That is the design target; the overhang check fails undersides flatter than 40 degrees and warns between 40 and 45.
- A flat ledge may stick out 2 mm at most.
- Flat bridges over a wide opening (a ceiling): a ceiling longer than 12 mm may sag, so give wider openings 45 degree haunches in the top corners until the flat part is under 12 mm. A bridge over 30 mm always fails, whatever its shape.
- A window or door head in a thin wall is different: in a wall up to 3 mm thick it prints as wall lines only and bridges well without haunches. Printed cleanly: 22 mm in a 1.6 mm wall and 14 mm in a 2.4 mm wall (measured). The 3 mm limit itself is an estimate.
- Grooves, board undersides and ledges: cut them at 45 degrees, not square.
- Hanging round shapes are teardrops. Jetties sit on a 45 degree chamfer.
- A roof oversailing a gable needs a 45 degree moulding under the verge (the slicer otherwise reports a collapsing overhang).
- Use continuous corbels and edge beams (at least 2.4 mm) under slabs, not thin brackets.
- Do not cross two open arches. Make one direction blind.
- Raised detail on an upright wall (bars, hands, marks) gets a 45 degree foot on its underside.

### Top surfaces
- A top surface is either flat or at least 35 degrees steep. A 19 degree roof printed as loose rings with holes; 35 degrees, 39 degrees and flat printed cleanly (measured on real prints). Nothing between 19 and 35 was tried.
- The fillets required above are shallow surfaces too, but narrow ones. A shallow band narrower than about 3 mm (a fillet of up to 2 mm radius) is not a roof and does not count.
- Shallow ramps that are part of the function are allowed; list them as known exceptions.

### First layer and warping
- A tall part on a small foot gets a wider foot designed in (plinth, root plate, end plate) so it does not need a brim.
- A large flat bottom (150 mm or longer) shrinks as one sheet and lifts at the corners. Cut 45 degree channels into the underside (about 4 mm wide on the bed, 2 mm tall, on a grid of about 42 mm), so the first layers are separate feet. Stop the channels 1.5 mm before any socket, pin hole or thin floor. Thin shells get few or none.
- Do not lay a first layer over fine joints or grooves (0.6 mm paving joints caused long bridges). Fill them under everything that stands on them.

### If supports are switched on
Design for no supports, then check what happens with tree supports on (30 degree threshold).
- Tree supports ignore "don't support bridges": any flat underside about 2 mm or wider gets a support.
- A support that starts on the model inside a slot, cage or closed room cannot be pulled out. In those places nothing may be flat: use full 45 degree vaults, make low gaps solid, let braces meet mid-span.
- Supports are fine where they stand on the build plate, and where fingers or pliers reach them: the check assumes a gap of at least 8 mm leading to the support.

### Consistency
- Place a repeated detail (a clock face, a sign) by rotating it only. Mirroring a copy flips its content. If a whole part is mirrored, build the detail mirrored first.
- Repeated details share one helper and one set of constants.

## 3. Mating parts
- Print a small fit-test piece for every connector before the full part and include it in the delivery.
- Keep clearances in named constants so a failed fit test is a one-line fix.

## 4. Checks

Run them on the exported STL, in print orientation. All of them must pass on every part.

### The command

One command runs every check that is automated and gives one verdict per part:

```
uv run --no-project --python 3.12 --with-requirements "${CLAUDE_SKILL_DIR}/scripts/requirements.txt" "${CLAUDE_SKILL_DIR}/scripts/check.py" part.stl
```

`${CLAUDE_SKILL_DIR}` is the folder this file is in. `uv` builds a private environment with the pinned packages the first time; nothing is installed into the user's own Python. Without `uv`, create a virtual environment, `pip install -r` the same `requirements.txt` and run `check.py` with that Python. If packages are missing the command prints these instructions and stops.

Several parts can be given at once. Each gets a text report and a `<part>.report.json` next to the STL (position of every finding, the limits used, a fingerprint of the file).

### Reading the verdict

| Verdict | Exit code | Meaning |
|---|---|---|
| FAIL | 1 | At least one finding makes the part not print-ready. Fix the design. |
| INCOMPLETE | 2 | The part could not be read, has an implausible size (wrong units), or a check crashed. There is no answer yet. |
| PASS | 0 | Nothing failed. The line also names any warnings and every check that did not run. |

- Repeat the verdict line to the user exactly as printed, including "checks not run". A pass that covers one check is not a print-ready part.
- Never call a part print-ready on INCOMPLETE. Fix the export and run again.
- Warnings are for a person to look at. Say what each one is.
- Findings that are physical defects (too thin, floating, ledge, bridge over the hard limit, thin posts) cannot be waived. Judgment findings can: see below.

### Intended exceptions

Some findings are judgment calls: a shallow ramp that is part of the function, an overhang that is accepted, a support that is easy to pull out. Record each one in `<part>.exceptions.json` next to the STL:

```
{"exceptions": [
  {"kind": "slope_too_shallow", "box": [10, 0, 4, 40, 20, 9], "reason": "Loading ramp: the slope is the function"}
]}
```

- `kind` is the finding's name from the table at the end. Only kinds marked "can be waived" are accepted. A physical defect is refused and still fails.
- `box` is x0, y0, z0, x1, y1, z1 in the part's coordinates. It must contain the finding's x and y and overlap its height; take the position from the report. Keep the box tight: it waives every finding of that kind inside it.
- `reason` says why the feature is meant to be that way. It is printed with the verdict.
- Warnings about the whole part (not on the bed, very small) take an entry without a box.

Do not add an exception to make a part pass. It records a feature that is intended, not a problem that was hard to fix. The verdict then reads "with N waivers" and lists each one with its reason: show that list to the user when you deliver. An entry that matches nothing produces a warning, so stale exceptions surface after a redesign. A file that cannot be read makes the run INCOMPLETE.

### What is automated in this version

The tables at the end of this file are generated from the code and are the authority on limits and on which checks run. In this version the command runs **checks 1, 2, 3, 4 and 6**. Do check 5 by hand, as described, and say in your report that it was manual. The numbers each check uses are in the limits table at the end.

1. **Layer check (automated).** Slices the part layer by layer. Fails features narrower than the minimum width, outlines that start in mid-air, flat ledges beyond the ledge limit, bridges over the hard limit, and bridge decks that stick out past their supports by more than the ledge limit. Warns on long ceilings.
2. **Post check (automated).** Fails an overhang or bridge carried only by thin posts when the posts are tall and the overhang is large, and a free-standing column that is too tall for its width. Smaller overhangs on thin posts warn.
3. **Slope and overhang check (automated).** Fails a top surface that is neither flat nor steep enough, unless it is a narrow fillet band or a small patch. Fails a sloped underside flatter than the overhang limit that runs out further than a ledge may, and warns between that limit and the design target. Flat undersides are bridges and ledges and belong to check 1.
4. **Inner corner check (automated, report only).** Lists the sharp inner corners along horizontal edges and counts the vertical ones. It never fails a part: go through the list. Every horizontal one should have a fillet (or a 45 degree chamfer where it faces down). Say which ones were left sharp and why.
5. **Real slicer (manual for now).** Slice with the PrusaSlicer or OrcaSlicer command line: 0.4 mm nozzle, 0.2 mm layers, no supports, 3 walls. Measure the longest bridge over air and how far any overhang wall is out in the air (2 mm at most), and read the slicer's own alerts. The goal is no alert. With 2 walls some alerts come back (measured).
6. **Support prediction (automated).** Lists every flat underside wide enough to get a support when supports are switched on. On the build plate: information. On the model: a warning. On the model where no gap wide enough for a tool leads to it: fails, because the support cannot be pulled out. It looks sideways only, so a room that is open from above still counts as closed. Patches in places a hand cannot reach are designed away.

Slicer command lines print alerts without a location. To find the cause, slice the part cut off at increasing heights to find where the alert first appears, or build the part with one feature at a time.

PrusaSlicer bridges floating regions silently and OrcaSlicer reports them, so do not rely on one slicer for that. A clean slicer run is not proof either: the plates with the 19 degree roof above sliced successfully, and the problem only showed on the print.

### Known gaps in the automated checks
- Other setups are extrapolated, not measured. `--nozzle 0.6 --layer 0.3` scales the limits that depend on the nozzle and reports their findings as warnings labelled "scaled, not measured". Lengths such as the bridge and ledge limits do not scale and keep their verdict. See section 7.

## 5. Slicer projects and delivery
- Ask which slicer and printer the recipient uses and start from that printer's default profile.
- Deliver one multi-plate project file (3MF) per model, not one file per plate.
- Parts on a plate stand 25 mm apart. At 6 mm, support trees ran into the neighbouring part and OrcaSlicer refused to slice.
- Include the plain STLs as well, a fit-test piece, and a short read-me: plates, orientation, walls, whether a brim is needed, known exceptions.
- MakerWorld accepts print profiles only from a 3MF saved by Bambu Studio with a Bambu Lab printer selected, and expects photos of a real print. An OrcaSlicer 3MF is rejected; plain STLs upload as model files. (As of November 2026.)
- Keep email attachments small: split large deliveries into several zip files.

## 6. Reporting
Say what was checked and what was not printed. Give the verdict line of every part as printed, say which checks were automated and which you did by hand, and state plainly which rules are measured on a real print or slice and which are estimates. List any alert or warning that remains and the feature that causes it, or say that the feature was not pinned down.

## 7. Other printers and materials

This section is guidance, not measurement. Nothing in it was tested on a second printer.

- **Scales with the nozzle:** the minimum width (two extrusion lines, so 1.2 mm on a 0.6 mm nozzle) and the wall thickness up to which a window head prints as wall lines only.
- **Scales with layer height:** how far each layer may step out. Thicker layers make the same overhang angle harder.
- **Depends on material and cooling, so re-test:** bridge lengths, the 35 degree roof limit, the warping channels and the 150 mm length that triggers them. PETG and ABS bridge worse and warp more than PLA; an open-frame printer cools differently from an enclosed one.
- **Does not change:** nothing may start in mid-air, and inner corners still want fillets.

Three short prints re-measure the limits that matter most:
1. A bridge comb: flat bridges of 10, 15, 20, 25 and 30 mm between two walls. The longest clean one replaces the 12 mm ceiling limit.
2. A roof fan: small roofs at 15, 25, 35 and 45 degrees. The shallowest one with a closed top surface replaces 35.
3. A thin-wall strip with a 20 mm window, in walls of 1.6, 2.4 and 3.2 mm. The thickest wall whose head stays straight replaces the 3 mm thin-wall limit.

Until those are printed, say that the limits were measured on a different setup.

## Reference tables

<!-- generated by check.py --update-skill-tables: do not edit by hand -->

### Limits the checks use

For a 0.4 mm nozzle and 0.2 mm layers.

| Limit | Value | Source | Meaning |
|---|---|---|---|
| `min_width` | 0.8 mm | estimate | Narrowest printable feature: two extrusion lines. |
| `max_ledge` | 2 mm | estimate | Farthest a flat underside may stick out past the layer below. |
| `max_bridge` | 30 mm | estimate | Longest bridge over air. Longer fails. |
| `ceiling_warn` | 12 mm | estimate | A bridge wider than a thin wall head warns when longer than this. |
| `thin_wall_head` | 3 mm | estimate | A bridging strip at most this wide is a thin wall head: it prints as wall lines only, which bridge well (22 mm in a 1.6 mm wall and 14 mm in a 2.4 mm wall printed cleanly). Wider strips are ceilings. |
| `column_ratio` | 12 x | estimate | A free-standing column may be at most this many times as tall as wide. |
| `support_min_width` | 2 mm | estimate | A flat underside at least this wide gets a support when supports are switched on. |
| `tool_gap` | 8 mm | estimate | Narrowest gap a support can be pulled out through with pliers or a fingertip. |
| `roof_min_angle` | 35 deg | measured | A top surface is flat or at least this steep. 35 printed cleanly, 19 did not. |
| `fillet_band` | 3 mm | estimate | A shallow band narrower than this is a fillet, not a roof. |
| `overhang_target_angle` | 45 deg | estimate | Design target for undersides. Flatter than this warns. |
| `overhang_fail_angle` | 40 deg | estimate | An underside flatter than this fails, unless it is a ledge or a bridge. |
| `corner_min_edge` | 2 mm | estimate | Sharp inner edges shorter than this are left out of the corner report. |

### What the checks report

| Finding | Severity | Can be waived | Meaning |
|---|---|---|---|
| `thin_feature` | fail | no | Feature narrower than the minimum width |
| `floating_region` | fail | no | Outline that starts in mid-air, touching nothing below it |
| `ledge` | fail | no | Flat underside sticking out too far, held on one side only |
| `bridge_too_long` | fail | no | Bridge longer than the hard limit |
| `ceiling_bridge` | warn | yes | Wide ceiling bridge that may sag |
| `bridge` | info | no | Bridge within limits |
| `overhang_past_supports` | fail | no | Bridge whose deck sticks out past its supports |
| `thin_post_overhang` | fail | no | Overhang carried only by thin posts |
| `thin_post_overhang_small` | warn | yes | Small overhang carried only by thin posts |
| `slender_column` | fail | no | Free-standing column too tall for its width |
| `support_enclosed` | fail | yes | Support would stand on the model where it cannot be pulled out |
| `support_on_model` | warn | yes | Support would stand on the model |
| `support_on_plate` | info | no | Support would stand on the build plate |
| `slope_too_shallow` | fail | yes | Top surface too shallow to print as a closed skin |
| `overhang_too_flat` | fail | yes | Underside too flat to print without support |
| `overhang_shallow` | warn | yes | Underside flatter than the design target |
| `sharp_corner_horizontal` | info | no | Sharp inner corner along a horizontal edge |
| `sharp_corner_vertical` | info | no | Sharp inner corners along vertical edges |
| `exception_refused` | warn | no | Exception refused: this kind of finding cannot be waived |
| `exception_unused` | warn | no | Exception matched no finding |
| `off_bed` | warn | yes | Lowest point of the part is not at z = 0 |
| `small_part` | warn | yes | Part is very small: check the export units |

### Checks in version 0.2.0

| Check | Runs in this version | What it looks at |
|---|---|---|
| layer | yes | Thin features, floating regions, flat ledges and bridges, layer by layer |
| post | yes | Overhangs carried only by thin posts; slender columns |
| slope | yes | Top surfaces that are neither flat nor steep enough |
| overhang angle | yes | Sloped undersides flatter than the overhang limits |
| corner | yes | Sharp inner corners (report only) |
| support | yes | Where supports would go, and whether they can be removed |
| slicer | no, manual for now | A real slicer run: its alerts, bridges and overhang walls |

<!-- end of generated tables -->
