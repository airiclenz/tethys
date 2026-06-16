"""Regression UI test for the sparse-channel settings crash.

Channels are numbered, not array-indexed, and may be non-contiguous (the device
supports 5 channels but a user might configure only 1, 2 and 5). The channel
settings code used to look a channel up with ``channels[number - 1]``, assuming a
dense array. Clicking channel 5 then evaluated ``channels[4]`` on a 3-element
array and threw ``TypeError: undefined is not an object``, so the settings panel
never opened.

This test reproduces that exact setup in a real browser: it loads the channels
page, injects channels 1/2/5 through the page's own render path, clicks channel
5, and asserts the settings panel opens with the right title and that nothing
threw on the page.
"""

# A channel object as the websocket delivers it. Every field the row-render path
# reads is present; the data fields are null so the "no data yet" branches are
# taken (this test only cares about selecting the row, not its readings).
def _channel(number, nick_name):
    return {
        "number": number,
        "nickName": nick_name,
        "enabled": True,
        "channelType": "pump",
        "sensorData_lastMoisturePercent": None,
        "sensorData_lastBatteryVoltage": None,
        "sensorData_count": None,
        "sensorData_lastTimestamp": None,
        "action_count": None,
        "actionLog_count": 0,
        "actionLog_lastStartTime": None,
    }


# Deliberately non-contiguous: 5 is the failure case (channels[5-1] is undefined).
SPARSE_CHANNELS = [
    _channel(1, "Front bed"),
    _channel(2, "Back bed"),
    _channel(5, "Greenhouse"),
]


def test_clicking_sparse_numbered_channel_opens_settings(live_server, page):
    # Fail the test if any uncaught exception fires on the page — the original
    # bug surfaced as exactly such a TypeError.
    page_errors = []
    page.on("pageerror", lambda exc: page_errors.append(str(exc)))

    page.goto(f"{live_server.url}/channels/")

    # Wait until the channel module has loaded before driving it.
    page.wait_for_function(
        "() => window.tethys && window.tethys.channel "
        "&& typeof window.tethys.channel.updateDataSet === 'function'"
    )

    # Feed the sparse channel set in through the real render path (the same call
    # the websocket handler makes), then wait for channel 5's row to render.
    page.evaluate("(channels) => window.tethys.channel.updateDataSet(channels)", SPARSE_CHANNELS)
    page.wait_for_selector("#idChannel5")

    # Select channel 5 — this is the click that used to crash.
    page.click("#idChannel5")

    # On success the panel shows immediately; 5s is generous and keeps a
    # regression (panel never opens because the click threw) from hanging 30s.
    settings_panel = page.locator("#idSettings")
    settings_panel.wait_for(state="visible", timeout=5000)
    assert settings_panel.is_visible(), "settings panel did not open for channel 5"

    title = page.locator("#idSettingsTitle").inner_text()
    assert "5 /" in title, f"settings title was {title!r}, expected it to start with '5 /'"

    assert not page_errors, f"uncaught JS error(s) on the page: {page_errors}"
