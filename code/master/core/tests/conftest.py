import os
import sys

# Belt-and-suspenders alongside pytest.ini's `pythonpath = core`: ensure the
# core/ directory is importable regardless of pytest version or rootdir, so the
# flat imports (import pumpController, import gpioAdapter, from hardware ...)
# resolve the same way the running service sees them.
CORE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if CORE_DIR not in sys.path:
    sys.path.insert(0, CORE_DIR)
