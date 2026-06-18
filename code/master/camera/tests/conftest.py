import os
import sys

# The camera modules use flat imports (import config, import cameraController,
# from captureBackend ...), the same way the running service sees them with
# WorkingDirectory=camera/. Put camera/ at the FRONT of sys.path so its `config`
# module wins over core/'s same-named module (which the root pytest.ini puts on
# the path via `pythonpath = core`).
CAMERA_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if CAMERA_DIR not in sys.path:
    sys.path.insert(0, CAMERA_DIR)
