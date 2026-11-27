"""The runner: verdict, exit codes, report and the generated SKILL.md tables."""
import json
import os
import subprocess
import sys

import numpy as np
import pytest
import trimesh
from manifold3d import Manifold

import check
import layers

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILL = os.path.join(REPO, "skills", "fdm-print-ready-models", "SKILL.md")
CHECK_PY = os.path.join(REPO, "skills", "fdm-print-ready-models", "scripts", "check.py")
NOT_RUN = "geometry only: the slicer check did not run"
BY_HAND = "still to do by hand: raised ports, assembly instructions"


def box(x0, x1, y0, y1, z0, z1):
    return Manifold.cube([x1 - x0, y1 - y0, z1 - z0]).translate([x0, y0, z0])


def stl(tmp_path, solid, name="part.stl", scale=1.0, lift=0.0):
    mesh = solid.to_mesh()
    v = np.asarray(mesh.vert_properties)[:, :3] * scale + [0, 0, lift]
    path = tmp_path / name
    trimesh.Trimesh(v, np.asarray(mesh.tri_verts), process=False).export(path)
    return str(path)


def ceiling(gap):
    return box(0, 4, 0, 20, 0, 10) + box(4 + gap, 8 + gap, 0, 20, 0, 10) + box(0, 8 + gap, 0, 20, 10, 12)


GOOD = box(0, 30, 0, 20, 0, 10)


# ---- verdict precedence (pure function)

def results(*statuses):
    return [{"name": f"c{i}", "status": s} for i, s in enumerate(statuses)]


@pytest.mark.parametrize("statuses, part_error, verdict", [
    (["pass"], None, "PASS"),
    (["warn"], None, "PASS"),
    (["pass", "not_shipped"], None, "PASS"),
    (["pass", "skipped"], None, "PASS"),
    (["error"], None, "INCOMPLETE"),
    (["pass", "error"], None, "INCOMPLETE"),
    (["error"], "file not found", "INCOMPLETE"),
    (["fail"], None, "FAIL"),
    (["fail", "error"], None, "FAIL"),          # a failure outranks a crash
    (["fail", "warn", "not_shipped"], None, "FAIL"),
])
def test_verdict_precedence(statuses, part_error, verdict):
    assert check.decide(results(*statuses), part_error)[0] == verdict


def test_crash_and_unshipped_checks_are_named():
    _, quals = check.decide([{"name": "layer", "status": "error"}, {"name": "slicer", "status": "not_shipped"}])
    assert quals == ["crashed: layer", "checks not run: slicer"]
    _, quals = check.decide([{"name": "layer", "status": "pass"}, {"name": "slicer", "status": "skipped"}])
    assert quals == ["geometry only: the slicer check did not run"]


# ---- whole runs

def run(args, capsys):
    code = check.main(args)
    out = capsys.readouterr()
    return code, out.out, out.err


def test_good_part_passes_and_says_what_did_not_run(tmp_path, capsys):
    p = stl(tmp_path, GOOD)
    code, out, _ = run([p], capsys)
    assert code == 0
    assert f"VERDICT: PASS (layer, post, slope, overhang angle, corner and support checks only; {NOT_RUN}; {BY_HAND})" in out
    assert "the slicer check did not run: no slicer found" in out


def test_report_contents(tmp_path, capsys):
    p = stl(tmp_path, ceiling(12.5))
    code, out, _ = run([p], capsys)
    r = json.load(open(tmp_path / "part.report.json"))
    assert code == 0 and r["verdict"] == "PASS"
    assert r["schema"] == 1 and r["tool"]["version"] == check.__version__
    assert len(r["part"]["sha256"]) == 64 and r["part"]["file"] == "part.stl"
    assert r["limits"]["max_bridge"] == {"value": 30.0, "unit": "mm", "source": "estimate"}
    assert set(r["versions"]) == {"python", "numpy", "trimesh", "manifold3d"}
    f = r["checks"][0]["findings"][0]
    assert f["kind"] == "ceiling_bridge" and f["severity"] == "warn" and f["waivable"] is True
    assert {"x", "y", "z0", "z1"} <= set(f)
    assert "with 1 warning" in out
    assert str(tmp_path) not in json.dumps(r)        # no folder paths in a report


def test_fingerprint_changes_with_the_part(tmp_path, capsys):
    a = stl(tmp_path, GOOD, "a.stl")
    b = stl(tmp_path, box(0, 31, 0, 20, 0, 10), "b.stl")
    run([a, b], capsys)
    ha = json.load(open(tmp_path / "a.report.json"))["part"]["sha256"]
    hb = json.load(open(tmp_path / "b.report.json"))["part"]["sha256"]
    assert ha != hb


def test_failing_part_exits_1(tmp_path, capsys):
    code, out, _ = run([stl(tmp_path, ceiling(30.5)), "--no-report"], capsys)
    assert code == 1
    assert "FAIL  Bridge longer than the hard limit: span 30." in out
    assert "VERDICT: FAIL" in out


def test_one_failing_part_among_several_exits_1(tmp_path, capsys):
    code, _, _ = run([stl(tmp_path, GOOD, "a.stl"), stl(tmp_path, ceiling(30.5), "b.stl"), "--no-report"], capsys)
    assert code == 1


@pytest.mark.parametrize("make, message", [
    (lambda d: str(d / "missing.stl"), "file not found"),
    (lambda d: _write(d / "junk.stl", b"this is not an stl file at all\n" * 5), "could not check this part"),
    (lambda d: stl(d, GOOD, scale=0.001), "check the export units"),          # exported in metres
    (lambda d: stl(d, GOOD, scale=100.0), "check the export units"),          # 3 m wide
])
def test_unreadable_or_implausible_part_is_incomplete(tmp_path, capsys, make, message):
    code, out, _ = run([make(tmp_path), "--no-report"], capsys)
    assert code == 2
    assert message in out and "VERDICT: INCOMPLETE" in out


def _write(path, data):
    path.write_bytes(data)
    return str(path)


def test_open_mesh_is_incomplete(tmp_path, capsys):
    mesh = GOOD.to_mesh()
    p = tmp_path / "open.stl"
    trimesh.Trimesh(np.asarray(mesh.vert_properties)[:, :3], np.asarray(mesh.tri_verts)[:-2], process=False).export(p)
    code, out, _ = run([str(p), "--no-report"], capsys)
    assert code == 2 and "mesh problem" in out


def test_part_not_on_the_bed_warns_but_passes(tmp_path, capsys):
    code, out, _ = run([stl(tmp_path, GOOD, lift=5.0), "--no-report"], capsys)
    assert code == 0
    assert "warn  Lowest point of the part is not at z = 0" in out and "with 1 warning" in out


def test_inch_sized_part_warns(tmp_path, capsys):
    code, out, _ = run([stl(tmp_path, box(0, 100, 0, 50, 0, 20), scale=1 / 25.4), "--no-report"], capsys)
    assert code == 0 and "check the export units" in out


def test_a_crashing_check_is_reported_not_swallowed(tmp_path, capsys, monkeypatch):
    def boom(solid):
        raise RuntimeError("simulated crash")
    monkeypatch.setattr(layers, "run", boom)
    p = stl(tmp_path, GOOD)
    code, out, _ = run([p], capsys)
    r = json.load(open(tmp_path / "part.report.json"))
    assert code == 2 and "VERDICT: INCOMPLETE (crashed: layer" in out
    assert "the layer check crashed: RuntimeError: simulated crash" in out
    assert "Traceback" in r["checks"][0]["error"]


def test_a_pass_names_the_checks_done_by_hand_and_a_failure_does_not():
    by_hand = [{"name": "layer", "status": "pass"}, {"name": "raised ports", "status": "by_hand"}]
    assert check.decide(by_hand) == ("PASS", ["still to do by hand: raised ports"])
    assert check.decide([{"name": "layer", "status": "fail"}] + by_hand[1:]) == ("FAIL", [])


def test_out_may_not_name_a_file_the_command_reads(tmp_path, capsys):
    p = stl(tmp_path, GOOD)
    before = open(p, "rb").read()
    code, out, err = run([p, "--out", p], capsys)
    assert code == 2 and "--out names a file the command reads" in err and "VERDICT" not in out
    assert open(p, "rb").read() == before
    exc = tmp_path / "part.exceptions.json"
    exc.write_text('{"exceptions": []}')
    code, _, err = run([p, "--out", str(exc)], capsys)
    assert code == 2 and exc.read_text() == '{"exceptions": []}'


def test_unwritable_report_still_gives_the_verdict(tmp_path, capsys):
    code, out, err = run([stl(tmp_path, GOOD), "--out", str(tmp_path / "no_such_dir" / "r.json")], capsys)
    assert code == 0 and "VERDICT: PASS" in out and "could not write the report" in err


def test_missing_packages_message_names_both_install_routes():
    assert check.missing_packages(("numpy", "surely_not_installed_pkg")) == ["surely_not_installed_pkg"]
    text = check.install_help(["manifold3d"])
    assert "uv run --no-project --python 3.12 --with-requirements" in text and "pip install -r" in text


def test_runs_as_a_script(tmp_path):
    r = subprocess.run([sys.executable, CHECK_PY, stl(tmp_path, GOOD), "--no-report"], capture_output=True, text=True)
    assert r.returncode == 0 and "VERDICT: PASS" in r.stdout


def test_no_arguments_is_a_usage_error(capsys):
    assert check.main([]) == 2


# ---- text and code cannot disagree

def test_skill_tables_match_the_code():
    text = open(SKILL).read()
    a, b = text.index(check.BEGIN), text.index(check.END) + len(check.END)
    assert text[a:b] == check.skill_tables(), "run: check.py --update-skill-tables"


def test_a_hand_edited_number_is_caught():
    edited = check.skill_tables().replace("| 30 mm |", "| 36 mm |")
    assert edited != check.skill_tables()


def test_version_matches_the_plugin_manifest():
    manifest = json.load(open(os.path.join(REPO, ".claude-plugin", "plugin.json")))
    assert manifest["version"] == check.__version__


PROSE = {      # how the design rules in SKILL.md word each limit that the checks enforce
    "min_width": r"Nothing narrower than ([\d.]+) mm",
    "max_ledge": r"A flat ledge may stick out ([\d.]+) mm at most",
    "max_bridge": r"A bridge over ([\d.]+) mm always fails",
    "ceiling_warn": r"a ceiling longer than ([\d.]+) mm may sag",
    "thin_wall_head": r"in a wall up to ([\d.]+) mm thick",
    "column_ratio": r"at least 2\.4 mm, at most ([\d.]+) times as tall as wide",
    "support_min_width": r"any flat underside about ([\d.]+) mm or wider gets a support",
    "tool_gap": r"a gap of at least ([\d.]+) mm leading to the support",
    "roof_min_angle": r"either flat or at least ([\d.]+) degrees steep",
    "fillet_band": r"A shallow band narrower than about ([\d.]+) mm",
    "overhang_target_angle": r"Overhangs at ([\d.]+) degrees or steeper",
    "overhang_fail_angle": r"fails undersides flatter than ([\d.]+) degrees",
    "corner_min_edge": r"sharp inner edges of ([\d.]+) mm or longer",
}


@pytest.mark.parametrize("name", sorted(PROSE))
def test_the_design_rules_state_the_same_limit_as_the_code(name):
    import re
    import limits
    prose = open(SKILL).read().split(check.BEGIN)[0]
    found = re.findall(PROSE[name], prose)
    assert len(found) == 1, f"SKILL.md should state {name} exactly once in these words"
    assert float(found[0]) == limits.value(name)


def test_every_enforced_limit_is_stated_in_the_design_rules():
    import limits
    assert set(PROSE) == set(limits.LIMITS)


def test_skill_file_is_within_the_documented_size():
    assert len(open(SKILL).read().splitlines()) < 500


def test_skill_gives_the_command_through_the_skill_folder():
    text = open(SKILL).read()
    assert '"${CLAUDE_SKILL_DIR}/scripts/check.py"' in text
    assert '--with-requirements "${CLAUDE_SKILL_DIR}/scripts/requirements-slicer.txt"' in text
