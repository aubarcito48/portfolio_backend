from functools import wraps
import json

from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.db.models import Prefetch
from django.http import HttpResponse, JsonResponse

from .models import Enlace, Experiencia, Formacion, Perfil, Proyecto, Tecnologia
from .localization import localize_payload


PAGE_SIZE = 20
MAX_PAGE_SIZE = 100
ALLOWED_READ_METHODS = ('GET', 'HEAD', 'OPTIONS')


def localized_response(response, language):
    if response.get('Content-Type', '').startswith('application/json'):
        response.content = json.dumps(
            localize_payload(json.loads(response.content), language), ensure_ascii=False,
        )
    response['Content-Language'] = language
    return response


def public_read_only(view):
    @wraps(view)
    def wrapped(request, *args, **kwargs):
        language = request.GET.get('lang', 'es')
        if language not in ('es', 'en'):
            return JsonResponse({'detail': 'Idioma no admitido. Usá es o en.'}, status=400)
        if request.method == 'OPTIONS':
            return HttpResponse(
                status=204,
                headers={'Allow': ', '.join(ALLOWED_READ_METHODS)},
            )
        if request.method not in ('GET', 'HEAD'):
            return localized_response(JsonResponse(
                {'detail': 'Método no permitido.'},
                status=405,
                headers={'Allow': ', '.join(ALLOWED_READ_METHODS)},
            ), language)
        response = view(request, *args, **kwargs)
        localized_response(response, language)
        if request.method == 'HEAD':
            response.content = b''
        return response

    return wrapped


def paginated_response(request, items, results):
    try:
        page_size = int(request.GET.get('page_size', PAGE_SIZE))
        if page_size < 1:
            raise ValueError
    except (TypeError, ValueError):
        return JsonResponse(
            {'detail': 'page_size debe ser un entero mayor que cero.'},
            status=400,
        )

    page_size = min(page_size, MAX_PAGE_SIZE)
    paginator = Paginator(items, page_size)
    try:
        page = paginator.page(request.GET.get('page', 1))
    except (EmptyPage, PageNotAnInteger):
        return JsonResponse(
            {'detail': 'La página solicitada no existe.'},
            status=404,
        )

    def page_url(number):
        query = request.GET.copy()
        query['page'] = number
        return request.build_absolute_uri(
            f'{request.path}?{query.urlencode()}'
        )

    return JsonResponse(
        {
            'count': paginator.count,
            'next': page_url(page.next_page_number()) if page.has_next() else None,
            'previous': (
                page_url(page.previous_page_number())
                if page.has_previous()
                else None
            ),
            'results': results(page.object_list),
        }
    )


@public_read_only
def perfil_publico(request):
    try:
        perfil = Perfil.objects.get(is_published=True)
    except Perfil.DoesNotExist:
        return JsonResponse(
            {'detail': 'No hay un perfil publicado.'},
            status=404,
        )

    return JsonResponse(perfil.to_public_dict())


@public_read_only
def tecnologias_publicas(request):
    technologies = Tecnologia.objects.filter(is_published=True).order_by(
        'order', 'id'
    )

    def grouped_results(page_technologies):
        groups = []
        group_by_category = {}
        for technology in page_technologies:
            group = group_by_category.get(technology.category)
            if group is None:
                group = {'name': technology.category, 'technologies': []}
                group_by_category[technology.category] = group
                groups.append(group)
            group['technologies'].append(
                {'name': technology.name, 'url': technology.url}
            )
        return groups

    return paginated_response(request, technologies, grouped_results)


@public_read_only
def experiencias_publicas(request):
    experiencias = Experiencia.objects.filter(is_published=True).order_by(
        'order', 'id'
    )
    return paginated_response(
        request,
        experiencias,
        lambda records: [record.to_public_dict() for record in records],
    )


@public_read_only
def formacion_publica(request):
    registros = Formacion.objects.filter(is_published=True).order_by(
        'order', 'id'
    )
    return paginated_response(
        request,
        registros,
        lambda records: [record.to_public_dict() for record in records],
    )


@public_read_only
def enlaces_publicos(request):
    enlaces = Enlace.objects.filter(is_published=True).order_by('order', 'id')
    return paginated_response(
        request,
        enlaces,
        lambda records: [record.to_public_dict() for record in records],
    )


@public_read_only
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
    return paginated_response(
        request,
        proyectos,
        lambda records: [project.to_public_dict() for project in records],
    )


@public_read_only
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


def api_not_found(request, exception=None):
    if request.path.startswith('/api/'):
        return JsonResponse(
            {'detail': 'No se encontró el recurso solicitado.'},
            status=404,
        )
    return HttpResponse('Not found', status=404)
