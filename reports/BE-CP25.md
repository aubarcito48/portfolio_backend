# BE-CP25 — Despliegue de producción (TK18)

Fecha: 19/10/2026. Estado: **validación pública aprobada y validaciones manuales
confirmadas por el responsable**. No se realizaron escrituras de contenido,
nuevas migraciones ni despliegues durante esta revisión.

- Backend: https://portfolio-backend-6ecn.onrender.com
- Frontend: https://portfolio-nahuel48.vercel.app
- Commit indicado por el responsable como desplegado:
  [`d082a8207ce58ac1fe0a1397acddd167edc9872d`](https://github.com/aubarcito48/portfolio_backend/commit/d082a8207ce58ac1fe0a1397acddd167edc9872d).
- Evidencia automática: `TK18-production-verification.json` y
  `TK18-vercel-verification.json`. Captura local: `TK18-evidence/vercel.png`
  (ignorada por Git; adjuntar por separado si se desea conservar en la issue).

| Comprobación | Resultado y alcance |
| --- | --- |
| HTTPS y disponibilidad | `/health/` 200 con JSON genérico; HTTP redirige a HTTPS mediante 301 |
| API pública | Seis endpoints 200; cantidades visibles coinciden con transferencia |
| PostgreSQL/Supabase | Comprobación directa desde este equipo: motor PostgreSQL, proyecto esperado, esquema privado y SSL activos |
| Migraciones | Las 29 migraciones están aplicadas en Supabase; consulta de solo lectura |
| Datos | 30 registros y 12 relaciones; valores serializados y relaciones coinciden con transferencia |
| Servidor de producción | Gunicorn 26.2.0 fijado; comando de arranque documentado. No se inspeccionó el proceso remoto |
| DEBUG/hosts/cookies | Settings de producción rechazan DEBUG activo o hosts vacíos. Producción pública devuelve 404 genérico y cookie CSRF Secure |
| Django Admin | Login 200; cinco hojas CSS 200; acceso anónimo a proyectos redirige al login |
| Acceso administrativo autorizado | Confirmado por el responsable; no se solicitaron ni usaron credenciales |
| Escritura pública | OPTIONS anuncia GET/HEAD/OPTIONS; POST vacío a la colección devuelve 403. No se enviaron DELETE/PUT ni contenido |
| CORS real | Vercel publicado consume siete respuestas API 200, incluida paginación; cero solicitudes API fallidas. Un origen ajeno no recibe permiso CORS |
| Imágenes | Las seis imágenes `/assets/...` cargan desde Vercel, no desde Render |
| Reinicio/persistencia | Reinicio y conservación de datos confirmados por el responsable. No se ejecutó otro reinicio desde esta revisión |
| Secretos | Reportes contienen solo conteos, estados y URLs públicas. No se imprimieron secretos ni cookies completas; `.env*` siguen ignorados |

## Comprobaciones de despliegue

Se ejecutó `python manage.py check --deploy --settings=config.settings_supabase`
con la configuración real de producción **desde este equipo**, no desde Render.
Resultado: sin errores, dos advertencias y una excepción deliberada de correo.

- `security.W008`: redirección delegada al proxy Render, verificada con HTTP 301.
- `security.W004`: HSTS desactivado durante la puesta en servicio inicial. Se
  conserva como mejora pendiente hasta validar la política HTTPS de todos los
  accesos; no se habilita `includeSubDomains` ni preload automáticamente. No es
  una redirección faltante: HTTPS ya está comprobado. Advertencia documentada,
  no silenciada.
- `mail.E001`: únicamente esa comprobación se silencia en producción porque
  `dummy.EmailBackend` desactiva deliberadamente el correo. El proyecto no tiene
  flujos de envío y no requiere proveedor SMTP.

No se verificaron desde dentro de Render el motor efectivo, el proceso Gunicorn,
DEBUG/hosts exactos ni el resultado remoto de `check --deploy`. Las pruebas
directas contra Supabase y el código revisado no sustituyen esa observación.
Para añadir evidencia interna sin mostrar secretos, seguir
[`../docs/VERIFY_RENDER_DATABASE.md`](../docs/VERIFY_RENDER_DATABASE.md), ejecutar
`python manage.py verify_runtime_database` y `python manage.py check --deploy`
con los settings activos. El primer comando debe mostrar `runningOnRender=true`.
No confundir `localRepositoryCommit` con una detección automática del commit
remoto: aquí el commit desplegado lo confirmó el responsable.

## Reproducir las comprobaciones públicas

```powershell
.\.venv\Scripts\python.exe scripts/verify_production.py
```

El script regenera solo evidencia HTTP pública; no reproduce el login autorizado,
el reinicio ni la comprobación privada de runtime. Sus pendientes describen el
alcance automático. Las confirmaciones manuales de esta ejecución se conservan
en este documento.

No se detectaron fallos bloqueantes en las comprobaciones ejecutadas. Las
confirmaciones manuales y límites están separados para no atribuir al script
acciones que no realizó.
