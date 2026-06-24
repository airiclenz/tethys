
// Chart.js is loaded as a global from the vendored UMD build (see layout.html).
declare const Chart: any;

// ============================================================================
// ============================================================================
// ============================================================================
namespace tethys {
    export namespace charts {

        let moistureChart: any = null;   // Chart instance for moisture over time
        let voltageChart: any = null;    // Chart instance for battery voltage over time

        const moistureColor = "#39337b";                  // brand purple
        const moistureFill = "rgba(57, 51, 123, 0.08)";
        const voltageColor = "#2f8f4e";                   // green
        const voltageFill = "rgba(47, 143, 78, 0.08)";
        const thresholdColor = "#cc3333";                 // dashed low-battery line
        const actionThresholdColor = "#d98a00";           // dashed action-threshold line (moisture)
        const actionMarkerColor = "#1f9bd1";              // vertical watering-event markers (moisture)
        const actionMarkerFill = "rgba(31, 155, 209, 0.25)"; // legend swatch for the markers

        // Mirrors the low-battery warning threshold used in measurements.ts.
        const batteryMinVoltage = 3.5;


        // ============================================================================
        // Draw / refresh the two time-series charts from the current sensor readings.
        // Safe to call repeatedly: an existing chart is updated in place (no flicker),
        // and an empty list simply clears both charts.
        export function render(rows: any[], moistureThreshold: number | null = null,
                               actions: any[] = []) {

            // The vendored Chart.js global must be present; if the script failed to
            // load there is nothing to draw.
            if (typeof Chart === "undefined") {
                return;
            }

            // Always plot in chronological order, regardless of how the table below
            // is currently sorted.
            const ordered = rows.slice().sort((a, b) =>
                new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime());

            const labels = ordered.map(row => tethys.tool.formatDate(row.timestamp));
            const moistureData = ordered.map(row => row.moisturePercent);
            const voltageData = ordered.map(row => row.batteryVoltage);
            const thresholdData = ordered.map(() => batteryMinVoltage);

            // Real (ms) timestamps for the moisture chart's watering markers. The
            // x-axis is categorical (one slot per reading), so each action time is
            // mapped onto it by interpolating between its surrounding readings.
            const readingTimes = ordered.map(row => new Date(row.timestamp).getTime());
            const actionTimes = (actions || []).map(a => new Date(a.startTime).getTime());

            moistureChart = drawMoisture(
                labels, moistureData, moistureThreshold, readingTimes, actionTimes);
            voltageChart = drawVoltage(labels, voltageData, thresholdData);
        }


        // ============================================================================
        function drawMoisture(labels: string[], data: any[], threshold: number | null,
                              readingTimes: number[], actionTimes: number[]) {

            const canvas = <HTMLCanvasElement>(
                (<unknown>document.getElementById("idMoistureChart"))
            );
            if (canvas === null) {
                return moistureChart;
            }

            // The per-channel action threshold is drawn as a flat reference line
            // (one constant value per timestamp). When it is unknown the line is
            // simply empty and its legend entry drops out (blank label).
            const hasThreshold =
                threshold !== null && threshold !== undefined && !isNaN(threshold);
            const thresholdData = hasThreshold ? labels.map(() => threshold) : [];
            const thresholdLabel = hasThreshold ? "Action threshold: " + threshold + "%" : "";

            // Watering markers are painted by the tethysActionMarkers plugin. The
            // empty dataset below carries only their legend entry (blank label, so
            // it drops out, when there are no actions). Marker geometry travels via
            // the plugin options so it is available on the very first draw.
            const wateringLabel = actionTimes.length > 0 ? "Watering" : "";
            const markerOptions = {
                readingTimes: readingTimes,
                actionTimes: actionTimes,
                legendDatasetIndex: 2
            };

            if (moistureChart !== null) {
                moistureChart.data.labels = labels;
                moistureChart.data.datasets[0].data = data;
                moistureChart.data.datasets[1].data = thresholdData;
                moistureChart.data.datasets[1].label = thresholdLabel;
                moistureChart.data.datasets[2].label = wateringLabel;

                // Mutate the existing options in place (rather than replacing the
                // reference) so any cached plugin-options descriptor sees the new
                // marker geometry on the next draw.
                const existing = moistureChart.options.plugins.tethysActionMarkers;
                if (existing) {
                    existing.readingTimes = readingTimes;
                    existing.actionTimes = actionTimes;
                } else {
                    moistureChart.options.plugins.tethysActionMarkers = markerOptions;
                }

                moistureChart.update();
                return moistureChart;
            }

            const options: any = baseOptions("Moisture", "%", { min: 0, max: 100 }, true);
            options.plugins.tethysActionMarkers = markerOptions;

            return new Chart(canvas, {
                type: "line",
                data: {
                    labels: labels,
                    datasets: [
                        {
                            data: data,
                            borderColor: moistureColor,
                            backgroundColor: moistureFill,
                            borderWidth: 2,
                            pointRadius: 0,
                            pointHoverRadius: 4,
                            tension: 0.25,
                            fill: true,
                            spanGaps: true
                        },
                        {
                            // Per-channel action threshold (mirrors the battery line).
                            label: thresholdLabel,
                            data: thresholdData,
                            borderColor: actionThresholdColor,
                            borderWidth: 1,
                            borderDash: [6, 4],
                            pointRadius: 0,
                            pointHoverRadius: 0,
                            fill: false
                        },
                        {
                            // Legend-only entry for the watering markers; the plugin
                            // draws the actual vertical lines (dotted, matching below).
                            label: wateringLabel,
                            data: [],
                            borderColor: actionMarkerColor,
                            backgroundColor: actionMarkerFill,
                            borderWidth: 1,
                            borderDash: [2, 3],
                            pointRadius: 0,
                            pointHoverRadius: 0,
                            fill: false
                        }
                    ]
                },
                // Legend (filtered to labeled datasets) explains the reference lines.
                options: options,
                plugins: [actionMarkersPlugin]
            });
        }


        // ============================================================================
        // Per-chart plugin: draw a vertical line on the moisture chart at every
        // watering-action time. The chart's x-axis is categorical (one slot per
        // sensor reading), so each action's real timestamp is interpolated onto the
        // axis between the two readings that surround it. Actions outside the loaded
        // reading window are skipped rather than clamped to an edge.
        const actionMarkersPlugin = {
            id: "tethysActionMarkers",

            afterDatasetsDraw(chart: any, _args: any, options: any) {

                if (!options) {
                    return;
                }

                const readingTimes: number[] = options.readingTimes || [];
                const actionTimes: number[] = options.actionTimes || [];

                // Need at least two readings to interpolate, and at least one action.
                if (readingTimes.length < 2 || actionTimes.length === 0) {
                    return;
                }

                // Honour the "Watering" legend toggle: hide the lines when its
                // (empty) dataset has been switched off.
                const legendIndex = options.legendDatasetIndex;
                if (legendIndex !== undefined && legendIndex !== null) {
                    const meta = chart.getDatasetMeta(legendIndex);
                    if (meta && meta.hidden) {
                        return;
                    }
                }

                const xScale = chart.scales.x;
                const area = chart.chartArea;
                const ctx = chart.ctx;
                const first = readingTimes[0];
                const last = readingTimes[readingTimes.length - 1];

                ctx.save();
                ctx.strokeStyle = actionMarkerColor;
                ctx.lineWidth = 1;
                // Fine dotted pattern, distinct from the threshold line's longer dashes.
                ctx.setLineDash([2, 3]);

                actionTimes.forEach((time: number) => {

                    if (isNaN(time) || time < first || time > last) {
                        return;
                    }

                    const x = markerPixel(xScale, readingTimes, time);
                    if (x === null) {
                        return;
                    }

                    ctx.beginPath();
                    ctx.moveTo(x, area.top);
                    ctx.lineTo(x, area.bottom);
                    ctx.stroke();
                });

                ctx.restore();
            }
        };


        // ============================================================================
        // Map a real (ms) timestamp onto the categorical x-axis: find the reading
        // interval that contains it and interpolate the pixel position linearly
        // between the two category slots. Returns null when no interval matches.
        function markerPixel(xScale: any, readingTimes: number[], time: number): number | null {

            for (let i = 0; i < readingTimes.length - 1; i++) {
                const a = readingTimes[i];
                const b = readingTimes[i + 1];

                if (time >= a && time <= b) {
                    const span = b - a;
                    const frac = span > 0 ? (time - a) / span : 0;
                    const xa = xScale.getPixelForValue(i);
                    const xb = xScale.getPixelForValue(i + 1);
                    return xa + frac * (xb - xa);
                }
            }

            return null;
        }


        // ============================================================================
        function drawVoltage(labels: string[], data: any[], threshold: number[]) {

            const canvas = <HTMLCanvasElement>(
                (<unknown>document.getElementById("idVoltageChart"))
            );
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
                            label: "Low-battery threshold: " + batteryMinVoltage + " V",
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
                // Legend (filtered to labeled datasets) explains the threshold line.
                options: baseOptions("Battery", " V", { suggestedMin: 2.8, suggestedMax: 4.3 }, true)
            });
        }


        // ============================================================================
        // Shared chart options: clean look, thinned x-axis labels for large histories,
        // and tooltips that report only the real data series (not the threshold line).
        // When showThresholdLegend is set, the legend is shown but limited to datasets
        // that carry a label (i.e. the threshold line), so the user sees what it means.
        function baseOptions(seriesName: string, unit: string, yScale: any,
                             showThresholdLegend: boolean = false) {

            yScale.ticks = {
                maxTicksLimit: 6,
                callback: (value: any) => value + unit
            };
            yScale.grid = { color: "#eeeeee" };

            return {
                responsive: true,
                maintainAspectRatio: false,
                animation: false,
                interaction: { mode: "index", intersect: false },
                plugins: {
                    legend: showThresholdLegend
                        ? { display: true, labels: { filter: (item: any) => !!item.text } }
                        : { display: false },
                    tooltip: {
                        // Only the primary series (index 0); skip the threshold line.
                        filter: (item: any) => item.datasetIndex === 0,
                        callbacks: {
                            label: (item: any) =>
                                seriesName + ": " + item.formattedValue + unit
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

    }
}
