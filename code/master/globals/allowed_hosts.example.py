# =============================================================================
# Extra Django ALLOWED_HOSTS for the Tethys master — TEMPLATE.
#
# Copy this file to `allowed_hosts.py` (same directory) and list any extra
# hostnames Django should accept, e.g. this Pi's Tailscale name. `allowed_hosts.py`
# is git-ignored and per-install — the tailnet name never gets committed.
#
# Read at runtime by BOTH Django apps (web/tethys_web/settings.py and
# api/tethys_api/settings.py) and appended to the base ALLOWED_HOSTS
# (tethys.local, localhost, 127.0.0.1). This file is OPTIONAL: if `allowed_hosts.py`
# does not exist, install and the services continue normally with no extra hosts.
#
# Edit + apply with:  sudo systemctl restart tethys-api tethys-web daphne
#
# Hostnames only — NO scheme and NO port (not "https://..." and not "...:8000").
# nginx serves Tethys for any Host, so this list is the sole host allow-list.
# =============================================================================

EXTRA_ALLOWED_HOSTS = [
    # "tethys.<tailnet>.ts.net",
]
