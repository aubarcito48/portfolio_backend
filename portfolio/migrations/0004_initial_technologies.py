from django.db import migrations, models


TECHNOLOGIES = (
    (
        'Frontend',
        (
            ('JavaScript', 'https://developer.mozilla.org/en-US/docs/Web/JavaScript'),
            ('TypeScript', 'https://www.typescriptlang.org/docs/'),
            ('Angular', 'https://angular.dev/overview'),
            ('React', 'https://react.dev/learn'),
            ('HTML5', 'https://developer.mozilla.org/en-US/docs/Web/HTML'),
            ('CSS3', 'https://developer.mozilla.org/en-US/docs/Web/CSS'),
            ('Tailwind CSS', 'https://tailwindcss.com/docs'),
            ('Bootstrap', 'https://getbootstrap.com/docs/'),
        ),
    ),
    (
        'Backend',
        (
            ('Python', 'https://docs.python.org/3/'),
            ('Django', 'https://docs.djangoproject.com/en/stable/'),
            ('Node.js', 'https://nodejs.org/en/learn'),
            ('Express', 'https://expressjs.com/'),
            ('PHP', 'https://www.php.net/manual/en/'),
            ('WordPress', 'https://developer.wordpress.org/'),
            ('REST APIs', 'https://developer.mozilla.org/en-US/docs/Glossary/REST'),
        ),
    ),
    (
        'Bases de datos y herramientas',
        (
            ('MySQL', 'https://dev.mysql.com/doc/'),
            ('MongoDB', 'https://www.mongodb.com/docs/'),
            ('Git', 'https://git-scm.com/doc'),
            ('GitHub', 'https://docs.github.com/'),
        ),
    ),
    (
        'Calidad de software',
        (
            ('Cypress', 'https://docs.cypress.io/'),
            ('Playwright', 'https://playwright.dev/docs/intro'),
        ),
    ),
)


def create_initial_technologies(apps, schema_editor):
    Tecnologia = apps.get_model('portfolio', 'Tecnologia')
    database = schema_editor.connection.alias
    order = 0

    for category, technologies in TECHNOLOGIES:
        for name, url in technologies:
            Tecnologia.objects.using(database).get_or_create(
                name=name,
                category=category,
                defaults={
                    'url': url,
                    'order': order,
                    'is_published': True,
                },
            )
            order += 1


def remove_initial_technologies(apps, schema_editor):
    Tecnologia = apps.get_model('portfolio', 'Tecnologia')
    database = schema_editor.connection.alias
    seeded_technologies = models.Q()
    for category, technologies in TECHNOLOGIES:
        for name, _ in technologies:
            seeded_technologies |= models.Q(name=name, category=category)
    Tecnologia.objects.using(database).filter(seeded_technologies).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('portfolio', '0003_tecnologia'),
    ]

    operations = [
        migrations.RunPython(
            create_initial_technologies,
            remove_initial_technologies,
        ),
    ]
