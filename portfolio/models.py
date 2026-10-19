from django.core.exceptions import ValidationError
from django.core.validators import URLValidator
from django.db import models
from django.db.models import Q


class Perfil(models.Model):
    singleton_key = models.PositiveSmallIntegerField(
        default=1,
        editable=False,
        unique=True,
    )
    name = models.CharField(max_length=150)
    professional_title = models.CharField(max_length=200)
    biography = models.TextField()
    location = models.CharField(max_length=150)
    image_url = models.CharField(max_length=500)
    is_published = models.BooleanField(default=False)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ('name',)
        constraints = [
            models.CheckConstraint(
                condition=Q(singleton_key=1),
                name='portfolio_profile_singleton_key',
            ),
        ]
        verbose_name = 'perfil'
        verbose_name_plural = 'perfil'

    def save(self, *args, **kwargs):
        self.singleton_key = 1
        if self._state.adding and type(self).objects.exists():
            raise ValidationError('Solo puede existir un perfil.')
        return super().save(*args, **kwargs)

    def __str__(self):
        return self.name

    def to_public_dict(self):
        return {
            'name': self.name,
            'specialty': self.professional_title,
            'biography': self.biography,
            'location': self.location,
            'photo': self.image_url,
        }


class Tecnologia(models.Model):
    name = models.CharField(max_length=100)
    category = models.CharField(max_length=100)
    url = models.URLField(max_length=500)
    order = models.PositiveIntegerField(default=0)
    is_published = models.BooleanField(default=False)

    class Meta:
        ordering = ('order', 'id')
        constraints = [
            models.UniqueConstraint(
                models.functions.Lower('name'),
                models.functions.Lower('category'),
                name='portfolio_technology_unique_name_category',
            ),
        ]
        verbose_name = 'tecnología'
        verbose_name_plural = 'tecnologías'

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.name} ({self.category})'


class Experiencia(models.Model):
    title = models.CharField(max_length=150)
    organization = models.CharField(max_length=150)
    description = models.TextField()
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    is_current = models.BooleanField(default=False)
    order = models.PositiveIntegerField(default=0)
    is_published = models.BooleanField(default=False)

    class Meta:
        ordering = ('order', 'id')
        constraints = [
            models.CheckConstraint(
                condition=Q(end_date__isnull=True) | Q(end_date__gte=models.F('start_date')),
                name='portfolio_experience_valid_date_range',
            ),
            models.CheckConstraint(
                condition=Q(is_current=False) | Q(end_date__isnull=True),
                name='portfolio_current_experience_without_end_date',
            ),
        ]
        verbose_name = 'experiencia profesional'
        verbose_name_plural = 'experiencias profesionales'

    def clean(self):
        super().clean()
        if self.end_date and self.end_date < self.start_date:
            raise ValidationError(
                {'end_date': 'La fecha de fin no puede ser anterior a la fecha de inicio.'}
            )
        if self.is_current and self.end_date:
            raise ValidationError(
                {'end_date': 'Una experiencia actual no puede tener fecha de fin.'}
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.title} - {self.organization}'

    def to_public_dict(self):
        return {
            'title': self.title,
            'organization': self.organization,
            'description': self.description,
            'startDate': self.start_date.isoformat(),
            'endDate': self.end_date.isoformat() if self.end_date else None,
            'isCurrent': self.is_current,
        }


class Formacion(models.Model):
    class Type(models.TextChoices):
        STUDY = 'study', 'Estudio'
        CERTIFICATION = 'certification', 'Certificación'

    class Status(models.TextChoices):
        IN_PROGRESS = 'in_progress', 'En curso'
        COMPLETED = 'completed', 'Finalizada'

    name = models.CharField(max_length=200)
    institution = models.CharField(max_length=200)
    type = models.CharField(max_length=20, choices=Type.choices)
    status = models.CharField(max_length=20, choices=Status.choices)
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    url = models.URLField(max_length=500, blank=True)
    order = models.PositiveIntegerField(default=0)
    is_published = models.BooleanField(default=False)

    class Meta:
        ordering = ('order', 'id')
        constraints = [
            models.CheckConstraint(
                condition=Q(end_date__isnull=True)
                | Q(end_date__gte=models.F('start_date')),
                name='portfolio_education_valid_date_range',
            ),
            models.CheckConstraint(
                condition=(
                    Q(status='in_progress', end_date__isnull=True)
                    | Q(status='completed', end_date__isnull=False)
                ),
                name='portfolio_education_status_matches_dates',
            ),
            models.CheckConstraint(
                condition=Q(type__in=('study', 'certification')),
                name='portfolio_education_valid_type',
            ),
        ]
        verbose_name = 'formación'
        verbose_name_plural = 'formación'

    def clean(self):
        super().clean()
        if self.start_date and self.end_date and self.end_date < self.start_date:
            raise ValidationError(
                {'end_date': 'La fecha de fin no puede ser anterior a la fecha de inicio.'}
            )
        if self.status == self.Status.IN_PROGRESS and self.end_date:
            raise ValidationError(
                {'end_date': 'Una formación en curso no puede tener fecha de fin.'}
            )
        if self.status == self.Status.COMPLETED and not self.end_date:
            raise ValidationError(
                {'end_date': 'Una formación finalizada debe tener fecha de fin.'}
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.name} - {self.institution}'

    def to_public_dict(self):
        return {
            'name': self.name,
            'institution': self.institution,
            'type': self.type,
            'status': self.status,
            'startDate': self.start_date.isoformat(),
            'endDate': self.end_date.isoformat() if self.end_date else None,
            'url': self.url or None,
        }


def validate_project_image_url(value):
    if value.startswith('/') and not value.startswith('//'):
        return
    URLValidator(schemes=('http', 'https'))(value)


class Proyecto(models.Model):
    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200, unique=True)
    summary = models.CharField(max_length=300)
    description = models.TextField()
    project_type = models.CharField(max_length=100)
    image_url = models.CharField(
        max_length=500,
        blank=True,
        validators=[validate_project_image_url],
    )
    image_alt = models.CharField(max_length=300, blank=True)
    demo_url = models.URLField(max_length=500, blank=True)
    demo_label = models.CharField(max_length=100, blank=True, default='Ver demo')
    repository_url = models.URLField(max_length=500, blank=True)
    repository_label = models.CharField(
        max_length=100,
        blank=True,
        default='Repositorio',
    )
    technologies = models.ManyToManyField(
        Tecnologia,
        related_name='projects',
        blank=True,
    )
    order = models.PositiveIntegerField(default=0)
    is_published = models.BooleanField(default=False)

    class Meta:
        ordering = ('order', 'id')
        verbose_name = 'proyecto'
        verbose_name_plural = 'proyectos'

    def clean(self):
        super().clean()
        if self.image_url:
            validate_project_image_url(self.image_url)

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return self.title

    def to_public_dict(self):
        technologies = getattr(
            self,
            'published_technologies',
            self.technologies.filter(is_published=True).order_by('order', 'id'),
        )
        links = []
        if self.demo_url:
            links.append({'label': self.demo_label, 'url': self.demo_url})
        if self.repository_url:
            links.append(
                {'label': self.repository_label, 'url': self.repository_url}
            )
        links.extend(
            {'label': link.label, 'url': link.url}
            for link in self.additional_links.all()
        )

        return {
            'name': self.title,
            'slug': self.slug,
            'summary': self.summary,
            'type': self.project_type,
            'image': self.image_url,
            'imageAlt': self.image_alt,
            'description': self.description,
            'technologies': [technology.name for technology in technologies],
            'links': links,
        }


class EnlaceProyecto(models.Model):
    project = models.ForeignKey(
        Proyecto,
        on_delete=models.CASCADE,
        related_name='additional_links',
    )
    label = models.CharField(max_length=100)
    url = models.URLField(max_length=500)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ('order', 'id')
        verbose_name = 'enlace adicional del proyecto'
        verbose_name_plural = 'enlaces adicionales del proyecto'

    def __str__(self):
        return f'{self.label} - {self.project.title}'
