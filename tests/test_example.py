"""The worked example: it builds, it matches the committed STL, and it passes with no warnings."""
import hashlib
import importlib.util
import json
import os

import trimesh

import check

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXAMPLE = os.path.join(REPO, "examples", "shelter")


def load_generator():
    spec = importlib.util.spec_from_file_location("shelter", os.path.join(EXAMPLE, "shelter.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_the_committed_stl_is_what_the_generator_builds(tmp_path):
    """The skill's own advice: prove a change did not alter the geometry by comparing volumes."""
    solid = load_generator().build()
    committed = trimesh.load(os.path.join(EXAMPLE, "shelter.stl"), force="mesh")
    assert abs(committed.volume - solid.volume()) < 0.01


def test_the_example_passes_every_shipped_check_without_warnings(capsys):
    code = check.main([os.path.join(EXAMPLE, "shelter.stl"), "--no-report"])
    out = capsys.readouterr().out
    assert code == 0 and "VERDICT: PASS" in out
    assert "FAIL" not in out.replace("VERDICT", "") and "warn" not in out and "waived" not in out


def test_the_saved_report_belongs_to_the_committed_stl():
    report = json.load(open(os.path.join(EXAMPLE, "passing-report.json")))
    with open(os.path.join(EXAMPLE, "shelter.stl"), "rb") as fh:
        assert report["part"]["sha256"] == hashlib.sha256(fh.read()).hexdigest()
    assert report["verdict"] == "PASS" and report["counts"]["fail"] == 0 and report["counts"]["warn"] == 0
    assert report["tool"]["version"] == check.__version__


def test_the_preview_is_a_png(tmp_path):
    gen = load_generator()
    out = tmp_path / "p.png"
    gen.preview(gen.build(), str(out), size=120)
    assert out.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"
