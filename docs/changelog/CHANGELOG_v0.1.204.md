# OGR Slip2D v0.1.204

**F4b del servidor MCP: HTTPS remoto con OAuth 2.1, para ChatGPT y otros
clientes remotos.** Con esta versión se completa el desarrollo del servidor
MCP que planificó la spec 008 (F0–F4b).

## 1. Qué exige ChatGPT

Según la documentación de OpenAI (Apps SDK, *Authentication*, y la ayuda
del modo desarrollador), leída el 2026-09-24:

- el servidor tiene que ser **HTTPS público**;
- la autenticación es **OAuth 2.1** con PKCE S256;
- hacen falta los metadatos del recurso protegido y los del servidor de
  autorización;
- el registro de clientes es dinámico (DCR) o por CIMD;
- los tokens van atados al recurso;
- las URI de retorno son
  `https://chatgpt.com/connector_platform_oauth_redirect` y
  `https://chatgpt.com/connector/oauth/{callback_id}`.

**No admite un token fijo en cabecera**, que es lo único que tenía el
servidor.

## 2. Diseño: el servidor es su propio servidor de autorización

`ogr_mcp/oauth.py` usa la interfaz de proveedor del SDK instalado (mcp
2.2): `OAuthAuthorizationServerProvider`, `AuthSettings` y `custom_route`.
**No hay dependencias nuevas**; el extra `[mcp]` sigue siendo
`mcp>=2.1,<3`.

- **La autorización la da el dueño con el token del servidor.**
  - `/authorize` lleva a una página propia, `/approve`, que dice qué
    cliente pide acceso, a dónde volverá y que podrá usar `python_exec`.
  - Exige el token del servidor: tener el token es ser el dueño.
  - Un fallo se retrasa un segundo, y cinco fallos bloquean la petición.
  - La comparación es en tiempo constante.
- **Tokens opacos, en memoria.**
  - El código de autorización es de un solo uso y dura 5 min.
  - El de acceso dura una hora y el de renovación 30 días, y rota en cada
    uso.
  - Todos van atados al recurso: el SDK valida la audiencia con
    `validate_token_resource`.
  - Reiniciar el servidor los revoca todos.
- **El token fijo sigue valiendo** como `Bearer`, por el mismo
  verificador.
- **Registro DCR con lista blanca de URI de retorno.** Por defecto entran
  las dos de ChatGPT, la de Claude y las de *loopback*; `--oauth-redirect`
  añade otras.
- **No se ofrece CIMD.** Obligaría al servidor a descargar un documento de
  otro sitio: una llamada de red que el programa no hace (AGENTS.md).

## 3. HTTPS: dos caminos, y el servidor nunca abre un túnel

1. **Detrás de un túnel o *proxy*** que termina el TLS (cloudflared, ngrok,
   Caddy). Es el camino recomendado: el servidor sigue en *loopback*.
   - `--public-url https://…` fija el emisor y el recurso.
   - Añade el `Host` y el `Origin` públicos a los permitidos, que hasta
     ahora darían 421 y 403.
2. **TLS directo**, con `--tls-cert` y `--tls-key`, que se pasan a uvicorn.

**Reglas del contrato, comprobadas antes de escuchar:**

- `--no-auth` nunca va con `--public-url`;
- una `--public-url` `http://` solo se acepta en *loopback*, para pruebas;
- los dos archivos TLS van juntos y tienen que existir;
- `--oauth-redirect` solo con `--public-url`;
- ninguna de estas opciones se acepta sobre stdio.

## 4. Lo que se endureció al probarlo

Cuatro cosas salieron de los tests o de revisar el diseño antes de publicar.
Ninguna estaba en el plan:

- **El límite de intentos era por petición, y cualquiera abre peticiones.**
  - Basta con registrar un cliente con una URI de *loopback*, que está en la
    lista blanca, y pedir otra autorización: cinco intentos más.
  - Ahora, además del bloqueo por petición, **veinte fallos en diez minutos,
    contando todas las peticiones, paran toda aprobación**, también la del
    dueño, hasta que pase la ventana.
- **Con `--public-url`, el token tiene que tener al menos 32 caracteres.**
  En Internet es lo único entre un desconocido y `python_exec`, y la página
  de aprobación deja probarlo. El token generado tiene 43.
- **La lista blanca aceptaba el prefijo de ChatGPT pelado**
  (`https://chatgpt.com/connector/oauth/`, sin `{callback_id}`).
  - Un prefijo solo admite ahora **un segmento** de caracteres de
    identificador detrás.
  - No admite otro segmento más, ni consulta, ni fragmento.
- **La página de aprobación no se puede enmarcar ni guardar**
  (`X-Frame-Options: DENY`, `frame-ancestors 'none'`, `no-store`,
  `no-referrer`). El dueño teclea el token en ella: un marco transparente
  sobre una página señuelo lo recogería.

**Reportado sin corregir (del SDK).** El `/revoke` de mcp 2.2 exige el campo
`client_secret` también a un cliente público:

- `RevocationRequest` lo declara como `str | None`, pero sin valor por
  defecto;
- la autenticación de un cliente `none` lo ignora después;
- un cliente que siga el RFC 7009 al pie de la letra y lo omita recibe un
  400.

No se toca el SDK. Los tokens de acceso caducan en una hora y reiniciar el
servidor los revoca todos. El test manda el campo vacío y lo explica.

## 5. Tests

`tests/test_remote_oauth_v1204.py`:

- **El flujo completo contra un proceso real**:
  - metadatos;
  - 401 sin token, con el enlace a los metadatos;
  - registro, que rechaza una URI ajena;
  - `/authorize` → `/approve`, con las cabeceras que impiden enmarcarla o
    guardarla;
  - un token equivocado (401, con retardo);
  - aprobación;
  - `/token`, que rechaza el código con otro verificador PKCE y un código
    repetido;
  - una llamada MCP con el token emitido y otra con el fijo;
  - renovación rotativa;
  - revocación;
  - otro recurso rechazado en la autorización.
- **El `Host` público** se acepta y cualquier otro sigue en 421.
- **El proveedor**:
  - el bloqueo tras cinco fallos;
  - que abrir peticiones nuevas no reinicia la cuenta;
  - un token de otra audiencia, rechazado por el backend del SDK;
  - la lista blanca, con el prefijo pelado, un segmento de más, una
    consulta y un fragmento.
- **La línea de órdenes**: los cinco casos de §3 y un token corto con
  `--public-url` salen con código 2.
- **HTTPS directo** con un certificado autofirmado hecho en el test (se
  salta sin `cryptography`).

**Lo que no puedo probar**: la conexión real desde chatgpt.com, que
necesita la cuenta del propietario y un túnel. Queda como la tarea manual
2.7 de la spec, con los pasos en `docs/mcp/clientes.md`.

**Verificación:** la suite entera, sin filtros, pasa **4542 de 4542** (unos 34 min).
