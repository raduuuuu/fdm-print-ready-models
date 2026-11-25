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
