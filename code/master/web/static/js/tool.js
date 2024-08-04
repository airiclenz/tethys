// ============================================================================
// ============================================================================
// ============================================================================
var tethys;
(function (tethys) {
    let tool;
    (function (tool) {
        // ============================================================================
        function isValidDate(dateValue, checkForMinValue = true) {
            if (!(dateValue instanceof Date)) {
                return false;
            }
            if (checkForMinValue) {
                return dateValue.valueOf() > 0;
            }
            return true;
        }
        tool.isValidDate = isValidDate;
        // ============================================================================
        function limitValue(elementId, minimum, maximum) {
            var element = document.getElementById(elementId);
            if (element) {
                //var value = parseInt(element.value, 10);
                var value = Number(element.value);
                if (value) {
                    if (value < minimum) {
                        value = minimum;
                    }
                    if (value > maximum) {
                        value = maximum;
                    }
                    element.value = value.toString();
                }
            }
        }
        tool.limitValue = limitValue;
        // ============================================================================
        function getDurationString(startTime, durationMinutes) {
            let startTimeDate = new Date(startTime);
            let resultString = "";
            let hours = Math.floor(durationMinutes / 60);
            let minutes = durationMinutes - (hours * 60);
            resultString =
                this.pad(hours, 2) + "h " +
                    this.pad(minutes, 2) + "min";
            let endTime = addMinutes(startTimeDate, durationMinutes);
            resultString +=
                " → " +
                    this.getTimeString(endTime);
            return resultString;
        }
        tool.getDurationString = getDurationString;
        // ============================================================================
        function addMinutes(date, minutes) {
            return new Date(date.getTime() + minutes * 60000);
        }
        // ============================================================================
        function getTimePassedSinceString(timestamp) {
            var resultString = "";
            var totalSeconds = (new Date().getTime() - timestamp.getTime()) / 1000;
            var days = Math.floor(totalSeconds / 86400);
            totalSeconds = totalSeconds - days * 86400;
            var hours = Math.floor(totalSeconds / 3600);
            totalSeconds = totalSeconds - hours * 3600;
            var minutes = Math.floor(totalSeconds / 60);
            totalSeconds = totalSeconds - minutes * 60;
            var seconds = Math.floor(totalSeconds);
            var time = pad(timestamp.getHours(), 2) + ":" + pad(timestamp.getMinutes(), 2);
            var yesterday = new Date();
            yesterday.setDate(yesterday.getDate() - 1);
            var yesterdayDate = yesterday.toLocaleDateString("sv-SE");
            var timestampDate = timestamp.toLocaleDateString("sv-SE");
            if (days > 0) {
                if (yesterdayDate == timestampDate) {
                    resultString = "yesterday " + time;
                }
                else {
                    resultString = timestamp.toLocaleString("sv-SE");
                }
            }
            else {
                if (yesterdayDate == timestampDate) {
                    resultString = "yesterday " + time;
                }
                else if (hours > 0) {
                    if (hours < 2) {
                        resultString =
                            pad(hours, 2) +
                                ":" +
                                pad(minutes, 2) +
                                ":" +
                                pad(seconds, 2) +
                                " sec ago";
                    }
                    else {
                        resultString = "today " + time;
                    }
                }
                else if (minutes > 0) {
                    resultString =
                        pad(minutes, 2) + " min " + pad(seconds, 2) + " sec ago";
                }
                else {
                    resultString = pad(seconds, 2) + " sec ago";
                }
            }
            return resultString;
        }
        tool.getTimePassedSinceString = getTimePassedSinceString;
        // ============================================================================
        function pad(num, size) {
            var s = num + "";
            while (s.length < size) {
                s = "0" + s;
            }
            return s;
        }
        tool.pad = pad;
        // ============================================================================
        function formatDate(dateObject) {
            if (typeof dateObject === "string") {
                dateObject = new Date(dateObject);
            }
            var result = dateObject.getFullYear() +
                "-" +
                pad(dateObject.getMonth() + 1, 2) +
                "-" +
                pad(dateObject.getDate(), 2) +
                " " +
                pad(dateObject.getHours(), 2) +
                ":" +
                pad(dateObject.getMinutes(), 2);
            return result;
        }
        tool.formatDate = formatDate;
        // ============================================================================
        function getTimeString(dateTimeObject) {
            if (typeof dateTimeObject === "string") {
                dateTimeObject = new Date(dateTimeObject);
            }
            let hours = dateTimeObject.getUTCHours();
            let minutes = dateTimeObject.getUTCMinutes();
            let result = (pad(hours, 2) + ":" +
                pad(minutes, 2));
            return result;
        }
        tool.getTimeString = getTimeString;
        // ============================================================================
        function replaceAll(input, search, replacement) {
            return input.split(search).join(replacement);
        }
        tool.replaceAll = replaceAll;
        // ============================================================================
        function setVisibleState(elementName, state, displayStyle = "block") {
            const element = document.getElementById(elementName);
            if (state) {
                element.style.display = displayStyle;
            }
            else {
                element.style.display = "none";
            }
        }
        tool.setVisibleState = setVisibleState;
        // ============================================================================
        function getUTCDate(dateString) {
            const [date, time] = dateString.split("T");
            const [year, month, day] = date.split("-");
            // Remove the trailing "Z"
            const [hours, minutes, seconds] = time.slice(0, -1).split(":");
            // Month is 0-indexed in Date operations, so subtract 1 when converting to a Date object
            return new Date(Date.UTC(Number(year), Number(month) - 1, Number(day), Number(hours), Number(minutes), Number(seconds)));
        }
        tool.getUTCDate = getUTCDate;
    })(tool = tethys.tool || (tethys.tool = {}));
})(tethys || (tethys = {}));
//# sourceMappingURL=tool.js.map