# StitchWeather publicado

Fecha: 25/10/2026. El responsable proporcionó los repositorios frontend y
backend y la demo, y solicitó incorporar el proyecto a Supabase para el
portfolio desplegado.

Se agregó `stitchweather` como tercer proyecto publicado en el esquema `public`.
La API de Render pasó de dos a tres proyectos, y el frontend de Vercel mostró
la nueva tarjeta sin necesitar otro despliegue. `portfolio_django` quedó sin
cambios; es un esquema distinto y no se debe asumir que sus datos son los del
servicio publicado.

La descripción se basa en los README de los repositorios: Angular, Tailwind CSS,
Python y Django; búsqueda de ciudades, geolocalización, pronóstico de
OpenWeather y recomendaciones de Groq. Se asociaron cinco tecnologías ya
publicadas, sin crear ni modificar tecnologías. Se incluyeron la demo y ambos
repositorios. La imagen usa el archivo público de la propia app:
`https://app-clima-ecru.vercel.app/app-clima.png`. Depende de que ese archivo
permanezca disponible en futuros despliegues de la app del clima.

## Ejecución y verificación

El comando `load_stitchweather` valida los datos con los modelos Django, usa una
transacción y se detiene ante contenido existente que difiera. La ejecución se
envolvió en otra transacción para verificar, antes del commit, que los registros
anteriores y todo el esquema privado permanecieran iguales. Se guardó una
instantánea previa de los datos de portfolio en `backups/stitchweather-*/`,
ignorada por Git. No se cambiaron tablas, permisos, políticas ni usuarios.

Se ejecutó dos veces, manteniendo el mismo ID y las mismas relaciones: tres
proyectos, un nuevo enlace adicional y cinco nuevas relaciones de tecnologías.
La API pública devolvió HTTP 200 y `count=3`. Playwright verificó la tarjeta
publicada, la carga real de su imagen y la ausencia de desbordamiento horizontal
en móvil (390 px). Se revisaron las capturas de escritorio y móvil.

Evidencias:

- `reports/stitchweather-load.json`
- `reports/stitchweather-publication.json`
- `reports/stitchweather/card-desktop.png` y `card-mobile.png` (evidencia local)

## Idioma

La ficha está en español. El backend utiliza un catálogo estático para traducir
el contenido a inglés: el texto nuevo conserva el español también con `lang=en`
hasta agregar sus traducciones a `portfolio/localization.py` y desplegar el
backend. No se modificó ese catálogo ni se realizó un despliegue en esta carga.

## Repetición

No es necesario repetir la carga. Para verificarla con las mismas credenciales
locales de Supabase y el esquema publicado explícito:

```powershell
.\.venv\Scripts\python.exe manage.py load_stitchweather --schema public --publish --settings=config.settings_supabase
```

Las ediciones posteriores pueden hacerse desde Django Admin. El comando no
sobrescribe cambios que difieran de esta primera publicación.
