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
| `DJANGO_CSRF_TRUSTED_ORIGINS` | Orígenes HTTP/HTTPS exactos confiables para CSRF, separados por coma. Por defecto: ninguno. |
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
puerto (por ejemplo, `https://portfolio.example.com`). Solo se aceptan
orígenes HTTP/HTTPS exactos, sin rutas ni comodines; el backend no permite
credenciales CORS y limita los métodos anunciados a `GET`, `HEAD` y `OPTIONS`.
Las consultas públicas no necesitan cookies, sesión ni token.

La protección CSRF de Django permanece activa para el Admin y sus operaciones
de sesión. `DJANGO_CSRF_TRUSTED_ORIGINS` es independiente de CORS y debe quedar
vacía salvo que un Admin alojado en otro origen necesite enviar operaciones
protegidas; en ese caso, enumerá únicamente su origen HTTPS exacto. Confiar un
origen para CSRF no le concede permiso CORS, autenticación ni permisos de
administración. CORS tampoco reemplaza la validación CSRF.

El middleware `CorsMiddleware` se ejecuta antes de `CommonMiddleware`, mientras
que `CsrfViewMiddleware` permanece habilitado en la cadena de middleware. El
preflight CORS permitido devuelve HTTP 200 con sus cabeceras; `OPTIONS` directo
de la API devuelve HTTP 204.

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

### Regresión completa TK15

Para ejecutar la regresión del backend y del portfolio integrado en Windows,
configurá `.env`, instalá las dependencias del frontend (`npm ci`) e instalá los
navegadores Playwright (`npx playwright install chromium firefox webkit`).
Desde `portfolio_backend`, ejecutá:

```powershell
.\.venv\Scripts\python.exe scripts\run_regression.py
```

El runner ejecuta la suite Django en una base PostgreSQL con nombre aleatorio
`portfolio_suite_*`, distinta de `POSTGRES_DB` y de cualquier base de pruebas
preexistente. Django la crea y elimina al terminar. Después crea una base
`portfolio_e2e_*`, aplica migraciones y carga datos deterministas, incluidos
registros sintéticos publicados y borradores. El comando de carga rechaza
bases sin ese prefijo o sin las marcas explícitas del entorno de pruebas.
Nunca ejecutes la carga E2E sobre desarrollo o producción.

También ejecuta las pruebas unitarias de Angular y el build de producción.
Inicia Django y Angular localmente y corre Playwright con Chromium, Firefox y
WebKit en anchos de 360, 768 y 1440 px, con dos workers y sin reintentos locales.
La matriz combina la regresión aislada con recorridos `BE-CP22` contra la API
real: contenido publicado, 24 tecnologías en dos páginas, borradores excluidos
(incluso relaciones y detalle), navegación, destinos de enlaces y tema
persistido. Un fallo de red controlado permite comprobar carga, error y
reintento: la recuperación obtiene el perfil desde Django sin simular la
respuesta exitosa. Los casos aislados verifican además las listas vacías y el
perfil no publicado; no se consulta contenido de servicios externos.

Una comprobación HTTP adicional valida el contrato y CORS. Al finalizar, aun
si hay fallos, el runner detiene sus servidores y elimina exclusivamente la
base E2E que creó. El usuario PostgreSQL necesita `CREATEDB`; los puertos 8000
y 4301 deben estar libres. Se esperan los repositorios hermanos
`portfolio_backend/` y `cv-proyecto/`.

Cada ejecución conserva:

- `reports/TK15-regression-<fechaUTC>.json` y una copia `latest`: fecha,
  versiones reales, commits, estado del árbol de trabajo, hashes SHA-256 de
  fuentes, comandos, salidas, cantidades y estado de BE-CP22.
- `reports/<fechaUTC>/playwright-report/index.html`: informe navegable.
- `reports/<fechaUTC>/playwright-results.json`: resultados por caso y entorno.
- `reports/<fechaUTC>/test-results/`: capturas de contenido publicado y, en
  fallos, video, captura y trace.
- `reports/<fechaUTC>/django.log` y `angular.log`: registros persistentes.

Los JSON resumidos y el registro de defectos se pueden versionar. Los
subdirectorios de evidencia pesada se conservan localmente y se excluyen de
Git; para compartirlos, adjuntá esa carpeta comprimida. No contienen `.env`.
Los hashes identifican también las modificaciones locales que todavía no
forman parte de los commits registrados.

Para abrir la evidencia, desde `cv-proyecto`:

```powershell
npx playwright show-report ..\portfolio_backend\reports\<fechaUTC>\playwright-report
npx playwright show-trace <ruta-al-trace.zip>
```

El estado y los defectos de la ejecución de cierre están en
[`reports/BE-CP22.md`](reports/BE-CP22.md).

## Carga inicial de datos

Con las migraciones aplicadas, cargá o actualizá el contenido inicial aprobado
por Nahuel desde la carpeta del backend:

```powershell
python manage.py load_portfolio_data
```

El comando es repetible: actualiza el perfil, las tecnologías, los proyectos,
sus relaciones y enlaces profesionales por sus claves estables, conservando
los IDs existentes y sin borrar contenido adicional administrado desde Admin.
Valida todos los registros antes de escribirlos y ejecuta la aplicación dentro
de una transacción; cualquier error aborta y revierte la ejecución completa.
No contiene credenciales.

El frontend confirma el perfil, las tecnologías, los proyectos y los enlaces
GitHub/LinkedIn. No se cargan experiencias ni formación porque faltan fechas y
detalles verificables para completar esos registros sin inventar información.
Cuando Nahuel valide esos datos, se podrán agregar al comando y cargar desde
Admin.

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

## Administración del contenido

La administración está disponible en `/admin/`. Las personas sin iniciar
sesión deben autenticarse; el acceso requiere una cuenta activa con `is_staff`
y al menos un permiso sobre contenido del portfolio, además de los permisos
correspondientes a cada modelo. El índice del Admin y los modelos ajenos a sus
permisos quedan denegados. Creá una cuenta administrativa
local con:

```powershell
python manage.py createsuperuser
```

La migración crea el grupo **Editores de contenido**, con permisos explícitos
de consulta, creación y edición para Perfil, Tecnología, Experiencia,
Formación, Proyecto y Enlace, además de los permisos requeridos para administrar
los enlaces complementarios de proyectos desde su inline. El grupo no recibe
permisos de eliminación; asignalos individualmente solo cuando sean necesarios.
Para dar acceso a un editor, creá una cuenta desde Django Admin y agregala al
grupo. No se crean usuarios ni contraseñas por defecto. El perfil mantiene la
restricción de un único registro; las tecnologías de los proyectos se
seleccionan mediante un control de selección múltiple.

Los listados permiten buscar y filtrar contenido, y editar en línea el orden y
el estado de publicación cuando corresponde. Despublicar un elemento lo oculta
de los endpoints públicos sin eliminarlo. Los cambios hechos desde Admin se
guardan en PostgreSQL.

## API

La API pública no requiere autenticación y permite `GET`, `HEAD` y `OPTIONS`.
`POST`, `PUT`, `PATCH` y `DELETE` responden HTTP 405 con `detail` y no escriben
datos, incluso cuando la petición incluye una sesión de Admin.

Los listados admiten `page` y `page_size`. Por defecto se devuelven 20 elementos
por página; `page_size` puede ser de 1 a 100 y los valores superiores se limitan
a 100. Los listados usan este sobre:

```json
{
  "count": 21,
  "next": "http://localhost:8000/api/v1/enlaces/?page=2",
  "previous": null,
  "results": []
}
```

`count` indica la cantidad total de elementos publicados; `next` y `previous`
son URL de páginas, o `null` si no existen. Una página fuera de rango o no
numérica responde HTTP 404. Un `page_size` que no sea un entero positivo
responde HTTP 400. Los errores usan un objeto JSON `{"detail":"..."}`. El
perfil y el detalle de proyecto son recursos individuales y no usan paginación.

Rutas públicas:

| Método | Ruta | Respuesta |
| --- | --- | --- |
| `GET`, `HEAD`, `OPTIONS` | `/api/v1/perfil/` | Perfil publicado; HTTP 404 si no existe |
| `GET`, `HEAD`, `OPTIONS` | `/api/v1/tecnologias/` | Listado paginado de tecnologías agrupadas |
| `GET`, `HEAD`, `OPTIONS` | `/api/v1/experiencias/` | Listado paginado de experiencias |
| `GET`, `HEAD`, `OPTIONS` | `/api/v1/formacion/` | Listado paginado de formación |
| `GET`, `HEAD`, `OPTIONS` | `/api/v1/proyectos/` | Listado paginado de proyectos |
| `GET`, `HEAD`, `OPTIONS` | `/api/v1/proyectos/{slug}/` | Proyecto publicado; HTTP 404 si no existe |
| `GET`, `HEAD`, `OPTIONS` | `/api/v1/enlaces/` | Listado paginado de enlaces profesionales |

### Proyectos

`GET /api/v1/proyectos/` devuelve los proyectos publicados en orden ascendente
por `order` y, para empates, por ID, dentro de `results`. `GET
/api/v1/proyectos/{slug}/` devuelve directamente el objeto de un proyecto
publicado. El formato mantiene los campos que usa el frontend:

```json
{
  "name": "PintaEbook",
  "slug": "pintaebook",
  "summary": "Plataforma de libros y ebooks desarrollada por el equipo ISPC / ProCoders.",
  "type": "Proyecto en equipo",
  "image": "/assets/pintaebook.png",
  "imageAlt": "Página de inicio de PintaEbook con su presentación y navegación",
  "description": "Descripción del proyecto.",
  "technologies": ["Angular", "Python", "Django"],
  "links": [
    {
      "label": "Ver demo",
      "url": "https://pinta-ebook-eta.vercel.app/"
    }
  ]
}
```

Cada tecnología aparece como máximo una vez por proyecto y solo si está
publicada. Los proyectos despublicados no aparecen en el listado ni en detalle.
Una imagen puede ser una ruta local del frontend (por ejemplo
`/assets/pintaebook.png`) o una URL HTTP/HTTPS; demo, repositorio y enlaces
adicionales, cuando se proporcionan, deben ser URLs válidas. Si no hay
proyectos publicados, el listado responde HTTP 200 con `count: 0` y
`results: []`. Para un slug
inexistente o despublicado, el detalle responde HTTP 404:

```json
{
  "detail": "No se encontró el proyecto publicado."
}
```

La migración inicial carga los proyectos PintaEbook y DGES con la información
y enlaces definidos en el frontend. Incluye los enlaces adicionales de
frontend/backend y todos sus conocimientos técnicos; HTML, CSS y AJAX se
incorporan al catálogo de tecnologías porque están asociados al proyecto DGES.
Los proyectos, sus tecnologías y enlaces adicionales pueden administrarse en
Django Admin.

### Enlaces profesionales

`GET /api/v1/enlaces/` devuelve HTTP 200 con enlaces publicados en `results`,
ordenados por `order` ascendente y luego por ID. Cada elemento incluye solo
`label`, `type` y `url`:

```json
{
  "count": 2,
  "next": null,
  "previous": null,
  "results": [
    {
      "label": "GitHub",
      "type": "github",
      "url": "https://github.com/aubarcito48"
    },
    {
      "label": "LinkedIn",
      "type": "linkedin",
      "url": "https://www.linkedin.com/in/aubar48/"
    }
  ]
}
```

Las URL deben ser válidas y utilizar HTTP o HTTPS. Los enlaces despublicados no
aparecen; si no hay enlaces publicados, el endpoint devuelve HTTP 200 con
`count: 0` y `results: []`.
La migración inicial carga los perfiles públicos de GitHub y LinkedIn definidos
en el frontend. Los enlaces se pueden agregar y administrar en Django Admin.

### Tecnologías

`GET /api/v1/tecnologias/` devuelve HTTP 200 y grupos dentro de `results`,
conservando la estructura compatible con `technologyGroups` del frontend. Cada
grupo incluye el nombre de categoría y tecnologías con su nombre y enlace de
documentación:

```json
{
  "count": 1,
  "next": null,
  "previous": null,
  "results": [
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
}
```

Solo se incluyen tecnologías publicadas. `count` cuenta tecnologías, y
`page_size` pagina tecnologías antes de agruparlas. Los grupos aparecen en el
orden de su primera tecnología publicada; dentro de cada página, las
tecnologías se ordenan por `order` ascendente y luego por ID ascendente. Si una
categoría continúa en otra página, puede aparecer en ambas y el cliente puede
combinar sus elementos por nombre de categoría. Si no hay tecnologías
publicadas, el endpoint devuelve HTTP 200 con `count: 0` y `results: []`. La
migración inicial carga las tecnologías que muestra actualmente el frontend,
y pueden administrarse en Django Admin.

### Experiencias profesionales

`GET /api/v1/experiencias/` devuelve HTTP 200 con experiencias publicadas
ordenadas dentro de `results`:

```json
{
  "count": 1,
  "next": null,
  "previous": null,
  "results": [
    {
      "title": "Puesto",
      "organization": "Organización",
      "description": "Descripción de la experiencia.",
      "startDate": "2022-03-01",
      "endDate": null,
      "isCurrent": true
    }
  ]
}
```

Las fechas usan el formato ISO `YYYY-MM-DD`. Para experiencias actuales,
`endDate` es `null`; una fecha final no puede ser anterior a la inicial, y una
experiencia actual no puede tener fecha final. Si no hay experiencias
publicadas, el listado devuelve `count: 0` y `results: []`.

El frontend existente no contiene registros de experiencia con puestos,
organizaciones y fechas verificables. Por eso la migración crea el modelo, pero
no inventa ni precarga experiencias; los datos validados se pueden cargar en
Django Admin.

### Formación y certificaciones

`GET /api/v1/formacion/` devuelve HTTP 200 con registros publicados ordenados
dentro de `results`:

```json
{
  "count": 1,
  "next": null,
  "previous": null,
  "results": [
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
}
```

`type` admite `study` o `certification`; `status` admite `in_progress` o
`completed`. La formación en curso no tiene fecha de fin y la finalizada debe
tenerla; la fecha de fin tampoco puede ser anterior a la de inicio. `url` es
opcional y, cuando se informa, debe ser una URL válida. Si no hay registros
publicados, el endpoint devuelve HTTP 200 con `count: 0` y `results: []`.

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
