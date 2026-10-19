# BE-CP26 — Restauración y rollback (TK19)

Fecha: **19/10/2026**. Estado: **APROBADO**.
Última ejecución completa: 15:47:33–15:47:47, America/Buenos_Aires
(18:47:33–18:47:47 UTC). Tiempo total aproximado: 15 segundos con datos mínimos;
no representa un RTO de producción.

Procedimiento: [`../docs/BACKUP_RECOVERY.md`](../docs/BACKUP_RECOVERY.md).
Ejecución principal: [`TK19-recovery-20261019T184733Z.json`](TK19-recovery-20261019T184733Z.json).

## Entorno y versiones

- Windows, PostgreSQL/pg_dump/pg_restore 18.3, Python 3.14.3, Django 6.1.2.
- Código actual base: `9c64b61268a31136b0e9054a0a77c1064c02e509`, con los nuevos
  scripts sin commit aún. El JSON registra hashes SHA-256 de ambos scripts.
- Código anterior ensayado: `42e68bb46b2d245dec9b21167dd692cd0ca729bb`.
- Clúster nuevo con autenticación SCRAM, loopback y puerto asignado libremente;
  dos bases distintas, esquema privado `portfolio_django`, datos sintéticos.
- No se conectó a Supabase ni Render. Desarrollo y producción no se modificaron;
  `.env` y `.env.supabase` permanecieron idénticos y no se analizaron sus valores.

## Resultados

| Caso | Resultado |
| --- | --- |
| Generar copia | `pg_dump -Fc` terminó en 0; archivo de 57.442 bytes, hash registrado |
| Proteger artefactos | Carpeta privada con ACL restringida, dump y clúster ignorados por Git |
| Revisar catálogo | `pg_restore --list` terminó en 0 |
| Restaurar | Base nueva y vacía; `--single-transaction --exit-on-error`, sin `--clean` |
| Comparar contenido | 18 tablas completas y 17 secuencias idénticas, incluidos PK/FK/M2M, fechas con microsegundos y tablas internas Django |
| Portfolio | 14 registros de siete modelos y 5 relaciones proyecto-tecnología coincidentes |
| Django actual | `check` correcto, ninguna migración pendiente, health y API consultan la base recuperada |
| Publicación | Proyecto publicado responde 200, borrador 404 y tecnología oculta excluida del proyecto público |
| Rollback compatible | Código real de `42e68bb` extraído en otro directorio, `check` y las mismas consultas correctas sobre el esquema recuperado |
| Sin cambios en origen | Referencias antes y después idénticas |
| Destino no vacío | El guard rechazó el destino poblado antes de una segunda restauración; no se volvió a ejecutar pg_restore |
| Rollback incompatible | Revisión `b9eeb98` rechazada antes de initdb por diferencias en modelos/migraciones |
| Limpieza | Clúster temporal detenido; copias/logs privados retenidos para revisión |

Conteos de la muestra: Perfil 1, Tecnologia 3, Experiencia 2, Formacion 2,
Proyecto 2, EnlaceProyecto 2 y Enlace 2. Incluye contenido publicado y borradores;
no depende de servicios externos ni del contenido real del portfolio.

Se comprobaron nueve rutas con el cliente Django contra PostgreSQL: health,
perfil, tecnologías, experiencias, formación, proyectos, enlaces y dos detalles
de proyecto (publicado/borrador). Ocho respuestas 200 y una 404 esperada.
No se levantó Gunicorn ni se probó la infraestructura pública con la copia.

## Incidencias y repetición

**REC-01, corregido:** el primer lanzador usaba `capture_output` para `pg_ctl`.
En Windows, el servidor heredaba handles de las tuberías y el proceso Python
seguía esperando su cierre después de arrancar PostgreSQL.

Reproducción: lanzar `pg_ctl start` con `subprocess.run(capture_output=True)` en
Windows; comprobar que el servidor ya responde mientras `communicate()` espera.
Se detuvo exclusivamente ese clúster temporal para liberar los handles. No había
copias ni bases de muestra creadas todavía. El primer JSON conserva `failed` y
el fallo del cierre automático porque el servidor ya había sido detenido desde
fuera; su limpieza manual se documenta por separado.

Corrección: escribir stdout/stderr directamente en archivos privados, sin pipes
heredados. Las ejecuciones completas de 18:45 y 18:47 UTC finalizaron con
restauración/rollback correctos y apagado automático satisfactorio.

El caso negativo de rollback incompatible tiene `result=failed` y salida 1 en
[`TK19-recovery-20261019T184753Z.json`](TK19-recovery-20261019T184753Z.json): es
**el rechazo esperado** del mecanismo de seguridad, no una restauración fallida.
No se inició PostgreSQL en esa ejecución.

## Límites y seguimiento

Volver al código anterior no revierte datos ni migraciones. El ensayo solo admite
un rollback con modelos e historial idénticos, no prueba reversas destructivas ni
recuperación de cambios posteriores a una copia. Roles/ACL globales, secretos y
archivos externos requieren recuperación separada. No se restauró un backup real
de Supabase. La retención y réplica cifrada fuera del equipo quedaron definidas
en el procedimiento; su programación/almacenamiento no se provisionaron.

Conservar este resumen y los JSON seguros en Git. Los dumps, valores de referencia
completos, logs y copias de código quedan bajo `backups/` con acceso restringido.
Enlazar el commit de TK19 al publicar los cambios; no se hizo commit/push desde
esta ejecución.
