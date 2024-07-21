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
    let schedule;
    (function (schedule_1) {
        let schedules = [];
        let selectedScheduleNumber = null;
        let selectedScheduleIndex = null;
        //let newlyCreatedSchedule = null;
        // ============================================================================
        function getIndexOfScheduleWithId(id) {
            for (let i = 0; i < schedules.length; i++) {
                if (schedules[i].id === id) {
                    return i;
                }
            }
            return -1;
        }
        // ============================================================================
        function deselectAll() {
            selectedScheduleNumber = null;
            selectedScheduleIndex = null;
            tethys.tool.setVisibleState("button-delete", false);
        }
        schedule_1.deselectAll = deselectAll;
        // ============================================================================
        function addNewSchedule() {
            var body = {
                enabled: false,
                weekday: "Monday",
                startTime: "1900-01-01T22:00:00Z",
                durationMinutes: "540",
                scheduleType: "silent"
            };
            console.info(tethys.apiUrl);
            tethys.postCall(tethys.apiUrl + "schedule/", body)
                .then((response) => {
                if (!response.ok) {
                    return;
                }
                const reader = response.body.getReader();
                reader.read()
                    .then((readerResult) => {
                    const resultBody = new TextDecoder().decode(readerResult.value);
                    selectedScheduleNumber = JSON.parse(resultBody).id;
                    tethys.websocket.requestSchedules();
                });
            });
        }
        schedule_1.addNewSchedule = addNewSchedule;
        // ============================================================================
        function deleteSelectedSchedule() {
            return __awaiter(this, void 0, void 0, function* () {
                if (selectedScheduleNumber !== null) {
                    tethys.deleteCall(tethys.apiUrl + "schedule/" + selectedScheduleNumber)
                        .then((response) => {
                        selectedScheduleNumber = null;
                        selectedScheduleIndex = null;
                        toggleSettingsVisibility();
                        tethys.websocket.requestSchedules();
                        tethys.tool.setVisibleState("button-delete", false);
                        console.log("Schedule " +
                            selectedScheduleNumber +
                            " was deleted using the API.");
                    });
                }
            });
        }
        schedule_1.deleteSelectedSchedule = deleteSelectedSchedule;
        // ============================================================================
        function toggleSettingsVisibility(clickedScheduleNumber = null, forceEnable = false) {
            let elementSettings = document.getElementById("idSettings");
            let elementSchedule = null;
            let index = null;
            if (clickedScheduleNumber !== null) {
                elementSchedule = document.getElementById("idSchedule" + clickedScheduleNumber);
                index = getIndexOfScheduleWithId(clickedScheduleNumber);
            }
            if (forceEnable) {
                selectedScheduleNumber = null;
            }
            if (index === -1) {
                return;
            }
            // Select new Schedule
            if (selectedScheduleNumber === null &&
                clickedScheduleNumber !== null) {
                var elementSettingsTitle = document.getElementById("idSettingsTitle");
                elementSettingsTitle.textContent =
                    schedules[index].weekday +
                        " " +
                        tethys.tool.getTimeString(schedules[index].startTime);
                elementSettings.style.display = "block";
                elementSchedule.classList.add("table-row-active");
                tethys.tool.setVisibleState("button-delete", true);
                selectedScheduleNumber = clickedScheduleNumber;
                selectedScheduleIndex = index;
            }
            else {
                // De-select schedule
                if (clickedScheduleNumber === selectedScheduleNumber) {
                    elementSettings.style.display = "none";
                    if (elementSchedule !== null) {
                        elementSchedule.classList.remove("table-row-active");
                    }
                    tethys.tool.setVisibleState("button-delete", false);
                    selectedScheduleNumber = null;
                    selectedScheduleIndex = null;
                }
                // select different schedule or forceEnabled = true
                else {
                    var elementLastSchedule = document.getElementById("idSchedule" + selectedScheduleNumber);
                    var elementSettingsTitle = document.getElementById("idSettingsTitle");
                    elementSettingsTitle.textContent =
                        schedules[index].weekday +
                            " " +
                            tethys.tool.getTimeString(schedules[index].startTime);
                    elementSchedule.classList.add("table-row-active");
                    elementLastSchedule.classList.remove("table-row-active");
                    tethys.tool.setVisibleState("button-delete", true);
                    selectedScheduleNumber = clickedScheduleNumber;
                    selectedScheduleIndex = index;
                }
            }
            updateSettings();
        }
        schedule_1.toggleSettingsVisibility = toggleSettingsVisibility;
        // ============================================================================
        function updateSettings() {
            if (selectedScheduleIndex === null ||
                selectedScheduleIndex === -1) {
                return;
            }
            // Enabled
            var elementOptionEnabled = document.getElementById("idOptionEnabled");
            elementOptionEnabled.checked =
                schedules[selectedScheduleIndex].enabled;
            // ----------------
            // Weekday
            var elementOptionWeekday = document.getElementById("idSelectWeekday");
            elementOptionWeekday.value =
                schedules[selectedScheduleIndex].weekday;
            // Type
            var elementOptionType = document.getElementById("idSelectType");
            elementOptionType.value =
                schedules[selectedScheduleIndex].scheduleType;
            // ----------------
            // Start time
            var elementOptionStartTime = document.getElementById("idOptionStartTime");
            elementOptionStartTime.value =
                tethys.tool.getTimeString(schedules[selectedScheduleIndex].startTime);
            // Duration
            var elementOptionDuration = document.getElementById("idOptionDurationMinutes");
            elementOptionDuration.value =
                schedules[selectedScheduleIndex].durationMinutes;
        }
        schedule_1.updateSettings = updateSettings;
        // ============================================================================
        function updateEnabled() {
            const index = getIndexOfScheduleWithId(selectedScheduleNumber);
            var elementOptionEnabled = document.getElementById("idOptionEnabled");
            var value = elementOptionEnabled.checked;
            var body = { enabled: value };
            if (value != schedules[selectedScheduleIndex].enabled) {
                tethys.putCall(tethys.apiUrl + "schedule/" + selectedScheduleNumber, body)
                    .then((result) => {
                    if (result.ok == true) {
                        schedules[selectedScheduleIndex].enabled = value;
                        formatWeekday(schedules[index]);
                        console.log("Schedule " +
                            selectedScheduleNumber +
                            " - [enabled = " +
                            value +
                            "] was updated using the API.");
                    }
                });
            }
        }
        schedule_1.updateEnabled = updateEnabled;
        // ============================================================================
        //export
        function updateWeekday() {
            const index = getIndexOfScheduleWithId(selectedScheduleNumber);
            var elementOptionWeekday = document.getElementById("idSelectWeekday");
            var selectedIndex = elementOptionWeekday.selectedIndex;
            var value = elementOptionWeekday[selectedIndex].innerText;
            var body = { weekday: value };
            if (value != schedules[index].weekday) {
                tethys.putCall(tethys.apiUrl + "schedule/" + selectedScheduleNumber, body)
                    .then((result) => {
                    if (result.ok == true) {
                        schedules[index].weekday = value;
                        formatWeekday(schedules[index]);
                        console.log("Schedule " +
                            selectedScheduleNumber +
                            " - [weekday = " +
                            value +
                            "] was updated using the API.");
                    }
                });
            }
        }
        schedule_1.updateWeekday = updateWeekday;
        // ============================================================================
        //export
        function updateScheduleType() {
            const index = getIndexOfScheduleWithId(selectedScheduleNumber);
            var elementOptionType = document.getElementById("idSelectType");
            var selectedIndex = elementOptionType.selectedIndex;
            var value = elementOptionType[selectedIndex].innerText;
            var body = { weekday: value };
            if (value != schedules[index].scheduleType) {
                tethys.putCall(tethys.apiUrl + "schedule/" + selectedScheduleNumber, body)
                    .then((result) => {
                    if (result.ok == true) {
                        schedules[index].scheduleType = value;
                        formatScheduleType(schedules[index]);
                        console.log("Schedule " +
                            selectedScheduleNumber +
                            " - [scheduleType = " +
                            value +
                            "] was updated using the API.");
                    }
                });
            }
        }
        schedule_1.updateScheduleType = updateScheduleType;
        // ============================================================================
        //export
        function updateStartTime() {
            const index = getIndexOfScheduleWithId(selectedScheduleNumber);
            var elementStartTime = document.getElementById("idOptionStartTime");
            let timeValue = elementStartTime.value;
            let timeString = "0001-01-01T" + timeValue + ":00Z";
            let body = { startTime: timeString };
            if (timeValue != schedules[index].startTime) {
                tethys.putCall(tethys.apiUrl + "schedule/" + selectedScheduleNumber, body)
                    .then((result) => {
                    if (result.ok == true) {
                        schedules[index].startTime = timeString;
                        formatStartTime(schedules[index]);
                        console.log("Schedule " +
                            selectedScheduleNumber +
                            " - [startTime = " +
                            timeValue +
                            "] was updated using the API.");
                    }
                });
            }
        }
        schedule_1.updateStartTime = updateStartTime;
        // ============================================================================
        function updateDurationMinutes() {
            debugger;
            let index = getIndexOfScheduleWithId(selectedScheduleNumber);
            var elementDurationMinutes = document.getElementById("idOptionDurationMinutes");
            var value = elementDurationMinutes.value;
            var body = { durationMinutes: value };
            if (value != schedules[index].durationMinutes) {
                tethys.putCall(tethys.apiUrl + "schedule/" + selectedScheduleNumber, body)
                    .then((result) => {
                    if (result.ok == true) {
                        schedules[index].durationMinutes = value;
                        formatDurationMinutes(schedules[index]);
                        console.log("Schedule " +
                            selectedScheduleNumber +
                            " - [durationMinutes = " +
                            value +
                            "] was updated using the API.");
                    }
                });
            }
        }
        schedule_1.updateDurationMinutes = updateDurationMinutes;
        // ============================================================================
        function updateDataSet(scheduleData) {
            schedules = scheduleData;
            updateSchedules();
        }
        schedule_1.updateDataSet = updateDataSet;
        // ============================================================================
        function updateSchedules() {
            return __awaiter(this, void 0, void 0, function* () {
                let templatter = new tethys.Templatter("../static/templatter/");
                yield templatter.getTemplate("schedule_row.html");
                let elementScheduleRowDiv = document.getElementById("scheduleRows");
                let scheduleRowDivContent = "";
                schedules.forEach(schedule => {
                    scheduleRowDivContent +=
                        templatter.compile(schedule, tethys.nullString);
                });
                elementScheduleRowDiv.innerHTML = scheduleRowDivContent;
                // ::::::::::::::::::::::::
                // Reformatting of the data
                schedules.forEach(schedule => {
                    if (schedule.id === selectedScheduleNumber) {
                        let elementSchedule = document.getElementById("idSchedule" + schedule.id);
                        elementSchedule.classList.add("table-row-active");
                    }
                    formatData(schedule);
                });
                toggleSettingsVisibility(selectedScheduleNumber, true);
            });
        }
        schedule_1.updateSchedules = updateSchedules;
        // ============================================================================
        function formatData(schedule) {
            formatWeekday(schedule);
            formatStartTime(schedule);
            formatDurationMinutes(schedule);
        }
        // ============================================================================
        function formatWeekday(schedule) {
            var idWeekday = "idSchedule" + schedule.id + "_weekday";
            var elementWeekday = document.getElementById(idWeekday);
            if (elementWeekday === null ||
                elementWeekday === undefined) {
                return;
            }
            if (schedule.enabled == true) {
                elementWeekday.style.backgroundColor = "#6b99ff";
            }
            else {
                elementWeekday.style.backgroundColor = "#cccccc";
            }
            elementWeekday.textContent =
                tethys.tool.pad(schedule.id, 2) +
                    " / " +
                    schedule.weekday;
        }
        // ============================================================================
        function formatStartTime(schedule) {
            let idStartTime = "idSchedule" + schedule.id.toString() + "_startTime";
            var elementStartTime = document.getElementById(idStartTime);
            if (elementStartTime === null ||
                elementStartTime === undefined) {
                return;
            }
            var startTime = new Date(schedule.startTime);
            if (tethys.tool.isValidDate(startTime, false)) {
                var timeString = tethys.tool.getTimeString(startTime);
                elementStartTime.textContent = timeString;
            }
            else {
                elementStartTime.textContent = schedule.startTime;
            }
        }
        // ============================================================================
        function formatDurationMinutes(schedule) {
            var idDurationMinutes = "idSchedule" + schedule.id.toString() + "_duration";
            var elementDurationMinutes = document.getElementById(idDurationMinutes);
            if (elementDurationMinutes === null ||
                elementDurationMinutes === undefined) {
                return;
            }
            let durationString = tethys.tool.getDurationString(schedule.startTime, schedule.durationMinutes);
            elementDurationMinutes.innerHTML = durationString;
        }
        // ============================================================================
        function formatScheduleType(schedule) {
            var idScheduleType = "idSchedule" + (schedule.id) + "_type";
            var elementScheduleType = document.getElementById(idScheduleType);
            if (elementScheduleType === null ||
                elementScheduleType === undefined) {
                return;
            }
            elementScheduleType.textContent = schedule.scheduleType;
        }
        // ============================================================================
        function updateTimes() {
            schedules.forEach(schedule => {
                formatStartTime(schedule);
            });
        }
        schedule_1.updateTimes = updateTimes;
        /*
        // ::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
        var interval = setInterval(updateTimes, 990);
        */
    })(schedule = tethys.schedule || (tethys.schedule = {}));
})(tethys || (tethys = {}));
//# sourceMappingURL=schedule.js.map