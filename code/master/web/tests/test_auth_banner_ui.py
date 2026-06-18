"""Regression UI test for the API-auth banner.

Every API request needs an ``X-API-Key`` header; the API answers a missing or
wrong key with **403** (see ``api/tethys_api/permissions.py``). When that key is
not set in the browser, the dashboard silently fails to load any data. To make
the cause obvious, the page runs a one-shot probe (``GET /api/version/``) on
load and, on a 403, shows a warning banner under the header that links to
Settings; a successful probe leaves the banner hidden.

These tests drive that in a real browser by intercepting the probe and asserting
the banner appears on a 403 and stays hidden on a 200. The probe is mocked
(rather than standing up the API) so the tests stay hermetic and deterministic.
"""

# Permissive CORS headers so the browser accepts the mocked cross-origin probe
# response: the frontend calls the API on port 5000, a different origin than the
# web app under test.
_CORS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Headers": "*",
    "Access-Control-Allow-Methods": "*",
}


def _mock_version(status, body):
    """Build a ``page.route`` handler that answers the version probe.

    Also answers the CORS preflight (OPTIONS) so the real GET is let through.
    """
    def handler(route):
        if route.request.method == "OPTIONS":
            route.fulfill(status=204, headers=_CORS)
            return
        route.fulfill(
            status=status,
            headers=_CORS,
            content_type="application/json",
            body=body,
        )
    return handler


def test_auth_banner_shows_on_403(live_server, page):
    # No API key is set in this fresh browser context, so the probe gets a 403.
    page.route("**/api/version/", _mock_version(403, '{"detail": "forbidden"}'))

    page.goto(f"{live_server.url}/channels/")

    banner = page.locator("#authBanner")
    banner.wait_for(state="visible", timeout=5000)
    assert banner.is_visible(), "auth banner did not appear on a 403 probe"


def test_auth_banner_hidden_when_probe_succeeds(live_server, page):
    page.route("**/api/version/", _mock_version(200, '{"version": "3.0.0"}'))

    # Wait for the probe's GET to resolve so the hide path has run before we
    # assert; the banner must stay hidden on a successful probe.
    with page.expect_response(
        lambda r: "/api/version/" in r.url and r.request.method != "OPTIONS"
    ):
        page.goto(f"{live_server.url}/channels/")

    assert page.locator("#authBanner").is_hidden(), (
        "auth banner appeared despite a 200 probe"
    )
