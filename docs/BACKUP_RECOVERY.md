# TK19 — Copias, restauración y rollback

Responsable: Nahuel Argandoña. Caso: BE-CP26. Procedimiento validado el
19/10/2026 en PostgreSQL 18.3, Python 3.14.3 y Django 6.1.2.
Resultado: [`../reports/BE-CP26.md`](../reports/BE-CP26.md).

## Alcance y almacenamiento

El ensayo crea un clúster PostgreSQL nuevo que escucha exclusivamente en
`127.0.0.1`, usa un puerto libre y autenticación SCRAM con credenciales efímeras.
Crea dos bases nuevas: origen sintético y destino de recuperación. No acepta
conexiones de origen/destino como argumentos, no carga `.env` ni `.env.supabase`
y no consulta desarrollo, Render ni Supabase. Los archivos `.env*` se verifican
como bytes opacos mediante hash antes/después; no se analizan sus credenciales.

Los dumps, manifiestos completos, logs y clúster detenido quedan dentro de
`backups/recovery-<fechaUTC>-<id>/`, ignorado por Git. En Windows, el script
restringe la ACL de la carpeta al usuario ejecutor y SYSTEM antes de crear la
copia; en POSIX aplica modo 0700. El administrador del sistema conserva sus
facultades administrativas. La contraseña temporal de initdb se elimina después
de usarla y no se imprime. Nunca publicar dumps, secretos ni logs completos.

Política operativa para copias reales del portfolio:

- Responsable y acceso: Nahuel y únicamente operadores expresamente autorizados.
  El rol usado para copiar debe poder leer todas las tablas y secuencias del
  esquema, incluidos registros no publicados; un rol con RLS no debe producir
  silenciosamente una copia parcial. No dar acceso a `anon`/`authenticated`.
- Frecuencia: diaria cuando haya ediciones y siempre antes de migraciones o
  despliegues que cambien datos/esquema. Conservar 7 diarias, 4 semanales y 3
  mensuales; mantener la copia previa a un incidente hasta cerrar su revisión.
- Mantener una copia local protegida y otra fuera del equipo, cifrada y con
  acceso restringido. Cifrar el disco o volumen que contiene la copia local;
  `pg_dump -Fc` comprime, **no cifra**. Guardar la clave de cifrado separada.
- Guardar junto a cada copia fecha UTC, commit, versión PostgreSQL/cliente,
  alcance/esquema, tamaño, SHA-256, conteos y revisión de migraciones. Proteger el
  manifiesto igual que el dump si contiene información interna.
- Comprobar tamaño/hash y catálogo tras generar cada copia; ensayar restauración
  mensualmente y después de cambiar el procedimiento. Purgar solo copias vencidas
  de la ubicación verificada, nunca bases activas ni directorios calculados sin
  comprobar su ruta. La retención y la réplica externa son política documentada;
  este script no configura un scheduler, almacenamiento remoto ni borrados.

En Supabase Free no se debe depender de copias diarias descargables del proveedor:
mantener exportaciones propias protegidas. Una copia previa a la transferencia
no protege las ediciones posteriores del Admin. Este ensayo prueba el mecanismo
con datos conocidos; no equivale a restaurar un backup real de producción ni a
comprobar su almacenamiento externo.

## Repetir el ensayo completo

Requisitos: Git con la revisión compatible disponible, el entorno Python del
backend y binarios de PostgreSQL de la misma versión mayor del servidor o más
recientes para generar el dump. No se requiere arrancar el servicio PostgreSQL
local existente ni cambiar archivos de entorno. El script no funciona como root
en POSIX porque `initdb` lo impide; ejecutar como usuario ordinario.

Desde la raíz del backend, PowerShell:

```powershell
.\.venv\Scripts\python.exe scripts/validate_recovery.py --pg-bin 'C:/Program Files/PostgreSQL/18/bin'
if ($LASTEXITCODE -ne 0) { throw 'Ensayo fallido; revisar el reporte, no restaurar producción.' }
```

Para probar otra versión compatible, agregar `--rollback-ref <commit>`.
El script rechaza diferencias entre modelos/migraciones de esa versión y HEAD,
y cambios locales en esos archivos. No cambia la rama ni el checkout actual:
extrae el código anterior en la carpeta privada, verifica qué paquete importa y
ejecuta un proceso Django independiente contra la base recuperada.

Secuencia ejecutada y registrada:

1. Proteger la carpeta, desactivar dotenv y descartar credenciales heredadas.
2. `initdb --auth=scram-sha-256` y `pg_ctl start` en el directorio nuevo; comprobar
   `data_directory` real antes de trabajar. No reutilizar un clúster existente.
3. Crear origen y destino con `CREATE DATABASE ... TEMPLATE template0`.
4. Crear `portfolio_django` en origen, aplicar migraciones y cargar datos
   sintéticos conocidos. Solo se reemplazan las semillas de ese origen desechable.
5. Obtener referencia: todas las filas de todas las tablas mediante `to_jsonb`,
   orden canónico, hashes, conteos, secuencias (`last_value`, `is_called`),
   relaciones y respuestas de API. Se incluyen borradores y microsegundos.
6. `pg_dump --format=custom --no-password --file <copia>` del origen nuevo.
   No hay otros escritores y se compara el origen otra vez al terminar.
7. `pg_restore --list <copia>` para revisar el contenedor; esto por sí solo no
   acredita recuperación. Revalidar que el destino es nuevo y no contiene objetos.
8. `pg_restore --no-owner --no-privileges --exit-on-error --single-transaction
   --no-password --dbname <destino_nuevo> <copia>`. Nunca `--clean` ni `--create`
   contra una base existente. Ante fallo, detenerse: no reintentar sobre un destino
   parcialmente modificado sin revisarlo; usar otra base nueva.
9. Comparar referencia/origen/restaurado; comprobar endpoints y migraciones con
   Django actual. Repetir con el código anterior, sin revertir migraciones.
10. Detener el clúster en `finally` y conservar evidencias. Si el reporte indica
    `clusterStopped=false`, verificar la ruta absoluta privada y detener **solo**
    ese clúster con `pg_ctl -D <directorio_verificado> -m fast -w stop`.

La restauración contiene todas las tablas Django del ensayo. No hay usuarios
reales, sesiones reales ni datos extraídos de las bases existentes. No se ejecuta
`migrate` en destino antes de restaurar: el dump contiene esquema e historial.
La prueba de endpoints usa el cliente Django contra PostgreSQL recuperado, no
levanta Gunicorn ni contacta una URL pública.

## Copia de producción: preparación y comandos

Aplicar solo en una operación autorizada. Estos comandos no se ejecutaron contra
producción en TK19. Para Supabase, copiar el esquema de aplicación
`portfolio_django`, no restaurar esquemas gestionados `auth`, `storage`, etc.
Verificar previamente dependencias fuera del esquema y documentarlas por separado.
La copia de aplicación incluye Django Auth/sesiones para recuperación; no es el
fixture de transferencia que deliberadamente los excluye.

Preparar un archivo `pgpass.conf` privado fuera del repositorio, con formato
`host:puerto:base:usuario:contraseña`; ingresarlo desde el editor, no desde el chat.
Escapar `:` y `\` según libpq; restringir ACL al operador (en POSIX, 0600).
No pegar una URI con contraseña en comandos. Abrir una sesión de shell dedicada,
configurar variables PG no secretas desde los valores reales y apuntar
`PGPASSFILE` al archivo protegido. Verificar explícitamente host y base antes de
ejecutar. `PGSSLMODE=require` cifra; para autenticar también el servidor usar
`verify-full` con la CA correspondiente.

```powershell
# ORIGEN: Supabase, solo lectura. Usar nombres reales en los placeholders.
$env:PGHOST = '<host-session-pooler>'
$env:PGPORT = '5432'
$env:PGDATABASE = 'postgres'
$env:PGUSER = '<usuario-autorizado>'
$env:PGSSLMODE = 'require'
$env:PGPASSFILE = '<ruta-absoluta-al-pgpass-privado>'
$backupFile = '<ruta-protegida-nueva>/portfolio-<fechaUTC>.dump'
if (Test-Path -LiteralPath $backupFile) { throw 'No sobrescribir una copia existente.' }
& 'C:/Program Files/PostgreSQL/18/bin/pg_dump.exe' --no-password --format=custom --schema=portfolio_django --file $backupFile
if ($LASTEXITCODE -ne 0) { throw 'Copia fallida.' }
Get-FileHash -Algorithm SHA256 -LiteralPath $backupFile
& 'C:/Program Files/PostgreSQL/18/bin/pg_restore.exe' --list $backupFile
if ($LASTEXITCODE -ne 0) { throw 'Archivo ilegible.' }
```

El catálogo y manifiesto de una copia real también son privados: no redirigirlos
a logs públicos de CI. Cerrar la sesión dedicada después. La autenticación del
ensayo automatizado usa credenciales efímeras en el entorno del subproceso y no
necesita `pgpass.conf` ni modificar el entorno de la sesión del usuario.

## Recuperar el servicio ante un fallo

1. Identificar incidente, última copia válida y commit/esquema asociado. Detener
   escritores/ediciones y conservar el estado fallido para diagnóstico; no borrar
   la base afectada. Restaurar una copia anterior pierde los cambios posteriores:
   definir el corte y reconciliar esos cambios antes de abrir escritura.
2. Verificar integridad, alcance y procedencia confiable del dump. Una restauración
   ejecuta definiciones SQL del archivo: no usar archivos de origen desconocido.
3. Preparar una **base independiente nueva y vacía**, verificar identidad, SSL,
   permisos y catálogo sin tablas previas. Restaurar con el comando anterior,
   reemplazando `PGHOST`, `PGDATABASE`, `PGUSER` y `PGPASSFILE` por los del destino
   de recuperación. No dejar que siga seleccionada la conexión de origen.
4. `--no-owner --no-privileges` evita depender de roles/grants históricos. No
   prueba ni reconstruye la política de permisos de producción: establecer owner,
   rol de runtime y grants mínimos, revisar acceso al esquema y secretos externos
   por separado. Roles/tablespaces globales, archivos de Storage, imágenes locales,
   variables Render y claves no están incluidos en el respaldo del esquema.
5. Conectar un backend aislado al destino y conservar el mismo `search_path`.
   Ejecutar `check`, revisar `showmigrations --plan`, comparar cantidades/valores,
   PKs/FKs/M2M/secuencias y consultar health, listados/detalles, borradores,
   Admin/CSS y permisos. No crear tablas ni aplicar nuevas migraciones antes de
   comprobar la versión recuperada.
6. Ensayar la versión de código que corresponde a la copia. Revisar `check --deploy`
   con su configuración real. Tras la validación y autorización de puesta en
   servicio, cambiar la conexión privada de Render a la base recuperada, reiniciar
   y comprobar frontend, CORS y persistencia. Mantener la base anterior intacta
   hasta cerrar el incidente. La selección del destino/cambio de tráfico no se
   automatiza en este ensayo.

## Rollback y migraciones

**Volver a un commit anterior del código no revierte los datos ni las migraciones.**
El rollback ensayado usa `42e68bb` contra el esquema actual porque sus modelos e
historial de migraciones son idénticos a `9c64b61`. No hace `migrate` hacia atrás.
Esto verifica consultas de una versión compatible, no que cualquier commit viejo
funcione ni que el despliegue previo de Render restaure su base automáticamente.

Si hay diferencias de esquema, el script se detiene. Revisar `migrate --plan`
en una copia aislada: dependencias, operaciones irreversibles, `RunPython` sin
reversa y pérdida de columnas/filas al eliminar tablas. Una migración marcada
reversible técnicamente también puede perder información. Las semillas reversas
de este proyecto deben revisarse porque pueden borrar contenido por sus claves;
no asumir que ejecutar `migrate portfolio <anterior>` es una recuperación segura.

Preferir una corrección hacia adelante o cambios de esquema compatibles durante
la transición. Si se necesita volver a un esquema incompatible, restaurar una
copia asociada al código anterior en una base nueva y reconciliar las escrituras
posteriores. No usar `--fake`, editar `django_migrations`, borrar tablas ni ejecutar
reversas destructivas sobre producción para forzar coincidencia.

RPO orientativo con copia diaria: hasta 24 h de cambios, sujeto a que la copia
realmente se genere y verifique. Los tiempos de este ensayo pequeño **no son** un
RTO de producción: volumen, red, permisos, plan del proveedor y reconciliación
deben medirse para acordar un objetivo real.

Fuentes oficiales:

- [pg_dump 18](https://www.postgresql.org/docs/18/app-pgdump.html)
- [pg_restore 18](https://www.postgresql.org/docs/18/app-pgrestore.html)
- [Contraseñas libpq](https://www.postgresql.org/docs/18/libpq-pgpass.html)
- [Migraciones Django](https://docs.djangoproject.com/en/6.1/topics/migrations/)
- [Respaldos Supabase](https://supabase.com/docs/guides/platform/backups)
