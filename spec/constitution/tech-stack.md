# Stack y convenciones

Las convenciones completas están en [`AGENTS.md`](../../AGENTS.md), que es
la fuente única. Este archivo resume solo las decisiones **estructurales**
y por qué se tomaron.

## Decisiones y su motivo

| Decisión | Motivo |
|---|---|
| **Python 3.11+** | Legibilidad y ecosistema científico. La velocidad se resuelve vectorizando con NumPy donde importa. |
| **PySide6, no PyQt** | Licencia LGPL, compatible con la distribución del proyecto. |
| **`scipy.spatial.Delaunay`, no `triangle`** | La licencia de `triangle` prohíbe el uso comercial: incompatible con AGPL. |
| **`.ogr` en JSON puro, sin HDF5** | Los resultados se **recalculan**, no se almacenan. Más simple, sin dependencia binaria, y evita que resultados obsoletos sobrevivan a un cambio del modelo. |
| **AGPL-3.0-or-later, no GPL** | Una versión modificada ofrecida como servicio de red debe publicar su fuente; la GPL no lo exige porque servir no es distribuir. |
| **Runner de tests propio** | Sin dependencia de pytest, con un `pytest` simulado suficiente para el estilo de tests del proyecto. |
| **Motor sin noción de normas** | Los coeficientes parciales se aplican transformando una copia del proyecto. Añadir una norma es una tabla de números, no un cambio en la matemática. |
| **Capa de operaciones `ogr_api`, sin Qt ni `mcp`** (v0.1.194, spec 008) | Un agente de IA, un script y —desde F4— el puente con la interfaz manejan el programa por las MISMAS operaciones con nombre. Valida lo que los dataclasses aceptan en silencio, hace de cada edición un paso de deshacer y corre los análisis en un subproceso cancelable. El SDK de MCP (MIT) entra como extra opcional `[mcp]` en v0.1.195, nunca como dependencia del programa. |
| **Los trabajos, en subproceso y no en hilo** | El motor no se puede interrumpir y un hilo no se puede matar; cancelar un análisis de una hora tiene que ser real. |

## Separaciones que no deben romperse

- **Motor ↔ interfaz**: el motor no conoce unidades de usuario, idiomas ni
  normas de diseño.
- **Anotación ↔ modelo físico**: el solver nunca lee `Project.annotations`.
  El único puente es *Convert Tool to Boundary*, explícito y unidireccional.
- **Cálculo ↔ presentación**: los contornos devuelven cadenas de color y no
  dependen de Qt, para poder probarlos y reutilizarlos en informes.
- **Operaciones ↔ transporte**: `ogr_api` no sabe si le llama un agente por
  stdio, por HTTP o la interfaz; el transporte (`ogr_mcp`, el puente de F4)
  no decide nada sobre el modelo. Una regla de modelo vive en
  `ogr_core/project/rules.py` y ninguno de los dos la copia.
