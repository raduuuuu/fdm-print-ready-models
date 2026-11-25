"""Post check, support prediction and the overhang-past-supports test, on generated shapes."""
import pytest
from manifold3d import Manifold

import layers
import limits


def box(x0, x1, y0, y1, z0, z1):
    return Manifold.cube([x1 - x0, y1 - y0, z1 - z0]).translate([x0, y0, z0])


def kinds(findings):
    return sorted(f.kind for f in findings)


# ---- posts

def deck_on_posts(post, height):
    """A 30 x 10 mm deck on two square posts `post` wide and `height` tall, on a base plate."""
    return (box(0, 30, 0, 10, 0, 2) + box(3, 3 + post, 4, 4 + post, 2, 2 + height)
            + box(26 - post, 26, 4, 4 + post, 2, 2 + height) + box(0, 30, 0, 10, 2 + height, 4 + height))


@pytest.mark.parametrize("post, height, expected", [
    (1.0, 12.0, ["thin_post_overhang"]),          # tall thin posts under a large deck: fails
    (1.0, 5.0, ["thin_post_overhang_small"]),     # the same on short posts: warns
    (4.0, 12.0, []),                              # stout posts: nothing
])
def test_overhang_on_posts(post, height, expected):
    assert kinds(layers.run_posts(deck_on_posts(post, height))) == expected


@pytest.mark.parametrize("width, height, expected", [
    (1.0, 20.0, ["slender_column"]),    # 20 times as tall as wide
    (1.0, 10.0, []),                    # too short to be judged
    (2.0, 20.0, []),                    # 10 times: within the limit
])
def test_slender_column(width, height, expected):
    part = box(0, 20, 0, 20, 0, 2) + box(9, 9 + width, 9, 9 + width, 2, 2 + height)
    assert kinds(layers.run_posts(part)) == expected


def test_post_findings_have_a_severity():
    for f in layers.run_posts(deck_on_posts(1.0, 12.0)) + layers.run_posts(deck_on_posts(1.0, 5.0)):
        assert limits.KINDS[f.kind]["severity"] in ("fail", "warn")


# ---- supports

def room(door=0.0):
    """A closed box on a base plate with a flat ceiling; `door` mm wide opening in one wall."""
    part = box(0, 30, 0, 30, 0, 20) - box(5, 25, 5, 25, 2, 16)
    if door:
        part = part - box(-1, 6, 15 - door / 2, 15 + door / 2, 2, 16)
    return part


def support_kinds(part):
    return sorted({f.kind for f in layers.run_supports(part)})


def test_support_under_a_mushroom_stands_on_the_plate():
    part = box(8, 12, 8, 12, 0, 10) + box(0, 20, 0, 20, 10, 12)
    assert support_kinds(part) == ["support_on_plate"]


def test_support_in_a_closed_room_cannot_be_removed():
    assert support_kinds(room()) == ["support_enclosed"]


def test_support_in_a_room_with_a_wide_door_can_be_removed():
    assert support_kinds(room(door=10.0)) == ["support_on_model"]


def test_a_slit_narrower_than_a_tool_does_not_help():
    assert support_kinds(room(door=4.0)) == ["support_enclosed"]


def test_a_narrow_window_head_in_an_outer_wall_can_be_reached():
    """The opening is narrower than a tool, but the support sits at the surface of the wall."""
    part = box(0, 30, 0, 10, 0, 2) + box(0, 30, 4, 6.4, 2, 20) - box(13, 17, 3, 7.4, 6, 14)
    assert support_kinds(part) == ["support_on_model"]


def test_a_sloped_underside_needs_no_support():
    # a 45 degree wedge: each layer steps out by one layer height, well inside the support growth
    from manifold3d import CrossSection
    profile = CrossSection([[(0, 0), (4, 0), (14, 10), (0, 10)]])
    part = Manifold.extrude(profile, 20).rotate([90, 0, 0])
    assert layers.run_supports(part) == []


# ---- a bridge deck that sticks out past its supports

def deck_on_walls(past):
    """Two walls 10 mm long with a deck across the 10 mm gap; the deck runs `past` mm beyond
    the ends of the walls."""
    return (box(0, 4, 0, 10, 0, 10) + box(14, 18, 0, 10, 0, 10) + box(0, 18, 0, 10 + past, 10, 12))


@pytest.mark.parametrize("past, expected", [
    (0.0, []),
    (1.5, []),                              # inside the ledge limit
    (10.0, ["overhang_past_supports"]),     # was passed as a bridge before
])
def test_deck_past_its_supports(past, expected):
    judged = sorted(f.kind for f in layers.run(deck_on_walls(past))
                    if limits.KINDS[f.kind]["severity"] == "fail")
    assert judged == expected


def test_the_old_behaviour_called_it_a_bridge():
    _, over, _ = layers.scan(deck_on_walls(10.0), cantilever=False)
    assert {item[0] for item in over} == {"bridge"}


# ---- the shared slicing pass

def test_slices_are_not_reused_for_a_different_part():
    """Checks share one slicing pass per part. A second part must get its own slices even if
    Python hands it the memory address the first one had."""
    for _ in range(20):
        assert layers.run(box(0, 30, 0, 20, 0, 10)) == []
        assert kinds(layers.run(box(0, 4, 0, 20, 0, 10) + box(0, 9, 0, 20, 10, 12))) == ["ledge"]
