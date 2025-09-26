# Agro AI Platform – Documentación de la API

Versión: 0.1  
Última actualización: 2025-09-26

## Introducción
API REST para gestionar autenticación de usuarios, parcelas y la asignación de planes por parcela. Esta versión cubre:
- Registro y login de usuarios (rol agricultor).
- Gestión de parcelas del usuario autenticado.
- Consulta de planes disponibles.
- Cambio de plan activo de una parcela.
- Endpoint de chat AI global usando Claude Sonnet 4 (Anthropic).
- Endpoint de chat AI con Ollama (local) y documentación Swagger.

Nota: Todas las rutas usan barra final. APPEND_SLASH=True.

## Base URL
- Desarrollo local: http://127.0.0.1:8000/

## Autenticación
- Endpoints públicos: 
  - POST /auth/register/
  - POST /auth/login/
  - GET /api/planes/
- Endpoints protegidos:
  - POST /api/parcelas/
  - POST /api/parcelas/{parcela_id}/cambiar-plan/
  - POST /auth/logout/
  - GET /auth/me/
  - PATCH /auth/me/
  - POST /api/ai/ollama/chat/

Modo de autenticación:
- TokenAuthentication (DRF authtoken). Registro y login devuelven: { "token": "..." , "user": {...} }.
- Enviar en endpoints protegidos:
  Authorization: Token TU_TOKEN

Notas:
- APPEND_SLASH=True (usar barra final).
- SessionAuthentication puede estar activa en desarrollo, pero los ejemplos usan Token.

## Modelos clave (resumen)
- User (authentication.User): hereda de AbstractUser y se le asigna un Rol (users.Rol).
- Parcela (parcels.Parcela):
  - usuario (FK a User), nombre, ubicacion, tamano_hectareas, coordenadas, created_at, updated_at.
- Plan (plans.Plan):
  - nombre, descripcion, frecuencia_minutos, precio, created_at, updated_at.
- ParcelaPlan (plans.ParcelaPlan):
  - parcela (FK), plan (FK), fecha_inicio, fecha_fin, estado[activo|suspendido|vencido], created_at, updated_at.
  - Restricción: un plan activo por parcela.

## Semillas de datos (populate_db.py)
- Crea roles base: agricultor, administrador, tecnico, superadmin.
- Crea módulos, operaciones y permisos (si tu esquema los define).
- Crea planes base: Básico, Estándar, Pro.
- (Opcional) Usuario demo agricultor: agricultor1 / 12345678.

Ejecutar:
- python manage.py makemigrations
- python manage.py migrate
- python populate_db.py

---

## Endpoints

### 1) Registro de usuario
POST /auth/register/

Crea un usuario con rol agricultor y su perfil básico. Devuelve token.

Body (JSON):
{
  "username": "agri01",
  "email": "agri01@demo.com",
  "password": "TuPasswordSegura",
  "nombres": "Juan",
  "apellidos": "Pérez",
  "telefono": "999999999",
  "dni": "12345678",
  "fecha_nacimiento": "1990-01-01"
}

Respuestas
- 201 Created
  {
    "token": "xxxxxxxx",
    "user": {
      "user_id": 12,
      "username": "agri01",
      "email": "agri01@demo.com"
    }
  }
- 400 Bad Request: validaciones (username/email duplicado, formato email, etc.)

Curl
curl -X POST http://127.0.0.1:8000/auth/register/ ^
  -H "Content-Type: application/json" ^
  -d "{\"username\":\"agri01\",\"email\":\"agri01@demo.com\",\"password\":\"TuPasswordSegura\"}"

Notas
- El password no se devuelve en respuestas.
- El usuario queda activo de inmediato en esta versión (puedes cambiarlo a un flujo de verificación).

---

### 2) Login
POST /auth/login/

Autentica al usuario y devuelve token.

Body (JSON):
{
  "username": "agri01",
  "password": "TuPasswordSegura"
}

Respuestas
- 200 OK
  {
    "token": "xxxxxxxx",
    "user": {
      "user_id": 12,
      "username": "agri01",
      "email": "agri01@demo.com"
    }
  }
- 401 Unauthorized: credenciales inválidas o usuario inactivo.

Curl
curl -X POST http://127.0.0.1:8000/auth/login/ ^
  -H "Content-Type: application/json" ^
  -d "{\"username\":\"agri01\",\"password\":\"TuPasswordSegura\"}"

---

### 2.1) Logout (Token)
POST /auth/logout/  (protegido)

Headers:
- Authorization: Token xxxxxxxxx

Respuestas
- 204 No Content

Curl
curl -X POST http://127.0.0.1:8000/auth/logout/ ^
  -H "Authorization: Token xxxxxxxxx"

---

### 2.2) Cuenta del usuario (me)
GET /auth/me/  (protegido)
- Devuelve datos del usuario y su perfil.

200:
{
  "id": 2,
  "username": "agri01",
  "email": "agri01@demo.com",
  "rol": "agricultor",
  "profile": {
    "nombres": "Juan",
    "apellidos": "Pérez",
    "telefono": "999999999",
    "dni": "12345678",
    "fecha_nacimiento": "1990-01-01"
  }
}

PATCH /auth/me/  (protegido)
- Actualiza campos del perfil.

Body:
{ "nombres": "Juan Carlos", "telefono": "999111222" }

200: mismo formato que GET /auth/me/

Curl
curl -X PATCH http://127.0.0.1:8000/auth/me/ ^
  -H "Content-Type: application/json" ^
  -H "Authorization: Token xxxxxxxxx" ^
  -d "{\"nombres\":\"Juan Carlos\",\"telefono\":\"999111222\"}"

---

### 3) Listado de planes
GET /api/planes/

Lista todos los planes disponibles ordenados por precio.

Respuesta 200 OK
[
  {
    "id": 1,
    "nombre": "Básico",
    "descripcion": "Monitoreo básico",
    "frecuencia_minutos": 60,
    "precio": "0.00",
    "created_at": "2025-09-20T10:00:00Z",
    "updated_at": "2025-09-20T10:00:00Z"
  },
  ...
]

Curl
curl http://127.0.0.1:8000/api/planes/

---

### 4) Crear parcela y asignar plan
POST /api/parcelas/  (protegido)

Crea una parcela para el usuario autenticado y asigna un plan activo (crea registro en parcelas_planes).

Headers:
- Cookie de sesión (o Authorization si usas BasicAuth/JWT)

Body (JSON):
{
  "nombre": "Parcela A",
  "ubicacion": "Cusco",
  "tamano_hectareas": "2.5",
  "coordenadas": "-13.52,-71.97",
  "plan_id": 1
}

Respuestas
- 201 Created
  {
    "parcela_id": 7,
    "plan": "Básico"
  }
- 400 Bad Request: plan_id inválido, validaciones de campos.
- 401 Unauthorized: sin autenticación.

Curl (usando cookie guardada en login)
curl -X POST http://127.0.0.1:8000/api/parcelas/ ^
  -H "Content-Type: application/json" ^
  -b cookies.txt ^
  -d "{\"nombre\":\"Parcela A\",\"plan_id\":1}"

---

### 5) Cambiar plan activo de una parcela
POST /api/parcelas/{parcela_id}/cambiar-plan/  (protegido)

Headers:
- Authorization: Token xxxxxxxxx

Body (JSON):
{ "plan_id": 2 }

Respuestas
- 200 OK
  { "detail": "Plan actualizado.", "parcela_id": 7, "plan_id": 2 }
- 400 Bad Request | 401 Unauthorized | 404 Not Found

Curl
curl -X POST http://127.0.0.1:8000/api/parcelas/7/cambiar-plan/ ^
  -H "Content-Type: application/json" ^
  -H "Authorization: Token xxxxxxxxx" ^
  -d "{\"plan_id\":2}"

---

### RBAC – Overrides por usuario
GET /api/rbac/overrides/  (protegido, requiere administracion/ver)
- Query: ?user=ID&modulo=ID&operacion=ID&allow=true|false

POST /api/rbac/overrides/  (protegido, requiere administracion/actualizar)
Body:
{ "user": 12, "modulo": 2, "operacion": 5, "allow": false }

PATCH /api/rbac/overrides/{id}/  (protegido)
Body:
{ "allow": true }

DELETE /api/rbac/overrides/{id}/  (protegido)

Nota:
- Si existe override para (user, modulo, operacion), se aplica primero:
  - allow=true: concede aunque el rol no lo tenga.
  - allow=false: deniega aunque el rol lo tenga.

---

### Admin – Usuarios
GET /api/rbac/admin/users/  (protegido, administracion/ver)
- Query: ?rol=ID&is_active=true|false&search=&ordering=
PATCH /api/rbac/admin/users/{id}/  (protegido, usuarios/actualizar)
- Body: { "email": "...", "is_active": true, "rol_id": 3 }

### Admin – Parcelas
GET /api/admin/parcelas/  (protegido, administracion/ver)
- Query: ?usuario=ID&ubicacion=&search=&ordering=
PATCH /api/admin/parcelas/{id}/  (protegido, administracion/actualizar)
- Body: { "nombre": "...", "ubicacion": "...", "tamano_hectareas": "3.00" }

Notas:
- Usa Authorization: Token <token_admin>.
- Los permisos se validan con RBAC: administracion/ver para listar y administracion/actualizar para modificar.

## Documentación automática
- Swagger UI: http://127.0.0.1:8000/api/docs/
- ReDoc: http://127.0.0.1:8000/api/redoc/
- OpenAPI (JSON): http://127.0.0.1:8000/api/schema/
Notas:
- En Swagger pulsa “Authorize” y usa: Authorization: Token TU_TOKEN

## AI – Chat con Ollama
POST /api/ai/ollama/chat/  (protegido)

Body (JSON):
{
  "prompt": "¿Cómo riego mis tomates?"
}

200 OK
{
  "text": "…respuesta del modelo…"
}

Errores
- 400: falta prompt
- 502: Ollama no disponible
- 500: error interno

Notas:
- Requiere Authorization: Token TU_TOKEN.
- Implementación: ai.views.OllamaChatView (parchea ai.services.ollama.subprocess.run en tests).

Curl
curl -X POST http://127.0.0.1:8000/api/ai/ollama/chat/ ^
  -H "Content-Type: application/json" ^
  -H "Authorization: Token xxxxxxxxx" ^
  -d "{\"prompt\":\"¿Cómo riego mis tomates?\"}"

## Códigos de estado
- 200 OK: Operación exitosa (consultas y cambios de plan).
- 201 Created: Recursos creados (registro de usuario, creación de parcela).
- 400 Bad Request: Datos inválidos o faltantes.
- 401 Unauthorized: No autenticado.
- 403 Forbidden: Autenticado pero sin permisos (si aplicas RBAC en vistas).
- 404 Not Found: Recurso inexistente o no pertenece al usuario.
- 409 Conflict: Conflictos de negocio (p. ej., plan ya activo) — no implementado aún.
- 422 Unprocessable Entity: Validaciones de dominio más específicas — opcional.

## Formato de errores
{
  "detail": "Mensaje de error legible",
  "field_name": ["mensaje de validación específica"]
}

## Reglas y validaciones principales
- Un plan activo por parcela (restricción única en ParcelaPlan).
- plan_id debe existir.
- username y email únicos para registro.
- Solo el dueño de la parcela puede cambiar su plan.

## Seguridad y buenas prácticas
- Usar HTTPS en producción.
- Implementar JWT/TokenAuth antes de exponer públicamente.
- Limitar tasas (throttling) en /auth/*.
- Validar tamaño y formato de campos de parcela según negocio.
- Registrar auditoría de cambios de plan si se requiere trazabilidad.

## Rutas y archivos relevantes
- authentication/urls.py
- authentication/views.py
- authentication/serializers.py
- parcels/urls.py
- parcels/views.py
- parcels/serializers.py
- plans/urls.py
- plans/views.py
- plans/serializers.py
- plans/models.py
- agro_ai_platform/urls.py

## Roadmap (sugerido)
- Listar parcelas del usuario con su plan activo.
- Detalle de una parcela (incluye plan vigente e historial).
- Cancelar/suspender plan de parcela.
- Integración de pagos y estados de suscripción (pendiente/aprobada).
- JWT, refresh tokens y permisos RBAC por vista/acción.
- Versionado de API (v1/) y OpenAPI/Swagger.

---

### Parcelas
#### Listar parcelas (con filtros, búsqueda y orden)
GET /api/parcelas/  (protegido)

Query params:
- ubicacion: string (filtro exacto)
- search: string (nombre, ubicacion)
- ordering: created_at | nombre | tamano_hectareas  (usa “-” para descendente)

Paginación:
- page, page_size (por defecto PAGE_SIZE=10)

Headers:
- Authorization: Token TU_TOKEN

200:
[
  {
    "id": 1,
    "nombre": "Parcela A",
    "ubicacion": "Cusco",
    "tamano_hectareas": "2.50",
    "plan_activo": "Básico",
    "created_at": "...",
    "updated_at": "..."
  }
]

#### Crear parcela
POST /api/parcelas/  (protegido)

Body:
{
  "nombre": "Parcela A",
  "ubicacion": "Cusco",
  "tamano_hectareas": "2.5",
  "coordenadas": "-13.5,-71.9",
  "plan_id": 1
}

201:
{ "parcela_id": 7, "plan": "Básico" }

#### Detalle y edición de parcela
GET /api/parcelas/{id}/  (protegido)
PATCH /api/parcelas/{id}/  (protegido)
PUT /api/parcelas/{id}/  (protegido)

Body (PATCH ejemplo):
{ "nombre": "Parcela A - Norte", "tamano_hectareas": "3.10" }

Respuestas:
- 200 OK: mismo formato que detalle
- 404 Not Found: no existe o no pertenece al usuario
