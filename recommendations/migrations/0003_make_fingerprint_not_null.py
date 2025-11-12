from django.db import migrations, models
import uuid

def fill_and_assert(apps, schema_editor):
    Recommendation = apps.get_model('recommendations', 'Recommendation')
    existing = set(
        Recommendation.objects.exclude(fingerprint__isnull=True).values_list('fingerprint', flat=True)
    )
    # Rellenar NULL o cadenas vacías
    to_update = Recommendation.objects.filter(models.Q(fingerprint__isnull=True) | models.Q(fingerprint=''))
    for obj in to_update:
        fp = uuid.uuid4().hex
        while fp in existing:
            fp = uuid.uuid4().hex
        obj.fingerprint = fp
        obj.save(update_fields=['fingerprint'])
        existing.add(fp)

class Migration(migrations.Migration):

    dependencies = [
        ('recommendations', '0002_alter_recommendation_options_recommendation_code_and_more'),
    ]

    operations = [
        migrations.RunPython(fill_and_assert, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='recommendation',
            name='fingerprint',
            field=models.CharField(max_length=32, unique=True, editable=False),
        ),
    ]