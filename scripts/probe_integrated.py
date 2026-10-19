import json
from urllib.error import HTTPError
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen


API_URL = 'http://localhost:8000/api/v1/'
FRONTEND_URL = 'http://127.0.0.1:4301/'
ALLOWED_ORIGIN = 'http://127.0.0.1:4301'


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def get_json(path):
    request = Request(
        urljoin(API_URL, path),
        headers={'Accept': 'application/json', 'Origin': ALLOWED_ORIGIN},
    )
    try:
        with urlopen(request, timeout=10) as response:
            status = response.status
            headers = response.headers
            payload = json.loads(response.read().decode('utf-8'))
    except HTTPError as error:
        raise RuntimeError(f'GET {path} devolvió HTTP {error.code}.') from error

    require(status == 200, f'GET {path} devolvió HTTP {status}, se esperaba 200.')
    require(
        headers.get('Access-Control-Allow-Origin') == ALLOWED_ORIGIN,
        f'GET {path} no autorizó el origen CORS del frontend.',
    )
    require(
        headers.get('Access-Control-Allow-Credentials', '').lower() != 'true',
        f'GET {path} habilitó credenciales CORS para contenido público.',
    )
    return payload


def get_page(path):
    payload = get_json(path)
    require(isinstance(payload, dict), f'{path} debe devolver un objeto paginado.')
    require(isinstance(payload.get('count'), int), f'{path} no incluye count válido.')
    require(isinstance(payload.get('results'), list), f'{path} no incluye results válido.')
    return payload


def check_frontend():
    with urlopen(FRONTEND_URL, timeout=10) as response:
        html = response.read().decode('utf-8')
        require(response.status == 200, 'Angular no devolvió HTTP 200.')
    require('<app-root' in html, 'La página de Angular no contiene el elemento app-root.')
    print('OK: Angular responde HTTP 200 en el origen E2E.')


def check_public_api():
    profile = get_json('perfil/')
    require(profile.get('name') == 'Nahuel Argandoña', 'Perfil publicado inesperado.')
    print('OK: perfil público recibido desde Django.')

    first_page = get_page('tecnologias/?page_size=20')
    require(first_page['count'] == 24, 'La semilla debe publicar 24 tecnologías.')
    require(first_page['next'], 'La primera página de tecnologías debe enlazar la siguiente.')
    next_page_url = urlparse(first_page['next'])
    api_origin = urlparse(API_URL)
    require(
        (next_page_url.scheme, next_page_url.netloc)
        == (api_origin.scheme, api_origin.netloc),
        'La paginación de tecnologías apuntó a un origen inesperado.',
    )
    second_page_path = next_page_url.path.removeprefix(api_origin.path)
    second_page = get_page(second_page_path + '?' + next_page_url.query)
    technology_names = [
        item['name']
        for page in (first_page, second_page)
        for group in page['results']
        for item in group['technologies']
    ]
    require(len(technology_names) == 24, 'La paginación no devolvió las 24 tecnologías.')
    require(
        len(set(technology_names)) == len(technology_names),
        'La paginación devolvió tecnologías duplicadas.',
    )
    require('TK15 Draft Technology' not in technology_names, 'Se expuso una tecnología borrador.')
    print('OK: 24 tecnologías recibidas en dos páginas, sin duplicados ni borradores.')

    projects = get_page('proyectos/')
    project_names = {project['name'] for project in projects['results']}
    require({'PintaEbook', 'DGES'} <= project_names, 'Faltan proyectos publicados esperados.')
    require(
        all(project.get('name') != 'TK15 Draft Project' for project in projects['results']),
        'Se expuso un proyecto borrador.',
    )
    print('OK: proyectos publicados presentes y proyecto borrador excluido.')

    links = get_page('enlaces/')
    link_labels = {link['label'] for link in links['results']}
    require({'GitHub', 'LinkedIn'} <= link_labels, 'Faltan enlaces profesionales esperados.')
    require(
        all(link.get('label') != 'TK15 Draft Link' for link in links['results']),
        'Se expuso un enlace borrador.',
    )
    print('OK: enlaces profesionales publicados presentes y enlace borrador excluido.')

    for path in ('experiencias/', 'formacion/'):
        payload = get_page(path)
        require(payload['count'] == 1, f'{path} debe contener una fila publicada.')
        require('Draft' not in json.dumps(payload), f'{path} expuso un borrador.')
        print(f'OK: {path} devuelve solo la fila publicada.')


def main():
    check_frontend()
    check_public_api()


if __name__ == '__main__':
    main()
