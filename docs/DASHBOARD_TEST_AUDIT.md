# Auditoría de Tests del Dashboard CRM

## 📊 Matriz de Cobertura

### ✅ CUBIERTO - Backend / API (Tests sólidos)

| Funcionalidad | Archivo | Línea | Tipo Test | Validación |
|---|---|---|---|---|
| Cambio de etapa normal | test_drag_drop.py | 89 | API PATCH | ✅ Estado BD + actividad creada |
| Cambio a etapa cerrada | test_drag_drop.py | 103 | API PATCH | ✅ `is_closed=True`, `closed_result="won"` |
| Agregar nota | test_drag_drop.py | 118 | API POST | ✅ Actividad `note_added` creada |
| Reopen (crear lead recompra) | test_drag_drop.py | 136 | API POST | ✅ Nuevo lead creado, `is_recompra=True` |
| Reopen falla si no cerrado | test_drag_drop.py | 179 | API POST | ✅ 400 error con mensaje específico |
| Eliminar lead | test_drag_drop.py | 247 | API DELETE | ✅ `is_deleted=True`, actividad `deleted` |
| Restaurar lead | test_drag_drop.py | 302 | API POST | ✅ `is_deleted=False`, etapa preservada |
| Borrado permanente por antigüedad | test_drag_drop.py | 365 | Lógica | ✅ Elimina >30 días |

### ✅ CUBIERTO - Renderizado HTML (Tests aceptables)

| Funcionalidad | Archivo | Línea | Validación |
|---|---|---|---|
| Dashboard HTML carga | test_drag_drop.py | 195 | ✅ 200 OK + etiquetas en HTML |
| Tarjetas tienen `data-stage` | test_drag_drop.py | 204 | ✅ `data-stage="Lead"` presente |
| Tarjetas cerradas tienen `data-is-closed` | test_drag_drop.py | 211 | ✅ `data-is-closed="true"` presente |
| Badge recompra renderiza | test_drag_drop.py | 218 | ⚠️ Busca "recompra" en HTML (débil) |
| Etiquetas en tarjeta | test_drag_drop.py | 195 | ✅ Nombre tag en HTML |
| Filtros periodo (hoy, ayer, 7d, 30d, mes, todo) | test_drag_drop.py | 445 | ✅ Todos presentes en HTML |
| Filtros etapa muestran pipeline | test_drag_drop.py | 464 | ✅ "Lead", "Calificacion" en HTML |
| Filtros fuente (Meta, Google, TikTok, etc) | test_drag_drop.py | 506 | ✅ Opciones en `<select>` |
| Stats endpoint actualiza | test_drag_drop.py | 748 | ✅ Total de leads correcto |

### ✅ CUBIERTO - UI Selenium (Pero solo estructura HTML)

| Funcionalidad | Archivo | Línea | Problema |
|---|---|---|---|
| Kanban renderiza 3 columnas | test_ui_selenium.py | 163 | ⚠️ Solo cuenta elementos, no verifica drag |
| Tarjetas tienen `draggable="true"` | test_ui_selenium.py | 167 | ⚠️ Verifica atributo, no drag real |
| Tarjetas tienen `data-stage` | test_ui_selenium.py | 174 | ⚠️ Verifica atributo HTML |
| Tarjetas tienen `data-lead-id` | test_ui_selenium.py | 313 | ⚠️ Verifica atributo HTML |
| Columnas tienen `data-stage` | test_ui_selenium.py | 323 | ⚠️ Verifica atributo HTML |
| Filtros de etapa en sidebar | test_ui_selenium.py | 332 | ⚠️ Solo valida presencia |
| Tarjetas son `<a>` links | test_ui_selenium.py | 347 | ✅ Verifica tag y href |
| Botón eliminar existe | test_ui_selenium.py | 220 | ✅ Existe |
| Modal de eliminación abre | test_ui_selenium.py | 237 | ✅ Click real + modal visible |
| Confirmar eliminación funciona | test_ui_selenium.py | 249 | ✅ Click real + BD actualizada |
| Botón restaurar funciona | test_ui_selenium.py | 289 | ✅ Click real + BD actualizada |

---

## ❌ NO CUBIERTO - Lo que NO se prueba

### 🔴 CRÍTICO: Drag & Drop Real

| Caso | Descripción | Por Qué Falta | Impacto |
|---|---|---|---|
| **Drag tarjeta entre etapas** | Arrastrar una tarjeta de "Lead" a "Calificacion" | Sin `ActionChains` o `drag_and_drop()` en Selenium | ❌ No se valida la UX principal |
| **Drag crea nota automática** | El sistema debe crear una `LeadActivity` cuando se hace drag | No hay test que simule drag + verifique nota | ❌ Posible regresión silenciosa |
| **Drag a etapa cerrada → modal reopen** | Debería aparecer modal con opciones "Fue un error" / "Nueva oportunidad" | Sin simular drag a etapa cerrada | ❌ Workflow crítico sin test |
| **"Fue un error" revierte tarjeta** | Click en "Fue un error" vuelve la tarjeta a etapa anterior | Sin simular este flujo visual | ❌ Reversión de drag sin test |
| **"Nueva oportunidad" crea recompra** | Click en "Nueva oportunidad" crea lead nuevo | Sin simular este flujo visual | ❌ Recompra sin test de UX |
| **Drag entre columnas actualiza visualmente** | La tarjeta desaparece de columna vieja y aparece en nueva | Sin validación visual post-drag | ❌ Animaciones/transiciones sin test |
| **Drag con keyboard (a11y)** | Arrastrar tarjetas con teclado | No existe test | ❌ Accesibilidad sin cobertura |

### 🟡 SECUNDARIO: Filtros (Verifican presencia, NO funcionalidad)

| Caso | Descripción | Test Actual | Problema |
|---|---|---|---|
| **Filtro período: cambiar a "7d"** | Seleccionar "7d" filtra leads creados hace 7 días | Solo verifica HTML existe | ⚠️ No valida que filtre |
| **Filtro etapa: desmarcar "Lead"** | Desmarcar Lead debería ocultarlas | Solo verifica checkbox existe | ⚠️ No valida que oculte |
| **Filtro fuente: cambiar a "Meta"** | Cambiar a Meta debería mostrar solo Meta | Solo verifica opción existe | ⚠️ No valida que filtre |
| **Rango personalizado (Desde/Hasta)** | Filtrar por fecha personalizada | Solo verifica inputs existen | ⚠️ No valida funcionalidad |
| **"Solo abiertos" toggle** | Click en toggle debe ocultarleads cerrados | Solo verifica toggle existe | ⚠️ No valida cambio |
| **Aplicar/Limpiar filtros** | Botones deben ejecutar la acción | Solo verifica existen | ⚠️ No valida acción |

### 🟠 MENOR: Búsqueda y Otros

| Caso | Descripción | Cobertura |
|---|---|---|
| **Búsqueda de leads (#lead-search)** | Campo de búsqueda en dashboard | ❌ Solo existe en HTML, no funcional |
| **Ordenamiento de tarjetas** | Orden por fecha/nombre/etc | ❌ Ningún test |
| **Paginación dentro de columnas** | Si hay muchos leads, paginar | ❌ Ningún test |
| **Animación drag visual** | Ver tarjeta moverse en pantalla | ❌ Ningún test |
| **Error handling en drag** | Drag fallido muestra error | ❌ Ningún test |
| **Concurrencia: 2 usuarios simultáneo** | Dos usuarios arrastrando mismo lead | ❌ Ningún test |

---

## 📋 Conclusión

### Lo que SÍ funciona (cubierto por tests)
- ✅ API de cambio de etapa (backend)
- ✅ Eliminación/Restauración de leads
- ✅ Creación de leads recompra vía API
- ✅ Renderizado básico del HTML
- ✅ Navegación entre detalles (botón eliminar, restaurar)

### Lo que NO se sabe si funciona (sin tests)
- ❌ **Drag & Drop visual** (LA CARACTERÍSTICA PRINCIPAL)
- ❌ **Modal de reopen** cuando se arrastra a etapa cerrada
- ❌ **"Fue un error" / "Nueva oportunidad"** (opciones dentro del modal)
- ❌ **Filtros** (presencia pero no funcionalidad)
- ❌ **Búsqueda** (campo existe pero no se valida)
- ❌ **Ordenamiento**
- ❌ **Casos de error** en drag

### Riesgo
**Muy Alto**: El dashboard puede parecer que funciona (tests pasan), pero el drag & drop real podría estar completamente roto sin que lo detectemos. Los tests de Selenium solo verifican HTML, no comportamiento.

---

## 🛠️ Próximos Pasos Recomendados

1. **Escribir tests de drag & drop real** con `ActionChains` (Alto)
2. **Tests de modales de reopen** (Alto)
3. **Tests de filtros funcionales** (Medio)
4. **Tests de búsqueda** (Medio)
5. **Tests de error handling** (Bajo)
