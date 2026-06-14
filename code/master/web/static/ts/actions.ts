
// ============================================================================
// ============================================================================
// ============================================================================
namespace tethys {
    export namespace actions {

        let rows: any[] = [];             // raw ActionLog records (sorted in place)
        let channel: number | null = null; // currently selected channel number
        let sortField = "startTime";
        let sortAsc = false;              // default: newest first
        let pendingDelete: any = null;    // { kind: "row", id } | { kind: "all" }

        const numericFields = ["id"];
        const dateFields = ["startTime", "endTime"];


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
                const response = await getCall(apiUrl + "actionLog/" + channel);

                if (!response.ok) {
                    rows = [];
                    render();
                    return;
                }

                const data = await response.json();
                rows = data.actionLogs || [];
            } catch (e) {
                console.error("Could not load channel actions:", e);
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
        function getDurationMs(row: any) {

            const start = new Date(row.startTime).getTime();
            const end = new Date(row.endTime).getTime();

            if (isNaN(start) || isNaN(end)) {
                return NaN;
            }

            return end - start;
        }


        // ============================================================================
        function applySort() {

            const factor = sortAsc ? 1 : -1;

            rows.sort((a, b) => {
                let av;
                let bv;

                if (sortField === "duration") {
                    av = getDurationMs(a);
                    bv = getDurationMs(b);
                } else if (dateFields.indexOf(sortField) !== -1) {
                    av = new Date(a[sortField]).getTime();
                    bv = new Date(b[sortField]).getTime();
                } else if (numericFields.indexOf(sortField) !== -1) {
                    av = Number(a[sortField]);
                    bv = Number(b[sortField]);
                } else {
                    av = a[sortField];
                    bv = b[sortField];
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

            const container = document.getElementById("actionRows")!;

            if (rows.length === 0) {
                container.innerHTML =
                    '<div class="div-row table-row-odd">' +
                    '<div class="div-column div-column-padding col-100" style="color: ' +
                    tethys.nullColor + ';">No actions for this channel.</div>' +
                    "</div>";
                return;
            }

            let templatter = new Templatter("../static/templatter/");
            await templatter.getTemplate("action_row.html");

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
                actionType: row.actionType,
                startTime: formatTimestamp(row.startTime),
                endTime: formatTimestamp(row.endTime),
                duration: formatDuration(row.startTime, row.endTime)
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
        function formatDuration(startTime: any, endTime: any) {

            const start = new Date(startTime);
            const end = new Date(endTime);

            if (!tethys.tool.isValidDate(start) || !tethys.tool.isValidDate(end)) {
                return tethys.nullString;
            }

            let totalSeconds = Math.round((end.getTime() - start.getTime()) / 1000);
            if (totalSeconds < 0) {
                totalSeconds = 0;
            }

            const hours = Math.floor(totalSeconds / 3600);
            totalSeconds -= hours * 3600;
            const minutes = Math.floor(totalSeconds / 60);
            const seconds = totalSeconds - minutes * 60;

            if (hours > 0) {
                return tethys.tool.pad(hours, 2) + "h " +
                    tethys.tool.pad(minutes, 2) + "m " +
                    tethys.tool.pad(seconds, 2) + "s";
            }

            return tethys.tool.pad(minutes, 2) + ":" + tethys.tool.pad(seconds, 2);
        }


        // ============================================================================
        function updateSortIndicators() {

            const fields = ["id", "actionType", "startTime", "endTime", "duration"];

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

            setMessage("Do you want to delete action #" + id + "?");
        }


        // ============================================================================
        export function requestDeleteAll() {

            if (rows.length === 0) {
                return;
            }

            pendingDelete = { kind: "all" };

            setMessage(
                "Do you want to delete ALL " + rows.length +
                " actions for channel " + channel + "?");
        }


        // ============================================================================
        function setMessage(message: string) {

            const element = document.getElementById("idActionsDeleteMessage");
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
                url = apiUrl + "actionLog/entry/" + request.id;
            } else {
                url = apiUrl + "actionLog/" + channel;
            }

            deleteCall(url).then((response) => {
                if (response.ok) {
                    console.log("Channel action(s) deleted using the API.");
                } else {
                    console.log("Delete failed: " + response.statusText);
                }
                load();
            });
        }

    }
}
