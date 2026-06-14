
// ============================================================================
// ============================================================================
// ============================================================================
namespace tethys {
    export namespace schedule {

        let schedules: any[] = [];
        let selectedScheduleNumber: number | null = null;
        let selectedScheduleIndex: any = null;
        //let newlyCreatedSchedule = null;


        // ============================================================================
        function getIndexOfScheduleWithId(id: any) {

            for (let i = 0; i < schedules.length; i++) {
                if (schedules[i].id === id) {
                    return i;
                }
            }

            return -1;
        }

        // ============================================================================
        export function deselectAll() {
            selectedScheduleNumber = null;
            selectedScheduleIndex = null;

            tethys.tool.setVisibleState("button-delete", false);
        }


        // ============================================================================
        export function addNewSchedule() {

            var body = {
                enabled: false,
                weekday: "Monday",
                startTime: "1900-01-01T22:00:00Z",
                durationMinutes: "540",
                scheduleType: "silent"
            };

            console.info(tethys.apiUrl);

            postCall(tethys.apiUrl + "schedule/", body)
                .then((response) => {

                    if (!response.ok) {
                        return;
                    }

                    const reader = response.body!.getReader();

                    reader.read()
                        .then((readerResult) => {

                            const resultBody = new TextDecoder().decode(readerResult.value);
                            selectedScheduleNumber = JSON.parse(resultBody).id;

                            tethys.websocket.requestSchedules();
                        });
                });

        }


        // ============================================================================
        export async function deleteSelectedSchedule() {

            if (selectedScheduleNumber !== null) {

                deleteCall(apiUrl + "schedule/" + selectedScheduleNumber)
                    .then((response) => {

                        selectedScheduleNumber = null;
                        selectedScheduleIndex = null;
                        toggleSettingsVisibility()

                        tethys.websocket.requestSchedules();
                        tethys.tool.setVisibleState("button-delete", false);

                        console.log(
                            "Schedule " +
                            selectedScheduleNumber +
                            " was deleted using the API.");
                    });


            }
        }


        // ============================================================================
        export function toggleSettingsVisibility(
            clickedScheduleNumber: any = null,
            forceEnable = false) {

            let elementSettings = document.getElementById("idSettings")!;
            let elementSchedule = null;
            let index: any = null;

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

                var elementSettingsTitle = document.getElementById("idSettingsTitle")!;

                elementSettingsTitle.textContent =
                    schedules[index].weekday +
                    " " +
                    tethys.tool.getTimeString(schedules[index].startTime);
                elementSettings.style.display = "block";
                elementSchedule!.classList.add("table-row-active");

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
                    var elementLastSchedule = document.getElementById(
                        "idSchedule" + selectedScheduleNumber
                    )!;

                    var elementSettingsTitle =
                        document.getElementById("idSettingsTitle")!;

                    elementSettingsTitle.textContent =
                        schedules[index].weekday +
                        " " +
                        tethys.tool.getTimeString(schedules[index].startTime);
                    elementSchedule!.classList.add("table-row-active");
                    elementLastSchedule.classList.remove("table-row-active");

                    tethys.tool.setVisibleState("button-delete", true);

                    selectedScheduleNumber = clickedScheduleNumber;
                    selectedScheduleIndex = index;
                }
            }

            updateSettings();
        }




        // ============================================================================
        export function updateSettings() {

            if (selectedScheduleIndex === null ||
                selectedScheduleIndex === -1) {
                return;
            }

            // Enabled
            var elementOptionEnabled = <HTMLInputElement>(
                (<unknown>document.getElementById("idOptionEnabled"))
            );
            elementOptionEnabled.checked =
                schedules[selectedScheduleIndex].enabled;

            // ----------------
            // Weekday
            var elementOptionWeekday = <HTMLSelectElement>(
                (<unknown>document.getElementById("idSelectWeekday"))
            );
            elementOptionWeekday.value =
                schedules[selectedScheduleIndex].weekday;

            // Type
            var elementOptionType = <HTMLSelectElement>(
                (<unknown>document.getElementById("idSelectType"))
            );
            elementOptionType.value =
                schedules[selectedScheduleIndex].scheduleType;

            // ----------------
            // Start time
            var elementOptionStartTime = <HTMLInputElement>(
                (<unknown>document.getElementById("idOptionStartTime"))
            );
            elementOptionStartTime.value =
                tethys.tool.getTimeString(
                    schedules[selectedScheduleIndex].startTime);

            // Duration
            var elementOptionDuration = <HTMLInputElement>(
                (<unknown>document.getElementById("idOptionDurationMinutes"))
            );
            elementOptionDuration.value =
                schedules[selectedScheduleIndex].durationMinutes;

        }


        // ============================================================================
        export function updateEnabled() {
            const index = getIndexOfScheduleWithId(selectedScheduleNumber);

            var elementOptionEnabled = <HTMLInputElement>(
                (<unknown>document.getElementById("idOptionEnabled"))
            );
            var value = elementOptionEnabled.checked;
            var body = { enabled: value };

            if (value != schedules[selectedScheduleIndex].enabled) {
                putCall(apiUrl + "schedule/" + selectedScheduleNumber, body)
                    .then((result) => {
                        if (result.ok == true) {
                            schedules[selectedScheduleIndex].enabled = value;

                            formatWeekday(schedules[index]);

                            console.log(
                                "Schedule " +
                                selectedScheduleNumber +
                                " - [enabled = " +
                                value +
                                "] was updated using the API."
                            );
                        }
                    });
            }
        }


        // ============================================================================
        //export
        export function updateWeekday() {
            const index = getIndexOfScheduleWithId(selectedScheduleNumber);

            var elementOptionWeekday = <HTMLSelectElement>(
                (<unknown>document.getElementById("idSelectWeekday"))
            );

            var selectedIndex = elementOptionWeekday.selectedIndex;
            var value = elementOptionWeekday[selectedIndex].innerText;
            var body = { weekday: value };

            if (value != schedules[index].weekday) {
                putCall(apiUrl + "schedule/" + selectedScheduleNumber, body)
                    .then((result) => {
                        if (result.ok == true) {
                            schedules[index].weekday = value;

                            formatWeekday(schedules[index]);

                            console.log(
                                "Schedule " +
                                selectedScheduleNumber +
                                " - [weekday = " +
                                value +
                                "] was updated using the API."
                            );
                        }
                    });
            }
        }

        // ============================================================================
        //export
        export function updateScheduleType() {
            const index = getIndexOfScheduleWithId(selectedScheduleNumber);

            var elementOptionType = <HTMLSelectElement>(
                (<unknown>document.getElementById("idSelectType"))
            );

            var selectedIndex = elementOptionType.selectedIndex;
            var value = elementOptionType[selectedIndex].innerText;
            var body = { weekday: value };

            if (value != schedules[index].scheduleType) {
                putCall(apiUrl + "schedule/" + selectedScheduleNumber, body)
                    .then((result) => {
                        if (result.ok == true) {
                            schedules[index].scheduleType = value;

                            formatScheduleType(schedules[index]);

                            console.log(
                                "Schedule " +
                                selectedScheduleNumber +
                                " - [scheduleType = " +
                                value +
                                "] was updated using the API."
                            );
                        }
                    });
            }
        }


        // ============================================================================
        //export
        export function updateStartTime() {
            const index = getIndexOfScheduleWithId(selectedScheduleNumber);

            var elementStartTime = <HTMLSelectElement>(
                (<unknown>document.getElementById("idOptionStartTime"))
            );

            let timeValue = elementStartTime.value;
            let timeString = "0001-01-01T" + timeValue + ":00Z";
            let body = { startTime: timeString };

            if (timeValue != schedules[index].startTime) {
                putCall(apiUrl + "schedule/" + selectedScheduleNumber, body)
                    .then((result) => {
                        if (result.ok == true) {
                            schedules[index].startTime = timeString;

                            formatStartTime(schedules[index]);

                            console.log(
                                "Schedule " +
                                selectedScheduleNumber +
                                " - [startTime = " +
                                timeValue +
                                "] was updated using the API."
                            );
                        }
                    });
            }
        }

        // ============================================================================
        export function updateDurationMinutes() {

            debugger;

            let index = getIndexOfScheduleWithId(selectedScheduleNumber);

            var elementDurationMinutes = <HTMLInputElement>(
                (<unknown>document.getElementById("idOptionDurationMinutes"))
            );
            var value = elementDurationMinutes.value;
            var body = { durationMinutes: value };

            if (value != schedules[index].durationMinutes) {
                putCall(apiUrl + "schedule/" + selectedScheduleNumber, body)
                    .then((result) => {
                        if (result.ok == true) {

                            schedules[index].durationMinutes = value;

                            formatDurationMinutes(schedules[index]);

                            console.log(
                                "Schedule " +
                                selectedScheduleNumber +
                                " - [durationMinutes = " +
                                value +
                                "] was updated using the API."
                            );
                        }
                    });
            }
        }


        // ============================================================================
        export function updateDataSet(
            scheduleData: any) {

            schedules = scheduleData;
            updateSchedules();
        }


        // ============================================================================
        export async function updateSchedules() {
            let templatter = new Templatter("../static/templatter/");
            await templatter.getTemplate("schedule_row.html");

            let elementScheduleRowDiv = document.getElementById("scheduleRows")!;
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
                    let elementSchedule = document.getElementById("idSchedule" + schedule.id)!;
                    elementSchedule.classList.add("table-row-active");
                }

                formatData(schedule);
            });

            toggleSettingsVisibility(selectedScheduleNumber, true);

        }

        // ============================================================================
        function formatData(schedule: any) {
            formatWeekday(schedule);
            formatStartTime(schedule);
            formatDurationMinutes(schedule);
        }


        // ============================================================================
        function formatWeekday(schedule: any) {
            var idWeekday = "idSchedule" + schedule.id + "_weekday";
            var elementWeekday = document.getElementById(idWeekday);

            if (elementWeekday === null ||
                elementWeekday === undefined) {
                return;
            }

            if (schedule.enabled == true) {
                elementWeekday.style.backgroundColor = "#6b99ff";
            } else {
                elementWeekday.style.backgroundColor = "#cccccc";
            }

            elementWeekday.textContent =
                tethys.tool.pad(schedule.id, 2) +
                " / " +
                schedule.weekday;
        }


        // ============================================================================
        function formatStartTime(schedule: any) {

            let idStartTime =
                "idSchedule" + schedule.id.toString() + "_startTime";

            var elementStartTime = document.getElementById(
                idStartTime
            );

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
        function formatDurationMinutes(schedule: any) {
            var idDurationMinutes =
                "idSchedule" + schedule.id.toString() + "_duration";

            var elementDurationMinutes = document.getElementById(
                idDurationMinutes
            );

            if (elementDurationMinutes === null ||
                elementDurationMinutes === undefined) {
                return;
            }

            let durationString =
                tethys.tool.getDurationString(
                    schedule.startTime,
                    schedule.durationMinutes);

            elementDurationMinutes.innerHTML = durationString;
        }


        // ============================================================================
        function formatScheduleType(schedule: any) {
            var idScheduleType =
                "idSchedule" + (schedule.id) + "_type";

            var elementScheduleType = document.getElementById(
                idScheduleType
            );

            if (elementScheduleType === null ||
                elementScheduleType === undefined) {
                return;
            }

            elementScheduleType.textContent = schedule.scheduleType;
        }




        // ============================================================================
        export function updateTimes() {
            schedules.forEach(schedule => {

                formatStartTime(schedule);
            });


        }

        /*
        // ::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
        var interval = setInterval(updateTimes, 990);
        */

    }
}
