from django.db import migrations


PROJECTS = (
    {
        'title': 'PintaEbook',
        'slug': 'pintaebook',
        'summary': (
            'Plataforma de libros y ebooks desarrollada por el equipo '
            'ISPC / ProCoders.'
        ),
        'description': (
            'Plataforma de libros y ebooks desarrollada como parte del equipo '
            'ISPC / ProCoders. El proyecto integra trabajo de frontend y '
            'backend, APIs, autenticación y funcionalidades asistidas por '
            'inteligencia artificial.'
        ),
        'project_type': 'Proyecto en equipo',
        'image_url': '/assets/pintaebook.png',
        'image_alt': (
            'Página de inicio de PintaEbook con su presentación y navegación'
        ),
        'demo_url': 'https://pinta-ebook-eta.vercel.app/',
        'demo_label': 'Ver demo',
        'repository_url': (
            'https://github.com/ISPC-ProCoders-2026/Pintaebook_backend'
        ),
        'repository_label': 'Backend',
        'order': 0,
        'is_published': True,
        'technologies': (
            'Angular',
            'Python',
            'Django',
            'REST APIs',
            'Git',
            'GitHub',
        ),
        'additional_links': (
            (
                'Frontend',
                'https://github.com/ISPC-ProCoders-2026/PintaEbook',
                0,
            ),
        ),
    },
    {
        'title': 'DGES',
        'slug': 'dges',
        'summary': (
            'Actualización y reorganización del sitio institucional de la DGES.'
        ),
        'description': (
            'Proyecto de actualización y reorganización del sitio institucional '
            'de la DGES, orientado a mejorar el acceso a la información, la '
            'experiencia de navegación y la adaptación a distintos dispositivos.'
        ),
        'project_type': 'Pasantía · Proyecto en equipo',
        'image_url': '/assets/dges.png',
        'image_alt': (
            'Página de inicio del sitio institucional de la Dirección General '
            'de Educación Superior'
        ),
        'demo_url': 'https://dges-cba.edu.ar/wp/',
        'demo_label': 'Ver sitio',
        'repository_url': 'https://github.com/ispc-pasantia-2025',
        'repository_label': 'Repositorio',
        'order': 1,
        'is_published': True,
        'technologies': (
            'PHP',
            'WordPress',
            'HTML',
            'CSS',
            'REST APIs',
            'AJAX',
        ),
        'additional_links': (),
    },
)

ADDITIONAL_TECHNOLOGIES = (
    ('HTML', 'Frontend', 'https://developer.mozilla.org/en-US/docs/Web/HTML'),
    ('CSS', 'Frontend', 'https://developer.mozilla.org/en-US/docs/Web/CSS'),
    ('AJAX', 'Backend', 'https://developer.mozilla.org/en-US/docs/Web/Guide/AJAX'),
)


def create_initial_projects(apps, schema_editor):
    Tecnologia = apps.get_model('portfolio', 'Tecnologia')
    Proyecto = apps.get_model('portfolio', 'Proyecto')
    EnlaceProyecto = apps.get_model('portfolio', 'EnlaceProyecto')
    database = schema_editor.connection.alias

    for index, (name, category, url) in enumerate(ADDITIONAL_TECHNOLOGIES, 21):
        Tecnologia.objects.using(database).get_or_create(
            name=name,
            category=category,
            defaults={
                'url': url,
                'order': index,
                'is_published': True,
            },
        )

    for project_data in PROJECTS:
        data = project_data.copy()
        technology_names = data.pop('technologies')
        additional_links = data.pop('additional_links')
        project, _ = Proyecto.objects.using(database).get_or_create(
            slug=data['slug'],
            defaults=data,
        )

        for technology_name in technology_names:
            technology = Tecnologia.objects.using(database).get(name=technology_name)
            project.technologies.add(technology)

        for label, url, order in additional_links:
            EnlaceProyecto.objects.using(database).get_or_create(
                project=project,
                label=label,
                defaults={'url': url, 'order': order},
            )


def remove_initial_projects(apps, schema_editor):
    Proyecto = apps.get_model('portfolio', 'Proyecto')
    Tecnologia = apps.get_model('portfolio', 'Tecnologia')
    database = schema_editor.connection.alias

    Proyecto.objects.using(database).filter(
        slug__in=[project['slug'] for project in PROJECTS]
    ).delete()
    Tecnologia.objects.using(database).filter(
        name__in=[technology[0] for technology in ADDITIONAL_TECHNOLOGIES]
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('portfolio', '0007_proyecto_enlaceproyecto'),
    ]

    operations = [
        migrations.RunPython(create_initial_projects, remove_initial_projects),
    ]
