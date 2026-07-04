/**
 * SAMA Analytics Bridge — punto de entrada único para datos de charts.
 * Todos los renderizadores reciben la misma estructura de datos.
 */
(function() {
    'use strict';

    window.SAMACharts = window.SAMACharts || {};

    var tenantSlug = window.SAMA ? window.SAMA.getTenantSlug() : '';
    var currentDays = 30;
    var currentOffset = 0;
    var currentSource = '';

    function setDays(n) { currentDays = n; currentOffset = 0; }
    function setOffset(n) { currentOffset = n; }
    function setSource(s) { currentSource = s; }
    function getParams() { return { days: currentDays, offset: currentOffset, source: currentSource }; }
    function getTenantSlug() { return tenantSlug; }

    function fetch(url, opts) {
        opts = opts || {};
        opts.headers = opts.headers || {};
        opts.headers['X-CSRFToken'] = window.SAMA ? window.SAMA.getCookie('csrftoken') : '';
        return window.fetch(url, opts);
    }

    function loadCharts() {
        var params = getParams();
        var since = params.days > 0
            ? new Date(Date.now() - (params.days + params.offset * params.days) * 86400000).toISOString().split('T')[0]
            : '';
        var url = '/api/crm/tenants/' + tenantSlug + '/analytics/?days=' + params.days + '&offset=' + params.offset + '&source=' + encodeURIComponent(params.source);
        if (since) url += '&since=' + since;

        fetch(url).then(function(r) { return r.ok ? r.json() : null; }).then(function(data) {
            if (!data) return;

            if (window.SAMACharts.Stats) {
                window.SAMACharts.Stats.render(data.summary || {});
            }
            if (window.SAMACharts.GoalCards) {
                window.SAMACharts.GoalCards.render(
                    data.kpi_targets || [],
                    data.current_period_label || ''
                );
            }
            if (window.SAMACharts.Map) {
                window.SAMACharts.Map.render(
                    data.leads_by_region || [],
                    data.leads_geocoded || []
                );
            }
            if (window.SAMACharts.RegionTable) {
                window.SAMACharts.RegionTable.render(data.leads_geocoded || []);
            }
            if (window.SAMACharts.Funnel) {
                window.SAMACharts.Funnel.render(
                    data.funnel || [],
                    data.kpi_targets || [],
                    data.summary || {}
                );
            }
            if (window.SAMACharts.SourceMix) {
                window.SAMACharts.SourceMix.render(data.leads_by_source_monthly || []);
            }
            if (window.SAMACharts.Timeline) {
                window.SAMACharts.Timeline.render(
                    data.leads_by_day || [],
                    data.leads_by_stage_won || [],
                    data.leads_by_stage_lost || [],
                    data.quotes_sent || [],
                    data.leads_by_stage || {},
                    (data.pipeline_stages || []).map(function(s) { return s.name || s; }),
                    data.kpi_targets || []
                );
            }

            window.SAMACharts._data = data;
            window.dispatchEvent(new CustomEvent('charts-loaded', { detail: data }));
        }).catch(function(e) { console.error('[SAMACharts] load error:', e); });
    }

    function refresh() { loadCharts(); }

    window.SAMACharts = {
        setDays: setDays,
        setOffset: setOffset,
        setSource: setSource,
        getParams: getParams,
        getTenantSlug: getTenantSlug,
        fetch: fetch,
        load: loadCharts,
        refresh: refresh,
        _data: null
    };
})();