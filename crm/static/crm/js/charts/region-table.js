/**
 * RegionTable chart renderer — department data table.
 * Dependencies: bridge.js (SAMACharts global)
 */
(function() {
    'use strict';

    var currentMapMetric = 'total';

    function getMapIntensity(r, metric) {
        if (metric === 'won') return r.intensidad_won || 0;
        if (metric === 'conversion') return (r.conversion_rate || 0) / 100;
        return r.intensidad || 0;
    }

    function getMapColor(intensity) {
        if (intensity === 0) return 'var(--color-muted)';
        if (intensity > 0.8) return 'var(--color-heat-5)';
        if (intensity > 0.6) return 'var(--color-heat-4)';
        if (intensity > 0.4) return 'var(--color-heat-3)';
        if (intensity > 0.2) return 'var(--color-heat-2)';
        return 'var(--color-heat-1)';
    }

    function render(geocodedData) {
        var tbody = document.getElementById('region-table-body');
        if (!tbody) return;

        if (!geocodedData || geocodedData.length === 0) {
            tbody.innerHTML = '<tr><td colspan="5" class="text-center text-muted py-4">Sin datos disponibles</td></tr>';
            return;
        }

        var html = '';
        geocodedData.forEach(function(r) {
            var total = r.total || 0;
            var won = r.won || 0;
            var lost = r.lost || 0;
            var conversion = total > 0 ? Math.round((won / total) * 100) : 0;
            var barIntensity = getMapIntensity(r, currentMapMetric);
            var barColor = getMapColor(barIntensity);
            var barWidth = Math.round(barIntensity * 100);

            html += '<tr>' +
                '<td><strong>' + (r.departamento || r.ciudad || '—') + '</strong></td>' +
                '<td class="text-center fw-bold">' + total + '</td>' +
                '<td class="text-center" style="color:' + (won > 0 ? '#22c55e' : '#94a3b8') + '">' + won + '</td>' +
                '<td class="text-center" style="color:' + (lost > 0 ? '#ef4444' : '#94a3b8') + '">' + lost + '</td>' +
                '<td>' +
                    '<div class="d-flex align-items-center gap-2">' +
                        '<span class="badge" style="background:' + barColor + ';color:#fff;font-size:10px">' + conversion + '%</span>' +
                        '<div class="conv-bar" style="flex:1"><div class="conv-bar-fill" style="width:' + barWidth + '%;background:' + barColor + '"></div></div>' +
                    '</div>' +
                '</td>' +
                '</tr>';
        });
        tbody.innerHTML = html;
    }

    window.SAMACharts = window.SAMACharts || {};
    window.SAMACharts.RegionTable = { render: render };
})();