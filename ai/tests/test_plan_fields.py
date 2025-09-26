from plans.models import Plan
def test_plan_defaults(db):
    p = Plan.objects.create(
        nombre="Tmp",
        descripcion="tmp",
        frecuencia_minutos=None,
        veces_por_dia=3,
        horarios_por_defecto=["07:00","15:00","22:00"],
        limite_lecturas_dia=8,
        precio=0
    )
    assert p.veces_por_dia in (3,6,8)
    assert len(p.horarios_por_defecto) == p.veces_por_dia