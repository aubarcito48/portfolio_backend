# TK18 — Render, Supabase y Vercel

Backend: `https://portfolio-backend-6ecn.onrender.com`.
Frontend: `https://portfolio-nahuel48.vercel.app`.
Resultado y límites de validación: [`../reports/BE-CP25.md`](../reports/BE-CP25.md).

## Proveedor y persistencia

La base elegida es PostgreSQL en Supabase, con acceso mediante Session pooler y
SSL; no se aloja en el disco del servicio Render. El reinicio de ese servicio no
elimina la base externa. El responsable confirmó un reinicio conservando datos.
El esquema Django es `portfolio_django` y no está expuesto a los roles públicos
de la Data API. El frontend accede a Django, nunca directamente a PostgreSQL.

La captura inicial indicaba plan Free; no se consultó la facturación actual.
Supabase recomienda exportaciones y copias externas para Free; los respaldos
diarios administrados corresponden a planes pagos. El respaldo previo a la
transferencia conserva el origen local, no sustituye respaldos posteriores de
producción. Definir una frecuencia de exportación protegida según las ediciones
del Admin y probar la restauración en una base aislada. No restaurar sobre la
base activa para probar un respaldo.

El filesystem de Render Free es efímero y el servicio puede suspenderse por
inactividad. No guardar datos o medios persistentes allí. El plan Free de
Supabase también puede pausar proyectos por baja actividad; revisar el plan y
Dashboard si `/health/` deja de responder, sin concluir que se perdieron datos.

## Configuración reproducible

`manage.py` está en la raíz del repositorio backend: Root Directory vacío.

```text
Build: pip install -r requirements.txt && python manage.py collectstatic --noinput && python manage.py migrate --noinput
Start: python -m gunicorn config.wsgi:application --bind 0.0.0.0:$PORT
Health Check Path: /health/
Python: 3.14.3
```

Si existe Pre-Deploy Command, mover allí `python manage.py migrate --noinput`.
No repetir la transferencia ni aplicar semillas a mano: la base ya está migrada.
Las versiones de Gunicorn y WhiteNoise están fijadas en `requirements.txt`.

Variables necesarias, siempre privadas: `DJANGO_SECRET_KEY`,
`DJANGO_ENVIRONMENT=production`, `DJANGO_DEBUG=False`,
`DJANGO_ALLOWED_HOSTS=portfolio-backend-6ecn.onrender.com`, las cinco
`POSTGRES_*` de conexión, y
`DJANGO_CORS_ALLOWED_ORIGINS=https://portfolio-nahuel48.vercel.app`.
Definir `DJANGO_CSRF_TRUSTED_ORIGINS` para el origen HTTPS del Admin cuando
corresponda; no agregar Vercel por el solo hecho de consumir GET públicos.

Con la configuración separada de Supabase, usar
`DJANGO_SETTINGS_MODULE=config.settings_supabase` y un secret file
`.env.supabase` donde ese módulo lo espera, con los hosts finales reales y
`POSTGRES_SSLMODE=require` (o `verify-full` con CA). Este módulo lee el archivo
privado, así que sus valores deben estar actualizados; no alcanza con cambiar
variables del Dashboard si el archivo conserva otros valores.
Una configuración alternativa debe preservar explícitamente SSL y `search_path`
del esquema privado. `config.settings` por sí solo no añade esas dos opciones.
No cambiar settings de un despliegue funcional sin revisar primero cómo arranca.
No copiar `.env` local al servicio ni versionar los secret files.

## Administración y comprobación

Crear el administrador solo si hace falta, dentro del entorno de producción:

```sh
python manage.py createsuperuser
```

Ingresar la contraseña interactivamente, sin argumentos ni logs. En servicios
gratuitos Render no proporciona Shell/SSH: usar una ejecución privada autorizada
disponible para ese entorno, sin agregar endpoints para crear usuarios. No
ejecutar el comando local con settings de desarrollo esperando crear el usuario
en producción. El responsable ya confirmó su acceso al Admin; no crear duplicados.

La API Angular de producción usa
`https://portfolio-backend-6ecn.onrender.com/api/v1`; desarrollo conserva localhost.
Las imágenes `/assets/...` pertenecen a `public/assets/` del frontend. WhiteNoise
sirve exclusivamente los estáticos Django bajo `/static/`, incluidos los del Admin.

Al actualizar: comprobar `check --deploy`, migraciones, health, Admin/CSS y CORS.
Para un reinicio planificado, guardar antes y después la salida segura de
`verify_runtime_database`, comprobar health y los conteos; no reimportar datos
para hacer coincidir resultados. No activar tests Django sobre producción.

Fuentes oficiales consultadas el 19/10/2026:

- [Django en Render](https://render.com/docs/deploy-django)
- [Limitaciones de Render Free](https://render.com/docs/free)
- [Backups de Supabase](https://supabase.com/docs/guides/platform/backups)
- [Checklist de producción de Supabase](https://supabase.com/docs/guides/deployment/going-into-prod)
