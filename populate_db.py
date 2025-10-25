import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'agro_ai_platform.settings')
django.setup()
from datetime import datetime, timezone
from django.conf import settings
from users.models import Rol, Modulo, Operacion, RolesOperaciones, PerfilUsuario, UserOperacionOverride, Prospecto
from plans.models import Plan
from authentication.models import User
from parcels.models import Parcela, Cultivo, Variedad
from recommendations.models import Recommendation
from rest_framework.authtoken.models import Token
from nodes.models import Node, NodoSecundario

# Elimina todos los registros de las tablas principales (orden seguro por FK)
print("Eliminando datos previos...")

# 1. Elimina perfiles y overrides relacionados a usuarios
PerfilUsuario.objects.all().delete()
UserOperacionOverride.objects.all().delete()

# 2. Elimina tokens
Token.objects.all().delete()

# 3. Elimina recomendaciones, nodos, parcelas, cultivos, variedades
Recommendation.objects.all().delete()
NodoSecundario.objects.all().delete()
Node.objects.all().delete()
Parcela.objects.all().delete()
Cultivo.objects.all().delete()
Variedad.objects.all().delete()

# 4. Elimina permisos RBAC y prospectos
RolesOperaciones.objects.all().delete()
Operacion.objects.all().delete()
Modulo.objects.all().delete()
Plan.objects.all().delete()
Prospecto.objects.all().delete()

# 5. Elimina usuarios (excepto superusuario si lo deseas)
User.objects.all().delete()

# 6. Finalmente elimina roles
Rol.objects.all().delete()

print("Datos previos eliminados.")

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


# 1) Roles base
ROLES = ['agricultor', 'administrador', 'tecnico', 'superadmin']
roles = {name: Rol.objects.get_or_create(nombre=name)[0] for name in ROLES}

# 2) Módulos base (añadidos 'cultivos' y 'variedades' para controlar catálogo)
MODULOS = [
    'usuarios', # Controla el acceso a los usuarios
    'parcelas', # Controla el acceso a las parcelas
    'cultivos', # Controla el acceso a los cultivos
    'variedades', # Controla el acceso a las variedades
    'etapas',    # Controla el acceso a las etapas
    'reglas',    # Controla el acceso a las reglas por etapa
    'planes', # Controla el acceso a los planes
    'sensores', # Controla el acceso a los sensores
    'recomendaciones', # Controla el acceso a las recomendaciones
    'tareas', # Controla el acceso a las tareas
    'alertas', # Controla el acceso a las alertas
    'nodos', # Controla el acceso a los nodos
    'reportes', # Controla el acceso a los reportes
    'administracion', # Controla el acceso a la administración
    'tecnicos', # Controla el acceso a los técnicos
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
    },
    'agricultor': {
        'parcelas':       ['ver', 'crear', 'actualizar'],
        'cultivos':       ['ver'],
        'variedades':     ['ver'],
        'etapas':         ['ver'],
        'reglas':         ['ver'],
        'planes':         ['ver', 'crear'],
        'sensores':       ['ver'],
        'tareas':         ['ver', 'crear', 'actualizar'],
        'alertas':        ['ver'],
        'reportes':       ['ver'],
        'nodos':          ['ver'],
        'recomendaciones':['ver'],
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

parcela1, _ = Parcela.objects.get_or_create(
    usuario=agri, nombre="Parcela Demo 1",
    defaults={
        "ubicacion": "Valle Central",
        "tamano_hectareas": 5.0,
        "latitud": -12.0464,
        "longitud": -77.0428,
        "altitud": 120.0,
        "cultivo": maiz,
        "variedad": maiz_blanco,
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
        "cultivo": papaya,
        "variedad": papaya_red,
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
        "cultivo": palta,
        "variedad": palta_hass,
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
        "cultivo": palta,
        "variedad": palta_hass,
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
        "cultivo": papaya,
        "variedad": papaya_red,
    }
)

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
Prospecto.objects.all().delete()

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
    "Seed OK: roles, módulos, operaciones, permisos, planes, usuarios, parcelas, MongoDB y nodos."
)