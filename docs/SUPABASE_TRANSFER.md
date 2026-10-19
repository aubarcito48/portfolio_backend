# PostgreSQL local → Supabase: transferencia verificada

Estado al 19/10/2026: **transferencia real completada y comparada**, con autorización
expresa del propietario. El preflight no encontró tablas de la aplicación ni el
esquema privado. Se conservaron los objetos internos de Supabase. No repetir
`import-new`: el destino ya contiene la aplicación.

Se respaldó PostgreSQL local antes de escribir en Supabase. El respaldo completo
y el fixture se obtuvieron desde la misma instantánea exportada de PostgreSQL.
Evidencia sin secretos: `reports/supabase-transfer-execution.json`.
Artefactos privados: `backups/transfer-20261019T163611Z/`.

## Diseño revisado contra el proyecto

Se transfieren únicamente los siete modelos de `portfolio`: Perfil, Tecnologia,
Experiencia, Formacion, Proyecto, EnlaceProyecto y Enlace. El fixture incluye
PKs, todos los campos serializables, borradores, orden, fechas, las tecnologías
M2M de cada proyecto y la FK de cada enlace adicional a su proyecto.
No exporta `auth`, `sessions`, `admin`, `contenttypes` ni `django_migrations`.

**El respaldo completo sí conserva las tablas locales internas**, para poder
recuperar el origen; nunca se restaura automáticamente en Supabase. La carga
remota utiliza exclusivamente el fixture de `portfolio`.

Se utiliza un esquema nuevo y privado `portfolio_django`, separado de `public`,
`auth`, `storage` y otros esquemas de Supabase. La importación se niega si ese
esquema ya existe, aunque esté vacío, o si detecta tablas Django/portfolio en
otro esquema. Los objetos ajenos se inventarían y no se tocan. Si hay contenido
previo, detenerse y revisar el informe: no hay `flush`, `DROP`, borrado ni fusión.

Cuatro migraciones históricas crean contenido inicial: `0002`, `0004`, `0008`
y `0009`. Ejecutarlas normalmente y después usar `loaddata` puede provocar
choques de PK/slug/singleton o sobrescritura de semillas. Por eso `import-new`
aplica las migraciones existentes y **omite en memoria únicamente esas cuatro
funciones de semilla de contenido**. No cambia archivos históricos. Conserva
las operaciones de esquema y la migración `0010_content_editors`.
Las semillas se sustituyen por el fixture local completo, no por ediciones ni
borrados en el destino. Si cambian esas funciones, el comando se detiene.

La creación del esquema, migración, `loaddata` y comparación inicial se hacen
en una transacción PostgreSQL, con un advisory lock para coordinar ejecuciones
de esta herramienta. Un error revierte la instalación nueva. Esto no autoriza
escribir en un esquema previo ni coordina herramientas externas: mantener el
destino fuera de uso hasta completar y verificar la transferencia.

## Configuraciones separadas

- **ORIGEN LOCAL:** `--settings=config.settings_local_transfer`. Lee `.env`
  explícitamente sin editarlo, fuerza un host loopback y evita heredar una
  conexión remota del shell. Usa sus variables `POSTGRES_*`.
- **DESTINO SUPABASE:** `--settings=config.settings_supabase`. Solo lee
  `.env.supabase`, sin fallback a `.env` ni a credenciales locales heredadas.
  Fuerza producción, `DEBUG=False`, SSL y `search_path` privado. Todas las
  conexiones nuevas seleccionan `portfolio_django, pg_catalog`.

Se completó `.env.supabase` con los datos proporcionados y una
`DJANGO_SECRET_KEY` generada con aleatoriedad criptográfica, sin imprimirla.
La contraseña se ingresa o reemplaza directamente en la línea
`POSTGRES_PASSWORD=` del archivo privado, desde el editor. Este archivo y
`backups/` están ignorados por Git; `.env` local permanece intacto.
La plantilla compartible es `config/supabase.env.example`.

La transferencia no necesita dominio Render: se configuró
`DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1`. Antes de publicar, revisar:

- `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD` rotada,
  `POSTGRES_HOST`, `POSTGRES_PORT`, desde **Connect** del proyecto correcto.
- `DJANGO_SECRET_KEY` de producción y `DJANGO_ALLOWED_HOSTS` del backend.
- Los orígenes CORS/CSRF HTTPS finales cuando corresponda.
- `POSTGRES_SSLMODE=require` como mínimo. Para verificar identidad del
  servidor, usar `verify-full` y `POSTGRES_SSLROOTCERT` con la CA de Supabase.

Para migraciones se prefiere conexión directa. Si la red local solo tiene IPv4
y no hay acceso directo IPv4, usar Session pooler, no Transaction pooler.
Los datos de host/usuario se copian de Connect, no se deducen de la región.
La captura corresponde a Session pooler en puerto 5432. No usar URI con la
contraseña en la línea de comandos ni asumir que los corchetes del ejemplo
son parte de ella. No se requiere `supabase-py` ni una service-role API key.

## Comandos reproducibles (PowerShell)

**La transferencia real ya terminó; no repetir el import en este destino.**
Estos pasos describen una instalación nueva. Desde `portfolio_backend`,
activar el entorno virtual o usar el ejecutable completo como se indica.
Elegir una carpeta nueva por ejecución; no reutilizar una que ya contenga dumps.

```powershell
$transferRun = 'backups/transfer-' + (Get-Date -Format 'yyyyMMdd-HHmmss')
New-Item -ItemType Directory $transferRun
```

### 1. SUPABASE — primer acceso: solo inspección

Con autorización para el destino elegido, el comando inicia una transacción
read-only, inventaría relaciones por esquema y guarda el catálogo sin mostrar
contraseñas, hosts, usuarios ni filas privadas en consola:

```powershell
.\.venv\Scripts\python.exe manage.py transfer_portfolio preflight --file "$transferRun/supabase-before.json" --settings=config.settings_supabase
if ($LASTEXITCODE -ne 0) { throw 'STOP: revisar configuración o contenido existente; no migrar.' }
```

Revisar el JSON privado: `targetSchemaExists` debe ser `false` y
`djangoObjectsOutsideTarget` debe estar vacío. Los esquemas internos de
Supabase pueden tener objetos y datos; no son una base «vacía» y no se eliminan.
No se leen sus filas. Si el proyecto sigue Unhealthy, resolver su disponibilidad
antes de avanzar; no asumir que ese estado se debe al código Django.

### 2. LOCAL — respaldo completo recuperable

Pausar cambios en el Admin local y cualquier otro escritor hasta finalizar
exportación y comparación. `pg_dump` toma su propia instantánea; el fixture
toma otra instantánea consistente, por lo que el origen debe permanecer estable
para que ambos correspondan al mismo estado lógico.

```powershell
.\.venv\Scripts\python.exe manage.py transfer_portfolio backup --file "$transferRun/local-full.dump" --pg-dump "C:/Program Files/PostgreSQL/18/bin/pg_dump.exe" --settings=config.settings_local_transfer
if ($LASTEXITCODE -ne 0) { throw 'STOP: respaldo local fallido.' }
```

Usar `pg_dump` de la misma versión mayor o superior al servidor local. El
comando pasa credenciales por el entorno del proceso hijo, no por argv. Verificar
que el archivo es legible (guardar el catálogo, sin pegarlo públicamente):

```powershell
& 'C:/Program Files/PostgreSQL/18/bin/pg_restore.exe' --list "$transferRun/local-full.dump" > "$transferRun/backup-catalog.txt"
if ($LASTEXITCODE -ne 0) { throw 'STOP: respaldo ilegible.' }
```

Conservar una copia protegida fuera del equipo. `--list` verifica el contenedor,
no sustituye un ensayo de restauración. No usar este dump completo como método
de carga en Supabase.

### 3. LOCAL — dumpdata de portfolio

```powershell
.\.venv\Scripts\python.exe manage.py transfer_portfolio export --file "$transferRun/portfolio.json" --settings=config.settings_local_transfer
if ($LASTEXITCODE -ne 0) { throw 'STOP: exportación local fallida.' }
```

Internamente ejecuta `dumpdata portfolio --all` en una instantánea repeatable-read
de solo lectura, con stream UTF-8 explícito para Windows. Guarda los datos en
archivo privado e imprime solo cantidades, número de relaciones y hash.
No usar redirección de consola ni editar el fixture. Los PKs y las referencias
se conservan; no se utilizan natural keys de modelos internos.

### 4. SUPABASE — migraciones + loaddata, SOLO instalación nueva

Esta etapa **es escritura y requiere autorización para cada instalación nueva**.
La ejecución registrada fue autorizada y ya finalizó. Revisar primero el
informe preflight; el comando vuelve a comprobar
el destino inmediatamente antes de crear algo:

```powershell
.\.venv\Scripts\python.exe manage.py transfer_portfolio import-new --file "$transferRun/portfolio.json" --settings=config.settings_supabase
if ($LASTEXITCODE -ne 0) { throw 'STOP: instalación no completada; no publicar el backend.' }
```

Ejecuta `migrate` y `loaddata` de Django con el tratamiento de semillas descrito
arriba. No ejecutar `migrate` y `loaddata` manualmente como reemplazo de este
paso; perderías las guardas de esquema nuevo y el tratamiento de semillas.
No ejecutar `supabase db push` ni generar otro historial paralelo para estos
modelos: el historial autoritativo es `portfolio/migrations/`.

### 5. SUPABASE — comparación posterior de solo lectura

```powershell
.\.venv\Scripts\python.exe manage.py transfer_portfolio compare --file "$transferRun/portfolio.json" --settings=config.settings_supabase
if ($LASTEXITCODE -ne 0) { throw 'STOP: diferencias detectadas; no habilitar tráfico.' }
```

Compara cantidades por los siete modelos y el total de enlaces M2M, y un hash
canónico de **todos los PKs, campos y relaciones**, no solo de los conteos.
Incluye fechas, borradores, orden y claves foráneas; ordena las listas M2M para
no confundir diferencias de representación con diferencias de contenido.
No imprime valores privados si hay diferencias. `match=true` confirma igualdad
con el fixture exportado, no con cambios locales posteriores: mantener el
origen congelado o exportar otra instantánea y compararla en un archivo nuevo.

No reejecutar `import-new` para actualizar datos: se niega ante un esquema
existente. No hay sobrescritura automática, ni política de sincronización.

### 6. SUPABASE — administrador de producción separado

Después de verificar la importación, crear una cuenta nueva de forma interactiva:

```powershell
.\.venv\Scripts\python.exe manage.py createsuperuser --settings=config.settings_supabase
```

No pasar contraseña como argumento ni reutilizar usuarios locales. Las tablas
internas, permisos y el grupo «Editores de contenido» se crean **desde las
migraciones del destino**, no se copian del origen. No se copian sesiones ni
historial del Admin. Un usuario de Django Admin no es un usuario de Supabase Auth.

## Seguridad y puesta en servicio posterior

No exponer `portfolio_django` mediante la Data API de Supabase ni otorgar acceso
a `anon`/`authenticated`. El frontend seguirá consumiendo la API Django, que
filtra borradores y aplica sus permisos. La herramienta revoca acceso de PUBLIC
al esquema nuevo; no modifica grants ni políticas de otros esquemas. Revisar
Advisors y la configuración de esquemas expuestos antes de publicar. RLS en
esquemas privados puede agregarse como defensa adicional con un rol de runtime
limitado y políticas acordes; no se agregan políticas genéricas basadas en
Supabase Auth a un backend que utiliza Django Auth.

Usar la cuenta privilegiada solo para instalación. Antes de producción definir
un rol de runtime con mínimos permisos para consultas, sesiones y operaciones
del Admin. No se crean roles ni se cambian permisos de objetos existentes
automáticamente. No habilitar grants amplios para «resolver» errores.

**El backend desplegado debe seleccionar el mismo esquema privado**, usando
`DJANGO_SETTINGS_MODULE=config.settings_supabase` y el archivo privado como
secret file accesible al servicio, o una configuración equivalente revisada.
Cambiar solo `POSTGRES_HOST` en los settings base dejaría `search_path` apuntando
al esquema incorrecto. No se configuró Render ni se cargaron secretos allí.

Los campos de imágenes/enlaces son rutas o URLs; el fixture no copia archivos
del frontend ni Storage. Verificar `/health/`, Admin, CORS/CSRF y contenido
publicado/borradores cuando se habilite el backend de destino.

## Validación realizada y límites

Se instalaron globalmente las skills oficiales `supabase` y
`supabase-postgres-best-practices` para Codex y se revisaron sus instrucciones,
changelog y guías de conexiones, seguridad y observabilidad. La operación real
se realizó después de la autorización explícita y del preflight satisfactorio.

Un ensayo en un clúster PostgreSQL local independiente, con credenciales
sintéticas y `.env` desactivado, completó backup legible, exportación,
instalación/importación y comparación exacta. Se usó un perfil con PK 41 para
detectar conflictos con la semilla habitual de PK 1. Incluyó borradores y M2M.
Un usuario sintético del origen no apareció en destino. Un segundo intento de
importación fue rechazado y la comparación posterior siguió coincidiendo.
La suite completa pasó con 111 pruebas. Evidencia local sin secretos reales:
`reports/supabase-transfer-validation.json`.

La ejecución real verificó PostgreSQL local 18.3 y Supabase PostgreSQL 17.11,
SSL activo, cero migraciones pendientes y `/health/` HTTP 200 mediante el cliente
Django conectado al destino. No representa una prueba HTTP de Render.
Se compararon todos los campos serializados, PKs y relaciones: 1 perfil,
24 tecnologías, 2 proyectos, 1 enlace de proyecto, 2 enlaces, 0 experiencias,
0 formaciones y 12 relaciones proyecto-tecnología. El origen exportado antes y
después coincide y el hash del `.env` local permanece igual.

En destino hay cero usuarios Django, sesiones e historial Admin. Los permisos
y el grupo de editores fueron generados por migraciones propias del destino.
Los roles `anon` y `authenticated` no tienen USAGE sobre el esquema privado.
El inventario de objetos fuera de ese esquema permanece igual al preflight;
no se inspeccionaron filas privadas de los servicios internos de Supabase.

Pendiente de producción: rotar la contraseña compartida, crear el administrador
por separado, definir el rol de runtime con mínimos permisos, configurar el
dominio real/CORS/CSRF y verificar Render cuando se despliegue. No se desplegó
Render ni se creó un administrador automáticamente.
El dump completo real se validó con `pg_restore --list`; no se realizó una
restauración completa de ese respaldo real. El ensayo previo utilizó datos
sintéticos en un clúster local aislado.

Fuentes oficiales consultadas:

- https://supabase.com/docs/guides/database/connecting-to-postgres
- https://supabase.com/docs/guides/api/securing-your-api
- https://supabase.com/docs/guides/monitoring-and-debugging
- https://supabase.com/changelog
- https://docs.djangoproject.com/en/6.1/ref/django-admin/
