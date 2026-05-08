# Pruebas del Sistema de Resúmenes IA

## Descripción General

Se implementó un sistema automático de generación de resúmenes IA para mensajes de WhatsApp:
- **Resúmenes diarios**: Por usuario y día (texto corto y puntual)
- **Resúmenes mensuales**: General mensual por usuario (con revisiones)
- **Automatización**: Cada 12 horas (10:00 y 22:00) o manual desde UI

---

## 1. Interfaz Web de Sincronización + Resúmenes

### Ubicación
- **URL**: http://localhost:8000/ingesta/sync/

### Flujo
1. **Botón "Sincronizar WhatsApp"**
   - Trae mensajes nuevos de Evolution API
   - Crea/actualiza usuarios y mensajes en BD
   - Habilita automáticamente el boton de resúmenes después

2. **Botón "Generar Resúmenes IA (últimas 12h)"** (activado solo después de ingesta exitosa)
   - Se ejecuta después de sincronizar
   - Procesa las 12 horas anteriores
   - Genera resúmenes diarios + mensuales
   - Muestra: usuarios procesados, tokens consumidos, resúmenes creados/actualizados

---

## 2. Comandos de Prueba

### 2.1 Inspección de Datos (sin IA)
```bash
python manage.py test_summary_inspect --lookback-hours 72
```

**Salida esperada:**
- Usuario seleccionado automáticamente (el más reciente con mensajes)
- Lista de mensajes en la ventana
- Estado de resúmenes diarios existentes
- Validación de estructura

**Ejemplo:**
```
USUARIO: John Doe (573002068597) (ID=538)
VENTANA: 2026-04-14T07:37:24.545618+00:00 -> 2026-04-17T07:37:24.545618+00:00
MENSAJES TEXTO: 6

  04-14 11:57 | 📥 CLIENTE | Bueno dias
  04-16 03:20 | 📥 CLIENTE | Buenas noches
  04-16 05:25 | 📤 ASESOR | 🤦

RESÚMENES DIARIOS EXISTENTES:
  ⏳ 2026-04-14 | SIN RESUMEN
  ✗ 2026-04-17 | 319 tokens | msgs=1 | 'NO_DATA...'

✓ Estructura validada correctamente.
```

### 2.2 Procesamiento Completo (con IA - Ollama requerido)
```bash
python manage.py test_summary_single_user --lookback-hours 72 --show-messages
```

**Parámetros:**
- `--user-id <ID>`: Procesa usuario específico. Si se omite, toma el primero con mensajes recientes
- `--lookback-hours <N>`: Ventana en horas (default: 12)
- `--show-messages`: Muestra mensajes antes de generar resumen

**Salida esperada:**
```
Usuario seleccionado: John Doe (ID=538)
Mensajes encontrados: 6 desde 2026-04-14T07:37:24.545618+00:00

=== MENSAJES ===
  11:57 | CLIENTE | Bueno dias
  05:25 | ASESOR  | 🤦

=== GENERANDO RESUMEN ===
Status: completed
Procesados: 1 usuarios
Mensajes textuales procesados: 6
Resúmenes diarios: 2 creados, 0 actualizados
Resúmenes mensuales: 0 creados, 1 actualizado
Tokens: 245 entrada + 74 salida = 319 total

✓ Procesamiento completado.
```

---

## 3. Comando Automático (Sin UI)

### 3.1 Ejecutar resúmenes en ventana 10:00 o 22:00 (scheduler)
```bash
python manage.py run_text_summaries --only-current-slot --skip-ingestion
```

**Respuesta fuera de ventana:**
```
Fuera de ventana 10:00/22:00. No se ejecuta.
```

**Respuesta en ventana:**
```
Slot 2026-04-17T10:00:00+00:00 -> 2026-04-17T22:00:00+00:00 | status=completed users=5/8 tokens=1200
Proceso terminado. corridos=1 | omitidos_por_completado=0
```

### 3.2 Resúmenes de las últimas 48 horas + ingesta previa
```bash
python manage.py run_text_summaries --lookback-hours 48
```

### 3.3 Forzar reprocesar (ignora completados anteriores)
```bash
python manage.py run_text_summaries --lookback-hours 24 --force
```

---

## 4. API REST

### 4.1 Disparar Resúmenes IA Manual

**Endpoint:**
```
POST /ingesta/api/summary/
```

**Payload:**
```json
{
  "lookback_hours": 12,
  "force": false
}
```

**Respuesta (202 - Job creado):**
```json
{
  "job_id": "abc123-...",
  "status": "queued",
  "progress": 0,
  "message": "Tarea de resúmenes creada"
}
```

**Consultar estado (poll cada segundo):**
```
GET /ingesta/api/summary/{job_id}/status/
```

**Respuesta final (completed):**
```json
{
  "job_id": "abc123-...",
  "status": "completed",
  "progress": 100,
  "message": "Resúmenes IA completados",
  "result": {
    "run_key": "manual_abc123-...",
    "status": "completed",
    "eligible_users": 8,
    "processed_users": 5,
    "failed_users": 0,
    "daily_summaries_created": 12,
    "daily_summaries_updated": 3,
    "monthly_summaries_created": 0,
    "monthly_summaries_updated": 1,
    "total_tokens": 1847
  }
}
```

---

## 5. Dashboard de Resúmenes

### Ubicación
- **URL**: http://localhost:8000/ingesta/crm/user/{user_id}/

### Vista 1: Resumen IA del Mes
```
Resumen IA del mes
2026-04 | revisión 1

Tema general con pendientes y contactos principales.
Tokens: 456 | Mensajes base: 87

Pendientes: Llamada cliente, Envío documentos
```

### Vista 2: Resúmenes IA por Día (tabla)
```
| Fecha      | Resumen puntual                    | Pendientes | Tokens |
|------------|------------------------------------| -----------|--------|
| 2026-04-17 | Consulta disponibilidad producto  | Cotizar    | 245    |
| 2026-04-16 | Seguimiento pedido anterior       | -          | 189    |
| 2026-04-14 | No hay resumen                    | -          | 0      |
```

---

## 6. Auditoría en Django Admin

### Ubicación
- **URL**: http://localhost:8000/admin/ingesta/

### Vistas de Auditoría

#### 6.1 Summary Execution Control
Registra cada corrida de resúmenes:
- `run_key`: Identificador único de corrida
- `slot_start / slot_end`: Ventana de tiempo procesada
- `status`: running | completed | failed | skipped
- `eligible_users`: Usuarios con mensajes en ventana
- `processed_users`: Usuarios con cambios de resumen
- `total_tokens`: Entrada + salida consumidos en IA

#### 6.2 Daily Text Summary
Resúmenes por día:
- Fecha del resumen
- Usuario
- Texto generado (corto y puntual)
- `pending_items`: Pendientes detectados
- Tokens usados
- Timestamp de última ejecución que lo actualizó

#### 6.3 Monthly Text Summary
Resúmenes mensuales:
- Año/mes
- Usuario
- Revisión (incrementa si se actualiza)
- `is_current`: Marca la versión vigente
- Tokens y mensajes de origen

---

## 7. Configuración (.env)

```env
# Resúmenes IA
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2
AI_SUMMARY_TIMEOUT_SECONDS=90
AI_SUMMARY_SCHEDULER_ENABLED=True
AI_SUMMARY_STARTUP_LOOKBACK_HOURS=48
AI_SUMMARY_CHECK_INTERVAL_SECONDS=300
```

---

## 8. Caraterísticas de Seguridad y Robustez

### ✓ Implementado

1. **Sin Alucinación**
   - Si no hay datos, devuelve `NO_DATA` en lugar de inventar
   - Validación estricta de JSON
   - Conversión segura de tipos

2. **Evita Reprocesos**
   - Revisa si mensaje_count + último_timestamp no cambió
   - Solo regenera si hay datos nuevos
   - Control por corrida: `run_key` único

3. **Control de Ejecución**
   - Estado de cada corrida: RUNNING | COMPLETED | FAILED | SKIPPED
   - Contadores granulares: usuarios elegibles, procesados, fallidos
   - Texto de detalle para debugging

4. **Tokens Auditables**
   - Entrada (prompt_tokens) + Salida (completion_tokens) registrados
   - Acumulados por corrida, por usuario, por día y mes
   - Permiten análisis de costo IA

5. **Scheduler Robusto**
   - No interfiere con comandos administrativos
   - Retry con backoff en caso de fallo
   - Log centralizado en Django
   - Solo ejecuta en 10:00 y 22:00 UTC

6. **Duración y Timeout**
   - Timeout configurable (default 90s) para IA
   - Detección de no respondidos
   - Transcripción compacta para optimizar tokens

---

## 9. Scenario de Prueba Completa

### Paso 1: Sincronizar desde UI
1. Ir a http://localhost:8000/ingesta/sync/
2. Seleccionar instancia "Deya3"
3. Click "Sincronizar WhatsApp"
4. Esperar "Proceso completado"
5. Notar que botón "Generar Resúmenes IA" se habilita

### Paso 2: Generar Resúmenes desde UI
1. Click "Generar Resúmenes IA (últimas 12h)"
2. Monitor los tokens y usuarios procesados
3. Ver resultados en JSON

### Paso 3: Validar en Dashboard
1. Ir a http://localhost:8000/ingesta/crm/
2. Seleccionar un usuario con resumen
3. Ir a detalle (click en usuario)
4. Scroll down para ver:
   - "Resumen IA del mes"
   - "Resúmenes IA por día"

### Paso 4: Auditoría en Admin
1. Ir a http://localhost:8000/admin/ingesta/summaryexecutioncontrol/
2. Ver lista de corridas (más recientes primero)
3. Click en una para ver detalles: usuarios, tokens, estado

---

## 10. Troubleshooting

### Problema: Botón de resúmenes deshabilitado
- **Causa**: Ingesta falló
- **Solución**: Revisar error en "Resultado" de sync

### Problema: Resumen dice "NO_DATA"
- **Causa**: Mensajes son solo emojis sin texto
- **Solución**: Normal, el sistema no alucina. Agrega en `.text` que "No hay datos"

### Problema: Ollama timeout
- **Causa**: Ollama no responde en 90s
- **Solución**: Verificar `OLLAMA_BASE_URL`, aumentar timeout en .env

### Problema: Scheduler no corre
- **Causa**: Disabled en settings o comando de gestión activo
- **Solución**: Verificar `AI_SUMMARY_SCHEDULER_ENABLED=True` en .env

---

## 11. Métricas y KPIs

**Por corrida (SummaryExecutionControl):**
- Usuarios elegibles vs procesados (ratio de cambio)
- Fallos vs éxito (confiabilidad)
- Tokens entrada/salida (optimización de prompts)

**Por usuario (DailyTextSummary, MonthlyTextSummary):**
- `has_data`: Si el resumen contiene información útil
- `pending_items`: Cantidad de tareas pendientes detectadas
- `source_message_count`: Mensajes que generaron el resumen
- `total_tokens`: Gasto de IA por usuario/día

---

## 12. Notas para Producción

1. **Guardar SummaryExecutionControl en data warehouse** para auditoría
2. **Alertar si failed_users > 10%** de eligible_users
3. **Dashboard** con gráfico de tokens consumidos por mes
4. **Webhook** para notificar si resumen tiene "NO_DATA" 3+ días
5. **Rate limiting** en API `/ingesta/api/summary/` a máximo 1 corrida/60s
