"""Slope, overhang-angle and corner checks on generated shapes."""
import math

import pytest
from manifold3d import CrossSection, Manifold

import check
import limits
import surfaces


def box(x0, x1, y0, y1, z0, z1):
    return Manifold.cube([x1 - x0, y1 - y0, z1 - z0]).translate([x0, y0, z0])


def profile(points, length):
    """A solid with this x-z outline, `length` long in y."""
    area = sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(points, points[1:] + points[:1]))
    pts = points if area > 0 else points[::-1]
    return Manifold.extrude(CrossSection([pts]), length).rotate([90, 0, 0])


def kinds(findings):
    return sorted(f.kind for f in findings)


# ---- top surfaces

def roof(angle, width=30.0, length=40.0):
    rise = width * math.tan(math.radians(angle))
    return profile([(0, 0), (width, 0), (width, 4 + rise), (0, 4)], length)


@pytest.mark.parametrize("angle, expected", [
    (19.0, ["slope_too_shallow"]),     # the roof that printed as loose rings
    (34.0, ["slope_too_shallow"]),
    (35.0, []),                        # printed cleanly
    (39.0, []),
])
def test_roof_angle(angle, expected):
    assert kinds(surfaces.run_slopes(roof(angle))) == expected


def test_flat_top_is_fine():
    assert surfaces.run_slopes(box(0, 30, 0, 20, 0, 5)) == []


def cove(radius, length):
    """A wall on a floor with a round fillet of this radius between them."""
    arc = [(radius + radius * math.cos(math.radians(t)), radius + radius * math.sin(math.radians(t)))
           for t in range(270, 179, -10)]
    return profile([(-4, -2), (20, -2), (20, 0)] + arc + [(0, 12), (-4, 12)], length)


def test_a_long_fillet_is_not_a_roof():
    """A 2 mm fillet 400 mm long: a large area of shallow surface, but only about 1 mm wide."""
    assert surfaces.run_slopes(cove(2.0, 400.0)) == []


def test_a_shallow_strip_wider_than_a_fillet_fails():
    assert kinds(surfaces.run_slopes(roof(20.0, width=5.0, length=60.0))) == ["slope_too_shallow"]


def test_a_small_shallow_patch_is_ignored():
    """38 mm2 at 23 degrees printed cleanly on a real part."""
    assert surfaces.run_slopes(roof(23.0, width=3.2, length=12.0)) == []


# ---- undersides

def overhang(angle, run):
    """A wall with a wedge growing out of it: the underside is `angle` from the bed and runs
    out `run` mm."""
    rise = run * math.tan(math.radians(angle))
    return profile([(0, 0), (4, 0), (4, 10), (4 + run, 10 + rise), (4 + run, 12 + rise), (0, 12 + rise)], 20.0)


@pytest.mark.parametrize("angle, run, expected", [
    (38.0, 6.0, ["overhang_too_flat"]),
    (42.0, 6.0, ["overhang_shallow"]),
    (47.0, 6.0, []),
    (45.0, 6.0, []),                    # the design target itself
    (20.0, 1.5, []),                    # no further out than a ledge may reach
])
def test_underside_angle(angle, run, expected):
    assert kinds(surfaces.run_overhangs(overhang(angle, run))) == expected


def test_a_flat_bridge_ceiling_is_left_to_the_layer_check():
    part = box(0, 4, 0, 20, 0, 10) + box(14, 18, 0, 20, 0, 10) + box(0, 18, 0, 20, 10, 12)
    assert surfaces.run_overhangs(part) == []


# ---- corners

def wall_on_floor():
    return box(0, 30, 0, 20, 0, 2) + box(10, 14, 0, 20, 2, 12)


def test_sharp_corner_where_a_wall_meets_a_floor_is_listed():
    found = [f for f in surfaces.run_corners(wall_on_floor()) if f.kind == "sharp_corner_horizontal"]
    assert len(found) == 2 and all(f.value == pytest.approx(20.0, abs=0.1) for f in found)


def test_a_filleted_corner_is_not_listed():
    found = [f for f in surfaces.run_corners(cove(2.0, 40.0)) if f.kind == "sharp_corner_horizontal"]
    assert found == []


def test_edges_shorter_than_the_limit_are_left_out():
    part = box(0, 30, 0, 20, 0, 2) + box(10, 11, 10, 11, 2, 3)          # a 1 mm cube on the floor
    assert [f for f in surfaces.run_corners(part) if f.kind == "sharp_corner_horizontal"] == []


def test_vertical_corners_are_counted_in_one_line():
    part = box(0, 30, 0, 20, 0, 10) - box(10, 20, 5, 21, -1, 11)        # a notch: two vertical inner corners
    found = surfaces.run_corners(part)
    vertical = [f for f in found if f.kind == "sharp_corner_vertical"]
    assert len(vertical) == 1 and vertical[0].area == 2 and vertical[0].value == pytest.approx(20.0, abs=0.1)


def test_corners_never_change_the_verdict():
    results = [{"name": "corner", "status": "pass"}]
    assert limits.KINDS["sharp_corner_horizontal"]["severity"] == "info"
    assert limits.KINDS["sharp_corner_vertical"]["severity"] == "info"
    assert check.decide(results)[0] == "PASS"


def test_a_different_part_gets_its_own_mesh():
    for _ in range(20):
        assert surfaces.run_slopes(roof(39.0)) == []
        assert kinds(surfaces.run_slopes(roof(19.0))) == ["slope_too_shallow"]
