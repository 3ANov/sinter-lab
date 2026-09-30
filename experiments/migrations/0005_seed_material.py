from decimal import Decimal
from django.db import migrations


def seed_material(apps, schema_editor):
    alias = schema_editor.connection.alias
    material = apps.get_model('experiments', 'Material').objects.using(alias).create(
        name='Карбид вольфрама и никель',
        description='Порошковая прессовка, состоящая из карбида вольфрама и никеля',
    )
    apps.get_model('experiments', 'CoefficientSet').objects.using(alias).create(
        material=material, version=1,
        a0=Decimal('-17.46'), a1=Decimal('-0.00622'), a2=Decimal('0.04293'),
        a3=Decimal('0.000015'), a4=Decimal('-0.000014'), a5=Decimal('-0.000000005'),
    )


class Migration(migrations.Migration):
    dependencies = [('experiments', '0004_create_computation_run')]
    operations = [migrations.RunPython(seed_material, migrations.RunPython.noop)]
