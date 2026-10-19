from django.contrib import admin

from .models import (
    EnlaceProyecto,
    Experiencia,
    Formacion,
    Perfil,
    Proyecto,
    Tecnologia,
)


@admin.register(Perfil)
class PerfilAdmin(admin.ModelAdmin):
    list_display = ('name', 'professional_title', 'is_published', 'updated_at')
    readonly_fields = ('updated_at',)

    def has_add_permission(self, request):
        return not Perfil.objects.exists() and super().has_add_permission(request)


@admin.register(Tecnologia)
class TecnologiaAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'order', 'is_published')
    list_filter = ('category', 'is_published')
    list_editable = ('order', 'is_published')
    search_fields = ('name', 'category')
    ordering = ('order', 'id')


@admin.register(Experiencia)
class ExperienciaAdmin(admin.ModelAdmin):
    list_display = (
        'title',
        'organization',
        'start_date',
        'end_date',
        'is_current',
        'is_published',
        'order',
    )
    list_filter = ('is_current', 'is_published')
    list_editable = ('is_current', 'is_published', 'order')
    search_fields = ('title', 'organization', 'description')
    ordering = ('order', 'id')


@admin.register(Formacion)
class FormacionAdmin(admin.ModelAdmin):
    list_display = (
        'name',
        'institution',
        'type',
        'status',
        'start_date',
        'end_date',
        'is_published',
        'order',
    )
    list_filter = ('type', 'status', 'is_published')
    list_editable = ('status', 'is_published', 'order')
    search_fields = ('name', 'institution')
    ordering = ('order', 'id')


class EnlaceProyectoInline(admin.TabularInline):
    model = EnlaceProyecto
    extra = 0


@admin.register(Proyecto)
class ProyectoAdmin(admin.ModelAdmin):
    list_display = ('title', 'slug', 'order', 'is_published')
    list_filter = ('is_published', 'project_type')
    list_editable = ('order', 'is_published')
    search_fields = ('title', 'summary', 'description')
    prepopulated_fields = {'slug': ('title',)}
    filter_horizontal = ('technologies',)
    inlines = (EnlaceProyectoInline,)
    ordering = ('order', 'id')
