"""Intended exceptions: judgment findings can be waived with a reason, physical defects cannot."""
import json
import math

import numpy as np
import pytest
import trimesh
from manifold3d import CrossSection, Manifold

import check


def box(x0, x1, y0, y1, z0, z1):
    return Manifold.cube([x1 - x0, y1 - y0, z1 - z0]).translate([x0, y0, z0])


def stl(tmp_path, solid, name="part.stl", lift=0.0):
    mesh = solid.to_mesh()
    path = tmp_path / name
    trimesh.Trimesh(np.asarray(mesh.vert_properties)[:, :3] + [0, 0, lift], np.asarray(mesh.tri_verts),
                    process=False).export(path)
    return str(path)


def ramp():
    """A 19 degree ramp, 30 mm wide and 40 mm long: fails the slope check."""
    rise = 30 * math.tan(math.radians(19))
    pts = [(0, 0), (30, 0), (30, 4 + rise), (0, 4)]
    return Manifold.extrude(CrossSection([pts]), 40).rotate([90, 0, 0])


THIN = box(0, 30, 0, 20, 0, 2) + box(5, 15, 5, 5.6, 2, 7)
CEILING = box(0, 4, 0, 20, 0, 10) + box(16.5, 20.5, 0, 20, 0, 10) + box(0, 20.5, 0, 20, 10, 12)
EVERYWHERE = [-1000, -1000, -1000, 1000, 1000, 1000]


def write(tmp_path, entries, name="part.exceptions.json"):
    (tmp_path / name).write_text(json.dumps({"exceptions": entries}))


def run(args, capsys):
    code = check.main(args)
    return code, capsys.readouterr().out


def test_without_a_file_the_ramp_fails(tmp_path, capsys):
    code, out = run([stl(tmp_path, ramp()), "--no-report"], capsys)
    assert code == 1 and "FAIL  Top surface too shallow" in out


def test_a_waived_slope_passes_and_shows_the_reason(tmp_path, capsys):
    p = stl(tmp_path, ramp())
    write(tmp_path, [{"kind": "slope_too_shallow", "box": EVERYWHERE, "reason": "Loading ramp: the slope is the function"}])
    code, out = run([p], capsys)
    assert code == 0
    assert "waived  Top surface too shallow" in out
    assert "reason: Loading ramp: the slope is the function" in out
    assert "VERDICT: PASS (" in out and "with 1 waiver" in out
    r = json.load(open(tmp_path / "part.report.json"))
    f = [f for c in r["checks"] for f in c["findings"] if f["kind"] == "slope_too_shallow"][0]
    assert f["severity"] == "waived" and f["waived_from"] == "fail" and r["counts"]["waived"] == 1
    assert r["exceptions"] == {"file": "part.exceptions.json", "entries": 1, "error": None}


def test_a_box_that_misses_the_finding_waives_nothing(tmp_path, capsys):
    p = stl(tmp_path, ramp())
    write(tmp_path, [{"kind": "slope_too_shallow", "box": [500, 500, 0, 600, 600, 10], "reason": "somewhere else entirely"}])
    code, out = run([p, "--no-report"], capsys)
    assert code == 1 and "FAIL  Top surface too shallow" in out
    assert "warn  Exception matched no finding: slope_too_shallow (somewhere else entirely)" in out


def test_a_physical_defect_cannot_be_waived(tmp_path, capsys):
    p = stl(tmp_path, THIN)
    write(tmp_path, [{"kind": "thin_feature", "box": EVERYWHERE, "reason": "decorative, I accept it"}])
    code, out = run([p, "--no-report"], capsys)
    assert code == 1
    assert "FAIL  Feature narrower than the minimum width" in out
    assert "warn  Exception refused: this kind of finding cannot be waived: thin_feature" in out
    assert "waived" not in out.replace("cannot be waived", "")


def test_a_waived_warning_leaves_the_count(tmp_path, capsys):
    p = stl(tmp_path, CEILING)
    assert "with 1 warning" in run([p, "--no-report"], capsys)[1]
    write(tmp_path, [{"kind": "ceiling_bridge", "box": EVERYWHERE, "reason": "short print, sag is acceptable"}])
    code, out = run([p, "--no-report"], capsys)
    assert code == 0 and "with 1 waiver" in out and "warning" not in out.split("VERDICT")[1]


def test_a_part_level_warning_takes_an_entry_without_a_box(tmp_path, capsys):
    p = stl(tmp_path, box(0, 30, 0, 20, 0, 10), lift=5.0)
    write(tmp_path, [{"kind": "off_bed", "reason": "exported at its assembled height"}])
    code, out = run([p, "--no-report"], capsys)
    assert code == 0 and "waived  Lowest point of the part is not at z = 0" in out and "with 1 waiver" in out


def test_one_box_waives_every_finding_of_that_kind_inside_it(tmp_path, capsys):
    two = ramp() + ramp().translate([50, 0, 0])
    p = stl(tmp_path, two)
    write(tmp_path, [{"kind": "slope_too_shallow", "box": EVERYWHERE, "reason": "both ramps are intended"}])
    code, out = run([p, "--no-report"], capsys)
    assert code == 0 and "with 2 waivers" in out


def test_a_stale_exception_warns_after_the_redesign(tmp_path, capsys):
    p = stl(tmp_path, box(0, 30, 0, 20, 0, 10))
    write(tmp_path, [{"kind": "slope_too_shallow", "box": EVERYWHERE, "reason": "ramp that no longer exists"}])
    code, out = run([p, "--no-report"], capsys)
    assert code == 0 and "warn  Exception matched no finding" in out and "with 1 warning" in out


@pytest.mark.parametrize("content, message", [
    ('{"exceptions": [', "not valid JSON at line 1"),
    ('[]', 'must be an object with a list named "exceptions"'),
    ('{"exceptions": [{"kind": "no_such_kind", "box": null, "reason": "because"}]}', "unknown kind 'no_such_kind'"),
    ('{"exceptions": [{"kind": "slope_too_shallow", "box": [0, 0, 0, 1, 1, 1]}]}', "a reason is required"),
    ('{"exceptions": [{"kind": "slope_too_shallow", "box": [0, 0, 0, 1, 1, 1], "reason": "  "}]}', "a reason is required"),
    ('{"exceptions": [{"kind": "slope_too_shallow", "box": [0, 0, 0, 1], "reason": "four numbers"}]}', "box must be six numbers"),
    ('{"exceptions": [{"kind": "slope_too_shallow", "box": [5, 0, 0, 1, 1, 1], "reason": "x0 after x1"}]}', "box must be six numbers"),
])
def test_a_broken_file_makes_the_run_incomplete(tmp_path, capsys, content, message):
    p = stl(tmp_path, box(0, 30, 0, 20, 0, 10))
    (tmp_path / "part.exceptions.json").write_text(content)
    code, out = run([p, "--no-report"], capsys)
    assert code == 2 and "VERDICT: INCOMPLETE" in out
    assert "problem with the exceptions file part.exceptions.json" in out and message in out


def test_a_broken_file_does_not_hide_a_failure(tmp_path, capsys):
    p = stl(tmp_path, ramp())
    (tmp_path / "part.exceptions.json").write_text("{")
    code, out = run([p, "--no-report"], capsys)
    assert code == 1 and "FAIL  Top surface too shallow" in out and "problem with the exceptions file" in out


def test_the_file_can_be_named_on_the_command_line(tmp_path, capsys):
    p = stl(tmp_path, ramp())
    write(tmp_path, [{"kind": "slope_too_shallow", "box": EVERYWHERE, "reason": "intended ramp"}], name="elsewhere.json")
    code, out = run([p, "--no-report", "--exceptions", str(tmp_path / "elsewhere.json")], capsys)
    assert code == 0 and "with 1 waiver" in out


def test_a_named_file_that_does_not_exist_is_incomplete(tmp_path, capsys):
    code, out = run([stl(tmp_path, box(0, 30, 0, 20, 0, 10)), "--no-report", "--exceptions", str(tmp_path / "none.json")], capsys)
    assert code == 2 and "cannot be read" in out


def test_every_kind_that_fails_and_cannot_be_waived_is_a_physical_defect():
    import limits
    unwaivable = {k for k, v in limits.KINDS.items() if v["severity"] == "fail" and not v["waivable"]}
    assert unwaivable == {"thin_feature", "floating_region", "ledge", "bridge_too_long",
                          "overhang_past_supports", "thin_post_overhang", "slender_column",
                          "slicer_bridge_too_long", "slicer_wall_in_air"}
