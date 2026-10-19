from django.db import migrations


def create_initial_profile(apps, schema_editor):
    Perfil = apps.get_model('portfolio', 'Perfil')
    database = schema_editor.connection.alias
    Perfil.objects.using(database).get_or_create(
        singleton_key=1,
        defaults={
            'name': 'Nahuel Argandoña',
            'professional_title': (
                'Full-Stack Developer | Software Development | QA & Testing'
            ),
            'biography': (
                'Soy desarrollador de software de Córdoba, Argentina, y '
                'actualmente curso la Tecnicatura Superior en Desarrollo de '
                'Software en el Instituto Superior Politécnico de Córdoba '
                '(ISPC).\n\n'
                'Me interesa construir aplicaciones web, resolver problemas '
                'técnicos, integrar APIs y profundizar en la calidad del '
                'software y las pruebas automatizadas. Mi recorrido incluye '
                'tecnologías frontend y backend, desarrollo con WordPress y '
                'soporte técnico informático.\n\n'
                'Hoy estoy enfocado en seguir creciendo como desarrollador y '
                'contribuir a proyectos reales.'
            ),
            'location': 'Córdoba, Argentina',
            'image_url': '/assets/nahuel.jpg',
            'is_published': True,
        },
    )


def remove_initial_profile(apps, schema_editor):
    Perfil = apps.get_model('portfolio', 'Perfil')
    database = schema_editor.connection.alias
    Perfil.objects.using(database).filter(singleton_key=1).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('portfolio', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(create_initial_profile, remove_initial_profile),
    ]
