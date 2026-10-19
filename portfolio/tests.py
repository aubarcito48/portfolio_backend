from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.db import IntegrityError, connection, transaction
from django.test import TestCase, TransactionTestCase, override_settings

from .models import Perfil


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
