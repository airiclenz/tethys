
// ============================================================================
// ============================================================================
// ============================================================================
namespace tethys {
    export namespace websocket {

        let webSocket = null;
        let webSocketUri = "";


        // ============================================================================
        export function setWebSocketUrl() {

            var url = new URL(window.location.href);

            webSocketUri =
                "ws://" +
                url.host +
                "/ws/";

            console.log("WebSocket URL: " + webSocketUri);
        }



        // ============================================================================
        export function connect() {

            webSocket = new WebSocket(webSocketUri);
            webSocket.onopen = function (evt) { onOpen(evt) };
            webSocket.onclose = function (evt) { onClose(evt) };
            webSocket.onmessage = function (evt) { onMessage(evt) };
            webSocket.onerror = function (evt) { onError(evt) };


        }


        // ============================================================================
        function onOpen(evt) {

            var location = getSiteLocation();
            var commandString = "";

            switch (location) {

                case tethys.location.channel:
                    requestChannelSummary();
                    break;

                case tethys.location.schedule:
                    requestScheduleSummary();
                    break;
            }

            requestSystemStatus();
            // run every 10 seconds
            setInterval(requestSystemStatus, 30000);

            console.log("WebSocket CONNECTED to ./" + location + "/");
        }


        // ============================================================================
        export function requestChannelSummary() {

            webSocket.send(JSON.stringify({
                command: "requestChannelSummary"
            }));
        }


        // ============================================================================
        export function requestScheduleSummary() {

            webSocket.send(JSON.stringify({
                command: "requestScheduleSummary"
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
        function onClose(evt) {
            console.log("WebSocket DISCONNECTED");
        }

        // ============================================================================
        function onMessage(evt) {

            var data = JSON.parse(evt.data);
            var message = data.message;
            var location = getSiteLocation();

            if (message !== undefined) {
                data = JSON.parse(message);
            }


            if (location === tethys.location.channel &&
                data[0].responseType === "requestChannelSummary") {

                tethys.channel.updateDataSet(data[2].channelSummary);
                tethys.setSilentPhaseStatus(data[1].silentPhaseStatus);
            }

            if (location === tethys.location.schedule &&
                data[0].responseType === "requestScheduleSummary") {

                tethys.schedule.updateDataSet(data[2].scheduleSummary);
                tethys.setSilentPhaseStatus(data[1].silentPhaseStatus);

            }

            if (data[0].responseType === "requestSystemStatus") {
                tethys.setCoreTemperature(data[1].coreTemperature);
                tethys.setCoreServiceState(data[2].coreServiceState);

            }
        }

        // ============================================================================
        function onError(evt) {
            console.log("WebSocket ERROR: " + evt.data);
        }


    }
}