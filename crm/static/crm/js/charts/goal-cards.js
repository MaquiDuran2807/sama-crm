/**
 * GoalCards chart renderer — KPI goal progress cards.
 * Renders any metric type dynamically using metric metadata (icon, color, unit).
 * Dependencies: bridge.js (SAMACharts global)
 */
(function() {
    'use strict';

    function render(kpiTargets, periodLabel) {
        var emptyEl = document.getElementById('goal-no-targets');
        var listEl = document.getElementById('goal-cards-list');
        if (!emptyEl || !listEl) return;

        if (!kpiTargets || kpiTargets.length === 0) {
            emptyEl.style.display = 'flex';
            listEl.style.display = 'none';
            return;
        }

        emptyEl.style.display = 'none';
        listEl.style.display = 'grid';
        listEl.innerHTML = '';

        kpiTargets.forEach(function(target) {
            var pct = target.progress_percent || 0;
            var status = pct >= 80 ? 'on-track' : (pct >= 50 ? 'at-risk' : 'behind');
            var isPercent = target.metric_unit === '%';
            var isCurrency = target.metric_unit === 'COP';

            var current = target.current_value || 0;
            var targetVal = target.target_value || 0;

            var displayCurrent = isPercent
                ? current.toFixed(1) + '%'
                : (isCurrency ? formatCOP(current) : Math.round(current));
            var displayTarget = isPercent
                ? targetVal.toFixed(1) + '%'
                : (isCurrency ? formatCOP(targetVal) : Math.round(targetVal));

            var card = document.createElement('div');
            card.className = 'goal-card ' + status;
            card.innerHTML =
                '<div class="goal-card-header">' +
                    '<span class="goal-icon" style="background:' + (target.metric_color || '#3b82f6') + '1a;color:' + (target.metric_color || '#3b82f6') + '">' +
                        '<i class="' + (target.metric_icon || 'bi-graph-up') + '"></i>' +
                    '</span>' +
                    '<div class="goal-card-meta">' +
                        '<span class="goal-name">' + (target.name || target.metric_type) + '</span>' +
                        '<span class="goal-period">' + (periodLabel || target.period_type) + '</span>' +
                    '</div>' +
                '</div>' +
                '<div class="goal-numbers">' +
                    '<span class="goal-current">' + displayCurrent + '</span>' +
                    '<span class="goal-separator">/</span>' +
                    '<span class="goal-target">' + displayTarget + ' ' + (target.metric_unit || '') + '</span>' +
                '</div>' +
                '<div class="goal-progress-container">' +
                    '<div class="goal-progress-bar-track">' +
                        '<div class="goal-progress-bar-fill" style="width:' + Math.min(pct, 100) + '%;background:' + (target.metric_color || '#3b82f6') + '"></div>' +
                    '</div>' +
                    '<span class="goal-percent" style="color:' + (target.metric_color || '#3b82f6') + '">' + Math.round(pct) + '%</span>' +
                '</div>';
            listEl.appendChild(card);
        });
    }

    function formatCOP(value) {
        if (value >= 1000000) {
            return '$' + (value / 1000000).toFixed(1) + 'M';
        } else if (value >= 1000) {
            return '$' + (value / 1000).toFixed(0) + 'K';
        }
        return '$' + Math.round(value);
    }

    window.SAMACharts = window.SAMACharts || {};
    window.SAMACharts.GoalCards = { render: render };
})();