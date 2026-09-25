# Conectar cada cliente

En todos los ejemplos, sustituye `C:\ruta\a\mis\proyectos` por tu carpeta de
trabajo. Si `ogr-slip2d-mcp` no está en el `PATH`, usa como comando la ruta
completa de tu Python con los argumentos `-m ogr_mcp ...`.

## Claude Code

```bash
claude mcp add ogr-slip2d -- ogr-slip2d-mcp --workdir "C:\ruta\a\mis\proyectos"
```

## Claude Desktop

Edita `%APPDATA%\Claude\claude_desktop_config.json` (Windows) o
`~/Library/Application Support/Claude/claude_desktop_config.json` (macOS).
**La versión de la Microsoft Store** lo guarda en su propia carpeta:
`%LOCALAPPDATA%\Packages\Claude_<id>\LocalCache\Roaming\Claude\claude_desktop_config.json`.
Comprobado el 2026-09-25: su configuración estaba allí, y lo que se añadió
allí fue lo que cargó.
Si el comando no está en el `PATH` de la aplicación, pon la ruta completa de
`ogr-slip2d-mcp.exe`:

```json
{
  "mcpServers": {
    "ogr-slip2d": {
      "command": "ogr-slip2d-mcp",
      "args": ["--workdir", "C:\\ruta\\a\\mis\\proyectos"]
    }
  }
}
```

## LM Studio (modelos locales)

`%USERPROFILE%\.lmstudio\mcp.json` en Windows, `~/.lmstudio/mcp.json` en
macOS y Linux. Mismo formato que Cursor:

```json
{
  "mcpServers": {
    "ogr-slip2d": {
      "command": "ogr-slip2d-mcp",
      "args": ["--profile", "compact", "--workdir", "C:\\ruta\\a\\mis\\proyectos"]
    }
  }
}
```

**Usa `--profile compact` con modelos pequeños.** Publica 14 herramientas en
vez de 74; `model_define` hace la geometría en una sola llamada y
`python_exec` cubre el resto. Un modelo pequeño se pierde entre muchas
herramientas, y cada descripción ocupa contexto en cada petición.

## Ollama

Ollama sirve modelos pero no habla MCP: lo habla el cliente que los usa. Con
[mcp-client-for-ollama](https://github.com/jonigl/mcp-client-for-ollama) (o
cualquier cliente MCP que acepte el formato `mcpServers`), la entrada es la
misma que la de LM Studio, con `--profile compact`.

## Open WebUI

Open WebUI sólo acepta MCP por **HTTP** (*Streamable HTTP*, desde la v0.6.31).

1. Arranca el servidor con un token:

   ```bash
   ogr-slip2d-mcp --transport http --port 8765 --token-file token.txt --workdir "C:\ruta\a\mis\proyectos"
   ```

   Sin `--token-file` ni `OGR_MCP_TOKEN` el servidor genera uno y lo escribe
   en su salida de errores al arrancar.
2. En Open WebUI: *Settings → Admin → Integrations → External Tool Servers →
   + Add Connection*. Type **MCP (Streamable HTTP)**, URL
   `http://127.0.0.1:8765/mcp`, Auth **Bearer** y el token en *Key*.

Si Open WebUI corre en Docker, `127.0.0.1` es el contenedor, no tu máquina:
usa `http://host.docker.internal:8765/mcp` y arranca el servidor con
`--host 0.0.0.0` **y** un token explícito (sin token se niega a arrancar).

## BionicGPT y otros clientes OpenAPI (con `mcpo`)

BionicGPT integra herramientas por **OpenAPI**. [`mcpo`](https://github.com/open-webui/mcpo)
convierte un servidor MCP en una API OpenAPI sin código propio.

**`mcpo` va en su propio entorno, con `mcp<2`.** Medido el 2026-09-24:
`mcpo` 0.0.20 no arranca con el SDK `mcp` 2.x (importa
`streamablehttp_client`, que la 2.0 renombró), y no fija la versión. En un
entorno aparte con `mcp` 1.30 funciona, y de paso demuestra que este servidor
atiende a los clientes antiguos del protocolo de 2025:

```bash
python -m venv mcpo-env
mcpo-env\Scripts\pip install mcpo "mcp<2"
mcpo-env\Scripts\mcpo --port 8000 --api-key "tu-clave" -- ogr-slip2d-mcp --workdir "C:\ruta\a\mis\proyectos"
```

(En Linux y macOS, `mcpo-env/bin/...`.) `ogr-slip2d-mcp` sigue siendo el de tu
entorno normal, el que tiene OGR Slip2D.

La especificación OpenAPI queda en `http://localhost:8000/openapi.json` y la
documentación interactiva en `http://localhost:8000/docs`. Da esa URL y la
clave al cliente OpenAPI.

`model_render` devuelve la imagen como *data URI*, que un cliente OpenAPI no
siempre muestra: pásale `save_path` y queda además en disco. Un error de una
herramienta llega como HTTP 500 con el mensaje del servidor en `detail`
(código, qué está mal y la sugerencia).

## OpenAI Agents SDK (Python)

```python
from agents import Agent, Runner
from agents.mcp import MCPServerStdio

async with MCPServerStdio(
    params={"command": "ogr-slip2d-mcp",
            "args": ["--workdir", r"C:\ruta\a\mis\proyectos"]},
    client_session_timeout_seconds=60,   # un análisis puede tardar
) as ogr:
    agent = Agent(name="geotecnia", mcp_servers=[ogr],
                  instructions="Analiza taludes con OGR Slip2D.")
    result = await Runner.run(agent, "Construye y calcula el talud ...")
```

`client_session_timeout_seconds` importa: el valor por defecto del SDK es
de pocos segundos y `analysis_run` espera hasta 30 s por defecto antes de
devolver un `job_id`. O súbelo, o pide `wait_seconds` pequeños y usa `job_get`.

## Ver en el programa lo que hace el agente

**No hay nada que configurar** (desde v0.1.207). Si OGR Slip2D está
abierto, lo que pidas al agente se hace **en su ventana**, desde cualquier
cliente. Si no está abierto, el servidor trabaja con modelos propios, como
antes. El orden en que abras el programa y el cliente da igual. Si cierras
el programa y lo vuelves a abrir, el servidor lo encuentra solo.

- **El programa arranca su puente al abrirse.** Es la opción *Herramientas >
  Puente para agentes (MCP)*, que ya sale marcada. Se apaga desde ese menú o
  abriendo el programa con `python -m ogr_gui --no-agent-bridge`.
- **Con la ventana abierta, es tu modelo:**
  - cada edición del agente es un paso de *Edición > Deshacer*, y el lienzo
    se redibuja;
  - un `analysis_run` del agente sale en el panel de resultados y en el
    lienzo, como un *Compute*;
  - `model_render(source="window")` es una captura del lienzo tal como lo
    ves.
- **`project_new` y `project_open` abren en la ventana**, y se niegan
  mientras haya cambios sin guardar: el agente no decide tirar tu trabajo.
  Tiene que guardarlos o preguntarte.
- **Mientras la ventana calcula, las operaciones que editan devuelven
  `Busy`**: el cálculo de la ventana usa el modelo vivo.
- **Lo que ya era del servidor sigue siendo suyo.** Un modelo que el agente
  empezó antes de abrir el programa sigue en el servidor. `server_info` dice
  a dónde va la siguiente llamada, y cada modelo de `open_models` dice si
  está en la ventana.
- **Las rutas relativas** se resuelven contra el `--workdir` del servidor
  también en la ventana.

Dos opciones del servidor cambian este comportamiento:

- `--headless` no usa nunca la ventana (el comportamiento anterior a
  v0.1.207);
- `--attach [PID]` usa **solo** una ventana, nunca modelos propios, y sin
  ventana dice qué abrir. Con varias ventanas abiertas, el modo por defecto
  usa la más reciente y `--attach PID` elige una.

El puente escucha solo en `127.0.0.1`, con un token aleatorio que la ventana
escribe en `~/.ogr-slip2d/bridges/<pid>.json`. Ese archivo se borra al
apagar el puente o cerrar la ventana. Ver [seguridad.md](seguridad.md).

## ChatGPT

ChatGPT solo se conecta a servidores **HTTPS públicos** y solo mediante
OAuth. Antes de seguir, lee [seguridad.md](seguridad.md): exponer este
servidor a Internet es exponer `python_exec`, es decir, tu máquina.

1. Arranca el servidor en *loopback*, con un token que conozcas:

   ```bash
   ogr-slip2d-mcp --transport http --port 8765 --token-file token.txt --public-url https://TU-TUNEL.example --workdir "C:\ruta\a\mis\proyectos"
   ```

   El token tiene que tener al menos 32 caracteres. Sin `--token-file`, el
   servidor genera uno y lo escribe en la consola.

2. Pon delante un túnel que termine el HTTPS y apunte a
   `http://127.0.0.1:8765`. Por ejemplo, `cloudflared tunnel --url
   http://127.0.0.1:8765` te da la dirección que va en `--public-url`, y
   entonces hay que reiniciar el servidor con ella.
3. En ChatGPT, activa el **modo desarrollador** y crea un conector (la
   ayuda de OpenAI, *Developer mode and MCP apps in ChatGPT*, dice dónde en
   cada plan):
   - dirección: `https://TU-TUNEL.example/mcp`;
   - autenticación: **OAuth**.
4. ChatGPT te lleva a la página `/approve` del servidor. Comprueba que el
   cliente es el que esperas y escribe el token de `token.txt`.
5. Al terminar, cierra el túnel y el servidor.

La conexión desde chatgpt.com no la cubren los tests del repositorio: hay que
hacerla a mano (tarea 2.7 de la spec 008). Los tests sí recorren el mismo
flujo OAuth completo contra un servidor real en local, y HTTPS con un
certificado propio.

## Comprobar la conexión

Pide al agente que llame a `server_info`. Debe responder con la versión, las
unidades (SI) y la lista de herramientas publicadas.
