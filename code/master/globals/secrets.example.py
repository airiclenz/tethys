# =============================================================================
# Local secrets for the Tethys master — TEMPLATE.
#
# Copy this file to `secrets.py` (same directory) and fill in real values.
# `secrets.py` is git-ignored and must NEVER be committed. It is the single
# source of truth read by BOTH the Django API (api/tethys_api/settings.py) and
# the non-Django core process (core/apiInterface.py, core/radio.py).
#
# The installer (install/install.sh) generates `secrets.py` with a random key if
# it does not already exist, and prints the key so you can paste it into the web
# UI once (Settings popup -> API key).
#
# Generate a key manually with:
#   python3 -c "import secrets; print(secrets.token_urlsafe(32))"
# =============================================================================

# Shared key required on every API request that mutates state, and (since the
# reads were locked down) on read requests too. Used by the web UI, the core
# daemon, and the web backend's server-side polling.
TETHYS_API_KEY = "change-me"

# Django SECRET_KEYs, one per Django app. Unique per install, never committed.
# Generate each with:
#   python3 -c "from django.core.management.utils import get_random_secret_key as g; print(g())"
API_SECRET_KEY = "change-me"
WEB_SECRET_KEY = "change-me"
