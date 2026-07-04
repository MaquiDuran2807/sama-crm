/**
 * KPI Modal — overlay for managing KPI targets.
 * Shows all available metric types as selectable cards with period picker.
 * Dependencies: bridge.js (SAMACharts global)
 */
(function() {
    'use strict';

    var modalEl = null;

    var CATEGORIES = {
        volume: { label: 'Volumen', icon: 'bi-bar-chart', color: '#3b82f6' },
        conversion: { label: 'Conversion', icon: 'bi-graph-up', color: '#8b5cf6' },
        revenue: { label: 'Ingresos', icon: 'bi-wallet2', color: '#22c55e' },
        efficiency: { label: 'Eficiencia', icon: 'bi-clock', color: '#f5a623' },
    };

    var PERIODS = [
        { value: 'daily', label: 'Diario' },
        { value: 'weekly', label: 'Semanal' },
        { value: 'monthly', label: 'Mensual' },
        { value: 'quarterly', label: 'Trimestral' },
    ];

    var activeCategory = 'all';

    function getCSRFToken() {
        return window.SAMA && window.SAMA.getCookie ? window.SAMA.getCookie('csrftoken') : '';
    }

    function getTenantSlug() {
        return window.SAMACharts ? window.SAMACharts.getTenantSlug() : '';
    }

    function getExistingSlugs(existingTargets) {
        var slugs = {};
        if (existingTargets) {
            existingTargets.forEach(function(t) { slugs[t.metric_type] = t; });
        }
        return slugs;
    }

    function getPeriodRange() {
        var start = new Date();
        start.setDate(1);
        start.setHours(0, 0, 0, 0);
        var end = new Date(start);
        end.setMonth(end.getMonth() + 1);
        end.setDate(end.getDate() - 1);
        end.setHours(23, 59, 59, 999);
        return { start: start.toISOString(), end: end.toISOString() };
    }

    function buildCategoryFilter() {
        var html = '<div class="kpi-category-filter">';
        html += '<button class="kpi-cat-btn active" data-cat="all">Todos</button>';
        Object.keys(CATEGORIES).forEach(function(cat) {
            var info = CATEGORIES[cat];
            html += '<button class="kpi-cat-btn" data-cat="' + cat + '">' +
                '<i class="' + info.icon + '"></i> ' + info.label + '</button>';
        });
        html += '</div>';
        return html;
    }

    function buildMetricCards(metrics, existing) {
        var existingSlugs = getExistingSlugs(existing);
        var html = '<div class="kpi-cards-grid">';
        metrics.forEach(function(m) {
            var existingTarget = existingSlugs[m.slug];
            var catInfo = CATEGORIES[m.category] || {};
            html += '<div class="kpi-metric-card' + (existingTarget ? ' active' : '') + '" data-slug="' + m.slug + '" data-cat="' + m.category + '">' +
                '<div class="kpi-metric-card-header">' +
                    '<span class="kpi-metric-icon" style="background:' + m.color + '1a;color:' + m.color + '">' +
                        '<i class="' + m.icon + '"></i>' +
                    '</span>' +
                    '<span class="kpi-metric-check"><i class="bi bi-check-lg"></i></span>' +
                '</div>' +
                '<div class="kpi-metric-name">' + m.name + '</div>' +
                '<div class="kpi-metric-desc">' + m.description + '</div>' +
                '<div class="kpi-metric-target-row">' +
                    '<span class="kpi-metric-unit">' + m.unit + '</span>' +
                    '<input type="number" class="kpi-target-input" ' +
                        'placeholder="Meta" min="0" step="1" ' +
                        'value="' + (existingTarget ? existingTarget.target_value : '') + '">' +
                '</div>' +
                '<div class="kpi-metric-existing">' +
                    (existingTarget
                        ? '<span class="kpi-badge-active">Activa</span>'
                        : '<span class="kpi-badge-inactive">Sin meta</span>') +
                '</div>' +
            '</div>';
        });
        html += '</div>';
        return html;
    }

    function buildPeriodSelect() {
        var html = '<div class="kpi-period-row">' +
            '<label class="kpi-period-label">Periodo:</label>';
        PERIODS.forEach(function(p) {
            html += '<label class="kpi-period-option">' +
                '<input type="radio" name="kpi-period" value="' + p.value + '" ' +
                    (p.value === 'monthly' ? 'checked ' : '') + '> ' + p.label +
            '</label>';
        });
        html += '</div>';
        return html;
    }

    function open(existingTargets) {
        if (modalEl) modalEl.remove();
        modalEl = document.createElement('div');
        modalEl.className = 'modal-overlay';
        modalEl.id = 'kpi-modal';

        modalEl.innerHTML =
            '<div class="modal-content kpi-modal-large">' +
                '<div class="modal-header">' +
                    '<h3><i class="bi bi-bullseye"></i> Configurar Metas KPI</h3>' +
                    '<div class="kpi-modal-actions-header">' +
                        '<button class="kpi-reset-btn" id="kpi-reset-btn"><i class="bi bi-arrow-counterclockwise"></i> Limpiar</button>' +
                        '<button class="modal-close" id="kpi-modal-close">&times;</button>' +
                    '</div>' +
                '</div>' +
                '<div class="modal-body">' +
                    '<div class="kpi-section-label">Selecciona los metricos que quieres rastrear y define su objetivo</div>' +
                    buildCategoryFilter() +
                    '<div class="kpi-metrics-container" id="kpi-metrics-container"></div>' +
                    buildPeriodSelect() +
                    '<div class="kpi-modal-actions">' +
                        '<button class="btn-primary" id="kpi-save-btn">' +
                            '<i class="bi bi-check-lg"></i> Guardar todas las metas' +
                        '</button>' +
                        '<button class="btn-secondary" id="kpi-cancel-btn">Cancelar</button>' +
                    '</div>' +
                '</div>' +
            '</div>';

        document.body.appendChild(modalEl);
        modalEl.classList.add('show');

        document.getElementById('kpi-modal-close').addEventListener('click', close);
        document.getElementById('kpi-cancel-btn').addEventListener('click', close);
        modalEl.addEventListener('click', function(e) { if (e.target === modalEl) close(); });

        setupCategoryFilter(existingTargets);
        renderMetricCards(existingTargets);

        document.getElementById('kpi-save-btn').addEventListener('click', function() { saveTargets(existingTargets); });
        document.getElementById('kpi-reset-btn').addEventListener('click', function() { renderMetricCards(existingTargets); });
    }

    function setupCategoryFilter(existingTargets) {
        document.querySelectorAll('.kpi-cat-btn').forEach(function(btn) {
            btn.addEventListener('click', function() {
                document.querySelectorAll('.kpi-cat-btn').forEach(function(b) { b.classList.remove('active'); });
                btn.classList.add('active');
                activeCategory = btn.getAttribute('data-cat');
                filterMetricCards();
            });
        });
    }

    function filterMetricCards() {
        document.querySelectorAll('.kpi-metric-card').forEach(function(card) {
            if (activeCategory === 'all' || card.getAttribute('data-cat') === activeCategory) {
                card.style.display = '';
            } else {
                card.style.display = 'none';
            }
        });
    }

    function renderMetricCards(existingTargets) {
        var container = document.getElementById('kpi-metrics-container');
        if (!container) return;
        container.innerHTML = buildMetricCards(getAvailableMetrics(), existingTargets);
        setupCardInteractions();
        filterMetricCards();
    }

    function setupCardInteractions() {
        document.querySelectorAll('.kpi-metric-card').forEach(function(card) {
            card.addEventListener('click', function() {
                card.classList.toggle('active');
                var input = card.querySelector('.kpi-target-input');
                if (card.classList.contains('active') && input && !input.value) {
                    input.focus();
                }
            });
            var input = card.querySelector('.kpi-target-input');
            if (input) {
                input.addEventListener('click', function(e) { e.stopPropagation(); });
                input.addEventListener('input', function(e) {
                    if (input.value && input.value > 0) {
                        card.classList.add('active');
                    }
                });
            }
        });
    }

    function getAvailableMetrics() {
        return [
            { slug: 'leads', name: 'Leads totales', description: 'Total de nuevos leads captados', unit: 'leads', icon: 'bi-people', color: '#3b82f6', category: 'volume' },
            { slug: 'conversions', name: 'Conversiones', description: 'Leads cerrados como ganados', unit: 'leads', icon: 'bi-trophy', color: '#2ec27e', category: 'conversion' },
            { slug: 'conversion_rate', name: 'Tasa de conversion', description: 'Porcentaje de leads convertidos', unit: '%', icon: 'bi-graph-up-arrow', color: '#8b5cf6', category: 'conversion' },
            { slug: 'avg_days', name: 'Dias promedio cierre', description: 'Tiempo promedio para cerrar un lead', unit: 'dias', icon: 'bi-clock', color: '#f5a623', category: 'efficiency' },
            { slug: 'avg_deal_value', name: 'Valor promedio negocio', description: 'Valor promedio por negocio cerrado', unit: 'COP', icon: 'bi-currency-dollar', color: '#06b6d4', category: 'revenue' },
            { slug: 'revenue', name: 'Ingresos totales', description: 'Suma de valores de negocios cerrados', unit: 'COP', icon: 'bi-wallet2', color: '#22c55e', category: 'revenue' },
            { slug: 'quotes_sent', name: 'Cotizaciones enviadas', description: 'Total de cotizaciones enviadas', unit: 'cotiz.', icon: 'bi-file-earmark-text', color: '#f59e0b', category: 'volume' },
            { slug: 'quotes_accepted', name: 'Cotizaciones aceptadas', description: 'Cotizaciones aceptadas por clientes', unit: 'cotiz.', icon: 'bi-check-square', color: '#10b981', category: 'conversion' },
            { slug: 'leads_per_day', name: 'Leads por dia', description: 'Promedio de leads por dia', unit: 'leads/dia', icon: 'bi-calendar-day', color: '#6366f1', category: 'efficiency' },
            { slug: 'pipeline_value', name: 'Valor en pipeline', description: 'Suma de valores de leads activos', unit: 'COP', icon: 'bi-stack', color: '#0ea5e9', category: 'revenue' },
            { slug: 'retention_rate', name: 'Tasa de retencion', description: 'Porcentaje de clientes que repiten', unit: '%', icon: 'bi-person-check', color: '#a855f7', category: 'conversion' },
            { slug: 'follow_up_rate', name: 'Tasa de seguimiento', description: 'Porcentaje de leads con seguimiento', unit: '%', icon: 'bi-chat-left-text', color: '#ec4899', category: 'efficiency' },
            { slug: 'new_contacts', name: 'Contactos nuevos', description: 'Total de contactos nuevos creados', unit: 'contactos', icon: 'bi-person-plus', color: '#14b8a6', category: 'volume' },
            { slug: 'emails_sent', name: 'Emails enviados', description: 'Campanas de email enviadas', unit: 'emails', icon: 'bi-envelope', color: '#64748b', category: 'volume' },
            { slug: 'calls_made', name: 'Llamadas realizadas', description: 'Total de llamadas telefonicas', unit: 'llamadas', icon: 'bi-telephone', color: '#0d9488', category: 'volume' },
            { slug: 'meetings_scheduled', name: 'Reuniones agendadas', description: 'Reuniones programadas', unit: 'reuniones', icon: 'bi-calendar-event', color: '#7c3aed', category: 'volume' },
            { slug: 'cost_per_lead', name: 'Costo por lead', description: 'Costo promedio de adquisicion por lead', unit: 'COP', icon: 'bi-cash-stack', color: '#b45309', category: 'efficiency' },
            { slug: 'roi', name: 'Retorno de inversion', description: 'ROI de las campanhas', unit: '%', icon: 'bi-bar-chart', color: '#059669', category: 'revenue' },
        ];
    }

    function close() {
        if (modalEl) {
            modalEl.classList.remove('show');
            setTimeout(function() { if (modalEl) { modalEl.remove(); modalEl = null; } }, 200);
        }
    }

    function saveTargets(existingTargets) {
        var period = document.querySelector('input[name="kpi-period"]:checked');
        if (!period) {
            console.error('[KPI Modal] No period selected');
            return;
        }
        var periodValue = period.value;

        var existingSlugs = getExistingSlugs(existingTargets);
        var csrf = getCSRFToken();
        var slug = getTenantSlug();
        var periodRange = getPeriodRange();
        var saves = [];

        console.log('[KPI Modal] Saving targets:', {
            slug: slug, csrf: csrf ? 'OK' : 'MISSING',
            existing: Object.keys(existingSlugs),
            period: periodValue, periodRange: periodRange
        });

        document.querySelectorAll('.kpi-metric-card.active').forEach(function(card) {
            var metricSlug = card.getAttribute('data-slug');
            var input = card.querySelector('.kpi-target-input');
            var value = parseFloat(input.value) || 0;
            if (value <= 0) {
                console.warn('[KPI Modal] Skipping', metricSlug, '— invalid value:', input.value);
                return;
            }

            var existing = existingSlugs[metricSlug];
            var method = existing ? 'PATCH' : 'POST';
            var url = '/api/crm/tenants/' + slug + '/kpi-targets/' + (existing ? existing.id + '/' : '');

            console.log('[KPI Modal] Saving:', method, url, {metric_type: metricSlug, target_value: value, period_type: periodValue});

            saves.push(
                fetch(url, {
                    method: method,
                    headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrf },
                    body: JSON.stringify({
                        metric_type: metricSlug,
                        target_value: value,
                        period_type: periodValue,
                        is_active: true,
                    })
                }).then(function(r) {
                    console.log('[KPI Modal] Response:', r.status, url);
                    if (!r.ok) return r.json().then(function(e) { console.error('[KPI Modal] API error:', e); throw e; });
                    return r.json();
                })
            );
        });

        document.querySelectorAll('.kpi-metric-card:not(.active)').forEach(function(card) {
            var metricSlug = card.getAttribute('data-slug');
            var existing = existingSlugs[metricSlug];
            if (existing) {
                saves.push(
                    fetch('/api/crm/tenants/' + slug + '/kpi-targets/' + existing.id + '/', {
                        method: 'PATCH',
                        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrf },
                        body: JSON.stringify({ is_active: false })
                    }).then(function(r) {
                        console.log('[KPI Modal] Deactivated:', r.status, metricSlug);
                        if (!r.ok) return r.json().then(function(e) { console.error('[KPI Modal] API error:', e); throw e; });
                        return r.json();
                    })
                );
            }
        });

        if (saves.length === 0) {
            console.warn('[KPI Modal] No active cards selected, closing anyway');
            close();
            return;
        }

        Promise.all(saves)
            .then(function(results) {
                console.log('[KPI Modal] All saves complete:', results.length, 'saved');
                close();
                if (window.SAMACharts) window.SAMACharts.refresh();
            })
            .catch(function(e) {
                console.error('[KPI Modal] Save failed:', e);
            });
    }

            window.SAMACharts = window.SAMACharts || {};
    window.SAMACharts.KPIModal = { open: open, close: close };
})();