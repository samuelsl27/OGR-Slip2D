# Herramientas

Las 56 herramientas del perfil `full`. Las marcadas con **C** están también
en el perfil `compact`. Los parámetros y sus descripciones exactas los
publica el propio servidor (`tools/list`); aquí va para qué sirve cada una.

`tests/test_mcp_server_v1195.py` comprueba que este archivo nombra todas.

## Proyecto (`core`)

| Herramienta | C | Para qué |
|---|---|---|
| `server_info` | C | Versión, unidades, reglas de modelado, modelos abiertos y cobertura del programa. La primera llamada. |
| `catalog` | C | Lo que ofrece el programa: modelos de resistencia con sus parámetros, métodos, búsquedas, tipos de contorno, ajustes con sus opciones. |
| `project_new` | C | Crea un modelo vacío o el talud de demostración; devuelve su `project_id`. |
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
| `boundary_add` | | Un contorno: exterior, de material, nivel freático, piezométrica, desembalse, grieta de tracción, objeto de Block Search, capa débil o superficie anisótropa. Un contorno de material **cerrado** (`closed=true`) es una lente: su propia región y un hueco en la de alrededor (desde v0.1.197). |
| `boundary_edit` | | Editar o borrar un contorno: vértices, traslación, tipo, nombre. |
| `material_set` | | Crear o modificar un material. |
| `material_delete` | | Borrar un material (se niega mientras lo usen regiones). |
| `material_assign` | | Asignar un material a la región que contiene un punto. |
| `external_reshape` | | Expandir o encoger el contorno exterior: desplazamiento paralelo, o una polilínea de relleno o excavación con los dos extremos sobre él. |
| `slope_angle_change` | | Cambiar el ángulo global de la cara del talud entre dos vértices del exterior (pie y coronación): solo se mueve la cara, proyectando en horizontal (por defecto), en vertical o girando; `keep_benches` conserva el ancho de las bermas. Los contornos que acaban en la cara la siguen; soportes y cargas no se mueven (se avisa). |
| `geometry_cleanup` | | Informe de vértices duplicados, autointersecciones y cruces entre contornos; con `apply`, los corrige. |

`boundary_edit` también copia, escala, rota y simplifica. Una lente de material cerrada dentro del modelo se rechaza: el constructor de regiones no la resuelve (reportado en v0.1.196).

## Cargas (`loads`)

| Herramienta | C | Para qué |
|---|---|---|
| `load_set` | | Añadir o cambiar una carga repartida (kPa entre dos puntos) o lineal (kN/m en un punto). |
| `load_delete` | | Borrar cargas. |
| `seismic_set` | | Carga sísmica pseudoestática: kh, kv y si se aplica. |
| `seismic_record_set` | | Añadir un acelerograma (archivo, texto o valores) para el análisis de Newmark, o renombrarlo. |
| `seismic_record_delete` | | Borrar un acelerograma. |

Una carga lineal «normal al contorno» o «con ángulo respecto al contorno» toma su dirección de la superficie del terreno en su punto (desde v0.1.199): la normal apunta hacia el terreno (en un vértice, la bisectriz), y el ángulo se mide en sentido antihorario desde el terreno recorrido de izquierda a derecha, así que −90° es la normal. Fuera del terreno se rechaza.

## Soportes (`supports`)

| Herramienta | C | Para qué |
|---|---|---|
| `support_type_set` | | Definir o cambiar un tipo de soporte (conjunto de propiedades de una clase). |
| `support_type_delete` | | Borrar un tipo (se niega mientras haya soportes que lo usan). |
| `support_set` | | Colocar un soporte (cabeza en la cara del talud, cola dentro) o moverlo, estirarlo o editarlo. |
| `support_pattern_add` | | Una fila de soportes a lo largo de un segmento. |
| `support_delete` | | Borrar soportes o un patrón entero. |
| `support_ungroup` | | Desagrupar un patrón. |

## Búsqueda (`search`)

| Herramienta | C | Para qué |
|---|---|---|
| `tension_crack_set` | | Agua en la grieta de tracción. |
| `focus_set` | | Objetos de foco (ventana, línea, punto, tangente) que acotan la búsqueda. |
| `focus_delete` | | Borrar objetos de foco. |
| `user_surface_add` | | Un círculo propio que se analiza junto a la búsqueda. |
| `user_surface_delete` | | Borrarlos. |

## Anotaciones (`annotations`)

| Herramienta | C | Para qué |
|---|---|---|
| `annotation_set` | | Dibujar líneas, flechas, textos, cotas, ejes, imágenes; cambiarlas u ocultarlas. El cálculo nunca las lee. |
| `annotation_delete` | | Borrarlas. |
| `annotation_to_boundary` | | El único puente, explícito, de un dibujo al modelo. |
| `properties_table` | | Tablas de materiales, soportes o propiedades hidráulicas. |

## Archivos (`files`)

| Herramienta | C | Para qué |
|---|---|---|
| `dxf_inspect` | | Leer un DXF sin importarlo: capas, tipo propuesto, unidad y problemas. |
| `dxf_import` | | Importar su geometría (un paso de deshacer). |
| `dxf_export` | | Exportar el modelo y las superficies críticas de un resultado. |
| `report_generate` | | Informe PDF de un análisis. |
| `properties_import` | | Copiar materiales o tipos de soporte de otro `.ogr`. |

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
