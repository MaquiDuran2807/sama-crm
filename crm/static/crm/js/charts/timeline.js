/**
 * Timeline chart renderer — multi-series line chart with accumulated total.
 * Dependencies: bridge.js (SAMACharts global)
 */
(function() {
    'use strict';

    var chartInstance = null;
    var timelineAllDatasets = [];
    var selectedPhases = new Set();
    var pipelineStages = [];
    var months = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic'];
    var stageColors = {
        'Lead': '#3b82f6',
        'Calificacion': '#8b5cf6',
        'Cotizacion Enviada': '#f5a623',
        'Seguimiento': '#06b6d4',
        'Cerrado Ganado': '#2ec27e',
        'Cerrado Perdido': '#ef4444',
        'Cotizacion Enviada': '#f5a623',
    };

    function getViewMode(days) {
        if (days === 0) return 'monthly';
        if (days <= 30) return 'daily';
        if (days <= 90) return 'weekly';
        if (days <= 365) return 'monthly';
        return 'quarterly';
    }

    function getWeekNumber(date) {
        var d = new Date(Date.UTC(date.getFullYear(), date.getMonth(), date.getDate()));
        var dayNum = d.getUTCDay() || 7;
        d.setUTCDate(d.getUTCDate() + 4 - dayNum);
        var yearStart = new Date(Date.UTC(d.getUTCFullYear(), 0, 1));
        return Math.ceil((((d - yearStart) / 86400000) + 1) / 7);
    }

    function groupDataByPeriod(dataArray, viewMode) {
        var result = {};
        if (viewMode === 'daily') {
            dataArray.forEach(function(d) {
                var parts = d.date.split('-');
                var year = parseInt(parts[0], 10);
                var month = parseInt(parts[1], 10) - 1;
                var day = parseInt(parts[2], 10);
                var key = day + ' ' + months[month];
                if (!result[key]) result[key] = { count: 0, sortKey: String(year) + String(month).padStart(2, '0') + String(day).padStart(2, '0') };
                result[key].count += d.count;
            });
        } else if (viewMode === 'weekly') {
            dataArray.forEach(function(d) {
                var parts = d.date.split('-');
                var year = parseInt(parts[0], 10);
                var month = parseInt(parts[1], 10) - 1;
                var day = parseInt(parts[2], 10);
                var dObj = new Date(year, month, day);
                var weekNum = getWeekNumber(dObj);
                var key = 'S' + weekNum + ' ' + months[month].substring(0, 3);
                if (!result[key]) result[key] = { count: 0, sortKey: String(year) + String(month).padStart(2, '0') + String(weekNum).padStart(2, '0') };
                result[key].count += d.count;
            });
        } else if (viewMode === 'monthly') {
            dataArray.forEach(function(d) {
                var parts = d.date.split('-');
                var year = parseInt(parts[0], 10);
                var month = parseInt(parts[1], 10) - 1;
                var key = months[month] + ' ' + year;
                if (!result[key]) result[key] = { count: 0, sortKey: String(year) + String(month).padStart(2, '0') };
                result[key].count += d.count;
            });
        } else if (viewMode === 'quarterly') {
            dataArray.forEach(function(d) {
                var parts = d.date.split('-');
                var year = parseInt(parts[0], 10);
                var month = parseInt(parts[1], 10) - 1;
                var quarter = Math.floor(month / 3) + 1;
                var key = 'Q' + quarter + ' ' + year;
                if (!result[key]) result[key] = { count: 0, sortKey: String(year) + String(quarter) };
                result[key].count += d.count;
            });
        }

        var sortedKeys = Object.keys(result).sort(function(a, b) { return result[a].sortKey.localeCompare(result[b].sortKey); });
        return {
            labels: sortedKeys,
            values: sortedKeys.map(function(k) { return result[k].count; })
        };
    }

    function buildStageDataMap(stageData, stageName, viewMode) {
        var records = stageData[stageName] || [];
        var map = {};
        if (viewMode === 'daily') {
            records.forEach(function(r) {
                var parts = r.date.split('-');
                var key = parseInt(parts[2], 10) + ' ' + months[parseInt(parts[1], 10) - 1];
                map[key] = (map[key] || 0) + r.count;
            });
        } else if (viewMode === 'weekly') {
            records.forEach(function(r) {
                var parts = r.date.split('-');
                var dObj = new Date(parseInt(parts[0], 10), parseInt(parts[1], 10) - 1, parseInt(parts[2], 10));
                var key = 'S' + getWeekNumber(dObj) + ' ' + months[parseInt(parts[1], 10) - 1].substring(0, 3);
                map[key] = (map[key] || 0) + r.count;
            });
        } else if (viewMode === 'monthly') {
            records.forEach(function(r) {
                var parts = r.date.split('-');
                var key = months[parseInt(parts[1], 10) - 1] + ' ' + parts[0];
                map[key] = (map[key] || 0) + r.count;
            });
        } else if (viewMode === 'quarterly') {
            records.forEach(function(r) {
                var parts = r.date.split('-');
                var quarter = Math.floor((parseInt(parts[1], 10) - 1) / 3) + 1;
                var key = 'Q' + quarter + ' ' + parts[0];
                map[key] = (map[key] || 0) + r.count;
            });
        }
        return map;
    }

    function getColors() {
        var theme = localStorage.getItem('sama-crm-theme') || 'dark';
        return theme === 'light'
            ? { text: '#1a1d24', muted: '#6b7385', border: '#e2e6ed' }
            : { text: '#d4d8e3', muted: '#6b7385', border: '#313849' };
    }

    function render(dayData, wonData, lostData, quoteData, stageData, stageNames, kpiTargets) {
        var canvas = document.getElementById('timeline-chart');
        if (!canvas) return;

        if (chartInstance) {
            chartInstance.destroy();
            chartInstance = null;
        }

        var params = window.SAMACharts ? window.SAMACharts.getParams() : { days: 30 };
        var viewMode = getViewMode(params.days);
        pipelineStages = stageData;

        var newGrouped = groupDataByPeriod(dayData, viewMode);
        var wonGrouped = groupDataByPeriod(wonData, viewMode);
        var lostGrouped = groupDataByPeriod(lostData, viewMode);
        var quoteGrouped = groupDataByPeriod(quoteData, viewMode);

        var dayLabels = newGrouped.labels;
        var newCounts = newGrouped.values;
        var wonCounts = wonGrouped.values;
        var lostCounts = lostGrouped.values;
        var quoteCounts = quoteGrouped.values;

        var ctx = canvas.getContext('2d');
        var colors = getColors();

        var datasets = [];

        datasets.push({
            label: 'Leads nuevos',
            data: newCounts,
            borderColor: '#3b82f6',
            backgroundColor: 'rgba(59, 130, 246, 0.15)',
            fill: true,
            tension: 0.3,
            pointRadius: 3,
            pointBackgroundColor: '#3b82f6',
            borderWidth: 2,
        });

        datasets.push({
            label: 'Total Leads (acumulado)',
            data: newCounts.map(function(_, i) {
                var sum = 0;
                for (var j = 0; j <= i; j++) { sum += (newCounts[j] || 0); }
                return sum;
            }),
            borderColor: '#9333ea',
            backgroundColor: 'rgba(147, 51, 234, 0.08)',
            fill: false,
            tension: 0.3,
            pointRadius: 2,
            pointBackgroundColor: '#9333ea',
            borderWidth: 2,
        });

        datasets.push({
            label: 'Cerrados Ganados',
            data: wonCounts,
            borderColor: '#2ec27e',
            backgroundColor: 'rgba(46, 194, 126, 0.08)',
            borderDash: [5, 5],
            fill: false,
            tension: 0.3,
            pointRadius: 2,
            pointBackgroundColor: '#2ec27e',
            borderWidth: 2,
        });

        datasets.push({
            label: 'Cerrados Perdidos',
            data: lostCounts,
            borderColor: '#ef4444',
            backgroundColor: 'rgba(239, 68, 68, 0.08)',
            borderDash: [5, 5],
            fill: false,
            tension: 0.3,
            pointRadius: 2,
            pointBackgroundColor: '#ef4444',
            borderWidth: 2,
        });

        datasets.push({
            label: 'Cotizaciones Enviadas',
            data: quoteCounts,
            borderColor: '#f5a623',
            backgroundColor: 'rgba(245, 166, 35, 0.08)',
            borderDash: [2, 2],
            fill: false,
            tension: 0.3,
            pointRadius: 2,
            pointBackgroundColor: '#f5a623',
            borderWidth: 2,
        });

        stageNames.forEach(function(stageName) {
            var color = stageColors[stageName] || '#6b7385';
            var stageObj = null;
            for (var si = 0; si < (pipelineStages.length || 0); si++) {
                if ((pipelineStages[si] && pipelineStages[si].name) === stageName) {
                    stageObj = pipelineStages[si];
                    break;
                }
            }

            var borderStyle = [5, 5];
            if (stageObj && stageObj.order) {
                var order = stageObj.order;
                if (order % 2 === 0) borderStyle = [2, 2];
                else if (order % 3 === 0) borderStyle = [10, 5];
            }

            var stageMap = buildStageDataMap(stageData, stageName, viewMode);
            var stageCounts = dayLabels.map(function(label) { return stageMap[label] || 0; });

            datasets.push({
                label: stageName,
                data: stageCounts,
                borderColor: color,
                backgroundColor: color + '15',
                fill: false,
                tension: 0.3,
                pointRadius: 2,
                pointBackgroundColor: color,
                borderWidth: 1.5,
                borderDash: borderStyle,
            });
        });

        timelineAllDatasets = datasets.slice();

        var visibleDatasets = selectedPhases.size > 0
            ? datasets.filter(function(ds) { return selectedPhases.has(ds.label); })
            : datasets;

        chartInstance = new Chart(ctx, {
            type: 'line',
            data: {
                labels: dayLabels,
                datasets: visibleDatasets,
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                plugins: {
                    legend: {
                        display: true,
                        position: 'top',
                        labels: {
                            color: colors.text,
                            usePointStyle: true,
                            padding: 15,
                            font: { size: 12 },
                        },
                    },
                    datalabels: { display: false },
                },
                scales: {
                    x: {
                        ticks: {
                            color: colors.muted,
                            maxRotation: 45,
                            minRotation: 45,
                            font: { size: 10 },
                        },
                        grid: { color: colors.border },
                    },
                    y: {
                        ticks: {
                            color: colors.muted,
                            callback: function(v) { return Number.isInteger(v) ? v : ''; }
                        },
                        grid: { color: colors.border },
                        beginAtZero: true,
                        suggestedMin: 0,
                    },
                },
            },
        });

        selectedPhases = new Set();
        selectedPhases.add('Leads nuevos');
        stageNames.forEach(function(n) { selectedPhases.add(n); });
    }

    function renderPhaseSelector(stageNames) {
        var container = document.getElementById('phase-selector');
        if (!container) return;

        container.innerHTML = '';

        stageNames.forEach(function(name) {
            var color = stageColors[name] || '#6b7385';

            var pill = document.createElement('button');
            pill.className = 'phase-pill active';
            pill.style.borderColor = color;
            pill.style.color = color;
            pill.style.background = color + '22';
            pill.textContent = name;
            pill.dataset.stage = name;
            pill.dataset.color = color;
            selectedPhases.add(name);

            pill.addEventListener('click', function() {
                togglePhase(pill, name);
            });
            container.appendChild(pill);
        });
    }

    function togglePhase(pill, stageName) {
        if (selectedPhases.has(stageName)) {
            if (selectedPhases.size <= 1) return;
            selectedPhases.delete(stageName);
            pill.classList.remove('active');
            pill.style.background = '';
            pill.style.color = '';
        } else {
            selectedPhases.add(stageName);
            pill.classList.add('active');
            var color = pill.dataset.color;
            pill.style.background = color + '22';
            pill.style.color = color;
        }
        updateChart();
    }

    function updateChart() {
        if (!chartInstance) return;
        if (timelineAllDatasets.length === 0) return;

        var newDatasets = selectedPhases.size > 0
            ? timelineAllDatasets.filter(function(ds) { return selectedPhases.has(ds.label); })
            : timelineAllDatasets.slice();

        chartInstance.data.datasets = newDatasets;
        chartInstance.update('none');
    }

    window.SAMACharts = window.SAMACharts || {};
    window.SAMACharts.Timeline = {
        render: render,
        renderPhaseSelector: renderPhaseSelector,
        togglePhase: togglePhase
    };
})();