
// ============================================================================
// ============================================================================
// ============================================================================
namespace tethys {
    export namespace websocket {

        let webSocket: any = null;
        let webSocketUri = "";
        let statusInterval: any = null;


        // ============================================================================
        export function setWebSocketUrl() {

            var url = new URL(window.location.href);

            webSocketUri =
                "ws://" +
                url.host +
                "/ws/tethys/";

            console.log("WebSocket URL: " + webSocketUri);
        }



        // ============================================================================
        // base64url-encode a string (UTF-8 safe) so any API key — including the
        // special characters common in passwords — can ride in the WebSocket
        // subprotocol, whose values must be valid HTTP tokens. The backend
        // base64url-decodes it back before validating.
        function base64UrlEncode(value: string): string {
            const bytes = new TextEncoder().encode(value);
            let binary = "";
            bytes.forEach((b) => { binary += String.fromCharCode(b); });
            return btoa(binary)
                .replace(/\+/g, "-")
                .replace(/\//g, "_")
                .replace(/=+$/, "");
        }


        // ============================================================================
        export function connect() {

            // The channel summary is delivered over this socket, and the backend now
            // requires the same API key the REST API does. Browsers can't set headers
            // on a WebSocket, so present the key (from localStorage) as a subprotocol:
            // ["tethys", base64url(key)]. "tethys" is a constant marker the server
            // echoes on accept; the second entry is the encoded key. With no key set
            // we offer only the marker and the server rejects the handshake.
            const key = tethys.getApiKey();
            const protocols = key ? ["tethys", base64UrlEncode(key)] : ["tethys"];

            webSocket = new WebSocket(webSocketUri, protocols);
            webSocket.onopen = function (evt: any) { onOpen(evt) };
            webSocket.onclose = function (evt: any) { onClose(evt) };
            webSocket.onmessage = function (evt: any) { onMessage(evt) };
            webSocket.onerror = function (evt: any) { onError(evt) };


        }


        // ============================================================================
        // Tear down the current socket and reconnect with the latest stored key.
        // Called after the API key changes in Settings so the channel/schedule data
        // appears (or disappears) immediately, without a page reload.
        export function reconnect() {

            if (webSocket !== null) {
                try {
                    // Drop the handler so the teardown doesn't log a spurious close.
                    webSocket.onclose = null;
                    webSocket.close();
                } catch (e) {
                    // Socket may already be closing/closed — nothing to do.
                }
                webSocket = null;
            }

            connect();
        }


        // ============================================================================
        function onOpen(evt: any) {

            var location = getSiteLocation();

            switch (location) {

                case tethys.location.channel:
                    requestChannelSummary();
                    break;

                case tethys.location.schedule:
                    requestSchedules();
                    break;
            }

            requestSystemStatus();
            // run every 30 seconds. Clear any prior interval first so a reconnect
            // (e.g. after the API key changes in Settings) doesn't stack duplicate
            // timers.
            if (statusInterval !== null) {
                clearInterval(statusInterval);
            }
            statusInterval = setInterval(requestSystemStatus, 30000);

            console.log("WebSocket CONNECTED to ./" + location + "/");
        }


        // ============================================================================
        export function requestChannelSummary() {

            webSocket.send(JSON.stringify({
                command: "requestChannelSummary"
            }));
        }


        // ============================================================================
        export function requestSchedules() {

            webSocket.send(JSON.stringify({
                command: "requestSchedules"
            }));
        }

        // ============================================================================
        export function requestSystemStatus() {

            webSocket.send(JSON.stringify({
                command: "requestSystemStatus"
            }));

            console.log("Send command requestSystemStatus");
        }

        // ============================================================================
        function onClose(evt: any) {
            console.log("WebSocket DISCONNECTED");
        }

        // ============================================================================
        function onMessage(evt: any) {

            //debugger;

            var data = JSON.parse(evt.data);
            var message = data.message;
            var location = getSiteLocation();

            if (message !== undefined) {
                data = JSON.parse(message);
            }

            if (location === tethys.location.channel &&
                data.responseType === "requestChannelSummary") {

                tethys.channel.updateDataSet(data.channelSummaries);
            }

            if (location === tethys.location.schedule &&
                data.responseType === "requestSchedules") {

                tethys.schedule.updateDataSet(data.schedules);
            }

            if (data.responseType === "requestSystemStatus") {
                tethys.setCoreTemperature(data.coreTemperature);
                tethys.setCoreServiceState(data.coreServiceState);
                tethys.setSilentPhaseStatus(data.silentPhaseStatus);
            }
        }

        // ============================================================================
        function onError(evt: any) {
            console.log("WebSocket ERROR: " + evt.data);
        }


    }
}