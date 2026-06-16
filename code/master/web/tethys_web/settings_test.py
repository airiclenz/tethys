"""Django settings used by the Playwright UI tests.

Identical to the normal web settings except that the staticfiles finders point
at the in-repo ``static/`` tree. In production nginx serves ``/static/`` from the
collected ``staticcollect/`` folder; for tests we serve straight from source so
no ``collectstatic`` step is needed and the live server picks up the JS that
``conftest.py`` just compiled from TypeScript.
"""
from tethys_web.settings import *  # noqa: F401,F403
from tethys_web.settings import BASE_DIR

# BASE_DIR is the web/ directory, so web/static/ holds the compiled js, css,
# vendor and templatter assets the page loads.
STATICFILES_DIRS = [BASE_DIR / "static"]
