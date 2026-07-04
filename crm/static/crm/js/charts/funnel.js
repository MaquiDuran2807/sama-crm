/**
 * Funnel chart renderer — horizontal bar chart for sales funnel.
 * Dependencies: bridge.js (SAMACharts global)
 */
(function() {
    'use strict';

    var chartInstance = null;

    function render(funnelData, kpiTargets, summary) {
        var canvas = document.getElementById('funnel-chart');
        if (!canvas) return;

        if (chartInstance) {
            chartInstance.destroy();
            chartInstance = null;
        }

        if (!funnelData || funnelData.length === 0) return;

        var totalLeads = funnelData.reduce(function(s, f) { return s + f.count; }, 0);
        var summaryEl = document.getElementById('funnel-summary');

        var convTarget = null;
        var convRatio = null;
        if (kpiTargets) {
            kpiTargets.forEach(function(t) {
                if (t.metric_type === 'conversions') convTarget = t;
            });
            if (convTarget && convTarget.target_value > 0) {
                convRatio = Math.round((totalLeads / convTarget.target_value) * 100);
            }
        }

        if (summaryEl) {
            var html = '<span class="funnel-total">' + totalLeads + ' leads totales</span>';
            if (convTarget && convTarget.target_value > 0) {
                html += ' <span style="color:var(--color-primary);font-weight:700">(' + convRatio + '% de meta)</span>';
            }
            summaryEl.innerHTML = html;
        }

        var samaGradient = [
            '#003366', '#004080', '#1959A8', '#4078C0',
            '#A04C1E', '#CC6628', '#E67D33', '#F08C40',
            '#FF9933'
        ];

        var labels = funnelData.map(function(f) { return f.stage; });
        var counts = funnelData.map(function(f) { return f.count; });

        var bgColors = funnelData.map(function(f, i) {
            var idx = Math.floor((i / Math.max(funnelData.length - 1, 1)) * (samaGradient.length - 1));
            return samaGradient[idx];
        });

        var borderColors = funnelData.map(function(f, i) {
            var idx = Math.floor((i / Math.max(funnelData.length - 1, 1)) * (samaGradient.length - 1));
            return samaGradient[Math.min(idx + 1, samaGradient.length - 1)];
        });

        var ctx = canvas.getContext('2d');
        var colors = (function() {
            var theme = localStorage.getItem('sama-crm-theme') || 'dark';
            return theme === 'light'
                ? { text: '#1a1d24', muted: '#6b7385', border: '#e2e6ed' }
                : { text: '#d4d8e3', muted: '#6b7385', border: '#313849' };
        })();

        chartInstance = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Leads',
                    data: counts,
                    backgroundColor: bgColors,
                    borderColor: borderColors,
                    borderWidth: 2,
                    borderRadius: 4,
                    barPercentage: 0.75,
                }],
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
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
            },
        });
    }

    window.SAMACharts = window.SAMACharts || {};
    window.SAMACharts.Funnel = { render: render };
})();