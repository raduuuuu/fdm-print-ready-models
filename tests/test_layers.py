"""Layer checks on small generated shapes, one limit at a time.

Every shape is built here from boxes, in print orientation (flat on the bed, z up, sizes in mm).
The shapes sit 0.5 mm clear of each limit, so slicing tolerances cannot flip a result.
"""
import numpy as np
import pytest
import trimesh
from manifold3d import Manifold

import layers
import limits


def box(x0, x1, y0, y1, z0, z1):
    return Manifold.cube([x1 - x0, y1 - y0, z1 - z0]).translate([x0, y0, z0])


def kinds(findings):
    return sorted(f.kind for f in findings)


def judged(findings):
    """Kinds that are not just information."""
    return sorted(f.kind for f in findings if limits.KINDS[f.kind]["severity"] != "info")


def ceiling(gap, depth=20.0):
    """Two walls 10 mm tall with a 2 mm slab across the gap between them. `depth` wide: a ceiling."""
    return (box(0, 4, 0, depth, 0, 10) + box(4 + gap, 8 + gap, 0, depth, 0, 10)
            + box(0, 8 + gap, 0, depth, 10, 12))


def window(gap, wall=1.6):
    """A thin wall with a window `gap` wide: the head over the window is a thin wall head."""
    return box(0, gap + 20, 0, wall, 0, 20) - box(10, 10 + gap, -1, wall + 1, 5, 12)


def test_plain_block_has_no_findings():
    assert layers.run(box(0, 30, 0, 20, 0, 10)) == []


@pytest.mark.parametrize("thickness, expected", [(0.6, ["thin_feature"]), (1.0, [])])
def test_thin_wall(thickness, expected):
    part = box(0, 30, 0, 20, 0, 2) + box(5, 15, 5, 5 + thickness, 2, 7)
    assert judged(layers.run(part)) == expected


@pytest.mark.parametrize("reach, expected", [(1.5, []), (5.0, ["ledge"])])
def test_flat_ledge(reach, expected):
    part = box(0, 4, 0, 20, 0, 10) + box(0, 4 + reach, 0, 20, 10, 12)
    assert judged(layers.run(part)) == expected


@pytest.mark.parametrize("gap, expected", [
    (11.5, "bridge"),            # under the ceiling limit: information only
    (12.5, "ceiling_bridge"),    # a wide ceiling over 12 mm warns
    (29.5, "ceiling_bridge"),
    (30.5, "bridge_too_long"),   # over 30 mm fails
])
def test_ceiling_bridge_tiers(gap, expected):
    found = layers.run(ceiling(gap))
    assert kinds(found) == [expected]
    assert found[0].value == pytest.approx(gap, abs=0.3)


@pytest.mark.parametrize("gap, expected", [
    (22.0, "bridge"),            # a window head in a thin wall does not warn
    (29.5, "bridge"),
    (30.5, "bridge_too_long"),   # but still fails over 30 mm
])
def test_thin_wall_head(gap, expected):
    assert kinds(layers.run(window(gap))) == [expected]


@pytest.mark.parametrize("wall, expected", [
    (2.4, "bridge"),            # the measured case: 22 mm head in a 2.4 mm wall
    (3.0, "bridge"),
    (5.0, "ceiling_bridge"),    # the narrowest real ceiling seen on the station parts
])
def test_head_width_decides_between_thin_wall_and_ceiling(wall, expected):
    assert kinds(layers.run(window(22.0, wall=wall))) == [expected]


def test_wall_modelled_at_exactly_the_head_limit_counts_as_thin_wall_head():
    assert kinds(layers.run(window(22.0, wall=limits.value("thin_wall_head")))) == ["bridge"]


def test_floating_region_beside_a_supported_part():
    part = box(0, 10, 0, 10, 0, 10) + box(20, 25, 0, 5, 6, 8)
    found = [f for f in layers.run(part) if f.kind == "floating_region"]
    assert len(found) == 1
    assert found[0].z0 == pytest.approx(6.1, abs=0.11)


def test_floating_region_after_empty_layers():
    """Nothing is printed between z 2 and z 6, then a cube starts: it floats.
    The original float check skipped the first layer after a gap."""
    part = box(0, 10, 0, 10, 0, 2) + box(2, 7, 2, 7, 6, 8)
    found = [f for f in layers.run(part) if f.kind == "floating_region"]
    assert len(found) == 1
    assert found[0].z0 == pytest.approx(6.1, abs=0.11)


def test_a_sliver_too_narrow_to_extrude_is_not_a_floating_region():
    """A 0.02 mm wide outline, one layer tall, just past the edge of the layer below.
    A real roof that printed cleanly has five of these; no slicer extrudes them."""
    part = box(0, 20, 0, 10, 0, 6) + box(0, 20, 10.0, 10.02, 6.0, 6.2)
    assert layers.run(part) == []


def test_a_small_but_printable_island_in_mid_air_is_a_floating_region():
    part = box(0, 20, 0, 10, 0, 6) + box(0, 5, 11.5, 12.3, 6.0, 8.0)      # 0.8 mm wide, 1.5 mm away
    assert "floating_region" in kinds(layers.run(part))


@pytest.mark.parametrize("step, expected", [
    (1.6, []),            # the printed case: a column starting beside a bar, sharing an edge
    (5.0, ["ledge"]),     # touching, but reaching further than a ledge may
])
def test_an_outline_touching_the_layer_below_is_a_ledge_not_floating(step, expected):
    part = box(0, 12, 0, 1.6, 0, 6) + box(5, 7, -step, 0, 6, 10)
    assert judged(layers.run(part)) == expected


def test_an_outline_with_a_gap_to_the_layer_below_is_floating():
    part = box(0, 12, 0, 1.6, 0, 6) + box(5, 7, -2.0, -0.9, 6, 10)      # 0.9 mm gap
    assert judged(layers.run(part)) == ["floating_region"]


def test_first_layer_on_the_bed_is_not_floating():
    part = box(0, 10, 0, 10, 0, 2) + box(20, 30, 0, 10, 0, 2)
    assert layers.run(part) == []


def test_every_kind_has_a_severity_and_a_waiver_rule():
    part = ceiling(12.5) + box(60, 70, 0, 0.6, 0, 6).translate([0, 30, 0])
    for f in layers.run(part) + layers.run(ceiling(30.5)) + layers.run(window(22.0)):
        assert limits.KINDS[f.kind]["severity"] in ("fail", "warn", "info")
        assert isinstance(limits.KINDS[f.kind]["waivable"], bool)


def test_physical_defects_cannot_be_waived():
    for kind in ("thin_feature", "floating_region", "ledge", "bridge_too_long"):
        assert limits.KINDS[kind]["severity"] == "fail"
        assert limits.KINDS[kind]["waivable"] is False


def _write_stl(m, path):
    mesh = m.to_mesh()
    trimesh.Trimesh(np.asarray(mesh.vert_properties)[:, :3], np.asarray(mesh.tri_verts),
                    process=False).export(path)


def test_load_reads_a_solid(tmp_path):
    p = tmp_path / "block.stl"
    _write_stl(box(0, 10, 0, 10, 0, 5), p)
    assert layers.run(layers.load(str(p))) == []


def test_load_accepts_a_part_made_of_touching_bodies(tmp_path):
    """Two bodies sharing a face: trimesh calls this open, the checks must still accept it."""
    p = tmp_path / "two.stl"
    a, b = box(0, 10, 0, 10, 0, 5).to_mesh(), box(10, 20, 0, 10, 0, 5).to_mesh()
    va, vb = np.asarray(a.vert_properties)[:, :3], np.asarray(b.vert_properties)[:, :3]
    faces = np.vstack([np.asarray(a.tri_verts), np.asarray(b.tri_verts) + len(va)])
    trimesh.Trimesh(np.vstack([va, vb]), faces, process=False).export(p)
    assert layers.run(layers.load(str(p))) == []


def test_load_rejects_a_missing_file(tmp_path):
    with pytest.raises((FileNotFoundError, ValueError)):
        layers.load(str(tmp_path / "nope.stl"))


def test_load_rejects_an_open_mesh(tmp_path):
    p = tmp_path / "open.stl"
    mesh = box(0, 10, 0, 10, 0, 5).to_mesh()
    faces = np.asarray(mesh.tri_verts)[:-2]          # remove two triangles: a hole
    trimesh.Trimesh(np.asarray(mesh.vert_properties)[:, :3], faces, process=False).export(p)
    with pytest.raises(layers.MeshError):
        layers.load(str(p))
