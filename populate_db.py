import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'agro_ai_platform.settings')
django.setup()
from datetime import datetime, timezone
from django.conf import settings
from users.models import Rol, Modulo, Operacion, RolesOperaciones, PerfilUsuario
from plans.models import Plan
from authentication.models import User
from parcels.models import Parcela
from recommendations.models import Recommendation
from rest_framework.authtoken.models import Token
from nodes.models import Node, NodoSecundario

# Elimina perfiles y parcelas previos
PerfilUsuario.objects.all().delete()
Parcela.objects.all().delete()

# 1) Roles base
ROLES = ['agricultor', 'administrador', 'tecnico', 'superadmin']
roles = {name: Rol.objects.get_or_create(nombre=name)[0] for name in ROLES}

# 2) Módulos base
MODULOS = [
    'usuarios',
    'parcelas',
    'planes',
    'sensores',
    'recomendaciones',
    'tareas',
    'alertas',
    'nodos',
    'reportes',
    'administracion',
    'tecnicos',
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

# 4) Permisos por rol
MATRIZ = {
    'superadmin': {m: OPERACIONES for m in MODULOS},
    'administrador': {
        'usuarios':       ['ver', 'crear', 'actualizar', 'eliminar'],
        'parcelas':       ['ver', 'crear', 'actualizar', 'eliminar'],
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
        'tareas':   ['ver', 'actualizar'],
        'alertas':  ['ver', 'actualizar'],
        'reportes': ['ver'],
        'tecnicos': ['ver', 'actualizar'],
    },
    'agricultor': {
        'parcelas':       ['ver', 'crear', 'actualizar'],
        'planes':         ['ver', 'crear'],
        'sensores':       ['ver'],
        'tareas':         ['ver', 'crear', 'actualizar'],
        'alertas':        ['ver'],
        'reportes':       ['ver'],
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
    su = User.objects.create_superuser('superadmin', 'super@demo.com', '12345678')
    su.rol = roles['superadmin']
    su.save()
    usuarios_seed.append(su)
else:
    usuarios_seed.append(User.objects.get(username='superadmin'))

# administrador
if not User.objects.filter(username='admin1').exists():
    admin = User.objects.create_user(username='admin1', email='admin@demo.com', password='12345678', is_staff=True)
    admin.rol = roles['administrador']
    admin.save()
    usuarios_seed.append(admin)
else:
    usuarios_seed.append(User.objects.get(username='admin1'))

# técnico
if not User.objects.filter(username='tecnico1').exists():
    tec = User.objects.create_user(username='tecnico1', email='tec@demo.com', password='12345678')
    tec.rol = roles['tecnico']
    tec.save()
    usuarios_seed.append(tec)
else:
    usuarios_seed.append(User.objects.get(username='tecnico1'))

# agricultor
if not User.objects.filter(username='agricultor1').exists():
    agri = User.objects.create_user(username='agricultor1', email='agri@demo.com', password='12345678', is_active=True)
    agri.rol = roles['agricultor']
    agri.save()
    usuarios_seed.append(agri)
else:
    usuarios_seed.append(User.objects.get(username='agricultor1'))

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
        "tipo_cultivo": "Maíz",
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
        "tipo_cultivo": "Arroz",
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
        "tipo_cultivo": "Papa",
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

# 9) MongoDB: telemetría demo
try:
    from pymongo import MongoClient
    import datetime as dt

    client = MongoClient(settings.MONGO_URL)
    mdb = client[settings.MONGO_DB]
    readings = mdb.sensor_readings
    readings.create_index([("parcela_id", 1)])
    readings.create_index([("timestamp", -1)])

    if readings.count_documents({"seed_tag": "demo"}) == 0:
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

        readings.insert_many(docs)
        print("MongoDB: sensor_readings insertados.")
    else:
        print("MongoDB: seed_tag=demo ya existe, no se duplica.")
except ImportError:
    print("Nota: pymongo no instalado. Ejecuta: pip install pymongo")
except Exception as e:
    print(f"MongoDB: error al insertar datos demo -> {e}")

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

print(
    "Seed OK: roles, módulos, operaciones, permisos, planes, usuarios, parcelas, MongoDB y nodos."
)