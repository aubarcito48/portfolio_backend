from django.db.models import Prefetch
from django.http import JsonResponse
from django.views.decorators.http import require_GET

from .models import Experiencia, Formacion, Perfil, Proyecto, Tecnologia


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


@require_GET
def tecnologias_publicas(request):
    groups = []
    group_by_category = {}

    for tecnologia in Tecnologia.objects.filter(is_published=True).order_by(
        'order', 'id'
    ):
        group = group_by_category.get(tecnologia.category)
        if group is None:
            group = {'name': tecnologia.category, 'technologies': []}
            group_by_category[tecnologia.category] = group
            groups.append(group)
        group['technologies'].append(
            {'name': tecnologia.name, 'url': tecnologia.url}
        )

    return JsonResponse(groups, safe=False)


@require_GET
def experiencias_publicas(request):
    experiencias = Experiencia.objects.filter(is_published=True).order_by(
        'order', 'id'
    )
    return JsonResponse(
        [experiencia.to_public_dict() for experiencia in experiencias],
        safe=False,
    )


@require_GET
def formacion_publica(request):
    registros = Formacion.objects.filter(is_published=True).order_by(
        'order', 'id'
    )
    return JsonResponse(
        [registro.to_public_dict() for registro in registros],
        safe=False,
    )


@require_GET
def proyectos_publicos(request):
    proyectos = (
        Proyecto.objects.filter(is_published=True)
        .prefetch_related(
            Prefetch(
                'technologies',
                queryset=Tecnologia.objects.filter(is_published=True).order_by(
                    'order', 'id'
                ),
                to_attr='published_technologies',
            ),
            'additional_links',
        )
        .order_by('order', 'id')
    )
    return JsonResponse(
        [proyecto.to_public_dict() for proyecto in proyectos],
        safe=False,
    )


@require_GET
def detalle_proyecto_publico(request, slug):
    try:
        proyecto = (
            Proyecto.objects.filter(is_published=True)
            .prefetch_related(
                Prefetch(
                    'technologies',
                    queryset=Tecnologia.objects.filter(
                        is_published=True
                    ).order_by('order', 'id'),
                    to_attr='published_technologies',
                ),
                'additional_links',
            )
            .get(slug=slug)
        )
    except Proyecto.DoesNotExist:
        return JsonResponse(
            {'detail': 'No se encontró el proyecto publicado.'},
            status=404,
        )

    return JsonResponse(proyecto.to_public_dict())
