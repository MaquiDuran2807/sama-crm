/**
 * Map chart renderer — Colombia SVG map with heat coloring.
 * Dependencies: bridge.js (SAMACharts global)
 */
(function() {
    'use strict';

    var currentMapMetric = 'total';
    var currentGeocodedData = null;
    var deptNameToSVGId = {
        'amazonas': 'AMA', 'antioquia': 'ANT', 'arauca': 'ARA', 'atlantico': 'ATL',
        'bogota d.c.': 'DC', 'bogota': 'DC',
        'bolivar': 'BOL', 'boyaca': 'BOY', 'caldas': 'CAL', 'caqueta': 'CAQ',
        'casanare': 'CAS', 'cauca': 'CAU', 'cesar': 'CES', 'choco': 'CHO',
        'cordoba': 'COR', 'cundinamarca': 'CUN',
        'guainia': 'GUA', 'guaviare': 'GUV', 'huila': 'HUI',
        'la guajira': 'LAG',
        'magdalena': 'MAG', 'meta': 'MET',
        'narino': 'NAR', 'norte de santander': 'NSA',
        'putumayo': 'PUT', 'quindio': 'QUI', 'risaralda': 'RIS',
        'santander': 'SAN', 'sucre': 'SUC',
        'san andres y providencia': 'SAP',
        'tolima': 'TOL', 'valle del cauca': 'VAC',
        'vaupes': 'VAU', 'vichada': 'VID'
    };

    function normalizeDeptKey(name) {
        if (!name) return '';
        return name.toLowerCase()
            .normalize('NFD').replace(/[\u0300-\u036f]/g, '')
            .replace(/[^a-z0-9]/g, '_')
            .replace(/_+/g, '_')
            .replace(/^_|_$/g, '')
            .trim();
    }

    function getMapIntensity(data, metric) {
        if (metric === 'won') return data.intensidad_won || 0;
        if (metric === 'conversion') return (data.conversion || 0) / 100;
        return data.intensidad || 0;
    }

    function getMapColor(intensity) {
        if (intensity === 0) return 'var(--color-muted)';
        if (intensity > 0.8) return 'var(--color-heat-5)';
        if (intensity > 0.6) return 'var(--color-heat-4)';
        if (intensity > 0.4) return 'var(--color-heat-3)';
        if (intensity > 0.2) return 'var(--color-heat-2)';
        return 'var(--color-heat-1)';
    }

    function getOrCreateTooltip() {
        var tooltip = document.getElementById('map-tooltip');
        if (!tooltip) {
            tooltip = document.createElement('div');
            tooltip.id = 'map-tooltip';
            tooltip.className = 'map-tooltip';
            document.body.appendChild(tooltip);
        }
        return tooltip;
    }

    function showMapTooltip(e, text) {
        var tooltip = getOrCreateTooltip();
        tooltip.textContent = text;
        tooltip.style.display = 'block';
        moveMapTooltip(e);
    }

    function moveMapTooltip(e) {
        var tooltip = document.getElementById('map-tooltip');
        if (tooltip && tooltip.style.display === 'block') {
            tooltip.style.left = (e.pageX + 12) + 'px';
            tooltip.style.top = (e.pageY + 12) + 'px';
        }
    }

    function hideMapTooltip() {
        var tooltip = document.getElementById('map-tooltip');
        if (tooltip) tooltip.style.display = 'none';
    }

    function render(regionData, geocodedData) {
        var container = document.getElementById('colombia-svg-map');
        if (!container) return;

        currentGeocodedData = geocodedData;

        container.innerHTML = '';
        fetch('/static/crm/img/colombia.svg')
            .then(function(r) { return r.text(); })
            .then(function(svgText) {
                container.innerHTML = svgText;
                var svg = container.querySelector('svg');
                if (!svg) return;

                var dataMap = {};
                if (geocodedData && geocodedData.length > 0) {
                    geocodedData.forEach(function(d) {
                        var rawName = (d.departamento || d.ciudad || '').trim().toLowerCase();
                        var svgId = deptNameToSVGId[rawName];
                        if (svgId) {
                            var conversionRate = d.total > 0 ? Math.round((d.won / d.total) * 100) : 0;
                            dataMap[svgId.toLowerCase()] = {
                                total: d.total,
                                won: d.won || 0,
                                lost: d.lost || 0,
                                conversion: conversionRate,
                                intensidad: d.intensidad || 0,
                                intensidad_won: d.intensidad_won || 0,
                                label: d.departamento || d.ciudad
                            };
                        }
                    });
                }

                var paths = svg.querySelectorAll('path');
                paths.forEach(function(path) {
                    var rawId = (path.getAttribute('id') || '').replace('CO-', '').trim().toLowerCase();
                    var data = dataMap[rawId];
                    var newPath = path.cloneNode(true);
                    path.parentNode.replaceChild(newPath, path);

                    if (data) {
                        var intensity = getMapIntensity(data, currentMapMetric);
                        var color = getMapColor(intensity);
                        newPath.style.fill = color;

                        newPath.addEventListener('mouseenter', function(e) {
                            var won = data.won || 0;
                            var lost = data.lost || 0;
                            var total = data.total || 0;
                            var convPct = total > 0 ? Math.round((won / total) * 100) : 0;
                            var statusNote = '';
                            if (total > 0 && won === 0 && lost === 0) statusNote = ' (en curso)';
                            else if (total > 0 && won === 0 && lost > 0) statusNote = ' (sin conversion)';
                            showMapTooltip(e,
                                data.label + '\n' +
                                'Leads: ' + total + ' | Ganados: ' + won + ' | Perdidos: ' + lost + '\n' +
                                'Conversion: ' + convPct + '%' + statusNote
                            );
                        });
                        newPath.addEventListener('mousemove', moveMapTooltip);
                        newPath.addEventListener('mouseleave', hideMapTooltip);
                    } else {
                        newPath.style.fill = 'var(--color-muted)';
                    }
                });
            })
            .catch(function(e) { console.error('[Map] failed to load SVG:', e); });
    }

    function setMetric(metric) {
        currentMapMetric = metric;
        if (currentGeocodedData) render(null, currentGeocodedData);
    }

    window.SAMACharts = window.SAMACharts || {};
    window.SAMACharts.Map = { render: render, setMetric: setMetric };
})();