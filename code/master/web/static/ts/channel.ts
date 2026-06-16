
// ============================================================================
// ============================================================================
// ============================================================================
namespace tethys {
    export namespace channel {

        let channels: any[] = [];
        let selectedChannelNumber: any = null;
        // Channel number whose settings panel should be opened automatically
        // once the next summary refresh has rendered the rows (set right after
        // a new channel is created). null when there is nothing pending.
        let pendingOpenChannelNumber: number | null = null;

        // ============================================================================
        function getIndexOfchannelWithNumber(
            channelNumber: number) {

            return channels.findIndex(channel => channel.number === channelNumber);
        }

        // ============================================================================
        export function deselectAll() {
            if (selectedChannelNumber !== null) {
                const elementChannel = document.getElementById("idChannel" + selectedChannelNumber);
                if (elementChannel) { elementChannel.classList.remove("table-row-active"); }
            }

            const elementSettings = document.getElementById("idSettings");
            if (elementSettings) { elementSettings.style.display = "none"; }

            selectedChannelNumber = null;
        }


        // ============================================================================
        export async function deleteSelectedChannel() {

            if (selectedChannelNumber === null) {
                return;
            }

            const deletedNumber = selectedChannelNumber;

            deleteCall(apiUrl + "channel/" + deletedNumber)
                .then((response) => {

                    // Collapse the settings flip-out and clear the selection so the
                    // refreshed channel list does not re-highlight the deleted row.
                    const elementSettings = document.getElementById("idSettings");
                    const elementChannel = document.getElementById("idChannel" + deletedNumber);

                    if (elementSettings) { elementSettings.style.display = "none"; }
                    if (elementChannel) { elementChannel.classList.remove("table-row-active"); }

                    selectedChannelNumber = null;

                    tethys.websocket.requestChannelSummary();

                    console.log("Channel " + deletedNumber + " was deleted using the API.");
                });
        }

        // ============================================================================
        export function addNewChannel() {

            let nextNumber = getNextFreeNumber();

            if (nextNumber === -1) {
                return;
            }

            var body = {
                number: nextNumber,
                enabled: false,
                channelType: "pump",
                actionTriggerPercent: 50,
                pumpDurationSeconds: 10,
                sensorMeasureFrequencyMinutes: 60,
                sensorTransmissionPowerLevel: "low",
                //sensorTriggerCalibration: false
            };

            postCall(apiUrl + "channel/", body)
                .then((response) => {

                    if (!response.ok) {
                        return;
                    }

                    // Clear the current selection and arrange for the new
                    // channel's settings panel to open once the refreshed list
                    // has rendered its row (see updateChannels). The summary
                    // arrives asynchronously over the websocket, so the row does
                    // not exist in the DOM yet. (The POST response carries the
                    // full channel JSON, not a bare number, so it must not be
                    // fed to parseInt - that yielded NaN and wedged the toggle.)
                    selectedChannelNumber = null;
                    pendingOpenChannelNumber = nextNumber;

                    tethys.websocket.requestChannelSummary();
                });
        }

        // ============================================================================
        export function toggleSettingsVisibility(clickedChannelNumber: number) {

            var elementSettings = document.getElementById("idSettings")!;
            var elementChannel = document.getElementById("idChannel" + clickedChannelNumber)!;

            if (selectedChannelNumber === null) {

                var elementSettingsTitle = document.getElementById("idSettingsTitle")!;

                elementSettingsTitle.textContent =
                    channels[getIndexOfchannelWithNumber(clickedChannelNumber)].number +
                    " / " +
                    channels[getIndexOfchannelWithNumber(clickedChannelNumber)].nickName;
                elementSettings.style.display = "block";
                elementChannel.classList.add("table-row-active");

                selectedChannelNumber = clickedChannelNumber;
            }

            else {
                // De-select channel
                if (clickedChannelNumber === selectedChannelNumber) {

                    elementSettings.style.display = "none";
                    elementChannel.classList.remove("table-row-active");

                    selectedChannelNumber = null;
                }
                // select different channel
                else {
                    var elementLastChannel = document.getElementById(
                        "idChannel" + selectedChannelNumber
                    )!;

                    var elementSettingsTitle =
                        document.getElementById("idSettingsTitle")!;

                    elementSettingsTitle.textContent =
                        channels[getIndexOfchannelWithNumber(clickedChannelNumber)].number +
                        " / " +
                        channels[getIndexOfchannelWithNumber(clickedChannelNumber)].nickName;
                    elementChannel.classList.add("table-row-active");
                    elementLastChannel.classList.remove("table-row-active");

                    selectedChannelNumber = clickedChannelNumber;
                }
            }

            updateSettings();
        }


        // ============================================================================
        function getNextFreeNumber() {

            let nextFreeNumber = 1;

            channels.forEach(channel => {
                if (channel.number == nextFreeNumber) {
                    nextFreeNumber++;
                }
            });

            if (nextFreeNumber > 5) {
                return -1;
            }

            return nextFreeNumber;
        }


        // ============================================================================
        export function updateDataSet(
            channelSummary: any) {

            channels = channelSummary;
            updateChannels();
            updateSettings();
            
        }

        // ============================================================================
        //export
        export async function updateChannels() {

            let templatter = new Templatter("../static/templatter/");
            await templatter.getTemplate("channel_row.html");

            let elementChannelRowDiv = document.getElementById("channelRows")!;
            let channelRowDivContent = "";

            channels.forEach(channel => {
                channelRowDivContent +=
                    templatter.compile(channel, tethys.nullString);
            });

            elementChannelRowDiv.innerHTML = channelRowDivContent;

            // ::::::::::::::::::::::::
            // Reformatting of the data
            channels.forEach(channel => {

                if (channel.number === selectedChannelNumber) {
                    let elementChannel = document.getElementById("idChannel" + channel.number)!;
                    elementChannel.classList.add("table-row-active");
                }

                formatData(channel);
            });

            // Auto-open the settings panel for a just-created channel, now that
            // its row exists in the DOM. Consumed once so later refreshes do not
            // re-open it. Reuses the normal click handler so the behavior is
            // identical to selecting the row by hand.
            if (pendingOpenChannelNumber !== null) {
                const numberToOpen = pendingOpenChannelNumber;
                pendingOpenChannelNumber = null;

                const channelExists =
                    channels.some(channel => channel.number === numberToOpen);

                if (selectedChannelNumber === null && channelExists) {
                    toggleSettingsVisibility(numberToOpen);
                }
            }
        }


        // ============================================================================
        function formatData(channel: any) {
            formatChannelNumber(channel);
            formatChannelType(channel);
            formatChannelStatus(channel);
            formatSensorVoltage(channel);
            formatChannelDataCount(channel);
            formatLastSensorDataTime(channel);
            formatChannelActionCount(channel);
            formatLastActionTime(channel);
        }


        // ============================================================================
        function formatChannelNumber(channel: any) {
            var id = "idChannel" + channel.number + "_number";
            var elementChannelNumber = document.getElementById(id)!;

            if (channel.enabled == true) {
                elementChannelNumber.style.backgroundColor = "#6b99ff";
            } else {
                elementChannelNumber.style.backgroundColor = "#cccccc";
            }
        }

        // ============================================================================
        function formatChannelType(channel: any) {
            var elementChannelType = document.getElementById(
                "idChannel" + channel.number + "_type"
            )!;
            elementChannelType.textContent = channel.channelType;
        }

        // ============================================================================
        function formatChannelStatus(channel: any) {
            var elementStatus = document.getElementById(
                "idChannel" + channel.number + "_status"
            )!;

            if (channel.sensorData_lastMoisturePercent !== null) {
                elementStatus.innerHTML =
                    generateMoistureSpanContent(channel);
            }
            else {
                elementStatus.textContent = tethys.nullString;
                elementStatus.style.color = tethys.nullColor;
            }
        }

        // ============================================================================
        function formatSensorVoltage(channel: any) {

            var elementBattery = document.getElementById(
                "idChannel" + channel.number + "_sensorVoltage"
            )!;

            if (channel.sensorData_lastBatteryVoltage !== null) {

                let voltage =
                    parseFloat(
                        channel.sensorData_lastBatteryVoltage);

                if (voltage < 3.5) {

                    elementBattery.innerHTML =
                        voltage.toFixed(2) + " V" +
                        "&nbsp;&nbsp;" +
                        "<img src=\"../static/images/svg/warning.svg\" width=\"14\">";

                } else {

                    elementBattery.innerHTML =
                        voltage.toFixed(2) + " V";
                }
            }
            else {
                elementBattery.innerHTML = tethys.nullString;
                elementBattery.style.color = tethys.nullColor;
            }
        }

        // ============================================================================
        function formatChannelDataCount(channel: any) {
            var elementDataCount = document.getElementById(
                "idChannel" + channel.number + "_dataCount"
            )!;
            if (channel.sensorData_count !== null) {
                elementDataCount.innerHTML = channel.sensorData_count;
            }
            else {
                elementDataCount.innerHTML = tethys.nullString;
                elementDataCount.style.color = tethys.nullColor;
            }
        }


        // ============================================================================
        function formatLastSensorDataTime(channel: any) {

            var elementSensorTime =
                document.getElementById(
                    "idChannel" + channel.number + "_lastSensorDataTimestamp");

            if (elementSensorTime === null ||
                elementSensorTime === undefined) {
                return;
            }

            var lastTimestamp = new Date(channel.sensorData_lastTimestamp);

            if (tethys.tool.isValidDate(lastTimestamp)) {

                elementSensorTime.textContent =
                    tethys.tool.getTimePassedSinceString(lastTimestamp);
            } else {
                elementSensorTime.textContent = nullString;
                elementSensorTime.style.color = nullColor;
            }
        }


        // ============================================================================
        function formatChannelActionCount(channel: any) {

            var elementActionCount =
                document.getElementById(
                    "idChannel" + channel.number + "_actionCount"
                );

            if (elementActionCount === null ||
                elementActionCount === undefined) {
                return;
            }

            if (channel.action_count === null) {
                elementActionCount.innerHTML = nullString;
                elementActionCount.style.color = nullColor;
            }
            else {
                elementActionCount.innerHTML = channel.actionLog_count;
            }


        }


        // ============================================================================
        function formatLastActionTime(channel: any) {

            var elementActionTime =
                document.getElementById(
                    "idChannel" + channel.number + "_lastActionStartTime");

            if (elementActionTime === null ||
                elementActionTime === undefined) {
                return;
            }

            var lastStartTime = new Date(channel.actionLog_lastStartTime);

            if (tethys.tool.isValidDate(lastStartTime)) {

                elementActionTime.textContent =
                    tethys.tool.getTimePassedSinceString(lastStartTime);

            } else {
                elementActionTime.textContent = nullString;
                elementActionTime.style.color = nullColor;
            }

        }

        // ============================================================================
        export function onCountMouseEnter(
            channelNumber: number,
            dataSetName: string) {

            const elementId =
                getCountElementId(channelNumber, dataSetName);

            const element =
                document.getElementById(elementId)!;

            const index =
                getIndexOfchannelWithNumber(channelNumber);

            // Resolve the count field and the drill-down page for this cell.
            // (The channel summary exposes the action count as `actionLog_count`.)
            let count;
            let href;

            switch (dataSetName) {
                case 'sensorData_count':
                    count = channels[index].sensorData_count;
                    href = "../measurements/?channel=" + channelNumber;
                    break;

                case 'action_count':
                    count = channels[index].actionLog_count;
                    href = "../actions/?channel=" + channelNumber;
                    break;

                default:
                    return;
            }

            // Nothing recorded yet: leave the count as-is rather than offering a
            // link to an empty dataset.
            if (!count) {
                return;
            }

            element.innerHTML =
                '<a href="' + href + '" onclick="event.stopPropagation()">Open Dataset</a>';
        }

        // ============================================================================
        export function onCountMouseLeave(
            channelNumber: number,
            dataSetName: string) {

            const index =
                getIndexOfchannelWithNumber(channelNumber);

            switch (dataSetName) {
                case 'sensorData_count':
                    formatChannelDataCount(channels[index]);
                    break;

                case 'action_count':
                    formatChannelActionCount(channels[index]);
                    break;
            }
        }


        // ============================================================================
        function getCountElementId(
            channelNumber: number,
            datSetName: string) {

            let elementId = 'idChannel' + channelNumber;

            switch (datSetName) {
                case 'sensorData_count':
                    elementId += '_dataCount';
                    break;

                case 'action_count':
                    elementId += '_actionCount';
                    break;
            }
            return elementId
        }


        // ============================================================================
        export function generateMoistureSpanContent(channel: any) {

            var status;
            var comparator;

            if (channel.sensorData_lastMoisturePercent > channel.actionTriggerPercent) {
                comparator = ">";
                //status = "✓";
                status = "<img src=\"../static/images/svg/check.svg\" width=\"14\">";
            }
            else if (channel.sensorData_lastMoisturePercent < channel.actionTriggerPercent) {
                comparator = "<";
                //status = "<span style=\"color: #FF0000;\">⚠</span>";
                status = "<img src=\"../static/images/svg/warning.svg\" width=\"14\">";
            }
            else {
                comparator = "=";
                //status = "<span style=\"color: #FF0000;\">⚠</span>";
                status = "<img src=\"../static/images/svg/warning.svg\" width=\"14\">";
            }

            var result =
                status +
                "&nbsp;&nbsp;&nbsp; <strong>" +
                channel.sensorData_lastMoisturePercent +
                "%</strong>&nbsp;" +
                comparator +
                " " +
                channel.actionTriggerPercent +
                "%";

            return result;
        }


        // ============================================================================
        export function updateSettings() {

            if (selectedChannelNumber === null) {
                return;
            }

            const index = getIndexOfchannelWithNumber(selectedChannelNumber);


            // Enabled
            var elementOptionEnabled = <HTMLInputElement>(
                (<unknown>document.getElementById("idOptionEnabled"))
            );
            elementOptionEnabled.checked = channels[index].enabled;

            // Nickname
            var elementOptionNickName = <HTMLInputElement>(
                (<unknown>document.getElementById("idOptionNickName"))
            );
            elementOptionNickName.value = channels[index].nickName;

            // Channel type
            var elementSelectChannelType = <HTMLSelectElement>(
                (<unknown>document.getElementById("idSelectChannelType"))
            );
            elementSelectChannelType.selectedIndex =
                channels[index].channelTypeValue - 1;

            // Measure Frequency
            var elementOptionFrequency = <HTMLInputElement>(
                (<unknown>document.getElementById("idOptionFrequency"))
            );
            elementOptionFrequency.value =
                channels[index].sensorMeasureFrequencyMinutes;

            // Pump Duration
            var elementOptionPumpDuration = <HTMLInputElement>(
                (<unknown>document.getElementById("idOptionPumpDuration"))
            );
            elementOptionPumpDuration.value = channels[index].pumpDurationSeconds;

            // Action Trigger Percent
            var elementOptionActionTriggerPercent = <HTMLInputElement>(
                (<unknown>document.getElementById("idOptionActionTriggerPercent"))
            );
            elementOptionActionTriggerPercent.value =
                channels[index].actionTriggerPercent;

            // Trigger Calibration
            var elementOptionCalibrate = <HTMLInputElement>(
                (<unknown>document.getElementById("idOptionCalibrate"))
            );
            elementOptionCalibrate.checked =
                channels[index].sensorTriggerCalibration;

            // Transmission Power
            var elementSelectTransmissionPower = <HTMLSelectElement>(
                (<unknown>document.getElementById("idSelectTransmissionPower"))
            );

            for (var i = 0; i < elementSelectTransmissionPower.options.length; i++) {
                if (elementSelectTransmissionPower.options[i].text === channels[index].sensorTransmissionPowerLevel) {
                    elementSelectTransmissionPower.selectedIndex = i;
                    break;
                }
            }

            // Firmware Version (read-only; reported by the sensor on boot). The
            // version is followed by a colored hint comparing it to the latest
            // firmware the master reads from the sensor source (wpw_Version.h):
            // green "up to date", amber "latest is vX.Y.Z", grey if the sensor
            // is somehow ahead of this checkout. Nothing extra is shown until a
            // sensor has actually reported a version.
            var elementFirmwareVersion = <HTMLElement>(
                (<unknown>document.getElementById("idFirmwareVersion"))
            );
            var reportedVersion = channels[index].sensorFirmwareVersion;
            var firmwareStatus = channels[index].firmwareStatus;
            var latestVersion = channels[index].latestFirmwareVersion;

            elementFirmwareVersion.textContent =
                reportedVersion || tethys.nullString;

            if (reportedVersion && firmwareStatus && firmwareStatus !== "unknown") {
                var firmwareHint = document.createElement("span");
                firmwareHint.classList.add("firmware-status");

                if (firmwareStatus === "up_to_date") {
                    firmwareHint.classList.add("firmware-up-to-date");
                    firmwareHint.textContent = "(up to date)";
                } else if (firmwareStatus === "outdated") {
                    firmwareHint.classList.add("firmware-outdated");
                    firmwareHint.textContent = "(latest is v" + latestVersion + ")";
                } else if (firmwareStatus === "ahead") {
                    firmwareHint.classList.add("firmware-ahead");
                    firmwareHint.textContent = "(ahead of repo v" + latestVersion + ")";
                }

                elementFirmwareVersion.appendChild(firmwareHint);
            }

            // Test Channel
            var elementTestChannelLabel = <HTMLSelectElement>(
                (<unknown>document.getElementById("idTestChannelLabel"))
            );

            var elementTestChannelCheckBoxContainer = <HTMLSelectElement>(
                (<unknown>document.getElementById("idTestChannelCheckBoxContainer"))
            );

            if (channels[index].enabled) {
                elementTestChannelLabel.style.visibility = "visible"
                elementTestChannelCheckBoxContainer.style.visibility = "visible"
            }
            else {
                elementTestChannelLabel.style.visibility = "hidden"
                elementTestChannelCheckBoxContainer.style.visibility = "hidden"
            }

        }


        // ============================================================================
        export function updateEnabled() {
            var callChannelNumber = selectedChannelNumber;
            var elementOptionEnabled = <HTMLInputElement>(
                (<unknown>document.getElementById("idOptionEnabled"))
            );
            var value = elementOptionEnabled.checked;
            var body = { enabled: value };

            if (value != channels[getIndexOfchannelWithNumber(selectedChannelNumber)].enabled) {
                putCall(apiUrl + "channel/" + selectedChannelNumber, body).then((result) => {
                    if (result.ok == true) {
                        channels[getIndexOfchannelWithNumber(callChannelNumber)].enabled = value;
                        updateChannels();
                        updateSettings();

                        console.log(
                            "Channel " +
                            callChannelNumber +
                            " - [enabled = " +
                            value +
                            "] was updated using the API."
                        );
                    }
                });
            }
        }

        // ============================================================================
        export function updateNickName() {
            var callChannelNumber = selectedChannelNumber;
            var elementOptionNickName = <HTMLInputElement>(
                (<unknown>document.getElementById("idOptionNickName"))
            );
            var value = elementOptionNickName.value;
            var body = { nickName: value };

            if (value != channels[getIndexOfchannelWithNumber(selectedChannelNumber)].nickName) {
                putCall(apiUrl + "channel/" + selectedChannelNumber, body).then((result) => {
                    if (result.ok == true) {
                        channels[getIndexOfchannelWithNumber(callChannelNumber)].nickName = value;
                        updateChannels();

                        var elementChannelNumber = document.getElementById(
                            "idChannel" + callChannelNumber + "_number"
                        )!;

                        elementChannelNumber.innerHTML = callChannelNumber + " / " + value;

                        console.log(
                            "Channel " +
                            callChannelNumber +
                            " - [nickName = " +
                            value +
                            "] was updated using the API."
                        );
                    }
                });
            }
        }

        // ============================================================================
        export function updateType() {
            var callChannelNumber = selectedChannelNumber;
            var elementOptionChannelType = <HTMLSelectElement>document.getElementById(
                "idSelectChannelType"
            );

            var selectedIndex = elementOptionChannelType.selectedIndex;
            var value = elementOptionChannelType[selectedIndex].innerText;
            var body = { channelType: value };

            if (value != channels[getIndexOfchannelWithNumber(selectedChannelNumber)].channelType) {
                putCall(apiUrl + "channel/" + selectedChannelNumber, body).then((result) => {
                    if (result.ok == true) {
                        channels[getIndexOfchannelWithNumber(callChannelNumber)].channelType = value;

                        var elementChannelType = document.getElementById(
                            "idChannel" + callChannelNumber + "_type"
                        )!;

                        elementChannelType.innerHTML = value;

                        console.log(
                            "Channel " +
                            callChannelNumber +
                            " - [channelType = " +
                            value +
                            "] was updated using the API."
                        );
                    }
                });
            }
        }

        // ============================================================================
        export function updateFrequency() {
            var callChannelNumber = selectedChannelNumber;
            var elementOptionFrequency = <HTMLInputElement>(
                (<unknown>document.getElementById("idOptionFrequency"))
            );
            var value = elementOptionFrequency.value;
            var body = { sensorMeasureFrequencyMinutes: value };

            if (value != channels[getIndexOfchannelWithNumber(selectedChannelNumber)].sensorMeasureFrequencyMinutes) {
                putCall(apiUrl + "channel/" + selectedChannelNumber, body).then((result) => {
                    if (result.ok == true) {
                        channels[getIndexOfchannelWithNumber(callChannelNumber)].sensorMeasureFrequencyMinutes =
                            value;
                        console.log(
                            "Channel " +
                            callChannelNumber +
                            " - [sensorMeasureFrequencyMinutes = " +
                            value +
                            "] was updated using the API."
                        );
                    }
                });
            }
        }

        // ============================================================================
        export function updatePumpDuration() {
            var callChannelNumber = selectedChannelNumber;
            var elementOptionPumpDuration = <HTMLInputElement>(
                (<unknown>document.getElementById("idOptionPumpDuration"))
            );
            var value = elementOptionPumpDuration.value;
            var body = { pumpDurationSeconds: value };

            if (value != channels[getIndexOfchannelWithNumber(selectedChannelNumber)].pumpDurationSeconds) {
                putCall(apiUrl + "channel/" + selectedChannelNumber, body).then((result) => {
                    if (result.ok == true) {
                        channels[getIndexOfchannelWithNumber(callChannelNumber)].pumpDurationSeconds = value;
                        console.log(
                            "Channel " +
                            callChannelNumber +
                            " - [pumpDurationSeconds = " +
                            value +
                            "] was updated using the API."
                        );
                    }
                });
            }
        }

        // ============================================================================
        export function updateActionTriggerPercent() {
            var callChannelNumber = selectedChannelNumber;
            var elementOptionActionTriggerPercent = <HTMLInputElement>(
                (<unknown>document.getElementById("idOptionActionTriggerPercent"))
            );
            var value = elementOptionActionTriggerPercent.value;
            var body = { actionTriggerPercent: value };

            if (value != channels[getIndexOfchannelWithNumber(selectedChannelNumber)].actionTriggerPercent) {
                putCall(apiUrl + "channel/" + selectedChannelNumber, body).then((result) => {
                    if (result.ok == true) {
                        channels[getIndexOfchannelWithNumber(callChannelNumber)].actionTriggerPercent = value;

                        var elementChannelStatus = document.getElementById(
                            "idChannel" + callChannelNumber + "_status"
                        )!;

                        elementChannelStatus.innerHTML =
                            generateMoistureSpanContent(channels[getIndexOfchannelWithNumber(callChannelNumber)]);

                        console.log(
                            "Channel " +
                            callChannelNumber +
                            " - [actionTriggerPercent = " +
                            value +
                            "] was updated using the API."
                        );
                    }
                });
            }
        }

        // ============================================================================
        //export
        export function updateTransmissionPower() {
            var callChannelNumber = selectedChannelNumber;
            var elementOptionTransmissionPower = <HTMLSelectElement>(
                (<unknown>document.getElementById("idSelectTransmissionPower"))
            );

            var selectedIndex = elementOptionTransmissionPower.selectedIndex;
            var value = elementOptionTransmissionPower[selectedIndex].innerText;
            var body = { sensorTransmissionPowerLevel: value };

            if (value != channels[getIndexOfchannelWithNumber(selectedChannelNumber)].channelType) {
                putCall(apiUrl + "channel/" + selectedChannelNumber, body).then((result) => {
                    if (result.ok == true) {
                        channels[getIndexOfchannelWithNumber(callChannelNumber)].sensorTransmissionPowerLevel =
                            value;

                        console.log(
                            "Channel " +
                            callChannelNumber +
                            " - [sensorTransmissionPowerLevel = " +
                            value +
                            "] was updated using the API."
                        );
                    }
                });
            }
        }

        // ============================================================================
        export function updateTriggerCalibration() {
            var callChannelNumber = selectedChannelNumber;
            var elementOptionCalibrate = <HTMLInputElement>(
                (<unknown>document.getElementById("idOptionCalibrate"))
            );
            var value = elementOptionCalibrate.checked;
            var body = { sensorTriggerCalibration: value };

            if (value != channels[getIndexOfchannelWithNumber(selectedChannelNumber)].sensorTriggerCalibration) {
                putCall(apiUrl + "channel/" + selectedChannelNumber, body).then((result) => {
                    if (result.ok == true) {
                        channels[getIndexOfchannelWithNumber(callChannelNumber)].sensorTriggerCalibration =
                            value;
                        console.log(
                            "Channel " +
                            callChannelNumber +
                            " - [sensorTriggerCalibration = " +
                            value +
                            "] was updated using the API."
                        );
                    }
                });
            }
        }

        // ============================================================================
        export function triggerChannel() {
            var callChannelNumber = selectedChannelNumber;
            var elementTestChannel = <HTMLInputElement>(
                (<unknown>document.getElementById("idTestChannel"))
            );
            var value = elementTestChannel.checked;

            var callString: string;
            value ? (callString = "activate") : (callString = "deactivate");

            patchCall(apiUrl + "channel/" + selectedChannelNumber + "/" + callString).then(
                (response) => {
                    if (response.ok) {
                        console.log(
                            "Channel " + callChannelNumber + " was " + callString + "d."
                        );
                    } else {
                        console.log(
                            "Channel " +
                            callChannelNumber +
                            " wad not " +
                            callString +
                            "d: " +
                            response.statusText
                        );

                        // Permission denied: the API key is missing or wrong.
                        // Revert the toggle and point the user at Settings.
                        if (response.status === 403) {
                            elementTestChannel.checked = !value;
                            alert(
                                "Not authorized to control the pump. Set the " +
                                "correct API key in Settings (top menu)."
                            );
                        }
                    }
                }
            );
        }


        // ============================================================================
        export function updateTimes() {
            channels.forEach(channel => {

                formatLastSensorDataTime(channel);
                formatLastActionTime(channel);

            });
        }



        // ::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
        var interval = setInterval(updateTimes, 990);


    }
}