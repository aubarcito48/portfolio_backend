# Formación del ISPC publicada

Fecha: 19/10/2026. El responsable solicitó recuperar la formación del frontend,
confirmó inicio en ISPC en **marzo de 2024** y proporcionó el enlace de Drive.
El frontend anterior mostraba la tecnicatura en curso y su título intermedio
Junior Full Stack Developer. El certificado existente acredita emisión el
01/06/2026. No se usaron las fechas ni la URL de ejemplo de los tests frontend.

Datos publicados:

- Tecnicatura Superior en Desarrollo de Software, Instituto Superior Politécnico
  de Córdoba, en curso desde marzo de 2024.
- Junior Full Stack Developer, ISPC, titulación intermedia finalizada, con fecha
  del certificado 01/06/2026 y el enlace de Drive indicado por el responsable.

El campo DateField requiere un día: `2024-03-01` representa técnicamente el mes
confirmado, no una declaración de que las clases empezaron exactamente el día 1.
El frontend ya muestra fechas con precisión de mes y año. La formación y su
titulación intermedia utilizan el inicio confirmado de la misma formación ISPC.
No fue necesario cambiar modelos, migraciones ni código Angular.

## Ejecución y verificaciones

Se respaldó cada esquema afectado mediante pg_dump custom con una instantánea
compartida con la referencia de portfolio. Las copias y los datos completos están
en `backups/education-update/`, ignorados por Git y con ACL restringida. El comando
crea solo los dos registros aprobados, rechaza duplicados o contenido diferente y
no sobreescribe ediciones posteriores. Se ejecutó dos veces conservando sus PKs.

El PostgreSQL local quedó con dos formaciones publicadas. En Supabase se encontró
que existen dos esquemas de aplicación: `portfolio_django` de la transferencia y
`public`. Después de publicar en el primero, la API aún devolvía cero filas y el
esquema public estaba vacío. Se respaldó y cargó también public; la API publicada
pasó a devolver las dos formaciones, fechas y URL esperadas. Esto señala el esquema
efectivo del despliegue actual; no se cambió su conexión ni se inspeccionó su
proceso interno. No se mezclaron usuarios/sesiones ni otros contenidos entre
esquemas. Los datos previos de portfolio permanecieron iguales fuera de Formación.

La separación entre esos esquemas debe tenerse presente en futuras operaciones:
`config.settings_supabase` selecciona explícitamente `portfolio_django` y no
cambia por sí solo lo que consulta el backend ya desplegado. No cambiar a ciegas
el esquema de Render, porque las cuentas administrativas pueden ser diferentes.

Evidencias:

- `reports/education-load-local.json`
- `reports/education-load-supabase.json`
- `reports/education-load-supabase-public.json`
- `reports/education-publication.json`

Suite backend final: **115 pruebas aprobadas**. API pública de Render: 200 y
`count=2`. Enlace Drive: HTTP 200 sin redirección obligatoria a login en la
comprobación anónima. No se hizo una prueba visual con navegador conectado en
esta ejecución; la verificación publicada se realizó por HTTP.

El frontend consume la API existente: basta recargar la página para obtener los
nuevos registros. No se subió el PDF a Supabase ni se requirió un nuevo despliegue.
Los reportes históricos de transferencia/despliegue que registran cero
formaciones conservan su significado y su fecha. El comparador contra el fixture
original puede señalar diferencias legítimas después de esta actualización;
no reimportar ni sobreescribir datos para forzar esa comparación a coincidir.

## Repetir de forma controlada

En local:

```powershell
.\.venv\Scripts\python.exe manage.py load_approved_education --publish --settings=config.settings_local_transfer
```

En un entorno de producción que ya incluya este comando, usar los settings
activos del servicio para seleccionar su esquema correcto:

```sh
python manage.py load_approved_education --publish
```

La carga ya fue ejecutada; no es necesario repetirla. Sin `--publish`, se crean
borradores y no se despublican registros existentes. Ante un conflicto, el comando
se detiene sin cambios parciales. Las futuras ediciones del contenido se realizan
desde Django Admin; actualizar el enlace allí no requiere mover el archivo PDF.
