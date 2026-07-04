# 📊 Reporte de Auditoría - Tests del Dashboard CRM

## Fecha: 11 de mayo de 2026
## Estado: Auditoría Completa + Nuevos Tests Creados

---

## 🔴 HALLAZGOS CRÍTICOS INICIALES

### Problema #1: Tests de Selenium NO hacen Drag & Drop Real
**Severidad:** CRÍTICA  
**Ubicación:** `crm/tests/test_ui_selenium.py` (tests 167-347)  
**Problema:** 
- Los tests verifican atributos HTML (`draggable`, `data-stage`, etc.)
- NO usan `ActionChains` para simular drag real
- Verifican presencia de elementos, no comportamiento
- Ejemplo: `test_card_draggable_attribute()` solo valida que `draggable="true"` existe

**Impacto:** 
- ❌ El drag & drop podría estar completamente roto
- ❌ El modal de reopen no se prueba
- ❌ El flujo "Fue un error" / "Nueva oportunidad" NO se valida

---

### Problema #2: Tests de Filtros Solo Verifican HTML
**Severidad:** ALTA  
**Ubicación:** `crm/tests/test_drag_drop.py` (tests 445-750)  
**Problema:**
- Filtros de periodo: solo verifica que existen en HTML
- Filtros de etapa: solo verifica checkboxes, no que oculten tarjetas
- Filtros de fuente: solo verifica opciones en select
- Filtros de búsqueda: no se valida
- Filtros de tareas: no se valida

**Impacto:**
- ⚠️ Filtros podrían no funcionar sin detectarse
- ⚠️ Usuario selecciona filtro pero nada cambia

---

### Problema #3: Refresh Manual Requerido
**Severidad:** MEDIA  
**Usuario Reportó:** "Pasé manualmente uno hacia atrás y tuve que actualizar para ver que sí se pasó"  
**Interpretación:** 
- Drag funciona (BD actualiza)
- Pero DOM no se actualiza automáticamente
- Requiere F5 o refresh manual

**Por Verificar:** Si es un bug real o percepción del usuario

---

## ✅ SOLUCIÓN IMPLEMENTADA

### Nuevo Suite de Tests: `crm/tests/test_drag_drop_real.py`

#### 1️⃣ **Tests de Drag & Drop Real (6 casos)**

Usan `ActionChains` para simular drag REAL del usuario:

```python
actions = ActionChains(self.driver)
actions.drag_and_drop(source_card, target_column).perform()
```

| Test | Valida | Resultado Esperado |
|---|---|---|
| `test_drag_card_from_lead_to_calificacion_no_refresh_needed` | Drag no requiere refresh | Tarjeta en DOM + BD actualizada |
| `test_drag_backward_calificacion_to_lead` | Drag hacia atrás funciona | Movimiento inverso registrado |
| `test_drag_multiple_times_forward_backward` | Múltiples drags | 3+ actividades creadas |
| `test_drag_card_to_closed_stage_shows_reopen_modal` | Modal de reopen aparece | Modal visible con botones |
| `test_fue_un_error_reverts_drag` | Click "Fue un error" revierte | Tarjeta vuelve a etapa anterior |
| `test_nueva_oportunidad_creates_recompra_lead` | Crear recompra | Nuevo lead creado |

#### 2️⃣ **Tests de Filtros Funcionales (11 casos)**

Validan que los filtros FUNCIONAN, no solo existen:

```python
# Antes
initial_cards = len(self.driver.find_elements(By.CLASS_NAME, "lead-card"))

# Aplicar filtro
lead_checkbox.click()
apply_btn.click()

# Después
filtered_cards = len(self.driver.find_elements(By.CLASS_NAME, "lead-card"))
self.assertLess(filtered_cards, initial_cards)  # Debe haber menos
```

| Filtro | Test | Validación |
|---|---|---|
| **Tiempo** | `test_filter_time_period_hoy_shows_only_today` | "Hoy" muestra solo de hoy |
| | `test_filter_time_period_7d_hides_old_leads` | "7d" oculta leads >7 días |
| | `test_date_range_filter_custom_dates` | Rango personalizado funciona |
| **Etapas** | `test_filter_stage_unchecked_hides_cards` | Desmarcar etapa oculta |
| **Estado** | `test_filter_open_only_toggle_hides_closed` | Toggle solo abiertos |
| **Fuente** | `test_filter_source_shows_only_selected` | Select de fuente filtra |
| **Etiquetas** | `test_filter_tags_shows_only_tagged_leads` | Tags filtran correctamente |
| **Tareas** | `test_filter_task_with_pending_shows_leads_with_tasks` | Filtro de tareas funciona |
| **Búsqueda** | `test_search_filters_leads_by_name_realtime` | Búsqueda en tiempo real |
| | `test_search_combined_with_filters` | Búsqueda + filtros juntos |
| **Gestión** | `test_clear_filters_resets_all` | Limpiar restaura todos |

---

## 📋 Matriz de Cobertura ANTES vs DESPUÉS

### ANTES (test_ui_selenium.py + test_drag_drop.py)

| Funcionalidad | Cobertura | Tipo |
|---|---|---|
| Drag tarjeta entre etapas | ❌ | HTML check (fake) |
| Drag automático sin refresh | ❌ | NO cubierto |
| Modal reopen | ❌ | NO cubierto |
| "Fue un error" button | ❌ | NO cubierto |
| "Nueva oportunidad" button | ❌ | NO cubierto |
| Filtros funcionan | ❌ | HTML check (fake) |
| Búsqueda | ❌ | HTML check (fake) |
| API backend | ✅ | Sólido |

### DESPUÉS (test_drag_drop_real.py)

| Funcionalidad | Cobertura | Tipo |
|---|---|---|
| Drag tarjeta entre etapas | ✅ | ActionChains real |
| Drag automático sin refresh | ✅ | Valida DOM + BD |
| Modal reopen | ✅ | ActionChains + assertions |
| "Fue un error" button | ✅ | Click + revert test |
| "Nueva oportunidad" button | ✅ | Click + lead creation test |
| Filtros funcionan | ✅ | Counts + visibility |
| Búsqueda | ✅ | Realtime + combined |
| API backend | ✅ | Sólido (sin cambios) |

**Mejora: 1/8 → 7/8 casos cubiertos**

---

## 🔍 Validación del Bug Reportado

### Caso: "Pasé manualmente uno hacia atrás y tuve que actualizar"

**Test que lo cubre:**
```python
def test_drag_card_from_lead_to_calificacion_no_refresh_needed():
    # Drag
    actions.drag_and_drop(source_card, target_column).perform()
    sleep(1)  # SIN refresh manual
    
    # Validar en BD
    lead_in_lead.refresh_from_db()
    self.assertEqual(lead_in_lead.current_stage, "Calificacion")
    
    # Validar en DOM (¡sin refresh!)
    lead_column_after = self.driver.find_element(By.CSS_SELECTOR, "[data-stage='Lead']")
    final_cards = len(lead_column_after.find_elements(By.CLASS_NAME, "lead-card"))
    self.assertEqual(final_cards, initial_count - 1)  # Debe estar actualizado
```

**Resultado esperado:**
- ✅ Si test PASA: drag actualiza DOM automáticamente (no requiere refresh)
- ❌ Si test FALLA: hay un bug en la actualización automática del DOM

---

## 🚀 Próximos Pasos

### 1. Ejecutar Tests (Inmediato)
```bash
pytest crm/tests/test_drag_drop_real.py -v

# O específicamente el caso del usuario:
pytest crm/tests/test_drag_drop_real.py::TestDragDropRealBehavior::test_drag_card_from_lead_to_calificacion_no_refresh_needed -v
```

### 2. Analizar Resultados
- Si **PASAN**: Dashboard está bien, refresh no era necesario
- Si **FALLAN**: Identificar el bug específico

### 3. Corregir Problemas Encontrados
- Si es DOM no actualiza: revisar JavaScript de drag handler
- Si es API no responde: revisar vistas Django
- Si es modal no aparece: revisar template HTML

### 4. Integrar a CI/CD
- Agregar a pipeline de tests automáticos
- Ejecutar antes de cada deploy

---

## 📊 Estadísticas

| Métrica | Valor |
|---|---|
| Tests creados | 17 |
| Tests de drag | 6 |
| Tests de filtros | 11 |
| Casos de UI cubiertos | 7 |
| Documentación | 3 archivos |
| Tiempo estimado ejecución | 10-15 min |
| Líneas de código de test | ~800 |

---

## ⚠️ Consideraciones Técnicas

### Por Qué ActionChains es Mejor

**Viejo (sin ActionChains):**
```python
# Solo verifica que draggable="true" existe
card = self.driver.find_element(By.CLASS_NAME, "lead-card")
self.assertEqual(card.get_attribute("draggable"), "true")  # ← Fake test
```

**Nuevo (con ActionChains):**
```python
# Simula drag REAL y valida efectos
actions = ActionChains(self.driver)
actions.drag_and_drop(source_card, target_column).perform()  # ← Real interaction
sleep(1)
lead.refresh_from_db()
self.assertEqual(lead.current_stage, "Calificacion")  # ← Verifica efecto real
```

### Por Qué WebDriverWait es Mejor

**Viejo:**
```python
sleep(2)  # ← Espera ciega, frágil
```

**Nuevo:**
```python
WebDriverWait(self.driver, 10).until(
    EC.presence_of_element_located((By.ID, "reopenModal"))
)  # ← Espera inteligente, se ejecuta apenas el elemento aparece
```

---

## 📄 Archivos Generados

| Archivo | Propósito |
|---|---|
| `crm/tests/test_drag_drop_real.py` | Suite completa de tests |
| `docs/DASHBOARD_TEST_AUDIT.md` | Auditoría detallada |
| `docs/TEST_EXECUTION_PLAN.md` | Plan de ejecución |
| `run_dashboard_tests.py` | Script para ejecutar tests |
| `TESTING_FOLLOW_UP.md` | Este documento |

---

## ✅ Conclusión

Se ha identificado que los tests existentes eran principalmente **smoke tests** (verifican que no se rompe) pero no **functional tests** (verifican que funciona).

La nueva suite `test_drag_drop_real.py` es un conjunto robusto de **functional tests** que:

1. ✅ Simula acciones reales del usuario (drag, click)
2. ✅ Valida cambios en DB
3. ✅ Valida cambios en DOM
4. ✅ Cubre todos los filtros
5. ✅ Detecta bugs de actualización automática

**Recomendación:** Ejecutar inmediatamente para identificar si hay problemas ocultos.
