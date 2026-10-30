# Inicio y Sobre mí independientes

`Perfil.introduction` almacena la presentación breve de Inicio.
`Perfil.biography` conserva el texto completo de Sobre mí y sus datos de contacto.
Ambos se publican en `/api/v1/perfil/` y se incluyen en el contexto MCP de Aubar.
El frontend ya no deduce la presentación del primer párrafo de la biografía.

La migración `0012_perfil_introduction` agrega un campo de texto opcional y
restaura la presentación original del perfil de Nahuel. No modifica la biografía.
El campo se puede editar en Django Admin. La traducción al inglés reutiliza el
texto revisado del catálogo de traducciones existente.

Se aplicó en Supabase, esquema `public`, mediante
`scripts/publish_profile_introduction.py --apply`, después de probar la operación
con rollback. La herramienta guarda un respaldo privado en `backups/`, exige un
plan limitado a esa única migración y comprueba que todos los campos previos del
perfil permanecen iguales. No modifica el esquema privado ni la base local.

Para verlo publicado hay que desplegar primero el backend con el campo nuevo de
la API y luego el frontend. La migración de `public` ya está aplicada; en otros
entornos se aplica con el flujo normal `python manage.py migrate` contra su base.
