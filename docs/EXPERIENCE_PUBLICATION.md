# Experiencia laboral aprobada

Fecha: 19/10/2026. El responsable solicitó cargar la experiencia del frontend y
proporcionó los cargos, organizaciones, tareas y períodos. También confirmó enero
como mes de inicio de la actividad freelance en 2023. La primera carga conservó
el inglés recibido; luego el responsable pidió traducir la experiencia al español,
como el resto del portfolio. No se agregaron clientes, métricas ni responsabilidades.

| Cargo | Organización | Período |
| --- | --- | --- |
| Pasante de desarrollo web | DGES | Junio–noviembre de 2025 |
| Desarrollador full stack independiente | Freelance | Enero de 2023–actualidad |
| Soporte técnico informático | Sanatorio Francés | Noviembre de 2024–mayo de 2025 |

Las fechas se guardan con día 1 para representar el mes confirmado. No indican
que el primer día del mes fuera exactamente el inicio/fin laboral. El frontend
ya presenta fechas con precisión de mes/año y usa `isCurrent` para «Actualidad».
No se cambiaron modelos, migraciones ni código Angular.

## Seguridad de la carga

El comando `load_approved_experience` crea únicamente las tres experiencias
aprobadas. Valida todos los registros dentro de una transacción, rechaza
duplicados, registros ajenos o diferencias con ediciones existentes y no los
sobrescribe. Sin `--publish` crea borradores sin despublicar contenido existente.
Se verificó que repetir la carga conserva las PKs y no duplica registros.

Antes de escribir se generaron backups custom del esquema de aplicación y una
referencia de portfolio con la misma instantánea PostgreSQL. Los archivos y
datos completos permanecen bajo `backups/experience-update/`, ignorados por Git
y con ACL restringida. No se trasladaron usuarios ni sesiones entre bases.

Destinos: PostgreSQL local y los esquemas `public` y `portfolio_django` existentes
en Supabase. La publicación de formación ya había permitido identificar que
el servicio Render consulta los datos de `public`; no se cambió su conexión ni
se fusionaron esquemas. Cada destino se respalda y compara por separado.
El resto del portfolio, incluida la formación cargada anteriormente, se compara
antes y después para confirmar que permanece intacto.

Evidencia de cada ejecución en `reports/experience-load-<destino>.json`.
Verificación pública en `reports/experience-publication.json`.

## Repetir solo si corresponde

En local:

```powershell
.\.venv\Scripts\python.exe manage.py load_approved_experience --publish --settings=config.settings_local_transfer
```

En un servicio que ya incluya el comando, usar sus settings activos:

```sh
python manage.py load_approved_experience --publish
```

La carga ya ejecutada no necesita un nuevo despliegue para mostrarse. El comando
se conserva para reproducibilidad; las ediciones posteriores se hacen desde el
Admin. Si un registro fue editado, el comando se detendrá en lugar de reemplazarlo.
Los reportes históricos de transferencia con cero experiencias conservan su
fecha y significado; no se actualizan para ocultar cambios legítimos de contenido.

## Corrección del idioma — 19/10/2026

`translate_approved_experience` traduce únicamente los cargos y las descripciones
de los tres registros originales conocidos. Conserva PKs, organizaciones, fechas,
orden y publicación. Rechaza cambios ajenos y valida todos los registros antes de
escribir dentro de una transacción; repetirlo no duplica ni despublica contenido.
`load_approved_experience` ahora utiliza el español para futuras cargas nuevas.

Se respalda cada destino por separado en `backups/experience-spanish/`, ignorado
por Git y con acceso restringido. Los reportes `reports/experience-spanish-*.json`
comparan los registros antes/después y comprueban que el resto del portfolio no
cambia. La modificación de contenido no requiere un redeploy.

Para repetir tras revisar el destino y respaldarlo, usar sus settings explícitos:

```powershell
.\.venv\Scripts\python.exe manage.py translate_approved_experience --settings=config.settings_local_transfer
```

No ejecutar este comando contra un destino distinto suponiendo que selecciona
producción automáticamente: local, `public` y `portfolio_django` son destinos
independientes, como se explica arriba.
