# Servidor MCP de OGR Slip2D

Un agente de IA —Claude, un modelo local en LM Studio u Ollama, Open WebUI,
BionicGPT, OpenAI— puede manejar OGR Slip2D sin abrir la interfaz: construir el
modelo, calcularlo, leer los resultados y verlos en una imagen. Lo hace a
través del **Model Context Protocol** (MCP), el estándar abierto para conectar
modelos de lenguaje con programas.

Especificación de diseño: [`spec/features/008-servidor-mcp/`](../../spec/features/008-servidor-mcp/spec.md).

## Instalación

```bash
pip install -e ".[mcp]"        # desde el repositorio
ogr-slip2d-mcp --version
```

El extra `[mcp]` añade el SDK oficial de MCP para Python (licencia MIT). El
programa de escritorio no lo necesita; sólo el servidor.

Si el comando `ogr-slip2d-mcp` no está en el `PATH`, `python -m ogr_mcp`
hace exactamente lo mismo.

## Arranque

```bash
# stdio: lo lanza el cliente (Claude, LM Studio, OpenAI Agents SDK...)
ogr-slip2d-mcp --workdir "C:\ruta\a\mis\proyectos"

# perfil reducido para modelos locales pequeños
ogr-slip2d-mcp --profile compact --workdir "C:\ruta\a\mis\proyectos"

# HTTP (Open WebUI, mcpo): siempre con token
ogr-slip2d-mcp --transport http --port 8765 --token-file token.txt
```

`--workdir` es la carpeta contra la que se resuelven las rutas relativas
(abrir y guardar `.ogr`, guardar imágenes). Sin él, las rutas tienen que ser
absolutas. Muchos clientes arrancan el servidor en una carpeta que nadie
eligió, así que conviene darlo siempre.

Opciones completas: `ogr-slip2d-mcp --help`.

## Qué puede hacer hoy

28 herramientas, descritas en [herramientas.md](herramientas.md):

- abrir, crear, guardar y describir modelos;
- el modelo entero en una llamada (`model_define`): contornos, materiales,
  qué material ocupa cada región y el nivel freático;
- ajustes con validación: un nombre o valor mal escrito se rechaza con una
  sugerencia, nunca se acepta en silencio;
- análisis en segundo plano, cancelables;
- resultados, superficies críticas con sus dovelas, e imagen PNG del modelo;
- deshacer y rehacer;
- `python_exec` para todo lo que aún no tiene herramienta (ver
  [seguridad.md](seguridad.md)).

`server_info` dice cuánto del menú del programa cubre ya el agente
(`program_coverage`). Lo que falta —cargas, soportes, DXF, informe, foco,
anotaciones (fase F2); agua con elementos finitos, estadística,
retroanálisis (F3)— llega en las próximas versiones, y hasta entonces se
alcanza con `python_exec`.

## Configurar cada cliente

Ver [clientes.md](clientes.md): Claude Desktop, Claude Code, LM Studio,
clientes de Ollama, Open WebUI, BionicGPT y otros clientes OpenAPI (con
`mcpo`), OpenAI Agents SDK y ChatGPT.

## Cómo trabaja un agente con él

```
project_new → model_define → project_validate → analysis_configure
            → analysis_run → results_get / model_render → project_save
```

Unidades SI siempre (m, kN, kPa, kN/m³, grados). La guía completa que lee el
agente está en el recurso `ogr://guide` y en
[`ogr_mcp/guide.py`](../../ogr_mcp/guide.py).
