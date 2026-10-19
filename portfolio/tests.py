from datetime import date

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.db import IntegrityError, connection, transaction
from django.urls import reverse
from django.test import TestCase, TransactionTestCase, override_settings

from .models import (
    Enlace,
    EnlaceProyecto,
    Experiencia,
    Formacion,
    Perfil,
    Proyecto,
    Tecnologia,
)


class PostgreSQLPersistenceTests(TransactionTestCase):
    def test_record_persists_after_reopening_database_connection(self):
        self.assertEqual(connection.vendor, 'postgresql')

        record = ContentType.objects.create(
            app_label='portfolio',
            model='persistence_probe',
        )
        connection.close()

        persisted_record = ContentType.objects.get(pk=record.pk)
        self.assertEqual(persisted_record.model, 'persistence_probe')

    @override_settings(CORS_ALLOWED_ORIGINS=['http://localhost:4200'])
    def test_allows_local_angular_origin(self):
        response = self.client.get(
            '/admin/login/',
            HTTP_ORIGIN='http://localhost:4200',
        )

        self.assertEqual(
            response.headers.get('Access-Control-Allow-Origin'),
            'http://localhost:4200',
        )

    @override_settings(CORS_ALLOWED_ORIGINS=['http://localhost:4200'])
    def test_rejects_unconfigured_origin(self):
        response = self.client.get(
            '/admin/login/',
            HTTP_ORIGIN='http://malicious.example',
        )

        self.assertNotIn('Access-Control-Allow-Origin', response.headers)


class PerfilApiTests(TestCase):
    def test_returns_published_profile_using_frontend_field_names(self):
        response = self.client.get('/api/v1/perfil/')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            set(response.json()),
            {'name', 'specialty', 'biography', 'location', 'photo'},
        )
        self.assertEqual(response.json()['name'], 'Nahuel Argandoña')
        self.assertEqual(
            response.json()['specialty'],
            'Full-Stack Developer | Software Development | QA & Testing',
        )
        self.assertEqual(
            response.json()['biography'],
            (
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
        )
        self.assertEqual(response.json()['location'], 'Córdoba, Argentina')
        self.assertEqual(response.json()['photo'], '/assets/nahuel.jpg')

    def test_returns_documented_json_404_when_profile_is_missing(self):
        Perfil.objects.all().delete()

        response = self.client.get('/api/v1/perfil/')

        self.assertEqual(response.status_code, 404)
        self.assertEqual(
            response.json(),
            {'detail': 'No hay un perfil publicado.'},
        )

    def test_returns_documented_json_404_when_profile_is_unpublished(self):
        perfil = Perfil.objects.get()
        perfil.is_published = False
        perfil.save()

        response = self.client.get('/api/v1/perfil/')

        self.assertEqual(response.status_code, 404)
        self.assertEqual(
            response.json(),
            {'detail': 'No hay un perfil publicado.'},
        )

    def test_orm_rejects_a_second_profile(self):
        with self.assertRaisesMessage(
            ValidationError,
            'Solo puede existir un perfil.',
        ):
            Perfil.objects.create(
                name='Segundo perfil',
                professional_title='Título',
                biography='Biografía',
                location='Córdoba',
                image_url='/assets/segundo.jpg',
            )

    def test_database_rejects_a_second_profile_from_bulk_orm_create(self):
        second_profile = Perfil(
            name='Segundo perfil',
            professional_title='Título',
            biography='Biografía',
            location='Córdoba',
            image_url='/assets/segundo.jpg',
        )

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Perfil.objects.bulk_create([second_profile])


class TecnologiaApiTests(TestCase):
    def setUp(self):
        Tecnologia.objects.all().delete()

    def create_tecnologia(
        self,
        name,
        category,
        order=0,
        is_published=True,
        url=None,
    ):
        return Tecnologia.objects.create(
            name=name,
            category=category,
            order=order,
            is_published=is_published,
            url=url
            or f"https://docs.example.com/{name.lower().replace(' ', '-')}",
        )

    def test_returns_published_technologies_grouped_by_category_and_order(self):
        self.create_tecnologia('JavaScript', 'Frontend', order=2)
        first = self.create_tecnologia('Angular', 'Frontend', order=1)
        tied = self.create_tecnologia('TypeScript', 'Frontend', order=1)
        self.create_tecnologia('Django', 'Backend', order=4)
        self.create_tecnologia(
            'Draft framework',
            'Backend',
            order=3,
            is_published=False,
        )

        response = self.client.get('/api/v1/tecnologias/')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            [
                {
                    'name': 'Frontend',
                    'technologies': [
                        {
                            'name': first.name,
                            'url': first.url,
                        },
                        {
                            'name': tied.name,
                            'url': tied.url,
                        },
                        {
                            'name': 'JavaScript',
                            'url': 'https://docs.example.com/javascript',
                        },
                    ],
                },
                {
                    'name': 'Backend',
                    'technologies': [
                        {
                            'name': 'Django',
                            'url': 'https://docs.example.com/django',
                        },
                    ],
                },
            ],
        )

    def test_resolves_equal_order_using_ascending_id(self):
        first = self.create_tecnologia('First', 'Frontend', order=3)
        second = self.create_tecnologia('Second', 'Frontend', order=3)

        response = self.client.get('/api/v1/tecnologias/')

        self.assertEqual(
            [item['name'] for item in response.json()[0]['technologies']],
            [first.name, second.name],
        )

    def test_returns_empty_list_when_there_are_no_published_technologies(self):
        self.create_tecnologia(
            'Draft',
            'Backend',
            is_published=False,
        )

        response = self.client.get('/api/v1/tecnologias/')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [])

    def test_rejects_duplicate_name_within_category_case_insensitively(self):
        self.create_tecnologia('Python', 'Backend')

        with self.assertRaises(ValidationError):
            self.create_tecnologia('python', 'backend')

    def test_allows_same_name_in_different_categories(self):
        self.create_tecnologia('Python', 'Backend')
        self.create_tecnologia('Python', 'Data science')

    def test_database_rejects_duplicate_name_in_category_from_bulk_create(self):
        self.create_tecnologia('Python', 'Backend')
        duplicate = Tecnologia(
            name='python',
            category='backend',
            url='https://docs.example.com/python',
        )

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Tecnologia.objects.bulk_create([duplicate])


class ExperienciaApiTests(TestCase):
    def create_experiencia(
        self,
        title,
        organization,
        start_date,
        end_date=None,
        is_current=False,
        order=0,
        is_published=True,
    ):
        return Experiencia.objects.create(
            title=title,
            organization=organization,
            description=f'Descripción de {title}.',
            start_date=start_date,
            end_date=end_date,
            is_current=is_current,
            order=order,
            is_published=is_published,
        )

    def test_returns_only_published_experiences_in_order(self):
        self.create_experiencia(
            'Experiencia finalizada',
            'Organización anterior',
            date(2020, 1, 1),
            end_date=date(2021, 6, 30),
            order=2,
        )
        current = self.create_experiencia(
            'Experiencia actual',
            'Organización actual',
            date(2022, 3, 1),
            is_current=True,
            order=1,
        )
        self.create_experiencia(
            'Experiencia no publicada',
            'Borrador',
            date(2024, 1, 1),
            is_current=True,
            order=0,
            is_published=False,
        )

        response = self.client.get('/api/v1/experiencias/')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            [
                {
                    'title': 'Experiencia actual',
                    'organization': 'Organización actual',
                    'description': 'Descripción de Experiencia actual.',
                    'startDate': '2022-03-01',
                    'endDate': None,
                    'isCurrent': True,
                },
                {
                    'title': 'Experiencia finalizada',
                    'organization': 'Organización anterior',
                    'description': 'Descripción de Experiencia finalizada.',
                    'startDate': '2020-01-01',
                    'endDate': '2021-06-30',
                    'isCurrent': False,
                },
            ],
        )
        self.assertIsNone(response.json()[0]['endDate'])

    def test_returns_empty_list_when_no_experiences_are_published(self):
        self.create_experiencia(
            'Experiencia borrador',
            'Organización',
            date(2024, 1, 1),
            is_current=True,
            is_published=False,
        )

        response = self.client.get('/api/v1/experiencias/')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [])

    def test_resolves_equal_order_using_ascending_id(self):
        first = self.create_experiencia(
            'Primera',
            'Organización',
            date(2020, 1, 1),
            is_current=True,
            order=1,
        )
        second = self.create_experiencia(
            'Segunda',
            'Organización',
            date(2021, 1, 1),
            is_current=True,
            order=1,
        )

        response = self.client.get('/api/v1/experiencias/')

        self.assertEqual(
            [item['title'] for item in response.json()],
            [first.title, second.title],
        )

    def test_rejects_end_date_before_start_date(self):
        with self.assertRaises(ValidationError):
            self.create_experiencia(
                'Fechas inválidas',
                'Organización',
                date(2023, 1, 1),
                end_date=date(2022, 12, 31),
            )

    def test_rejects_current_experience_with_end_date(self):
        with self.assertRaises(ValidationError):
            self.create_experiencia(
                'Empleo actual inválido',
                'Organización',
                date(2023, 1, 1),
                end_date=date(2024, 1, 1),
                is_current=True,
            )

    def test_database_rejects_invalid_date_range_from_bulk_create(self):
        invalid_experience = Experiencia(
            title='Fechas inválidas',
            organization='Organización',
            description='Descripción',
            start_date=date(2023, 1, 1),
            end_date=date(2022, 12, 31),
        )

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Experiencia.objects.bulk_create([invalid_experience])

    def test_database_rejects_current_experience_with_end_date_from_bulk_create(
        self,
    ):
        invalid_experience = Experiencia(
            title='Empleo actual inválido',
            organization='Organización',
            description='Descripción',
            start_date=date(2023, 1, 1),
            end_date=date(2024, 1, 1),
            is_current=True,
        )

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Experiencia.objects.bulk_create([invalid_experience])


class FormacionApiTests(TestCase):
    def create_formacion(
        self,
        name,
        institution,
        type,
        status,
        start_date,
        end_date=None,
        url='',
        order=0,
        is_published=True,
    ):
        return Formacion.objects.create(
            name=name,
            institution=institution,
            type=type,
            status=status,
            start_date=start_date,
            end_date=end_date,
            url=url,
            order=order,
            is_published=is_published,
        )

    def test_returns_published_studies_and_certifications_in_order(self):
        self.create_formacion(
            name='Tecnicatura Superior en Desarrollo de Software',
            institution='Instituto Superior Politécnico de Córdoba (ISPC)',
            type=Formacion.Type.STUDY,
            status=Formacion.Status.IN_PROGRESS,
            start_date=date(2022, 3, 1),
            order=2,
        )
        certification = self.create_formacion(
            name='Junior Full Stack Developer',
            institution='Instituto Superior Politécnico de Córdoba (ISPC)',
            type=Formacion.Type.CERTIFICATION,
            status=Formacion.Status.COMPLETED,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 12, 1),
            url='https://example.com/certificate',
            order=1,
        )
        self.create_formacion(
            name='Formación borrador',
            institution='Institución',
            type=Formacion.Type.STUDY,
            status=Formacion.Status.IN_PROGRESS,
            start_date=date(2025, 1, 1),
            order=0,
            is_published=False,
        )

        response = self.client.get('/api/v1/formacion/')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            [
                {
                    'name': 'Junior Full Stack Developer',
                    'institution': 'Instituto Superior Politécnico de Córdoba (ISPC)',
                    'type': 'certification',
                    'status': 'completed',
                    'startDate': '2024-01-01',
                    'endDate': '2024-12-01',
                    'url': 'https://example.com/certificate',
                },
                {
                    'name': 'Tecnicatura Superior en Desarrollo de Software',
                    'institution': 'Instituto Superior Politécnico de Córdoba (ISPC)',
                    'type': 'study',
                    'status': 'in_progress',
                    'startDate': '2022-03-01',
                    'endDate': None,
                    'url': None,
                },
            ],
        )
        self.assertEqual(response.json()[0]['name'], certification.name)

    def test_returns_empty_list_when_no_education_is_published(self):
        self.create_formacion(
            name='Estudio borrador',
            institution='Institución',
            type=Formacion.Type.STUDY,
            status=Formacion.Status.IN_PROGRESS,
            start_date=date(2025, 1, 1),
            is_published=False,
        )

        response = self.client.get('/api/v1/formacion/')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [])

    def test_resolves_equal_order_using_ascending_id(self):
        first = self.create_formacion(
            'Primero',
            'Institución',
            Formacion.Type.STUDY,
            Formacion.Status.IN_PROGRESS,
            date(2023, 1, 1),
            order=1,
        )
        second = self.create_formacion(
            'Segundo',
            'Institución',
            Formacion.Type.STUDY,
            Formacion.Status.IN_PROGRESS,
            date(2024, 1, 1),
            order=1,
        )

        response = self.client.get('/api/v1/formacion/')

        self.assertEqual(
            [item['name'] for item in response.json()],
            [first.name, second.name],
        )

    def test_rejects_end_date_before_start_date(self):
        with self.assertRaises(ValidationError):
            self.create_formacion(
                name='Fechas inválidas',
                institution='Institución',
                type=Formacion.Type.STUDY,
                status=Formacion.Status.COMPLETED,
                start_date=date(2024, 1, 1),
                end_date=date(2023, 12, 31),
            )

    def test_rejects_in_progress_education_with_end_date(self):
        with self.assertRaises(ValidationError):
            self.create_formacion(
                name='Estudio en curso inválido',
                institution='Institución',
                type=Formacion.Type.STUDY,
                status=Formacion.Status.IN_PROGRESS,
                start_date=date(2024, 1, 1),
                end_date=date(2024, 12, 31),
            )

    def test_rejects_completed_education_without_end_date(self):
        with self.assertRaises(ValidationError):
            self.create_formacion(
                name='Formación finalizada inválida',
                institution='Institución',
                type=Formacion.Type.CERTIFICATION,
                status=Formacion.Status.COMPLETED,
                start_date=date(2024, 1, 1),
            )

    def test_rejects_invalid_optional_url(self):
        with self.assertRaises(ValidationError):
            self.create_formacion(
                name='URL inválida',
                institution='Institución',
                type=Formacion.Type.CERTIFICATION,
                status=Formacion.Status.IN_PROGRESS,
                start_date=date(2024, 1, 1),
                url='esto-no-es-una-url',
            )

    def test_database_rejects_completed_record_without_end_date(self):
        invalid_record = Formacion(
            name='Formación inválida',
            institution='Institución',
            type=Formacion.Type.STUDY,
            status=Formacion.Status.COMPLETED,
            start_date=date(2024, 1, 1),
        )

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Formacion.objects.bulk_create([invalid_record])


class ProyectoApiTests(TestCase):
    def setUp(self):
        Proyecto.objects.all().delete()

    def create_project(
        self,
        title,
        slug,
        order=0,
        is_published=True,
        demo_url='',
        repository_url='',
        image_url='',
    ):
        return Proyecto.objects.create(
            title=title,
            slug=slug,
            summary=f'Resumen de {title}.',
            description=f'Descripción de {title}.',
            project_type='Proyecto en equipo',
            image_url=image_url,
            image_alt=f'Imagen de {title}',
            demo_url=demo_url,
            repository_url=repository_url,
            order=order,
            is_published=is_published,
        )

    def create_technology(self, name, published=True):
        return Tecnologia.objects.create(
            name=name,
            category='Proyecto',
            url=f'https://docs.example.com/{name.lower()}',
            is_published=published,
        )

    def test_list_returns_published_projects_with_only_published_technologies(self):
        later = self.create_project('Proyecto tardío', 'proyecto-tardio', order=2)
        first = self.create_project(
            'Proyecto primero',
            'proyecto-primero',
            order=1,
            demo_url='https://demo.example.com',
            repository_url='https://github.com/example/project',
            image_url='/assets/project.png',
        )
        draft = self.create_project(
            'Proyecto borrador',
            'proyecto-borrador',
            order=0,
            is_published=False,
        )
        published_technology = self.create_technology('Django')
        unpublished_technology = self.create_technology(
            'DraftTech',
            published=False,
        )
        first.technologies.add(published_technology, unpublished_technology)
        EnlaceProyecto.objects.create(
            project=first,
            label='Frontend',
            url='https://github.com/example/frontend',
        )
        draft.technologies.add(published_technology)

        response = self.client.get('/api/v1/proyectos/')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            [project['slug'] for project in response.json()],
            [first.slug, later.slug],
        )
        self.assertEqual(
            response.json()[0],
            {
                'name': 'Proyecto primero',
                'slug': 'proyecto-primero',
                'summary': 'Resumen de Proyecto primero.',
                'type': 'Proyecto en equipo',
                'image': '/assets/project.png',
                'imageAlt': 'Imagen de Proyecto primero',
                'description': 'Descripción de Proyecto primero.',
                'technologies': ['Django'],
                'links': [
                    {'label': 'Ver demo', 'url': 'https://demo.example.com'},
                    {
                        'label': 'Repositorio',
                        'url': 'https://github.com/example/project',
                    },
                    {
                        'label': 'Frontend',
                        'url': 'https://github.com/example/frontend',
                    },
                ],
            },
        )
        self.assertNotIn(unpublished_technology.name, response.content.decode())
        self.assertNotIn(draft.title, response.content.decode())

    def test_detail_returns_published_project(self):
        project = self.create_project('Proyecto publicado', 'publicado')
        technology = self.create_technology('Python')
        project.technologies.add(technology)

        response = self.client.get('/api/v1/proyectos/publicado/')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['slug'], 'publicado')
        self.assertEqual(response.json()['technologies'], ['Python'])

    def test_detail_returns_404_for_missing_slug(self):
        response = self.client.get('/api/v1/proyectos/no-existe/')

        self.assertEqual(response.status_code, 404)
        self.assertEqual(
            response.json(),
            {'detail': 'No se encontró el proyecto publicado.'},
        )

    def test_detail_returns_404_for_unpublished_project(self):
        self.create_project(
            'Proyecto borrador',
            'borrador',
            is_published=False,
        )

        response = self.client.get('/api/v1/proyectos/borrador/')

        self.assertEqual(response.status_code, 404)
        self.assertEqual(
            response.json(),
            {'detail': 'No se encontró el proyecto publicado.'},
        )

    def test_list_returns_empty_list_when_no_projects_are_published(self):
        self.create_project(
            'Proyecto borrador',
            'borrador',
            is_published=False,
        )

        response = self.client.get('/api/v1/proyectos/')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [])

    def test_rejects_duplicate_slug(self):
        self.create_project('Primero', 'proyecto')

        with self.assertRaises(ValidationError):
            self.create_project('Duplicado', 'proyecto')

    def test_database_rejects_duplicate_slug_from_bulk_create(self):
        self.create_project('Primero', 'proyecto')
        duplicate = Proyecto(
            title='Duplicado',
            slug='proyecto',
            summary='Resumen',
            description='Descripción',
            project_type='Proyecto en equipo',
        )

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Proyecto.objects.bulk_create([duplicate])

    def test_rejects_invalid_optional_urls(self):
        with self.assertRaises(ValidationError):
            self.create_project(
                'URL inválida',
                'url-invalida',
                demo_url='esto-no-es-una-url',
            )

    def test_accepts_frontend_relative_image_path(self):
        project = self.create_project(
            'Imagen local',
            'imagen-local',
            image_url='/assets/project.png',
        )

        self.assertEqual(project.image_url, '/assets/project.png')

    def test_list_does_not_duplicate_project_with_multiple_technologies(self):
        project = self.create_project('Proyecto', 'proyecto')
        project.technologies.add(
            self.create_technology('Python'),
            self.create_technology('Django'),
        )

        response = self.client.get('/api/v1/proyectos/')

        self.assertEqual(
            [item['slug'] for item in response.json()],
            ['proyecto'],
        )


class EnlaceApiTests(TestCase):
    def setUp(self):
        Enlace.objects.all().delete()

    def create_enlace(
        self,
        label,
        type,
        url,
        order=0,
        is_published=True,
    ):
        return Enlace.objects.create(
            label=label,
            type=type,
            url=url,
            order=order,
            is_published=is_published,
        )

    def test_returns_only_published_links_with_public_fields_in_order(self):
        second = self.create_enlace(
            'LinkedIn',
            'linkedin',
            'https://www.linkedin.com/in/example/',
            order=2,
        )
        first = self.create_enlace(
            'GitHub',
            'github',
            'https://github.com/example',
            order=1,
        )
        self.create_enlace(
            'Borrador',
            'other',
            'https://example.com/draft',
            order=0,
            is_published=False,
        )

        response = self.client.get('/api/v1/enlaces/')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            [
                {'label': first.label, 'type': first.type, 'url': first.url},
                {'label': second.label, 'type': second.type, 'url': second.url},
            ],
        )
        self.assertEqual(
            set(response.json()[0]),
            {'label', 'type', 'url'},
        )

    def test_resolves_equal_order_using_ascending_id(self):
        first = self.create_enlace(
            'Primero',
            'other',
            'https://example.com/first',
        )
        second = self.create_enlace(
            'Segundo',
            'other',
            'https://example.com/second',
        )

        response = self.client.get('/api/v1/enlaces/')

        self.assertEqual(
            [item['label'] for item in response.json()],
            [first.label, second.label],
        )

    def test_returns_empty_list_when_no_links_are_published(self):
        self.create_enlace(
            'Borrador',
            'other',
            'https://example.com/draft',
            is_published=False,
        )

        response = self.client.get('/api/v1/enlaces/')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [])

    def test_rejects_invalid_url(self):
        with self.assertRaises(ValidationError):
            self.create_enlace('Inválido', 'other', 'esto-no-es-una-url')

    def test_rejects_non_http_protocol(self):
        with self.assertRaises(ValidationError):
            self.create_enlace('FTP', 'other', 'ftp://example.com/profile')

    def test_only_allows_get_requests(self):
        response = self.client.post('/api/v1/enlaces/')

        self.assertEqual(response.status_code, 405)


class DjangoAdminPermissionTests(TestCase):
    managed_models = (
        Perfil,
        Tecnologia,
        Experiencia,
        Formacion,
        Proyecto,
        Enlace,
    )

    def setUp(self):
        user_model = get_user_model()
        self.non_staff = user_model.objects.create_user(
            username='portfolio-non-staff',
        )
        self.staff_without_permissions = user_model.objects.create_user(
            username='portfolio-no-permissions',
            is_staff=True,
        )
        self.editor = user_model.objects.create_user(
            username='portfolio-editor',
            is_staff=True,
        )
        self.editor_group = Group.objects.get(name='Editores de contenido')
        self.editor.groups.add(self.editor_group)

    def admin_model_url(self, model, action):
        return reverse(f'admin:portfolio_{model._meta.model_name}_{action}')

    def test_anonymous_admin_access_redirects_to_login(self):
        response = self.client.get('/admin/')

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, '/admin/login/?next=/admin/')

    def test_non_staff_user_cannot_access_admin(self):
        self.client.force_login(self.non_staff)

        response = self.client.get('/admin/')

        self.assertEqual(response.status_code, 302)
        self.assertIn('/admin/login/', response.url)

    def test_staff_without_model_permissions_cannot_open_content_changelists(self):
        self.client.force_login(self.staff_without_permissions)

        index_response = self.client.get('/admin/')
        self.assertEqual(index_response.status_code, 302)
        self.assertIn('/admin/login/', index_response.url)

        for model in self.managed_models:
            with self.subTest(model=model.__name__):
                response = self.client.get(
                    self.admin_model_url(model, 'changelist')
                )
                self.assertEqual(response.status_code, 302)
                self.assertIn('/admin/login/', response.url)

    def test_user_with_model_scoped_permissions_cannot_access_other_models(self):
        scoped_user = get_user_model().objects.create_user(
            username='portfolio-scoped-editor',
            is_staff=True,
        )
        scoped_permissions = self.editor_group.permissions.filter(
            codename__in=('view_enlace', 'change_enlace'),
        )
        scoped_user.user_permissions.add(*scoped_permissions)
        self.client.force_login(scoped_user)

        allowed_response = self.client.get(
            self.admin_model_url(Enlace, 'changelist')
        )
        denied_response = self.client.get(
            self.admin_model_url(Proyecto, 'changelist')
        )
        denied_add_response = self.client.get(
            self.admin_model_url(Enlace, 'add')
        )

        self.assertEqual(allowed_response.status_code, 200)
        self.assertEqual(denied_response.status_code, 403)
        self.assertEqual(denied_add_response.status_code, 403)

    def test_editor_group_has_explicit_view_add_change_and_no_delete_permissions(self):
        expected_permissions = {
            f'{action}_{model._meta.model_name}'
            for model in (*self.managed_models, EnlaceProyecto)
            for action in ('view', 'add', 'change')
        }
        actual_permissions = set(
            self.editor_group.permissions.filter(
                content_type__app_label='portfolio',
            ).values_list('codename', flat=True)
        )

        self.assertSetEqual(actual_permissions, expected_permissions)

    def test_editor_can_view_and_open_add_pages_for_managed_models(self):
        self.client.force_login(self.editor)

        for model in self.managed_models:
            with self.subTest(model=model.__name__):
                changelist_response = self.client.get(
                    self.admin_model_url(model, 'changelist')
                )
                self.assertEqual(changelist_response.status_code, 200)

                add_response = self.client.get(
                    self.admin_model_url(model, 'add')
                )
                if model is Perfil and Perfil.objects.exists():
                    self.assertEqual(add_response.status_code, 403)
                else:
                    self.assertEqual(add_response.status_code, 200)

    def test_editor_can_unpublish_a_link_and_public_api_hides_it(self):
        link = Enlace.objects.get(type='github')
        self.client.force_login(self.editor)

        response = self.client.post(
            reverse(
                'admin:portfolio_enlace_change',
                args=(link.pk,),
            ),
            {
                'label': link.label,
                'type': link.type,
                'url': link.url,
                'order': link.order,
            },
        )

        self.assertEqual(response.status_code, 302)
        link.refresh_from_db()
        self.assertFalse(link.is_published)
        public_links = self.client.get('/api/v1/enlaces/').json()
        self.assertNotIn(link.url, [item['url'] for item in public_links])

    def test_editor_admin_changes_to_all_content_types_are_saved_and_public(self):
        self.client.force_login(self.editor)

        profile = Perfil.objects.get()
        profile_response = self.client.post(
            reverse('admin:portfolio_perfil_change', args=(profile.pk,)),
            {
                'name': 'Perfil actualizado desde Admin',
                'professional_title': profile.professional_title,
                'biography': profile.biography,
                'location': profile.location,
                'image_url': profile.image_url,
                'is_published': 'on',
            },
        )
        self.assertEqual(profile_response.status_code, 302)
        self.assertEqual(
            self.client.get('/api/v1/perfil/').json()['name'],
            'Perfil actualizado desde Admin',
        )

        technology_response = self.client.post(
            self.admin_model_url(Tecnologia, 'add'),
            {
                'name': 'Admin Published Technology',
                'category': 'Admin',
                'url': 'https://docs.example.com/admin-technology',
                'order': '30',
                'is_published': 'on',
            },
        )
        self.assertEqual(technology_response.status_code, 302)
        technologies = self.client.get('/api/v1/tecnologias/').json()
        self.assertIn(
            'Admin Published Technology',
            [
                item['name']
                for group in technologies
                for item in group['technologies']
            ],
        )

        experience_response = self.client.post(
            self.admin_model_url(Experiencia, 'add'),
            {
                'title': 'Experiencia desde Admin',
                'organization': 'Organización de prueba',
                'description': 'Descripción administrada.',
                'start_date': '2025-01-01',
                'end_date': '',
                'is_current': 'on',
                'order': '30',
                'is_published': 'on',
            },
        )
        self.assertEqual(experience_response.status_code, 302)
        experiences = self.client.get('/api/v1/experiencias/').json()
        self.assertIn(
            'Experiencia desde Admin',
            [item['title'] for item in experiences],
        )

        education_response = self.client.post(
            self.admin_model_url(Formacion, 'add'),
            {
                'name': 'Formación desde Admin',
                'institution': 'Institución de prueba',
                'type': Formacion.Type.STUDY,
                'status': Formacion.Status.IN_PROGRESS,
                'start_date': '2025-01-01',
                'end_date': '',
                'url': '',
                'order': '30',
                'is_published': 'on',
            },
        )
        self.assertEqual(education_response.status_code, 302)
        education = self.client.get('/api/v1/formacion/').json()
        self.assertIn(
            'Formación desde Admin',
            [item['name'] for item in education],
        )

        project_response = self.client.post(
            self.admin_model_url(Proyecto, 'add'),
            {
                'title': 'Proyecto desde Admin',
                'slug': 'proyecto-desde-admin',
                'summary': 'Resumen administrado.',
                'description': 'Descripción administrada.',
                'project_type': 'Proyecto personal',
                'image_url': '',
                'image_alt': '',
                'demo_url': '',
                'demo_label': 'Ver demo',
                'repository_url': '',
                'repository_label': 'Repositorio',
                'technologies': [],
                'order': '30',
                'is_published': 'on',
                'additional_links-TOTAL_FORMS': '1',
                'additional_links-INITIAL_FORMS': '0',
                'additional_links-MIN_NUM_FORMS': '0',
                'additional_links-MAX_NUM_FORMS': '1000',
                'additional_links-0-label': 'Frontend del proyecto',
                'additional_links-0-url': 'https://example.com/project-frontend',
                'additional_links-0-order': '0',
            },
        )
        self.assertEqual(project_response.status_code, 302)
        self.assertEqual(
            self.client.get(
                '/api/v1/proyectos/proyecto-desde-admin/'
            ).json()['links'],
            [
                {
                    'label': 'Frontend del proyecto',
                    'url': 'https://example.com/project-frontend',
                }
            ],
        )

        link_response = self.client.post(
            self.admin_model_url(Enlace, 'add'),
            {
                'label': 'Enlace desde Admin',
                'type': 'portfolio',
                'url': 'https://example.com/admin-link',
                'order': '30',
                'is_published': 'on',
            },
        )
        self.assertEqual(link_response.status_code, 302)
        links = self.client.get('/api/v1/enlaces/').json()
        self.assertIn(
            'https://example.com/admin-link',
            [item['url'] for item in links],
        )

        profile = Perfil.objects.get()
        self.assertEqual(
            self.client.post(
                reverse('admin:portfolio_perfil_change', args=(profile.pk,)),
                {
                    'name': profile.name,
                    'professional_title': profile.professional_title,
                    'biography': profile.biography,
                    'location': profile.location,
                    'image_url': profile.image_url,
                },
            ).status_code,
            302,
        )
        self.assertEqual(self.client.get('/api/v1/perfil/').status_code, 404)

        technology = Tecnologia.objects.get(name='Admin Published Technology')
        self.assertEqual(
            self.client.post(
                reverse(
                    'admin:portfolio_tecnologia_change',
                    args=(technology.pk,),
                ),
                {
                    'name': technology.name,
                    'category': technology.category,
                    'url': technology.url,
                    'order': technology.order,
                },
            ).status_code,
            302,
        )
        technologies = self.client.get('/api/v1/tecnologias/').json()
        self.assertNotIn(
            technology.name,
            [
                item['name']
                for group in technologies
                for item in group['technologies']
            ],
        )

        experience = Experiencia.objects.get(title='Experiencia desde Admin')
        self.assertEqual(
            self.client.post(
                reverse(
                    'admin:portfolio_experiencia_change',
                    args=(experience.pk,),
                ),
                {
                    'title': experience.title,
                    'organization': experience.organization,
                    'description': experience.description,
                    'start_date': experience.start_date.isoformat(),
                    'end_date': '',
                    'is_current': 'on',
                    'order': experience.order,
                },
            ).status_code,
            302,
        )
        experiences = self.client.get('/api/v1/experiencias/').json()
        self.assertNotIn(
            experience.title,
            [item['title'] for item in experiences],
        )

        education_record = Formacion.objects.get(name='Formación desde Admin')
        self.assertEqual(
            self.client.post(
                reverse(
                    'admin:portfolio_formacion_change',
                    args=(education_record.pk,),
                ),
                {
                    'name': education_record.name,
                    'institution': education_record.institution,
                    'type': education_record.type,
                    'status': education_record.status,
                    'start_date': education_record.start_date.isoformat(),
                    'end_date': '',
                    'url': '',
                    'order': education_record.order,
                },
            ).status_code,
            302,
        )
        education = self.client.get('/api/v1/formacion/').json()
        self.assertNotIn(
            education_record.name,
            [item['name'] for item in education],
        )

        project = Proyecto.objects.get(slug='proyecto-desde-admin')
        self.assertEqual(
            self.client.post(
                reverse(
                    'admin:portfolio_proyecto_change',
                    args=(project.pk,),
                ),
                {
                    'title': project.title,
                    'slug': project.slug,
                    'summary': project.summary,
                    'description': project.description,
                    'project_type': project.project_type,
                    'image_url': '',
                    'image_alt': '',
                    'demo_url': '',
                    'demo_label': project.demo_label,
                    'repository_url': '',
                    'repository_label': project.repository_label,
                    'technologies': [],
                    'order': project.order,
                    'additional_links-TOTAL_FORMS': '0',
                    'additional_links-INITIAL_FORMS': '0',
                    'additional_links-MIN_NUM_FORMS': '0',
                    'additional_links-MAX_NUM_FORMS': '1000',
                },
            ).status_code,
            302,
        )
        self.assertEqual(
            self.client.get(
                '/api/v1/proyectos/proyecto-desde-admin/'
            ).status_code,
            404,
        )

        link = Enlace.objects.get(type='portfolio')
        self.assertEqual(
            self.client.post(
                reverse('admin:portfolio_enlace_change', args=(link.pk,)),
                {
                    'label': link.label,
                    'type': link.type,
                    'url': link.url,
                    'order': link.order,
                },
            ).status_code,
            302,
        )
        links = self.client.get('/api/v1/enlaces/').json()
        self.assertNotIn(link.url, [item['url'] for item in links])

    def test_editor_cannot_delete_records_without_explicit_delete_permission(self):
        link = Enlace.objects.get(type='github')
        self.client.force_login(self.editor)

        response = self.client.post(
            reverse(
                'admin:portfolio_enlace_delete',
                args=(link.pk,),
            ),
        )

        self.assertEqual(response.status_code, 403)
        self.assertTrue(Enlace.objects.filter(pk=link.pk).exists())

    def test_superuser_can_delete_when_authorized(self):
        superuser = get_user_model().objects.create_superuser(
            username='portfolio-superuser',
            email='admin@example.com',
        )
        link = Enlace.objects.get(type='github')
        self.client.force_login(superuser)

        response = self.client.post(
            reverse(
                'admin:portfolio_enlace_delete',
                args=(link.pk,),
            ),
            {'post': 'yes'},
        )

        self.assertEqual(response.status_code, 302)
        self.assertFalse(Enlace.objects.filter(pk=link.pk).exists())

    def test_editor_profile_admin_preserves_singleton_restriction(self):
        self.client.force_login(self.editor)

        response = self.client.get(self.admin_model_url(Perfil, 'add'))

        self.assertEqual(response.status_code, 403)
        self.assertEqual(Perfil.objects.count(), 1)

    def test_admin_registrations_cover_all_managed_models(self):
        from .admin import portfolio_admin_site

        for model in self.managed_models:
            with self.subTest(model=model.__name__):
                self.assertIn(model, portfolio_admin_site._registry)
