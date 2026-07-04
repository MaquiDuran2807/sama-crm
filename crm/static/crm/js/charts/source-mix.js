/**
 * SourceMix chart renderer — stacked bar chart by source per month.
 * Dependencies: bridge.js (SAMACharts global)
 */
(function() {
    'use strict';

    var chartInstance = null;
    var months = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic'];

    function getColors() {
        var theme = localStorage.getItem('sama-crm-theme') || 'dark';
        return theme === 'light'
            ? { text: '#1a1d24', muted: '#6b7385', border: '#e2e6ed' }
            : { text: '#d4d8e3', muted: '#6b7385', border: '#313849' };
    }

    function render(sourceMonthlyData) {
        var canvas = document.getElementById('source-mix-chart');
        if (!canvas) return;

        if (chartInstance) {
            chartInstance.destroy();
            chartInstance = null;
        }

        if (!sourceMonthlyData || sourceMonthlyData.length === 0) {
            var ctx2 = canvas.getContext('2d');
            var colors2 = getColors();
            chartInstance = new Chart(ctx2, {
                type: 'bar',
                data: { labels: [], datasets: [] },
                options: {
                    responsive: true,
                    maintainAspectRatio: true,
                    plugins: { legend: { display: false } },
                },
            });
            return;
        }

        var sourceColors = {
            meta: '#1877F2',
            google: '#4285F4',
            tiktok: '#ff0050',
            web: '#64748b',
            referral: '#FF9933',
        };

        var platforms = ['meta', 'google', 'tiktok', 'web', 'referral'];

        var labels = sourceMonthlyData.map(function(r) {
            var parts = r.month.split('-');
            var monthIdx = parseInt(parts[1], 10) - 1;
            return months[monthIdx].substring(0, 3) + ' ' + parts[0];
        });

        var datasets = platforms.map(function(p) {
            return {
                label: p.charAt(0).toUpperCase() + p.slice(1),
                data: sourceMonthlyData.map(function(r) { return r[p] || 0; }),
                backgroundColor: sourceColors[p] || '#64748b',
                borderColor: 'transparent',
                borderWidth: 0,
                stack: 'sources',
            };
        });

        var ctx = canvas.getContext('2d');
        var colors = getColors();

        chartInstance = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: datasets,
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
                        stacked: true,
                        ticks: { color: colors.muted, font: { size: 11 } },
                        grid: { display: false },
                    },
                    y: {
                        stacked: true,
                        ticks: { color: colors.muted },
                        grid: { color: colors.border },
                        beginAtZero: true,
                    },
                },
            },
        });
    }

    window.SAMACharts = window.SAMACharts || {};
    window.SAMACharts.SourceMix = { render: render };
})();