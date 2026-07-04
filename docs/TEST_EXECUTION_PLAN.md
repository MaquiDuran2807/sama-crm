# Test Execution Plan - Dashboard Drag & Drop + Filtros

## 📋 Suite de Tests a Ejecutar

### Archivo: `crm/tests/test_drag_drop_real.py`

**Total de tests: ~20 casos cubiertos**

---

## 🎯 Casos de Drag & Drop (Con ActionChains - Drag REAL)

| # | Caso | Validación Principal | Archivo |
|---|------|---|---|
| 1 | Drag Lead → Calificacion **SIN refresh** | Tarjeta se mueve, BD actualiza, NO requiere refresh manual | ✅ |
| 2 | Drag hacia ATRÁS Calificacion → Lead | Movimiento inverso, se refleja inmediatamente | ✅ |
| 3 | Múltiples drags Forward/Backward | Secuencia: Lead → Calif → Lead → Calif, registra 3 actividades | ✅ |
| 4 | Drag a etapa cerrada → Modal reopen | Modal aparece con botones "Fue un error" y "Nueva oportunidad" | ✅ |
| 5 | Click "Fue un error" → Revierte drag | Tarjeta vuelve a etapa anterior, BD NO cambia | ✅ |
| 6 | Click "Nueva oportunidad" → Crea recompra | Nuevo lead creado con is_recompra=True | ✅ |

---

## 🔍 Filtros de Tiempo (Período rápido)

| # | Filtro | Validación | Status |
|---|--------|---|---|
| 7 | "Hoy" | Muestra solo leads creados hoy | ✅ |
| 8 | "7 días" | Oculta leads >7 días atrás | ✅ |
| 9 | Rango personalizado Desde/Hasta | Filtra entre fechas específicas | ✅ |

---

## 🏷️ Filtros de Etiquetas (Tags)

| # | Caso | Validación | Status |
|---|------|---|---|
| 10 | Seleccionar tag "VIP" | Muestra solo leads con ese tag | ✅ |

---

## ✓ Filtros de Estado

| # | Caso | Validación | Status |
|---|------|---|---|
| 11 | Desmarcar etapa "Lead" | Oculta tarjetas de Lead | ✅ |
| 12 | Toggle "Solo abiertos" | Oculta leads cerrados | ✅ |
| 13 | Filtro "Fuente" = "Meta" | Muestra solo Meta | ✅ |

---

## ⏳ Filtros de Tareas

| # | Caso | Validación | Status |
|---|------|---|---|
| 14 | "Con tareas pendientes" | Muestra solo leads con tasks | ✅ |

---

## 🔎 Búsqueda

| # | Caso | Validación | Status |
|---|------|---|---|
| 15 | Búsqueda por nombre en tiempo real | Filtra sin presionar aplicar | ✅ |
| 16 | Búsqueda + filtros combinados | Ambos funcionan juntos | ✅ |

---

## 🔄 Gestión de Filtros

| # | Caso | Validación | Status |
|---|------|---|---|
| 17 | Click "Limpiar filtros" | Restaura todos los leads | ✅ |

---

## 🔑 Key Finding del Usuario

**"Pasé manualmente uno hacia atrás y tuve que actualizar para ver que sí se pasó"**

→ **Test 1 valida esto**: `test_drag_card_from_lead_to_calificacion_no_refresh_needed`
  - Arrastra tarjeta
  - **NO hace refresh**
  - Valida que la tarjeta aparezca en DOM automáticamente
  - Valida que BD esté actualizada sin refrescar

---

## 🚀 Cómo Ejecutar

```bash
# Todos los tests
pytest crm/tests/test_drag_drop_real.py -v

# Solo tests de drag
pytest crm/tests/test_drag_drop_real.py::TestDragDropRealBehavior -v

# Solo tests de filtros
pytest crm/tests/test_drag_drop_real.py::TestFiltersFunctional -v

# Un test específico
pytest crm/tests/test_drag_drop_real.py::TestDragDropRealBehavior::test_drag_card_from_lead_to_calificacion_no_refresh_needed -v

# Con output detallado
pytest crm/tests/test_drag_drop_real.py -vv -s --tb=short
```

---

## 📊 Resultado Esperado

✅ **Todos los tests deben PASAR**

Esto confirmará que:
1. ✅ Drag & drop funciona sin refresh
2. ✅ Múltiples movimientos se registran correctamente
3. ✅ Modal de reopen aparece cuando es necesario
4. ✅ Todos los filtros funcionan como se espera
5. ✅ Búsqueda es en tiempo real
6. ✅ Sistema de roles está intacto

---

## ⚠️ Posibles Fallos y Causas

| Error | Causa Probable | Solución |
|---|---|---|
| `ElementNotFound: reopenModal` | Modal no existe en template | Verificar `dashboard.html` y template modales |
| `StaleElementReference` | DOM cambió entre acciones | Aumentar `sleep()` o usar waits más largos |
| `TimeoutException` | BD no se actualiza a tiempo | Verificar que el drag está siendo capturado por la API |
| `ActionChains fallando` | Versión de Selenium incompatible | `pip install --upgrade selenium` |
| Filtros no aplican | JavaScript no cargó | Verificar que `static/crm/js/dashboard.js` existe |

---

## 📝 Notas Técnicas

- **Headless mode**: Tests corren sin interfaz gráfica
- **WebDriverWait**: Esperas inteligentes por elementos, no `sleep()` fijos
- **ActionChains**: Simula drag & drop real del usuario
- **Live Server**: Django serve las pages en `http://localhost:PORT/`
- **Fixtures**: Crean datos de test en BD limpios para cada test

