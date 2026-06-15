"use strict";
// ============================================================================
// ============================================================================
// ============================================================================
var tethys;
(function (tethys) {
    let charts;
    (function (charts) {
        let moistureChart = null; // Chart instance for moisture over time
        let voltageChart = null; // Chart instance for battery voltage over time
        const moistureColor = "#39337b"; // brand purple
        const moistureFill = "rgba(57, 51, 123, 0.08)";
        const voltageColor = "#2f8f4e"; // green
        const voltageFill = "rgba(47, 143, 78, 0.08)";
        const thresholdColor = "#cc3333"; // dashed low-battery line
        // Mirrors the low-battery warning threshold used in measurements.ts.
        const batteryMinVoltage = 3.5;
        // ============================================================================
        // Draw / refresh the two time-series charts from the current sensor readings.
        // Safe to call repeatedly: an existing chart is updated in place (no flicker),
        // and an empty list simply clears both charts.
        function render(rows) {
            // The vendored Chart.js global must be present; if the script failed to
            // load there is nothing to draw.
            if (typeof Chart === "undefined") {
                return;
            }
            // Always plot in chronological order, regardless of how the table below
            // is currently sorted.
            const ordered = rows.slice().sort((a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime());
            const labels = ordered.map(row => tethys.tool.formatDate(row.timestamp));
            const moistureData = ordered.map(row => row.moisturePercent);
            const voltageData = ordered.map(row => row.batteryVoltage);
            const thresholdData = ordered.map(() => batteryMinVoltage);
            moistureChart = drawMoisture(labels, moistureData);
            voltageChart = drawVoltage(labels, voltageData, thresholdData);
        }
        charts.render = render;
        // ============================================================================
        function drawMoisture(labels, data) {
            const canvas = document.getElementById("idMoistureChart");
            if (canvas === null) {
                return moistureChart;
            }
            if (moistureChart !== null) {
                moistureChart.data.labels = labels;
                moistureChart.data.datasets[0].data = data;
                moistureChart.update();
                return moistureChart;
            }
            return new Chart(canvas, {
                type: "line",
                data: {
                    labels: labels,
                    datasets: [{
                            data: data,
                            borderColor: moistureColor,
                            backgroundColor: moistureFill,
                            borderWidth: 2,
                            pointRadius: 0,
                            pointHoverRadius: 4,
                            tension: 0.25,
                            fill: true,
                            spanGaps: true
                        }]
                },
                options: baseOptions("Moisture", "%", { min: 0, max: 100 })
            });
        }
        // ============================================================================
        function drawVoltage(labels, data, threshold) {
            const canvas = document.getElementById("idVoltageChart");
            if (canvas === null) {
                return voltageChart;
            }
            if (voltageChart !== null) {
                voltageChart.data.labels = labels;
                voltageChart.data.datasets[0].data = data;
                voltageChart.data.datasets[1].data = threshold;
                voltageChart.update();
                return voltageChart;
            }
            return new Chart(canvas, {
                type: "line",
                data: {
                    labels: labels,
                    datasets: [
                        {
                            data: data,
                            borderColor: voltageColor,
                            backgroundColor: voltageFill,
                            borderWidth: 2,
                            pointRadius: 0,
                            pointHoverRadius: 4,
                            tension: 0.25,
                            fill: true,
                            spanGaps: true
                        },
                        {
                            // Low-battery reference line (mirrors the < 3.5 V warning).
                            data: threshold,
                            borderColor: thresholdColor,
                            borderWidth: 1,
                            borderDash: [6, 4],
                            pointRadius: 0,
                            pointHoverRadius: 0,
                            fill: false
                        }
                    ]
                },
                options: baseOptions("Battery", " V", { suggestedMin: 2.8, suggestedMax: 4.3 })
            });
        }
        // ============================================================================
        // Shared chart options: clean look, thinned x-axis labels for large histories,
        // and tooltips that report only the real data series (not the threshold line).
        function baseOptions(seriesName, unit, yScale) {
            yScale.ticks = {
                maxTicksLimit: 6,
                callback: (value) => value + unit
            };
            yScale.grid = { color: "#eeeeee" };
            return {
                responsive: true,
                maintainAspectRatio: false,
                animation: false,
                interaction: { mode: "index", intersect: false },
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        // Only the primary series (index 0); skip the threshold line.
                        filter: (item) => item.datasetIndex === 0,
                        callbacks: {
                            label: (item) => seriesName + ": " + item.formattedValue + unit
                        }
                    }
                },
                scales: {
                    x: {
                        ticks: {
                            maxTicksLimit: 8,
                            autoSkip: true,
                            maxRotation: 0,
                            minRotation: 0
                        },
                        grid: { display: false }
                    },
                    y: yScale
                }
            };
        }
    })(charts = tethys.charts || (tethys.charts = {}));
})(tethys || (tethys = {}));
//# sourceMappingURL=charts.js.map