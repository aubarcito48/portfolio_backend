# Portfolio backend

Formulario de contacto con envío al correo del portfolio:
[configuración de Resend/Render y verificación](docs/CONTACT.md).

Bot de WhatsApp con activación por el mensaje del portfolio:
[integración Meta Cloud API, variables de Render y pruebas](docs/WHATSAPP.md).

Backend del portfolio con Django. El proyecto Django se llama `config` y la
aplicación inicial es `portfolio`.

El [Curriculum Vitae se administra como enlace profesional](docs/CV_PUBLICATION.md),
desde el backend y Supabase, sin fijar su URL en Angular.

Proyecto de hardware incorporado al portfolio: [Aubar Bot · publicación y verificación](docs/AUBAR_BOT_PUBLICATION.md).

## Aubar · Asistente con IA

El portfolio incluye un chat en español e inglés. Django obtiene únicamente
información publicada mediante MCP y genera respuestas con Groq.
Configuración de `.env`, contrato, límites, pruebas y pasos para Render:
[guía de Aubar](docs/AUBAR.md).

El contenido público admite español e inglés con `?lang=es` / `?lang=en`.
Ver [idiomas, mantenimiento de traducciones y orden de publicación](docs/I18N.md).

## Versiones

- Python 3.14.3
- Django 6.1.2
- django-cors-headers 4.9.0
- PostgreSQL 18.3
- Psycopg 3.3.6 (`psycopg[binary]`)
- Gunicorn 26.2.0 (servidor de producción para Linux/Unix)
- WhiteNoise 6.12.0 (estáticos del Admin)
- Dependencias exactas: [`requirements.txt`](./requirements.txt)

## Despliegue en Render

TK18: backend publicado y comprobaciones públicas aprobadas el 19/10/2026.
El responsable confirmó acceso administrativo, reinicio y persistencia con el
commit `d082a82`. Ver [procedimiento actual Render/Supabase](docs/RENDER_DEPLOYMENT.md)
y [BE-CP25: evidencias y límites](reports/BE-CP25.md). Las notas de ensayo local
de esta sección son históricas; no sustituyen la comprobación del servicio.

Crear un Web Service Python conectado a este repositorio. `manage.py` está
en la raíz; **Root Directory se deja vacío**.

| Campo | Valor |
| --- | --- |
| Build Command | `pip install -r requirements.txt && python manage.py collectstatic --noinput && python manage.py migrate --noinput` |
| Start Command | `python -m gunicorn config.wsgi:application --bind 0.0.0.0:$PORT` |
| Health Check Path | `/health/` |
| Python | `PYTHON_VERSION=3.14.3`, versión usada en la validación local |

Si el plan ofrece Pre-Deploy Command, mover allí `python manage.py migrate
--noinput` y quitarlo del build. Las migraciones deben aplicarse una vez por
despliegue, sin ejecutar tests sobre la base de producción.

Configurar en Render `DJANGO_ENVIRONMENT=production`, `DJANGO_DEBUG=False`, una
`DJANGO_SECRET_KEY` nueva y persistente, y `DJANGO_ALLOWED_HOSTS` con el hostname
real sin esquema ni rutas. Para PostgreSQL se requieren `POSTGRES_DB`,
`POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_HOST` del proveedor y
`POSTGRES_PORT=5432`; el código no interpreta `DATABASE_URL`. Cargar los valores
en Render sin versionarlos ni compartirlos. Se eligió Supabase: la conexión no
usa la red interna de Render. Preservar SSL y el esquema `portfolio_django` según
`docs/RENDER_DEPLOYMENT.md`; los settings base solos no configuran esas opciones.

`DJANGO_CORS_ALLOWED_ORIGINS` debe contener el origen HTTPS exacto del frontend.
El Admin utiliza CSRF; configurar `DJANGO_CSRF_TRUSTED_ORIGINS` con sus orígenes
HTTPS exactos cuando corresponda. El frontend en otro dominio requiere además
su propia URL absoluta de API o un rewrite; CORS no cambia esa URL.

WhiteNoise se ejecuta inmediatamente después de `SecurityMiddleware` y sirve
los estáticos recolectados en `STATIC_ROOT=BASE_DIR / 'staticfiles'` bajo
`/static/`. No hace falta configurar otro servicio para el CSS/JS del Admin.
En producción se reconoce `X-Forwarded-Proto` del proxy de Render y las cookies
de sesión y CSRF se marcan `Secure`; estas opciones no se activan en desarrollo
ni en tests. La confianza en esa cabecera requiere mantener el proxy confiable.

El formulario de contacto envía por HTTPS con Resend (ver `docs/CONTACT.md`).
La recuperación de contraseña por email sigue deshabilitada. En producción `MAILERS` usa el
backend `dummy`: descarta mensajes del Admin sin red ni salida a consola. No se configura
SMTP para ese mailer. Django considera ese backend no apto para envío real y
emite `mail.E001`; se exceptúa **solo ese chequeo, solo en producción**, porque
el envío está deshabilitado intencionalmente. El resto de los chequeos sigue
activo. Desarrollo conserva el backend de consola. Si se incorpora email en
el futuro, reemplazar esa configuración y retirar la excepción.

Validación realizada: dependencias, `check`, `collectstatic` (130 archivos),
ausencia de migraciones pendientes y 106 tests sobre un clúster PostgreSQL
temporal con configuración sintética y carga de `.env` desactivada.
Con `DEBUG=False` se verificaron `/static/admin/css/base.css`, login del Admin,
HTTPS por cabecera y `/health/` contra PostgreSQL real.

Pendientes antes de dar por verificado el despliegue:

- Arrancar Gunicorn en Linux y consultar Admin, estáticos y health. Windows
  carece de `fcntl`; el WSL local tampoco pudo iniciarse. La instalación del
  paquete y el smoke WSGI pasan, pero no sustituyen esa prueba en Linux.
- `check --deploy` conserva `security.W004` (HSTS no habilitado) y
  `security.W008` (redirección HTTPS delegada al proxy). Confirmar la
  redirección de Render; decidir HSTS cuando el dominio HTTPS esté validado.
  Esas advertencias no se silencian ni se activa HSTS automáticamente.
- Cargar las variables reales, ejecutar las migraciones en Render y comprobar
  CORS/CSRF con los dominios definitivos. No se ha desplegado ni conectado a
  una base de Render durante esta preparación.

Evidencia: [`reports/render-deployment-validation.json`](reports/render-deployment-validation.json).
No se leyó ni modificó el archivo `.env` para estas verificaciones.

## Instalación local (Windows / PowerShell)

Copias y recuperación (TK19): [procedimiento](docs/BACKUP_RECOVERY.md) y
[BE-CP26: ensayo aprobado](reports/BE-CP26.md). Para repetirlo sin tocar bases
existentes ni cargar archivos `.env`, ejecutar desde esta raíz:

```powershell
.\.venv\Scripts\python.exe scripts/validate_recovery.py --pg-bin 'C:/Program Files/PostgreSQL/18/bin'
```

El ensayo genera datos sintéticos, restaura en otra base nueva y prueba una
versión anterior compatible. Las copias privadas quedan ignoradas en `backups/`.
Volver a un commit previo no revierte automáticamente datos ni migraciones.

Para una transferencia PostgreSQL local → Supabase, consultar
[`docs/SUPABASE_TRANSFER.md`](docs/SUPABASE_TRANSFER.md). El procedimiento usa
configuraciones separadas, respaldo local y guardas contra contenido existente.
Transferencia real completada y comparada el 19/10/2026; evidencia sin secretos en
[`reports/supabase-transfer-execution.json`](reports/supabase-transfer-execution.json).
El destino ya contiene la aplicación: no repetir `import-new`.

Para verificar la conexión activa dentro del servicio desplegado, sin mostrar
secretos ni modificar datos, consultar
[`docs/VERIFY_RENDER_DATABASE.md`](docs/VERIFY_RENDER_DATABASE.md).
La API pública coincide con Supabase; la identidad interna de Render requiere
la comprobación dentro de su proceso, no puede deducirse solo de `/health/`.

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

## Rendimiento y consultas — TK16 / BE-CP23

Con PostgreSQL y `.env` configurados, desde `portfolio_backend`:

```powershell
.\.venv\Scripts\python.exe scripts\measure_performance.py --label after --run-tests
```

Requiere `CREATEDB` y el puerto local 8765 libre. No necesita frontend ni
servicios externos. El runner crea una base PostgreSQL aleatoria y descartable,
aplica migraciones y carga 100 proyectos publicados y un borrador, cada uno
con cinco tecnologías publicadas, una oculta y dos enlaces adicionales.
También carga perfil, tecnologías, experiencias, formación y enlaces
deterministas. La carga rechaza bases de desarrollo y nombres que no cumplen
las guardas E2E; reemplaza contenido solamente en la base temporal creada.

Mide por HTTP real los siete endpoints de contenido y, adicionalmente, el
listado de 100 proyectos. Cada escenario recibe cinco peticiones de
calentamiento y 50 medidas secuenciales; conserva duración, código HTTP,
errores, tamaño y hash del contenido de cada respuesta. Calcula p95 con rango
más cercano: posición `ceil(0.95 * 50)`, es decir, el valor 48 ordenado.
La medición utiliza `DEBUG=False`, `runserver --noreload --nothreading`,
loopback, concurrencia uno y conexiones HTTP nuevas, sin caché de respuestas.
Se mantiene la configuración PostgreSQL normal del proyecto, con conexiones
Django no persistentes (`CONN_MAX_AGE=0`).

El primer acceso a perfil se informa aparte: duración HTTP inicial y tiempo
desde crear el proceso hasta recibir esa respuesta. La disponibilidad se
comprueba por TCP sin consultar la API. Es un proceso Django nuevo, con
PostgreSQL ya iniciado y los datos recién cargados; no representa un reinicio
del sistema ni una caché de disco vacía. El objetivo provisional de 1000 ms
se evalúa sobre el p95 caliente, no sobre el inicio del proceso.

Las consultas SQL se capturan en otra etapa mediante el cliente Django,
tres veces por escenario y con conexión ya inicializada. No se instrumentan
las peticiones HTTP usadas para calcular latencias. El listado de proyectos
debe conservar cuatro consultas al pasar de 1 a 20 o 100 elementos; el detalle
usa tres. Las pruebas de presupuesto de consultas verifican esto junto con
contenido, orden, paginación y exclusión de borradores. La suite completa
mantiene las comprobaciones de permisos y validaciones.

`--run-tests` ejecuta la regresión al terminar las mediciones, en otra base
aleatoria independiente. El resultado es un JSON histórico en
`reports/TK16-<fechaUTC>-after.json`, con muestras, p95, SQL, versiones, commit,
hashes de fuentes y salidas de ejecución. Su carpeta del mismo nombre guarda
los logs y la captura SQL; los datos esenciales también están en el JSON
versionable. Al terminar se elimina únicamente la base temporal creada.

Para comparar dos ejecuciones con los mismos datos y condiciones:

```powershell
.\.venv\Scripts\python.exe scripts\measure_performance.py --label after --compare reports\TK16-<fechaUTC>-before.json --run-tests
```

Las etiquetas `before`/`after` identifican versiones medidas; no cambian el
código automáticamente. La comparación verifica condiciones, contenido y
consultas. Si un p95 supera 1000 ms o hay errores, el runner conserva la
evidencia y termina con código distinto de cero. La interpretación, hardware,
resultados de cierre y pasos para repetir la versión anterior están en
[`reports/BE-CP23.md`](reports/BE-CP23.md).

## Disponibilidad y logs seguros — TK17 / BE-CP24

`GET /health/` no requiere autenticación y ejecuta exactamente `SELECT 1`
contra la conexión PostgreSQL configurada. No lee tablas del portfolio ni
modifica datos; puede utilizarse antes de aplicar migraciones.

| Condición | HTTP | JSON |
| --- | --- | --- |
| PostgreSQL responde correctamente | 200 | `{"status":"ok"}` |
| Error de conexión, de consulta o resultado inesperado | 503 | `{"status":"unavailable"}` |

Las respuestas incluyen `Cache-Control` con `no-store` y no incluyen nombres
de usuario, servidores, credenciales ni trazas. `HEAD` hace la misma comprobación
y devuelve el mismo código sin cuerpo. `OPTIONS` solo informa los métodos y
devuelve 204 sin consultar PostgreSQL; los monitores deben usar `GET`.
Los métodos de escritura se rechazan. La apertura de conexiones PostgreSQL
tiene `connect_timeout=3` segundos; este límite corresponde al establecimiento
de conexión, no a un timeout global de cualquier consulta o petición.

Consulta local:

```powershell
curl.exe -i http://127.0.0.1:8000/health/
```

Los logs de Python se envían a stderr como JSON. Conservan fecha UTC, nivel,
componente, evento, código HTTP y una categoría de error permitida cuando
está disponible. Por ejemplo, una caída de PostgreSQL registra
`component=health`, `event=database_unavailable`, `errorType=OperationalError`
y `statusCode=503`. Django también puede registrar un evento HTTP de ese 503.

El formateador utiliza una lista de campos permitidos: nunca serializa el
mensaje libre, argumentos, texto de excepciones, traceback, SQL, objetos de
solicitud ni campos adicionales arbitrarios. Así se excluyen cuerpos privados,
cookies, cabeceras de autorización, tokens, query strings y credenciales,
incluso si llegan dentro de una excepción. Las excepciones desconocidas usan
`UnexpectedError`, sin exponer el nombre de una clase arbitraria.
Los loggers de Django y la aplicación usan este formato; se reemplazan los
handlers por defecto de Django, incluido el envío de excepciones por correo.
La configuración no controla los logs independientes de un proxy o servidor
externo. En producción debe mantenerse `DJANGO_DEBUG=False`, como exige la
configuración del proyecto.

Para conservar y consultar stderr del servidor local:

```powershell
New-Item -ItemType Directory -Force reports\local
python manage.py runserver --noreload 2> reports\local\backend.log
# En otra terminal:
Get-Content reports\local\backend.log -Wait
```

Para repetir la evidencia completa:

```powershell
.\.venv\Scripts\python.exe scripts\validate_readiness.py
```

Requiere `.env`, PostgreSQL con `CREATEDB` y el puerto 8766 libre. Crea una
base temporal, consulta el endpoint por HTTP y repite el acceso con un proceso
de prueba que apunta a un puerto PostgreSQL local sin servicio. Comprueba
200 → 503 → 200 al restaurar la configuración; no detiene PostgreSQL ni cambia
las credenciales reales. Los tokens y cookies inyectados son marcadores
sintéticos cuya ausencia en respuestas y logs se verifica automáticamente.
Después ejecuta toda la suite Django en otra base aleatoria y elimina su
base temporal. El servidor WSGI del runner es exclusivamente de prueba y
no registra URLs crudas mediante el access logger de la biblioteca estándar.

El JSON `reports/TK17-readiness-<fechaUTC>.json` conserva respuestas, logs
seguros, versiones, commit base, hashes de las fuentes, resultado y salida
de tests. Los logs de cada fase quedan en `reports/TK17-<fechaUTC>/`.
Estado y evidencias: [`reports/BE-CP24.md`](reports/BE-CP24.md).

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
