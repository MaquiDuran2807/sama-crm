import re

with open('crm/static/crm/js/analytics.js', 'r', encoding='utf-8') as f:
    content = f.read()

patches = [
    # 7: Add dataMax, suggestedMax, cumulative, Meta lineal before visibleDatasets
    ('timelineAllDatasets = datasets.slice();\n\n        var visibleDatasets',
     '''timelineAllDatasets = datasets.slice();

        var dataMax = Math.max.apply(null, newCounts.concat(wonCounts, lostCounts, quoteCounts).filter(function(n) { return !isNaN(n) && n !== null; })) || 0;
        var kpiMax = 0;
        (kpiTargets || []).forEach(function(t) {
            if (t.target_value > 0 && (t.metric_type === 'leads' || t.metric_type === 'conversions')) {
                if (t.target_value > kpiMax) kpiMax = t.target_value;
            }
        });
        var suggestedMax = Math.max(dataMax, kpiMax) * 1.2;
        if (suggestedMax === 0) suggestedMax = 10;

        var cumulativeCounts = [];
        var running = 0;
        newCounts.forEach(function(v) { running += v || 0; cumulativeCounts.push(running); });

        datasets.push({
            label: 'Acumulado',
            data: cumulativeCounts,
            borderColor: '#8b5cf6',
            backgroundColor: 'rgba(139, 92, 246, 0.1)',
            fill: true,
            tension: 0.1,
            pointRadius: 1.5,
            pointBackgroundColor: '#8b5cf6',
            borderWidth: 1.5,
        });

        var leadTarget = null;
        (kpiTargets || []).forEach(function(t) {
            if (t.metric_type === 'leads') leadTarget = t;
        });
        var targetVal = leadTarget ? leadTarget.target_value : 0;
        var targetLineCounts = dayLabels.map(function() { return targetVal; });

        datasets.push({
            label: 'Meta lineal',
            data: targetLineCounts,
            borderColor: '#10b981',
            backgroundColor: 'transparent',
            borderDash: [8, 4],
            fill: false,
            tension: 0,
            pointRadius: 0,
            borderWidth: 1.5,
        });

        var visibleDatasets'''),
    # 8: visibleDatasets filter
    ('datasets.filter(function(ds) { return selectedPhases.has(ds.label); })',
     '''datasets.filter(function(ds) {
                if (ds.label === 'Leads nuevos' || ds.label === 'Acumulado' || ds.label === 'Meta lineal') return true;
                return selectedPhases.has(ds.label);
              })'''),
    # 9: Add suggestedMax to Y scale
    ('suggestedMin: 0,\n                    },\n                },\n            },\n        });\n    }\n\n    function renderPhaseSelector',
     'suggestedMin: 0,\n                        suggestedMax: suggestedMax,\n                    },\n                },\n            },\n        });\n    }\n\n    function renderGoalCards(kpiTargets, periodLabel) {\n        var emptyEl = document.getElementById(\'goal-no-targets\');\n        var listEl = document.getElementById(\'goal-cards-list\');\n        if (!emptyEl || !listEl) return;\n\n        if (!kpiTargets || kpiTargets.length === 0) {\n            emptyEl.style.display = \'flex\';\n            listEl.style.display = \'none\';\n            return;\n        }\n\n        emptyEl.style.display = \'none\';\n        listEl.style.display = \'grid\';\n        listEl.innerHTML = \'\';\n\n        var metricLabels = {\n            leads: \'Leads\',\n            conversions: \'Conversiones\',\n            conversion_rate: \'Tasa conversion\',\n            avg_days: \'Dias promedio cierre\',\n        };\n\n        kpiTargets.forEach(function(target) {\n            var pct = target.progress_percent || 0;\n            var status = pct >= 80 ? \'on-track\' : (pct >= 50 ? \'at-risk\' : \'behind\');\n            var isRate = target.metric_type === \'conversion_rate\';\n            var displayCurrent = isRate ? (target.current_value || 0) + \'%\' : Math.round(target.current_value || 0);\n            var displayTarget = isRate ? (target.target_value || 0) + \'%\' : Math.round(target.target_value || 0);\n            var metricLabel = metricLabels[target.metric_type] || target.metric_type;\n\n            var card = document.createElement(\'div\');\n            card.className = \'goal-card \' + status;\n            card.innerHTML =\n                \'<div class="goal-card-header">\' +\n                    \'<span class="goal-name">\' + (target.name || metricLabel) + \'</span>\' +\n                    \'<span class="goal-period">\' + (periodLabel || \'Mes\') + \'</span>\' +\n                \'</div>\' +\n                \'<div class="goal-numbers">\' +\n                    \'<span class="goal-current">\' + displayCurrent + \'</span>\' +\n                    \'<span class="goal-separator">/</span>\' +\n                    \'<span class="goal-target">\' + displayTarget + \'</span>\' +\n                \'</div>\' +\n                \'<div class="goal-progress-container">\' +\n                    \'<div class="goal-progress-bar-track">\' +\n                        \'<div class="goal-progress-bar-fill" style="width:\' + Math.min(pct, 100) + \'%"></div>\' +\n                    \'</div>\' +\n                    \'<span class="goal-percent">\' + Math.round(pct) + \'%</span>\' +\n                \'</div>\';\n            listEl.appendChild(card);\n        });\n    }\n\n    function renderPhaseSelector'),
]

for old, new in patches:
    if old in content:
        content = content.replace(old, new)
        print(f"OK: {repr(old[:40])}")
    else:
        print(f"MISS: {repr(old[:40])}")

with open('crm/static/crm/js/analytics.js', 'w', encoding='utf-8') as f:
    f.write(content)

print('\nPart 2 done')