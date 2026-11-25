"""Every number the checks use, in one place.

The checks only measure. This file says what each measurement is compared against, how serious
each kind of finding is, and whether a designer may waive it. SKILL.md's limits table is
generated from LIMITS, so the text and the code cannot state different numbers.

All limits are for the tested setup: 0.4 mm nozzle, 0.2 mm layers, PLA.
`source` is "measured" (seen on a real print or slice) or "estimate" (a starting point).
"""
from dataclasses import dataclass

NOZZLE = 0.4   # mm
LAYER = 0.2    # mm


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
}

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
FLOAT_BOND = NOZZLE / 2        # mm; an outline within this distance of the layer below touches it and
#                           is judged as a ledge (max_ledge), not as floating. Columns that start
#                           beside a bar, sharing an edge, printed cleanly on three real parts
FLOAT_MIN_WIDTH = NOZZLE / 2   # mm; an outline narrower than this is a slicing sliver that no
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
    "thin_feature":    {"severity": "fail", "waivable": False, "limit": "min_width",
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
    "off_bed":         {"severity": "warn", "waivable": True, "limit": None,
                        "text": "Lowest point of the part is not at z = 0"},
    "small_part":      {"severity": "warn", "waivable": True, "limit": None,
                        "text": "Part is very small: check the export units"},
}


def value(name):
    return LIMITS[name].value
