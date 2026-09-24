# Plan de implementación

## Enfoque

Capas en un solo sentido:

```
ogr_core ─► ogr_slip2d / ogr_fem2d ─► ogr_api ─► { ogr_mcp, ogr_gui (puente F4), ogr_cli }
```

`ogr_api` es un **registro de operaciones con nombre**: funciones Python
tipadas que reciben un `project_id` y devuelven JSON seguro. `ogr_mcp` escribe
a mano una herramienta por operación (para controlar descripciones y tipos),
y el puente de F4 reenviará `(operación, kwargs)` al mismo registro, de modo
que el puente sea sólo un cambio de transporte.

## Archivos que se tocan (F1a)

| Archivo | Qué cambia |
|---|---|
| `ogr_core/project/rules.py` | nuevo — invariantes movidas de la GUI |
| `ogr_core/project/commands.py` | `SnapshotCommand` |
| `ogr_slip2d/analysis_runner.py` | `evaluate_surfaces` (una puerta para una superficie dada) |
| `ogr_api/` | nuevo — workspace, coerción, esquema de ajustes, catálogo, operaciones, resultados, render, `python_exec`, jobs |
| `ogr_gui/main_window.py` | delega en `rules.py` |
| `ogr_gui/reported_quantity.py` | delega la decisión de magnitud en `ogr_api.results` |

## Decisiones de diseño

- **Copias con `deepcopy`, nunca con `to_dict`/`from_dict`.** El viaje por
  JSON aplica migraciones por valor (D182: un `max_lambda = 1,5` deliberado
  vuelve como 6,0), así que no es una identidad. Una copia de trabajo que
  cambiara ajustes sería el mismo defecto que se quiere evitar.
- **Deshacer por instantánea de atributos ligeros** (`SnapshotCommand`), que
  restaura **sobre el mismo objeto** `Project`: vale igual en *headless* y en
  el puente, donde la GUI tiene referencias al objeto. Los atributos pesados
  (malla, campo de filtración) sólo entran si la operación los declara.
- **Jobs en subproceso, no en hilo.** Un hilo no se puede matar y el motor no
  tiene cancelación; el subproceso además aísla un fallo nativo y deja la
  salida estándar fuera del protocolo. Es un proceso **no daemon**, para que el
  pool del grid paralelo siga pudiendo arrancar dentro.
- **Resumen dentro del worker**: un `SearchResult` de 4840 círculos pesa unos
  30 MB con todas sus dovelas; viaja el resumen y, aparte, el resultado
  completo en un pickle que sólo se lee si se pide.
- **Render con matplotlib Agg** (`Figure` + `FigureCanvasAgg`, sin pyplot):
  los manejadores del servidor corren en hilos de trabajo y `QGraphicsScene`
  exige el hilo principal de una `QGuiApplication`. En F4 el puente devuelve
  una captura del lienzo real.
- **stdout.** El SDK 2.x ya desvía el descriptor 1 a stderr mientras sirve por
  stdio y sirve el protocolo desde un duplicado privado (medido en el *spike*
  de F0 sobre `mcp` 2.2.0). No se reimplementa; se **prueba** de extremo a
  extremo.
- **Errores inesperados.** El SDK 2.x oculta el detalle de una excepción que
  no sea `ToolError` («Error executing tool X»). La envoltura convierte toda
  excepción en `ToolError` con su tipo y mensaje, que es lo único que le
  permite al agente corregirse.
- **Seguridad HTTP.** Token *bearer* por *middleware* ASGI propio sobre la app
  del SDK (la autenticación del SDK está pensada para OAuth y exige un emisor),
  más `TransportSecuritySettings` para `Origin`/`Host`.

## Riesgos

- Deriva entre la GUI y `ogr_api` si una regla se copia en vez de moverse: la
  vigilan los tests de delegación y el inventario de acciones.
- Windows: arranque de 1–2 s por job, `taskkill /T` para el árbol, y el
  directorio de trabajo arbitrario con el que arrancan algunos clientes.
- Modelos locales pequeños: su calidad no la controla el servidor; la prueba
  manual con dos o tres modelos es criterio de aceptación de F1b.
