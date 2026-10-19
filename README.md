# Portfolio backend

Backend del portfolio con Django. El proyecto Django se llama `config` y la
aplicación inicial es `portfolio`.

## Versiones

- Python 3.14.3
- Django 6.1.2
- django-cors-headers 4.9.0
- PostgreSQL 18.3
- Psycopg 3.3.6 (`psycopg[binary]`)
- Dependencias exactas: [`requirements.txt`](./requirements.txt)

## Instalación local (Windows / PowerShell)

Desde la carpeta `portfolio_backend`:

```powershell
py -3.14 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Editá `.env` y reemplazá `DJANGO_SECRET_KEY` por una clave aleatoria. Podés
generarla con:

```powershell
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

Configurá esa clave y las credenciales de PostgreSQL en `.env`. El archivo está
excluido de Git; no compartas ni versiones sus valores reales. Django rechaza
la clave ilustrativa `replace-with-...`.

### Variables de entorno

| Variable | Uso |
| --- | --- |
| `DJANGO_ENVIRONMENT` | `development`, `test` o `production`. Por defecto: `development`. |
| `DJANGO_SECRET_KEY` | Obligatoria en todos los entornos; nunca uses la clave de ejemplo. |
| `DJANGO_DEBUG` | `True` o `False`. Por defecto se activa solo en desarrollo; en producción debe ser `False`. |
| `DJANGO_ALLOWED_HOSTS` | Hosts separados por coma. En producción es obligatorio y explícito. |
| `DJANGO_CORS_ALLOWED_ORIGINS` | Orígenes web permitidos separados por coma. En desarrollo permite por defecto `http://localhost:4200`. |
| `POSTGRES_DB` | Base PostgreSQL de desarrollo. Obligatoria. |
| `POSTGRES_USER` | Usuario PostgreSQL. Obligatoria. |
| `POSTGRES_PASSWORD` | Contraseña PostgreSQL. Obligatoria; no la guardes en Git. |
| `POSTGRES_HOST` | Host PostgreSQL. Por defecto: `127.0.0.1`. |
| `POSTGRES_PORT` | Puerto PostgreSQL. Por defecto: `5432`. |
| `POSTGRES_TEST_DB` | Base exclusiva para pruebas. Por defecto: `test_<POSTGRES_DB>`. |

`.env.example` documenta nombres y valores ilustrativos, no credenciales
utilizables. Django se conecta a PostgreSQL; el usuario configurado necesita
permisos sobre la base de desarrollo y permiso `CREATEDB` para que Django cree
la base de pruebas. `POSTGRES_TEST_DB` debe ser distinta de `POSTGRES_DB`.
El runner de Django crea y elimina la base de pruebas al ejecutar tests, así
que debe ser una base dedicada y descartable.

Para producción, configurá `DJANGO_ENVIRONMENT=production`, una clave segura,
`DJANGO_DEBUG=False` y la lista real de `DJANGO_ALLOWED_HOSTS`. Si faltan la
clave secreta o los hosts de producción, Django detiene el inicio con un error
de configuración descriptivo sin imprimir valores secretos. El entorno de
pruebas puede seleccionarse con `DJANGO_ENVIRONMENT=test`; `DEBUG` queda
desactivado por defecto.

La API permite CORS para el frontend Angular local en `http://localhost:4200`
durante desarrollo. En otros entornos, definí explícitamente
`DJANGO_CORS_ALLOWED_ORIGINS` con los orígenes confiables, incluyendo esquema y
puerto (por ejemplo, `https://portfolio.example.com`). No se habilita acceso
desde cualquier origen ni se activa el envío de credenciales por CORS.

## Comprobaciones y servidor

Con el entorno virtual activado y `.env` configurado:

```powershell
python manage.py check
python manage.py migrate
python manage.py showmigrations
$env:DJANGO_ENVIRONMENT = "test"
python manage.py test
$env:DJANGO_ENVIRONMENT = "development"
python manage.py runserver
```

`manage.py test` usa `POSTGRES_TEST_DB`, separada de la base de desarrollo. El
usuario PostgreSQL necesita permiso `CREATEDB` para que Django cree esa base
temporal. La prueba de persistencia guarda un registro ORM, cierra la conexión
y lo consulta desde una conexión nueva.

## Perfil público

La migración inicial crea el perfil publicado con los datos que ya muestra el
frontend. Se puede actualizar desde Django Admin; la aplicación permite un
solo perfil.

`GET /api/v1/perfil/` devuelve HTTP 200 con los campos públicos en camelCase
compatibles con el frontend:

```json
{
  "name": "Nahuel Argandoña",
  "specialty": "Full-Stack Developer | Software Development | QA & Testing",
  "biography": "Biografía del perfil",
  "location": "Córdoba, Argentina",
  "photo": "/assets/nahuel.jpg"
}
```

El estado de publicación y la fecha de actualización no se exponen. Si no hay
un perfil publicado, responde HTTP 404:

```json
{
  "detail": "No hay un perfil publicado."
}
```

## API

Los endpoints de consulta permiten únicamente `GET`; los demás métodos
responden HTTP 405.

### Tecnologías

`GET /api/v1/tecnologias/` devuelve HTTP 200 y una lista de grupos compatible
con `technologyGroups` del frontend. Cada grupo incluye el nombre de categoría
y tecnologías con su nombre y enlace de documentación:

```json
[
  {
    "name": "Frontend",
    "technologies": [
      {
        "name": "JavaScript",
        "url": "https://developer.mozilla.org/en-US/docs/Web/JavaScript"
      }
    ]
  }
]
```

Solo se incluyen tecnologías publicadas. Los grupos aparecen en el orden de su
primera tecnología publicada; dentro de cada grupo, las tecnologías se ordenan
por `order` ascendente y luego por ID ascendente. Si no hay tecnologías
publicadas, el endpoint devuelve HTTP 200 con `[]`. La migración inicial carga
las tecnologías que muestra actualmente el frontend, y pueden administrarse
en Django Admin.

### Experiencias profesionales

`GET /api/v1/experiencias/` devuelve HTTP 200 con una lista ordenada de
experiencias publicadas:

```json
[
  {
    "title": "Puesto",
    "organization": "Organización",
    "description": "Descripción de la experiencia.",
    "startDate": "2022-03-01",
    "endDate": null,
    "isCurrent": true
  }
]
```

Las fechas usan el formato ISO `YYYY-MM-DD`. Para experiencias actuales,
`endDate` es `null`; una fecha final no puede ser anterior a la inicial, y una
experiencia actual no puede tener fecha final. El endpoint devuelve `[]` si no
hay experiencias publicadas.

El frontend existente no contiene registros de experiencia con puestos,
organizaciones y fechas verificables. Por eso la migración crea el modelo, pero
no inventa ni precarga experiencias; los datos validados se pueden cargar en
Django Admin.

### Formación y certificaciones

`GET /api/v1/formacion/` devuelve HTTP 200 con una lista ordenada de registros
publicados:

```json
[
  {
    "name": "Tecnicatura Superior en Desarrollo de Software",
    "institution": "Instituto Superior Politécnico de Córdoba (ISPC)",
    "type": "study",
    "status": "in_progress",
    "startDate": "2022-03-01",
    "endDate": null,
    "url": null
  }
]
```

`type` admite `study` o `certification`; `status` admite `in_progress` o
`completed`. La formación en curso no tiene fecha de fin y la finalizada debe
tenerla; la fecha de fin tampoco puede ser anterior a la de inicio. `url` es
opcional y, cuando se informa, debe ser una URL válida. Si no hay registros
publicados, el endpoint devuelve HTTP 200 con `[]`.

El frontend confirma el nombre del estudio, ISPC y la certificación Junior Full
Stack Developer, pero no proporciona fechas de inicio/finalización verificadas.
Por eso la migración crea el modelo sin inventar ni precargar registros; los
datos validados se pueden cargar desde Django Admin.

## Relación con el frontend

El contrato de datos de referencia está en `cv-proyecto/src/app/shared/data/`:

- `profile.data.ts`: `profile` y `portfolioContent.home/about`, con campos en
  camelCase, objetos anidados y listas para párrafos, formación, tecnologías,
  proyectos y enlaces.
- `slider-slides.data.ts`: lista de diapositivas; `link` puede ser `null` o un
  objeto con `label` y `url`.
- `focus-chill.data.ts`: configuración de reproducción con `enabled`,
  `spotifyUrl`, `iframeTitle` y `autoplay`.

La API de perfil, tecnologías y formación usa nombres JSON camelCase para las
fechas y conserva las estructuras públicas de las secciones del frontend. En
TK04–TK07 no se modificó el frontend.
