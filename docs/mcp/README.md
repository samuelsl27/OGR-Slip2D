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

56 herramientas, descritas en [herramientas.md](herramientas.md):

- abrir, crear (vacío o el talud de demostración), guardar y describir
  modelos;
- el modelo entero en una llamada (`model_define`): contornos, materiales,
  qué material ocupa cada región y el nivel freático;
- editar contornos: mover, copiar, escalar, girar, simplificar, ampliar o
  recortar el exterior, y revisar la geometría (vértices repetidos, cruces);
- cargas repartidas y puntuales, sismo pseudoestático y registros de
  aceleración;
- tipos de soporte y soportes, sueltos o en patrón;
- grieta de tracción y su agua, objetos de foco y superficies propias;
- anotaciones, y su único puente a la geometría (`annotation_to_boundary`);
- DXF de entrada y de salida, informe PDF e importar propiedades de otro
  proyecto;
- ajustes con validación: un nombre o valor mal escrito se rechaza con una
  sugerencia, nunca se acepta en silencio;
- análisis en segundo plano, cancelables;
- resultados, superficies críticas con sus dovelas, e imagen PNG del modelo;
- deshacer y rehacer: cada edición es un paso;
- `python_exec` para todo lo que aún no tiene herramienta (ver
  [seguridad.md](seguridad.md)).

Un ajuste que el cálculo no leería se rechaza con el motivo en vez de
guardarse: una carga puntual normal al contorno fuera del terreno (no tiene
contorno al que ser normal), `angle_deg` con una carga vertical, una
tolerancia de foco en una ventana... Es la regla 7 del proyecto aplicada en la puerta.

`server_info` dice cuánto del menú del programa cubre ya el agente
(`program_coverage`): 99 de las 136 acciones de la ventana principal, 23 son
sólo de interfaz (zoom, *pan*...) y quedan 14, todas de la fase F3 (agua con
elementos finitos, estadística, retroanálisis, optimización). Hasta entonces
se alcanzan con `python_exec`.

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
