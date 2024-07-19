
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

            switch (location) {

                case tethys.location.channel:
                    requestChannelSummary();
                    break;

                case tethys.location.schedule:
                    requestSchedules();
                    break;
            }

            requestSystemStatus();
            // run every 30 seconds
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
        function onClose(evt) {
            console.log("WebSocket DISCONNECTED");
        }

        // ============================================================================
        function onMessage(evt) {

            //debugger;

            var data = JSON.parse(evt.data);
            var message = data.message;
            var location = getSiteLocation();

            if (message !== undefined) {
                data = JSON.parse(message);
            }

            if (location === tethys.location.channel &&
                data.responseType === "requestChannelSummary") {

                tethys.channel.updateDataSet(data[2].channelSummary);
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
        function onError(evt) {
            console.log("WebSocket ERROR: " + evt.data);
        }


    }
}