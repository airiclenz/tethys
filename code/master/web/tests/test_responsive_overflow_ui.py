"""Regression UI test: no horizontal overflow at phone widths.

When the layout was folded to phone size, an empty strip appeared at the right
edge of *every* page and a horizontal scrollbar showed up. The cause was the
silent-phase tooltip in the shared header (``.tooltip .tooltiptext`` in
main.css): a fixed ``270px``, ``position: absolute`` box anchored near the
top-right that grew *rightward*, off-screen. Although ``visibility: hidden`` by
default, it still laid out and so extended the document's scrollable width — an
invisible strip plus a horizontal scrollbar. The fix anchors the box to its
right edge (so it grows left, into the viewport) and caps its width with a
``max-width`` that keeps it on-screen on both sides down to ~320px.

The offending markup lives in ``layout.html``'s shared header, so the bug — and
this test — applies to every route. We load each page in a narrow viewport and
assert nothing crosses the viewport horizontally.
"""
import pytest

# The four named views; "" just redirects to channels/, so these cover every
# distinct page. All render the shared header where the bug lived.
ROUTES = ["channels/", "schedules/", "measurements/", "actions/"]

# 320 is the tightest mainstream phone — the width where a right-anchored box is
# most at risk of spilling off the *left* edge (what the max-width guards). 390
# is a common modern phone. Both must be clean.
WIDTHS = [320, 390]

# Run in the page: collect any element whose box crosses either viewport edge and
# report the document's horizontal overflow. scrollWidth catches rightward
# overflow (the original bug); the per-element left/right scan also catches a box
# spilling off the left (the failure mode the max-width is there to prevent).
_PROBE_JS = """
() => {
  const docEl = document.documentElement;
  const vw = docEl.clientWidth;
  const offenders = [...document.querySelectorAll('*')]
    .map(el => {
      const r = el.getBoundingClientRect();
      return {
        tag: el.tagName.toLowerCase(),
        id: el.id,
        cls: String(el.className),
        left: Math.round(r.left),
        right: Math.round(r.right),
      };
    })
    .filter(o => o.right > vw + 1 || o.left < -1);
  return { overflow: docEl.scrollWidth - vw, offenders };
}
"""


def _mock_version_ok(route):
    """Answer the on-load ``GET /api/version/`` probe with 200 so the auth banner
    stays hidden and the page sits in its normal authenticated layout. Keeps the
    test hermetic (no real API on :5000 needed) and also satisfies the CORS
    preflight, mirroring test_auth_banner_ui.py."""
    cors = {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Headers": "*",
        "Access-Control-Allow-Methods": "*",
    }
    if route.request.method == "OPTIONS":
        route.fulfill(status=204, headers=cors)
        return
    route.fulfill(
        status=200,
        headers=cors,
        content_type="application/json",
        body='{"version": "test"}',
    )


@pytest.mark.parametrize("width", WIDTHS)
@pytest.mark.parametrize("route", ROUTES)
def test_no_horizontal_overflow_at_phone_width(live_server, page, route, width):
    page.set_viewport_size({"width": width, "height": 720})
    page.route("**/api/version/", _mock_version_ok)

    page.goto(f"{live_server.url}/{route}")

    # The offending element is static markup in the shared header, so it is laid
    # out as soon as the page loads. Wait for it to be in the DOM (it is never
    # "visible" — its container is visibility:hidden until the silent phase),
    # then measure.
    page.wait_for_selector("#idSilentPhaseTooltip", state="attached")

    result = page.evaluate(_PROBE_JS)

    assert result["overflow"] <= 1, (
        f"/{route} at {width}px overflows horizontally by {result['overflow']}px "
        f"(horizontal scrollbar); offending elements: {result['offenders']}"
    )
    assert not result["offenders"], (
        f"/{route} at {width}px has element(s) crossing a viewport edge: "
        f"{result['offenders']}"
    )
