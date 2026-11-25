import os
import sys

SCRIPTS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                       "skills", "fdm-print-ready-models", "scripts")
sys.path.insert(0, SCRIPTS)
