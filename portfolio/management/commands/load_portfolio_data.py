from django.core.management.base import BaseCommand
from django.db import transaction

from portfolio.models import (
    Enlace,
    EnlaceProyecto,
    Perfil,
    Proyecto,
    Tecnologia,
)


PROFILE = {
    'name': 'Nahuel Argandoña',
    'professional_title': (
        'Full-Stack Developer | Software Development | QA & Testing'
    ),
    'biography': (
        'Soy desarrollador de software de Córdoba, Argentina, y actualmente '
        'curso la Tecnicatura Superior en Desarrollo de Software en el '
        'Instituto Superior Politécnico de Córdoba (ISPC).\n\n'
        'Me interesa construir aplicaciones web, resolver problemas técnicos, '
        'integrar APIs y profundizar en la calidad del software y las pruebas '
        'automatizadas. Mi recorrido incluye tecnologías frontend y backend, '
        'desarrollo con WordPress y soporte técnico informático.\n\n'
        'Hoy estoy enfocado en seguir creciendo como desarrollador y '
        'contribuir a proyectos reales.'
    ),
    'location': 'Córdoba, Argentina',
    'image_url': '/assets/nahuel.jpg',
    'is_published': True,
}

TECHNOLOGIES = (
    ('JavaScript', 'Frontend', 'https://developer.mozilla.org/en-US/docs/Web/JavaScript'),
    ('TypeScript', 'Frontend', 'https://www.typescriptlang.org/docs/'),
    ('Angular', 'Frontend', 'https://angular.dev/overview'),
    ('React', 'Frontend', 'https://react.dev/learn'),
    ('HTML5', 'Frontend', 'https://developer.mozilla.org/en-US/docs/Web/HTML'),
    ('CSS3', 'Frontend', 'https://developer.mozilla.org/en-US/docs/Web/CSS'),
    ('Tailwind CSS', 'Frontend', 'https://tailwindcss.com/docs'),
    ('Bootstrap', 'Frontend', 'https://getbootstrap.com/docs/'),
    ('Python', 'Backend', 'https://docs.python.org/3/'),
    ('Django', 'Backend', 'https://docs.djangoproject.com/en/stable/'),
    ('Node.js', 'Backend', 'https://nodejs.org/en/learn'),
    ('Express', 'Backend', 'https://expressjs.com/'),
    ('PHP', 'Backend', 'https://www.php.net/manual/en/'),
    ('WordPress', 'Backend', 'https://developer.wordpress.org/'),
    (
        'REST APIs',
        'Backend',
        'https://developer.mozilla.org/en-US/docs/Glossary/REST',
    ),
    ('MySQL', 'Bases de datos y herramientas', 'https://dev.mysql.com/doc/'),
    ('MongoDB', 'Bases de datos y herramientas', 'https://www.mongodb.com/docs/'),
    ('Git', 'Bases de datos y herramientas', 'https://git-scm.com/doc'),
    ('GitHub', 'Bases de datos y herramientas', 'https://docs.github.com/'),
    ('Cypress', 'Calidad de software', 'https://docs.cypress.io/'),
    ('Playwright', 'Calidad de software', 'https://playwright.dev/docs/intro'),
    ('HTML', 'Frontend', 'https://developer.mozilla.org/en-US/docs/Web/HTML'),
    ('CSS', 'Frontend', 'https://developer.mozilla.org/en-US/docs/Web/CSS'),
    ('AJAX', 'Backend', 'https://developer.mozilla.org/en-US/docs/Web/Guide/AJAX'),
)

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
        'summary': 'Actualización y reorganización del sitio institucional de la DGES.',
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
        'technologies': ('PHP', 'WordPress', 'HTML', 'CSS', 'REST APIs', 'AJAX'),
        'additional_links': (),
    },
)

PROFESSIONAL_LINKS = (
    {
        'label': 'GitHub',
        'type': 'github',
        'url': 'https://github.com/aubarcito48',
        'order': 0,
        'is_published': True,
    },
    {
        'label': 'LinkedIn',
        'type': 'linkedin',
        'url': 'https://www.linkedin.com/in/aubar48/',
        'order': 1,
        'is_published': True,
    },
)


class Command(BaseCommand):
    help = 'Crea o actualiza los datos públicos aprobados del portfolio.'

    def handle(self, *args, **options):
        with transaction.atomic():
            prepared = self._prepare_data()
            counts = self._apply_data(prepared)

        self.stdout.write(
            self.style.SUCCESS(
                'Carga inicial completada; se procesaron: '
                f"{counts['profile']} perfil, "
                f"{counts['technologies']} tecnologías, "
                f"{counts['projects']} proyectos y "
                f"{counts['links']} enlaces profesionales."
            )
        )
        self.stdout.write(
            'No se cargaron experiencias ni formaciones: faltan datos '
            'verificables aprobados (fechas y detalles).'
        )

    def _prepare_data(self):
        profile = Perfil.objects.filter(singleton_key=1).first()
        if profile is None:
            profile = Perfil(singleton_key=1, **PROFILE)
        for field, value in PROFILE.items():
            setattr(profile, field, value)
        profile.full_clean()

        technologies = []
        technology_by_name = {}
        for name, category, url in TECHNOLOGIES:
            technology = Tecnologia.objects.filter(
                name__iexact=name,
                category__iexact=category,
            ).first()
            if technology is None:
                technology = Tecnologia(
                    name=name,
                    category=category,
                    url=url,
                    order=len(technologies),
                    is_published=True,
                )
            else:
                technology.name = name
                technology.category = category
                technology.url = url
                technology.order = len(technologies)
                technology.is_published = True
            technology.full_clean()
            technologies.append(technology)
            technology_by_name[name] = technology

        projects = []
        additional_links = []
        for project_data in PROJECTS:
            data = project_data.copy()
            technology_names = data.pop('technologies')
            project_links = data.pop('additional_links')
            project = Proyecto.objects.filter(slug=data['slug']).first()
            if project is None:
                project = Proyecto(**data)
            else:
                for field, value in data.items():
                    setattr(project, field, value)
            project.full_clean()
            missing_technologies = set(technology_names) - set(
                technology_by_name
            )
            if missing_technologies:
                raise ValueError(
                    f"El proyecto {project.slug!r} referencia tecnologías "
                    f"inexistentes en la carga: {sorted(missing_technologies)}."
                )
            projects.append(
                (project, tuple(technology_by_name[name] for name in technology_names))
            )
            additional_links.extend(
                (project, label, url, order)
                for label, url, order in project_links
            )

        for project, label, url, order in additional_links:
            existing_link = None
            if project.pk is not None:
                existing_link = EnlaceProyecto.objects.filter(
                    project=project,
                    label=label,
                ).first()
            link = existing_link or EnlaceProyecto(
                project=project,
                label=label,
                url=url,
                order=order,
            )
            link.url = url
            link.order = order
            link.full_clean(exclude=('project',) if project.pk is None else ())

        professional_links = []
        for link_data in PROFESSIONAL_LINKS:
            link = Enlace.objects.filter(type=link_data['type']).order_by('id').first()
            if link is None:
                link = Enlace(**link_data)
            else:
                for field, value in link_data.items():
                    setattr(link, field, value)
            link.full_clean()
            professional_links.append(link)

        return {
            'profile': profile,
            'technologies': technologies,
            'projects': projects,
            'professional_links': professional_links,
            'additional_links': additional_links,
        }

    def _apply_data(self, prepared):
        profile = prepared['profile']
        profile.save()

        for technology in prepared['technologies']:
            technology.save()

        for project, technologies in prepared['projects']:
            project.save()
            project.technologies.set(technologies)

        self._apply_additional_links(prepared['additional_links'])

        for link in prepared['professional_links']:
            link.save()

        return {
            'profile': 1,
            'technologies': len(prepared['technologies']),
            'projects': len(prepared['projects']),
            'links': len(prepared['professional_links']),
        }

    def _apply_additional_links(self, additional_links):
        for project, label, url, order in additional_links:
            EnlaceProyecto.objects.update_or_create(
                project=project,
                label=label,
                defaults={'url': url, 'order': order},
            )
