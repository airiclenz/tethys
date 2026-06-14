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
    let actions;
    (function (actions) {
        let rows = []; // raw ActionLog records (sorted in place)
        let channel = null; // currently selected channel number
        let sortField = "startTime";
        let sortAsc = false; // default: newest first
        let pendingDelete = null; // { kind: "row", id } | { kind: "all" }
        const numericFields = ["id"];
        const dateFields = ["startTime", "endTime"];
        // ============================================================================
        function init() {
            return __awaiter(this, void 0, void 0, function* () {
                channel = readChannelParam();
                yield loadChannels();
                yield load();
            });
        }
        actions.init = init;
        // ============================================================================
        function readChannelParam() {
            const value = new URLSearchParams(window.location.search).get("channel");
            const parsed = parseInt(value, 10);
            return isNaN(parsed) ? null : parsed;
        }
        // ============================================================================
        // Fill the channel switcher from the channel summary, and make sure the
        // selected channel actually exists (falling back to the first one).
        function loadChannels() {
            return __awaiter(this, void 0, void 0, function* () {
                const select = document.getElementById("idChannelSelect");
                let summaries = [];
                try {
                    const response = yield tethys.getCall(tethys.apiUrl + "channelSummary/");
                    if (response.ok) {
                        const data = yield response.json();
                        summaries = data.channelSummaries || [];
                    }
                }
                catch (e) {
                    console.error("Could not load the channel list:", e);
                }
                let optionsHtml = "";
                summaries.forEach((summary) => {
                    optionsHtml +=
                        '<option value="' + summary.number + '">' +
                            summary.number + " / " + summary.nickName +
                            "</option>";
                });
                select.innerHTML = optionsHtml;
                const numbers = summaries.map((summary) => summary.number);
                if (channel === null || numbers.indexOf(channel) === -1) {
                    channel = numbers.length > 0 ? numbers[0] : 1;
                }
                select.value = String(channel);
            });
        }
        // ============================================================================
        function onChannelChange() {
            const select = document.getElementById("idChannelSelect");
            channel = parseInt(select.value, 10);
            // Keep the URL shareable / reload-safe without a full navigation.
            history.replaceState(null, "", "?channel=" + channel);
            load();
        }
        actions.onChannelChange = onChannelChange;
        // ============================================================================
        function load() {
            return __awaiter(this, void 0, void 0, function* () {
                if (channel === null) {
                    rows = [];
                    render();
                    return;
                }
                try {
                    const response = yield tethys.getCall(tethys.apiUrl + "actionLog/" + channel);
                    if (!response.ok) {
                        rows = [];
                        render();
                        return;
                    }
                    const data = yield response.json();
                    rows = data.actionLogs || [];
                }
                catch (e) {
                    console.error("Could not load channel actions:", e);
                    rows = [];
                }
                render();
            });
        }
        actions.load = load;
        // ============================================================================
        function sortBy(field) {
            if (sortField === field) {
                sortAsc = !sortAsc;
            }
            else {
                sortField = field;
                sortAsc = true;
            }
            render();
        }
        actions.sortBy = sortBy;
        // ============================================================================
        function getDurationMs(row) {
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
                }
                else if (dateFields.indexOf(sortField) !== -1) {
                    av = new Date(a[sortField]).getTime();
                    bv = new Date(b[sortField]).getTime();
                }
                else if (numericFields.indexOf(sortField) !== -1) {
                    av = Number(a[sortField]);
                    bv = Number(b[sortField]);
                }
                else {
                    av = a[sortField];
                    bv = b[sortField];
                }
                // Push null / NaN values to the bottom regardless of direction.
                const aBad = av === null || av === undefined || (typeof av === "number" && isNaN(av));
                const bBad = bv === null || bv === undefined || (typeof bv === "number" && isNaN(bv));
                if (aBad && bBad)
                    return 0;
                if (aBad)
                    return 1;
                if (bBad)
                    return -1;
                if (typeof av === "string") {
                    return av.localeCompare(bv) * factor;
                }
                return (av - bv) * factor;
            });
        }
        // ============================================================================
        function render() {
            return __awaiter(this, void 0, void 0, function* () {
                applySort();
                updateSortIndicators();
                updateDeleteAllButton();
                const container = document.getElementById("actionRows");
                if (rows.length === 0) {
                    container.innerHTML =
                        '<div class="div-row table-row-odd">' +
                            '<div class="div-column div-column-padding col-100" style="color: ' +
                            tethys.nullColor + ';">No actions for this channel.</div>' +
                            "</div>";
                    return;
                }
                let templatter = new tethys.Templatter("../static/templatter/");
                yield templatter.getTemplate("action_row.html");
                let content = "";
                rows.forEach(row => {
                    content += templatter.compile(toDisplay(row), tethys.nullString);
                });
                container.innerHTML = content;
            });
        }
        actions.render = render;
        // ============================================================================
        function toDisplay(row) {
            return {
                id: row.id,
                actionType: row.actionType,
                startTime: formatTimestamp(row.startTime),
                endTime: formatTimestamp(row.endTime),
                duration: formatDuration(row.startTime, row.endTime)
            };
        }
        // ============================================================================
        function formatTimestamp(timestamp) {
            const date = new Date(timestamp);
            if (tethys.tool.isValidDate(date)) {
                return tethys.tool.formatDate(date);
            }
            return tethys.nullString;
        }
        // ============================================================================
        function formatDuration(startTime, endTime) {
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
            }
            else {
                button.style.opacity = "1";
                button.style.pointerEvents = "auto";
            }
        }
        // ============================================================================
        function requestRowDelete(id) {
            pendingDelete = { kind: "row", id: id };
            setMessage("Do you want to delete action #" + id + "?");
        }
        actions.requestRowDelete = requestRowDelete;
        // ============================================================================
        function requestDeleteAll() {
            if (rows.length === 0) {
                return;
            }
            pendingDelete = { kind: "all" };
            setMessage("Do you want to delete ALL " + rows.length +
                " actions for channel " + channel + "?");
        }
        actions.requestDeleteAll = requestDeleteAll;
        // ============================================================================
        function setMessage(message) {
            const element = document.getElementById("idActionsDeleteMessage");
            if (element !== null) {
                element.textContent = message;
            }
        }
        // ============================================================================
        function confirmDelete() {
            if (pendingDelete === null) {
                return;
            }
            const request = pendingDelete;
            pendingDelete = null;
            let url;
            if (request.kind === "row") {
                url = tethys.apiUrl + "actionLog/entry/" + request.id;
            }
            else {
                url = tethys.apiUrl + "actionLog/" + channel;
            }
            tethys.deleteCall(url).then((response) => {
                if (response.ok) {
                    console.log("Channel action(s) deleted using the API.");
                }
                else {
                    console.log("Delete failed: " + response.statusText);
                }
                load();
            });
        }
        actions.confirmDelete = confirmDelete;
    })(actions = tethys.actions || (tethys.actions = {}));
})(tethys || (tethys = {}));
//# sourceMappingURL=actions.js.map