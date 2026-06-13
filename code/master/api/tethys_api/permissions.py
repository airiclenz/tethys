# =============================================================================
# API key permission.
#
# Tethys has no user accounts; the API is a single-tenant device API on the LAN.
# This permission gates every *mutating* request (POST/PUT/PATCH/DELETE) behind a
# single shared key, while leaving read-only requests open so the dashboard,
# polling, and the core's GET reads keep working. The worst risk it closes is an
# unauthenticated host turning on a pump via PATCH /api/channel/<n>/activate.
#
# The key is sent in the `X-API-Key` request header and must match
# settings.TETHYS_API_KEY (loaded from the git-ignored globals/secrets.py).
#
# Limitation: traffic is plain HTTP on the LAN, so the key is observable to a
# sniffer. This raises the bar from "any LAN host" to "needs the key"; it is not
# a substitute for transport encryption.
# =============================================================================

import hmac

from django.conf import settings
from rest_framework.permissions import BasePermission, SAFE_METHODS


class ApiKeyForWrite(BasePermission):
    '''Allow safe methods (GET/HEAD/OPTIONS) unconditionally; require a matching
    X-API-Key header for every mutating method.'''

    message = "A valid X-API-Key header is required for this request."

    def has_permission(self, request, view):
        # Safe methods stay open. OPTIONS being safe also lets the browser's
        # CORS preflight succeed without the key.
        if request.method in SAFE_METHODS:
            return True

        expected = getattr(settings, "TETHYS_API_KEY", None)
        provided = request.headers.get("X-API-Key")

        # Fail closed if the server key is unset/empty or the client sent nothing.
        if not expected or not provided:
            return False

        # Constant-time compare to avoid leaking the key via timing.
        return hmac.compare_digest(str(provided), str(expected))
