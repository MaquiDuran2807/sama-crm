# 📋 MATRIZ DE COBERTURA DE TESTS - Dashboard Kanban

## Leyenda
- ✅ **Cubierto** - Test que valida funcionamiento real
- ⚠️ **Parcial** - Test que solo verifica presencia HTML
- ❌ **No cubierto** - Sin test

---

## 🎯 DRAG & DROP

### Movimiento entre etapas activas
| Caso | BD Update | DOM Update | Sin Refresh | Status |
|---|---|---|---|---|
| Lead → Calificacion | ✅ | ✅ | ✅ | **CUBIERTO** |
| Calificacion → Lead | ✅ | ✅ | ✅ | **CUBIERTO** |
| Forward x3 | ✅ | ✅ | ✅ | **CUBIERTO** |
| Backward | ✅ | ✅ | ✅ | **CUBIERTO** |

### Movimiento a etapa cerrada
| Caso | Modal Aparece | Botones Presentes | Click Funciona | Status |
|---|---|---|---|---|
| Lead → Cerrado | ✅ | ✅ | ✅ | **CUBIERTO** |
| "Fue un error" | ✅ | ✅ | ✅ | **CUBIERTO** |
| "Nueva oportunidad" | ✅ | ✅ | ✅ | **CUBIERTO** |

### Otros casos drag
| Caso | Status | Notas |
|---|---|---|
| Drag con mouse lento | ⚠️ | Teórico, no probado |
| Drag en mobile | ❌ | No soporta touch |
| Drag con teclado (a11y) | ❌ | No existe keyboard handler |

---

## 🔍 FILTROS DE TIEMPO

| Período | Muestra Correcto | Oculta Correcto | Status |
|---|---|---|---|
| Hoy | ✅ | ✅ | **CUBIERTO** |
| Ayer | ⚠️ | ⚠️ | Solo HTML |
| 7 días | ✅ | ✅ | **CUBIERTO** |
| 30 días | ⚠️ | ⚠️ | Solo HTML |
| Este mes | ⚠️ | ⚠️ | Solo HTML |
| Todo | ⚠️ | ⚠️ | Solo HTML (pero es default) |
| Rango custom | ✅ | ✅ | **CUBIERTO** |

**Cobertura Filtros Tiempo: 3/7 = 43%**

---

## 🏷️ FILTROS DE ETAPAS

| Etapa | Oculta Cuando Unchecked | Muestra Cuando Checked | Status |
|---|---|---|---|
| Lead | ✅ | ✅ | **CUBIERTO** |
| Calificacion | ⚠️ | ⚠️ | Solo HTML |
| Cerrado Ganado | ⚠️ | ⚠️ | Solo HTML |

**Cobertura Filtros Etapas: 1/3 = 33%**

---

## 🏢 FILTROS DE FUENTE

| Fuente | Filtra Correcto | Status |
|---|---|---|
| Meta | ⚠️ | Solo HTML |
| Google Ads | ⚠️ | Solo HTML |
| TikTok | ⚠️ | Solo HTML |
| Web | ✅ | **CUBIERTO** |
| Referral | ⚠️ | Solo HTML |

**Cobertura Filtros Fuente: 1/5 = 20%**

---

## 📌 FILTROS DE ETIQUETAS

| Acción | Muestra Tags | Oculta Others | Status |
|---|---|---|---|
| Seleccionar "VIP" | ✅ | ✅ | **CUBIERTO** |
| Múltiples tags | ❌ | ❌ | No probado |
| Desmarcar tag | ⚠️ | ⚠️ | Solo HTML |

**Cobertura Filtros Tags: 1/3 = 33%**

---

## ✓ FILTROS DE ESTADO

| Filtro | Funciona | Status |
|---|---|---|
| "Solo abiertos" toggle | ✅ | **CUBIERTO** |
| Oculta leads cerrados | ✅ | **CUBIERTO** |

**Cobertura Filtros Estado: 2/2 = 100%**

---

## ⏰ FILTROS DE TAREAS

| Filtro | Funciona | Status |
|---|---|---|
| Con tareas pendientes | ✅ | **CUBIERTO** |
| Vencen hoy | ❌ | No probado |
| Mañana | ❌ | No probado |
| Vencidas | ❌ | No probado |
| Sin tareas | ❌ | No probado |

**Cobertura Filtros Tareas: 1/5 = 20%**

---

## 🔎 BÚSQUEDA

| Caso | Funciona | Realtime | Combinado | Status |
|---|---|---|---|---|
| Por nombre | ✅ | ✅ | ⚠️ | **PARCIAL** |
| Por teléfono | ⚠️ | ⚠️ | ❌ | No probado |
| Por producto | ⚠️ | ⚠️ | ❌ | No probado |
| + Filtros | ✅ | - | ✅ | **CUBIERTO** |

**Cobertura Búsqueda: 2/4 = 50%**

---

## 🔧 GESTIÓN DE FILTROS

| Acción | Funciona | Status |
|---|---|---|
| Aplicar filtros | ✅ | **CUBIERTO** |
| Limpiar filtros | ✅ | **CUBIERTO** |
| Sidebar toggle | ⚠️ | Solo HTML |
| Overlay mobile | ⚠️ | Solo HTML |

**Cobertura Gestión: 2/4 = 50%**

---

## 📊 ESTADÍSTICAS GLOBALES

### Por Categoría
| Categoría | Cubierto | Total | % |
|---|---|---|---|
| Drag & Drop | 6 | 6 | **100%** |
| Filtros Tiempo | 3 | 7 | **43%** |
| Filtros Etapas | 1 | 3 | **33%** |
| Filtros Fuente | 1 | 5 | **20%** |
| Filtros Tags | 1 | 3 | **33%** |
| Filtros Estado | 2 | 2 | **100%** |
| Filtros Tareas | 1 | 5 | **20%** |
| Búsqueda | 2 | 4 | **50%** |
| Gestión | 2 | 4 | **50%** |
| **TOTAL** | **19** | **39** | **49%** |

### Resumen por Tipo
| Tipo | Cubierto | Total | % |
|---|---|---|---|
| ✅ Funcional (ActionChains) | 19 | 39 | **49%** |
| ⚠️ HTML-only (fake) | 15 | 39 | **38%** |
| ❌ No cubierto | 5 | 39 | **13%** |

---

## 🎯 PRIORIDADES PARA COMPLETAR

### 🔴 CRÍTICA (Hacer primero)
- [ ] `test_filter_period_30d_hides_old_leads` - Filtro 30 días (muy usado)
- [ ] `test_filter_all_stages_can_be_unchecked` - Todos los filters de etapas
- [ ] `test_search_by_phone` - Búsqueda por teléfono
- [ ] `test_task_filter_overdue` - Tareas vencidas

### 🟡 MEDIA (Hacer segundo)
- [ ] `test_filter_source_all_platforms` - Todas las fuentes
- [ ] `test_filter_multiple_tags` - Multiple tags selection
- [ ] `test_search_by_product` - Búsqueda por producto
- [ ] `test_drag_with_slow_mouse` - Drag lento

### 🟢 BAJA (Opcional)
- [ ] `test_sidebar_mobile_responsive` - Mobile sidebar
- [ ] `test_keyboard_navigation_a11y` - Keyboard accessibility
- [ ] `test_touch_drag` - Touch events

---

## ✅ CHECKLIST DE VALIDACIÓN

Antes de llamar "completo" al testing:

### Drag & Drop
- [x] Drag forward funciona
- [x] Drag backward funciona
- [x] Sin refresh requerido
- [x] Modal de reopen aparece
- [x] Modal buttons funcionan
- [x] Actividades se crean

### Filtros Básicos
- [x] Filtro período "Hoy" funciona
- [x] Filtro período "7d" funciona
- [x] Filtro etapas unchecked oculta
- [x] Filtro "Solo abiertos" funciona

### Búsqueda y Combinaciones
- [x] Búsqueda por nombre realtime
- [x] Búsqueda + filtros juntos
- [x] Limpiar filtros restaura todos

### Por Completar
- [ ] Todos los períodos de tiempo
- [ ] Todos los filtros de fuente
- [ ] Todos los filtros de tareas
- [ ] Búsqueda por teléfono y producto
- [ ] Tests de accesibilidad

---

## 📈 Meta de Cobertura

**Actual:** 49% (19/39 casos)  
**Meta:** 100% (39/39 casos)  
**Progreso:** 19 → 39 tests por crear

**Estimado de tiempo completo:** 2-3 horas más de escritura de tests
