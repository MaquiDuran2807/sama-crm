/**
 * Stats chart renderer — summary cards at the top of analytics.
 * Dependencies: bridge.js (SAMACharts global)
 */
(function() {
    'use strict';

    function render(summary) {
        var el;

        el = document.getElementById('stat-total');
        if (el) el.textContent = summary.total_leads || 0;

        el = document.getElementById('stat-conversion');
        if (el) el.textContent = Math.round((summary.conversion_rate || 0) * 100) + '%';

        el = document.getElementById('stat-avg');
        if (el) el.textContent = Math.round(summary.avg_days_to_close || 0);

        el = document.getElementById('stat-week');
        if (el) el.textContent = summary.leads_this_week || 0;

        el = document.getElementById('stat-won');
        if (el) el.textContent = summary.won_leads || 0;

        el = document.getElementById('stat-lost');
        if (el) el.textContent = summary.lost_leads || 0;
    }

    window.SAMACharts = window.SAMACharts || {};
    window.SAMACharts.Stats = { render: render };
})();