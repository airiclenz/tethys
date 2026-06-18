
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
        let objectUrl: string | null = null;    // the currently-shown blob URL
        // Tears down the full-screen click/Escape listeners; null while windowed.
        let fullscreenExit: (() => void) | null = null;

        // A capture size the device advertises, as the status JSON delivers it.
        interface Resolution {
            width: number;
            height: number;
        }


        // ============================================================================
        export function init() {

            // Reinforce on-demand at the client: release the camera when the tab is
            // hidden or the page is being left. The service's idle auto-off is the
            // real guarantee — this just releases the device sooner.
            document.addEventListener("visibilitychange", () => {
                if (document.hidden) {
                    stopCapture(false);
                }
            });
            window.addEventListener("pagehide", () => stopCapture(true));

            // Sync the toggle to the real service state (e.g. left enabled in
            // another tab) so the page reflects reality on load.
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
        async function enable() {

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

            startPolling();
        }


        // ============================================================================
        function disable() {
            stopCapture(false);
        }


        // ============================================================================
        function startPolling() {

            // Guard against a double-start leaving a second interval running.
            if (pollTimer !== null) {
                window.clearInterval(pollTimer);
            }

            showFrameArea();
            tick();                                  // first frame immediately
            pollTimer = window.setInterval(tick, refreshMs);
        }


        // ============================================================================
        async function tick() {

            try {
                const response = await getCall(cameraUrl + "snapshot" + resolutionQuery());

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
                    setStatus("Snapshot failed (" + response.status + ").");
                    return;
                }

                const blob = await response.blob();
                showBlob(blob);
                setStatus("Live — refreshing every " + (refreshMs / 1000) + "s.");
            } catch (e) {
                setStatus("Lost connection to the camera service.");
                console.error("Snapshot fetch failed:", e);
            }
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
        // The "?w=W&h=H" suffix for the snapshot request from the current dropdown
        // selection, or "" when nothing is selected (so the backend uses its default).
        function resolutionQuery(): string {

            const select = getResolutionSelect();
            const value = select ? select.value : "";
            if (!value) {
                return "";
            }

            const [width, height] = value.split("x");
            return "?w=" + width + "&h=" + height;
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
        }

    }
}
