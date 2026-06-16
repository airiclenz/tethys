"""Auth tests for the channel-summary WebSocket.

The dashboard receives the channel summary over the WebSocket (``ws/tethys/``,
``TethysConsumer``), NOT over REST. The REST API already requires a valid
``X-API-Key`` and answers 403 without it (``api/tethys_api/permissions.py``), but
the socket used to accept every client unconditionally — so a browser with no/
invalid key still saw live channel data. ``TethysConsumer.connect()`` now gates the
handshake on the same key, presented (base64url-encoded, since browsers can't set
headers on a WebSocket) as the second subprotocol after a ``"tethys"`` marker.

These tests drive the consumer directly with Channels' ``WebsocketCommunicator``
(bypassing the ASGI origin validator so they stay hermetic) and assert the
handshake is accepted only with the correct key. Each async scenario runs in a
dedicated thread with its own event loop (see ``_run_async``) so no
``pytest-asyncio`` dependency is needed and the suite's Playwright tests — which
run their own event loop in the test thread — don't collide with ours.
"""
import asyncio
import base64
import threading

from channels.testing import WebsocketCommunicator

from tethys_web import consumers
from tethys_web.consumers import TethysConsumer

# A deliberately nasty key: the special characters common in real passwords are
# NOT valid WebSocket-subprotocol tokens, so this also proves the base64url
# transport round-trips an arbitrary key.
TEST_KEY = "%{;u#8b29u,r?)%!d={,3-l+q3v.s@0}*1t-xki^:73fp&.;$~m[+9ms5k{_,:se<7?m7mwh)._v-g%z~u^un^wu[0:1am+.p^vn"

MARKER = "tethys"


def _encode(key):
    """Match the frontend's base64UrlEncode: urlsafe alphabet, no padding."""
    return base64.urlsafe_b64encode(key.encode("utf-8")).decode("ascii").rstrip("=")


def _prepare(settings, monkeypatch):
    """Make the consumer hermetic: in-memory channel layer, known key, no polling.

    ``self.channel_layer`` is resolved from Django's ``CHANNEL_LAYERS`` (Redis in
    production); swap it for the in-memory backend so ``group_add`` needs no Redis.
    The consumer reads the key from the ``tethys_web.settings`` *module* (not
    django.conf), so patch it there. ``startPolling`` would spawn a timer that
    calls the real API, so stub it out.
    """
    settings.CHANNEL_LAYERS = {
        "default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}
    }
    monkeypatch.setattr(consumers.settings, "TETHYS_API_KEY", TEST_KEY)
    monkeypatch.setattr(consumers.jobs, "startPolling", lambda: None)


def _run_async(factory):
    """Run an async scenario in a dedicated thread with its own event loop.

    The Playwright UI tests in this suite run a sync-API event loop in the test
    thread, which makes asgiref's ``async_to_sync`` refuse to run here. A fresh
    thread has no running loop, so ``asyncio.run`` works regardless of suite
    ordering. ``factory`` is an async function (a fresh coroutine per call).
    """
    box = {}

    def runner():
        try:
            box["value"] = asyncio.run(factory())
        except BaseException as exc:  # surface failures to the test thread
            box["error"] = exc

    thread = threading.Thread(target=runner)
    thread.start()
    thread.join()
    if "error" in box:
        raise box["error"]
    return box["value"]


def _connect(subprotocols):
    """Open and immediately close a connection; return ``(accepted, value)``."""
    async def scenario():
        communicator = WebsocketCommunicator(
            TethysConsumer.as_asgi(), "/ws/tethys/", subprotocols=subprotocols
        )
        result = await communicator.connect()
        await communicator.disconnect()
        return result

    return _run_async(scenario)


def test_valid_key_is_accepted(settings, monkeypatch):
    _prepare(settings, monkeypatch)

    accepted, subprotocol = _connect([MARKER, _encode(TEST_KEY)])

    assert accepted is True, "correct key was rejected"
    # The server must echo the marker (never the key) for the browser to accept.
    assert subprotocol == MARKER


def test_missing_key_is_rejected(settings, monkeypatch):
    _prepare(settings, monkeypatch)

    # Only the marker, no key entry — mirrors a browser with no key set.
    accepted, _ = _connect([MARKER])

    assert accepted is False, "connection without a key was accepted"


def test_wrong_key_is_rejected(settings, monkeypatch):
    _prepare(settings, monkeypatch)

    accepted, _ = _connect([MARKER, _encode("not-the-key")])

    assert accepted is False, "connection with a wrong key was accepted"


def test_garbage_subprotocol_is_rejected(settings, monkeypatch):
    _prepare(settings, monkeypatch)

    # A non-base64 value must fail decoding and be treated as "no key", not crash.
    accepted, _ = _connect([MARKER, "!!!not-base64!!!"])

    assert accepted is False, "connection with an undecodable key was accepted"


def test_authorized_client_receives_channel_summary(settings, monkeypatch):
    """An authorized client gets channel data — guards against over-rejecting."""
    _prepare(settings, monkeypatch)
    monkeypatch.setattr(
        consumers.tools, "getResponseForSensorSummary", lambda: "summary-payload"
    )

    async def scenario():
        communicator = WebsocketCommunicator(
            TethysConsumer.as_asgi(),
            "/ws/tethys/",
            subprotocols=[MARKER, _encode(TEST_KEY)],
        )
        accepted, _ = await communicator.connect()
        await communicator.send_json_to({"command": "requestChannelSummary"})
        response = await communicator.receive_from()
        await communicator.disconnect()
        return accepted, response

    accepted, response = _run_async(scenario)

    assert accepted is True
    assert response == "summary-payload"
