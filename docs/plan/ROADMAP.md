# Roadmap de Profesionalización — SAMA AdTech

**Inicio:** 2026-07-02  
**Proyecto:** SAMA AdTech (Django + DRF + PostgreSQL)  
**Objetivo:** Llevar el proyecto de MVP/Beta a producción profesional

---

## Filosofía de Ejecución

Cada fase es **independiente y atómica**: puede ejecutarse sola sin romper el resto.  
Cada fase debe **dejar el programa funcionando exactamente igual que antes** (o mejor).  
Cada fase genera su propia **documentación de cambios** y **registro de tests**.

---

## Resumen de Fases

| Fase | Nombre | Prioridad | Horas Est. | Dependencias |
|------|--------|-----------|------------|--------------|
| 00 | Fundación (README, LICENSE, CI/CD) | 🔴 P0 | 4h | Ninguna |
| 01 | Seguridad (cross-tenant, auth, rate limit) | 🔴 P0 | 6h | Ninguna |
| 02 | Arquitectura (application layer, Celery) | 🟠 P1 | 8h | Fase 00 |
| 03 | Performance (N+1 queries, analytics) | 🟠 P1 | 6h | Fase 01 |
| 04 | Testing (conftest, cobertura, domain tests) | 🟠 P1 | 10h | Fase 00 |
| 05 | Bugs y Deuda Técnica | 🟡 P2 | 4h | Fase 01 |
| 06 | Producción (Docker, deploy, PostgreSQL) | 🟡 P2 | 8h | Fase 00 |
| 07 | Polish (OpenAPI, factories, diagramas) | 🟢 P3 | 6h | Fase 04 |
| **Total** | | | **~52h** | |

---

## Estructura de una Fase

Cada fase vive en `docs/plan/FASE-NN-nombre.md` y contiene:

```
1. METADATOS — ID, nombre, prioridad, horas estimadas, dependencias, estado
2. OBJETIVO — Qué se logra al completar esta fase
3. REGLAS DE EJECUCIÓN — Normas obligatorias durante esta fase
4. CHECKLIST — Tareas concretas con checkboxes
5. ARCHIVOS AFECTADOS — Lista de archivos a modificar/crear/eliminar
6. CRITERIOS DE ACEPTACIÓN — Cómo saber si la fase está completa
7. TRACKING DE TIEMPO — Tabla hora por hora
8. TRACKING DE LÍNEAS — Líneas creadas/eliminadas por archivo
```

---

## Reglas Obligatorias para TODAS las Fases

### 📝 Documentación de Cambios
- Cada fase debe generar un archivo `docs/changelog/FASE-NN-cambios.md`
- Explicar **qué** se cambió, **por qué** se cambió, y **cómo** funciona ahora
- Incluir referencias a los archivos modificados con números de línea

### 🧪 Tests
- Todo nuevo código DEBE tener su test correspondiente
- Tests deben pasar antes y después de cada cambio
- Documentar los tests nuevos en el changelog de la fase
- Tests Selenium deben usar `WebDriverWait`, NO `sleep()`

### 📐 Documentación en Código
- **Todas** las funciones nuevas deben tener type hints
- **Todas** las clases y funciones públicas deben tener docstrings (estilo NumPy)
- NO agregar comentarios triviales (`# Esto suma x e y`)
- Código debe ser auto-documentado: nombres descriptivos de variables/funciones

### 🔄 Atomicidad
- Cada commit debe ser **funcional independiente**: el programa corre después de cada commit
- No mezclar cambios de distintas fases en un mismo commit
- Si un cambio requiere modificar 3 archivos, hazlo en UN commit atómico
- El proyecto DEBE seguir funcionando después de cada interacción

### 🎯 Aislamiento
- Cada fase debe ser lo más independiente posible
- Una fase no debe romper el funcionamiento de otra
- Si hay dependencias entre fases, están documentadas explícitamente

### ⏱️ Tracking de Tiempo

Cada fase registra:

```markdown
## Tracking de Tiempo
| Fecha | Hora Ini | Hora Fin | Horas | Acumulado Fase | Acumulado Global | Tarea |
|-------|----------|----------|-------|----------------|------------------|-------|
```

### 📊 Tracking de Líneas

Cada fase registra:

```markdown
## Tracking de Líneas
| Archivo | Líneas Creadas | Líneas Eliminadas | Neto |
|---------|---------------|-------------------|------|
```

---

## Timeline Estimado

| Fecha | Hito | Fase | Horas |
|-------|------|------|-------|
| 2026-07-02 | Sesión 1 | Fase 00 + Fase 01 | ~10h |
| 2026-07-03 | Sesión 2 | Fase 02 + Fase 03 | ~14h |
| 2026-07-04 | Sesión 3 | Fase 04 | ~10h |
| 2026-07-05 | Sesión 4 | Fase 05 + Fase 06 | ~12h |
| 2026-07-06 | Sesión 5 | Fase 07 + Revision | ~6h |

> **Nota:** Las fechas son estimadas. Cada sesión actualizará el avance real.

---

## Estado Actual del Proyecto (Línea Base)

| Métrica | Valor |
|---------|-------|
| Apps Django | 6 |
| Modelos totales | ~28 |
| Endpoints REST | ~35 |
| Tests totales | ~214 |
| Cobertura estimada | 40-50% |
| Bugs conocidos graves | 7 |
| Vulnerabilidades activas críticas | 2 |
| Documentación profesional | 10% |
| Listo para producción | ❌ NO |
