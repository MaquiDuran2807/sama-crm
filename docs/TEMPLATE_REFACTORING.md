# Refactorización de Templates CRM

## Resumen

Se han separado los estilos CSS y scripts JavaScript en archivos independientes, siguiendo la arquitectura global/específico:

- **Global**: Aplican a todas las páginas (theme, layout base)
- **Específico**: Solo a una página particular

## Estructura de Archivos Estáticos

```
crm/static/crm/
├── css/
│   ├── base_layout.css    (GLOBAL - header, footer, botones, modals, main container)
│   ├── themes.css         (GLOBAL - solo variables CSS)
│   ├── dashboard.css      (ESPECÍFICO - kanban, stats, search)
│   ├── analytics.css      (ESPECÍFICO - analíticas)
│   ├── lead_detail.css   (ESPECÍFICO - detalle de lead)
│   └── trash.css         (ESPECÍFICO - papelera)
└── js/
    ├── theme.js          (GLOBAL - theme toggle, helpers: getCookie, getTenantSlug)
    ├── dashboard.js      (ESPECÍFICO - drag & drop, search, modals del kanban)
    ├── analytics.js     (ESPECÍFICO - gráficos de analíticas)
    ├── lead_detail.js   (ESPECÍFICO - detalle de lead)
    └── trash.js         (ESPECÍFICO - restaurar leads)
```

## Jerarquía de Carga

### CSS (orden en base.html)
1. `themes.css` - Variables CSS globales (tema oscuro/claro)
2. `base_layout.css` - Estilos globales (header, footer, botones, modals)
3. Cada página añade su CSS específico

### JS (orden en base.html)
1. Bootstrap JS (cdn)
2. `theme.js` - Funciones globales y theme toggle
3. Cada página añade su JS específico

## Carga por Página

| Página | CSS | JS |
|--------|-----|-----|
| base.html | themes.css + base_layout.css | theme.js |
| dashboard.html | + dashboard.css | + dashboard.js |
| analytics.html | + dashboard.css + analytics.css | + analytics.js |
| lead_detail.html | + dashboard.css + lead_detail.css | + dashboard.js + lead_detail.js |
| trash.html | + dashboard.css + trash.css | + trash.js |

## theme.js - Funciones Globales

Expone el objeto `SAMA` con helpers disponibles para todos los scripts:

```javascript
SAMA.getCookie(name)      // Obtiene cookie por nombre
SAMA.getTenantSlug()     // Obtiene tenant slug del body
```

También inicializa el theme toggle al cargar la página.

## Templates Actualizados

### base.html
Carga el theme toggle (botón) y los scripts CSS/JS globales.

### dashboard.html
- stats-row (tarjetas de métricas)
- kanban-container (columnas y tarjetas)
- search-container (búsqueda)
- Modals (noteModal, reopenModal, errorRestoreModal, recompraModal)

### analytics.html
- filter-bar (filtros de fecha y fuente)
- summary-cards (tarjetas de resumen)
- charts-row (gráficos embudo y fuente)
- timeline-chart (línea de tiempo)

### lead_detail.html
- cardx (estilos de tarjetas)
- timeline-item (actividad)
- trace-bar (trazabilidad)
- Modals (activityModal, deleteLeadModal)

### trash.html
- trash-page (contenedor principal)
- trash-list / trash-item (lista de leads eliminados)
- toast (notificaciones)

## Tests

Todos los 37 tests del CRM pasan correctamente:

```bash
pytest crm/tests/ -v
# ========================= 37 passed in 17.57s =========================
```

## Beneficios

1. **Mantenibilidad**: CSS y JS organizados por alcance (global vs específico)
2. **Caché**: Archivos independientes pueden ser cacheados por el navegador
3. **Reutilización**: `SAMA` namespace con helpers disponibles globalmente
4. **Separación de responsabilidades**: theme.js no depende de la página
5. **Legibilidad**: Templates HTML más limpios

## Notas

- Los archivos CSS usan variables CSS definidas en `themes.css`
- Las librerías externas (Chart.js, Bootstrap) siguen siendo cargadas desde CDN
- El theme se aplica al `<body>` con la clase `theme-light`
- Los archivos específicos verifican la existencia de elementos antes de inicializar