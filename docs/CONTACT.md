# Contacto del portfolio

Angular envía `POST /api/v1/contacto/` a Django, que manda un correo de texto plano
por la API HTTPS de Resend. El único destinatario permitido es
`nahuel.cba.48@gmail.com`. El visitante no puede modificarlo. Su correo se coloca
en `Reply-To`, para responder desde Gmail; no se suplanta como remitente.
No se envían confirmaciones automáticas a terceros ni adjuntos.

## Activación en Render

El código queda preparado, pero el envío real requiere configurar el proveedor:

1. Crear una cuenta gratuita en <https://resend.com> usando **nahuel.cba.48@gmail.com**
   y verificar ese correo. El remitente de prueba `onboarding@resend.dev` solo
   permite enviar al correo del dueño de la cuenta. Si se usa otro destinatario,
   Resend exige verificar un dominio propio y usar un remitente de ese dominio.
2. Crear una API Key con permiso de envío. Copiarla directamente a Render:

   ```dotenv
   RESEND_API_KEY=tu_clave_privada_de_resend
   CONTACT_FROM_EMAIL=onboarding@resend.dev
   ```

3. Publicar primero el backend, conservar las variables de Django, WhatsApp y Groq
   existentes, guardar las variables nuevas y esperar **Live**. No es necesario
   cambiar Build Command ni Start Command, instalar dependencias o migrar tablas.
4. Publicar el frontend. Su `apiBaseUrl` existente se utiliza para `/contacto/`.
   `DJANGO_CORS_ALLOWED_ORIGINS` debe incluir el origen HTTPS exacto del portfolio.
   No agregar secretos en Vercel/Angular ni en Git.
5. Enviar desde el formulario un mensaje real identificado como prueba. Comprobar
   en Resend el estado del envío y en Gmail la bandeja de entrada y Spam.
   Usar Responder en Gmail y comprobar que se dirige al email del visitante.

Referencias oficiales:
[limitación del remitente resend.dev](https://resend.com/docs/knowledge-base/403-error-resend-dev-domain),
[API de envío](https://resend.com/docs/api-reference/emails/send-email),
[precios y cuotas](https://resend.com/pricing).
El plan gratuito publicado ofrece 3.000 correos mensuales y 100 diarios; revisar
el panel antes de activar. No contratar un plan pago ni habilitar excedentes para
esta integración. No hace falta comprar un dominio para el envío restringido al
correo de la cuenta con `onboarding@resend.dev`; es el remitente de pruebas de Resend.
Para un remitente propio de producción se necesita un dominio verificable.

Render gratuito bloquea los puertos SMTP habituales 25/465/587, por eso se usa
HTTPS y no SMTP de Gmail. No se pide contraseña de Gmail, contraseña de aplicación
ni acceso a la bandeja de entrada.
[Documentación de Render](https://render.com/docs/free).

## Comportamiento

- Campos obligatorios: nombre y apellido (2–100), teléfono (7–15 dígitos,
  hasta 32 caracteres con signos), email (hasta 254), asunto (3–160) y mensaje
  (10–3.000 caracteres). La etiqueta española `Gmail` se conserva según el pedido,
  pero se aceptan correos válidos de otros proveedores.
- Botón bloqueado durante el envío, mensajes claros de validación y estados
  accesibles de éxito/error. En un error se conserva el texto para reintentar.
- Se considera enviado solo cuando Resend confirma que aceptó la solicitud con
  un ID. Eso no garantiza llegada a la bandeja principal: puede haber rebotes o spam.
  Sin credenciales, o ante un rechazo/timeout del proveedor, devuelve 503 y no
  presenta una confirmación falsa.
- UUID de solicitud enviado como Idempotency-Key. Reintentar el mismo contenido
  desde el mismo formulario reutiliza la clave, evitando duplicados durante la
  ventana de 24 horas de Resend. Cambiar contenido genera una clave nueva;
  recargar la página pierde esa identidad. [Idempotencia](https://resend.com/docs/dashboard/emails/idempotency-keys).
- Los mensajes no se almacenan en la base de datos ni en localStorage. Pasan por
  Render y Resend para llegar al destinatario. No afirmar que el proveedor no retiene
  información. Los logs propios no incluyen datos del visitante, claves ni cuerpos
  de error del proveedor; muestran `component=contact`, `event=delivery_failed`
  y el status HTTP si está disponible.
- Orígenes web restringidos, cuerpo JSON máximo 16 KiB, rechazo de caracteres de
  control/inyección de cabeceras, honeypot y límite global de 10 intentos/hora y
  30/día por proceso, con dos envíos simultáneos. Las cuotas cuentan intentos,
  incluidos fallos. No hay cola ni reenvío automático.
- Los límites viven en memoria: se reinician al desplegar y se multiplican con
  varios workers. El servicio existente usa uno. No son una garantía de gasto
  global ni impiden que un tercero agote la cuota. Para mayor tráfico/abuso,
  incorporar CAPTCHA y una cuota compartida persistente.

El MAILERS de Django para el Admin sigue deshabilitado en producción: esta ruta
envía directamente por HTTPS y no modifica ese comportamiento.

## Validación sin correos reales

```powershell
.\.venv\Scripts\python.exe scripts/test_contact.py
```

Usa SQLite en memoria, desactiva `.env`, simula Resend/Groq/Meta e incluye la
regresión de Aubar y WhatsApp. No toca Supabase ni envía mensajes.
En el frontend: `npm run build`, `npm test -- --watch=false` y
`npx playwright test e2e/contact-form.spec.ts --project=chromium-desktop-1440 --project=chromium-mobile-360`.
