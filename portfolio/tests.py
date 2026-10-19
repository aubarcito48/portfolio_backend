from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.db import IntegrityError, connection, transaction
from django.test import TestCase, TransactionTestCase, override_settings

from .models import Perfil, Tecnologia


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
