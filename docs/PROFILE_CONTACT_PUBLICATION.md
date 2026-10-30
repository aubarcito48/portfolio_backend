# Biografía y contacto del perfil

El 30/10/2026 se actualizó exclusivamente `biography` del perfil publicado en
`public.portfolio_perfil` de Supabase. Se quitó la presentación repetida del ISPC,
se amplió el texto aprobado sobre APIs, IA, WhatsApp, formularios e IoT y se agregaron
los párrafos `Teléfono: 3517587047` y `Correo: nahuel.cba.48@gmail.com`.

No se crearon columnas ni se cambiaron políticas, permisos o tablas relacionadas.
El perfil del esquema privado y el PostgreSQL local no se modificaron.
El contenido se mantiene en la biografía existente: la API `/api/v1/perfil/`,
el frontend y el contexto MCP de los asistentes leen ese mismo dato.

`scripts/publish_profile_contact.py` guarda una copia privada ignorada por Git en
`backups/`, valida el contenido previo y actualiza en una transacción corta con
comparación del valor anterior. Sin `--apply` revierte la operación. Si el contenido
ya coincide, no cambia `updated_at`. Ante ediciones posteriores no reconocidas,
se detiene para evitar sobrescribirlas.

La respuesta de la API pública de Render se verificó después de la publicación.
El frontend dejó de filtrar el párrafo por texto y de escribir el contacto fijo.
Las futuras ediciones de la biografía se realizan desde Django Admin o Supabase.
Los cambios locales de traducción al inglés y de las instrucciones de Aubar
requieren desplegar el backend; el nuevo contenido español ya está publicado.
