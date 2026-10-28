# Aubar Bot · ESP32 en el portfolio

Publicado el 28 de octubre de 2026 por solicitud del propietario del portfolio.
Fuente: https://github.com/aubarcito48/aubar-bot, revisión
`e8454ea277a1cf00a5168490accfc7d2c6310462`.

## Resultado

- Supabase `public`: Aubar Bot es el cuarto proyecto publicado (`aubar-bot`).
- PostgreSQL local: incorporado después de los dos proyectos que ya existían.
- Asociadas Python, C++, Arduino y ESP32. Se agregaron las tres tecnologías
  que faltaban bajo Sistemas embebidos, conservando las tecnologías anteriores.
- Repositorio del proyecto enlazado; no se inventó una demo web para el hardware.
- Imagen del propio repositorio con URL fijada a la revisión verificada.
- No se modificó el proyecto físico, su firmware ni la carpeta `botbar`.

La API de Render devolvió HTTP 200 y `count=4`, incluida la nueva ficha con su
imagen y tecnologías. La imagen devolvió HTTP 200 y `image/png`. El propietario
confirmó que la tarjeta se ve correctamente en el portfolio publicado.

## Integridad de los datos

Se generaron respaldos previos privados en `backups/`, ignorados por Git.
La carga se ejecutó dentro de transacciones con esquema explícito y bloqueo
acotado. Se comprobó que las filas anteriores permanecieran iguales, que no
se alteraran tablas ajenas a la carga y que el esquema `portfolio_django` de
Supabase permaneciera sin cambios. No hubo cambios de esquema, RLS, usuarios
ni permisos.

La repetición del comando conservó los mismos registros y relaciones. Un
ensayo local sin `--apply` verificó la reversión antes de la carga definitiva.
Tres pruebas aisladas con SQLite en memoria comprobaron idempotencia,
protección de ediciones existentes y traducción sin modificar URLs. La carga
real y sus invariantes se verificaron también contra PostgreSQL.

Evidencias sin credenciales:

- `reports/aubar-bot-local-publication.json`
- `reports/aubar-bot-supabase-publication.json`

## Idiomas y despliegue

La descripción original está en español. Se incorporaron la traducción de la
ficha y de Sistemas embebidos a `portfolio/localization.py`.

**Pendiente:** publicar estos cambios del backend para que la nueva ficha se
traduzca con `?lang=en`. Hasta entonces la API online mantiene el texto español
también en inglés, salvo las etiquetas que ya estaban traducidas.

No hace falta desplegar el frontend para mostrar el proyecto: las tarjetas
se cargan desde la API. Los cambios de contenido posteriores pueden realizarse
desde Django Admin; el comando de carga rechaza sobrescribir ediciones distintas.

## Comandos de carga

La carga ya se ejecutó; no es necesario repetirla.

```powershell
# Ensayo local: copia previa, carga, verificación y rollback.
.\.venv\Scripts\python.exe scripts/publish_aubar_project.py --target local

# Aplicar en local o Supabase, solo cuando corresponda.
.\.venv\Scripts\python.exe scripts/publish_aubar_project.py --target local --apply
.\.venv\Scripts\python.exe scripts/publish_aubar_project.py --target supabase --apply
```

El script usa los settings explícitos de cada destino y no imprime secretos.
El comando base también exige `--schema public` o `--schema portfolio_django`;
seleccionar otro esquema representa otro destino, no una copia del publicado.
