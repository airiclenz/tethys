"use strict";
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
    const baseApi = ":5000/api/";
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
        loadApiKeyField();
    }
    tethys.afterPageLoad = afterPageLoad;
    // ============================================================================
    // API key (stored locally in the browser). The API requires this key as the
    // `X-API-Key` header on every mutating request (POST/PUT/PATCH/DELETE),
    // including manual pump activate/deactivate. Reads (GET) do not need it.
    // ============================================================================
    const API_KEY_STORAGE = "tethys_api_key";
    function getApiKey() {
        try {
            return localStorage.getItem(API_KEY_STORAGE) || "";
        }
        catch (e) {
            return "";
        }
    }
    tethys.getApiKey = getApiKey;
    function setApiKey(key) {
        try {
            localStorage.setItem(API_KEY_STORAGE, (key || "").trim());
        }
        catch (e) {
            console.error("Could not store the API key:", e);
        }
    }
    tethys.setApiKey = setApiKey;
    // Header object merged into every mutating request; empty when no key is set.
    function authHeaders() {
        const key = getApiKey();
        return key ? { "X-API-Key": key } : {};
    }
    // Called from the Settings popup Save button.
    function saveApiKeyFromField() {
        var element = document.getElementById("idApiKey");
        if (element) {
            setApiKey(element.value);
            console.log("API key saved locally.");
        }
    }
    tethys.saveApiKeyFromField = saveApiKeyFromField;
    // Populate the Settings field with the stored key on page load.
    function loadApiKeyField() {
        var element = document.getElementById("idApiKey");
        if (element) {
            element.value = getApiKey();
        }
    }
    // Toggle the API key field between masked (password) and plain (text), so
    // the user can verify what they pasted. Called from the Settings popup.
    function toggleApiKeyVisibility() {
        var field = document.getElementById("idApiKey");
        var toggle = document.getElementById("idApiKeyToggle");
        if (!field) {
            return;
        }
        if (field.type === "password") {
            field.type = "text";
            if (toggle) {
                toggle.innerHTML = "Hide";
            }
        }
        else {
            field.type = "password";
            if (toggle) {
                toggle.innerHTML = "Show";
            }
        }
    }
    tethys.toggleApiKeyVisibility = toggleApiKeyVisibility;
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
    function postCall() {
        return __awaiter(this, arguments, void 0, function* (url = "", body = {}) {
            const response = yield fetch(url, {
                method: "POST",
                // mode: no-cors, *cors, same-origin
                // *default, no-cache, reload, force-cache, only-if-cached
                cache: "no-cache",
                headers: Object.assign({ "Content-Type": "application/json" }, authHeaders()),
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
    function putCall() {
        return __awaiter(this, arguments, void 0, function* (url = "", body = {}) {
            const response = yield fetch(url, {
                method: "PUT",
                // mode: no-cors, *cors, same-origin
                // *default, no-cache, reload, force-cache, only-if-cached
                cache: "no-cache",
                headers: Object.assign({ "Content-Type": "application/json" }, authHeaders()),
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
    function patchCall() {
        return __awaiter(this, arguments, void 0, function* (url = "", body = {}) {
            const response = yield fetch(url, {
                method: "PATCH",
                // mode: no-cors, *cors, same-origin
                // *default, no-cache, reload, force-cache, only-if-cached
                cache: "no-cache",
                headers: Object.assign({ "Content-Type": "application/json" }, authHeaders()),
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
    tethys.patchCall = patchCall;
    // ============================================================================
    function getCall() {
        return __awaiter(this, arguments, void 0, function* (url = "") {
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
    function deleteCall() {
        return __awaiter(this, arguments, void 0, function* (url = "") {
            const response = yield fetch(url, {
                method: "DELETE",
                // mode: 'no-cors', '*cors', 'same-origin',
                // *default, no-cache, reload, force-cache, only-if-cached
                cache: "no-cache",
                headers: Object.assign({}, authHeaders()),
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