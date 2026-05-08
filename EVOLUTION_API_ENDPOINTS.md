# Evolution API Endpoints Encontrados (instancia local)

Fecha de validacion: 2026-04-17
Version detectada: `2.3.7`
Base URL usada: `http://localhost:8080`

## 1) Endpoints confirmados por prueba directa

### GET /
- Estado: probado, `200 OK`
- Que hace: health/welcome de Evolution API.
- Respuesta incluye:
  - `version`
  - `manager`
  - `documentation`

### GET /manager y GET /manager/
- Estado: probado, `200 OK`
- Que hace: carga la UI web (SPA) de Evolution Manager.
- Nota: no es endpoint de datos para ingesta.

### POST /chat/findMessages/{instanceName}
- Estado: usado en produccion del proyecto.
- Que hace: lista mensajes paginados por instancia.
- Uso actual en proyecto:
  - `POST /chat/findMessages/Deya3`
  - Body con `where`, `offset`, `page`.

### POST /chat/getBase64FromMediaMessage/{instanceName}
- Estado: probado, `201` (exitoso).
- Que hace: devuelve media descifrada en base64 para mensajes con URL `.enc`.
- Ejemplo probado:
  - `POST /chat/getBase64FromMediaMessage/Deya3`
  - Body: `{"message": <raw_data_del_mensaje>}`
- Campos observados en respuesta:
  - `mediaType`
  - `fileName`
  - `size`
  - `mimetype`
  - `base64`

## 2) Endpoints detectados en el bundle del Manager (no todos probados)

Estos se encontraron en el JS del manager (`/assets/index-CO3NSIFj.js`), por lo que existen referencias internas:

### /chat/findChats/
- Detectado en bundle.
- Posible uso: listar chats/conversaciones.

### /chat/findMessages/
- Detectado en bundle.
- Corresponde al flujo de busqueda de mensajes (ademas del endpoint con instancia que ya usamos).

### /message/sendText/
- Detectado en bundle.
- Posible uso: envio de texto.

### /message/sendMedia/
- Detectado en bundle.
- Posible uso: envio de media.

### /message/sendWhatsAppAudio/
- Detectado en bundle.
- Posible uso: envio de audio WhatsApp.

## 3) Rutas probadas y no disponibles en este despliegue

Estas rutas devolvieron `404` en este entorno local:
- `/docs`
- `/swagger`
- `/swagger-json`
- `/api-docs`
- `/openapi`
- `/openapi.json`
- `/v3/api-docs`
- `/chat/getBase64FromMediaMessage` (sin `{instanceName}`)

## 4) Implicaciones para multimedia en este proyecto

- Audio/imagen/video con URL `.enc` no son reproducibles directamente desde CDN.
- Para esos casos, se debe usar:
  - `POST /chat/getBase64FromMediaMessage/{instanceName}`
- El proyecto ya integra esta estrategia para guardar archivo local reproducible cuando la URL viene cifrada.

## 5) Recomendacion operativa

- Mantener endpoint principal de ingesta: `/chat/findMessages/{instanceName}`.
- Mantener fallback de decode media: `/chat/getBase64FromMediaMessage/{instanceName}`.
- Si se cambia version de Evolution, revalidar:
  - formato de request para decode,
  - codigos de respuesta,
  - campos (`base64`, `fileName`, `mimetype`).
