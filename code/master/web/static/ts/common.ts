
// ============================================================================
// ============================================================================
// ============================================================================
namespace tethys {

    const baseApi = ":5000/api/";
    let silentPhaseStatus: any = null;
    let coreTemperature = 0.0;
    let coreServiceState = false;

    //export let webSocket = null;
    export let apiUrl = "";
    export let nullString = "--";
    export let nullColor = "#aaaaaa";


    export const location = {
        channel: "channels",
        schedule: "schedules",
        measurements: "measurements",
        actions: "actions"
    }

    const menuIds: { [key: string]: string } = {
        channels: "menu-sensor-channels",
        schedules: "menu-schedules"
    }



    // ============================================================================
    export function afterPageLoad() {

        setBaseApiUrl();
        tethys.websocket.setWebSocketUrl();
        tethys.websocket.connect();
        updateSilentPhaseStatus();
        markActiveMenu();
        loadApiKeyField();

        // Bootstrap the per-page data view. Runs AFTER setBaseApiUrl() so that
        // tethys.apiUrl is available to the page's REST calls. The channels and
        // schedules pages still bootstrap themselves through the WebSocket.
        switch (getSiteLocation()) {
            case location.measurements:
                tethys.measurements.init();
                break;

            case location.actions:
                tethys.actions.init();
                break;
        }
    }


    // ============================================================================
    // API key (stored locally in the browser). The API requires this key as the
    // `X-API-Key` header on every request, reads included (only the CORS preflight
    // OPTIONS is exempt). The dashboard stays blank until the key is set here.
    // ============================================================================
    const API_KEY_STORAGE = "tethys_api_key";

    export function getApiKey() {
        try {
            return localStorage.getItem(API_KEY_STORAGE) || "";
        } catch (e) {
            return "";
        }
    }

    export function setApiKey(key: string) {
        try {
            localStorage.setItem(API_KEY_STORAGE, (key || "").trim());
        } catch (e) {
            console.error("Could not store the API key:", e);
        }
    }

    // Header object merged into every request (reads and writes); empty when no
    // key is set.
    function authHeaders(): Record<string, string> {
        const key = getApiKey();
        return key ? { "X-API-Key": key } : {};
    }

    // Called from the Settings popup Save button.
    export function saveApiKeyFromField() {
        var element = <HTMLInputElement>(
            (<unknown>document.getElementById("idApiKey"))
        );
        if (element) {
            setApiKey(element.value);
            console.log("API key saved locally.");
        }
    }

    // Populate the Settings field with the stored key on page load.
    function loadApiKeyField() {
        var element = <HTMLInputElement>(
            (<unknown>document.getElementById("idApiKey"))
        );
        if (element) {
            element.value = getApiKey();
        }
    }

    // Toggle the API key field between masked (password) and plain (text), so
    // the user can verify what they pasted. Called from the Settings popup.
    export function toggleApiKeyVisibility() {
        var field = <HTMLInputElement>(
            (<unknown>document.getElementById("idApiKey"))
        );
        var toggle = document.getElementById("idApiKeyToggle");
        if (!field) {
            return;
        }
        if (field.type === "password") {
            field.type = "text";
            if (toggle) { toggle.innerHTML = "Hide"; }
        } else {
            field.type = "password";
            if (toggle) { toggle.innerHTML = "Show"; }
        }
    }


    // ============================================================================
    export function deselectAll() {

        let location = getSiteLocation();
        console.info(location);

        if (location === 'channels') {
            tethys.channel.deselectAll();
        }

        else if (location === 'schedules') {
            tethys.schedule.deselectAll();
        }
    }

    // ============================================================================
    function markActiveMenu() {

        let location =
            getSiteLocation();

        for (const id in menuIds) {
            const idValue = menuIds[id];

            let elementMenu =
                document.getElementById(idValue)!;

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
    export function setSilentPhaseStatus(
        newSilentPhaseStatus: any) {

        silentPhaseStatus = newSilentPhaseStatus;
        updateSilentPhaseStatus();
    }

    // ============================================================================
    export function setCoreTemperature(newCoreTemperature: any) {
        coreTemperature = newCoreTemperature;
        updateCoreTemperature();
    }

    // ============================================================================
    export function setCoreServiceState(newCoreServiceState: any) {
        coreServiceState = newCoreServiceState;
        updateCoreServiceState();
    }


    // ============================================================================
    export function getSiteLocation() {

        let url = new URL(window.location.href);

        let location = url.pathname;
        return tethys.tool.replaceAll(location, "/", "");
    }


    // ============================================================================
    export function updateSilentPhaseStatus() {

        if (silentPhaseStatus === null) {
            return;
        }

        var elementIsSilentPhase = document.getElementById("idIsSilentPhase")!;

        var elementsilentPhaseTooltip = document.getElementById(
            "idSilentPhaseTooltip"
        )!;

        if (silentPhaseStatus.inPhase) {
            elementIsSilentPhase.style.visibility = "visible";

            var start = tethys.tool.formatDate(silentPhaseStatus.startTime);
            var end = tethys.tool.formatDate(silentPhaseStatus.endTime);
            var tooltip = "start: " + start + "<br>end:  " + end;

            elementsilentPhaseTooltip.innerHTML = tooltip;
        } else {
            elementIsSilentPhase.style.visibility = "hidden";
        }
    }

    // ============================================================================
    export function updateCoreTemperature() {

        if (coreTemperature === null) {
            return;
        }

        var elementCoreTemperature = document.getElementById("idCoreTemperature")!;

        elementCoreTemperature.innerHTML = "Pi-Core: " + coreTemperature.toFixed(1) + "°C";
    }


    // ============================================================================
    export function updateCoreServiceState() {

        var elementCoreServiceState = document.getElementById("idCoreServiceState")!;

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


    // ============================================================================
    export function setBaseApiUrl() {

        var url = new URL(window.location.href);

        apiUrl =
            url.protocol +
            "//" +
            url.hostname +
            baseApi;

        console.log("Base API URL:  " + apiUrl);

    }


    // ============================================================================
    export async function postCall(url = "", body = {}) {
        const response = await fetch(url, {
            method: "POST",
            // mode: no-cors, *cors, same-origin
            // *default, no-cache, reload, force-cache, only-if-cached
            cache: "no-cache",
            headers: {
                "Content-Type": "application/json",
                ...authHeaders()
            },
            // manual, *follow, error
            //redirect: 'follow',
            // no-referrer, *no-referrer-when-downgrade, origin, origin-when-cross-origin,
            // same-origin, strict-origin, strict-origin-when-cross-origin, unsafe-url
            //referrerPolicy: 'no-referrer',
            body: JSON.stringify(body)
        });

        return response;
    }


    // ============================================================================
    export async function putCall(url = "", body = {}) {
        const response = await fetch(url, {
            method: "PUT",
            // mode: no-cors, *cors, same-origin
            // *default, no-cache, reload, force-cache, only-if-cached
            cache: "no-cache",
            headers: {
                "Content-Type": "application/json",
                ...authHeaders()
            },
            // manual, *follow, error
            //redirect: 'follow',
            // no-referrer, *no-referrer-when-downgrade, origin, origin-when-cross-origin,
            // same-origin, strict-origin, strict-origin-when-cross-origin, unsafe-url
            //referrerPolicy: 'no-referrer',
            body: JSON.stringify(body)
        });

        return response;
    }

    // ============================================================================
    export async function patchCall(url = "", body = {}) {
        const response = await fetch(url, {
            method: "PATCH",
            // mode: no-cors, *cors, same-origin
            // *default, no-cache, reload, force-cache, only-if-cached
            cache: "no-cache",
            headers: {
                "Content-Type": "application/json",
                ...authHeaders()
            },
            // manual, *follow, error
            //redirect: 'follow',
            // no-referrer, *no-referrer-when-downgrade, origin, origin-when-cross-origin,
            // same-origin, strict-origin, strict-origin-when-cross-origin, unsafe-url
            //referrerPolicy: 'no-referrer',
            body: JSON.stringify(body)
        });

        return response;
    }


    // ============================================================================
    export async function getCall(url = "") {
        const response = await fetch(url, {
            method: "GET",
            // mode: 'no-cors', '*cors', 'same-origin',
            // *default, no-cache, reload, force-cache, only-if-cached
            cache: "no-cache",
            // Reads now require the key too (only OPTIONS is exempt server-side),
            // so the dashboard shows data only once the key is set in Settings.
            headers: {
                ...authHeaders()
            },
            // manual, *follow, error
            //redirect: 'follow',
            // no-referrer, *no-referrer-when-downgrade, origin, origin-when-cross-origin,
            // same-origin, strict-origin, strict-origin-when-cross-origin, unsafe-url
            //referrerPolicy: 'no-referrer',
            //body: JSON.stringify(body)
        });

        return response;
    }


    // ============================================================================
    export async function deleteCall(url = "") {
        const response = await fetch(url, {
            method: "DELETE",
            // mode: 'no-cors', '*cors', 'same-origin',
            // *default, no-cache, reload, force-cache, only-if-cached
            cache: "no-cache",
            headers: {
                ...authHeaders()
            },
            // manual, *follow, error
            //redirect: 'follow',
            // no-referrer, *no-referrer-when-downgrade, origin, origin-when-cross-origin,
            // same-origin, strict-origin, strict-origin-when-cross-origin, unsafe-url
            //referrerPolicy: 'no-referrer',
            //body: JSON.stringify(body)
        });

        return response;
    }

}

