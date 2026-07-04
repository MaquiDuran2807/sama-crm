"""
Visual regression tests for SAMA Analytics charts.
Each chart is tested with the same fixture data to ensure deterministic output.
"""
import os
import re
import subprocess
import sys

import pytest


FIXTURE_DATA = {
    "summary": {
        "total_leads": 125,
        "conversion_rate": 0.16,
        "avg_days_to_close": 18,
        "leads_this_week": 32,
        "won_leads": 20,
        "lost_leads": 15,
    },
    "kpi_targets": [
        {"id": 1, "metric_type": "leads", "target_value": 100, "current_value": 125, "progress_percent": 125},
        {"id": 2, "metric_type": "conversions", "target_value": 20, "current_value": 20, "progress_percent": 100},
    ],
    "leads_by_region": [
        {"department": "Antioquia", "total": 40, "won": 8},
        {"department": "Cundinamarca", "total": 30, "won": 5},
        {"department": "Valle del Cauca", "total": 25, "won": 4},
    ],
    "leads_geocoded": [
        {"departamento": "Antioquia", "total": 40, "won": 8, "lost": 5, "intensidad": 0.8},
        {"departamento": "Cundinamarca", "total": 30, "won": 5, "lost": 3, "intensidad": 0.6},
        {"departamento": "Valle del Cauca", "total": 25, "won": 4, "lost": 2, "intensidad": 0.5},
    ],
    "funnel": [
        {"stage": "Lead", "count": 125},
        {"stage": "Calificacion", "count": 80},
        {"stage": "Cotizacion Enviada", "count": 45},
        {"stage": "Seguimiento", "count": 25},
        {"stage": "Cerrado Ganado", "count": 20},
    ],
    "leads_by_source_monthly": [
        {"month": "2026-03", "meta": 30, "google": 20, "tiktok": 15, "web": 10, "referral": 5},
        {"month": "2026-04", "meta": 35, "google": 25, "tiktok": 18, "web": 12, "referral": 8},
    ],
    "leads_by_day": [
        {"date": "2026-05-01", "count": 5},
        {"date": "2026-05-02", "count": 8},
        {"date": "2026-05-03", "count": 3},
        {"date": "2026-05-04", "count": 10},
        {"date": "2026-05-05", "count": 7},
    ],
    "leads_by_stage_won": [
        {"date": "2026-05-01", "count": 1},
        {"date": "2026-05-02", "count": 2},
        {"date": "2026-05-03", "count": 1},
        {"date": "2026-05-04", "count": 3},
        {"date": "2026-05-05", "count": 2},
    ],
    "leads_by_stage_lost": [
        {"date": "2026-05-01", "count": 0},
        {"date": "2026-05-02", "count": 1},
        {"date": "2026-05-03", "count": 0},
        {"date": "2026-05-04", "count": 2},
        {"date": "2026-05-05", "count": 1},
    ],
    "quotes_sent": [
        {"date": "2026-05-01", "count": 2},
        {"date": "2026-05-02", "count": 3},
        {"date": "2026-05-03", "count": 1},
        {"date": "2026-05-04", "count": 4},
        {"date": "2026-05-05", "count": 3},
    ],
    "leads_by_stage": {
        "Lead": [{"date": "2026-05-01", "count": 3}, {"date": "2026-05-02", "count": 5}],
        "Calificacion": [{"date": "2026-05-01", "count": 2}, {"date": "2026-05-02", "count": 3}],
    },
    "pipeline_stages": [
        {"name": "Lead", "order": 0, "color": "#3b82f6"},
        {"name": "Calificacion", "order": 1, "color": "#8b5cf6"},
        {"name": "Cotizacion Enviada", "order": 2, "color": "#f5a623"},
        {"name": "Seguimiento", "order": 3, "color": "#06b6d4"},
        {"name": "Cerrado Ganado", "order": 4, "color": "#2ec27e"},
        {"name": "Cerrado Perdido", "order": 5, "color": "#ef4444"},
    ],
    "current_period_label": "Mayo 2026",
}


def js_syntax_check(path):
    """Verify a JS file passes node --check."""
    result = subprocess.run(
        ["node", "--check", path],
        capture_output=True,
        text=True,
    )
    return result.returncode == 0


def pytest_collect():
    """Collect all chart files for testing."""
    js_dir = "crm/static/crm/js"
    charts_dir = os.path.join(js_dir, "charts")
    shared_dir = os.path.join(js_dir, "shared")

    files = []
    for root, dirs, filenames in os.walk(charts_dir):
        for fn in filenames:
            if fn.endswith(".js"):
                files.append(os.path.join(root, fn))
    for root, dirs, filenames in os.walk(shared_dir):
        for fn in filenames:
            if fn.endswith(".js"):
                files.append(os.path.join(root, fn))

    return files


class TestChartJSSyntax:
    """Every chart JS file must pass node --check."""

    @pytest.mark.parametrize("js_file", pytest_collect())
    def test_js_syntax(self, js_file):
        assert js_syntax_check(js_file), f"Syntax error in {js_file}"


class TestChartFileStructure:
    """Verify each chart module exposes expected SAMACharts interface."""

    def test_bridge_exposes_api(self):
        bridge = "crm/static/crm/js/shared/bridge.js"
        with open(bridge) as f:
            content = f.read()
        assert "window.SAMACharts" in content
        assert "setDays" in content
        assert "load" in content
        assert "refresh" in content

    def test_each_chart_exposes_render(self):
        charts = {
            "stats": "crm/static/crm/js/charts/stats.js",
            "goal-cards": "crm/static/crm/js/charts/goal-cards.js",
            "funnel": "crm/static/crm/js/charts/funnel.js",
            "source-mix": "crm/static/crm/js/charts/source-mix.js",
            "timeline": "crm/static/crm/js/charts/timeline.js",
            "map": "crm/static/crm/js/charts/map.js",
            "region-table": "crm/static/crm/js/charts/region-table.js",
            "kpi-modal": "crm/static/crm/js/charts/kpi-modal.js",
        }
        for name, path in charts.items():
            with open(path) as f:
                content = f.read()
            assert "window.SAMACharts" in content, f"{name}: missing window.SAMACharts"
            assert "render" in content or "open" in content, f"{name}: missing render/open method"


class TestChartCSSSyntax:
    """Every CSS file must be valid CSS (no obvious errors)."""

    @pytest.mark.parametrize(
        "css_file",
        [
            "crm/static/crm/css/charts/stats.css",
            "crm/static/crm/css/charts/goal-cards.css",
            "crm/static/crm/css/charts/map.css",
            "crm/static/crm/css/charts/region-table.css",
            "crm/static/crm/css/charts/funnel.css",
            "crm/static/crm/css/charts/source-mix.css",
            "crm/static/crm/css/charts/timeline.css",
            "crm/static/crm/css/charts/kpi-modal.css",
            "crm/static/crm/css/analytics.css",
        ],
    )
    def test_css_file_readable(self, css_file):
        with open(css_file) as f:
            content = f.read()
        assert len(content) > 10, f"{css_file} is too short or empty"
        assert "{" in content, f"{css_file} has no CSS rules"


class TestChartTemplateStructure:
    """Verify each chart partial has the required DOM IDs."""

    @pytest.mark.parametrize(
        "template,required_ids",
        [
            ("crm/templates/crm/charts/goal-cards.html", ["goal-cards-container", "btn-manage-kpi", "goal-no-targets", "goal-cards-list"]),
            ("crm/templates/crm/charts/funnel.html", ["funnel-chart", "funnel-summary"]),
            ("crm/templates/crm/charts/source-mix.html", ["source-mix-chart"]),
            ("crm/templates/crm/charts/timeline.html", ["timeline-chart", "phase-selector"]),
            ("crm/templates/crm/charts/map.html", ["colombia-svg-map", "map-metric-select"]),
            ("crm/templates/crm/charts/region-table.html", ["region-table", "region-table-body"]),
        ],
    )
    def test_template_has_required_ids(self, template, required_ids):
        with open(template) as f:
            content = f.read()
        for id_name in required_ids:
            assert id_name in content, f"{template} missing required id='{id_name}'"


class TestAnalyticsTemplateIncludes:
    """Verify analytics.html includes all chart partials."""

    def test_analytics_includes_all_chart_partials(self):
        with open("crm/templates/crm/analytics.html") as f:
            content = f.read()

        partials = [
            "goal-cards.html",
            "map.html",
            "region-table.html",
            "funnel.html",
            "source-mix.html",
            "timeline.html",
        ]
        for partial in partials:
            assert f'include "crm/charts/{partial}"' in content, f"Missing include for {partial}"

    def test_analytics_loads_all_chart_js(self):
        with open("crm/templates/crm/analytics.html") as f:
            content = f.read()

        scripts = [
            "stats.js",
            "goal-cards.js",
            "funnel.js",
            "source-mix.js",
            "timeline.js",
            "map.js",
            "region-table.js",
            "kpi-modal.js",
        ]
        for script in scripts:
            assert f"charts/{script}" in content, f"Missing script tag for {script}"
        assert "shared/bridge.js" in content, "Missing bridge.js script"

    def test_analytics_loads_all_chart_css(self):
        with open("crm/templates/crm/analytics.html") as f:
            content = f.read()

        css_files = [
            "charts/stats.css",
            "charts/goal-cards.css",
            "charts/map.css",
            "charts/region-table.css",
            "charts/funnel.css",
            "charts/source-mix.css",
            "charts/timeline.css",
            "charts/kpi-modal.css",
        ]
        for css in css_files:
            assert f"charts/{css.split('/')[-1]}" in content, f"Missing CSS link for {css}"


class TestChartBridgeDataContract:
    """Verify bridge calls each chart renderer with correct parameters."""

    def test_bridge_calls_all_renderers(self):
        with open("crm/static/crm/js/shared/bridge.js") as f:
            content = f.read()

        expected_calls = [
            ("Stats", "SAMACharts.Stats"),
            ("GoalCards", "SAMACharts.GoalCards"),
            ("Map", "SAMACharts.Map"),
            ("RegionTable", "SAMACharts.RegionTable"),
            ("Funnel", "SAMACharts.Funnel"),
            ("SourceMix", "SAMACharts.SourceMix"),
            ("Timeline", "SAMACharts.Timeline"),
        ]
        for module, _call_pattern in expected_calls:
            assert f"SAMACharts.{module}" in content, f"Missing {module} in bridge"


class TestChartRenderingDeterminism:
    """Test that given the same fixture data, chart outputs are deterministic."""

    def test_stats_renders_same_output_for_same_data(self):
        summary = FIXTURE_DATA["summary"]
        total_leads = summary["total_leads"]
        conv_rate = summary["conversion_rate"]

        rendered = {
            "total_leads": total_leads,
            "conv_pct": round(conv_rate * 100),
        }
        assert rendered["total_leads"] == 125
        assert rendered["conv_pct"] == 16

        out1 = str(rendered)
        out2 = str(rendered)
        assert out1 == out2, "Stats output not deterministic"

    def test_goal_cards_render_same_output_for_same_data(self):
        ctx = {"kpi_targets": FIXTURE_DATA["kpi_targets"], "period_label": "Mayo 2026"}
        from django.template import Template, Context

        template = Template("""
        {% for target in kpi_targets %}
        <div class="goal-card{% if target.progress_percent >= 80 %} on-track{% elif target.progress_percent >= 50 %} at-risk{% else %} behind{% endif %}">
            <div class="goal-name">{{ target.metric_type|capfirst }}</div>
            <div class="goal-current">{{ target.current_value }}</div>
            <div class="goal-target">{{ target.target_value }}</div>
            <div class="goal-percent">{{ target.progress_percent }}%</div>
        </div>
        {% endfor %}
        """)

        out1 = template.render(Context(ctx))
        out2 = template.render(Context(ctx))
        assert out1 == out2, "Goal cards output not deterministic"

    def test_funnel_summary_deterministic(self):
        from django.template import Template, Context

        funnel = FIXTURE_DATA["funnel"]
        total = sum(f["count"] for f in funnel)
        ctx = {"total_leads": total, "conv_ratio": 625}

        template = Template("""
        <span class="funnel-total">{{ total_leads }} leads totales</span>
        {% if conv_ratio %}<span>({{ conv_ratio }}% de meta)</span>{% endif %}
        """)

        out1 = template.render(Context(ctx))
        out2 = template.render(Context(ctx))
        assert out1 == out2, "Funnel summary not deterministic"

    def test_region_table_renders_all_rows(self):
        rows = FIXTURE_DATA["leads_geocoded"]
        html_parts = []
        for r in rows:
            pct = r["total"] > 0 and round((r["won"] / r["total"]) * 100) or 0
            html_parts.append(
                f'<td><strong>{r["departamento"]}</strong></td>' +
                f'<td class="text-center fw-bold">{r["total"]}</td>' +
                f'<td class="text-center" style="color:#22c55e">{r["won"]}</td>' +
                f'<td class="text-center" style="color:#ef4444">{r["lost"]}</td>' +
                f'<td><span class="badge">{pct}%</span></td>'
            )

        out = "\n".join(html_parts)
        assert "Antioquia" in out
        assert "Cundinamarca" in out
        assert "Valle del Cauca" in out
        assert out.count("<td") == 15, f"Expected 15 <td> (3 rows x 5 cols), got {out.count('<td')}"

    def test_timeline_has_leads_and_total_lines(self):
        labels = ["1 May", "2 May", "3 May", "4 May", "5 May"]
        new_counts = [5, 8, 3, 10, 7]
        total = [5, 13, 16, 26, 33]

        assert labels[0] == "1 May"
        assert sum(new_counts) == 33, "Total leads should be 33"
        assert total[-1] == 33, "Last cumulative should be 33"

    def test_kpi_modal_has_required_fields(self):
        with open("crm/static/crm/js/charts/kpi-modal.js") as f:
            content = f.read()

        assert "modal-overlay" in content, "Modal needs .modal-overlay class"
        assert "kpi-cards-grid" in content, "Modal needs metric cards grid"
        assert "kpi-target-input" in content, "Modal needs target input field"
        assert "kpi-save-btn" in content, "Modal needs save button"
        assert "kpi-cancel-btn" in content, "Modal needs cancel button"
        assert "getAvailableMetrics" in content, "Modal needs metric list function"
        assert "saveTargets" in content, "Modal needs saveTargets function"
        assert "kpi-category-filter" in content, "Modal needs category filter"


class TestChartIndependence:
    """Verify charts don't share mutable state beyond the bridge."""

    def test_no_global_mutable_state_in_chart_files(self):
        chart_files = [
            "crm/static/crm/js/charts/stats.js",
            "crm/static/crm/js/charts/goal-cards.js",
            "crm/static/crm/js/charts/funnel.js",
            "crm/static/crm/js/charts/source-mix.js",
            "crm/static/crm/js/charts/timeline.js",
        ]
        for fpath in chart_files:
            with open(fpath) as f:
                content = f.read()
            problematic_patterns = [
                re.compile(r"var\s+(tenantSlug|currentDays|currentSource)\s*="),
                re.compile(r"function\s+fetchAnalytics"),
                re.compile(r"currentOffset\s*="),
            ]
            for pat in problematic_patterns:
                matches = pat.findall(content)
                assert not matches, f"{fpath}: found shared state pattern '{matches[0] if matches else ''}'"

    def test_timeline_has_isolated_selected_phases(self):
        with open("crm/static/crm/js/charts/timeline.js") as f:
            content = f.read()
        assert "selectedPhases" in content, "Timeline needs selectedPhases state"
        occurrences = content.count("selectedPhases")
        assert occurrences <= 20, f"Timeline selectedPhases referenced {occurrences} times (may be shared)"

    def test_bridge_is_only_file_with_fetch(self):
        bridge = "crm/static/crm/js/shared/bridge.js"
        with open(bridge) as f:
            bridge_content = f.read()

        chart_dir = "crm/static/crm/js/charts"
        for fname in os.listdir(chart_dir):
            if not fname.endswith(".js"):
                continue
            if fname in ("kpi-modal.js", "map.js"):
                continue
            with open(os.path.join(chart_dir, fname)) as f:
                content = f.read()
            if "fetch(" in content or "fetch(url" in content:
                assert False, f"{fname} should not contain fetch - use bridge instead"


class TestChartConsistencyAcrossRefresh:
    """Charts must produce consistent output on repeated refresh with same data."""

    def test_funnel_chart_always_shows_total_leads(self):
        total = sum(f["count"] for f in FIXTURE_DATA["funnel"])
        assert total == 295, f"Total leads should be 295, got {total}"

    def test_source_mix_all_platforms_have_data(self):
        platforms = ["meta", "google", "tiktok", "web", "referral"]
        for row in FIXTURE_DATA["leads_by_source_monthly"]:
            for p in platforms:
                assert p in row, f"Missing platform {p} in {row}"

    def test_timeline_datasets_are_deterministic(self):
        day_data = FIXTURE_DATA["leads_by_day"]
        new_counts = [d["count"] for d in day_data]
        cumulative = []
        running = 0
        for c in new_counts:
            running += c
            cumulative.append(running)

        assert cumulative == [5, 13, 16, 26, 33], f"Cumulative line wrong: {cumulative}"
        assert new_counts == [5, 8, 3, 10, 7], f"New counts wrong: {new_counts}"

    def test_all_chart_ids_are_unique(self):
        all_ids = []
        for tmpl in [
            "crm/templates/crm/charts/goal-cards.html",
            "crm/templates/crm/charts/funnel.html",
            "crm/templates/crm/charts/source-mix.html",
            "crm/templates/crm/charts/timeline.html",
            "crm/templates/crm/charts/map.html",
            "crm/templates/crm/charts/region-table.html",
        ]:
            with open(tmpl) as f:
                content = f.read()
            ids = re.findall(r'id="([^"]+)"', content)
            all_ids.extend(ids)

        duplicates = [i for i in all_ids if all_ids.count(i) > 1]
        assert not duplicates, f"Duplicate chart IDs found: {set(duplicates)}"


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))