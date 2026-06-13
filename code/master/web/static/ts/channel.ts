
// ============================================================================
// ============================================================================
// ============================================================================
namespace tethys {
    export namespace channel {

        let channels = [];
        let selectedChannelNumber = null;

        // ============================================================================
        function getIndexOfchannelWithNumber(
            channelNumber) {

            return channelNumber - 1;
        }

        // ============================================================================
        export function deselectAll() {
            selectedChannelNumber = null;

            tethys.tool.setVisibleState("button-delete", false);
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
                triggerLevel: 50,
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

                    const reader = response.body.getReader();

                    reader.read()
                        .then((readerResult) => {

                            const resultBody = new TextDecoder().decode(readerResult.value);
                            selectedChannelNumber = parseInt(resultBody, 10);

                            tethys.websocket.requestChannelSummary();
                        });
                });
        }

        // ============================================================================
        export function toggleSettingsVisibility(clickedChannelNumber) {

            var elementSettings = document.getElementById("idSettings");
            var elementChannel = document.getElementById("idChannel" + clickedChannelNumber);

            if (selectedChannelNumber === null) {

                var elementSettingsTitle = document.getElementById("idSettingsTitle");

                elementSettingsTitle.textContent =
                    channels[clickedChannelNumber - 1].number +
                    " / " +
                    channels[clickedChannelNumber - 1].nickName;
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
                    );

                    var elementSettingsTitle =
                        document.getElementById("idSettingsTitle");

                    elementSettingsTitle.textContent =
                        channels[clickedChannelNumber - 1].number +
                        " / " +
                        channels[clickedChannelNumber - 1].nickName;
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
            channelSummary) {

            channels = channelSummary;
            updateChannels();
            updateSettings();
            
        }

        // ============================================================================
        //export
        export async function updateChannels() {

            let templatter = new Templatter("../static/templatter/");
            await templatter.getTemplate("channel_row.html");

            let elementChannelRowDiv = document.getElementById("channelRows");
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
                    let elementChannel = document.getElementById("idChannel" + channel.number);
                    elementChannel.classList.add("table-row-active");
                }

                formatData(channel);
            });
        }


        // ============================================================================
        function formatData(channel) {
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
        function formatChannelNumber(channel) {
            var id = "idChannel" + channel.number + "_number";
            var elementChannelNumber = document.getElementById(id);

            if (channel.enabled == true) {
                elementChannelNumber.style.backgroundColor = "#6b99ff";
            } else {
                elementChannelNumber.style.backgroundColor = "#cccccc";
            }
        }

        // ============================================================================
        function formatChannelType(channel) {
            var elementChannelType = document.getElementById(
                "idChannel" + channel.number + "_type"
            );
            elementChannelType.textContent = channel.channelType;
        }

        // ============================================================================
        function formatChannelStatus(channel) {
            var elementStatus = document.getElementById(
                "idChannel" + channel.number + "_status"
            );

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
        function formatSensorVoltage(channel) {

            var elementBattery = document.getElementById(
                "idChannel" + channel.number + "_sensorVoltage"
            );

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
        function formatChannelDataCount(channel) {
            var elementDataCount = document.getElementById(
                "idChannel" + channel.number + "_dataCount"
            );
            if (channel.sensorData_count !== null) {
                elementDataCount.innerHTML = channel.sensorData_count;
            }
            else {
                elementDataCount.innerHTML = tethys.nullString;
                elementDataCount.style.color = tethys.nullColor;
            }
        }


        // ============================================================================
        function formatLastSensorDataTime(channel) {

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
        function formatChannelActionCount(channel) {

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
        function formatLastActionTime(channel) {

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
            channelNumber,
            dataSetName) {

            const elementId =
                getCountElementId(channelNumber, dataSetName);

            const element =
                document.getElementById(elementId);

            const index =
                getIndexOfchannelWithNumber(channelNumber);

            if (channels[index][dataSetName] === null) {
                return;
            }

            element.innerHTML = '<a href="something">Open Dataset</a>';
        }

        // ============================================================================
        export function onCountMouseLeave(
            channelNumber,
            dataSetName) {

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
            channelNumber,
            datSetName) {

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
        export function generateMoistureSpanContent(channel) {

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

            if (value != channels[selectedChannelNumber - 1].enabled) {
                putCall(apiUrl + "channel/" + selectedChannelNumber, body).then((result) => {
                    if (result.ok == true) {
                        channels[callChannelNumber - 1].enabled = value;
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

            if (value != channels[selectedChannelNumber - 1].enabled) {
                putCall(apiUrl + "channel/" + selectedChannelNumber, body).then((result) => {
                    if (result.ok == true) {
                        channels[callChannelNumber - 1].nickName = value;
                        updateChannels();

                        var elementChannelNumber = document.getElementById(
                            "idChannel" + callChannelNumber + "_number"
                        );

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

            if (value != channels[selectedChannelNumber - 1].channelType) {
                putCall(apiUrl + "channel/" + selectedChannelNumber, body).then((result) => {
                    if (result.ok == true) {
                        channels[callChannelNumber - 1].channelType = value;

                        var elementChannelType = document.getElementById(
                            "idChannel" + callChannelNumber + "_type"
                        );

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

            if (value != channels[selectedChannelNumber - 1].sensorMeasureFrequencyMinutes) {
                putCall(apiUrl + "channel/" + selectedChannelNumber, body).then((result) => {
                    if (result.ok == true) {
                        channels[callChannelNumber - 1].sensorMeasureFrequencyMinutes =
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

            if (value != channels[selectedChannelNumber - 1].pumpDurationSeconds) {
                putCall(apiUrl + "channel/" + selectedChannelNumber, body).then((result) => {
                    if (result.ok == true) {
                        channels[callChannelNumber - 1].pumpDurationSeconds = value;
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

            if (value != channels[selectedChannelNumber - 1].actionTriggerPercent) {
                putCall(apiUrl + "channel/" + selectedChannelNumber, body).then((result) => {
                    if (result.ok == true) {
                        channels[callChannelNumber - 1].actionTriggerPercent = value;

                        var elementChannelStatus = document.getElementById(
                            "idChannel" + callChannelNumber + "_status"
                        );

                        elementChannelStatus.innerHTML =
                            generateMoistureSpanContent(channels[callChannelNumber - 1]);

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

            if (value != channels[selectedChannelNumber - 1].channelType) {
                putCall(apiUrl + "channel/" + selectedChannelNumber, body).then((result) => {
                    if (result.ok == true) {
                        channels[callChannelNumber - 1].sensorTransmissionPowerLevel =
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

            if (value != channels[selectedChannelNumber - 1].sensorTriggerCalibration) {
                putCall(apiUrl + "channel/" + selectedChannelNumber, body).then((result) => {
                    if (result.ok == true) {
                        channels[callChannelNumber - 1].sensorTriggerCalibration =
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

            var callString;
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