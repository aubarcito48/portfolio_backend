# Curriculum Vitae · Enlace dinámico

## Versiones en español e inglés

La presentación y Contacto agrupan los enlaces como
`Curriculum Vitae: Español | Inglés`. Ambos se obtienen de la API y abren
Drive en una pestaña nueva. Al cambiar el idioma se traducen las etiquetas,
pero ambas versiones permanecen disponibles.

- Español: tipo `cv`, URL original indicada abajo.
- Inglés: tipo `cv_en`, etiqueta de administración `Curriculum Vitae (English)`,
  URL `https://drive.google.com/file/d/1sA7CrGlnX3rSwsffLnBrR9BJzgM-JNUK/view?usp=sharing`.

Ambos registros están publicados en PostgreSQL local y Supabase `public`.
El esquema privado permanece sin cambios. Para actualizar cualquiera de
las URLs se edita su enlace profesional en Django Admin.
`load_curriculum_vitae --language en --schema public` permite cargar la
versión inglesa con las mismas protecciones de respaldo, transacción e
idempotencia. Sin `--language` el comando conserva el comportamiento español.
Se verificaron tres pruebas de backend, ambos idiomas de la API de Render
y la agrupación del frontend en desktop y celular.

Publicado el 28 de octubre de 2026 por solicitud del propietario. El modelo
`Enlace` y su Django Admin ya admitían este contenido: `type` no está limitado
a GitHub o LinkedIn. No se modificaron modelos, tablas, permisos ni migraciones.

Se agregó un enlace publicado de tipo `cv`, etiqueta `Curriculum Vitae` y URL:

https://drive.google.com/file/d/1Y24Qqs4Be3twPaFE7_Y1Fkk89YGlbLYe/view?usp=sharing

El orden coloca el CV después de GitHub y LinkedIn. La URL se guarda en
PostgreSQL local y en Supabase `public`, que alimenta la API online. El PDF
permanece en Drive; no se cargaron archivos a Supabase Storage.

La carga incluye respaldo previo en `backups/` (ignorado por Git), transacción,
esquema explícito, validación Django y verificación de idempotencia. Los enlaces
anteriores y los del esquema privado `portfolio_django` quedaron sin cambios.
La API de Render devolvió HTTP 200, `count=3` y el enlace CV con `lang=es` y
`lang=en`. La etiqueta latina se conserva en ambos idiomas.

Angular ya recorre los enlaces de la API, por lo que no necesita enlaces fijos
ni un despliegue para mostrarlo en la presentación y en Contacto. Aubar recibe
el enlace dentro de su contexto público cuando se renueva su caché de un minuto.

Para actualizarlo: Django Admin → Enlaces profesionales → Curriculum Vitae.
Editar la URL existente conserva su posición y evita duplicados. El comando de
carga se niega a sobrescribir un CV que haya sido editado.

La carga ya está realizada; estos comandos son una referencia de mantenimiento:

```powershell
.\.venv\Scripts\python.exe manage.py load_curriculum_vitae --schema public --settings=config.settings_local_transfer
.\.venv\Scripts\python.exe manage.py load_curriculum_vitae --schema public --settings=config.settings_supabase
```

`--dry-run` revierte la carga después de validarla. Dos pruebas en una base
SQLite en memoria verificaron publicación, orden, repetición y protección de
ediciones; la publicación real se verificó contra PostgreSQL y la API de Render.
