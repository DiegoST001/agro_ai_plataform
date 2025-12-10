import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'agro_ai_platform.settings')
django.setup()
from datetime import datetime, timezone
from django.conf import settings
from users.models import Rol, Modulo, Operacion, RolesOperaciones, PerfilUsuario, UserOperacionOverride, Prospecto
from plans.models import Plan, ParcelaPlan
from parcels.models import Parcela, Ciclo
from crops.models import Cultivo, Variedad, Etapa, ReglaPorEtapa
from authentication.models import User
from recommendations.models import Recommendation
from rest_framework.authtoken.models import Token
from nodes.models import Node, NodoSecundario
from django.db import connection
from django.db.utils import ProgrammingError
from django.db.models import ProtectedError

SEED_ENV = os.getenv("SEED_ENV", "dev").lower()  # dev | prod

def safe_delete(model_cls):
    """
    Elimina todos los registros del modelo solo si la tabla existe en la DB.
    Evita errores si el modelo/migración cambió de app/tabla.
    """
    try:
        existing = connection.introspection.table_names()
    except Exception:
        # en caso de que introspection falle, intentar borrar y capturar ProgrammingError
        try:
            model_cls.objects.all().delete()
            print(f"Deleted all from {model_cls.__name__} (no introspection).")
        except ProgrammingError:
            print(f"Tabla para {model_cls.__name__} no existe. Omitiendo delete.")
        return

    tbl = model_cls._meta.db_table
    if tbl in existing:
        try:
            model_cls.objects.all().delete()
            print(f"Deleted all from table '{tbl}' ({model_cls.__name__}).")
        except ProgrammingError:
            print(f"ProgrammingError al borrar {tbl}. Omitiendo.")
    else:
        print(f"Tabla '{tbl}' no existe en la DB. Omitiendo {model_cls.__name__}.")

def model_table_exists(model_cls):
    try:
        tables = connection.introspection.table_names()
    except Exception:
        return False
    return model_cls._meta.db_table in tables

# --- LIMPIEZA CONTROLADA ---
if SEED_ENV == "dev":
    print("Eliminando datos previos (DEV) (orden seguro por FK)...")
    safe_delete(Recommendation)
    safe_delete(NodoSecundario)
    safe_delete(Node)
    safe_delete(ParcelaPlan)
    safe_delete(ReglaPorEtapa)
    safe_delete(Ciclo)
    safe_delete(Parcela)
    safe_delete(Etapa)
    safe_delete(Variedad)
    safe_delete(Cultivo)
    safe_delete(PerfilUsuario)
    safe_delete(UserOperacionOverride)
    safe_delete(Token)
    safe_delete(RolesOperaciones)
    safe_delete(Operacion)
    safe_delete(Modulo)
    safe_delete(Plan)
    safe_delete(Prospecto)
    try:
        safe_delete(User)
    except Exception as e:
        print(f"Error eliminando Users: {e} (continuando)")
    try:
        safe_delete(Rol)
    except ProtectedError as pe:
        print(f"ProtectedError al borrar Rol: {pe}. Intentando eliminar usuarios y reintentando...")
        try:
            User.objects.all().delete()
            safe_delete(Rol)
        except Exception as e:
            print(f"No se pudo eliminar usuarios/roles automáticamente: {e}")
else:
    print("SEED_ENV=prod: sin borrado masivo de datos.")

# --- CATALOGOS CROPS MÍNIMOS ---
crops_models = [Cultivo, Variedad, Etapa, ReglaPorEtapa]
crops_ready = all(model_table_exists(m) for m in crops_models)

if not crops_ready:
    print("[seed] Tablas de crops/parcels no detectadas. Se omite catálogo y ciclos.")
else:
    # Crear solo el cultivo/variedad requeridos
    cultivo_fresa = Cultivo.objects.get_or_create(nombre="San Fresa Andre")[0]
    variedad_andre = Variedad.objects.get_or_create(cultivo=cultivo_fresa, nombre="Andre")[0]

    cultivo_fresa.variedades.set([variedad_andre])

    # Etapas para “San Fresa Andre”
    etapas_def = [
        ("Plántula", 20),
        ("Crecimiento", 60),
        ("Floración", 20),
        ("Fructificación", 40),
        ("Cosecha", 10),
    ]
    for orden, (nombre, duracion) in enumerate(etapas_def, start=1):
        Etapa.objects.update_or_create(
            variedad=variedad_andre,
            nombre=nombre,
            defaults={'orden': orden, 'duracion_estimada_dias': duracion, 'activo': True}
        )

    # Reglas genéricas por etapa
    default_rules = [
        ("temperatura_aire", 15.0, 35.0, "Ajustar ventilación/aireación", "Proteger del frío/intensificar riego", True),
        ("humedad_suelo", 30.0, 70.0, "Aumentar riego", "Reducir riego/drenaje", True),
        ("ndvi", 0.25, 0.9, "Revisar vigor y nutrición", "Posible exceso de vegetación o sombra", True),
    ]
    for etapa in Etapa.objects.filter(variedad=variedad_andre):
        for parametro, minimo, maximo, accion_menor, accion_mayor, activo in default_rules:
            ReglaPorEtapa.objects.get_or_create(
                etapa=etapa,
                parametro=parametro,
                defaults={
                    "minimo": minimo,
                    "maximo": maximo,
                    "accion_si_menor": accion_menor,
                    "accion_si_mayor": accion_mayor,
                    "activo": activo,
                    "prioridad": max(0, 10 - (etapa.orden or 0)),
                    "created_by": None,
                }
            )

    # RBAC mínimo
    ROLES = ['agricultor', 'administrador', 'tecnico', 'superadmin']
    roles = {name: Rol.objects.get_or_create(nombre=name)[0] for name in ROLES}

    MODULOS = [
        'usuarios','parcelas','cultivos','variedades','etapas','reglas','planes',
        'sensores','recomendaciones','tareas','alertas','nodos','reportes','administracion',
        'tecnicos','autenticacion','ai','brain','ciclos',
    ]
    modulos = {name: Modulo.objects.get_or_create(nombre=name)[0] for name in MODULOS}
    OPERACIONES = ['ver', 'crear', 'actualizar', 'eliminar', 'aprobar']
    operaciones_por_modulo = {}
    for mname, modulo in modulos.items():
        ops = {}
        for op_name in OPERACIONES:
            op, _ = Operacion.objects.get_or_create(modulo=modulo, nombre=op_name)
            ops[op_name] = op
        operaciones_por_modulo[mname] = ops

    MATRIZ = {
        'superadmin': {m: OPERACIONES for m in MODULOS},
        'administrador': {
            'usuarios': ['ver','crear','actualizar','eliminar'],
            'parcelas': ['ver','crear','actualizar','eliminar'],
            'cultivos': ['ver','crear','actualizar','eliminar'],
            'variedades': ['ver','crear','actualizar','eliminar'],
            'etapas': ['ver','crear','actualizar','eliminar'],
            'reglas': ['ver','crear','actualizar','eliminar','aprobar'],
            'planes': ['ver','crear','actualizar','eliminar'],
            'sensores': ['ver','crear','actualizar','eliminar'],
            'recomendaciones': ['ver','aprobar'],
            'tareas': ['ver','crear','actualizar','eliminar'],
            'alertas': ['ver','actualizar'],
            'nodos': ['ver','crear','actualizar','eliminar'],
            'reportes': ['ver','crear'],
            'administracion': ['ver','actualizar'],
            'tecnicos': ['ver','crear','actualizar','eliminar'],
            'autenticacion': ['ver','crear','actualizar','eliminar'],
            'ai': ['ver','crear','actualizar','eliminar'],
            'brain': ['ver','crear','actualizar','eliminar'],
            'ciclos': ['ver','crear','actualizar','eliminar'],
        },
        'tecnico': {
            'sensores': ['ver','actualizar'],
            'parcelas': ['ver'],
            'cultivos': ['ver'],
            'variedades': ['ver'],
            'etapas': ['ver'],
            'reglas': ['ver','actualizar'],
            'tareas': ['ver','actualizar'],
            'alertas': ['ver','actualizar'],
            'reportes': ['ver'],
            'tecnicos': ['ver','actualizar'],
            'autenticacion': ['ver'],
            'ai': ['ver'],
            'brain': ['ver'],
            'ciclos': ['ver','actualizar'],
        },
        'agricultor': {
            'parcelas': ['ver','crear','actualizar','eliminar'],
            'cultivos': ['ver'],
            'variedades': ['ver'],
            'etapas': ['ver'],
            'reglas': ['ver'],
            'planes': ['ver','crear'],
            'sensores': ['ver'],
            'tareas': ['ver','crear','actualizar','eliminar'],
            'alertas': ['ver'],
            'reportes': ['ver'],
            'nodos': ['ver'],
            'recomendaciones': ['ver'],
            'autenticacion': ['ver'],
            'ai': ['ver'],
            'brain': ['ver'],
            'ciclos': ['ver','crear','actualizar'],
        },
    }
    def vincular(rol_nombre, modulo_nombre, ops_names):
        rol = roles[rol_nombre]; modulo = modulos[modulo_nombre]
        for op_name in ops_names:
            op = operaciones_por_modulo[modulo_nombre][op_name]
            RolesOperaciones.objects.get_or_create(rol=rol, modulo=modulo, operacion=op)

    for rname, reglas in MATRIZ.items():
        for mname, ops in reglas.items():
            if mname in modulos:
                vincular(rname, mname, ops)

    # Planes
    PLANES = [
        {'nombre': 'Básico','descripcion': '3 lecturas/día','veces_por_dia': 3,'horarios_por_defecto': ["07:00","15:00","22:00"],'precio': 0},
        {'nombre': 'Estándar','descripcion': '6 lecturas/día','veces_por_dia': 6,'horarios_por_defecto': ["06:00","09:00","12:00","15:00","18:00","21:00"],'precio': 29.90},
        {'nombre': 'Avanzado','descripcion': '8 lecturas/día','veces_por_dia': 8,'horarios_por_defecto': ["06:00","08:00","10:00","12:00","14:00","16:00","18:00","20:00"],'precio': 49.90},
    ]
    for data in PLANES:
        Plan.objects.update_or_create(nombre=data['nombre'], defaults=data)

    # Usuarios base + tokens
    usuarios_seed = []
    if not User.objects.filter(username='superadmin').exists():
        su = User.objects.create_superuser('superadmin', 'soporte@agronix.lat', '12345678', rol=roles['superadmin'])
        usuarios_seed.append(su)
    else:
        usuarios_seed.append(User.objects.get(username='superadmin'))

    if not User.objects.filter(username='admin1').exists():
        admin = User.objects.create_user(username='admin1', email='admin@demo.com', password='12345678', is_staff=True, rol=roles['administrador'])
        usuarios_seed.append(admin)
    else:
        usuarios_seed.append(User.objects.get(username='admin1'))

    if not User.objects.filter(username='tecnico1').exists():
        tec = User.objects.create_user(username='tecnico1', email='tec@demo.com', password='12345678', rol=roles['tecnico'])
        usuarios_seed.append(tec)
    else:
        usuarios_seed.append(User.objects.get(username='tecnico1'))

    if not User.objects.filter(username='agricultor1').exists():
        agri = User.objects.create_user(username='agricultor1', email='agri@demo.com', password='12345678', is_active=True, rol=roles['agricultor'])
        usuarios_seed.append(agri)
    else:
        usuarios_seed.append(User.objects.get(username='agricultor1'))

    for u in usuarios_seed:
        Token.objects.get_or_create(user=u)

    # Parcelas demo mínimas y Ciclo con variedad Andre
    agri = User.objects.get(username='agricultor1')
    parcela1, _ = Parcela.objects.get_or_create(
        usuario=agri, nombre="Parcela Demo 1",
        defaults={"ubicacion": "Valle Central","tamano_hectareas": 5.0,"latitud": -12.0464,"longitud": -77.0428,"altitud": 120.0}
    )

    etapa_orden_1 = Etapa.objects.filter(variedad=variedad_andre, activo=True, orden=1).first()
    today_date = datetime.now(timezone.utc).date()

    ciclo = Ciclo.objects.filter(parcela=parcela1, estado='activo').first()
    if not ciclo:
        Ciclo.objects.create(
            parcela=parcela1,
            cultivo=cultivo_fresa,
            variedad=variedad_andre,
            etapa_actual=etapa_orden_1,
            etapa_inicio=today_date if etapa_orden_1 else None,
            estado='activo'
        )

    # Recomendación demo mínima
    Recommendation.objects.get_or_create(
        parcela=parcela1,
        titulo="Riego inicial",
        defaults={"detalle": "Aplicar riego ligero al amanecer", "tipo": "general"}
    )

# Prospectos demo (solo en dev)
if SEED_ENV == "dev":
    safe_delete(Prospecto)
    prospectos_demo = [
        {"nombre_completo": "Carlos Pérez", "dni": "70441234","correo": "carlos.perez@example.com","telefono": "999000111","ubicacion_parcela": "Valle Central - Sector A","descripcion_terreno": "5 ha, suelo franco, ligera pendiente"},
        {"nombre_completo": "María López", "dni": "70441235","correo": "maria.lopez@example.com","telefono": "999000112","ubicacion_parcela": "Costa Norte - Playa","descripcion_terreno": "12 ha, suelo arenoso, riego por goteo posible"},
    ]
    for p in prospectos_demo:
        Prospecto.objects.create(**p)
    print(f"Prospectos insertados: {len(prospectos_demo)}")

# Perfiles demo mínimos (idempotente)
for u in User.objects.filter(username__in=['admin1','tecnico1','agricultor1']):
    PerfilUsuario.objects.get_or_create(
        usuario=u,
        defaults={"nombres": f"{u.username.capitalize()} Nombre","apellidos": f"{u.username.capitalize()} Apellido","telefono": "999999999","dni": "12345678","experiencia_agricola": 2,"fecha_nacimiento": "1990-01-01"}
    )

print("Seed OK (mínimo): roles, permisos, planes, superadmin soporte@agronix.lat, cultivo San Fresa Andre, variedad Andre, etapas/reglas, parcela y ciclo.")

