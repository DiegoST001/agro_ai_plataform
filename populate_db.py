import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'agro_ai_platform.settings')
django.setup()
from datetime import datetime, timezone
from django.conf import settings
from users.models import Rol, Modulo, Operacion, RolesOperaciones, PerfilUsuario, UserOperacionOverride, Prospecto
from plans.models import Plan, ParcelaPlan
# añadí Ciclo import
from parcels.models import Parcela, Ciclo
from crops.models import Cultivo, Variedad, Etapa, ReglaPorEtapa
from authentication.models import User
from recommendations.models import Recommendation
from rest_framework.authtoken.models import Token
from nodes.models import Node, NodoSecundario
from django.db import connection
from django.db.utils import ProgrammingError
from django.db.models import ProtectedError

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

# Elimina todos los registros de las tablas principales (orden seguro por FK)
print("Eliminando datos previos (orden seguro por FK)...")

# 1. Limpiar entidades dependientes primero
safe_delete(Recommendation)
safe_delete(NodoSecundario)
safe_delete(Node)
safe_delete(ParcelaPlan)        # planes asociados a parcelas
safe_delete(ReglaPorEtapa)     # reglas técnicas por etapa
# eliminar ciclos antes de parcelas
safe_delete(Ciclo)
safe_delete(Parcela)
safe_delete(Etapa)
safe_delete(Variedad)
safe_delete(Cultivo)

# 2. Perfiles, overrides y tokens (usar safe_delete para evitar errores por tablas ausentes)
safe_delete(PerfilUsuario)
safe_delete(UserOperacionOverride)
safe_delete(Token)

# 3. Permisos RBAC, planes, prospectos (usar safe_delete)
safe_delete(RolesOperaciones)
safe_delete(Operacion)
safe_delete(Modulo)
safe_delete(Plan)
safe_delete(Prospecto)

# 4. Usuarios y roles (si quieres preservar superuser, omite safe_delete(User))
try:
    safe_delete(User)
except Exception as e:
    print(f"Error eliminando Users: {e} (continuando)")

# Eliminar roles: si hay ProtectedError, intentar borrar usuarios referenciados y reintentar
try:
    safe_delete(Rol)
except ProtectedError as pe:
    print(f"ProtectedError al borrar Rol: {pe}. Intentando eliminar usuarios que referencian roles y reintentando...")
    try:
        # Forzar eliminación de usuarios referenciados (riesgoso: revisa si deseas conservar algunos)
        User.objects.all().delete()
        print("Usuarios eliminados. Reintentando eliminar roles...")
        safe_delete(Rol)
    except Exception as e:
        print(f"No se pudo eliminar usuarios/roles automáticamente: {e}. Revisa migraciones/constraints.")

print("Datos previos eliminados.")

# --- CATALOGOS CROPS: crear solo si las tablas existen en la BD ---
def model_table_exists(model_cls):
    try:
        tables = connection.introspection.table_names()
    except Exception:
        return False
    return model_cls._meta.db_table in tables

crops_models = [Cultivo, Variedad, Etapa, ReglaPorEtapa]
crops_ready = all(model_table_exists(m) for m in crops_models)

# inicializar variables para evitar NameError si no se crean los cultivos
papaya = palta = maiz = mango = uva = platano = tomate = None
palta_hass = palta_fuerte = palta_reed = palta_booth = None
papaya_red = papaya_maradol = papaya_sunrise = None
maiz_blanco = maiz_amarillo = maiz_dulce = maiz_choclo = None
mango_tommy = mango_kent = mango_haden = mango_ataulfo = None
uva_red = uva_thompson = uva_concord = uva_flame = None
platano_cavendish = platano_dwarf = platano_plantain = platano_gros = None
tomate_roma = tomate_cherry = tomate_beef = tomate_heirloom = None

if not crops_ready:
    print("[seed] Tablas de crops/parcels para catálogo no detectadas. Se omite creación de cultivos/variedades/etapas/reglas y asignación automática de ciclos.")
else:
    # Crea cultivos base
    papaya = Cultivo.objects.get_or_create(nombre="Papaya")[0]
    palta = Cultivo.objects.get_or_create(nombre="Palta")[0]
    maiz = Cultivo.objects.get_or_create(nombre="Maíz")[0]
    mango = Cultivo.objects.get_or_create(nombre="Mango")[0]
    uva = Cultivo.objects.get_or_create(nombre="Uva")[0]
    platano = Cultivo.objects.get_or_create(nombre="Plátano")[0]
    tomate = Cultivo.objects.get_or_create(nombre="Tomate")[0]

    # Variedades por cultivo (múltiples entradas)
    # Palta
    palta_hass = Variedad.objects.get_or_create(cultivo=palta, nombre="Hass")[0]
    palta_fuerte = Variedad.objects.get_or_create(cultivo=palta, nombre="Fuerte")[0]
    palta_reed = Variedad.objects.get_or_create(cultivo=palta, nombre="Reed")[0]
    palta_booth = Variedad.objects.get_or_create(cultivo=palta, nombre="Booth")[0]

    # Papaya
    papaya_red = Variedad.objects.get_or_create(cultivo=papaya, nombre="Red Lady")[0]
    papaya_maradol = Variedad.objects.get_or_create(cultivo=papaya, nombre="Maradol")[0]
    papaya_sunrise = Variedad.objects.get_or_create(cultivo=papaya, nombre="Sunrise")[0]

    # Maíz
    maiz_blanco = Variedad.objects.get_or_create(cultivo=maiz, nombre="Blanco")[0]
    maiz_amarillo = Variedad.objects.get_or_create(cultivo=maiz, nombre="Amarillo")[0]
    maiz_dulce = Variedad.objects.get_or_create(cultivo=maiz, nombre="Dulce")[0]
    maiz_choclo = Variedad.objects.get_or_create(cultivo=maiz, nombre="Choclo")[0]

    # Mango
    mango_tommy = Variedad.objects.get_or_create(cultivo=mango, nombre="Tommy Atkins")[0]
    mango_kent = Variedad.objects.get_or_create(cultivo=mango, nombre="Kent")[0]
    mango_haden = Variedad.objects.get_or_create(cultivo=mango, nombre="Haden")[0]
    mango_ataulfo = Variedad.objects.get_or_create(cultivo=mango, nombre="Ataulfo")[0]

    # Uva
    uva_red = Variedad.objects.get_or_create(cultivo=uva, nombre="Red Globe")[0]
    uva_thompson = Variedad.objects.get_or_create(cultivo=uva, nombre="Thompson Seedless")[0]
    uva_concord = Variedad.objects.get_or_create(cultivo=uva, nombre="Concord")[0]
    uva_flame = Variedad.objects.get_or_create(cultivo=uva, nombre="Flame Seedless")[0]

    # Plátano / Banano
    platano_cavendish = Variedad.objects.get_or_create(cultivo=platano, nombre="Cavendish")[0]
    platano_dwarf = Variedad.objects.get_or_create(cultivo=platano, nombre="Dwarf Cavendish")[0]
    platano_plantain = Variedad.objects.get_or_create(cultivo=platano, nombre="Plantain")[0]
    platano_gros = Variedad.objects.get_or_create(cultivo=platano, nombre="Gros Michel")[0]

    # Tomate
    tomate_roma = Variedad.objects.get_or_create(cultivo=tomate, nombre="Roma")[0]
    tomate_cherry = Variedad.objects.get_or_create(cultivo=tomate, nombre="Cherry")[0]
    tomate_beef = Variedad.objects.get_or_create(cultivo=tomate, nombre="Beefsteak")[0]
    tomate_heirloom = Variedad.objects.get_or_create(cultivo=tomate, nombre="Heirloom")[0]

    # --- Asegurar explicitamente la relación cultivo -> variedades (idempotente) ---
    cultivo_map = {
        papaya: [papaya_red, papaya_maradol, papaya_sunrise],
        palta: [palta_hass, palta_fuerte, palta_reed, palta_booth],
        maiz: [maiz_blanco, maiz_amarillo, maiz_dulce, maiz_choclo],
        mango: [mango_tommy, mango_kent, mango_haden, mango_ataulfo],
        uva: [uva_red, uva_thompson, uva_concord, uva_flame],
        platano: [platano_cavendish, platano_dwarf, platano_plantain, platano_gros],
        tomate: [tomate_roma, tomate_cherry, tomate_beef, tomate_heirloom],
    }

    for cultivo_obj, variedades_list in cultivo_map.items():
        # pasar instancias de Variedad (no pks) al manager reverse de ForeignKey
        cultivo_obj.variedades.set(variedades_list)
        print(f"Cultivo '{cultivo_obj.nombre}' tiene {cultivo_obj.variedades.count()} variedades asignadas.")

    # Crear etapas por variedad
    def crear_etapas(variedad_obj, etapas_list):
        for orden, (nombre, duracion) in enumerate(etapas_list, start=1):
            Etapa.objects.get_or_create(
                variedad=variedad_obj,
                nombre=nombre,
                defaults={'orden': orden, 'duracion_estimada_dias': duracion, 'activo': True}
            )

    # definiciones y default_etapas (mantener igual)
    etapas_por_cultivo = {
        palta: [
            ("Germinación / Plantación", 30),
            ("Crecimiento vegetativo", 120),
            ("Floración", 30),
            ("Fructificación", 180),
            ("Cosecha", 30),
        ],
        papaya: [
            ("Plántula", 30),
            ("Crecer / Formación", 90),
            ("Floración", 30),
            ("Fructificación", 120),
            ("Cosecha", 30),
        ],
        maiz: [
            ("Germinación", 10),
            ("Vegetativo", 40),
            ("Floración", 20),
            ("Maduración", 30),
            ("Cosecha", 10),
        ],
        mango: [
            ("Plántula", 60),
            ("Crecimiento vegetativo", 180),
            ("Floración", 30),
            ("Fructificación", 150),
            ("Cosecha", 30),
        ],
        tomate: [
            ("Germinación", 10),
            ("Plántula", 20),
            ("Floración", 20),
            ("Fructificación", 30),
            ("Cosecha", 10),
        ],
        uva: [
            ("Plántula", 30),
            ("Crecimiento", 120),
            ("Floración", 25),
            ("Maduración", 60),
            ("Cosecha", 15),
        ],
        platano: [
            ("Establecimiento", 60),
            ("Crecimiento", 200),
            ("Floración", 40),
            ("Fructificación", 120),
            ("Cosecha", 30),
        ],
    }

    # lista por defecto si no hay definición específica por cultivo
    default_etapas = [
        ("Plántula", 30),
        ("Crecimiento", 90),
        ("Floración", 30),
        ("Fructificación", 120),
        ("Cosecha", 30),
    ]

    # -- REEMPLAZAR: crear etapas para todas las variedades en la BD (idempotente y robusto) --
    # preparar mapa por nombre de cultivo (clave en minúsculas) para evitar comparar instancias
    etapas_por_cultivo_by_name = {
        palta.nombre.lower(): etapas_por_cultivo.get(palta, default_etapas),
        papaya.nombre.lower(): etapas_por_cultivo.get(papaya, default_etapas),
        maiz.nombre.lower(): etapas_por_cultivo.get(maiz, default_etapas),
        mango.nombre.lower(): etapas_por_cultivo.get(mango, default_etapas),
        tomate.nombre.lower(): etapas_por_cultivo.get(tomate, default_etapas),
        uva.nombre.lower(): etapas_por_cultivo.get(uva, default_etapas),
        platano.nombre.lower(): etapas_por_cultivo.get(platano, default_etapas),
    }

    # Obtener todas las variedades actuales y crear/actualizar etapas para cada una
    all_variedades = Variedad.objects.select_related('cultivo').all()
    for variedad_obj in all_variedades:
        cultivo_name = (variedad_obj.cultivo.nombre or "").lower()
        etapas_list = etapas_por_cultivo_by_name.get(cultivo_name, default_etapas)
        for orden, (nombre, duracion) in enumerate(etapas_list, start=1):
            etapa_obj, created = Etapa.objects.update_or_create(
                variedad=variedad_obj,
                nombre=nombre,
                defaults={
                    'orden': orden,
                    'duracion_estimada_dias': duracion,
                    'activo': True,
                }
            )
        print(f"[seed] Etapas aseguradas para variedad '{variedad_obj.nombre}' (cultivo: '{variedad_obj.cultivo.nombre}').")

    # --- NUEVO: crear reglas genéricas por cada etapa creada (idempotente) ---
    # reglas por etapa: temperatura_aire, humedad_suelo, ndvi
    default_rules = [
        ("temperatura_aire", 15.0, 35.0, "Ajustar ventilación/aireación", "Proteger del frío/intensificar riego", True),
        ("humedad_suelo", 30.0, 70.0, "Aumentar riego", "Reducir riego/drenaje", True),
        ("ndvi", 0.25, 0.9, "Revisar vigor y nutrición", "Posible exceso de vegetación o sombra", True),
    ]

    # crear reglas para todas las etapas existentes
    etapas_qs = Etapa.objects.all()
    for etapa in etapas_qs:
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

    print(f"[seed] Reglas genéricas creadas para {etapas_qs.count()} etapas.")

    # 1) Roles base
    ROLES = ['agricultor', 'administrador', 'tecnico', 'superadmin']
    roles = {name: Rol.objects.get_or_create(nombre=name)[0] for name in ROLES}

    # 2) Módulos base (añadidos 'cultivos' y 'variedades' para controlar catálogo)
    MODULOS = [
        'usuarios',        # Controla el acceso a los usuarios
        'parcelas',        # Controla el acceso a las parcelas
        'cultivos',        # Controla el acceso a los cultivos
        'variedades',      # Controla el acceso a las variedades
        'etapas',          # Controla el acceso a las etapas
        'reglas',          # Controla el acceso a las reglas por etapa
        'planes',          # Controla el acceso a los planes
        'sensores',        # Controla el acceso a los sensores
        'recomendaciones', # Controla el acceso a las recomendaciones
        'tareas',          # Controla el acceso a las tareas
        'alertas',         # Controla el acceso a las alertas
        'nodos',           # Controla el acceso a los nodos
        'reportes',        # Controla el acceso a los reportes
        'administracion',  # Controla el acceso a la administración
        'tecnicos',        # Controla el acceso a los técnicos

        # módulos añadidos
        'autenticacion',   # endpoints de login/registro/token (app authentication)
        'ai',              # endpoints AI
        'brain',           # brain API
        'ciclos',         # Controla el acceso a los ciclos de cultivo
    ]
    modulos = {name: Modulo.objects.get_or_create(nombre=name)[0] for name in MODULOS}

    # 3) Operaciones base
    OPERACIONES = ['ver', 'crear', 'actualizar', 'eliminar', 'aprobar']
    operaciones_por_modulo = {}
    for mname, modulo in modulos.items():
        ops = {}
        for op_name in OPERACIONES:
            op, _ = Operacion.objects.get_or_create(modulo=modulo, nombre=op_name)
            ops[op_name] = op
        operaciones_por_modulo[mname] = ops

    # 4) Permisos por rol (incluir cultivos/variedades/etapas/reglas)
    MATRIZ = {
        'superadmin': {m: OPERACIONES for m in MODULOS},
        'administrador': {
            'usuarios':       ['ver', 'crear', 'actualizar', 'eliminar'],
            'parcelas':       ['ver', 'crear', 'actualizar', 'eliminar'],
            'cultivos':       ['ver', 'crear', 'actualizar', 'eliminar'],
            'variedades':     ['ver', 'crear', 'actualizar', 'eliminar'],
            'etapas':         ['ver', 'crear', 'actualizar', 'eliminar'],
            'reglas':         ['ver', 'crear', 'actualizar', 'eliminar', 'aprobar'],
            'planes':         ['ver', 'crear', 'actualizar', 'eliminar'],
            'sensores':       ['ver', 'crear', 'actualizar', 'eliminar'],
            'recomendaciones':['ver', 'aprobar'],
            'tareas':         ['ver', 'crear', 'actualizar', 'eliminar'],
            'alertas':        ['ver', 'actualizar'],
            'nodos':          ['ver', 'crear', 'actualizar', 'eliminar'],
            'reportes':       ['ver', 'crear'],
            'administracion': ['ver', 'actualizar'],
            'tecnicos':       ['ver', 'crear', 'actualizar', 'eliminar'],
            # permisos para los módulos añadidos
            'autenticacion':  ['ver', 'crear', 'actualizar', 'eliminar'],
            'ai':             ['ver', 'crear', 'actualizar', 'eliminar'],
            'brain':          ['ver', 'crear', 'actualizar', 'eliminar'],
            'ciclos':         ['ver', 'crear', 'actualizar', 'eliminar'],
        },
        'tecnico': {
            'sensores': ['ver', 'actualizar'],
            'parcelas': ['ver'],
            'cultivos': ['ver'],
            'variedades': ['ver'],
            'etapas':   ['ver'],
            'reglas':   ['ver', 'actualizar'],
            'tareas':   ['ver', 'actualizar'],
            'alertas':  ['ver', 'actualizar'],
            'reportes': ['ver'],
            'tecnicos': ['ver', 'actualizar'],
            # permisos para los módulos añadidos
            'autenticacion': ['ver'],
            'ai':            ['ver'],
            'brain':         ['ver'],
            'ciclos':        ['ver', 'actualizar'],
        },
        'agricultor': {
            'parcelas':       ['ver', 'crear', 'actualizar', 'eliminar'],
            'cultivos':       ['ver'],
            'variedades':     ['ver'],
            'etapas':         ['ver'],
            'reglas':         ['ver'],
            'planes':         ['ver', 'crear'],
            'sensores':       ['ver'],
            'tareas':         ['ver', 'crear', 'actualizar', 'eliminar'],
            'alertas':        ['ver'],
            'reportes':       ['ver'],
            'nodos':          ['ver'],
            'recomendaciones':['ver'],
            # permisos para los módulos añadidos
            'autenticacion': ['ver'],
            'ai':            ['ver'],
            'brain':         ['ver'],
            'ciclos':        ['ver', 'crear', 'actualizar'],
        },
    }
    def vincular(rol_nombre: str, modulo_nombre: str, ops_names):
        rol = roles[rol_nombre]
        modulo = modulos[modulo_nombre]
        for op_name in ops_names:
            op = operaciones_por_modulo[modulo_nombre][op_name]
            RolesOperaciones.objects.get_or_create(rol=rol, modulo=modulo, operacion=op)

    for rname, reglas in MATRIZ.items():
        for mname, ops in reglas.items():
            if mname in modulos:
                vincular(rname, mname, ops)

    # 5) Planes base por horarios fijos
    PLANES = [
        {
            'nombre': 'Básico',
            'descripcion': '3 lecturas/día',
            'frecuencia_minutos': None,
            'veces_por_dia': 3,
            'horarios_por_defecto': ["07:00","15:00","22:00"],
            'limite_lecturas_dia': 8,
            'precio': 0,
        },
        {
            'nombre': 'Estándar',
            'descripcion': '6 lecturas/día',
            'frecuencia_minutos': None,
            'veces_por_dia': 6,
            'horarios_por_defecto': ["06:00","09:00","12:00","15:00","18:00","21:00"],
            'limite_lecturas_dia': 8,
            'precio': 29.90,
        },
        {
            'nombre': 'Avanzado',
            'descripcion': '8 lecturas/día',
            'frecuencia_minutos': None,
            'veces_por_dia': 8,
            'horarios_por_defecto': ["06:00","08:00","10:00","12:00","14:00","16:00","18:00","20:00"],
            'limite_lecturas_dia': 8,
            'precio': 49.90,
        },
    ]
    for data in PLANES:
        Plan.objects.update_or_create(
            nombre=data['nombre'],
            defaults=data
        )

    # 6) Usuarios base + tokens
    usuarios_seed = []

    # superadmin
    if not User.objects.filter(username='superadmin').exists():
        su = User.objects.create_superuser('superadmin', 'super@demo.com', '12345678', rol=roles['superadmin'])
        usuarios_seed.append(su)
    else:
        su = User.objects.get(username='superadmin')
        usuarios_seed.append(su)

    # administrador
    if not User.objects.filter(username='admin1').exists():
        admin = User.objects.create_user(username='admin1', email='admin@demo.com', password='12345678', is_staff=True, rol=roles['administrador'])
        usuarios_seed.append(admin)
    else:
        admin = User.objects.get(username='admin1')
        usuarios_seed.append(admin)

    # técnico
    if not User.objects.filter(username='tecnico1').exists():
        tec = User.objects.create_user(username='tecnico1', email='tec@demo.com', password='12345678', rol=roles['tecnico'])
        usuarios_seed.append(tec)
    else:
        tec = User.objects.get(username='tecnico1')
        usuarios_seed.append(tec)

    # agricultor
    if not User.objects.filter(username='agricultor1').exists():
        agri = User.objects.create_user(username='agricultor1', email='agri@demo.com', password='12345678', is_active=True, rol=roles['agricultor'])
        usuarios_seed.append(agri)
    else:
        agri = User.objects.get(username='agricultor1')
        usuarios_seed.append(agri)

    # --- Agricultor extra ---
    if not User.objects.filter(username='agricultor2').exists():
        agri2 = User.objects.create_user(username='agricultor2', email='agri2@demo.com', password='12345678', is_active=True, rol=roles['agricultor'])
        usuarios_seed.append(agri2)
    else:
        agri2 = User.objects.get(username='agricultor2')
        usuarios_seed.append(agri2)

    # tokens
    for u in usuarios_seed:
        Token.objects.get_or_create(user=u)

    # 7) Parcelas demo por usuario agricultor/admin
    agri = User.objects.get(username='agricultor1')
    admin = User.objects.get(username='admin1')

    # ahora Parcela no almacena cultivo/variedad; se crearán Ciclos por parcela luego
    parcela1, _ = Parcela.objects.get_or_create(
        usuario=agri, nombre="Parcela Demo 1",
        defaults={
            "ubicacion": "Valle Central",
            "tamano_hectareas": 5.0,
            "latitud": -12.0464,
            "longitud": -77.0428,
            "altitud": 120.0,
        }
    )
    parcela2, _ = Parcela.objects.get_or_create(
        usuario=agri, nombre="Parcela Demo 2",
        defaults={
            "ubicacion": "Costa Norte",
            "tamano_hectareas": 12.5,
            "latitud": -5.1945,
            "longitud": -80.6328,
            "altitud": 45.0,
        }
    )
    parcela3, _ = Parcela.objects.get_or_create(
        usuario=admin, nombre="Parcela Admin 1",
        defaults={
            "ubicacion": "Sierra Sur",
            "tamano_hectareas": 3.2,
            "latitud": -13.1631,
            "longitud": -72.5450,
            "altitud": 3400.0,
        }
    )

    # Parcelas para agricultor2
    parcela4, _ = Parcela.objects.get_or_create(
        usuario=agri2, nombre="Parcela Agri2 1",
        defaults={
            "ubicacion": "Selva Alta",
            "tamano_hectareas": 8.0,
            "latitud": -9.189967,
            "longitud": -75.015152,
            "altitud": 600.0,
        }
    )
    parcela5, _ = Parcela.objects.get_or_create(
        usuario=agri2, nombre="Parcela Agri2 2",
        defaults={
            "ubicacion": "Costa Sur",
            "tamano_hectareas": 15.0,
            "latitud": -16.409047,
            "longitud": -71.537451,
            "altitud": 200.0,
        }
    )

    # conservar mapping cultivo/variedad que antes iban en Parcela para crear Ciclos
    parcel_cultivar = {
        parcela1: (maiz, maiz_blanco),
        parcela2: (papaya, papaya_red),
        parcela3: (palta, palta_hass),
        parcela4: (palta, palta_hass),
        parcela5: (papaya, papaya_red),
    }

    # --- ASIGNAR CICLO (etapa_actual y etapa_inicio) por parcela (idempotente) ---
    from datetime import datetime, timezone as dt_timezone
    today_date = datetime.now(dt_timezone.utc).date()

    # mapa: parcela -> orden de la etapa que queremos asignar (1 = primer etapa)
    parcela_etapa_orden = {
        parcela1: 3,  # Parcela Demo 1 -> etapa orden 3
        parcela2: 1,  # Parcela Demo 2 -> etapa orden 1
        parcela3: 2,  # Parcela Admin 1 -> etapa orden 2
        parcela4: 4,  # Parcela Agri2 1 -> etapa orden 4
        parcela5: 1,  # Parcela Agri2 2 -> etapa orden 1
    }

    for parcela_obj, orden_deseado in parcela_etapa_orden.items():
        cultivo_obj, variedad_obj = parcel_cultivar.get(parcela_obj, (None, None))
        if not variedad_obj:
            print(f"[seed] Parcela {parcela_obj.nombre} no tiene variedad en mapping, se omite ciclo.")
            continue

        etapa = Etapa.objects.filter(variedad=variedad_obj, activo=True, orden=orden_deseado).first()
        if not etapa:
            # fallback: primera etapa activa por orden
            etapa = Etapa.objects.filter(variedad=variedad_obj, activo=True).order_by('orden').first()

        # buscar ciclo activo existente
        ciclo = Ciclo.objects.filter(parcela=parcela_obj, estado='activo').first()
        if not ciclo:
            # crear nuevo ciclo activo
            ciclo = Ciclo.objects.create(
                parcela=parcela_obj,
                cultivo=cultivo_obj,
                variedad=variedad_obj,
                etapa_actual=etapa,
                etapa_inicio=today_date if etapa else None,
                estado='activo'
            )
            print(f"[seed] Ciclo creado para parcela '{parcela_obj.nombre}' con etapa '{etapa.nombre if etapa else 'N/A'}'.")
        else:
            changed = False
            if ciclo.cultivo_id != (cultivo_obj.id if cultivo_obj else None):
                ciclo.cultivo = cultivo_obj
                changed = True
            if ciclo.variedad_id != (variedad_obj.id if variedad_obj else None):
                ciclo.variedad = variedad_obj
                changed = True
            if etapa and ciclo.etapa_actual_id != etapa.id:
                ciclo.etapa_actual = etapa
                changed = True
            if not ciclo.etapa_inicio:
                ciclo.etapa_inicio = today_date
                changed = True
            if changed:
                ciclo.save(update_fields=['cultivo','variedad','etapa_actual','etapa_inicio','updated_at'])
                print(f"[seed] Ciclo existente actualizado para parcela '{parcela_obj.nombre}' -> etapa '{etapa.nombre if etapa else 'N/A'}'.")

    # 8) Recomendaciones demo
    Recommendation.objects.get_or_create(
        parcela=parcela1,
        titulo="Riego inicial",
        defaults={"detalle": "Aplicar riego ligero al amanecer", "tipo": "general"}
    )
    Recommendation.objects.get_or_create(
        parcela=parcela2,
        titulo="Fertilización NPK",
        defaults={"detalle": "Aplicar NPK 15-15-15 a razón de 150 kg/ha", "tipo": "nutricion"}
    )

    # 10) Nodos maestros y secundarios demo
    nodo_maestro1, _ = Node.objects.get_or_create(
        codigo="NODE-001",
        parcela=parcela1,
        defaults={
            "lat": -12.0464,
            "lng": -77.0428,
            "estado": "activo",
            "bateria": 95,
            "senal": -70,
            "last_seen": datetime(2025, 10, 1, 8, 0, 0, tzinfo=timezone.utc),
        }
    )
    nodo_maestro2, _ = Node.objects.get_or_create(
        codigo="NODE-002",
        parcela=parcela2,
        defaults={
            "lat": -5.1945,
            "lng": -80.6328,
            "estado": "activo",
            "bateria": 90,
            "senal": -65,
            "last_seen": datetime(2025, 10, 2, 8, 0, 0, tzinfo=timezone.utc),
        }
    )
    nodo_maestro3, _ = Node.objects.get_or_create(
        codigo="NODE-003",
        parcela=parcela3,
        defaults={
            "lat": -13.1631,
            "lng": -72.5450,
            "estado": "activo",
            "bateria": 80,
            "senal": -60,
            "last_seen": datetime(2025, 10, 3, 8, 0, 0, tzinfo=timezone.utc),
        }
    )

    nodo_maestro4, _ = Node.objects.get_or_create(
        codigo="NODE-004",
        parcela=parcela4,
        defaults={
            "lat": -9.189967,
            "lng": -75.015152,
            "estado": "activo",
            "bateria": 92,
            "senal": -68,
            "last_seen": datetime(2025, 10, 4, 8, 0, 0, tzinfo=timezone.utc),
        }
    )
    nodo_maestro5, _ = Node.objects.get_or_create(
        codigo="NODE-005",
        parcela=parcela5,
        defaults={
            "lat": -16.409047,
            "lng": -71.537451,
            "estado": "activo",
            "bateria": 89,
            "senal": -72,
            "last_seen": datetime(2025, 10, 5, 8, 0, 0, tzinfo=timezone.utc),
        }
    )

    secundarios1 = []
    for i in range(1, 4):
        sec, _ = NodoSecundario.objects.get_or_create(
            codigo=f"NODE-01-S{i}",
            maestro=nodo_maestro1,
            defaults={
                "estado": "activo",
                "bateria": 90 - i * 2,
                "last_seen": datetime(2025, 10, 1, 8, 10 + i, 0, tzinfo=timezone.utc),
            }
        )
        secundarios1.append(sec)

    secundarios2 = []
    for i in range(1, 6):
        sec, _ = NodoSecundario.objects.get_or_create(
            codigo=f"NODE-02-S{i}",
            maestro=nodo_maestro2,
            defaults={
                "estado": "activo",
                "bateria": 88 - i * 2,
                "last_seen": datetime(2025, 10, 2, 8, 10 + i, 0, tzinfo=timezone.utc),
            }
        )
        secundarios2.append(sec)

    secundarios3 = []
    for i in range(1, 3):
        sec, _ = NodoSecundario.objects.get_or_create(
            codigo=f"NODE-03-S{i}",
            maestro=nodo_maestro3,
            defaults={
                "estado": "activo",
                "bateria": 75 - i * 2,
                "last_seen": datetime(2025, 10, 3, 8, 10 + i, 0, tzinfo=timezone.utc),
            }
        )
        secundarios3.append(sec)

    secundarios4 = []
    for i in range(1, 3):
        sec, _ = NodoSecundario.objects.get_or_create(
            codigo=f"NODE-04-S{i}",
            maestro=nodo_maestro4,
            defaults={
                "estado": "activo",
                "bateria": 90 - i * 2,
                "last_seen": datetime(2025, 10, 4, 8, 10 + i, 0, tzinfo=timezone.utc),
            }
        )
        secundarios4.append(sec)

    secundarios5 = []
    for i in range(1, 4):
        sec, _ = NodoSecundario.objects.get_or_create(
            codigo=f"NODE-05-S{i}",
            maestro=nodo_maestro5,
            defaults={
                "estado": "activo",
                "bateria": 87 - i * 2,
                "last_seen": datetime(2025, 10, 5, 8, 10 + i, 0, tzinfo=timezone.utc),
            }
        )
        secundarios5.append(sec)

    # 9) MongoDB: telemetría demo
    try:
        from pymongo import MongoClient
        import datetime as dt
        # intentar usar la conexión central si está disponible
        try:
            from agro_ai_platform.mongo import get_db
            db = get_db()
        except Exception:
            client = MongoClient(settings.MONGO_URL)
            db = client[settings.MONGO_DB]

        # Usar únicamente la colección `lecturas_sensores`
        lects = db.lecturas_sensores
        lects.create_index([("parcela_id", 1)])
        lects.create_index([("timestamp", -1)])

        if lects.count_documents({"seed_tag": "demo"}) == 0:
            docs = [
                {
                    "seed_tag": "demo",
                    "parcela_id": parcela1.id,
                    "codigo_nodo_maestro": nodo_maestro1.codigo,
                    "timestamp": dt.datetime(2025, 10, 1, 8, 0, 0),
                    "lecturas": [
                        {
                            "nodo_codigo": secundarios1[0].codigo,
                            "last_seen": secundarios1[0].last_seen,
                            "sensores": [
                                {"sensor": "temperatura", "valor": 22.5, "unidad": "°C"},
                                {"sensor": "humedad", "valor": 65.2, "unidad": "%"},
                            ]
                        },
                        {
                            "nodo_codigo": secundarios1[1].codigo,
                            "last_seen": secundarios1[1].last_seen,
                            "sensores": [
                                {"sensor": "temperatura", "valor": 23.1, "unidad": "°C"},
                            ]
                        }
                    ]
                },
                {
                    "seed_tag": "demo",
                    "parcela_id": parcela1.id,
                    "codigo_nodo_maestro": nodo_maestro1.codigo,
                    "timestamp": dt.datetime(2025, 10, 1, 14, 0, 0),
                    "lecturas": [
                        {
                            "nodo_codigo": secundarios1[2].codigo,
                            "last_seen": secundarios1[2].last_seen,
                            "sensores": [
                                {"sensor": "temperatura", "valor": 23.0, "unidad": "°C"},
                                {"sensor": "humedad", "valor": 66.0, "unidad": "%"},
                            ]
                        }
                    ]
                },
            ]

            # Agregar 10 documentos adicionales usando los nodos reales
            for i in range(10):
                maestro = nodo_maestro2 if i % 2 == 0 else nodo_maestro1
                secundarios = secundarios2 if maestro == nodo_maestro2 else secundarios1
                docs.append({
                    "seed_tag": "demo",
                    "parcela_id": parcela2.id if maestro == nodo_maestro2 else parcela1.id,
                    "codigo_nodo_maestro": maestro.codigo,
                    "timestamp": dt.datetime(2025, 10, 2, 8 + i, 0, 0),
                    "lecturas": [
                        {
                            "nodo_codigo": secundarios[i % len(secundarios)].codigo,
                            "last_seen": secundarios[i % len(secundarios)].last_seen,
                            "sensores": [
                                {"sensor": "temperatura", "valor": 20.0 + i, "unidad": "°C"},
                                {"sensor": "humedad", "valor": 60.0 + i, "unidad": "%"},
                            ]
                        }
                    ]
                })

            # --- Telemetría para agricultor2 ---
            docs += [
                {
                    "seed_tag": "demo",
                    "parcela_id": parcela4.id,
                    "codigo_nodo_maestro": nodo_maestro4.codigo,
                    "timestamp": dt.datetime(2025, 10, 4, 8, 0, 0),
                    "lecturas": [
                        {
                            "nodo_codigo": secundarios4[0].codigo,
                            "last_seen": secundarios4[0].last_seen,
                            "sensores": [
                                {"sensor": "temperatura", "valor": 21.5, "unidad": "°C"},
                                {"sensor": "humedad", "valor": 70.2, "unidad": "%"},
                            ]
                        },
                        {
                            "nodo_codigo": secundarios4[1].codigo,
                            "last_seen": secundarios4[1].last_seen,
                            "sensores": [
                                {"sensor": "temperatura", "valor": 22.1, "unidad": "°C"},
                            ]
                        }
                    ]
                },
                {
                    "seed_tag": "demo",
                    "parcela_id": parcela5.id,
                    "codigo_nodo_maestro": nodo_maestro5.codigo,
                    "timestamp": dt.datetime(2025, 10, 5, 8, 0, 0),
                    "lecturas": [
                        {
                            "nodo_codigo": secundarios5[0].codigo,
                            "last_seen": secundarios5[0].last_seen,
                            "sensores": [
                                {"sensor": "temperatura", "valor": 23.0, "unidad": "°C"},
                                {"sensor": "humedad", "valor": 68.0, "unidad": "%"},
                            ]
                        },
                        {
                            "nodo_codigo": secundarios5[1].codigo,
                            "last_seen": secundarios5[1].last_seen,
                            "sensores": [
                                {"sensor": "temperatura", "valor": 24.2, "unidad": "°C"},
                            ]
                        },
                        {
                            "nodo_codigo": secundarios5[2].codigo,
                            "last_seen": secundarios5[2].last_seen,
                            "sensores": [
                                {"sensor": "temperatura", "valor": 25.1, "unidad": "°C"},
                            ]
                        }
                    ]
                }
            ]

            # Insertar directamente en lecturas_sensores
            try:
                lects.insert_many(docs)
                print("MongoDB: lecturas_sensores insertados.")
            except Exception as e:
                print(f"MongoDB: error al insertar en lecturas_sensores -> {e}")
        else:
            print("MongoDB: lecturas_sensores seed_tag=demo ya existe, no se duplica.")
    except ImportError:
        print("Nota: pymongo no instalado. Ejecuta: pip install pymongo")
    except Exception as e:
        print(f"MongoDB: error al insertar datos demo -> {e}")

# --- PROSPECTOS DEMO ---
# aseguramos limpieza (ya se borra arriba pero dejamos idempotencia local)
safe_delete(Prospecto)

prospectos_demo = [
    {
        "nombre_completo": "Carlos Pérez",
        "dni": "70441234",
        "correo": "carlos.perez@example.com",
        "telefono": "999000111",
        "ubicacion_parcela": "Valle Central - Sector A",
        "descripcion_terreno": "5 ha, suelo franco, ligera pendiente"
    },
    {
        "nombre_completo": "María López",
        "dni": "70441235",
        "correo": "maria.lopez@example.com",
        "telefono": "999000112",
        "ubicacion_parcela": "Costa Norte - Playa",
        "descripcion_terreno": "12 ha, suelo arenoso, riego por goteo posible"
    },
    {
        "nombre_completo": "Juan Torres",
        "dni": "70441236",
        "correo": "juan.torres@example.com",
        "telefono": "999000113",
        "ubicacion_parcela": "Sierra Sur - Altiplano",
        "descripcion_terreno": "3 ha, altitud alta, suelos pedregosos"
    },
    {
        "nombre_completo": "Ana Gómez",
        "dni": "70441237",
        "correo": "ana.gomez@example.com",
        "telefono": "999000114",
        "ubicacion_parcela": "Selva Alta - Zona B",
        "descripcion_terreno": "8 ha, suelo húmedo, acceso limitado"
    },
    {
        "nombre_completo": "Luis Fernández",
        "dni": "70441238",
        "correo": "luis.fernandez@example.com",
        "telefono": "999000115",
        "ubicacion_parcela": "Valle Bajo - Parcelas 12",
        "descripcion_terreno": "10 ha, buen acceso, suelos ricos"
    },
    {
        "nombre_completo": "Beatriz Castillo",
        "dni": "70441239",
        "correo": "beatriz.castillo@example.com",
        "telefono": "999000116",
        "ubicacion_parcela": "Costa Sur - Parcel 5",
        "descripcion_terreno": "15 ha, suelo mixto, cercado parcial"
    },
]

for p in prospectos_demo:
    Prospecto.objects.create(**p)

print(f"Prospectos insertados: {len(prospectos_demo)}")

# Crear perfiles demo
for u in usuarios_seed:
    if u.username in ['admin1', 'tecnico1', 'agricultor1']:
        PerfilUsuario.objects.create(
            usuario=u,
            nombres=f"{u.username.capitalize()} Nombre",
            apellidos=f"{u.username.capitalize()} Apellido",
            telefono="999999999",
            dni="12345678",
            experiencia_agricola=2,
            fecha_nacimiento="1990-01-01",
        )
    elif u.username == 'agricultor2':
        PerfilUsuario.objects.get_or_create(
            usuario=u,
            defaults={
                "nombres": "Agricultor2 Nombre",
                "apellidos": "Agricultor2 Apellido",
                "telefono": "988888888",
                "dni": "87654321",
                "experiencia_agricola": 3,
                "fecha_nacimiento": "1988-05-15",
            }
        )

print(
    "Seed OK: roles, módulos, operaciones, permisos, planes, usuarios, parcelas, ciclos, MongoDB y nodos."
)

