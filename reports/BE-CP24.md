# BE-CP24 — Readiness y logs seguros

**APROBADO — TK17 / BE-HU10 / BE-RF12 / BE-RNF07.**
19/10/2026, 12:49:12–12:49:25, America/Buenos_Aires (UTC−03).
Responsable: Nahuel Argandoña.

## Evidencia y versión

[Informe completo de cierre](TK17-readiness-20261019T154912Z.json): respuestas
HTTP, registros seguros, entorno, revisión base, hashes de fuentes y salida de
la regresión. Commit base `c64ae6a`; TK17 corresponde a cambios locales todavía
sin publicar. El informe identifica los archivos Python ejecutados mediante
SHA-256 y se verificó su coincidencia al cerrar la tarea.

Entorno: Windows 10, Python 3.14.3, Django 6.1.2 y PostgreSQL 18.3.
Servidor WSGI local de prueba con `DEBUG=False` en `127.0.0.1:8766`.
No se usaron datos privados ni se modificó la base de desarrollo.

## Resultados reales

| Caso | Resultado |
| --- | --- |
| PostgreSQL disponible | HTTP 200, `{"status":"ok"}` |
| PostgreSQL inaccesible para el proceso de prueba | HTTP 503, `{"status":"unavailable"}` |
| Restauración de la conexión | HTTP 200, `{"status":"ok"}` |
| Consulta mínima sin escrituras | Test verifica exactamente una sentencia `SELECT 1` |
| Cookies, tokens y credenciales sintéticas | Ausentes de respuestas y logs |
| Error de conexión registrado | `database_unavailable`, `OperationalError`, HTTP 503 |
| Métodos de escritura | Rechazados sin acceder a la base |
| HEAD y OPTIONS | HEAD comprueba la base; OPTIONS solo informa métodos |
| Respuestas sin caché | `Cache-Control` incluye `no-store` |
| Suite completa PostgreSQL | **101 pruebas aprobadas**, código de salida 0 |

La caída real se provocó apuntando un proceso de prueba a un puerto loopback
reservado sin servicio PostgreSQL y usando credenciales sintéticas. Se mantuvo
PostgreSQL funcionando para el resto del equipo. La recuperación se verificó
con un nuevo proceso que recupera la configuración válida, sin cambiar `.env`.
Los tests también simulan fallos de apertura de cursor, de ejecución de SQL y
un resultado inesperado, y repiten el acceso exitoso después del fallo.

Las comprobaciones HTTP no requirieron migraciones ni tablas de aplicación:
el endpoint consulta PostgreSQL directamente y no depende del contenido.
La regresión completa usó otra base aleatoria con sus propias migraciones.
Se comprobó posteriormente en `pg_database` que ambas bases temporales ya no
existen. El runner no detiene servicios PostgreSQL ni escribe sobre desarrollo.

## Revisión de logs

El registro de fallo contiene solo campos permitidos:

```json
{
  "timestamp": "2026-10-19T15:49:17.399985+00:00",
  "level": "ERROR",
  "component": "health",
  "event": "database_unavailable",
  "errorType": "OperationalError",
  "statusCode": 503
}
```

Django emitió además un evento HTTP genérico del 503. Los registros completos
están incluidos en el JSON versionable y en
`TK17-20261019T154912Z/unavailable.log`. Los logs de disponibilidad y
recuperación no contienen errores.

Se verificaron los loggers de solicitud, servidor, base de datos, seguridad,
health y uno arbitrario. Los tests inyectan secretos sintéticos en mensajes,
argumentos, excepciones, nombres de logger/clase, SQL, campos adicionales,
cookies, cabeceras, rutas y query strings. El formato final no los incluye;
tampoco evalúa la representación de objetos arbitrarios. Los nombres de error
permitidos son categorías fijas; las excepciones desconocidas se identifican
como `UnexpectedError`. Se conservan diagnóstico básico, severidad y fecha,
sin texto libre ni trazas. Los logs de servidores externos no forman parte de
esta configuración de Python.

## Hallazgo corregido

La ejecución inicial
[TK17-readiness-20261019T154847Z.json](TK17-readiness-20261019T154847Z.json)
detectó que una apertura de conexión sin timeout explícito podía superar los
10 segundos del cliente HTTP durante la caída. La prueba falló por timeout y
conservó su informe; no se marcó como aprobada.

Se agregó `connect_timeout=3` a las opciones PostgreSQL. La repetición completa
de cierre devolvió el 503 esperado y luego 200 al restaurar la configuración.
Este timeout limita el establecimiento de conexión, no el tiempo global de
una consulta en una conexión ya existente. No quedan fallos bloqueantes en
BE-CP24. No se requieren migraciones de esquema.

## Reproducción

Desde `portfolio_backend`, con dependencias, `.env`, PostgreSQL con `CREATEDB`
y puerto 8766 libre:

```powershell
.\.venv\Scripts\python.exe scripts\validate_readiness.py
```

El runner comprueba disponibilidad, caída y recuperación por HTTP, verifica
ausencia de un marcador privado, captura logs, ejecuta la suite completa en
otra base descartable y conserva un informe histórico con fecha UTC. Para
ejecutar solamente las siete pruebas nuevas:

```powershell
$env:POSTGRES_TEST_DB = 'portfolio_suite_tk17_' + [guid]::NewGuid().ToString('N').Substring(0,12)
.\.venv\Scripts\python.exe manage.py test portfolio.test_health --noinput
Remove-Item Env:POSTGRES_TEST_DB
```

El README documenta el contrato público, consulta manual y lectura de stderr.
Los JSON resumidos y este registro se conservan para versionado; las carpetas
de logs se retienen localmente y están excluidas de Git.
