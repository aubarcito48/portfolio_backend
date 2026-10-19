from django.core.exceptions import ValidationError
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
