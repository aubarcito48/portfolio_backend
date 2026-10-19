# BE-CP22 — Suite y recorridos automatizados

Task: TK15 / issue #15. Requisito: BE-RNF08. Fecha: 19/10/2026,
America/Buenos_Aires. Responsable: Nahuel Argandoña.

## Ejecución de cierre

**Estado: APROBADO.** Ejecución `20261019T153207Z`, del 19/10/2026 entre
12:32:07 y 12:34:23 (UTC−03). Runner finalizado con código 0.

| Validación | Resultado real |
| --- | --- |
| Django con PostgreSQL independiente | 88 aprobadas, 0 fallos |
| Unitarias Angular | 17 aprobadas, 0 fallos |
| Build de producción | Aprobado |
| Playwright, 9 combinaciones navegador/ancho | 147 aprobadas, 6 no aplicables, 0 fallos, 0 inestables |
| Recorridos BE-CP22 con API real (incluidos en Playwright) | 27 aprobados, sin reintentos |
| Sonda HTTP integrada y CORS | Aprobada |
| Eliminación de las dos bases temporales | Confirmada mediante consulta posterior a `pg_database` |

Los 6 no aplicables son dos pruebas de menú móvil en escritorio para cada
uno de los tres navegadores; no representan fallos pendientes.

Entorno: Windows, Python 3.14.3, Django 6.1.2, PostgreSQL 18.3,
Node v24.13.1, npm 11.10.0, Angular 21.2.25 y Playwright 1.64.1.

Revisiones base:

- Backend: `9e98b49ad9d1014816ae1f90bbea12a3b9c0dcb9`.
- Frontend: `d38035cdacfdd0e590240a6514c2711d80c248ad`.

Ambos árboles tienen cambios locales TK15 sin publicar. Se verificó que los
hashes SHA-256 del informe coinciden con todas las fuentes al cerrar la tarea.

Comando desde `portfolio_backend`:

```powershell
.\.venv\Scripts\python.exe scripts\run_regression.py
```

El informe JSON registra versiones reales de Python, Django, PostgreSQL,
Node, npm, Angular y Playwright; commit base de ambos repositorios, árbol de
trabajo modificado y hashes de las fuentes ejecutadas. Las modificaciones
locales todavía no tienen un commit publicado.

## Cobertura

| Comprobación | Evidencia |
| --- | --- |
| Modelos, validaciones, restricciones PostgreSQL, endpoints, paginación y permisos Admin/CSRF/CORS | Suite Django completa |
| Guardas de la carga E2E, repetibilidad sin duplicados y rollback ante fallos | `portfolio/test_regression.py` |
| Consumo HTTP Angular, estados y accesibilidad | Suite unitaria Angular |
| Build de producción | Salida de Angular CLI |
| Contenido real, segunda página de tecnologías y exclusión de borradores | `e2e/real-api.spec.ts`, captura del portfolio y respuestas Django |
| Experiencia/formación sintéticas publicadas; borradores de todos los listados y detalle de proyecto ocultos | Semilla E2E, tests Django y navegador |
| Navegación, menú, enlaces, tema, persistencia y responsive | Matriz Chromium/Firefox/WebKit × 360/768/1440 |
| Carga, fallo de red y recuperación real con Reintentar | Recorrido integrado con una sola petición abortada |
| Listas vacías y perfil sin publicar | `e2e/api-integration.spec.ts`, API simulada determinista |
| Contrato público, paginación y CORS del origen Angular | `scripts/probe_integrated.py` |

Los destinos externos se verifican mediante URL y atributos; no se depende
de que Spotify, Google Fonts, GitHub, LinkedIn o las demos estén disponibles.
La emulación de ancho no representa pruebas en dispositivos físicos.

## Defectos y repetición

### TK15-D01 — Runner incompatible con la resolución de npm en Windows

- Detección: inspección del código iniciado; invocaba `npm` directamente con
  `subprocess.run` sin resolver `npm.cmd`.
- Reproducción: ejecutar el runner en Windows con npm instalado como shim
  `.cmd`; la obtención de versión puede terminar en `FileNotFoundError`.
- Corrección: resolver el ejecutable con `shutil.which('npm')`.
- Repetición: el runner ya obtiene la versión y llega a las suites Angular.

### TK15-D02 — Sonda de disponibilidad apuntaba a una ruta inexistente

- Detección: inspección; esperaba HTTP 2xx/3xx de `/api/v1/`, que no es un
  recurso público definido.
- Reproducción: iniciar Django y consultar `/api/v1/`; el 404 no satisface
  la espera y provoca timeout aunque el servidor esté funcionando.
- Corrección: esperar `/api/v1/perfil/` después de cargar la semilla publicada.
- Repetición: el runner inicia Django y Angular y ejecuta los navegadores.

### TK15-D03 — UnicodeEncodeError al imprimir la salida de Angular

- Detección real: ejecución `20261019T152846Z`.
- Reproducción: ejecutar el runner con stdout CP1252 en Windows; Angular
  imprime `✔` y Python falla al escribir ese carácter.
- Corrección: configurar stdout/stderr UTF-8 y conservar logs UTF-8.
- Evidencia: `TK15-regression-20261019T152846Z.json`.
- Repetición: las ejecuciones siguientes completan unitarias y build.

### TK15-D04 — Selector incorrecto en el nuevo caso de formación

- Detección real: ejecución `20261019T152911Z`, 9 fallos del mismo caso,
  138 aprobados y 6 no aplicables.
- Reproducción: buscar `TK15 Published Education` con rol `heading`; la
  plantilla lo presenta en un párrafo `.education-name`.
- Corrección: comprobar el texto visible en `.education-name`.
- Evidencia: reporte de esa ejecución, capturas, videos y traces en
  `20261019T152911Z/`.
- Repetición: los 9 casos afectados pasaron en `20261019T153207Z`; matriz
  completa de cierre aprobada. Estado: corregido y verificado.

No se detectaron defectos funcionales del producto en las pruebas completadas.
Los hallazgos anteriores corresponden a la infraestructura y los casos de
prueba que se estaban completando.

## Evidencias y aislamiento

- Resumen actual: [TK15-regression-latest.json](TK15-regression-latest.json).
- Cierre: [JSON histórico](TK15-regression-20261019T153207Z.json),
  [reporte HTML](20261019T153207Z/playwright-report/index.html) y
  [resultados por caso](20261019T153207Z/playwright-results.json).
- Cada resumen histórico conserva su fecha UTC; su carpeta del mismo nombre
  contiene reporte HTML/JSON, captura de contenido y evidencia de fallos.
- Los casos individuales y sus estados reales están en
  `<fechaUTC>/playwright-results.json`; el HTML permite filtrarlos.
- Solo las bases creadas por la ejecución son descartadas. La suite Django
  usa `portfolio_suite_*`; el navegador usa `portfolio_e2e_*`.
- La carga E2E exige entorno `test`, prefijo reservado, coincidencia con la
  marca explícita y nombres distintos de desarrollo y pruebas configuradas.
- Los JSON y este registro se conservan para versionado. Los subdirectorios
  de evidencia pesada quedan localmente, excluidos de Git; deben adjuntarse
  como artefacto al compartir el resultado. No se publica ningún `.env`.
