# BE-CP23 — Latencia y consultas

**APROBADO — TK16 / BE-RNF06.** Fecha: 19/10/2026,
America/Buenos_Aires (UTC−03). Medición inicial 12:40:55–12:41:22;
medición final 12:42:56–12:43:29. Responsable: Nahuel Argandoña.

## Evidencia

- [Medición inicial](TK16-20261019T154055Z-before.json): código de producción
  del commit base `df8097e`, con el harness nuevo de medición.
- [Medición final y comparación](TK16-20261019T154256Z-after.json): cambio
  local TK16 sobre ese commit; hashes de las fuentes en `revision`.
- Cada JSON conserva las 400 muestras calientes, 40 calentamientos, errores,
  tamaños, hashes del contenido, SQL de tres peticiones por escenario, entorno,
  fecha, comandos y salidas. El final incluye la regresión de **94 pruebas
  aprobadas**. No se requieren archivos externos para revisar estos resultados.
- Logs y SQL adicionales: carpetas `TK16-20261019T154055Z-before/` y
  `TK16-20261019T154256Z-after/`, retenidas localmente y excluidas de Git.
- La ejecución exploratoria `TK16-20261019T154204Z-after.json` se conserva,
  pero no se usa en la comparación final porque parte de la medición coincidió
  con una ejecución de tests. Se repitió sin esa interferencia.

## Entorno y protocolo

Windows, AMD Ryzen 7 5700X (8 núcleos / 16 hilos), 15,93 GiB RAM;
Python 3.14.3, Django 6.1.2 y PostgreSQL 18.3. PostgreSQL local ya iniciado.
Equipo de escritorio compartido con otros procesos; no es un servidor de
producción ni un ensayo de carga concurrente.

Ambas mediciones usan una base nueva de PostgreSQL creada por el runner, las
mismas migraciones y la misma semilla versión 1: 100 proyectos publicados y
un borrador, 12 tecnologías (10 publicadas), seis relaciones de tecnología
por proyecto (cinco publicadas y una oculta), 202 enlaces adicionales y diez
registros públicos más un borrador de experiencia, formación y enlaces.
El perfil también es sintético. No se solicita contenido externo.

Servidor `runserver --noreload --nothreading`, `DEBUG=False`,
`http://127.0.0.1:8765`, una petición a la vez, HTTP sin reutilización de
conexión y PostgreSQL con la configuración normal del proyecto
(`CONN_MAX_AGE=0`). No se habilitó caché de respuestas ni instrumentación SQL
durante la medición HTTP. La duración abarca apertura de conexión, middleware,
consultas, serialización y lectura completa de la respuesta por el cliente.

Se descartaron cinco calentamientos por escenario y se midieron 50 solicitudes.
El p95 usa rango más cercano: el elemento 48 de las 50 duraciones ordenadas.
Los códigos, errores y duración de todas las solicitudes se conservan,
incluidos los calentamientos. No se excluyen solicitudes fallidas del cálculo.
Hubo **0 errores** en las 400 medidas de cada ejecución.

Las consultas se capturaron aparte, con `CaptureQueriesContext` y el cliente
Django sobre una conexión inicializada: tres peticiones por escenario. Se
conservan las sentencias y sus tiempos; no se confunden esos tiempos internos
con la latencia HTTP. Las tres capturas dieron el mismo conteo en cada caso.

## Resultados calientes

Cada fila contiene 50 solicitudes antes y 50 después. Latencias en ms.

| Endpoint bajo `/api/v1/` | p95 antes | p95 después | Consultas antes → después | Objetivo ≤1000 ms |
| --- | ---: | ---: | ---: | --- |
| `perfil/` | 147,56 | 130,87 | 1 → 1 | Cumple |
| `tecnologias/` | 133,91 | 135,02 | 2 → 2 | Cumple |
| `experiencias/` | 152,16 | 136,41 | 2 → 2 | Cumple |
| `formacion/` | 52,63 | 149,74 | 2 → 2 | Cumple |
| `enlaces/` | 51,72 | 137,85 | 2 → 2 | Cumple |
| `proyectos/` (20 por página) | 64,81 | 149,69 | 4 → 4 | Cumple |
| `proyectos/?page_size=100` | 174,12 | 73,84 | 4 → 4 | Cumple |
| `proyectos/tk16-project-001/` | 160,26 | 57,71 | 3 → 3 | Cumple |

Las respuestas conservaron el mismo hash en todas las muestras de un
escenario y entre ambas versiones. Los tests verifican adicionalmente orden,
límites de página, segunda página, enlaces, tecnologías ocultas y detalle de
proyecto borrador. La suite completa conserva permisos y validaciones.

## Arranque separado

Primer acceso a `perfil/`, antes de cualquier calentamiento:

| Medida | Antes (ms) | Después (ms) |
| --- | ---: | ---: |
| Primera petición HTTP | 67,84 | 82,70 |
| Crear proceso → respuesta completa | 1012,65 | 1010,58 |

Una muestra por versión. La disponibilidad se detecta por TCP, sin consumir
la primera petición API. No incluye migraciones ni carga de datos. Es un
proceso Django nuevo; PostgreSQL y la caché del sistema no se reinician.
No es un p95 frío. El arranque supera ligeramente un segundo y queda
informado por separado; el objetivo provisional solicitado se aplica al
servicio caliente. Para producción conviene medir el servidor WSGI/ASGI real
y su política de precalentamiento si se define también un objetivo de arranque.

## Revisión y optimización

**No se encontró N+1.** La vista ya precargaba tecnologías publicadas y enlaces
adicionales. El listado usa cuatro consultas: `COUNT`, proyectos paginados,
tecnologías y enlaces adicionales. Esa cantidad no crece al pasar de 20 a
100 elementos. El detalle utiliza las mismas relaciones y no necesita `COUNT`.
Los otros listados usan dos consultas: conteo y página.

Se corrigió un costo de CPU en `Proyecto.to_public_dict`: el valor por defecto
de `getattr` construía anticipadamente un QuerySet filtrado y ordenado por
proyecto, incluso cuando `published_technologies` ya existía. Ahora ese QuerySet
solo se construye si falta la precarga. La ruta precargada, incluida una lista
vacía, no construye el fallback ni ejecuta consultas; la serialización aislada
mantiene su filtro y orden. Esto evita hasta 100 construcciones inútiles en
la página grande, pero **no elimina consultas SQL**, porque el QuerySet anterior
no llegaba a evaluarse. No se agregaron índices ni cachés sin una necesidad
demostrada por estos datos.

El p95 de 100 proyectos bajó en esta ejecución, mientras otros endpoints
sin cambios empeoraron. La variabilidad también afecta casos ajenos al cambio;
estas dos series no permiten atribuir causalmente una mejora de latencia al
serializador. La conclusión verificable es que se eliminó trabajo innecesario,
se conserva un presupuesto constante de SQL y todos los p95 cumplen el
objetivo provisional. No se declara una mejora general del rendimiento.

## Regresión y cierre

- **94 pruebas Django aprobadas**, incluidas seis nuevas sobre seguridad de la
  semilla, repetibilidad, presupuesto SQL, paginación y caminos de serialización.
- Presupuesto comprobado para tamaños 1, 20 y 100: cuatro consultas, sin N+1.
- Detalle: tres consultas; serialización ya precargada: cero consultas.
- `makemigrations --check --dry-run`: sin cambios de esquema.
- `git diff --check`: sin errores.
- Se confirmó por consulta a `pg_database` que las bases de las mediciones
  inicial/final y la suite final ya no existen. Desarrollo no recibió escrituras.

No hay desvíos del p95 objetivo ni defectos funcionales pendientes en BE-CP23.
La siguiente medición, si se amplía el alcance, debería usar el despliegue real,
mayor volumen y concurrencia; estos resultados describen este entorno local.

## Repetir

Para medir la versión actual, seguir el README. Para repetir también el antes
sin reemplazar archivos de la rama de trabajo, desde `portfolio_backend`:

```powershell
$tk16Python = (Resolve-Path .venv\Scripts\python.exe).Path
git worktree add --detach ..\portfolio_backend-tk16-before df8097e
Copy-Item scripts\measure_performance.py ..\portfolio_backend-tk16-before\scripts\
Copy-Item portfolio\management\commands\load_portfolio_performance_data.py ..\portfolio_backend-tk16-before\portfolio\management\commands\
Copy-Item portfolio\management\commands\profile_api_queries.py ..\portfolio_backend-tk16-before\portfolio\management\commands\
Copy-Item .env ..\portfolio_backend-tk16-before\.env
Push-Location ..\portfolio_backend-tk16-before
& $tk16Python scripts\measure_performance.py --label before
Pop-Location
```

El `.env` copiado permanece excluido de Git; no se incluye en los reportes.
Tomar la ruta del JSON recién generado y ejecutar en la versión actual:

```powershell
& $tk16Python scripts\measure_performance.py --label after --compare ..\portfolio_backend-tk16-before\reports\TK16-<fechaUTC>-before.json --run-tests
```

El runner exige las mismas condiciones y semilla para comparar, conserva
errores y rechaza diferencias de contenido. Las etiquetas no aplican cambios
de código por sí mismas. Evitar ejecutar otros tests o tareas pesadas en
paralelo con la medición. Las duraciones variarán entre ejecuciones.
