"""Every number the checks use, in one place.

The checks only measure. This file says what each measurement is compared against, how serious
each kind of finding is, and whether a designer may waive it. SKILL.md's limits table is
generated from LIMITS, so the text and the code cannot state different numbers.

All limits are for the tested setup: 0.4 mm nozzle, 0.2 mm layers, PLA.
`source` is "measured" (seen on a real print or slice) or "estimate" (a starting point).
"""
from dataclasses import dataclass, replace

TESTED_NOZZLE = 0.4   # mm; the setup every number below was chosen on
TESTED_LAYER = 0.2    # mm
NOZZLE = TESTED_NOZZLE   # the setup in use; change it with use()
LAYER = TESTED_LAYER


@dataclass(frozen=True)
class Limit:
    value: float
    unit: str
    source: str   # "measured" or "estimate"
    text: str


LIMITS = {
    "min_width": Limit(0.8, "mm", "estimate",
                       "Narrowest printable feature: two extrusion lines."),
    "max_ledge": Limit(2.0, "mm", "estimate",
                       "Farthest a flat underside may stick out past the layer below."),
    "max_bridge": Limit(30.0, "mm", "estimate",
                        "Longest bridge over air. Longer fails."),
    "ceiling_warn": Limit(12.0, "mm", "estimate",
                          "A bridge wider than a thin wall head warns when longer than this."),
    "thin_wall_head": Limit(3.0, "mm", "estimate",
                            "A bridging strip at most this wide is a thin wall head: it prints as "
                            "wall lines only, which bridge well (22 mm in a 1.6 mm wall and 14 mm "
                            "in a 2.4 mm wall printed cleanly). Wider strips are ceilings."),
    "column_ratio": Limit(12.0, "x", "estimate",
                          "A free-standing column may be at most this many times as tall as wide."),
    "support_min_width": Limit(2.0, "mm", "estimate",
                               "A flat underside at least this wide gets a support when supports "
                               "are switched on."),
    "tool_gap": Limit(8.0, "mm", "estimate",
                      "Narrowest gap a support can be pulled out through with pliers or a fingertip."),
    "roof_min_angle": Limit(35.0, "deg", "measured",
                            "A top surface is flat or at least this steep. 35 printed cleanly, 19 did not."),
    "fillet_band": Limit(3.0, "mm", "estimate",
                         "A shallow band narrower than this is a fillet, not a roof."),
    "overhang_target_angle": Limit(45.0, "deg", "estimate",
                                   "Design target for undersides. Flatter than this warns."),
    "overhang_fail_angle": Limit(40.0, "deg", "estimate",
                                 "An underside flatter than this fails, unless it is a ledge or a bridge."),
    "corner_min_edge": Limit(2.0, "mm", "estimate",
                             "Sharp inner edges shorter than this are left out of the corner report."),
}

# Surface checks.
FLAT_ANGLE = 3.0          # degrees; flatter than this is flat
ANGLE_MARGIN = 0.5        # degrees; a surface modelled at exactly a limit must not fail on rounding
SURFACE_MIN_AREA = 1.0    # mm2; smaller regions are ignored
SLOPE_MIN_AREA = 150.0    # mm2; a shallow top surface smaller than this is not reported. The value
#                           of the original slope check; two 38 mm2 patches at 23 degrees printed cleanly
RUN_TOL = 0.25            # mm; how far past max_ledge a sloped underside must run to be reported.
#                           The run is estimated from area and outline, so a 2.0 mm step reads 2.0x
NARROW_UNDERSIDE_MIN_AREA = 6.0   # mm2; a sloped underside too narrow for the overhang-angle rule is
#                           still reported when it runs out past max_ledge and is at least this
#                           large. Narrow ones up to 5.8 mm2 printed cleanly on three models
SHARP_ANGLE = 60.0        # degrees between two faces at an inner edge for it to count as sharp
CORNER_LIST_MAX = 200     # the corner report lists at most this many horizontal corners, longest first

# Post check: what counts as a thin post, and when an overhang resting on thin posts is serious.
POST_THIN_WIDTH = 1.2     # mm; a piece narrower than this everywhere is a thin post (2-3 lines)
POST_THIN_AREA = 12.0     # mm2; or one smaller than this in section
COLUMN_MIN_HEIGHT = 15.0  # mm; shorter columns are not judged for slenderness
POST_OVERHANG_AREA = 4.0  # mm2; smaller overhang islands on thin posts are ignored
POST_FAIL_HEIGHT = 8.0    # mm; an overhang on thin posts fails when the posts are taller than this
POST_FAIL_AREA = 20.0     # mm2; and the overhang is larger than this. Otherwise it warns.
POST_WIDE_AREA = 200.0    # mm2; pieces this large are never thin, so their width is not measured

# Support prediction.
SUPPORT_GROW = 0.35       # mm the layer below is grown by before looking for unsupported area
SUPPORT_MIN_AREA = 1.0    # mm2; smaller patches are ignored
SUPPORT_BASE_SHARE = 0.3  # a lower layer is the patch's base when it covers this share of it

# Slicer check.
SLICER_TIMEOUT = 600      # seconds a slicer run may take
SLICER_MIN_RUN = 3.0      # mm; overhang-wall runs shorter than this are ignored (letter tips)
SLICER_MIN_LINE = 2.0     # mm; bridging lines and spans shorter than this are ignored
SLICER_LEAN = 0.5         # mm; a bridging line this close to the layer below leans on its neighbour
SLICER_END_HELD = 1.0     # mm; an overhang wall whose ends are this close to the layer below is held there
SLICER_WALL_MIN = 0.6     # mm; an overhang wall must be at least this far out to be measured

# Internal tolerances of the layer scan. None of these is a design rule.
WIDTH_TOL = 0.1           # mm added to thin_wall_head, so a wall modelled at exactly the limit counts
STEP_FACTOR = 1.2         # layer outline is grown by STEP_FACTOR * LAYER before overhangs are
#                           measured. This only removes slivers; it is NOT an overhang-angle limit.
MIN_ISLAND_AREA = 0.25    # mm2 per layer; smaller overhang specks are ignored
MIN_THIN_AREA = 0.4       # mm2 per layer; smaller thin specks (letter tips) are ignored
MIN_THIN_TOTAL = 1.0      # mm2 summed over a thin feature
MIN_THIN_HEIGHT = 0.6     # mm; a thin feature must persist this high to be reported
BRIDGE_HELD = 0.5         # share of an overhang's rim resting on the layer below that makes it a
#                           bridge even with one contact (a pocket ceiling held all round)
FLOAT_MIN_AREA = 0.05     # mm2; smaller outlines are ignored by the floating-region test
FLOAT_SHRINK = 0.03       # mm the layer below is shrunk by: touching along an edge is not support
FLOAT_OVERLAP = 0.02      # an outline resting on less than this share of its area is floating
FLOAT_MIN_OVERLAP = 0.01  # mm2; or on less than this much area
FLOAT_BOND = 0.2          # mm (half a nozzle width); an outline within this distance of the layer below touches it and
#                           is judged as a ledge (max_ledge), not as floating. Columns that start
#                           beside a bar, sharing an edge, printed cleanly on three real parts
FLOAT_MIN_WIDTH = 0.2     # mm (half a nozzle width); an outline narrower than this is a slicing sliver that no
#                           slicer extrudes, so it cannot float (0.02 mm wide slivers on a roof
#                           that printed cleanly were reported before this floor existed)

# Part sanity (the runner checks these before any check runs).
MIN_PART_SIZE = 2.0       # mm; a part whose largest side is smaller was almost certainly exported
#                           in metres. The run stops as INCOMPLETE.
MAX_PART_SIZE = 2000.0    # mm; larger than any desktop printer: wrong units. INCOMPLETE.
SMALL_PART_SIZE = 5.0     # mm; smaller than this warns (an inch export of a 100 mm part reads 3.9)
BED_TOL = 0.01            # mm; a lowest point further from z = 0 than this warns

# How serious each kind of finding is, whether it may be waived, and what it is compared with.
# fail = the part is not print-ready; warn = look at it; info = reported, not judged.
KINDS = {
    "thin_feature":    {"severity": "fail", "waivable": False, "limit": "min_width", "scales": True,
                        "text": "Feature narrower than the minimum width"},
    "floating_region": {"severity": "fail", "waivable": False, "limit": None,
                        "text": "Outline that starts in mid-air, touching nothing below it"},
    "ledge":           {"severity": "fail", "waivable": False, "limit": "max_ledge",
                        "text": "Flat underside sticking out too far, held on one side only"},
    "bridge_too_long": {"severity": "fail", "waivable": False, "limit": "max_bridge",
                        "text": "Bridge longer than the hard limit"},
    "ceiling_bridge":  {"severity": "warn", "waivable": True, "limit": "ceiling_warn",
                        "text": "Wide ceiling bridge that may sag"},
    "bridge":          {"severity": "info", "waivable": False, "limit": "max_bridge",
                        "text": "Bridge within limits"},
    "overhang_past_supports": {"severity": "fail", "waivable": False, "limit": "max_ledge",
                        "text": "Bridge whose deck sticks out past its supports"},
    "thin_post_overhang": {"severity": "fail", "waivable": False, "limit": None, "scales": True,
                        "text": "Overhang carried only by thin posts"},
    "thin_post_overhang_small": {"severity": "warn", "waivable": True, "limit": None,
                        "text": "Small overhang carried only by thin posts"},
    "slender_column":  {"severity": "fail", "waivable": False, "limit": "column_ratio", "scales": True,
                        "text": "Free-standing column too tall for its width"},
    "support_enclosed": {"severity": "fail", "waivable": True, "limit": "tool_gap",
                        "text": "Support would stand on the model where it cannot be pulled out"},
    "support_on_model": {"severity": "warn", "waivable": True, "limit": "support_min_width",
                        "text": "Support would stand on the model"},
    "support_on_plate": {"severity": "info", "waivable": False, "limit": "support_min_width",
                        "text": "Support would stand on the build plate"},
    "slope_too_shallow": {"severity": "fail", "waivable": True, "limit": "roof_min_angle",
                        "text": "Top surface too shallow to print as a closed skin"},
    "overhang_too_flat": {"severity": "fail", "waivable": True, "limit": "overhang_fail_angle",
                        "text": "Underside too flat to print without support"},
    "overhang_shallow": {"severity": "warn", "waivable": True, "limit": "overhang_target_angle",
                        "text": "Underside flatter than the design target"},
    "overhang_narrow": {"severity": "warn", "waivable": True, "limit": "overhang_fail_angle",
                        "text": "Narrow sloped underside that runs out far"},
    "sharp_corner_horizontal": {"severity": "info", "waivable": False, "limit": "corner_min_edge",
                        "text": "Sharp inner corner along a horizontal edge"},
    "sharp_corner_vertical": {"severity": "info", "waivable": False, "limit": "corner_min_edge",
                        "text": "Sharp inner corners along vertical edges"},
    "slicer_bridge_too_long": {"severity": "fail", "waivable": False, "limit": "max_bridge",
                        "text": "Slicer: bridging line over air longer than the hard limit"},
    "slicer_wall_in_air": {"severity": "fail", "waivable": False, "limit": "max_ledge",
                        "text": "Slicer: overhang wall printed too far out in the air"},
    "slicer_alert":    {"severity": "warn", "waivable": True, "limit": None,
                        "text": "Slicer alert"},
    "slicer_untested_version": {"severity": "warn", "waivable": True, "limit": None,
                        "text": "Slicer version this check was not tested with"},
    "slicer_alerts_not_read": {"severity": "info", "waivable": False, "limit": None,
                        "text": "This slicer's own alerts are not read; only its bridges and walls are measured"},
    "slicer_longest_bridge": {"severity": "info", "waivable": False, "limit": "max_bridge",
                        "text": "Slicer: longest bridging line over air"},
    "exception_refused": {"severity": "warn", "waivable": False, "limit": None,
                        "text": "Exception refused: this kind of finding cannot be waived"},
    "exception_unused": {"severity": "warn", "waivable": False, "limit": None,
                        "text": "Exception matched no finding"},
    "off_bed":         {"severity": "warn", "waivable": True, "limit": None,
                        "text": "Lowest point of the part is not at z = 0"},
    "small_part":      {"severity": "warn", "waivable": True, "limit": None,
                        "text": "Part is very small: check the export units"},
}


# How each number changes on another nozzle or layer height. "nozzle": in proportion to the
# nozzle width. "layer": in proportion to the layer height. "none": it does not change, and a
# finding against it keeps its verdict on any setup. Every number in this file is listed.
SCALING = {
    "min_width": "nozzle", "thin_wall_head": "nozzle",
    "max_ledge": "none", "max_bridge": "none", "ceiling_warn": "none", "column_ratio": "none",
    "support_min_width": "none", "tool_gap": "none",
    "roof_min_angle": "none", "fillet_band": "none", "overhang_target_angle": "none",
    "overhang_fail_angle": "none", "corner_min_edge": "none",
    "FLAT_ANGLE": "none", "ANGLE_MARGIN": "none", "SURFACE_MIN_AREA": "none", "SLOPE_MIN_AREA": "none", "RUN_TOL": "none", "SHARP_ANGLE": "none",
    "NARROW_UNDERSIDE_MIN_AREA": "none",
    "CORNER_LIST_MAX": "none",
    "SLICER_TIMEOUT": "none", "SLICER_MIN_RUN": "none", "SLICER_MIN_LINE": "none", "SLICER_LEAN": "none",
    "SLICER_END_HELD": "none", "SLICER_WALL_MIN": "none",
    "POST_THIN_WIDTH": "nozzle", "FLOAT_BOND": "nozzle", "FLOAT_MIN_WIDTH": "nozzle",
    "SUPPORT_GROW": "layer",        # 0.35 mm is one 0.2 mm layer at a 30 degree support threshold
    "MIN_THIN_HEIGHT": "layer",     # three layers
    "POST_THIN_AREA": "none", "COLUMN_MIN_HEIGHT": "none", "POST_OVERHANG_AREA": "none",
    "POST_FAIL_HEIGHT": "none", "POST_FAIL_AREA": "none", "POST_WIDE_AREA": "none",
    "SUPPORT_MIN_AREA": "none", "SUPPORT_BASE_SHARE": "none", "WIDTH_TOL": "none",
    "STEP_FACTOR": "none",          # a factor of the layer height already
    "MIN_ISLAND_AREA": "none", "MIN_THIN_AREA": "none", "MIN_THIN_TOTAL": "none",
    "BRIDGE_HELD": "none", "FLOAT_MIN_AREA": "none", "FLOAT_SHRINK": "none",
    "FLOAT_OVERLAP": "none", "FLOAT_MIN_OVERLAP": "none",
    "MIN_PART_SIZE": "none", "MAX_PART_SIZE": "none", "SMALL_PART_SIZE": "none", "BED_TOL": "none",
}
_TESTED_LIMITS = dict(LIMITS)
_TESTED_CONSTANTS = {n: globals()[n] for n in SCALING if n not in LIMITS}


def use(nozzle=TESTED_NOZZLE, layer=TESTED_LAYER):
    """Switch every number to another nozzle width and layer height. use() returns to the
    tested setup. Scaled numbers are reasoning, not measurement."""
    g = globals()
    g["NOZZLE"], g["LAYER"] = nozzle, layer
    for name, how in SCALING.items():
        if how == "none":           # unchanged, and it keeps its type (some are counts)
            if name not in _TESTED_LIMITS:
                g[name] = _TESTED_CONSTANTS[name]
            continue
        f = nozzle / TESTED_NOZZLE if how == "nozzle" else layer / TESTED_LAYER
        if name in _TESTED_LIMITS:
            LIMITS[name] = replace(_TESTED_LIMITS[name], value=round(_TESTED_LIMITS[name].value * f, 3))
        else:
            g[name] = _TESTED_CONSTANTS[name] * f


def tested():
    return NOZZLE == TESTED_NOZZLE and LAYER == TESTED_LAYER


def kind_is_scaled(kind):
    """True when a finding of this kind rests on a number that was scaled for the setup in use."""
    return bool(KINDS[kind].get("scales")) and NOZZLE != TESTED_NOZZLE


def value(name):
    return LIMITS[name].value
