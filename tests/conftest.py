import os
import sys

SCRIPTS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                       "skills", "fdm-print-ready-models", "scripts")
sys.path.insert(0, SCRIPTS)


import pytest  # noqa: E402


@pytest.fixture(autouse=True)
def tested_setup():
    """Every test starts and ends on the tested nozzle and layer height."""
    import limits
    limits.use()
    yield
    limits.use()


@pytest.fixture(autouse=True)
def no_slicer_unless_asked(request, monkeypatch):
    """Tests must give the same result whether or not a slicer is installed. Only tests marked
    `live_slicer` may find one."""
    if "live_slicer" not in request.keywords:
        import slicer
        monkeypatch.setattr(slicer, "find", lambda kind: None)
