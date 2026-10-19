# Verificar la base activa en Render sin modificar datos

La API publicada y `/health/` responden 200, pero no exponen la identidad de la
base. Igualdad de contenido tampoco demuestra que Render use la misma instancia.
La configuración local solo admite PostgreSQL (sin fallback SQLite); confirmar el
servicio desplegado requiere ejecutar la comprobación dentro de ese servicio.
No imprimir `DATABASES`, variables de entorno, URI, contraseñas ni `diffsettings`.

## Comprobación completa

Con esta versión del código disponible en Render, desde Shell del servicio y la
carpeta de `manage.py`, ejecutar **sin seleccionar settings locales ni Supabase**:

```sh
python manage.py verify_runtime_database
```

El comando usa los settings activos del proceso: conexión `default`, motor,
host/usuario/proyecto esperados (solo booleanos), esquema `portfolio_django`, SSL
del cliente al pooler, siete conteos, relaciones y comparación canónica de todos
los campos serializados con `reports/supabase-transfer-execution.json`.
Ejecuta una transacción repeatable-read de solo lectura y SELECT; no ejecuta
migraciones, escrituras ni cambios de permisos. Si detecta SQLite, no lo consulta.
`runningOnRender=true` y `passed=true` son el resultado esperado dentro de Render.
Una diferencia con el reporte puede ser una edición legítima posterior: revisar,
no importar nuevamente ni sobrescribir datos para hacer pasar la comprobación.

No usar `--settings=config.settings_supabase` dentro de Render para esta prueba:
eso cambiaría la configuración que se pretende verificar. La variable
`DJANGO_SETTINGS_MODULE`, si el inicio del servicio la establece mediante un
argumento explícito, debe coincidir con la del proceso web.

## Servicio ya desplegado, antes de incorporar el comando

En una Shell disponible puede pegarse este bloque de solo lectura, que no depende
de archivos nuevos. Usa el mismo módulo por defecto que `config/wsgi.py`:

```sh
python - <<'PY'
import os, json
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()
from django.db import connection, transaction
from django.apps import apps
try:
    db = connection.settings_dict
    result = {
        'runningOnRender': os.getenv('RENDER') == 'true',
        'postgresql': connection.vendor == 'postgresql',
        'expectedSupabaseHost': db.get('HOST') == 'aws-0-us-east-1.pooler.supabase.com',
        'expectedProjectUser': db.get('USER') == 'postgres.lacgvfrppovxounlzzmp',
        'expectedDatabase': db.get('NAME') == 'postgres',
    }
    if result['postgresql']:
        with transaction.atomic():
            with connection.cursor() as cursor:
                cursor.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY')
                cursor.execute('SELECT current_schema()')
                result['expectedPrivateSchema'] = cursor.fetchone()[0] == 'portfolio_django'
                result['sslActive'] = bool(connection.connection.pgconn.ssl_in_use)
            models = apps.get_app_config('portfolio').get_models()
            result['counts'] = {m._meta.label_lower: m._base_manager.count() for m in models}
            project = apps.get_model('portfolio', 'Proyecto')
            result['projectTechnologyRelations'] = project.technologies.through.objects.count()
    print(json.dumps(result, indent=2))
except Exception:
    print('Read-only check failed; details withheld to protect secrets.')
    raise SystemExit(1)
PY
```

Esperado: Perfil 1, Tecnologia 24, Experiencia 0, Formacion 0, Proyecto 2,
EnlaceProyecto 1, Enlace 2 y 12 relaciones. El comando completo además compara
valores y relaciones, que este bloque breve no compara.

Render no ofrece Shell/SSH en Web Services gratuitos. Si no hay Shell, la
comprobación interna queda pendiente hasta disponer de ejecución privada en ese
servicio; puede ejecutarse este comando de solo lectura en un próximo arranque
autorizado y revisar únicamente su JSON seguro en logs. No agregar un endpoint
público de diagnóstico ni publicar credenciales. No se cambió ni desplegó Render.

## Resultado observado el 19/10/2026

- Desde este equipo, el comando contra Supabase pasó con SSL, cantidades,
  valores serializados y relaciones idénticos al reporte de transferencia.
- Las seis respuestas públicas de Render coinciden con las respuestas públicas
  obtenidas directamente desde Django conectado a Supabase; todos los conteos
  visibles coinciden y CORS permite `https://portfolio-nahuel48.vercel.app`.
- Las imágenes recibidas siguen siendo `/assets/nahuel.jpg`, `/assets/dges.png`
  y `/assets/pintaebook.png`; están en el build de Angular sin cambios de bytes.
- La identidad de la conexión **dentro de Render sigue pendiente**: no se dispone
  de una sesión privada del servicio. No presentar estas pruebas como esa evidencia.
- Evidencia: `reports/production-api-verification.json`.

Fuentes: [Render Shell/SSH](https://render.com/docs/ssh),
[conexiones Supabase](https://supabase.com/docs/guides/database/connecting-to-postgres).
