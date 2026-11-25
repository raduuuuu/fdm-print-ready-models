"""What must never be committed: personal folder paths, the station models' names and logos."""
import os
import re
import subprocess

import pytest

import check

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Built from pieces so this file does not contain what it forbids.
HOME_PATHS = [r"/" + "Users" + r"/[A-Za-z0-9._-]+", r"/" + "home" + r"/[a-z][a-z0-9._-]+",
              r"[A-Z]:\\" + "Users" + r"\\", r"/" + "mnt" + r"/project-files"]
WORDS = ["br" + "io", "s" + "bb", "station" + "kit"]


def scan(text):
    """Every forbidden thing found in `text`."""
    found = [m.group(0) for pat in HOME_PATHS for m in re.finditer(pat, text)]
    found += [w for w in WORDS if re.search(r"(?<![a-z])" + w + r"(?![a-z])", text, re.I)]
    return found


def tracked_files():
    out = subprocess.run(["git", "ls-files"], cwd=REPO, capture_output=True, text=True, check=True)
    return [f for f in out.stdout.splitlines() if f]


def test_no_personal_paths_or_model_names_in_tracked_files():
    problems = {}
    for name in tracked_files():
        with open(os.path.join(REPO, name), "rb") as fh:
            text = fh.read().decode("utf-8", errors="ignore")
        hits = scan(text) + scan(name)
        if hits:
            problems[name] = sorted(set(hits))
    assert problems == {}


@pytest.mark.parametrize("planted", [
    "saved to /" + "Users" + "/someone/Desktop/part.stl",
    "C:\\" + "Users" + "\\someone\\part.stl",
    "/" + "home" + "/someone/models",
    "fits " + "BR" + "IO" + " track",
])
def test_the_scan_catches_a_planted_problem(planted):
    assert scan(planted) != []


def test_the_scan_accepts_ordinary_text():
    assert scan("A library of print-safe parts; see ~/.claude/skills and /usr/bin.") == []


def test_known_good_part_passes_without_warnings(capsys):
    code = check.main([os.path.join(REPO, "tests", "fixtures", "known_good.stl"), "--no-report"])
    out = capsys.readouterr().out
    assert code == 0 and "VERDICT: PASS (layer, post and support checks only; with 2 warnings" in out
    assert out.count("warn  Support would stand on the model") == 2 and "FAIL" not in out.replace("VERDICT", "")


def test_every_measured_claim_in_the_skill_has_evidence():
    skill = open(os.path.join(REPO, "skills", "fdm-print-ready-models", "SKILL.md")).read()
    evidence = open(os.path.join(REPO, "EVIDENCE.md")).read()
    assert skill.count("(measured") == 6, "a (measured) claim was added or removed: update EVIDENCE.md and this count"
    for phrase in ("19 degrees", "35 degrees", "39 degrees", "1.6 mm wall", "2.4 mm wall",
                   "Thin fragile part", "Floating bridge anchors", "2 walls"):
        assert phrase in evidence
