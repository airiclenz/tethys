
// ============================================================================
// ============================================================================
// ============================================================================
// Webcam tab. Talks to the separate tethys-camera service over /camera/ (same
// origin, fronted by nginx). Enabling arms the service; a timer then fetches a
// fresh JPEG every few seconds with the X-API-Key header (an ordinary fetch, so
// no token-in-URL workaround), rendering each via a blob object URL. The service
// auto-disables on idle / the max-on ceiling, so a 409 means "it turned itself
// off" and the UI follows suit.
// ============================================================================
namespace tethys {
    export namespace webcam {

        const cameraUrl = "/camera/";
        // Refresh cadence. Kept comfortably under the service's idle timeout so
        // normal viewing never trips the idle auto-off.
        const refreshMs = 3000;

        // The class that turns the live frame into a full-viewport overlay
        // (web/static/css/main.css). Toggled — never inline-styled — so the UI
        // test can assert on it.
        const fullscreenClass = "camera-fullscreen";

        let pollTimer: number | null = null;
        // Frames shown in the current capture session — reset on each start,
        // surfaced as a small "Frame N" readout (idCameraFrameCount) so it's
        // visible that the live view is actually refreshing.
        let frameCount = 0;
        let objectUrl: string | null = null;    // the currently-shown blob URL
        // Tears down the full-screen click/Escape listeners; null while windowed.
        let fullscreenExit: (() => void) | null = null;
        // Set once a real page teardown (navigation / reload / close) begins. The
        // navigation cancels any in-flight snapshot fetch, which WebKit rejects as
        // "TypeError: Load failed"; this flag lets tick() recognise that benign
        // cancellation and stay quiet instead of logging a spurious error.
        let tearingDown = false;

        // Consecutive failed snapshots in the current session. After
        // maxSnapshotFailures in a row the live poll is stopped (so the browser
        // stops logging a failed request every few seconds) and the camera is
        // treated as "dropped off the bus": the status explains it and the Reset
        // button (a USB re-enumeration) is offered. Reset to 0 by any good frame.
        let snapshotFailures = 0;
        const maxSnapshotFailures = 2;
        // True while a USB-reset round is in flight, so a second click (or a stray
        // tick) can't fire overlapping resets.
        let resetting = false;
        // Floor wait after the API accepts the reset before the live view resumes.
        // Sized to the DETERMINISTIC part of recovery — the controller unbind/rebind
        // and the device re-enumerating (SETTLE_SECONDS + WAIT_SECONDS ≈ 14 s in
        // globals/usb_recovery.py) — so polling never resumes while the device is
        // still guaranteed absent. The variable tail (the tethys-camera restart) is
        // absorbed by the post-reset grace window below, not by this one constant.
        const resetWaitMs = 15000;
        // After the floor wait the camera service may still be restarting, so the
        // first snapshots can fail (a 503) before the device is truly back. For this
        // many ticks a failure is treated as "still coming back": it does NOT count
        // toward maxSnapshotFailures and does NOT re-show Reset — a single good frame
        // ends the window early. This is what makes resume tolerant rather than a bet
        // on one fixed wait matching the backend exactly.
        let postResetGraceTicks = 0;
        const postResetGraceTickCount = 6;

        // A capture size the device advertises, as the status JSON delivers it.
        interface Resolution {
            width: number;
            height: number;
        }

        // An adjustable control's range + initial position, as the status JSON
        // delivers it (only present for controls the camera actually exposes).
        interface ControlSpec {
            min: number;
            max: number;
            step: number;
            value: number;
        }

        // The controls surfaced as sliders. Each maps to an <input type="range">
        // + a <span> readout in index-webcam.html (idCameraFocus/idCameraZoom and
        // …Value), and to a ?<name>= snapshot query param.
        const controlNames = ["focus", "zoom"];
        // Per-device storage key for a slider's last value, so a pick sticks
        // across reloads on the device it was set from.
        function controlStorageKey(name: string): string {
            return "tethys.camera." + name;
        }


        // ============================================================================
        export function init() {

            // Keep the camera running while the tab is merely hidden — a quick
            // app/tab switch shouldn't kill the live view. Release only on a real
            // page teardown (navigation or close), where pagehide fires with
            // persisted === false; a bfcache hide (persisted === true, e.g. an iOS
            // app switch) is left running, with the service's max-on / idle timeout
            // as the real backstop. Not stopping on hide also removes the spurious
            // "access control checks" console error that a normal fetch produced
            // when fired as the page was being frozen.
            window.addEventListener("pagehide", (event) => {
                if (!event.persisted) {
                    tearingDown = true;
                    stopCapture(true);
                }
            });

            // Re-sync to the real service state on load, and again whenever the page
            // is restored from the back/forward cache (returning from another app),
            // so the toggle reflects reality — including a camera the service
            // released (idle / max-on) while we were away.
            window.addEventListener("pageshow", (event) => {
                if (event.persisted) {
                    syncFromStatus();
                }
            });
            syncFromStatus();
        }


        // ============================================================================
        // Called from the Enable flip switch (onchange in the template).
        export function onToggleChange() {

            const toggle = getToggle();

            if (toggle && toggle.checked) {
                enable();
            } else {
                disable();
            }
        }


        // ============================================================================
        // Called from the resolution dropdown (onchange in the template). Re-fetch
        // at the newly-picked size at once instead of waiting for the next poll —
        // but only while capturing, so changing the size with the camera off can't
        // trigger a 409 (which would read as an unexpected auto-off).
        export function onResolutionChange() {
            if (pollTimer !== null) {
                tick();
            }
        }


        // ============================================================================
        // Called continuously while a control slider is dragged (oninput in the
        // template). Updates the numeric readout only — no fetch, so a drag doesn't
        // fire one snapshot per pixel.
        export function onControlInput(name: string) {
            updateReadout(name);
        }


        // ============================================================================
        // Called when a control slider is released (onchange in the template).
        // Persists the pick per-device and re-fetches at the new value at once —
        // but only while capturing, so adjusting a control with the camera off
        // can't trigger a 409 (which would read as an unexpected auto-off).
        export function onControlChange(name: string) {
            const slider = getControlSlider(name);
            if (slider) {
                window.localStorage.setItem(controlStorageKey(name), slider.value);
            }
            if (pollTimer !== null) {
                tick();
            }
        }


        // ============================================================================
        // graceTicks > 0 (a resume after a USB reset) tells startPolling to tolerate
        // a still-restarting camera service for that many ticks; a normal enable
        // (the toggle) passes 0 and gets no grace.
        async function enable(graceTicks: number = 0) {

            setStatus("Starting camera…");

            try {
                const response = await postCall(cameraUrl + "start");

                if (!handleAuth(response)) {
                    return;
                }
                if (!response.ok) {
                    setToggle(false);
                    setStatus("Camera unavailable. Check the camera service.");
                    return;
                }
            } catch (e) {
                setToggle(false);
                setStatus("Could not reach the camera service.");
                console.error("Camera start failed:", e);
                return;
            }

            startPolling(graceTicks);
        }


        // ============================================================================
        function disable() {
            stopCapture(false);
        }


        // ============================================================================
        function startPolling(graceTicks: number = 0) {

            // Guard against a double-start leaving a second interval running.
            if (pollTimer !== null) {
                window.clearInterval(pollTimer);
            }

            // Fresh session: clear any prior failure run and hide the Reset button.
            // graceTicks seeds the post-reset tolerance window (0 for a normal start).
            snapshotFailures = 0;
            postResetGraceTicks = graceTicks;
            showResetButton(false);

            frameCount = 0;
            setFrameCount(null);                     // blank until the first frame
            showFrameArea();
            tick();                                  // first frame immediately
            pollTimer = window.setInterval(tick, refreshMs);
        }


        // ============================================================================
        async function tick() {

            try {
                const response = await getCall(cameraUrl + "snapshot" + snapshotQuery());

                // The service auto-disabled (idle window or max-on ceiling) — follow it.
                if (response.status === 409) {
                    stopPolling();
                    setToggle(false);
                    setStatus("Camera turned off automatically.");
                    return;
                }

                if (!handleAuth(response)) {
                    return;
                }

                if (!response.ok) {
                    await handleSnapshotFailure(response);
                    return;
                }

                snapshotFailures = 0;
                postResetGraceTicks = 0;             // a good frame ends any grace window
                showResetButton(false);
                const blob = await response.blob();
                showBlob(blob);
                setFrameCount(++frameCount);
                setStatus("Live — refreshing every " + (refreshMs / 1000) + "s.");
            } catch (e) {
                // A fetch cancelled by a page teardown (reload / navigation /
                // close) rejects here as "Load failed". That's benign — the page
                // is going away — so stay quiet rather than logging a scary error
                // and overwriting the status. A genuine mid-session drop still
                // reports below.
                if (tearingDown) {
                    return;
                }
                setStatus("Lost connection to the camera service.");
                console.error("Snapshot fetch failed:", e);
            }
        }


        // ============================================================================
        // A snapshot came back non-OK (typically a 503: the grab failed or the
        // device fell off the bus). Surface the real cause from the body; after a
        // couple in a row, stop the poll and offer a USB reset — both so the browser
        // stops logging a failed request every few seconds, and so the user gets a
        // one-click remote recovery.
        async function handleSnapshotFailure(response: Response) {

            // Still inside the post-reset grace window: the camera service is most
            // likely mid-restart, so don't count this toward the give-up threshold
            // or re-show Reset — just report progress and keep polling. A good frame
            // (in tick()) ends the window immediately.
            if (postResetGraceTicks > 0) {
                postResetGraceTicks -= 1;
                setStatus("Camera reconnecting…");
                return;
            }

            snapshotFailures += 1;
            const message = await describeFailure(response);

            if (snapshotFailures >= maxSnapshotFailures) {
                stopPolling();
                setToggle(false);
                setStatus(message + " — try Reset camera.");
                showResetButton(true);
            } else {
                setStatus(message);
            }
        }


        // ============================================================================
        // A human message for a failed snapshot, read from the service's JSON body
        // when present. The camera service's 503 detail names the real cause (e.g.
        // "no V4L2 Video Capture device found under /dev/video*"); an nginx 503
        // (camera service itself down) has no JSON body, so we fall back to the code.
        async function describeFailure(response: Response): Promise<string> {
            try {
                const data = await response.json();
                const detail = String((data && (data.detail || data.error)) || "");
                if (/no v4l2|video capture device|no such|not found|grab failed/i.test(detail)) {
                    return "No camera detected — it dropped off the USB bus.";
                }
                if (detail) {
                    return "Camera error: " + detail;
                }
            } catch (e) {
                // Non-JSON body (e.g. an nginx 503 page) — fall through to the code.
            }
            return "Snapshot failed (" + response.status + ").";
        }


        // ============================================================================
        // Reset camera button. Snapshots are failing because the USB device dropped
        // off the bus; ask the (root) API to re-enumerate the USB controller — the
        // one recovery that works without a physical replug — then re-enable the
        // live view once the device is back. POSTs the key-gated
        // /api/camera/reset-usb/ endpoint (same trust model as reboot).
        export async function resetCamera() {

            if (resetting) {
                return;
            }
            resetting = true;
            setResetButtonEnabled(false);
            setStatus("Resetting camera — re-enumerating USB (up to ~30 s)…");

            try {
                const response = await postCall(tethys.apiUrl + "camera/reset-usb/", {});

                if (!handleAuth(response)) {
                    finishReset();
                    return;
                }
                if (!response.ok) {
                    setStatus("Reset request failed (" + response.status + "). Please try again.");
                    finishReset();
                    return;
                }
            } catch (e) {
                setStatus("Could not reach the API to reset the camera.");
                console.error("Camera USB reset failed:", e);
                finishReset();
                return;
            }

            // The API accepted (202). After the floor wait, resume the live view
            // with a grace window so a camera service still mid-restart doesn't
            // immediately flap back to "failed → Reset": a good frame clears the
            // window and hides Reset; only failures that outlast the grace re-show
            // it. enable(graceTicks) threads the window through to startPolling.
            window.setTimeout(() => {
                finishReset();
                showResetButton(false);
                setToggle(true);
                enable(postResetGraceTickCount);
            }, resetWaitMs);
        }

        // Clear the in-flight guard and re-arm the button (shared by every exit
        // path of resetCamera, so a failure never leaves it stuck disabled).
        function finishReset() {
            resetting = false;
            setResetButtonEnabled(true);
        }


        // ============================================================================
        // Render a freshly-fetched JPEG, revoking the PREVIOUS object URL so the
        // decoded blobs don't accumulate over a long viewing session (the leak the
        // plan calls out).
        function showBlob(blob: Blob) {

            const image = getFrame();
            if (!image) {
                return;
            }

            const nextUrl = URL.createObjectURL(blob);
            image.src = nextUrl;
            image.style.display = "block";

            if (objectUrl) {
                URL.revokeObjectURL(objectUrl);
            }
            objectUrl = nextUrl;
        }


        // ============================================================================
        // Stop polling and release the device. useKeepalive is set on page unload,
        // where a normal fetch may be cancelled. Best-effort only: the service's
        // idle auto-off releases the device regardless, so a dropped stop is not a
        // safety issue.
        function stopCapture(useKeepalive: boolean) {

            stopPolling();
            setToggle(false);
            setStatus("Camera is off.");

            if (useKeepalive) {
                // keepalive lets the request outlive the page. sendBeacon can't be
                // used — it cannot carry the X-API-Key header.
                fetch(cameraUrl + "stop", {
                    method: "POST",
                    keepalive: true,
                    headers: authHeader()
                }).catch(() => { /* page is leaving; nothing to do */ });
            } else {
                postCall(cameraUrl + "stop").catch((e) => {
                    console.error("Camera stop failed:", e);
                });
            }
        }


        // ============================================================================
        // Clear the polling timer and the displayed frame, without POSTing stop
        // (used when the service already stopped, or auth failed).
        function stopPolling() {

            if (pollTimer !== null) {
                window.clearInterval(pollTimer);
                pollTimer = null;
            }

            clearFrame();
        }


        // ============================================================================
        async function syncFromStatus() {

            try {
                const response = await getCall(cameraUrl + "status");
                if (!response.ok) {
                    return;             // 403 etc. — leave off; the auth banner explains it
                }

                const data = await response.json();
                populateResolutions(data.resolutions, data.defaultResolution);
                populateControls(data.controls);
                if (data.enabled) {
                    setToggle(true);
                    startPolling();
                }
            } catch (e) {
                // Camera service unreachable — leave the page in its off state.
            }
        }


        // ============================================================================
        // Fill the resolution dropdown from the device-derived list, pre-selecting
        // the default. Idempotent: once options exist we leave them (and the user's
        // pick) alone, so a later status re-sync never clobbers a selection. An
        // empty/absent list leaves the select empty and disabled, and the snapshot
        // then falls back to the backend default.
        function populateResolutions(resolutions: Resolution[], defaultResolution: Resolution | null) {

            const select = getResolutionSelect();
            if (!select || select.options.length > 0 || !resolutions || resolutions.length === 0) {
                return;
            }

            for (const resolution of resolutions) {
                const option = document.createElement("option");
                option.value = resolution.width + "x" + resolution.height;
                option.textContent = resolution.width + " × " + resolution.height;
                if (defaultResolution
                    && resolution.width === defaultResolution.width
                    && resolution.height === defaultResolution.height) {
                    option.selected = true;
                }
                select.add(option);
            }

            select.disabled = false;
        }


        // ============================================================================
        // Fill the focus/zoom sliders from the camera-derived ranges. For each
        // control the camera exposes: set min/max/step, position it at the stored
        // value (per-device localStorage, so a pick sticks) or the status default,
        // enable it, and show the readout. A control the camera omits stays disabled
        // (greyed) and is never sent. Idempotent: an already-populated slider is left
        // alone, so a later status re-sync never resets a value mid-adjustment.
        function populateControls(controls: { [name: string]: ControlSpec } | undefined) {

            if (!controls) {
                return;
            }

            for (const name of controlNames) {
                const slider = getControlSlider(name);
                const spec = controls[name];
                if (!slider || slider.dataset.populated || !spec) {
                    continue;
                }

                slider.min = String(spec.min);
                slider.max = String(spec.max);
                slider.step = String(spec.step);
                slider.value = String(initialControlValue(name, spec));
                slider.disabled = false;
                slider.dataset.populated = "1";
                updateReadout(name);
            }
        }


        // ============================================================================
        // A slider's starting value: the per-device localStorage pick when it's a
        // number within the camera's range, else the status default. Clamping by
        // range means a stale value stored against a different camera can't push the
        // slider out of bounds.
        function initialControlValue(name: string, spec: ControlSpec): number {

            const raw = window.localStorage.getItem(controlStorageKey(name));
            const stored = raw === null ? NaN : Number(raw);
            if (!isNaN(stored) && stored >= spec.min && stored <= spec.max) {
                return stored;
            }
            return spec.value;
        }


        // ============================================================================
        // The full "?a=1&b=2" suffix for a snapshot request: the picked resolution
        // plus any enabled control sliders. "" when nothing is set, so the backend
        // falls back to its own defaults. One assembler so controls still apply even
        // when no resolution is selected (a plain "&focus=" wouldn't start a query).
        function snapshotQuery(): string {
            const params = resolutionParams().concat(controlParams());
            return params.length ? "?" + params.join("&") : "";
        }


        // ============================================================================
        // ["w=W", "h=H"] from the resolution dropdown, or [] when nothing is selected.
        function resolutionParams(): string[] {

            const select = getResolutionSelect();
            const value = select ? select.value : "";
            if (!value) {
                return [];
            }

            const [width, height] = value.split("x");
            return ["w=" + width, "h=" + height];
        }


        // ============================================================================
        // ["focus=F", "zoom=Z"] from the enabled control sliders. A disabled slider
        // (an unsupported control, or one not yet populated) contributes nothing, so
        // it's never sent — the backend then leaves that control alone.
        function controlParams(): string[] {

            const params: string[] = [];
            for (const name of controlNames) {
                const slider = getControlSlider(name);
                if (slider && !slider.disabled) {
                    params.push(name + "=" + slider.value);
                }
            }
            return params;
        }


        // ============================================================================
        // Returns false (and resets the UI) on a 403, so callers bail. The camera
        // service shares the API key, so the global auth banner — probed on page
        // load — already points the user at Settings.
        function handleAuth(response: Response): boolean {

            if (response.status === 403) {
                stopPolling();
                setToggle(false);
                setStatus("Authentication failed — set the API key in Settings.");
                return false;
            }

            return true;
        }


        // ============================================================================
        // X-API-Key header for the keepalive stop, built from the stored key
        // (common.ts's own header helper is file-private).
        function authHeader(): Record<string, string> {
            const key = getApiKey();
            return key ? { "X-API-Key": key } : {};
        }


        // ============================================================================
        // Toggle the live frame between windowed and a full-viewport CSS overlay.
        // The running poll keeps updating the same <img> underneath, so there's no
        // second image element. A no-op (with a hint) when no frame is showing yet.
        export function toggleFullscreen() {

            const image = getFrame();
            if (!image) {
                return;
            }

            if (image.classList.contains(fullscreenClass)) {
                exitFullscreen();
                return;
            }

            // clearFrame() removes the src when capture is off, so this also covers
            // "camera not enabled yet".
            if (!image.getAttribute("src")) {
                setStatus("Enable the camera first to view it full screen.");
                return;
            }

            enterFullscreen(image);
        }


        // ============================================================================
        // Enter full-screen and register per-session exits (tap the image or press
        // Escape). The teardown closure removes both, so there's no always-on global
        // key handler left behind.
        function enterFullscreen(image: HTMLImageElement) {

            image.classList.add(fullscreenClass);

            const onClick = () => exitFullscreen();
            const onKeydown = (event: KeyboardEvent) => {
                if (event.key === "Escape") {
                    exitFullscreen();
                }
            };

            image.addEventListener("click", onClick);
            document.addEventListener("keydown", onKeydown);

            fullscreenExit = () => {
                image.removeEventListener("click", onClick);
                document.removeEventListener("keydown", onKeydown);
            };
        }


        // ============================================================================
        // Leave full-screen and remove the exit listeners. Idempotent: safe to call
        // when already windowed (e.g. from clearFrame on an auto-off).
        function exitFullscreen() {

            const image = getFrame();
            if (image) {
                image.classList.remove(fullscreenClass);
            }

            if (fullscreenExit) {
                fullscreenExit();
                fullscreenExit = null;
            }
        }


        // -- small DOM helpers ---------------------------------------------------

        function getToggle(): HTMLInputElement | null {
            return document.getElementById("idWebcamEnable") as HTMLInputElement | null;
        }

        function getFrame(): HTMLImageElement | null {
            return document.getElementById("idCameraFrame") as HTMLImageElement | null;
        }

        function getResolutionSelect(): HTMLSelectElement | null {
            return document.getElementById("idCameraResolution") as HTMLSelectElement | null;
        }

        function getResetButton(): HTMLButtonElement | null {
            return document.getElementById("idCameraReset") as HTMLButtonElement | null;
        }

        // Show/hide the Reset button (hidden whenever the live view is healthy).
        function showResetButton(show: boolean) {
            const button = getResetButton();
            if (button) {
                button.hidden = !show;
            }
        }

        // Grey the Reset button out while a reset is in flight, so it can't be
        // double-fired.
        function setResetButtonEnabled(enabled: boolean) {
            const button = getResetButton();
            if (button) {
                button.disabled = !enabled;
            }
        }

        // Control slider/readout ids are "idCamera" + Capitalised name (+ "Value"),
        // e.g. focus -> idCameraFocus / idCameraFocusValue.
        function getControlSlider(name: string): HTMLInputElement | null {
            return document.getElementById("idCamera" + capitalize(name)) as HTMLInputElement | null;
        }

        function getControlReadout(name: string): HTMLElement | null {
            return document.getElementById("idCamera" + capitalize(name) + "Value");
        }

        function updateReadout(name: string) {
            const slider = getControlSlider(name);
            const readout = getControlReadout(name);
            if (slider && readout) {
                readout.textContent = slider.value;
            }
        }

        function capitalize(text: string): string {
            return text.charAt(0).toUpperCase() + text.slice(1);
        }

        function setToggle(on: boolean) {
            const toggle = getToggle();
            if (toggle) {
                toggle.checked = on;
            }
        }

        function setStatus(text: string) {
            const element = document.getElementById("idWebcamStatus");
            if (element) {
                element.textContent = text;
            }
        }

        // The small live frame counter (idCameraFrameCount). null blanks it (camera
        // off / between sessions); a number shows "Frame N".
        function setFrameCount(count: number | null) {
            const element = document.getElementById("idCameraFrameCount");
            if (element) {
                element.textContent = count === null ? "" : "Frame " + count;
            }
        }

        function showFrameArea() {
            const placeholder = document.getElementById("idCameraPlaceholder");
            if (placeholder) {
                placeholder.style.display = "none";
            }
        }

        function clearFrame() {
            // Drop out of full-screen first, so an auto-off mid-view never leaves a
            // black overlay (the frame loses its src below).
            exitFullscreen();

            const image = getFrame();
            if (image) {
                image.removeAttribute("src");
                image.style.display = "none";
            }

            const placeholder = document.getElementById("idCameraPlaceholder");
            if (placeholder) {
                placeholder.style.display = "block";
            }

            if (objectUrl) {
                URL.revokeObjectURL(objectUrl);
                objectUrl = null;
            }

            frameCount = 0;
            setFrameCount(null);
        }

    }
}
