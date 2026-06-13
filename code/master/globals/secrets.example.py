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

# Shared key required on every mutating API request (POST/PUT/PATCH/DELETE),
# including the manual pump activate/deactivate endpoint.
TETHYS_API_KEY = "change-me"

# Room to grow: the Django SECRET_KEYs can move here too (audit quick win), e.g.
# API_SECRET_KEY = "..."
# WEB_SECRET_KEY = "..."
