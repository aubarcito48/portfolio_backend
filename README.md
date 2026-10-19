# Portfolio backend

Backend del portfolio con Django. El proyecto Django se llama `config` y la
aplicación inicial es `portfolio`.

## Versiones

- Python 3.14.3
- Django 6.1.2
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

Configurá esa clave en `.env`. El archivo está excluido de Git; no compartas ni
versiones sus valores reales.

### Variables de entorno

| Variable | Uso |
| --- | --- |
| `DJANGO_ENVIRONMENT` | `development`, `test` o `production`. Por defecto: `development`. |
| `DJANGO_SECRET_KEY` | Obligatoria en todos los entornos; nunca uses la clave de ejemplo. |
| `DJANGO_DEBUG` | `True` o `False`. Por defecto se activa solo en desarrollo; en producción debe ser `False`. |
| `DJANGO_ALLOWED_HOSTS` | Hosts separados por coma. En producción es obligatorio y explícito. |
| `POSTGRES_DB` | Nombre previsto para la base PostgreSQL. |
| `POSTGRES_USER` | Usuario previsto de PostgreSQL. |
| `POSTGRES_PASSWORD` | Contraseña local de PostgreSQL; no la guardes en Git. |
| `POSTGRES_HOST` | Host del servidor PostgreSQL. |
| `POSTGRES_PORT` | Puerto del servidor PostgreSQL. |

Las variables `POSTGRES_*` quedan preparadas para la configuración de base de
datos de TK03; hasta entonces el proyecto usa SQLite. `.env.example` documenta
nombres y valores ilustrativos, no credenciales utilizables.

Para producción, configurá `DJANGO_ENVIRONMENT=production`, una clave segura,
`DJANGO_DEBUG=False` y la lista real de `DJANGO_ALLOWED_HOSTS`. Si faltan la
clave secreta o los hosts de producción, Django detiene el inicio con un error
de configuración descriptivo sin imprimir valores secretos. El entorno de
pruebas puede seleccionarse con `DJANGO_ENVIRONMENT=test`; `DEBUG` queda
desactivado por defecto.

## Comprobaciones y servidor

Con el entorno virtual activado y `.env` configurado:

```powershell
python manage.py check
python manage.py test
python manage.py runserver
```

La configuración inicial usa SQLite. `manage.py test` encuentra 0 pruebas en
esta etapa de scaffolding; se agregarán pruebas con los endpoints y modelos.

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
