(function() {
    'use strict';

    var tenantSlug = SAMA.getTenantSlug();
    var currentDays = 30;
    var currentSource = '';
    var charts = {};
    var currentOffset = 0;

    var periodLabels = {
        7: { singular: 'semana', plural: 'semanas', day: 7 },
        30: { singular: 'mes', plural: 'meses', day: 30 },
        90: { singular: 'trimestre', plural: 'trimestres', day: 90 },
        365: { singular: 'año', plural: 'años', day: 365 },
        0: { singular: 'todo', plural: 'todo', day: 0 },
    };

    var monthNames = ['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio', 'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre'];

    var darkColors = {
        bg: '#1a1d24',
        surface: '#21252e',
        card: '#262b36',
        border: '#313849',
        text: '#d4d8e3',
        muted: '#6b7385',
        accent: '#f06539',
        success: '#2ec27e',
        warning: '#f5a623',
        info: '#3b82f6',
    };

    var lightColors = {
        bg: '#f5f6f8',
        surface: '#ffffff',
        card: '#ffffff',
        border: '#e2e6ed',
        text: '#1a1d24',
        muted: '#6b7385',
        accent: '#f06539',
        success: '#2ec27e',
        warning: '#f5a623',
        info: '#3b82f6',
    };

    function getColors() {
        var theme = localStorage.getItem('sama-crm-theme') || 'dark';
        return theme === 'light' ? lightColors : darkColors;
    }

    function getPeriodLabel() {
        if (currentDays === 0) return 'Histórico completo';
        if (currentDays === 7) return 'Última semana';
        if (currentDays === 365) return 'Último año';
        var now = new Date();
        var end = new Date(now);
        var start = new Date(now);
        start.setDate(start.getDate() - currentDays + currentOffset * currentDays);
        end.setDate(end.getDate() + currentOffset * currentDays);
        if (currentOffset !== 0) {
            return formatDateRange(start, end);
        }
        return 'Últimos ' + currentDays + ' días';
    }

    function formatDateRange(start, end) {
        var startStr = start.getDate() + ' ' + monthNames[start.getMonth()].substring(0, 3);
        var endStr = end.getDate() + ' ' + monthNames[end.getMonth()].substring(0, 3);
        if (start.getFullYear() !== end.getFullYear()) {
            return startStr + ' ' + start.getFullYear() + ' — ' + endStr + ' ' + end.getFullYear();
        }
        return startStr + ' — ' + endStr;
    }

    function updatePeriodLabel() {
        var el = document.getElementById('current-period-label');
        if (el) el.textContent = getPeriodLabel();
    }

    function buildChartConfig(type, data, options) {
        var colors = getColors();
        return {
            type: type,
            data: data,
            options: Object.assign({
                responsive: true,
                maintainAspectRatio: true,
                plugins: {
                    legend: {
                        labels: {
                            color: colors.text,
                            font: { family: 'Inter', size: 12 },
                        },
                    },
                },
                scales: type !== 'pie' && type !== 'doughnut' ? {
                    x: {
                        ticks: { color: colors.muted },
                        grid: { color: colors.border },
                    },
                    y: {
                        ticks: { color: colors.muted },
                        grid: { color: colors.border },
                    },
                } : undefined,
            }, options),
        };
    }

    function loadAnalytics() {
        var url = '/api/crm/tenants/' + tenantSlug + '/analytics/';
        var params = [];
        if (currentDays > 0) params.push('days=' + currentDays);
        if (currentOffset !== 0) params.push('offset=' + currentOffset);
        if (currentSource) params.push('source=' + encodeURIComponent(currentSource));
        if (params.length) url += '?' + params.join('&');

        updatePeriodLabel();
        updateNavButtons();

        fetch(url, {
            headers: {
                'X-CSRFToken': SAMA.getCookie('csrftoken'),
            },
        })
        .then(function(r) { return r.ok ? r.json() : null; })
        .then(function(data) {
            if (!data) return;
            updateStats(data.summary);
            drawCharts(data);
        })
        .catch(function(e) { console.error('Analytics error:', e); });
    }

    function updateStats(summary) {
        document.getElementById('stat-total').textContent = summary.total_leads || 0;
        document.getElementById('stat-conversion').textContent = Math.round((summary.conversion_rate || 0) * 100) + '%';
        document.getElementById('stat-avg').textContent = Math.round(summary.avg_days_to_close || 0);
        document.getElementById('stat-week').textContent = summary.leads_this_week || 0;
    }

    function drawCharts(data) {
        var colors = getColors();
        var stageColors = ['#3b82f6', '#f06539', '#f5a623', '#2ec27e', '#8b5cf6', '#ec4899'];

        Object.keys(charts).forEach(function(k) {
            if (charts[k]) charts[k].destroy();
        });

        var funnelData = data.funnel || [];
        var funnelLabels = funnelData.map(function(f) { return f.stage; });
        var funnelCounts = funnelData.map(function(f) { return f.count; });

        var maxCount = Math.max.apply(null, funnelCounts) || 1;
        var funnelColors = funnelData.map(function(f, i) {
            var pct = Math.round((f.count / maxCount) * 100);
            var alpha = 0.4 + (pct / 100) * 0.6;
            return stageColors[i % stageColors.length] + Math.round(alpha * 255).toString(16).padStart(2, '0');
        });

        charts.funnel = new Chart(
            document.getElementById('funnel-chart'),
            buildChartConfig('bar', {
                labels: funnelLabels,
                datasets: [{
                    label: 'Leads',
                    data: funnelCounts,
                    backgroundColor: funnelColors,
                    borderColor: stageColors.slice(0, funnelLabels.length),
                    borderWidth: 2,
                    borderRadius: 6,
                    barPercentage: 0.75,
                }],
            }, {
                indexAxis: 'y',
                plugins: {
                    legend: { display: false },
                    datalabels: {
                        anchor: 'end',
                        align: 'end',
                        color: colors.text,
                        font: { weight: 'bold', size: 12 },
                        formatter: function(value, ctx) {
                            var total = ctx.dataset.data.reduce(function(a, b) { return a + b; }, 0);
                            var pct = total > 0 ? Math.round((value / total) * 100) : 0;
                            return value + ' (' + pct + '%)';
                        },
                        display: true,
                    },
                },
                scales: {
                    x: {
                        ticks: { color: colors.muted },
                        grid: { color: colors.border, drawBorder: false },
                        beginAtZero: true,
                    },
                    y: {
                        ticks: { color: colors.text, font: { weight: 600, size: 11 } },
                        grid: { display: false },
                    },
                },
            })
        );

        var sourceData = data.leads_by_source || [];
        var sourceLabels = sourceData.map(function(s) { return s.source || 'Desconocido'; });
        var sourceCounts = sourceData.map(function(s) { return s.count; });
        var sourceColors = ['#3b82f6', '#f06539', '#f5a623', '#2ec27e', '#8b5cf6'];
        charts.source = new Chart(
            document.getElementById('source-chart'),
            buildChartConfig('doughnut', {
                labels: sourceLabels,
                datasets: [{
                    data: sourceCounts,
                    backgroundColor: sourceColors.slice(0, sourceLabels.length),
                    borderColor: colors.card,
                    borderWidth: 3,
                }],
            }, {
                cutout: '60%',
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: {
                            padding: 12,
                            usePointStyle: true,
                            color: colors.text,
                        },
                    },
                    datalabels: {
                        color: '#fff',
                        font: {
                            weight: 'bold',
                            size: 12,
                        },
                        formatter: function(value, ctx) {
                            var total = ctx.dataset.data.reduce(function(a, b) { return a + b; }, 0);
                            var pct = Math.round((value / total) * 100);
                            return pct > 5 ? value : '';
                        },
                    },
                },
            })
        );

        var dayData = data.leads_by_day || [];
        var wonData = data.leads_by_stage_won || [];
        var lostData = data.leads_by_stage_lost || [];
        var quotesData = data.quotes_sent || [];

        var monthNames = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic'];

        var isMonthlyView = dayData.length > 45;

        var dataMap = {};
        var allDates = new Set();

        dayData.forEach(function(d) {
            var date = new Date(d.date);
            dataMap[d.date] = { new: d.count, won: 0, lost: 0, quote: 0 };
            allDates.add(d.date);
        });

        wonData.forEach(function(d) {
            if (dataMap[d.date]) dataMap[d.date].won = d.count;
            allDates.add(d.date);
        });

        lostData.forEach(function(d) {
            if (dataMap[d.date]) dataMap[d.date].lost = d.count;
            allDates.add(d.date);
        });

        quotesData.forEach(function(d) {
            if (dataMap[d.date]) dataMap[d.date].quote = d.count;
            allDates.add(d.date);
        });

        var sortedDates = Array.from(allDates).sort();

        var groupedData = {};
        if (isMonthlyView) {
            sortedDates.forEach(function(dateStr) {
                var d = new Date(dateStr);
                var key = monthNames[d.getMonth()] + ' ' + d.getFullYear();
                if (!groupedData[key]) {
                    groupedData[key] = { new: 0, won: 0, lost: 0, quote: 0, year: d.getFullYear(), month: d.getMonth() };
                }
                var m = dataMap[dateStr];
                if (m) {
                    groupedData[key].new += m.new;
                    groupedData[key].won += m.won;
                    groupedData[key].lost += m.lost;
                    groupedData[key].quote += m.quote;
                }
            });
        } else {
            sortedDates.forEach(function(dateStr) {
                var d = new Date(dateStr);
                var key = d.getDate() + ' ' + monthNames[d.getMonth()];
                groupedData[key] = { new: 0, won: 0, lost: 0, quote: 0, year: d.getFullYear(), month: d.getMonth() };
                var m = dataMap[dateStr];
                if (m) {
                    groupedData[key].new = m.new;
                    groupedData[key].won = m.won;
                    groupedData[key].lost = m.lost;
                    groupedData[key].quote = m.quote;
                }
            });
        }

        var keys = Object.keys(groupedData).sort(function(a, b) {
            var da = groupedData[a], db = groupedData[b];
            if (da.year !== db.year) return da.year - db.year;
            return da.month - db.month;
        });

        var dayLabels = keys;
        var newCounts = keys.map(function(k) { return groupedData[k].new; });
        var wonCounts = keys.map(function(k) { return groupedData[k].won; });
        var lostCounts = keys.map(function(k) { return groupedData[k].lost; });
        var quoteCounts = keys.map(function(k) { return groupedData[k].quote; });

        var datasets = [
            {
                label: 'Leads nuevos',
                data: newCounts,
                borderColor: '#3b82f6',
                backgroundColor: 'rgba(59, 130, 246, 0.15)',
                fill: true,
                tension: 0.3,
                pointRadius: 3,
                pointBackgroundColor: '#3b82f6',
                borderWidth: 2,
            },
            {
                label: 'Cerrados Ganados',
                data: wonCounts,
                borderColor: '#2ec27e',
                backgroundColor: 'transparent',
                borderDash: [5, 5],
                tension: 0.3,
                pointRadius: 2,
                pointBackgroundColor: '#2ec27e',
                borderWidth: 2,
            },
            {
                label: 'Cerrados Perdidos',
                data: lostCounts,
                borderColor: '#ef4444',
                backgroundColor: 'transparent',
                borderDash: [5, 5],
                tension: 0.3,
                pointRadius: 2,
                pointBackgroundColor: '#ef4444',
                borderWidth: 2,
            },
            {
                label: 'Cotizaciones Enviadas',
                data: quoteCounts,
                borderColor: '#f5a623',
                backgroundColor: 'transparent',
                borderDash: [2, 2],
                tension: 0.3,
                pointRadius: 2,
                pointBackgroundColor: '#f5a623',
                borderWidth: 2,
            }
        ];

        charts.timeline = new Chart(
            document.getElementById('timeline-chart'),
            buildChartConfig('line', {
                labels: dayLabels,
                datasets: datasets,
            }, {
                plugins: {
                    legend: {
                        display: true,
                        position: 'top',
                        labels: {
                            color: colors.text,
                            usePointStyle: true,
                            padding: 15,
                            filter: function(item) {
                                return item.text !== '';
                            },
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
                        ticks: { color: colors.muted },
                        grid: { color: colors.border },
                        beginAtZero: true,
                    },
                },
            })
        );
    }

    function updateNavButtons() {
        var prevBtn = document.getElementById('prev-period-btn');
        var nextBtn = document.getElementById('next-period-btn');
        if (currentDays === 0) {
            if (prevBtn) prevBtn.style.visibility = 'hidden';
            if (nextBtn) nextBtn.style.visibility = 'hidden';
        } else {
            if (prevBtn) prevBtn.style.visibility = 'visible';
            if (nextBtn) nextBtn.style.visibility = currentOffset === 0 ? 'hidden' : 'visible';
        }
    }

    document.getElementById('prev-period-btn').addEventListener('click', function() {
        if (currentDays === 0) return;
        currentOffset += 1;
        loadAnalytics();
    });

    document.getElementById('next-period-btn').addEventListener('click', function() {
        if (currentDays === 0 || currentOffset <= 0) return;
        currentOffset -= 1;
        loadAnalytics();
    });

    document.querySelectorAll('.range-btn').forEach(function(btn) {
        btn.addEventListener('click', function() {
            document.querySelectorAll('.range-btn').forEach(function(b) { b.classList.remove('active'); });
            btn.classList.add('active');
            currentDays = parseInt(btn.getAttribute('data-days'), 10);
            currentOffset = 0;
            loadAnalytics();
        });
    });

    var sourceSelect = document.getElementById('source-filter');
    if (sourceSelect) {
        sourceSelect.addEventListener('change', function() {
            currentSource = sourceSelect.value;
            loadAnalytics();
        });
    }

    // Escuchar cambios de tema desde theme.js (evento custom)
    window.addEventListener('theme-changed', function(e) {
        loadAnalytics();
    });

    // Fallback: event listener para cambios en otras pestañas
    window.addEventListener('storage', function(e) {
        if (e.key === 'sama-crm-theme') {
            document.body.classList.toggle('theme-light', e.newValue === 'light');
            loadAnalytics();
        }
    });

    loadAnalytics();
})();