
// ============================================================================
// ============================================================================
// ============================================================================
namespace tethys {
    export namespace measurements {

        let rows: any[] = [];             // raw SensorData records (sorted in place)
        let channel: number | null = null; // currently selected channel number
        let sortField = "timestamp";
        let sortAsc = false;              // default: newest first
        let pendingDelete: any = null;    // { kind: "row", id } | { kind: "all" }

        const numericFields = ["id", "moisturePercent", "batteryVoltage"];
        const dateFields = ["timestamp"];


        // ============================================================================
        export async function init() {

            channel = readChannelParam();
            await loadChannels();
            await load();
        }


        // ============================================================================
        function readChannelParam() {

            const value = new URLSearchParams(window.location.search).get("channel");
            const parsed = parseInt(value as string, 10);

            return isNaN(parsed) ? null : parsed;
        }


        // ============================================================================
        // Fill the channel switcher from the channel summary, and make sure the
        // selected channel actually exists (falling back to the first one).
        async function loadChannels() {

            const select = <HTMLSelectElement>(
                (<unknown>document.getElementById("idChannelSelect"))
            );

            let summaries = [];

            try {
                const response = await getCall(apiUrl + "channelSummary/");
                if (response.ok) {
                    const data = await response.json();
                    summaries = data.channelSummaries || [];
                }
            } catch (e) {
                console.error("Could not load the channel list:", e);
            }

            let optionsHtml = "";
            summaries.forEach((summary: any) => {
                optionsHtml +=
                    '<option value="' + summary.number + '">' +
                    summary.number + " / " + summary.nickName +
                    "</option>";
            });
            select.innerHTML = optionsHtml;

            const numbers = summaries.map((summary: any) => summary.number);

            if (channel === null || numbers.indexOf(channel) === -1) {
                channel = numbers.length > 0 ? numbers[0] : 1;
            }

            select.value = String(channel);
        }


        // ============================================================================
        export function onChannelChange() {

            const select = <HTMLSelectElement>(
                (<unknown>document.getElementById("idChannelSelect"))
            );

            channel = parseInt(select.value, 10);

            // Keep the URL shareable / reload-safe without a full navigation.
            history.replaceState(null, "", "?channel=" + channel);

            load();
        }


        // ============================================================================
        export async function load() {

            if (channel === null) {
                rows = [];
                render();
                return;
            }

            try {
                const response = await getCall(apiUrl + "sensorData/" + channel);

                if (!response.ok) {
                    rows = [];
                    render();
                    return;
                }

                const data = await response.json();
                rows = data.sensorData || [];
            } catch (e) {
                console.error("Could not load sensor readings:", e);
                rows = [];
            }

            render();
        }


        // ============================================================================
        export function sortBy(field: string) {

            if (sortField === field) {
                sortAsc = !sortAsc;
            } else {
                sortField = field;
                sortAsc = true;
            }

            render();
        }


        // ============================================================================
        function applySort() {

            const factor = sortAsc ? 1 : -1;

            rows.sort((a, b) => {
                let av = a[sortField];
                let bv = b[sortField];

                if (dateFields.indexOf(sortField) !== -1) {
                    av = new Date(av).getTime();
                    bv = new Date(bv).getTime();
                } else if (numericFields.indexOf(sortField) !== -1) {
                    av = Number(av);
                    bv = Number(bv);
                }

                // Push null / NaN values to the bottom regardless of direction.
                const aBad = av === null || av === undefined || (typeof av === "number" && isNaN(av));
                const bBad = bv === null || bv === undefined || (typeof bv === "number" && isNaN(bv));
                if (aBad && bBad) return 0;
                if (aBad) return 1;
                if (bBad) return -1;

                if (typeof av === "string") {
                    return av.localeCompare(bv) * factor;
                }

                return (av - bv) * factor;
            });
        }


        // ============================================================================
        export async function render() {

            applySort();
            updateSortIndicators();
            updateDeleteAllButton();

            const container = document.getElementById("measurementRows")!;

            if (rows.length === 0) {
                container.innerHTML =
                    '<div class="div-row table-row-odd">' +
                    '<div class="div-column div-column-padding col-100" style="color: ' +
                    tethys.nullColor + ';">No sensor readings for this channel.</div>' +
                    "</div>";
                return;
            }

            let templatter = new Templatter("../static/templatter/");
            await templatter.getTemplate("measurement_row.html");

            let content = "";
            rows.forEach(row => {
                content += templatter.compile(toDisplay(row), tethys.nullString);
            });

            container.innerHTML = content;
        }


        // ============================================================================
        function toDisplay(row: any) {
            return {
                id: row.id,
                timestamp: formatTimestamp(row.timestamp),
                moisture: row.moisturePercent === null ? tethys.nullString : row.moisturePercent + "%",
                battery: formatBattery(row.batteryVoltage)
            };
        }


        // ============================================================================
        function formatTimestamp(timestamp: any) {

            const date = new Date(timestamp);

            if (tethys.tool.isValidDate(date)) {
                return tethys.tool.formatDate(date);
            }

            return tethys.nullString;
        }


        // ============================================================================
        function formatBattery(batteryVoltage: any) {

            if (batteryVoltage === null || batteryVoltage === undefined) {
                return tethys.nullString;
            }

            const voltage = parseFloat(batteryVoltage);
            let result = voltage.toFixed(2) + " V";

            if (voltage < 3.5) {
                result +=
                    "&nbsp;&nbsp;" +
                    '<img src="../static/images/svg/warning.svg" width="14">';
            }

            return result;
        }


        // ============================================================================
        function updateSortIndicators() {

            const fields = ["id", "timestamp", "moisturePercent", "batteryVoltage"];

            fields.forEach(field => {
                const element = document.getElementById("idSortIndicator_" + field);
                if (element === null) {
                    return;
                }
                element.textContent = field === sortField ? (sortAsc ? " ▲" : " ▼") : "";
            });
        }


        // ============================================================================
        function updateDeleteAllButton() {

            const button = document.getElementById("idDeleteAllButton");
            if (button === null) {
                return;
            }

            // Dim and disable the "delete all" affordance when there is nothing
            // to delete.
            if (rows.length === 0) {
                button.style.opacity = "0.3";
                button.style.pointerEvents = "none";
            } else {
                button.style.opacity = "1";
                button.style.pointerEvents = "auto";
            }
        }


        // ============================================================================
        export function requestRowDelete(id: number) {

            pendingDelete = { kind: "row", id: id };

            setMessage("Do you want to delete reading #" + id + "?");
        }


        // ============================================================================
        export function requestDeleteAll() {

            if (rows.length === 0) {
                return;
            }

            pendingDelete = { kind: "all" };

            setMessage(
                "Do you want to delete ALL " + rows.length +
                " readings for channel " + channel + "?");
        }


        // ============================================================================
        function setMessage(message: string) {

            const element = document.getElementById("idMeasurementsDeleteMessage");
            if (element !== null) {
                element.textContent = message;
            }
        }


        // ============================================================================
        export function confirmDelete() {

            if (pendingDelete === null) {
                return;
            }

            const request = pendingDelete;
            pendingDelete = null;

            let url;
            if (request.kind === "row") {
                url = apiUrl + "sensorData/entry/" + request.id;
            } else {
                url = apiUrl + "sensorData/" + channel;
            }

            deleteCall(url).then((response) => {
                if (response.ok) {
                    console.log("Sensor reading(s) deleted using the API.");
                } else {
                    console.log("Delete failed: " + response.statusText);
                }
                load();
            });
        }

    }
}
