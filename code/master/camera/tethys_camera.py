# =============================================================================
# Tethys camera service — a tiny standalone HTTP server for on-demand webcam
# snapshots.
#
# Deliberately NOT folded into tethys-api: the single-worker API (kept single for
# SQLite) must never block on a ~0.3-1 s camera grab. This is stdlib only
# (http.server.ThreadingHTTPServer — no new Python dependency), bound to
# 127.0.0.1:8002 and fronted by nginx at /camera/.
#
# Auth reuses the exact constant-time X-API-Key check the Django API uses
# (api/tethys_api/permissions.py): OPTIONS stays open for CORS preflight; every
# other method must present the key. The request routing and auth are pure
# functions (authorize / route_request) so the full request behaviour — including
# the 409/403/202 status codes — is unit-testable without opening a socket.
# =============================================================================

import hmac
import json
import logging
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import config
from cameraController import CameraController, CameraDisabledError
from captureBackend import CaptureError, V4l2UsbBackend


log = logging.getLogger("tethys.camera")

# nginx forwards the full URI (its proxy_pass has no path), so the backend sees
# the /camera/ prefix; the smoke-test curls hit it directly the same way.
ROUTE_PREFIX = "/camera/"
KNOWN_ACTIONS = ("snapshot", "status", "start", "stop")


# =============================================================================
class Response:
    '''The (status, body, content_type) a route resolves to. Returned by the pure
    router and written out by the request handler — separating the decision from
    the socket is what makes routing testable.'''

    def __init__(self, status, body=b"", content_type="application/json"):
        self.status = status
        self.body = body
        self.content_type = content_type


# =============================================================================
def authorize(headers, expected_key):
    '''Constant-time X-API-Key check, fail-closed — the exact trust model of
    api/tethys_api/permissions.py. Rejects a missing server key or a missing
    client header before comparing.'''
    provided = headers.get("X-API-Key")
    if not expected_key or not provided:
        return False
    return hmac.compare_digest(str(provided), str(expected_key))


# =============================================================================
def route_request(controller, expected_key, method, path, headers):
    '''Resolve one request to a Response. Pure: no sockets, no globals.'''
    # OPTIONS stays open so a browser CORS preflight (which never carries the key)
    # succeeds — matching the API permission.
    if method == "OPTIONS":
        return Response(204)

    if not authorize(headers, expected_key):
        return _json(403, {"error": "A valid X-API-Key header is required."})

    action = _action_from_path(path)

    if action == "snapshot" and method == "GET":
        return _snapshot(controller)
    if action == "status" and method == "GET":
        return _json(200, controller.status())
    if action == "start" and method == "POST":
        return _start(controller)
    if action == "stop" and method == "POST":
        controller.stop()
        return _json(202, {"enabled": False})

    if action in KNOWN_ACTIONS:
        return _json(405, {"error": f"method {method} not allowed for /{action}"})
    return _json(404, {"error": "not found"})


def _start(controller):
    try:
        controller.start()
    except CaptureError as e:
        return _json(503, {"error": "could not start camera", "detail": str(e)})
    return _json(202, {"enabled": True})


def _snapshot(controller):
    try:
        frame = controller.snapshot()
    except CameraDisabledError:
        return _json(409, {"error": "camera is disabled; POST /camera/start first"})
    except CaptureError as e:
        return _json(503, {"error": "camera grab failed", "detail": str(e)})
    return Response(200, frame, "image/jpeg")


def _action_from_path(path):
    '''Strip the query string and the /camera/ prefix, returning the bare action
    (e.g. "snapshot"); empty string if the path is outside the prefix.'''
    path = path.split("?", 1)[0]
    if not path.startswith(ROUTE_PREFIX):
        return ""
    return path[len(ROUTE_PREFIX):].strip("/")


def _json(status, payload):
    body = json.dumps(payload).encode("utf-8")
    return Response(status, body, "application/json")


# =============================================================================
class CameraRequestHandler(BaseHTTPRequestHandler):
    '''Thin socket adapter: delegate the decision to route_request, then write the
    resulting Response. controller / expected_key are bound per server instance
    by make_handler_class.'''

    controller = None
    expected_key = None

    def do_GET(self):
        self._handle("GET")

    def do_POST(self):
        self._handle("POST")

    def do_OPTIONS(self):
        self._handle("OPTIONS")

    def _handle(self, method):
        response = route_request(
            self.controller, self.expected_key, method, self.path, self.headers,
        )
        body = response.body or b""

        self.send_response(response.status)
        self.send_header("Content-Type", response.content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        if body:
            self.wfile.write(body)

    def log_message(self, message_format, *args):
        # Route the stdlib's per-request line through our logger (journald) rather
        # than raw stderr.
        log.info("%s %s", self.address_string(), message_format % args)


# =============================================================================
def make_handler_class(controller, expected_key):
    '''Bind the controller and key to a fresh handler subclass, so each server
    instance has its own (avoids mutating shared class state across instances).'''

    class _BoundHandler(CameraRequestHandler):
        pass

    _BoundHandler.controller = controller
    _BoundHandler.expected_key = expected_key
    return _BoundHandler


# =============================================================================
def make_server():
    '''Production wiring: the one place the USB backend is bound. Returns the
    server and the controller (so the entry point can release the device on
    shutdown).'''
    backend = V4l2UsbBackend()
    controller = CameraController(backend)
    handler = make_handler_class(controller, config.get_api_key())
    server = ThreadingHTTPServer((config.HOST, config.PORT), handler)
    return server, controller


# =============================================================================
def main():
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s",
    )

    server, controller = make_server()
    log.info("tethys-camera listening on %s:%s", config.HOST, config.PORT)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        controller.stop()           # release the device on shutdown (fail-closed)
        server.server_close()


if __name__ == "__main__":
    main()
