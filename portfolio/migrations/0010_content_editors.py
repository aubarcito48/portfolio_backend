from django.db import migrations


EDITOR_GROUP_NAME = 'Editores de contenido'
MANAGED_MODELS = (
    'perfil',
    'tecnologia',
    'experiencia',
    'formacion',
    'proyecto',
    'enlace',
    'enlaceproyecto',
)
EDITOR_ACTIONS = ('view', 'add', 'change')


def configure_content_editors(apps, schema_editor):
    ContentType = apps.get_model('contenttypes', 'ContentType')
    Group = apps.get_model('auth', 'Group')
    Permission = apps.get_model('auth', 'Permission')
    database = schema_editor.connection.alias
    group, _ = Group.objects.using(database).get_or_create(
        name=EDITOR_GROUP_NAME,
    )
    permissions = []

    for model_name in MANAGED_MODELS:
        content_type, _ = ContentType.objects.using(database).get_or_create(
            app_label='portfolio',
            model=model_name,
        )
        for action in EDITOR_ACTIONS:
            codename = f'{action}_{model_name}'
            permission, _ = Permission.objects.using(database).get_or_create(
                content_type=content_type,
                codename=codename,
                defaults={'name': f'Can {action} {model_name}'},
            )
            permissions.append(permission)

    group.permissions.set(permissions)


def remove_content_editors(apps, schema_editor):
    Group = apps.get_model('auth', 'Group')
    Group.objects.using(schema_editor.connection.alias).filter(
        name=EDITOR_GROUP_NAME,
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('auth', '0012_alter_user_first_name_max_length'),
        ('portfolio', '0009_enlace'),
    ]

    operations = [
        migrations.RunPython(
            configure_content_editors,
            remove_content_editors,
        ),
    ]
