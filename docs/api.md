# Agro AI Platform – Documentación de la API

Versión: 0.2  
Última actualización: 2025-10-23

Usuarios/clientes: Authorization: Token ...
Nodos: Authorization: Node ...

## Introducción
API REST para gestionar autenticación de usuarios, RBAC, cultivos/variedades/etapas/reglas, parcelas, planes, nodos y tareas agrícolas. Incluye endpoints de AI y analítica (Brain) y flujo de tareas recomendadas por IA con trazabilidad de decisión.

Notas
- Todas las rutas usan barra final (APPEND_SLASH=True).
- Salvo que se indique lo contrario, las respuestas están paginadas (DRF PageNumberPagination).

## Base URL
- Desarrollo local: http://127.0.0.1:8000/

## Autenticación
- TokenAuthentication (DRF authtoken). Login devuelve: { "token": "..." , "user": {...} }.
- Enviar en endpoints protegidos:
  Authorization: Token TU_TOKEN

Errores (formato común)
{
  "detail": "Mensaje legible",
  "field": ["detalle validación opcional"]
}

Paginación
- Query: ?page=N&page_size=M (si está habilitado).
- Respuesta paginada: { count, next, previous, results: [...] }

Enums frecuentes
- Task.estado: pendiente | en_progreso | completada | cancelada
- Task.origen: manual | ia
- Task.decision: pendiente | aceptada | rechazada

Modelos clave (resumen)
- User (authentication.User): extiende AbstractUser, con Rol (users.Rol).
- Parcela (parcels.Parcela): usuario (FK), nombre, ubicacion, tamano_hectareas, coordenadas, created_at, updated_at.
- Plan (plans.Plan): nombre, descripcion, frecuencia_minutos, veces_por_dia, horarios_por_defecto[], limite_lecturas_dia, precio.
- ParcelaPlan (plans.ParcelaPlan): parcela, plan, fechas, estado (activo|suspendido|vencido). Restricción: un plan activo por parcela.
- Task (tasks.Task): parcela, tipo, descripcion, fecha_programada, estado, origen, decision, deleted_at, created_at, updated_at.

---

# Endpoints

## IA

### Chat con IA
POST /api/ai/chat/  (protegido)
- Body:
  {
    "prompt": "texto",
    "model": "opcional, p.ej. 'claude-3.5' | 'ollama:llama3'",
    "context": "string opcional",
    "temperature": 0.2
  }
- 200:
  { "text": "respuesta", "model": "claude-3.5", "tokens": { "input": 12, "output": 128 } }
- 400 | 502 | 500

### Listar integraciones IA
GET /api/ai/config/  (protegido, admin)
- 200: [ { "id":1, "nombre":"Claude", "provider":"anthropic", "enabled":true, "created_at":"...", "updated_at":"..." }, ... ]

### Crear integración IA
POST /api/ai/config/  (protegido, admin)
- Body:
  { "nombre":"Claude", "provider":"anthropic", "api_key":"****", "enabled":true }
- 201: { "id":1, "nombre":"Claude", "provider":"anthropic", "enabled":true }

### Detalle de integración IA
GET /api/ai/config/{id}/  (protegido, admin)
- 200: { "id":1, "nombre":"Claude", "provider":"anthropic", "enabled":true }

### Actualizar integración IA
PUT /api/ai/config/{id}/  (protegido, admin)
PATCH /api/ai/config/{id}/  (protegido, admin)
- Body (PUT/PATCH): { "nombre": "...", "provider": "...", "enabled": true }
- 200: objeto actualizado

### Eliminar integración IA
DELETE /api/ai/config/{id}/  (protegido, admin)
- 204

---

## Brain (analítica y series)

### Historial de lecturas (agrupado)
GET /api/brain/history/  (protegido)
- Query:
  - parcela_id: int (requerido)
  - parametro: string (p.ej. "humedad_suelo") (opcional)
  - from: ISO datetime (opcional)
  - to: ISO datetime (opcional)
  - bucket: minute|hour|day (default: hour)
- 200:
  {
    "parcela_id": 7,
    "bucket": "hour",
    "series": [
      { "t": "2025-10-23T10:00:00Z", "parametro":"humedad_suelo", "avg": 23.4, "min": 21.0, "max": 26.8 }
    ]
  }

### KPIs del sistema / usuario
GET /api/brain/kpis/  (protegido)
- Query:
  - scope: "user" | "global" (default: user)
  - days: int (ventana, default 7)
- 200:
  {
    "tareas_totales": 42,
    "tareas_ia_generadas": 12,
    "tareas_ia_aceptadas": 8,
    "tareas_ia_rechazadas": 3,
    "parcelas_monitoreadas": 5
  }

### Serie temporal para parámetro de parcela
GET /api/brain/series/  (protegido)
- Query:
  - parcela_id: int (req)
  - parametro: string (req)
  - from/to: ISO (opcionales)
- 200:
  {
    "parcela_id": 7,
    "parametro": "temperatura",
    "points": [ { "t":"2025-10-23T09:12:00Z", "v": 28.2 }, ... ]
  }

---

## Cultivos

### Listar cultivos
GET /api/cultivos/  (protegido, admin)
- 200: [ { "id":1, "nombre":"Tomate", "descripcion":"..." }, ... ]

### Crear cultivo
POST /api/cultivos/  (protegido, admin)
- Body: { "nombre":"Tomate", "descripcion":"..." }
- 201: { "id":1, "nombre":"Tomate", "descripcion":"..." }

### Detalle/actualizar/eliminar
GET /api/cultivos/{id}/  (protegido, admin)
PUT /api/cultivos/{id}/  (protegido, admin)
PATCH /api/cultivos/{id}/  (protegido, admin)
DELETE /api/cultivos/{id}/  (protegido, admin)

---

## Variedades

### Listar variedades por cultivo
GET /api/cultivos/{cultivo_id}/variedades/  (protegido, admin)
- 200: [ { "id": 10, "cultivo_id":1, "nombre":"Cherry", "descripcion":"..." }, ... ]

### Crear variedad por cultivo
POST /api/cultivos/{cultivo_id}/variedades/  (protegido, admin)
- Body: { "nombre":"Cherry", "descripcion":"..." }
- 201: { "id": 10, "cultivo_id":1, "nombre":"Cherry", ... }

### Variedades (global)
GET /api/variedades/  (protegido, admin)
POST /api/variedades/  (protegido, admin)

### Detalle/actualizar/eliminar variedad
GET /api/variedades/{id}/  (protegido, admin)
PUT /api/variedades/{id}/  (protegido, admin)
PATCH /api/variedades/{id}/  (protegido, admin)
DELETE /api/variedades/{id}/  (protegido, admin)

---

## Etapas

### Listar/crear etapas
GET /api/etapas/  (protegido, admin)
POST /api/etapas/  (protegido, admin)

### Etapas por variedad
GET /api/variedades/{variedad_id}/etapas/  (protegido, admin)
POST /api/variedades/{variedad_id}/etapas/  (protegido, admin)

### Detalle/actualizar/eliminar etapa
GET /api/etapas/{id}/  (protegido, admin)
PUT /api/etapas/{id}/  (protegido, admin)
PATCH /api/etapas/{id}/  (protegido, admin)
DELETE /api/etapas/{id}/  (protegido, admin)

### Reglas por etapa
GET /api/etapas/{etapa_id}/reglas/  (protegido, admin)
POST /api/etapas/{etapa_id}/reglas/  (protegido, admin)

---

## Reglas (alias)

GET /api/reglas/  (protegido, admin)
POST /api/reglas/  (protegido, admin)
GET /api/reglas/{id}/  (protegido, admin)
PUT /api/reglas/{id}/  (protegido, admin)
PATCH /api/reglas/{id}/  (protegido, admin)
DELETE /api/reglas/{id}/  (protegido, admin)

Modelo (referencial)
{
  "id": 5,
  "etapa_id": 3,
  "parametro": "humedad_suelo",
  "minimo": 20.0,
  "maximo": 35.0,
  "accion_si_menor": "regar",
  "accion_si_mayor": "reducir_riego",
  "activo": true
}

---

## Ingesta

### Ingesta de datos desde nodo maestro
POST /api/nodes/ingest/  (protegido con Authorization: Node <token_nodo>)
- Body (ejemplo):
  {
    "codigo_nodo_maestro": "NM-001",
    "parcela_id": 7,
    "timestamp": "2025-10-23T10:15:00Z",
    "lecturas": [
      {
        "nodo_codigo": "N1",
        "sensores": [
          { "sensor":"humedad_suelo", "valor": 23.4, "unidad":"%" },
          { "sensor":"temperatura", "valor": 28.1, "unidad":"C" }
        ]
      }
    ]
  }
- 201: { "detail":"ok", "inserted": 1 }
Notas
- Tras guardar, el sistema puede disparar el análisis de reglas (Brain) para crear tareas IA.

---

## Nodos

GET /api/nodos/  (protegido, admin)
- 200: [ { "id":1, "codigo":"NM-001", "parcela_id":7, "ubicacion":"...", "...": "..." }, ... ]

GET /api/nodos/{id}/  (protegido, admin)
- 200: detalle del nodo maestro

DELETE /api/nodos/{id}/delete/  (protegido, admin)
- 204

Nodos por parcela
- GET /api/parcelas/{parcela_id}/nodos/  (protegido)
- GET /api/parcelas/{parcela_id}/nodos/{id}/  (protegido)
- POST /api/parcelas/{parcela_id}/nodos/create/  (protegido)
  - Body: { "codigo":"NM-002", "ubicacion":"..." }

Nodos secundarios
- GET /api/nodos/{nodo_master_id}/secundarios/  (protegido, admin)
- POST /api/nodos/{nodo_master_id}/secundarios/create/  (protegido, admin)
  - Body: { "codigo":"NS-01", "tipo":"sensor", ... }
- GET /api/secundarios/  (protegido, admin)
- GET /api/secundarios/{id}/  (protegido, admin)
- DELETE /api/secundarios/{id}/delete/  (protegido, admin)

---

## Parcelas

### Listar parcelas
GET /api/parcelas/  (protegido)
- Query: ubicacion, search, ordering, page, page_size
- 200:
  [
    { "id":1, "nombre":"Parcela A", "ubicacion":"Cusco", "tamano_hectareas":"2.50", "plan_activo":"Básico", "created_at":"...", "updated_at":"..." }
  ]

### Crear parcela
POST /api/parcelas/  (protegido)
- Body:
  { "nombre":"Parcela A", "ubicacion":"Cusco", "tamano_hectareas":"2.5", "coordenadas":"-13.5,-71.9", "plan_id":1 }
- 201: { "parcela_id": 7, "plan": "Básico" }

### Detalle/edición/eliminación
GET /api/parcelas/{id}/  (protegido)
PUT /api/parcelas/{id}/  (protegido)
PATCH /api/parcelas/{id}/  (protegido)
DELETE /api/parcelas/{id}/  (protegido)

---

## Planes

### Suscripciones por parcela
GET /api/parcelas/{parcela_id}/planes/  (protegido)
- 200: [ { "id":11, "parcela_id":7, "plan_id":2, "estado":"activo", "fecha_inicio":"...", "fecha_fin":null }, ... ]

### Cambiar plan (crear suscripción)
POST /api/parcelas/{parcela_id}/planes/crear/  (protegido)
- Body: { "plan_id": 2 }
- 201: { "id":11, "parcela_id":7, "plan_id":2, "estado":"activo" }

### Gestión suscripción (admin/owner)
GET /api/parcelas/planes/{id}/  (protegido)
PUT /api/parcelas/planes/{id}/  (protegido)
PATCH /api/parcelas/planes/{id}/  (protegido)
DELETE /api/parcelas/planes/{id}/  (protegido)

### Planes (catálogo)
GET /api/planes/  (público)
POST /api/planes/  (protegido, admin)
GET /api/planes/{id}/  (público)
PUT /api/planes/{id}/  (protegido, admin)
PATCH /api/planes/{id}/  (protegido, admin)
DELETE /api/planes/{id}/  (protegido, admin)

Modelo Plan (respuesta)
{
  "id": 1,
  "nombre": "Básico",
  "descripcion": "Monitoreo básico",
  "frecuencia_minutos": 60,
  "veces_por_dia": 3,
  "horarios_por_defecto": ["07:00","15:00","22:00"],
  "limite_lecturas_dia": 8,
  "precio": "0.00",
  "created_at": "...",
  "updated_at": "..."
}

---

## Recomendaciones
Nota: En la versión actual, las recomendaciones del sistema se registran directamente como Tareas con origen="ia" y decision (pendiente/aceptada/rechazada). Estos endpoints existen solo si mantienes la app de recomendaciones. Si no, ignóralos.

GET /api/parcelas/{parcela_id}/recomendaciones/  (protegido)
POST /api/parcelas/{parcela_id}/recomendaciones/  (protegido)
GET /api/recomendaciones/  (protegido, admin)
GET /api/recomendaciones/{id}/  (protegido, admin)
PUT /api/recomendaciones/{id}/  (protegido, admin)
PATCH /api/recomendaciones/{id}/  (protegido, admin)
DELETE /api/recomendaciones/{id}/  (protegido, admin)

---

## Tareas

Modelo Task (respuesta)
{
  "id": 100,
  "parcela": 7,
  "tipo": "riego",
  "descripcion": "Regar 30 min (regla 5) — parametro=humedad_suelo, valor=18.2",
  "fecha_programada": "2025-10-23T11:30:00Z",
  "estado": "pendiente",
  "origen": "ia",          // manual | ia
  "decision": "pendiente", // pendiente | aceptada | rechazada
  "deleted_at": null,
  "created_at": "2025-10-23T10:40:00Z",
  "updated_at": "2025-10-23T10:40:00Z"
}

Campos y enums
- estado: pendiente | en_progreso | completada | cancelada
- origen: manual (usuario) | ia (sugerida)
- decision: pendiente | aceptada | rechazada
- Listados devuelven solo tasks activas (deleted_at == null). Para historial, usar include_deleted=true.

### Listar/crear tareas por parcela
GET /api/parcelas/{parcela_id}/tareas/  (protegido)
- Query (opcionales): estado, origen, decision, from, to (por fecha_programada), search (tipo/descripcion), include_deleted=true|false
- 200 (paginado): { count, next, previous, results: [Task] }

POST /api/parcelas/{parcela_id}/tareas/  (protegido)
- Body (crear manual):
  { "tipo":"fertilización", "descripcion":"NPK 15-15-15", "fecha_programada":"2025-10-24T08:00:00Z", "estado":"pendiente" }
- 201: Task

### Tareas (global)
GET /api/tareas/  (protegido, admin/tecnico)
POST /api/tareas/  (protegido, admin/tecnico)

### Detalle/actualizar/eliminar tarea
GET /api/tareas/{id}/  (protegido)
PUT /api/tareas/{id}/  (protegido)
PATCH /api/tareas/{id}/  (protegido)
DELETE /api/tareas/{id}/  (protegido)
- DELETE aplica eliminación lógica (marca deleted_at) si está implementado como soft-delete.

### Acciones sobre recomendaciones (si expuestas)
POST /api/tareas/{id}/accept/  (protegido)
- Efecto: decision=aceptada; conserva visible.
- 200: { "detail":"Aceptado" }

POST /api/tareas/{id}/reject/  (protegido)
- Efecto: decision=rechazada; si origen='ia' aplica soft-delete.
- 200: { "detail":"Rechazado" }

---

## RBAC

### Módulos
GET /api/rbac/modulos/  (protegido, administracion/ver)
GET /api/rbac/modulos/{id}/  (protegido, administracion/ver)
- Respuesta: { "id":2, "nombre":"administracion" }

### Roles
GET /api/rbac/roles/  (protegido, administracion/ver)
GET /api/rbac/roles/{id}/  (protegido, administracion/ver)
- Respuesta: { "id":1, "nombre":"administrador", "descripcion":"..." }

### Permisos por rol/módulo
GET /api/rbac/permissions/  (protegido, administracion/ver)
- Query: ?rol=ID&modulo=ID
- 200 (paginado):
  {
    "count": 160, "next": "...", "previous": null,
    "results": [
      {
        "id": 1801,
        "rol": { "id":60, "nombre":"admin", "descripcion":"..." },
        "modulo": { "id":173, "nombre":"administracion" },
        "operacion": { "id":863, "nombre":"actualizar", "modulo": { "id":173, "nombre":"administracion" } }
      }
    ]
  }

POST /api/rbac/permissions/  (protegido, administracion/actualizar)
- Body:
  { "rol_id":60, "modulo_id":173, "operacion_id":863 }
- 201: idem GET (objeto creado)

GET /api/rbac/permissions/{id}/  (protegido, administracion/ver)
DELETE /api/rbac/permissions/{id}/  (protegido, administracion/actualizar)

### Cambiar rol de un usuario
PATCH /api/rbac/users/{user_id}/role/  (protegido, usuarios/actualizar)
- Body: { "rol_id": 3 }
- 200: { "detail":"Rol actualizado", "user_id": 12, "rol_id": 3 }

---

## API Schema
GET /api/schema/
- OpenAPI JSON para herramientas (Swagger/ReDoc).

Swagger
- Swagger UI: /api/docs/
- ReDoc: /api/redoc/

---

## User (perfil)

Ver/crear/actualizar perfil del usuario autenticado
GET /api/user/profile/  (protegido)
POST /api/user/profile/  (protegido)
PUT /api/user/profile/  (protegido)
PATCH /api/user/profile/  (protegido)

Modelo PerfilUsuario
{
  "nombres": "Juan",
  "apellidos": "Pérez",
  "telefono": "999999999",
  "dni": "12345678",
  "fecha_nacimiento": "1990-01-01",
  "experiencia_agricola": 5
}

Respuesta GET /auth/me/ (relacionado)
{
  "id": 2, "username": "agri01", "email":"...", "rol":"agricultor",
  "profile": PerfilUsuario
}

---

## Prospectos

Listar
GET /api/user/prospectos/  (protegido, admin)
- 200: [ { "id":1, "nombre_completo":"...", "dni":"...", "correo":"...", "telefono":"...", "ubicacion_parcela":"...", "descripcion_terreno":"...", "estado":"pendiente|aprobado|rechazado" }, ... ]

Detalle
GET /api/user/prospectos/{id}/  (protegido, admin)

Aceptar prospecto y crear agricultor
POST /api/user/prospectos/{id}/aceptar/  (protegido, admin)
- Body: { "username":"nuevo", "password":"***", "correo":"opcional@email.com" }
- 201: { "msg": "Agricultor creado" }
- 400: { "error":"Username ya existe" }

---

## Auth

### Login de usuario
POST /auth/login/
- Body: { "username":"agri01", "password":"TuPasswordSegura" }
- 200: { "token":"...", "user": { "user_id": 12, "username":"agri01", "email":"..." } }

### Cerrar sesión
POST /auth/logout/  (protegido)
- 204

### Token (si está habilitado)
POST /auth/token/
- Body: { "username":"...", "password":"..." }
- 200: { "token":"..." }

---
## Notas de integración frontend

- Tipados sugeridos
  - Task:
    type Task = {
      id: number; parcela: number; tipo: string; descripcion: string;
      fecha_programada: string; estado: 'pendiente'|'en_progreso'|'completada'|'cancelada';
      origen: 'manual'|'ia'; decision: 'pendiente'|'aceptada'|'rechazada';
      deleted_at: string|null; created_at: string; updated_at: string;
    }
  - Plan:
    type Plan = {
      id:number; nombre:string; descripcion?:string|null;
      frecuencia_minutos?:number|null; veces_por_dia:number;
      horarios_por_defecto:string[]; limite_lecturas_dia:number; precio:string;
      created_at:string; updated_at:string;
    }
  - RBAC Permiso:
    type Permiso = {
      id:number;
      rol:{id:number; nombre:string; descripcion?:string};
      modulo:{id:number; nombre:string};
      operacion:{id:number; nombre:string; modulo:{id:number; nombre:string}};
    }

- Filtros comunes
  - Listas paginadas aceptan ?page, ?page_size.
  - Tareas: ?estado=&origen=&decision=&include_deleted=true.
  - Brain history: ?bucket=hour|day, ?from=ISO, ?to=ISO.

- Recomendaciones por IA
  - Las tareas sugeridas llegan con origen='ia' y decision='pendiente'.
  - Acciones: POST /api/tareas/{id}/accept/ o /reject/ si están expuestas; si no, usar PATCH /api/tareas/{id}/ con { "decision":"aceptada" } o { "decision":"rechazada" }.
  - Rechazo de IA puede aplicar soft-delete (no visible en listados normales).
