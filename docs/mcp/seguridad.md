# Seguridad del servidor MCP

## `python_exec` es ejecución de código, por diseño

El servidor publica siempre la herramienta `python_exec`, que ejecuta Python
arbitrario en el proceso del servidor con los permisos del usuario que lo
arrancó. Es una decisión del propietario (2026-09-24), la misma que toman los
servidores MCP de Blender y de QGIS: cubre todo lo que aún no tiene
herramienta propia.

La consecuencia es sencilla: **quien pueda hablar con el servidor puede
ejecutar código en tu máquina.** Todo lo demás se sigue de ahí.

## stdio

Con stdio (Claude, LM Studio, OpenAI Agents SDK) el servidor es un proceso
hijo del cliente y no abre ningún puerto. El riesgo que queda es la
**inyección de instrucciones**: un texto que el modelo lea —un archivo, una
web— puede pedirle que ejecute algo. Los clientes que piden confirmación antes
de cada herramienta (Claude Desktop, Claude Code) son la defensa; no la
desactives para `python_exec`.

## HTTP

- **Token siempre, también en 127.0.0.1.** «Sólo local» no es una frontera:
  cualquier página que visites puede hacer que tu navegador envíe peticiones
  a `localhost`. El token se compara en tiempo constante.
- **Host y Origin comprobados.** La protección contra *DNS rebinding* del SDK
  está activada: un `Host` que no es el del servidor recibe 421, y un
  `Origin` ajeno 403, incluso con token. `--allow-origin` añade orígenes.
- **Sin token no hay red.** Con un `--host` que no sea de *loopback*, el
  servidor exige un token explícito (`--token-file` u `OGR_MCP_TOKEN`) y se
  niega a arrancar sin él (código de salida 2). `--no-auth` sólo se acepta en
  *loopback*.
- Prefiere `--token-file` o la variable `OGR_MCP_TOKEN` a `--token`: un
  argumento de la línea de órdenes lo ven los demás usuarios de la máquina.

## El puente con la ventana

Desde v0.1.207 el programa **abre su puente al arrancar**, por decisión del
propietario: si OGR Slip2D está abierto, lo que pide un agente se hace en la
ventana. El puente escucha **solo en 127.0.0.1**, con un token aleatorio
nuevo cada vez.

- **El token.** Queda en `~/.ogr-slip2d/bridges/<pid>.json`, dentro de tu
  carpeta de usuario; en sistemas POSIX, ese archivo solo lo puedes leer tú.
  Sin el token, la ventana cierra la conexión tras la primera línea.
- **Lo que da.** Quien tenga el puente maneja la ventana, incluido
  `python_exec`, que corre **dentro del proceso de la ventana**.
- **No abre acceso nuevo.** Leer ese archivo exige ser tu usuario en esta
  máquina, y quien ya lo es puede ejecutar lo que quiera. Aun así, si no lo
  quieres encendido, apágalo en *Herramientas > Puente para agentes (MCP)*
  o abre el programa con `--no-agent-bridge`.
- **Los tests nunca ven tu ventana.** El runner da a toda la corrida una
  carpeta de descubrimiento vacía propia. Un test que arranca un servidor no
  puede editar el modelo que tengas abierto.

## Exposición a Internet (`--public-url`)

Exponer el servidor a Internet es exponer `python_exec`, es decir, tu
máquina. Hazlo solo si lo necesitas —ChatGPT no se conecta de otra forma— y
apágalo al terminar.

- **El servidor no abre túneles por su cuenta.** Pones tú delante un túnel o
  un proxy que termine el HTTPS (cloudflared, ngrok, Caddy…). El servidor
  sigue escuchando en `127.0.0.1` y se le dice su dirección pública con
  `--public-url https://…`. Alternativa: `--tls-cert` y `--tls-key` sirven
  HTTPS directamente.
- **Con `--public-url` el servidor es su propio servidor OAuth 2.1**
  (PKCE S256, registro dinámico, tokens atados al recurso). La
  autorización se concede **escribiendo el token del servidor** en su página
  `/approve`: tener el token es ser el dueño.
  - Los intentos fallidos se retrasan un segundo.
  - Tras cinco intentos fallidos, la petición queda bloqueada.
  - Tras veinte en diez minutos, contando todas las peticiones, se para
    toda aprobación durante un rato. Cualquiera puede abrir una petición
    nueva, así que un límite solo por petición no acotaría los intentos.
  - Por eso mismo, con `--public-url` el token tiene que tener al menos 32
    caracteres. El que genera el servidor tiene 43.
  - Ninguna otra web puede enmarcar la página (`X-Frame-Options`,
    `frame-ancestors`), y ni la página ni su procedencia se guardan
    (`no-store`, `no-referrer`).
- **Los tokens que emite:**
  - son opacos y viven en memoria: reiniciar el servidor los revoca todos;
  - el de acceso dura una hora y el de renovación, treinta días (rota en
    cada uso).
- **El token fijo sigue valiendo** como `Authorization: Bearer` para los
  clientes que mandan cabeceras.
- **Solo se registran clientes cuyas URI de retorno están en una lista
  blanca**: las de ChatGPT, la de Claude y las de *loopback*.
  `--oauth-redirect` añade otras.
- **No se ofrece CIMD** (documentos de metadatos de cliente por URL):
  obligaría al servidor a descargar un documento de otro sitio, y el
  servidor no hace llamadas de red.
- `--no-auth` nunca va con `--public-url`, y una `--public-url` `http://`
  solo se acepta en *loopback*, para pruebas.
- El `Host` y el `Origin` públicos se añaden a los permitidos; cualquier
  otro sigue recibiendo 421 / 403.

## Archivos

Las rutas relativas se resuelven contra `--workdir`. Guardar nunca
sobrescribe un archivo existente sin `overwrite=true`, salvo el propio archivo
del modelo, que es lo que significa guardar.

## Red y telemetría

El servidor no hace ninguna llamada de red por su cuenta. La dependencia
`opentelemetry-api` que trae el SDK es sólo la API: sin un SDK de telemetría
configurado, no exporta nada.
