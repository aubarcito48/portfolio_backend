from django.contrib import admin

from .models import Perfil, Tecnologia


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
