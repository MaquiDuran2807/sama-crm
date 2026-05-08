## DIAGNÓSTICO: ¿POR QUÉ NO SE HIZO EL RESUMEN?

### 📊 ESTADO ACTUAL

**✓ OLLAMA ESTÁ CONECTADO**
- URL: http://localhost:11434
- Status: HTTP 200 OK
- Modelo: llama3.2:3b (disponible)

---

### 📝 HISTORIAL DE EJECUCIONES

#### 1. **demo_process_summaries** ✓ COMPLETADA
- Status: `completed`
- Usuarios: 1/1 procesados
- Tokens: 670 (470 prompt + 200 completion)
- Duración: 0.02s
- **NOTA**: No llamó a Ollama (es un script de simulación)

#### 2. **test_summary_single_user** ⚠️ STUCK EN RUNNING
- Status: `running` (desde hace 6 minutos)
- Usuarios: 3/17 procesados
- Usuarios fallidos: 0
- Tokens generados: 3725
- **PROBLEMA**: Se enfiló pero NUNCA COMPLETÓ
- **CAUSA PROBABLE**: TIMEOUT conectando a Ollama o procesando

#### 3. **summary_2026041622_2026041710** ✓ COMPLETADA  
- Status: `completed`
- Usuarios: 2/2 procesados
- Tokens: 1956 (1640 prompt + 316 completion)
- Duración: 34.39s
- **NOTA**: Esta SÍ procesó con éxito

---

### ⚠️ PROBLEMA IDENTIFICADO

**La ejecución `test_summary_single_user` se quedó COLGADA**

Esto ocurre cuando:
1. Ollama demora más que el timeout (90s configurado)
2. El modelo demora en generar respuesta
3. Hay un error en la conexión mid-request

La corrida no se marcó como `completed` ni `failed`, sino que quedó en `running`.

---

### ✅ LO QUE SÍ FUNCIONA

La corrida `summary_2026041622_2026041710`:
- ✓ Conectó a Ollama exitosamente
- ✓ Generó resúmenes para 2 usuarios
- ✓ Guardó 1956 tokens en BD
- ✓ Se marcó como `completed`

Esto demuestra que **el sistema SÍ funciona** cuando:
- Ollama está respondiendo rápido
- No hay timeout

---

### 🔧 SOLUCIONES

**Opción 1: Resetear la corrida stuck**
```bash
python manage.py shell -c "from ingesta.models import SummaryExecutionControl; log = SummaryExecutionControl.objects.get(run_key='test_user_521_1776411327.088827'); log.status='failed'; log.detail='Timeout - marcado como fallido'; log.save(); print('✓ Marcada como fallida')"
```

**Opción 2: Optimizar Ollama**
- Aumentar `AI_SUMMARY_TIMEOUT_SECONDS` en `settings.py` (de 90 a 180)
- Reducir carga del sistema para que Ollama responda más rápido
- Usar modelo más pequeño o optimizado

**Opción 3: Ver logs detallados**
Ejecuta este comando para ver los errores de UNA corrida específica.
