# Aubar en WhatsApp · Meta Cloud API

La integración está implementada localmente. No está conectada a Meta ni activada
en Render hasta completar las credenciales y las pruebas reales de esta guía.
Reutiliza Aubar/Groq y el contenido publicado del portfolio, sin nuevas dependencias
ni cambios en la base de datos.

## Activación

Solo estos mensajes completos activan el asistente (incluidos mayúsculas, tildes y punto):

```text
Hola Nahuel, vi tu portfolio y me gustaría contactarte.
Hi Nahuel, I saw your portfolio and would like to get in touch.
```

Coinciden con el botón actual de Angular y su traducción. No es necesario modificar
el frontend si se mantiene el mismo número. Una frase copiada también activa el bot:
esto no prueba que la persona hizo clic en el portfolio.

El primer mensaje recibe una presentación automática, información sobre uso de IA
y cómo salir. Luego se pueden preguntar datos públicos del portfolio.
`SALIR`, `STOP`, `HUMANO` o `HUMAN` desactivan las respuestas automáticas.
No se avisa a Nahuel ni se garantiza atención humana; para retomarlo hay que
reenviar la frase exacta. La sesión también vence después de 30 minutos de inactividad.
Fuera de una sesión activa, cualquier otro mensaje se ignora.

## Primero: cuenta y número personal

1. Entrar a <https://developers.facebook.com/apps/> con la cuenta propia y completar
   el alta de desarrollador si Meta lo solicita.
2. Crear una aplicación que permita usar WhatsApp Business Platform. Los nombres de
   los pasos pueden variar en el panel. Agregar WhatsApp y acceder a **API Setup**
   (Configuración de API / Prueba de API).
3. Probar primero el número de prueba de Meta con un destinatario autorizado.
   Ese número no debe reemplazar el número público del portfolio para las pruebas.
4. Para conectar el número personal `+54 9 351 758-7047`, revisar las opciones de
   registro que Meta ofrece a esa cuenta. El ID de número de la API no es este teléfono.
   No asumir que se puede registrar directamente un número usado en WhatsApp personal
   y seguir usando la app. La coexistencia corresponde a un flujo específico para
   WhatsApp Business App y depende de elegibilidad y del proceso de incorporación.
5. Si el panel exige eliminar una cuenta o migrar el número, detener ese paso y
   evaluar el impacto antes de hacerlo. Esta integración no requiere borrar la cuenta
   ni desinstalar WhatsApp. El código se puede verificar con el número de prueba.

Referencias oficiales:
[inicio y entorno de pruebas](https://whatsappbusiness.com/developers/developer-hub/),
[incorporación de Business App / coexistencia](https://developers.facebook.com/documentation/business-messaging/whatsapp/embedded-signup/onboarding-business-app-users).

## Variables de Render

En el servicio existente **portfolio-backend → Environment**, agregar:

| Variable | Valor / dónde obtenerlo |
| --- | --- |
| `WHATSAPP_ENABLED` | `True` cuando todas las variables estén completas. `False` apaga la integración y devuelve 404 en el webhook. |
| `WHATSAPP_VERIFY_TOKEN` | Cadena aleatoria propia, larga, sin espacios. Poner exactamente la misma en la configuración del webhook de Meta. |
| `WHATSAPP_APP_SECRET` | App Secret de la aplicación de Meta, en configuración básica. No es el verify token. |
| `WHATSAPP_ACCESS_TOKEN` | Access Token de Meta con permiso para enviar mensajes desde la cuenta/número elegidos. El temporal sirve para pruebas y vence; para producción configurar el token apropiado del usuario del sistema y sus permisos. |
| `WHATSAPP_PHONE_NUMBER_ID` | Phone Number ID de API Setup. Solo dígitos; no usar el teléfono ni el WhatsApp Business Account ID. |
| `WHATSAPP_GRAPH_VERSION` | Versión soportada mostrada en el ejemplo de API Setup, con formato `vNN.0`. Copiar el valor real; no usar literalmente `vNN.0`. |
| `GROQ_API_KEY` | Clave de Groq que ya usa Aubar; conservarla. |
| `GROQ_MODEL` | Modelo configurado para Aubar; conservarlo. |

No pegar tokens en el chat, Git, Angular, capturas públicas ni URLs.
Para generar el verify token localmente:

```powershell
.\.venv\Scripts\python.exe -c "import secrets; print(secrets.token_urlsafe(32))"
```

Mantener el build actual. Configurar **un solo worker** y suficiente tiempo para
finalizar tareas pendientes durante un reinicio:

```sh
python -m gunicorn config.wsgi:application --bind 0.0.0.0:$PORT --workers 1 --graceful-timeout 60
```

No habilitar varios workers, múltiples instancias ni reciclado frecuente de workers:
el estado de esta primera versión es local al proceso. No configurar `WEB_CONCURRENCY`
para aumentar instancias. Guardar las variables y desplegar el código del backend.

## Webhook en Meta

En **WhatsApp → Configuration → Webhooks**, configurar:

```text
Callback URL: https://<dominio-real-del-backend>/api/v1/whatsapp/webhook/
Verify token: el valor privado de WHATSAPP_VERIFY_TOKEN
```

Usar el dominio del backend de Render, no el frontend de Vercel. Incluir la barra
final. Verificar y guardar; suscribirse al campo `messages`. Comprobar también que
la aplicación esté suscripta a la cuenta de WhatsApp que contiene el número elegido.
El GET devuelve el challenge al verificar el token y el POST exige una firma HMAC
SHA-256 válida con el App Secret. No hace falta cambiar CORS ni CSRF del Admin.

## Prueba real, antes de anunciarlo

Desde otro número autorizado para las pruebas:

1. Mandar `hola` al número conectado: el bot debe guardar silencio.
2. Mandar la frase exacta en español: debe presentarse como Aubar.
3. Preguntar por un proyecto publicado: debe responder con datos del portfolio.
4. Mandar `SALIR`, luego otra pregunta: debe confirmar la salida y quedar en silencio.
5. Repetir con la frase en inglés y `STOP`.
6. Comprobar `/health/` y el chat web ya existente.

Un número de prueba solo permite los destinatarios habilitados por Meta; no es una
demo pública. Para abrir al público hay que completar los requisitos que indique
Meta para la aplicación, la cuenta y el número real, y verificar el token de producción.

Si no funciona: revisar firma/App Secret, vencimiento del Access Token, Phone Number
ID, permisos y suscripción a `messages`. El token de verificación solo resuelve el GET;
no autoriza el envío. Los logs no imprimen tokens, teléfonos ni conversaciones.
Los errores nuevos distinguen `component=whatsapp`, `event=delivery_failed`
(rechazo de Meta, con `statusCode`, `metaCode` y `metaSubcode` numéricos si existen)
de `event=processing_failed` (fallo interno o de transporte con tipo acotado).
Los registros antiguos `backend_error` no permiten conocer esa causa: repetir
una prueba después de desplegar el diagnóstico nuevo. No publicar cuerpos de errores
del proveedor para depurarlo.

`gunicorn.conf.py` configura logs de acceso con la ruta sin query string para no
registrar el verify token que Meta envía al verificar el webhook. No sobrescribir
ese formato desde el Start Command ni desde `GUNICORN_CMD_ARGS`.

## Límites de esta primera versión

- El webhook responde rápido y una cola en segundo plano genera/envía las respuestas.
  Cola de hasta 20 lotes, hasta 100 mensajes por lote, un consumidor.
- Máximo 5 respuestas por minuto por conversación y 10 por minuto por proceso
  (salidas excluidas). Al superar esos límites se guarda silencio.
- Texto entrante hasta 1.200 caracteres. No se procesan audios, imágenes, grupos
  ni estados de entrega como consultas. Solo se acepta el Phone Number ID configurado.
- Se descartan eventos de más de 5 minutos (incluyendo los que envejecen en la cola).
  No se envían campañas, plantillas ni mensajes programados.
- Hasta 1.000 sesiones y 10.000 IDs de mensajes en memoria; historial acotado a
  8 mensajes / 6.000 caracteres. No se guardan conversaciones en la base de datos.
- Se suprimen IDs repetidos por hasta 24 horas mientras siga vivo el proceso.
  Un reinicio pierde sesiones, deduplicación y trabajo pendiente. Un error de envío
  queda registrado sin datos privados; no hay reintentos automáticos de salida.
  Después de un reinicio, una persona debe volver a activar el bot con la frase.
  Un evento de activación reenviado tras reiniciar puede producir otra bienvenida.
- Es una implementación inicial para el portfolio, con entrega de mejor esfuerzo.
  Para garantizar persistencia/reintentos y escalar, hace falta una cola durable,
  almacenamiento compartido y un worker separado.
- Si el hosting suspende el proceso, puede haber demoras o perderse tareas pendientes.
  Esta versión requiere que Render ejecute el proceso mientras se atienden mensajes.

Meta ofrece pruebas gratuitas. Su [página de precios](https://whatsappbusiness.com/products/platform-pricing/)
describe las condiciones de los mensajes de atención dentro de la ventana de 24 horas.
Confirmar la tarifa aplicable en la cuenta antes de producción: no asumir costo total
cero; hosting y Groq tienen sus propios planes, cuotas y límites.

## Verificación local aislada

```powershell
.\.venv\Scripts\python.exe scripts/test_whatsapp.py
```

Desactiva `.env`, usa SQLite en memoria y simula Meta/Groq. Incluye la regresión de
Aubar. No toca Supabase ni envía mensajes reales. No sustituye la prueba en Render
con la cuenta y número reales.
