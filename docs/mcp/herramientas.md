# Herramientas

Las 28 herramientas del perfil `full`. Las marcadas con **C** están también
en el perfil `compact`. Los parámetros y sus descripciones exactas los
publica el propio servidor (`tools/list`); aquí va para qué sirve cada una.

`tests/test_mcp_server_v1195.py` comprueba que este archivo nombra todas.

## Proyecto (`core`)

| Herramienta | C | Para qué |
|---|---|---|
| `server_info` | C | Versión, unidades, reglas de modelado, modelos abiertos y cobertura del programa. La primera llamada. |
| `catalog` | C | Lo que ofrece el programa: modelos de resistencia con sus parámetros, métodos, búsquedas, tipos de contorno, ajustes con sus opciones. |
| `project_new` | C | Crea un modelo vacío; devuelve su `project_id`. |
| `project_open` | C | Abre un `.ogr`. |
| `project_save` | C | Guarda en `.ogr`, el formato que abre el programa de escritorio. |
| `project_close` | | Cierra un modelo; se niega a perder cambios sin guardar salvo que se le diga. |
| `project_list` | | Los modelos abiertos. |
| `project_summary` | C | El modelo: contornos, materiales, qué material ocupa cada región y **cómo** (asignado, heredado o el primero por defecto), estado, historial y resultados. |
| `project_validate` | | Lo que comprobaría un cálculo, sin calcular. |
| `project_get` | | Una sección del modelo tal como la guarda el `.ogr`. |

## Modelo (`model`)

| Herramienta | C | Para qué |
|---|---|---|
| `model_define` | C | El modelo entero en una llamada: contornos, materiales, un punto dentro de la región de cada uno, nivel freático y ajustes. |
| `boundary_add` | | Un contorno: exterior, de material, nivel freático, piezométrica, desembalse, grieta de tracción, objeto de Block Search, capa débil o superficie anisótropa. |
| `boundary_edit` | | Editar o borrar un contorno: vértices, traslación, tipo, nombre. |
| `material_set` | | Crear o modificar un material. |
| `material_delete` | | Borrar un material (se niega mientras lo usen regiones). |
| `material_assign` | | Asignar un material a la región que contiene un punto. |

## Ajustes (`settings`)

| Herramienta | C | Para qué |
|---|---|---|
| `settings_get` | | Todos los ajustes con su valor, tipo y opciones. |
| `settings_set` | | Cualquier ajuste por ruta (`search.search_method`); todo o nada. |
| `analysis_configure` | C | Los ajustes de análisis más comunes en una llamada: métodos, tipo de superficie, búsqueda, dovelas, grid, dirección de rotura, norma. |

## Análisis (`analysis`)

| Herramienta | C | Para qué |
|---|---|---|
| `analysis_run` | C | Lanza el análisis en segundo plano; devuelve el resultado o un `job_id`. |
| `job_get` | C | Estado y progreso de un trabajo; su resultado al terminar. |
| `job_cancel` | C | Detiene un análisis y todos los procesos que arrancó. |
| `job_list` | | Los trabajos de la sesión. |
| `results_get` | C | Leer un resultado: resumen, superficie crítica con dovelas, mejores superficies, mínimos, avisos. |
| `surface_evaluate` | | El factor de seguridad de UNA superficie dada (círculo, tres puntos o polilínea), sin búsqueda. |

## Vista, historia y Python

| Herramienta | C | Para qué |
|---|---|---|
| `model_render` | C | Imagen PNG del modelo, con las superficies críticas de un resultado. |
| `project_history` | | Deshacer, rehacer o listar las ediciones. |
| `python_exec` | C | Python contra el modelo, para lo que aún no tiene herramienta. Ver [seguridad.md](seguridad.md). |

## Recursos

| URI | Contenido |
|---|---|
| `ogr://guide` | La guía de modelado completa que lee el agente. |
| `ogr://catalog/{kind}` | `catalog(kind)` como recurso. |
