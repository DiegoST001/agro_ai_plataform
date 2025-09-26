import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'agro_ai_platform.settings')
django.setup()
from datetime import datetime, timezone
from django.conf import settings
from users.models import Rol, Modulo, Operacion, RolesOperaciones
from plans.models import Plan
from authentication.models import User
from parcels.models import Parcela
from recommendations.models import Recommendation
from rest_framework.authtoken.models import Token

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
        "coordenadas": "-12.0464,-77.0428",
        "altitud": 120.0,
        "tipo_cultivo": "Maíz",
    }
)
parcela2, _ = Parcela.objects.get_or_create(
    usuario=agri, nombre="Parcela Demo 2",
    defaults={
        "ubicacion": "Costa Norte",
        "tamano_hectareas": 12.5,
        "coordenadas": "-5.1945,-80.6328",
        "altitud": 45.0,
        "tipo_cultivo": "Arroz",
    }
)
parcela3, _ = Parcela.objects.get_or_create(
    usuario=admin, nombre="Parcela Admin 1",
    defaults={
        "ubicacion": "Sierra Sur",
        "tamano_hectareas": 3.2,
        "coordenadas": "-13.1631,-72.5450",
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

# 9) MongoDB: telemetría demo
try:
    from pymongo import MongoClient
    import datetime as dt

    client = MongoClient(settings.MONGO_URL)
    mdb = client[settings.MONGO_DB]
    readings = mdb.sensor_readings
    # índices básicos
    readings.create_index([("parcela_id", 1)])
    readings.create_index([("timestamp", -1)])

    # upsert simple: evitamos duplicar si ya insertamos
    if readings.count_documents({"seed_tag": "demo"}) == 0:
        docs = [
            {
                "seed_tag": "demo",
                "parcela_id": parcela1.id,
                "usuario": agri.username,
                "sensor": "soil_moisture",
                "unidad": "%",
                "valor": v,
                "timestamp": dt.datetime.utcnow() - dt.timedelta(minutes=i*10),
            }
            for i, v in enumerate([32.1, 33.4, 31.8, 34.2, 35.0])
        ] + [
            {
                "seed_tag": "demo",
                "parcela_id": parcela2.id,
                "usuario": agri.username,
                "sensor": "temp_ambiente",
                "unidad": "C",
                "valor": v,
                "timestamp": dt.datetime.utcnow() - dt.timedelta(minutes=i*15),
            }
            for i, v in enumerate([24.0, 24.6, 25.2, 26.1])
        ]
        readings.insert_many(docs)
        print("MongoDB: sensor_readings insertados.")
    else:
        print("MongoDB: seed_tag=demo ya existe, no se duplica.")

except ImportError:
    print("Nota: pymongo no instalado. Ejecuta: pip install pymongo")
except Exception as e:
    print(f"MongoDB: error al insertar datos demo -> {e}")

print('Seed OK: roles, módulos, operaciones, permisos, planes, usuarios, parcelas y MongoDB.')