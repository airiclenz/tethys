import base64
import hmac
import json

from asgiref.sync import async_to_sync
from channels.generic.websocket import WebsocketConsumer
from . import settings, tools, jobs


lastUpdateLocal = None
isSilentPhaseLocal = None

# The browser offers this constant marker as its first WebSocket subprotocol and
# the base64url-encoded API key as its second (see _providedApiKey). We echo only
# the marker on accept so the key never appears in the handshake response.
API_KEY_SUBPROTOCOL = "tethys"


class TethysConsumer(WebsocketConsumer):
    # ::::::::::::::::::::::::::::::::::::::::::
    def connect(self):
        # The channel summary is delivered over this WebSocket, fetched server-side
        # with the backend's own key, so without a check here a browser with no/
        # invalid API key would still receive live channel data even though the
        # REST API (api/tethys_api/permissions.py) answers 403 for the same client.
        # Gate the socket behind the same key and reject the handshake (close before
        # accept) so nothing — channel summaries, schedules, or status — is sent.
        if not self._isAuthorized():
            tools.log("Client CONNECT REJECTED (missing/invalid API key) - "
                      + self.channel_name)
            self.close()
            return

        async_to_sync(self.channel_layer.group_add)(
            settings.CHANNEL_GROUP_NAME, self.channel_name
        )

        tools.log("Client CONNECT - " + self.channel_name)

        jobs.startPolling()

        # Echo the marker subprotocol (never the key); the browser requires the
        # server to select one of the protocols it offered.
        self.accept(subprotocol=API_KEY_SUBPROTOCOL)

    # ::::::::::::::::::::::::::::::::::::::::::
    def _providedApiKey(self):
        '''Return the raw API key the client offered, or None.

        Browsers can't set headers (like X-API-Key) on a WebSocket, so the web UI
        sends the key as a second subprotocol: ["tethys", base64url(key)].
        Subprotocol values must be valid HTTP tokens, which exclude many of the
        special characters common in passwords, so the key is base64url-encoded for
        transport and decoded back here. Any decode failure is treated as "no key".
        '''
        subprotocols = self.scope.get("subprotocols", [])
        encoded = next(
            (p for p in subprotocols if p != API_KEY_SUBPROTOCOL), None
        )
        if not encoded:
            return None

        try:
            padding = "=" * (-len(encoded) % 4)
            return base64.urlsafe_b64decode(encoded + padding).decode("utf-8")
        except (ValueError, UnicodeDecodeError):
            return None

    # ::::::::::::::::::::::::::::::::::::::::::
    def _isAuthorized(self):
        '''True only when the client presented the configured API key.

        Mirrors api/tethys_api/permissions.py: fail closed when the server key is
        unset/empty or the client sent nothing, then compare in constant time.
        '''
        expected = getattr(settings, "TETHYS_API_KEY", None)
        provided = self._providedApiKey()
        if not expected or not provided:
            return False
        return hmac.compare_digest(str(provided), str(expected))

    # ::::::::::::::::::::::::::::::::::::::::::
    def disconnect(self, close_code):
        async_to_sync(self.channel_layer.group_discard)(
            settings.CHANNEL_GROUP_NAME, self.channel_name
        )
        tools.log("Channel disconnected...")
        pass


    # ::::::::::::::::::::::::::::::::::::::::::
    # Receive message from WebSocket
    def receive(self, text_data):
        tools.log("Channel received web socket message: " + text_data)

        messageData = ""

        jsonData = json.loads(text_data)
        command = jsonData["command"]

        if command == "requestChannelSummary":
            messageData = tools.getResponseForSensorSummary()

        if command == "requestSchedules":
            messageData = tools.getResponseForSchedules()

        if command == "requestSystemStatus":
            messageData = tools.getReponseForSystemStatus()

        # answer to client
        self.send(text_data = messageData)

        pass

    # ::::::::::::::::::::::::::::::::::::::::::
    # Receive message from room group
    def channelSummary(self, event):
        message = event["message"]

        # Send message to WebSocket
        self.send(text_data=json.dumps({"message": message}))


    # ::::::::::::::::::::::::::::::::::::::::::
    # Receive message from room group
    def scheduleSummary(self, event):
        message = event["message"]

        # Send message to WebSocket
        self.send(text_data=json.dumps({"message": message}))
