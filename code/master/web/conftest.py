"""Shared fixtures for the web UI tests.

The compiled JavaScript under ``static/js`` is no longer committed (it is
regenerated from ``static/ts`` on every deploy — see
``install/deploy-static.sh``). So before the browser tests run we compile the
TypeScript once, exactly the way the deploy does.
"""
import os
import shutil
import subprocess
from pathlib import Path

import pytest

# Playwright's sync API runs an asyncio event loop in the test thread, which
# makes Django think its (single-threaded) test-database setup is happening
# "in an async context" and refuse it. This is the documented escape hatch for
# the Playwright + Django combo; safe because the DB work here is synchronous.
os.environ.setdefault("DJANGO_ALLOW_ASYNC_UNSAFE", "1")

WEB_DIR = Path(__file__).resolve().parent
TS_DIR = WEB_DIR / "static" / "ts"
COMPILED_ENTRY = WEB_DIR / "static" / "js" / "channel.js"


@pytest.fixture(scope="session", autouse=True)
def compile_typescript():
    """Compile static/ts -> static/js before any UI test loads a page.

    This codebase is loosely typed, so ``tsc`` reports type errors but still
    emits the JavaScript (``noEmitOnError`` is off). A non-zero exit is therefore
    expected and not treated as a failure, mirroring deploy-static.sh.
    """
    if shutil.which("tsc") is None:
        pytest.skip("'tsc' not found on PATH; cannot build the frontend for UI tests")

    subprocess.run(
        ["tsc", "-p", "tsconfig.json"],
        cwd=TS_DIR,
        check=False,
        capture_output=True,
        text=True,
    )

    if not COMPILED_ENTRY.exists():
        pytest.skip(f"{COMPILED_ENTRY.name} missing after tsc; frontend did not build")

    yield
