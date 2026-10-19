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

## Relación con el frontend

El contrato de datos de referencia está en `cv-proyecto/src/app/shared/data/`:

- `profile.data.ts`: `profile` y `portfolioContent.home/about`, con campos en
  camelCase, objetos anidados y listas para párrafos, formación, tecnologías,
  proyectos y enlaces.
- `slider-slides.data.ts`: lista de diapositivas; `link` puede ser `null` o un
  objeto con `label` y `url`.
- `focus-chill.data.ts`: configuración de reproducción con `enabled`,
  `spotifyUrl`, `iframeTitle` y `autoplay`.

La aplicación `portfolio` es el lugar para construir esos recursos en Django.
Cuando se exponga la API, conviene mantener una respuesta JSON compatible con
esas formas y nombres para que el frontend pueda consumirla sin cambios
innecesarios. En esta tarea no se modificó el frontend ni se definieron modelos
o endpoints antes de acordar el contrato de la API.
