from django.http import JsonResponse
from django.views.decorators.http import require_GET

from .models import Perfil


@require_GET
def perfil_publico(request):
    try:
        perfil = Perfil.objects.get(is_published=True)
    except Perfil.DoesNotExist:
        return JsonResponse(
            {'detail': 'No hay un perfil publicado.'},
            status=404,
        )

    return JsonResponse(perfil.to_public_dict())
