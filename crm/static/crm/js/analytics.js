(function() {
    'use strict';

    var tenantSlug = SAMA.getTenantSlug();
    var currentDays = 30;
    var currentSource = '';
    var charts = {};
    var currentOffset = 0;
    var currentGeocodedData = null;
    var currentMapMetric = 'total';
    var timelineAllDatasets = [];
    var leadsByStage = {};
    var pipelineStages = [];
    var selectedPhases = new Set();

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

    var months = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic'];

    var darkColors = {
        bg: '#1a1d24', surface: '#21252e', card: '#262b36',
        border: '#313849', text: '#d4d8e3', muted: '#6b7385',
        accent: '#f06539', success: '#2ec27e', warning: '#f5a623', info: '#3b82f6',
    };

    var lightColors = {
        bg: '#f5f6f8', surface: '#ffffff', card: '#ffffff',
        border: '#e2e6ed', text: '#1a1d24', muted: '#6b7385',
        accent: '#f06539', success: '#2ec27e', warning: '#f5a623', info: '#3b82f6',
    };

    var stageColors = {
        'Lead': '#3b82f6',
        'Calificacion': '#8b5cf6',
        'Cotizacion Enviada': '#f5a623',
        'Seguimiento': '#06b6d4',
        'Cerrado Ganado': '#2ec27e',
        'Cerrado Perdido': '#ef4444',
        'Cotización Enviada': '#f5a623',
    };

    function getColors() {
        var theme = localStorage.getItem('sama-crm-theme') || 'dark';
        return theme === 'light' ? lightColors : darkColors;
    }

    function getViewMode(days) {
        if (days === 0) return 'monthly';
        if (days <= 30) return 'daily';
        if (days <= 90) return 'weekly';
        if (days <= 365) return 'monthly';
        return 'quarterly';
    }

    function formatDateRange(start, end) {
        var startStr = start.getDate() + ' ' + months[start.getMonth()].substring(0, 3);
        var endStr = end.getDate() + ' ' + months[end.getMonth()].substring(0, 3);
        if (start.getFullYear() !== end.getFullYear()) {
            return startStr + ' ' + start.getFullYear() + ' - ' + endStr + ' ' + end.getFullYear();
        }
        return startStr + ' - ' + endStr;
    }

    function getPeriodLabel() {
        if (currentDays === 0) return 'Historico completo';
        if (currentDays === 7) return 'Ultima semana';
        if (currentDays === 365) return 'Ultimo ano';
        var now = new Date();
        var end = new Date(now);
        var start = new Date(now);
        start.setDate(start.getDate() - currentDays + currentOffset * currentDays);
        end.setDate(end.getDate() + currentOffset * currentDays);
        if (currentOffset !== 0) {
            return formatDateRange(start, end);
        }
        return 'Ultimos ' + currentDays + ' dias';
    }

    function updatePeriodLabel() {
        var el = document.getElementById('current-period-label');
        if (el) el.textContent = getPeriodLabel();
    }

    function normalizeDeptKey(name) {
        if (!name) return '';
        return name.toLowerCase()
            .normalize('NFD').replace(/[\u0300-\u036f]/g, '')
            .replace(/[^a-z0-9]/g, '_')
            .replace(/_+/g, '_')
            .replace(/^_|_$/g, '')
            .trim();
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

    function fetchAnalytics() {
        var since = currentDays > 0
            ? new Date(Date.now() - (currentDays + currentOffset * currentDays) * 86400000).toISOString().split('T')[0]
            : '';
        var url = '/api/crm/tenants/' + tenantSlug + '/analytics/?days=' + currentDays + '&offset=' + currentOffset + '&source=' + encodeURIComponent(currentSource);
        if (since) url += '&since=' + since;

        fetch(url, {
            headers: {
                'X-CSRFToken': SAMA.getCookie('csrftoken'),
            },
        })
        .then(function(r) { return r.ok ? r.json() : null; })
        .then(function(data) {
            if (!data) return;

            renderStats(data.summary);
            renderMap(data.leads_by_region || []);
            renderRegionTable(data.leads_geocoded || []);
            renderFunnelChart(data.funnel || []);
            renderSourceMixChart(data.leads_by_source_monthly || []);

            leadsByStage = data.leads_by_stage || {};
            pipelineStages = data.pipeline_stages || [];

            var previousSelection = {};
            selectedPhases.forEach(function(v) { previousSelection[v] = true; });

            renderPhaseSelector();

            var stageNames = pipelineStages.map(function(s) { return s.name || s; });
            stageNames.forEach(function(name) {
                if (previousSelection.hasOwnProperty(name)) {
                    selectedPhases.add(name);
                }
            });

            renderTimeChart(
                data.leads_by_day || [],
                data.leads_by_stage_won || [],
                data.leads_by_stage_lost || [],
                data.quotes_sent || [],
                leadsByStage,
                stageNames
            );
            currentGeocodedData = data.leads_geocoded || [];
            renderSVGMap(currentGeocodedData);
            updateNavButtons();
            updatePeriodLabel();
        })
        .catch(function(e) { console.error('Analytics error:', e); });
    }

    function renderStats(summary) {
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

    function renderMap(regionData) {
        var mapContainer = document.getElementById('colombia-svg-map');
        if (!mapContainer) return;

        var deptCounts = {};
        regionData.forEach(function(r) {
            var key = normalizeDeptKey(r.department);
            deptCounts[key] = r;
        });

        var maxTotal = 1;
        regionData.forEach(function(r) {
            if (r.total > maxTotal) maxTotal = r.total;
        });

        var colorScale = function(total) {
            if (!total || total === 0) return '#64748b';
            var ratio = total / maxTotal;
            if (ratio < 0.33) return '#dbeafe';
            if (ratio < 0.66) return '#60a5fa';
            return '#003366';
        };

        var svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
        svg.setAttribute('viewBox', '30 100 380 400');
        svg.setAttribute('class', 'col-map-svg');

        var tooltip = document.createElement('div');
        tooltip.style.cssText = 'position:absolute;background:#fff;border:1px solid #e2e6ed;border-radius:8px;padding:8px 12px;font-size:12px;color:#1a1d24;pointer-events:none;display:none;z-index:100;box-shadow:0 4px 12px rgba(0,0,0,0.15);';
        tooltip.style.position = 'absolute';
        mapContainer.style.position = 'relative';
        mapContainer.appendChild(tooltip);

        var deptPaths = [
            { id: 'ANTIOQUIA', d: 'M180,200 L220,180 L260,190 L280,230 L270,280 L240,310 L200,300 L170,260 Z', dept: 'Antioquia' },
            { id: 'CUNDINAMARCA', d: 'M240,120 L280,110 L300,140 L290,180 L260,190 L220,180 L230,140 Z', dept: 'Cundinamarca' },
            { id: 'VALLE', d: 'M140,240 L180,200 L170,260 L150,300 L120,290 L110,260 Z', dept: 'Valle del Cauca' },
            { id: 'ATLANTICO', d: 'M200,320 L240,310 L260,330 L250,360 L220,365 L195,340 Z', dept: 'Atlantico' },
            { id: 'SANTANDER', d: 'M230,180 L270,170 L290,200 L280,240 L250,250 L220,230 Z', dept: 'Santander' },
            { id: 'BOYACA', d: 'M270,140 L300,130 L310,160 L300,190 L280,195 L260,170 Z', dept: 'Boyaca' },
            { id: 'NARINO', d: 'M60,300 L110,260 L120,290 L110,340 L80,350 L50,330 Z', dept: 'Narino' },
            { id: 'CAUCA', d: 'M100,260 L140,240 L150,280 L140,320 L110,310 L95,285 Z', dept: 'Cauca' },
            { id: 'TOLIMA', d: 'M180,230 L220,210 L240,250 L230,290 L190,300 L170,270 Z', dept: 'Tolima' },
            { id: 'HUILA', d: 'M200,270 L240,250 L260,290 L250,330 L210,340 L190,300 Z', dept: 'Huila' },
            { id: 'MAGDALENA', d: 'M170,310 L200,300 L210,340 L200,370 L165,365 L160,335 Z', dept: 'Magdalena' },
            { id: 'CALDAS', d: 'M190,210 L220,200 L230,240 L210,270 L185,265 L180,230 Z', dept: 'Caldas' },
            { id: 'CORDOBA', d: 'M220,260 L260,240 L280,280 L270,320 L240,330 L215,300 Z', dept: 'Cordoba' },
            { id: 'SUCRE', d: 'M165,335 L200,325 L210,355 L195,375 L165,365 Z', dept: 'Sucre' },
            { id: 'BOLIVAR', d: 'M150,360 L195,350 L210,380 L200,410 L155,400 L145,375 Z', dept: 'Bolivar' },
            { id: 'CESAR', d: 'M190,310 L230,300 L245,335 L235,370 L195,365 L185,335 Z', dept: 'Cesar' },
            { id: 'NORTE_SANTANDER', d: 'M270,200 L310,190 L320,230 L300,260 L265,255 L260,225 Z', dept: 'Norte de Santander' },
            { id: 'CAQUETA', d: 'M280,170 L330,160 L340,210 L320,250 L280,245 L275,205 Z', dept: 'Caqueta' },
            { id: 'META', d: 'M250,190 L310,180 L320,230 L300,270 L260,265 L245,225 Z', dept: 'Meta' },
            { id: 'CASANARE', d: 'M310,200 L350,190 L365,230 L355,270 L315,265 L305,230 Z', dept: 'Casanare' },
            { id: 'RISARALDA', d: 'M155,230 L185,220 L195,255 L180,280 L150,275 L145,245 Z', dept: 'Risaralda' },
            { id: 'QUINDIO', d: 'M175,240 L195,235 L200,260 L190,280 L172,275 L168,250 Z', dept: 'Quindio' },
            { id: 'CALDAS2', d: 'M165,260 L185,255 L192,285 L182,305 L165,300 L160,270 Z', dept: 'Caldas' },
            { id: 'CHOCO', d: 'M110,200 L155,195 L165,240 L155,280 L120,275 L100,235 Z', dept: 'Choco' },
            { id: 'LA_GUAJIRA', d: 'M260,340 L310,330 L320,365 L305,395 L265,385 L255,355 Z', dept: 'La Guajira' },
            { id: 'VICHADA', d: 'M330,190 L380,185 L390,240 L370,290 L330,285 L325,235 Z', dept: 'Vichada' },
            { id: 'GUANIA', d: 'M370,240 L400,235 L410,285 L395,320 L365,315 L360,265 Z', dept: 'Guainia' },
            { id: 'VAUPES', d: 'M370,310 L400,305 L410,345 L395,380 L365,375 L360,335 Z', dept: 'Vaupes' },
            { id: 'GUAVIARE', d: 'M330,280 L370,275 L380,315 L365,350 L325,345 L320,305 Z', dept: 'Guaviare' },
            { id: 'PUTUMAYO', d: 'M290,300 L330,295 L340,340 L325,375 L290,370 L280,330 Z', dept: 'Putumayo' },
            { id: 'AMAZONAS', d: 'M340,370 L385,365 L395,420 L370,460 L330,455 L325,405 Z', dept: 'Amazonas' },
            { id: 'SAN_ANDRES', d: 'M100,430 L125,425 L130,450 L120,470 L95,465 L90,445 Z', dept: 'San Andres' },
        ];

        deptPaths.forEach(function(pathInfo) {
            var path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
            path.setAttribute('id', pathInfo.id);
            path.setAttribute('d', pathInfo.d);
            path.setAttribute('data-dept', pathInfo.dept);

            var mapKey = normalizeDeptKey(pathInfo.dept);
            var regionInfo = deptCounts[mapKey];

            if (regionInfo) {
                path.setAttribute('fill', colorScale(regionInfo.total));
                path.setAttribute('stroke', '#ffffff');
                path.setAttribute('stroke-width', '1');
                path.setAttribute('class', 'map-region');
                path.setAttribute('data-total', regionInfo.total);
                path.setAttribute('data-won', regionInfo.won);
                path.setAttribute('data-conv', regionInfo.conversion_rate);
                path.style.cursor = 'pointer';
                path.style.transition = 'opacity 0.2s';
            } else {
                path.setAttribute('fill', '#64748b');
                path.setAttribute('stroke', '#ffffff');
                path.setAttribute('stroke-width', '1');
                path.setAttribute('class', 'map-region');
                path.style.opacity = '0.5';
            }

            var capturedInfo = regionInfo;
            path.addEventListener('mouseenter', function(e) {
                var name = pathInfo.dept;
                var total = capturedInfo ? capturedInfo.total : 0;
                var won = capturedInfo ? capturedInfo.won : 0;
                var conv = capturedInfo ? capturedInfo.conversion_rate : 0;
                tooltip.innerHTML = '<strong>' + name + '</strong><br>Leads: ' + total + '<br>Ganados: ' + won + '<br>Conversion: ' + conv + '%';
                tooltip.style.display = 'block';
                tooltip.style.opacity = '1';
                path.style.opacity = '0.8';
            });

            path.addEventListener('mousemove', function(e) {
                var rect = mapContainer.getBoundingClientRect();
                var x = e.clientX - rect.left + 10;
                var y = e.clientY - rect.top + 10;
                tooltip.style.left = x + 'px';
                tooltip.style.top = y + 'px';
            });

            path.addEventListener('mouseleave', function() {
                tooltip.style.display = 'none';
                tooltip.style.opacity = '0';
                path.style.opacity = capturedInfo ? '1' : '0.5';
            });

            svg.appendChild(path);
        });

        mapContainer.appendChild(svg);

        var legendDiv = document.createElement('div');
        legendDiv.className = 'map-legend';
        legendDiv.innerHTML = '' +
            '<span class="legend-item"><span class="legend-dot" style="background:#64748b"></span>Sin datos</span>' +
            '<span class="legend-item"><span class="legend-dot" style="background:#dbeafe"></span>Bajo</span>' +
            '<span class="legend-item"><span class="legend-dot" style="background:#60a5fa"></span>Medio</span>' +
            '<span class="legend-item"><span class="legend-dot" style="background:#003366"></span>Alto</span>';
        legendDiv.style.cssText = 'display:flex;gap:12px;font-size:11px;color:#888;margin-top:8px;flex-wrap:wrap;';
        mapContainer.appendChild(legendDiv);
    }

    function renderRegionTable(geocodedData) {
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
            var mapIntensity = getMapIntensity(r, currentMapMetric);
            var barColor = getMapColor(mapIntensity);
            var barWidth = Math.round(mapIntensity * 100);

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

    function renderSVGMap(geocodedData) {
        var container = document.getElementById('colombia-svg-map');
        if (!container) return;

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
            .catch(function(e) { console.error('[SVG Map] failed to load:', e); });
    }

    function getMapIntensity(data, metric) {
        if (metric === 'won') return data.intensidad_won || 0;
        if (metric === 'conversion') return (data.conversion || 0) / 100;
        return data.intensidad || 0;
    }

    function getMapValue(data, metric) {
        if (metric === 'won') return data.won || 0;
        if (metric === 'conversion') return data.conversion || 0;
        return data.total || 0;
    }

    function getMapColor(intensity) {
        if (intensity === 0) return 'var(--color-muted)';
        if (intensity > 0.8) return 'var(--color-heat-5)';
        if (intensity > 0.6) return 'var(--color-heat-4)';
        if (intensity > 0.4) return 'var(--color-heat-3)';
        if (intensity > 0.2) return 'var(--color-heat-2)';
        return 'var(--color-heat-1)';
    }

    function showMapTooltip(e, text) {
        var tooltip = getOrCreateTooltip();
        tooltip.textContent = text;
        tooltip.style.display = 'block';
        moveMapTooltip(e);
    }

    function hideMapTooltip() {
        var tooltip = document.getElementById('map-tooltip');
        if (tooltip) tooltip.style.display = 'none';
    }

    function moveMapTooltip(e) {
        var tooltip = document.getElementById('map-tooltip');
        if (tooltip && tooltip.style.display === 'block') {
            tooltip.style.left = (e.pageX + 12) + 'px';
            tooltip.style.top = (e.pageY + 12) + 'px';
        }
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

    function renderFunnelChart(funnelData) {
        var canvas = document.getElementById('funnel-chart');
        if (!canvas) return;

        if (charts.funnel) {
            charts.funnel.destroy();
            delete charts.funnel;
        }

        if (!funnelData || funnelData.length === 0) return;

        var totalLeads = funnelData.reduce(function(s, f) { return s + f.count; }, 0);
        var summaryEl = document.getElementById('funnel-summary');
        if (summaryEl) {
            summaryEl.innerHTML = '<span class="funnel-total">' + totalLeads + ' leads totales</span>';
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
        var colors = getColors();

        charts.funnel = new Chart(ctx, {
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

    function renderSourceMixChart(sourceMonthlyData) {
        var canvas = document.getElementById('source-mix-chart');
        if (!canvas) return;

        if (charts.sourceMix) {
            charts.sourceMix.destroy();
            delete charts.sourceMix;
        }

        if (!sourceMonthlyData || sourceMonthlyData.length === 0) {
            var ctx2 = canvas.getContext('2d');
            var colors2 = getColors();
            charts.sourceMix = new Chart(ctx2, {
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

        charts.sourceMix = new Chart(ctx, {
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

    function groupDataByPeriod(dataArray, viewMode) {
        var result = {};

        if (viewMode === 'daily') {
            dataArray.forEach(function(d) {
                var parts = d.date.split('-');
                var year = parseInt(parts[0], 10);
                var month = parseInt(parts[1], 10) - 1;
                var day = parseInt(parts[2], 10);
                var key = day + ' ' + months[month];
                if (!result[key]) result[key] = { count: 0, year: year, month: month, day: day, sortKey: String(year) + String(month).padStart(2, '0') + String(day).padStart(2, '0') };
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
                if (!result[key]) result[key] = { count: 0, year: year, month: month, week: weekNum, sortKey: String(year) + String(month).padStart(2, '0') + String(weekNum).padStart(2, '0') };
                result[key].count += d.count;
            });
        } else if (viewMode === 'monthly') {
            dataArray.forEach(function(d) {
                var parts = d.date.split('-');
                var year = parseInt(parts[0], 10);
                var month = parseInt(parts[1], 10) - 1;
                var key = months[month] + ' ' + year;
                if (!result[key]) result[key] = { count: 0, year: year, month: month, sortKey: String(year) + String(month).padStart(2, '0') };
                result[key].count += d.count;
            });
        } else if (viewMode === 'quarterly') {
            dataArray.forEach(function(d) {
                var parts = d.date.split('-');
                var year = parseInt(parts[0], 10);
                var month = parseInt(parts[1], 10) - 1;
                var quarter = Math.floor(month / 3) + 1;
                var key = 'Q' + quarter + ' ' + year;
                if (!result[key]) result[key] = { count: 0, year: year, quarter: quarter, sortKey: String(year) + String(quarter) };
                result[key].count += d.count;
            });
        }

        var sortedKeys = Object.keys(result).sort(function(a, b) {
            return result[a].sortKey.localeCompare(result[b].sortKey);
        });

        return {
            labels: sortedKeys,
            values: sortedKeys.map(function(k) { return result[k].count; })
        };
    }

    function getWeekNumber(date) {
        var d = new Date(Date.UTC(date.getFullYear(), date.getMonth(), date.getDate()));
        var dayNum = d.getUTCDay() || 7;
        d.setUTCDate(d.getUTCDate() + 4 - dayNum);
        var yearStart = new Date(Date.UTC(d.getUTCFullYear(), 0, 1));
        return Math.ceil((((d - yearStart) / 86400000) + 1) / 7);
    }

    function buildStageDataMap(stageData, stageName, viewMode) {
        var records = stageData[stageName] || [];
        var map = {};
        var months2 = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic'];

        if (viewMode === 'daily') {
            records.forEach(function(r) {
                var parts = r.date.split('-');
                var year = parseInt(parts[0], 10);
                var month = parseInt(parts[1], 10) - 1;
                var day = parseInt(parts[2], 10);
                var key = day + ' ' + months2[month];
                map[key] = (map[key] || 0) + r.count;
            });
        } else if (viewMode === 'weekly') {
            records.forEach(function(r) {
                var parts = r.date.split('-');
                var year = parseInt(parts[0], 10);
                var month = parseInt(parts[1], 10) - 1;
                var day = parseInt(parts[2], 10);
                var dObj = new Date(year, month, day);
                var weekNum = getWeekNumber(dObj);
                var key = 'S' + weekNum + ' ' + months2[month].substring(0, 3);
                map[key] = (map[key] || 0) + r.count;
            });
        } else if (viewMode === 'monthly') {
            records.forEach(function(r) {
                var parts = r.date.split('-');
                var year = parseInt(parts[0], 10);
                var month = parseInt(parts[1], 10) - 1;
                var key = months2[month] + ' ' + year;
                map[key] = (map[key] || 0) + r.count;
            });
        } else if (viewMode === 'quarterly') {
            records.forEach(function(r) {
                var parts = r.date.split('-');
                var year = parseInt(parts[0], 10);
                var month = parseInt(parts[1], 10) - 1;
                var quarter = Math.floor(month / 3) + 1;
                var key = 'Q' + quarter + ' ' + year;
                map[key] = (map[key] || 0) + r.count;
            });
        }

        return map;
    }

    function renderTimeChart(dayData, wonData, lostData, quoteData, stageData, stageNames) {
        var canvas = document.getElementById('timeline-chart');
        if (!canvas) return;

        if (charts.timeline) {
            charts.timeline.destroy();
            delete charts.timeline;
        }

        var viewMode = getViewMode(currentDays);

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
            for (var si = 0; si < pipelineStages.length; si++) {
                if ((pipelineStages[si].name || pipelineStages[si]) === stageName) {
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

        charts.timeline = new Chart(ctx, {
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
    }

    function renderPhaseSelector() {
        var container = document.getElementById('phase-selector');
        if (!container) return;

        selectedPhases = new Set();

        container.innerHTML = '';

        pipelineStages.forEach(function(stage) {
            var name = stage.name || stage;
            var color = stage.color || stageColors[name] || '#6b7385';

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
        updateTimelineChart();
    }

    function updateTimelineChart() {
        if (!charts.timeline) return;
        if (timelineAllDatasets.length === 0) return;

        var newDatasets = selectedPhases.size > 0
            ? timelineAllDatasets.filter(function(ds) { return selectedPhases.has(ds.label); })
            : timelineAllDatasets.slice();

        charts.timeline.data.datasets = newDatasets;
        charts.timeline.update('none');
    }

    function applyTheme() {
        Object.keys(charts).forEach(function(k) {
            if (charts[k]) {
                charts[k].destroy();
            }
        });
        charts = {};
        if (typeof heatLayer !== 'undefined' && heatLayer) {
            heatMap.removeLayer(heatLayer);
            heatLayer = null;
        }
        if (typeof heatLegend !== 'undefined' && heatLegend) {
            heatMap.removeControl(heatLegend);
            heatLegend = null;
        }
        fetchAnalytics();
    }

    document.getElementById('prev-period-btn').addEventListener('click', function() {
        if (currentDays === 0) return;
        currentOffset += 1;
        fetchAnalytics();
    });

    document.getElementById('next-period-btn').addEventListener('click', function() {
        if (currentDays === 0 || currentOffset <= 0) return;
        currentOffset -= 1;
        fetchAnalytics();
    });

    document.querySelectorAll('.range-btn').forEach(function(btn) {
        btn.addEventListener('click', function() {
            document.querySelectorAll('.range-btn').forEach(function(b) { b.classList.remove('active'); });
            btn.classList.add('active');
            currentDays = parseInt(btn.getAttribute('data-days'), 10);
            currentOffset = 0;
            fetchAnalytics();
        });
    });

    var sourceSelect = document.getElementById('source-filter');
    if (sourceSelect) {
        sourceSelect.addEventListener('change', function() {
            currentSource = sourceSelect.value;
            fetchAnalytics();
        });
    }

    var metricSelect = document.getElementById('map-metric-select');
    if (metricSelect) {
        metricSelect.addEventListener('change', function() {
            currentMapMetric = metricSelect.value;
            if (currentGeocodedData) renderSVGMap(currentGeocodedData);
        });
    }

    window.addEventListener('theme-changed', function() {
        applyTheme();
    });

    window.addEventListener('storage', function(e) {
        if (e.key === 'sama-crm-theme') {
            document.body.classList.toggle('theme-light', e.newValue === 'light');
            applyTheme();
            if (currentGeocodedData) renderSVGMap(currentGeocodedData);
        }
    });

    fetchAnalytics();
})();