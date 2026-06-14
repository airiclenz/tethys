# =============================================================================
# API key permission.
#
# Tethys has no user accounts; the API is a single-tenant device API. This
# permission gates EVERY request (reads and writes alike) behind a single shared
# key. Reads were locked down alongside enabling safe remote (VPN) access: with
# the system reachable from a Tailscale/WireGuard device, sensor data and channel
# state should not be readable by anything that merely reaches the port. The worst
# risk it closes remains an unauthenticated host turning on a pump via
# PATCH /api/channel/<n>/activate.
#
# Only OPTIONS stays open, so the browser's CORS preflight (which never carries
# the key) succeeds; the real GET that follows must present the key.
#
# The key is sent in the `X-API-Key` request header and must match
# settings.TETHYS_API_KEY (loaded from the git-ignored globals/secrets.py). All
# callers send it: the web UI (browser localStorage), the core daemon, and the
# web backend's server-side polling.
#
# Note: the key is the access control; the VPN tunnel provides the transport
# encryption, so the key is not observable off-device.
# =============================================================================

import hmac

from django.conf import settings
from rest_framework.permissions import BasePermission


class ApiKeyRequired(BasePermission):
    '''Allow CORS preflight (OPTIONS) unconditionally; require a matching
    X-API-Key header for every other method, reads included.'''

    message = "A valid X-API-Key header is required for this request."

    def has_permission(self, request, view):
        # OPTIONS stays open so the browser's CORS preflight succeeds without the
        # key; every other method (GET/HEAD included) must present it.
        if request.method == "OPTIONS":
            return True

        expected = getattr(settings, "TETHYS_API_KEY", None)
        provided = request.headers.get("X-API-Key")

        # Fail closed if the server key is unset/empty or the client sent nothing.
        if not expected or not provided:
            return False

        # Constant-time compare to avoid leaking the key via timing.
        return hmac.compare_digest(str(provided), str(expected))
