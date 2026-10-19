from django.contrib import admin

from .models import Perfil


@admin.register(Perfil)
class PerfilAdmin(admin.ModelAdmin):
    list_display = ('name', 'professional_title', 'is_published', 'updated_at')
    readonly_fields = ('updated_at',)

    def has_add_permission(self, request):
        return not Perfil.objects.exists() and super().has_add_permission(request)
