# Aubar · Asistente del portfolio

Aubar responde sobre la información publicada de Nahuel. Usa Groq para generar
texto y el SDK oficial MCP 2.3.0 para recuperar perfil, proyectos, experiencia,
formación, tecnologías y enlaces. Habla español e inglés y puede usar el nombre
que el visitante proporcione en la conversación.

## Arquitectura

Angular → `POST /api/v1/chat/` → cliente MCP → herramienta
`consultar_portfolio` → mismas vistas públicas de la API → Groq → respuesta.

El cliente y servidor MCP se comunican con el transporte en memoria del SDK
dentro de Django. Hay descubrimiento y llamadas MCP reales, sin otro puerto,
contenedor, servidor HTTP público ni modelos locales. La herramienta no admite
URLs, consultas SQL, operaciones de escritura ni rutas arbitrarias. Invoca las
vistas públicas existentes y conserva sus filtros `is_published` y traducciones.
No se entrega al modelo acceso al Admin, al entorno ni a credenciales.

El contexto público se conserva en memoria hasta 60 segundos, separado por
idioma. Se admite hasta 100 elementos por recurso y 24.000 caracteres en total;
si se supera el límite, la consulta falla sin entregar un contexto incompleto.
Los límites son apropiados para el volumen actual del portfolio; revisar esta
estrategia si crece el contenido. No se incorporan embeddings ni una base vectorial.

## Configuración local

Instalar dependencias con `python -m pip install -r requirements.txt`.
Agregar al `.env` privado del backend, conservando las otras variables:

```dotenv
GROQ_API_KEY=tu_clave_privada
GROQ_MODEL=openai/gpt-oss-20b
```

Reiniciar Django después de guardar. La clave no se configura en Angular, no se
versiona y no se devuelve por la API. El modelo se ejecuta en Groq; solo el código
de la aplicación y el SDK ocupan RAM del hosting.

## Contrato HTTP

```json
{
  "mensaje": "Hola, soy Juan. ¿Qué proyectos hizo Nahuel con Angular?",
  "idioma": "es",
  "historial": []
}
```

Respuesta: `{"respuesta":"texto de Aubar"}`. `idioma` admite `es` o `en`.
El historial opcional solo acepta objetos `role`/`content` con rol `user` o
`assistant`; no se aceptan instrucciones de sistema desde el cliente.

- Mensaje: 1–1.200 caracteres; cuerpo JSON: máximo 16 KiB.
- Historial: máximo 8 mensajes, 2.000 caracteres por mensaje y 6.000 en total.
- Contexto MCP: presupuesto de 8 segundos; solicitud a Groq: timeout de 18 segundos.
- Generación: hasta 1.200 tokens de salida, con razonamiento bajo para GPT-OSS.
- Máximo 10 consultas por minuto y una generación simultánea **por proceso**.
- Sin caché HTTP y sin almacenamiento de conversaciones en la base de datos.

Devuelve 400/413/415 para entradas inválidas, 403 para orígenes no permitidos,
429 por concurrencia o cuotas y 503 si faltan la clave, el contexto o el proveedor.
No devuelve los cuerpos de error de Groq ni detalles de la base o credenciales.

Los endpoints de datos continúan siendo de solo lectura. CORS admite POST para
el chat; la exención CSRF se limita a este endpoint público sin autenticación,
cookies de sesión ni operaciones que modifiquen datos.

## Frontend y privacidad

El chat se abre a pedido del visitante. Presenta tres preguntas sugeridas,
admite Enter para enviar y Shift+Enter para saltos de línea, y permite cerrar
con Escape o comenzar una nueva conversación. Reintentar un error no duplica
el mensaje del visitante. Respuestas e inputs se renderizan como texto, sin HTML.

Los mensajes quedan en memoria del navegador mientras la página esté abierta,
con hasta 40 mensajes visibles y una ventana de contexto de 8. No se usan
localStorage, cookies ni tablas para guardar conversaciones. Cada consulta
envía a Groq el mensaje, el historial acotado y el contenido público del portfolio;
no afirmar que la conversación es completamente local o que el proveedor no retiene datos.

## Render

Primero publicar los cambios del backend. En el servicio **portfolio-backend**:

1. Abrir **Environment → Add Environment Variable**.
2. Agregar `GROQ_API_KEY` con el valor privado utilizado localmente.
3. Agregar `GROQ_MODEL` con `openai/gpt-oss-20b`.
4. Guardar y desplegar el servicio con las nuevas variables.
5. Publicar el frontend y probar un saludo y una pregunta sugerida en ambos idiomas.

Mantener el Build Command existente: `pip install -r requirements.txt && python
manage.py collectstatic --noinput && python manage.py migrate --noinput`.
MCP ya está en requirements; no requiere instalar modelos de voz, tocar la base
del portfolio ni agregar variables secretas en Vercel.

Usar un worker de Gunicorn al comenzar: los límites y el bloqueo son locales al
proceso. Con varios workers se multiplican; no constituyen una cuota global.
El endpoint es público y su presupuesto puede ser consumido por terceros. No
prometer acceso gratuito ilimitado: se aplican los límites del proveedor y del
hosting, y un servicio dormido puede demorar el primer pedido.

## Validación

```powershell
.\.venv\Scripts\python.exe scripts/test_aubar.py
```

El ejecutor desactiva `.env`, utiliza SQLite en memoria con datos sintéticos y
simula las respuestas de Groq. Verifica contrato, errores, cuotas, concurrencia,
CORS, llamadas MCP reales y exclusión de contenido sin publicar. No toca la base
local ni la de producción. No sustituye la regresión existente sobre PostgreSQL.

En el frontend: `npm test -- --watch=false`, `npm run build` y
`npx playwright test e2e/aubar-chat.spec.ts`. Las pruebas de navegador aíslan
Groq/API y cubren historial, idiomas, reintento, texto no ejecutable y tamaños de pantalla.

También se comprobó localmente el endpoint con la clave real: saludo por nombre,
pregunta de Angular y pregunta de Django en inglés. Esa prueba no verifica Render.
