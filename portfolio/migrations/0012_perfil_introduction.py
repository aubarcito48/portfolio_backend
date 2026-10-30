from django.db import migrations, models


def restore_introduction(apps, schema_editor):
    profile = apps.get_model('portfolio', 'Perfil')
    profile.objects.using(schema_editor.connection.alias).filter(
        singleton_key=1, name='Nahuel Argandoña', introduction='',
    ).update(introduction=(
        'Soy desarrollador de software de Córdoba, Argentina, y actualmente curso '
        'la Tecnicatura Superior en Desarrollo de Software en el Instituto '
        'Superior Politécnico de Córdoba (ISPC).'
    ))


class Migration(migrations.Migration):
    dependencies = [('portfolio', '0011_alter_enlace_url_alter_enlaceproyecto_url_and_more')]
    operations = [
        migrations.AddField(
            model_name='perfil', name='introduction',
            field=models.TextField(blank=True, default=''),
        ),
        migrations.RunPython(restore_introduction, migrations.RunPython.noop),
    ]
