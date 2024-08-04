var __awaiter = (this && this.__awaiter) || function (thisArg, _arguments, P, generator) {
    function adopt(value) { return value instanceof P ? value : new P(function (resolve) { resolve(value); }); }
    return new (P || (P = Promise))(function (resolve, reject) {
        function fulfilled(value) { try { step(generator.next(value)); } catch (e) { reject(e); } }
        function rejected(value) { try { step(generator["throw"](value)); } catch (e) { reject(e); } }
        function step(result) { result.done ? resolve(result.value) : adopt(result.value).then(fulfilled, rejected); }
        step((generator = generator.apply(thisArg, _arguments || [])).next());
    });
};
// ============================================================================
// ============================================================================
// ============================================================================
var tethys;
(function (tethys) {
    const baseApi = ":5001/api/";
    let silentPhaseStatus = null;
    let coreTemperature = 0.0;
    let coreServiceState = false;
    //export let webSocket = null;
    tethys.apiUrl = "";
    tethys.nullString = "--";
    tethys.nullColor = "#aaaaaa";
    tethys.location = {
        channel: "channels",
        schedule: "schedules"
    };
    const menuIds = {
        channels: "menu-sensor-channels",
        schedules: "menu-schedules"
    };
    // ============================================================================
    function afterPageLoad() {
        setBaseApiUrl();
        tethys.websocket.setWebSocketUrl();
        tethys.websocket.connect();
        updateSilentPhaseStatus();
        markActiveMenu();
    }
    tethys.afterPageLoad = afterPageLoad;
    // ============================================================================
    function deselectAll() {
        let location = getSiteLocation();
        console.info(location);
        if (location === 'channels') {
            tethys.channel.deselectAll();
        }
        else if (location === 'schedules') {
            tethys.schedule.deselectAll();
        }
    }
    tethys.deselectAll = deselectAll;
    // ============================================================================
    function markActiveMenu() {
        let location = getSiteLocation();
        for (const id in menuIds) {
            const idValue = menuIds[id];
            let elementMenu = document.getElementById(idValue);
            if (id === location) {
                elementMenu.style.color = "#FFFFFF";
                elementMenu.style.backgroundColor = "#003355";
            }
            else {
                elementMenu.style.backgroundColor = "#000000";
            }
        }
    }
    // ============================================================================
    function setSilentPhaseStatus(newSilentPhaseStatus) {
        silentPhaseStatus = newSilentPhaseStatus;
        updateSilentPhaseStatus();
    }
    tethys.setSilentPhaseStatus = setSilentPhaseStatus;
    // ============================================================================
    function setCoreTemperature(newCoreTemperature) {
        coreTemperature = newCoreTemperature;
        updateCoreTemperature();
    }
    tethys.setCoreTemperature = setCoreTemperature;
    // ============================================================================
    function setCoreServiceState(newCoreServiceState) {
        coreServiceState = newCoreServiceState;
        updateCoreServiceState();
    }
    tethys.setCoreServiceState = setCoreServiceState;
    // ============================================================================
    function getSiteLocation() {
        let url = new URL(window.location.href);
        let location = url.pathname;
        return tethys.tool.replaceAll(location, "/", "");
    }
    tethys.getSiteLocation = getSiteLocation;
    // ============================================================================
    function updateSilentPhaseStatus() {
        if (silentPhaseStatus === null) {
            return;
        }
        var elementIsSilentPhase = document.getElementById("idIsSilentPhase");
        var elementsilentPhaseTooltip = document.getElementById("idSilentPhaseTooltip");
        if (silentPhaseStatus.inPhase) {
            elementIsSilentPhase.style.visibility = "visible";
            var start = tethys.tool.formatDate(silentPhaseStatus.startTime);
            var end = tethys.tool.formatDate(silentPhaseStatus.endTime);
            var tooltip = "start: " + start + "<br>end:  " + end;
            elementsilentPhaseTooltip.innerHTML = tooltip;
        }
        else {
            elementIsSilentPhase.style.visibility = "hidden";
        }
    }
    tethys.updateSilentPhaseStatus = updateSilentPhaseStatus;
    // ============================================================================
    function updateCoreTemperature() {
        if (coreTemperature === null) {
            return;
        }
        var elementCoreTemperature = document.getElementById("idCoreTemperature");
        elementCoreTemperature.innerHTML = "Pi-Core: " + coreTemperature.toFixed(1) + "°C";
    }
    tethys.updateCoreTemperature = updateCoreTemperature;
    // ============================================================================
    function updateCoreServiceState() {
        var elementCoreServiceState = document.getElementById("idCoreServiceState");
        if (coreServiceState === null) {
            elementCoreServiceState.innerHTML = "Core-Service: --";
            return;
        }
        if (coreServiceState) {
            elementCoreServiceState.innerHTML = "Core-Service: Running";
        }
        else {
            elementCoreServiceState.innerHTML = "Core-Service: OFF";
        }
    }
    tethys.updateCoreServiceState = updateCoreServiceState;
    // ============================================================================
    function setBaseApiUrl() {
        var url = new URL(window.location.href);
        tethys.apiUrl =
            url.protocol +
                "//" +
                url.hostname +
                baseApi;
        console.log("Base API URL:  " + tethys.apiUrl);
    }
    tethys.setBaseApiUrl = setBaseApiUrl;
    // ============================================================================
    function postCall(url = "", body = {}) {
        return __awaiter(this, void 0, void 0, function* () {
            const response = yield fetch(url, {
                method: "POST",
                // mode: no-cors, *cors, same-origin
                // *default, no-cache, reload, force-cache, only-if-cached
                cache: "no-cache",
                headers: {
                    "Content-Type": "application/json"
                },
                // manual, *follow, error
                //redirect: 'follow',
                // no-referrer, *no-referrer-when-downgrade, origin, origin-when-cross-origin,
                // same-origin, strict-origin, strict-origin-when-cross-origin, unsafe-url
                //referrerPolicy: 'no-referrer',
                body: JSON.stringify(body)
            });
            return response;
        });
    }
    tethys.postCall = postCall;
    // ============================================================================
    function putCall(url = "", body = {}) {
        return __awaiter(this, void 0, void 0, function* () {
            const response = yield fetch(url, {
                method: "PUT",
                // mode: no-cors, *cors, same-origin
                // *default, no-cache, reload, force-cache, only-if-cached
                cache: "no-cache",
                headers: {
                    "Content-Type": "application/json"
                },
                // manual, *follow, error
                //redirect: 'follow',
                // no-referrer, *no-referrer-when-downgrade, origin, origin-when-cross-origin,
                // same-origin, strict-origin, strict-origin-when-cross-origin, unsafe-url
                //referrerPolicy: 'no-referrer',
                body: JSON.stringify(body)
            });
            return response;
        });
    }
    tethys.putCall = putCall;
    // ============================================================================
    function getCall(url = "") {
        return __awaiter(this, void 0, void 0, function* () {
            const response = yield fetch(url, {
                method: "GET",
                // mode: 'no-cors', '*cors', 'same-origin',
                // *default, no-cache, reload, force-cache, only-if-cached
                cache: "no-cache"
                //headers: { 'Content-Type': 'application/json' },
                // manual, *follow, error
                //redirect: 'follow',
                // no-referrer, *no-referrer-when-downgrade, origin, origin-when-cross-origin,
                // same-origin, strict-origin, strict-origin-when-cross-origin, unsafe-url
                //referrerPolicy: 'no-referrer',
                //body: JSON.stringify(body)
            });
            return response;
        });
    }
    tethys.getCall = getCall;
    // ============================================================================
    function deleteCall(url = "") {
        return __awaiter(this, void 0, void 0, function* () {
            const response = yield fetch(url, {
                method: "DELETE",
                // mode: 'no-cors', '*cors', 'same-origin',
                // *default, no-cache, reload, force-cache, only-if-cached
                cache: "no-cache"
                //headers: { 'Content-Type': 'application/json' },
                // manual, *follow, error
                //redirect: 'follow',
                // no-referrer, *no-referrer-when-downgrade, origin, origin-when-cross-origin,
                // same-origin, strict-origin, strict-origin-when-cross-origin, unsafe-url
                //referrerPolicy: 'no-referrer',
                //body: JSON.stringify(body)
            });
            return response;
        });
    }
    tethys.deleteCall = deleteCall;
})(tethys || (tethys = {}));
//# sourceMappingURL=common.js.map