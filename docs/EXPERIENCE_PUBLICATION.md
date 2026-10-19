# Experiencia laboral aprobada

Fecha: 19/10/2026. El responsable solicitó cargar la experiencia del frontend y
proporcionó los cargos, organizaciones, tareas y períodos. También confirmó enero
como mes de inicio de la actividad freelance en 2023. Se conservaron sus títulos
y descripciones en inglés, sin agregar clientes, métricas ni responsabilidades.

| Cargo | Organización | Período |
| --- | --- | --- |
| Web Development Intern | DGES | Junio–noviembre de 2025 |
| Freelance Full-Stack Developer | Freelance | Enero de 2023–actualidad |
| IT Technical Support | Sanatorio Francés | Noviembre de 2024–mayo de 2025 |

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
