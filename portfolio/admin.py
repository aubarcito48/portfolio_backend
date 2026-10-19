from django.contrib import admin

from .models import (
    Enlace,
    EnlaceProyecto,
    Experiencia,
    Formacion,
    Perfil,
    Proyecto,
    Tecnologia,
)


MANAGED_MODEL_NAMES = (
    'perfil',
    'tecnologia',
    'experiencia',
    'formacion',
    'proyecto',
    'enlace',
    'enlaceproyecto',
)
ADMIN_ACTIONS = ('view', 'add', 'change', 'delete')


class PortfolioAdminSite(admin.AdminSite):
    site_header = 'Administración del portfolio'

    def has_permission(self, request):
        if not super().has_permission(request):
            return False
        return any(
            request.user.has_perm(f'portfolio.{action}_{model_name}')
            for model_name in MANAGED_MODEL_NAMES
            for action in ADMIN_ACTIONS
        )


portfolio_admin_site = PortfolioAdminSite()


@admin.register(Enlace, site=portfolio_admin_site)
class EnlaceAdmin(admin.ModelAdmin):
    list_display = ('label', 'type', 'url', 'order', 'is_published')
    list_filter = ('type', 'is_published')
    list_editable = ('order', 'is_published')
    search_fields = ('label', 'type', 'url')
    ordering = ('order', 'id')


@admin.register(Perfil, site=portfolio_admin_site)
class PerfilAdmin(admin.ModelAdmin):
    list_display = ('name', 'professional_title', 'is_published', 'updated_at')
    list_editable = ('is_published',)
    readonly_fields = ('updated_at',)

    def has_add_permission(self, request):
        return not Perfil.objects.exists() and super().has_add_permission(request)


@admin.register(Tecnologia, site=portfolio_admin_site)
class TecnologiaAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'order', 'is_published')
    list_filter = ('category', 'is_published')
    list_editable = ('order', 'is_published')
    search_fields = ('name', 'category')
    ordering = ('order', 'id')


@admin.register(Experiencia, site=portfolio_admin_site)
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


@admin.register(Formacion, site=portfolio_admin_site)
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


@admin.register(Proyecto, site=portfolio_admin_site)
class ProyectoAdmin(admin.ModelAdmin):
    list_display = ('title', 'slug', 'order', 'is_published')
    list_filter = ('is_published', 'project_type')
    list_editable = ('order', 'is_published')
    search_fields = ('title', 'summary', 'description')
    prepopulated_fields = {'slug': ('title',)}
    filter_horizontal = ('technologies',)
    inlines = (EnlaceProyectoInline,)
    ordering = ('order', 'id')
