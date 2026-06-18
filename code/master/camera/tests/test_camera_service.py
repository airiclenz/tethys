import json

import pytest

from captureBackend import FakeSnapshotBackend
from cameraController import CameraController
from tethys_camera import authorize, route_request

from tests._helpers import collecting_timer_factory

KEY = "correct-key"


def make_controller(backend=None):
    backend = backend if backend is not None else FakeSnapshotBackend()
    factory, _ = collecting_timer_factory()
    controller = CameraController(backend, timer_factory=factory)
    return controller, backend


def headers(key=KEY):
    '''Request headers carrying the given X-API-Key; an empty dict when key is
    None (no header sent at all).'''
    return {"X-API-Key": key} if key is not None else {}


# -- authorize ----------------------------------------------------------------

def test_authorize_accepts_correct_key():
    assert authorize(headers(KEY), KEY) is True


@pytest.mark.parametrize("provided, expected", [
    (None, KEY),        # no client header
    ("", KEY),          # empty client header
    ("wrong", KEY),     # mismatch
    (KEY, ""),          # server key unset -> fail closed
    (KEY, None),        # server key missing -> fail closed
])
def test_authorize_rejects(provided, expected):
    assert authorize(headers(provided), expected) is False


# -- route_request: the HTTP contract (auth + status codes) -------------------

def test_options_is_open_without_key():
    controller, _ = make_controller()

    response = route_request(controller, KEY, "OPTIONS", "/camera/snapshot", headers(None))

    assert response.status == 204


def test_missing_key_is_forbidden():
    controller, _ = make_controller()

    response = route_request(controller, KEY, "GET", "/camera/status", headers(None))

    assert response.status == 403


def test_wrong_key_is_forbidden():
    controller, _ = make_controller()

    response = route_request(controller, KEY, "GET", "/camera/status", headers("nope"))

    assert response.status == 403


def test_status_returns_state():
    controller, _ = make_controller()

    response = route_request(controller, KEY, "GET", "/camera/status", headers())

    assert response.status == 200
    assert json.loads(response.body)["enabled"] is False


def test_start_enables_and_returns_202():
    controller, _ = make_controller()

    response = route_request(controller, KEY, "POST", "/camera/start", headers())

    assert response.status == 202
    assert json.loads(response.body)["enabled"] is True
    assert controller.is_enabled()


def test_snapshot_while_disabled_returns_409():
    controller, _ = make_controller()

    response = route_request(controller, KEY, "GET", "/camera/snapshot", headers())

    assert response.status == 409


def test_snapshot_while_enabled_returns_jpeg():
    controller, _ = make_controller()
    route_request(controller, KEY, "POST", "/camera/start", headers())

    response = route_request(controller, KEY, "GET", "/camera/snapshot", headers())

    assert response.status == 200
    assert response.content_type == "image/jpeg"
    assert response.body == FakeSnapshotBackend.CANNED_JPEG


def test_snapshot_capture_failure_returns_503():
    controller, _ = make_controller(backend=FakeSnapshotBackend(fail=True))
    route_request(controller, KEY, "POST", "/camera/start", headers())

    response = route_request(controller, KEY, "GET", "/camera/snapshot", headers())

    assert response.status == 503


def test_stop_disables_and_returns_202():
    controller, _ = make_controller()
    route_request(controller, KEY, "POST", "/camera/start", headers())

    response = route_request(controller, KEY, "POST", "/camera/stop", headers())

    assert response.status == 202
    assert json.loads(response.body)["enabled"] is False
    assert not controller.is_enabled()


def test_unknown_action_returns_404():
    controller, _ = make_controller()

    response = route_request(controller, KEY, "GET", "/camera/bogus", headers())

    assert response.status == 404


def test_known_action_wrong_method_returns_405():
    controller, _ = make_controller()

    response = route_request(controller, KEY, "GET", "/camera/start", headers())

    assert response.status == 405


def test_snapshot_path_with_query_string_is_routed():
    controller, _ = make_controller()
    route_request(controller, KEY, "POST", "/camera/start", headers())

    response = route_request(controller, KEY, "GET", "/camera/snapshot?ts=123", headers())

    assert response.status == 200


# -- snapshot resolution validation -------------------------------------------
#
# ?w=&h= picks the capture size. FakeSnapshotBackend advertises 1280x720 and
# 640x480, so a listed size passes, an unlisted one is 400, and a malformed
# query is 400 (the only path that emits this brand-new status).

def test_snapshot_with_supported_resolution_returns_jpeg():
    controller, _ = make_controller()
    route_request(controller, KEY, "POST", "/camera/start", headers())

    response = route_request(
        controller, KEY, "GET", "/camera/snapshot?w=1280&h=720", headers()
    )

    assert response.status == 200
    assert response.content_type == "image/jpeg"


def test_snapshot_with_unsupported_resolution_returns_400():
    controller, _ = make_controller()
    route_request(controller, KEY, "POST", "/camera/start", headers())

    response = route_request(
        controller, KEY, "GET", "/camera/snapshot?w=9999&h=9999", headers()
    )

    assert response.status == 400


@pytest.mark.parametrize("query", [
    "?w=abc&h=480",     # non-integer
    "?w=640",           # only one of the pair
    "?w=640&h=0",       # non-positive
])
def test_snapshot_with_malformed_resolution_returns_400(query):
    controller, _ = make_controller()
    route_request(controller, KEY, "POST", "/camera/start", headers())

    response = route_request(controller, KEY, "GET", "/camera/snapshot" + query, headers())

    assert response.status == 400


# -- snapshot focus / zoom validation -----------------------------------------
#
# ?focus=&zoom= pick the capture controls. FakeSnapshotBackend advertises focus
# 300-650 and zoom 100-400, so an in-range value passes (and is forwarded to the
# backend), an out-of-range value is 400, and a non-integer is 400. status()
# carries the same ranges so the UI can build the sliders.

def test_snapshot_with_in_range_focus_and_zoom_returns_jpeg():
    controller, backend = make_controller()
    route_request(controller, KEY, "POST", "/camera/start", headers())

    response = route_request(
        controller, KEY, "GET", "/camera/snapshot?focus=400&zoom=200", headers()
    )

    assert response.status == 200
    assert response.content_type == "image/jpeg"
    assert backend.last_capture == (None, None, 400, 200)


def test_snapshot_with_out_of_range_focus_returns_400():
    controller, _ = make_controller()
    route_request(controller, KEY, "POST", "/camera/start", headers())

    response = route_request(
        controller, KEY, "GET", "/camera/snapshot?focus=9999", headers()
    )

    assert response.status == 400


def test_snapshot_with_non_integer_zoom_returns_400():
    controller, _ = make_controller()
    route_request(controller, KEY, "POST", "/camera/start", headers())

    response = route_request(controller, KEY, "GET", "/camera/snapshot?zoom=abc", headers())

    assert response.status == 400


def test_status_reports_controls():
    controller, _ = make_controller()

    response = route_request(controller, KEY, "GET", "/camera/status", headers())
    controls = json.loads(response.body)["controls"]

    assert controls["focus"] == {"min": 300, "max": 650, "step": 1, "value": 550}
    assert controls["zoom"]["max"] == 400
