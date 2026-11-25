"""Other nozzles and layer heights: scaled limits, warnings only."""
import numpy as np
import pytest
import trimesh
from manifold3d import Manifold

import check
import layers
import limits


def box(x0, x1, y0, y1, z0, z1):
    return Manifold.cube([x1 - x0, y1 - y0, z1 - z0]).translate([x0, y0, z0])


def stl(tmp_path, solid, name="part.stl"):
    mesh = solid.to_mesh()
    path = tmp_path / name
    trimesh.Trimesh(np.asarray(mesh.vert_properties)[:, :3], np.asarray(mesh.tri_verts), process=False).export(path)
    return str(path)


WALL_1MM = box(0, 30, 0, 20, 0, 2) + box(5, 15, 5, 6.0, 2, 7)       # fine at 0.4, thin at 0.6
LONG_BRIDGE = box(0, 4, 0, 20, 0, 10) + box(34.5, 38.5, 0, 20, 0, 10) + box(0, 38.5, 0, 20, 10, 12)


def test_every_number_says_how_it_scales():
    numbers = {n for n, v in vars(limits).items()
               if n.isupper() and isinstance(v, (int, float)) and not isinstance(v, bool)}
    numbers -= {"NOZZLE", "LAYER", "TESTED_NOZZLE", "TESTED_LAYER"}
    assert numbers | set(limits.LIMITS) == set(limits.SCALING)
    assert set(limits.SCALING.values()) <= {"nozzle", "layer", "none"}


def test_scaling_follows_the_nozzle_and_leaves_lengths_alone():
    limits.use(nozzle=0.6, layer=0.3)
    assert limits.value("min_width") == pytest.approx(1.2)
    assert limits.value("thin_wall_head") == pytest.approx(4.5)
    assert limits.value("max_bridge") == 30.0 and limits.value("max_ledge") == 2.0
    assert limits.FLOAT_BOND == pytest.approx(0.3) and limits.SUPPORT_GROW == pytest.approx(0.525)
    limits.use()
    assert limits.value("min_width") == 0.8 and limits.FLOAT_BOND == 0.2 and limits.tested()


def test_the_layer_height_in_use_is_the_one_sliced_at():
    limits.use(nozzle=0.4, layer=0.1)
    _, sliced = layers.slices_of(box(0, 10, 0, 10, 0, 5))
    assert len(sliced) == 50


def run(args, capsys):
    code = check.main(args)
    return code, capsys.readouterr()


def test_a_scaled_limit_warns_and_says_so(tmp_path, capsys):
    p = stl(tmp_path, WALL_1MM)
    assert run([p, "--no-report"], capsys)[0] == 0                 # 1 mm wall is fine on 0.4
    code, out = run([p, "--no-report", "--nozzle", "0.6", "--layer", "0.3"], capsys)
    assert code == 0
    assert "warn  Feature narrower than the minimum width" in out.out
    assert "[limit scaled from a 0.4 mm nozzle, not measured]" in out.out
    assert "0.6 mm nozzle and 0.3 mm layers: scaled limits, not measured" in out.out


def test_a_length_limit_still_fails_on_another_setup(tmp_path, capsys):
    code, out = run([stl(tmp_path, LONG_BRIDGE), "--no-report", "--nozzle", "0.6", "--layer", "0.3"], capsys)
    assert code == 1 and "FAIL  Bridge longer than the hard limit" in out.out


def test_the_report_records_the_setup(tmp_path, capsys):
    import json
    p = stl(tmp_path, WALL_1MM)
    run([p, "--nozzle", "0.6", "--layer", "0.3"], capsys)
    r = json.load(open(tmp_path / "part.report.json"))
    assert r["setup"] == {"nozzle_mm": 0.6, "layer_mm": 0.3, "tested": False}
    assert r["limits"]["min_width"]["value"] == pytest.approx(1.2)
    assert any(f["scaled"] for c in r["checks"] for f in c["findings"])


def test_the_next_run_is_back_on_the_tested_setup(tmp_path, capsys):
    p = stl(tmp_path, WALL_1MM)
    run([p, "--no-report", "--nozzle", "0.6", "--layer", "0.3"], capsys)
    code, out = run([p, "--no-report"], capsys)
    assert code == 0 and "scaled" not in out.out


@pytest.mark.parametrize("args", [["--nozzle", "0"], ["--nozzle", "5"], ["--layer", "0.9"], ["--layer", "0.01"]])
def test_an_implausible_setup_is_refused(tmp_path, capsys, args):
    code, out = run([stl(tmp_path, WALL_1MM), "--no-report"] + args, capsys)
    assert code == 2 and "--nozzle must be" in out.err


def test_the_tables_always_describe_the_tested_setup():
    limits.use(nozzle=0.6, layer=0.3)
    assert "| `min_width` | 0.8 mm |" in check.skill_tables()
