"""UI test for the Webcam tab.

The tab talks to the separate tethys-camera service over /camera/, which is not
running during the test. We intercept those calls with Playwright routes (a
disabled status, a 202 on start, a stub JPEG on snapshot) and assert that: the
tab renders, the nav item highlights as active, and flipping Enable starts
capture and shows a live frame — i.e. the whole client wiring
(common.ts init switch -> webcam.ts -> /camera/) holds together.
"""

# Minimal JPEG (SOI + EOI). createObjectURL accepts any bytes; the test asserts
# on the resulting blob: URL and the status text, not on the decoded pixels.
STUB_JPEG = b"\xff\xd8\xff\xd9"


def test_webcam_tab_enables_and_shows_frame(live_server, page):
    # Fail the test on any uncaught page exception (same guard as the channels test).
    page_errors = []
    page.on("pageerror", lambda exc: page_errors.append(str(exc)))

    calls = {"start": 0, "snapshot": 0}

    def fulfill_json(route, status, body):
        route.fulfill(status=status, content_type="application/json", body=body)

    page.route(
        "**/camera/status",
        lambda route: fulfill_json(
            route, 200,
            '{"enabled": false, "lastFrameAgeSec": null, "device": "fake", "refreshSeconds": 3}',
        ),
    )

    def handle_start(route):
        calls["start"] += 1
        fulfill_json(route, 202, '{"enabled": true}')

    def handle_snapshot(route):
        calls["snapshot"] += 1
        route.fulfill(status=200, content_type="image/jpeg", body=STUB_JPEG)

    page.route("**/camera/start", handle_start)
    page.route("**/camera/snapshot*", handle_snapshot)
    page.route("**/camera/stop", lambda route: fulfill_json(route, 202, '{"enabled": false}'))

    page.goto(f"{live_server.url}/webcam/")

    # Wait until the webcam module has loaded before driving it.
    page.wait_for_function("() => window.tethys && window.tethys.webcam")

    # The Webcam nav item highlights as active (markActiveMenu paints the active
    # background #003355 = rgb(0, 51, 85)).
    nav_background = page.eval_on_selector(
        "#menu-webcam", "el => getComputedStyle(el).backgroundColor"
    )
    assert nav_background == "rgb(0, 51, 85)", f"nav not highlighted: {nav_background}"

    # The page starts off: placeholder visible, no frame.
    assert page.locator("#idCameraPlaceholder").is_visible()

    # Flip Enable on -> arms the service and starts the snapshot loop. The real
    # checkbox is hidden by the flipswitch CSS (opacity:0), so click the visible
    # label (the switch itself), which is what a user clicks.
    page.click("label.switch")

    # Once the first mocked snapshot lands, the status flips to "Live …".
    page.wait_for_function(
        "() => document.getElementById('idWebcamStatus')"
        ".textContent.indexOf('Live') !== -1"
    )

    assert calls["start"] == 1
    assert calls["snapshot"] >= 1

    # The frame is rendered from a blob object URL and the placeholder is hidden.
    frame_src = page.eval_on_selector("#idCameraFrame", "el => el.src")
    assert frame_src.startswith("blob:"), f"frame src was {frame_src!r}"

    placeholder_display = page.eval_on_selector(
        "#idCameraPlaceholder", "el => getComputedStyle(el).display"
    )
    assert placeholder_display == "none"

    assert not page_errors, f"uncaught JS error(s) on the page: {page_errors}"
