# Herramientas

Las 74 herramientas del perfil `full`. Las marcadas con **C** están también
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
| `material_set` | | Crear o modificar un material, también su envolvente de desembalse rápido (`drawdown_envelope`, desde v0.1.200). Las propiedades hidráulicas van por `hydraulic_set`. |
| `material_delete` | | Borrar un material (se niega mientras lo usen regiones). |
| `material_assign` | | Asignar un material a la región que contiene un punto. |
| `external_reshape` | | Expandir o encoger el contorno exterior: desplazamiento paralelo, o una polilínea de relleno o excavación con los dos extremos sobre él. |
| `slope_angle_change` | | Cambiar el ángulo global de la cara del talud entre dos vértices del exterior (pie y coronación): solo se mueve la cara, proyectando en horizontal (por defecto), en vertical o girando; `keep_benches` conserva el ancho de las bermas. Los contornos que acaban en la cara la siguen; soportes y cargas no se mueven (se avisa). |
| `geometry_cleanup` | | Informe de vértices duplicados, autointersecciones y cruces entre contornos; con `apply`, los corrige. |

`boundary_edit` también copia, escala, rota y simplifica.

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

## Agua subterránea (`groundwater`, desde v0.1.200)

| Herramienta | C | Para qué |
|---|---|---|
| `hydraulic_set` | | Propiedades hidráulicas de un material: permeabilidad saturada y anisotropía, modelo de la zona no saturada (con su biblioteca de suelos), contenidos de agua y almacenamiento. Un parámetro de otro modelo se rechaza. |
| `mesh_generate` | | Malla de elementos finitos. Sustituye a la anterior y borra sus condiciones de contorno y sus campos, también las de las etapas del transitorio: van por número de nodo. |
| `mesh_reset` | | Quitar la malla y todo lo calculado sobre ella. |
| `seepage_bc_set` | | Una condición de contorno en un lado (`left`, `right`, `bottom`, `ground`), en nodos, a lo largo de una polilínea del contorno, o un embalse a una cota. |
| `seepage_bc_clear` | | Volver a las condiciones por defecto (desconocida en la superficie, sin flujo en el resto), que no prescriben ninguna carga. |
| `transient_set` | | El transitorio por etapas: tiempos, condiciones de cada etapa, *Calculate SF* y estado inicial. |
| `water_grid_set` | | Rejilla de presiones de agua (puntos o un CSV) y sus opciones de interpolación. |
| `water_grid_delete` | | Quitarla. |
| `groundwater_run` | | Resolver el agua (permanente, o las etapas del transitorio con su factor de seguridad) en segundo plano. El campo se escribe de vuelta en el modelo en un paso de deshacer, salvo que el modelo haya cambiado mientras tanto. |
| `groundwater_results` | | Leer el campo: resumen, valores en un punto, caudal por una sección, superficie libre, etapas con sus factores, o todos los nodos en CSV. Funciona también tras reabrir el proyecto. |
| `drawdown_sweep_run` | | Desembalse rápido a varias cotas del embalse, porque el desembalse total no siempre es el peor; por la misma puerta que un análisis (coeficientes de diseño y comprobaciones). |

Unidades: cargas hidráulicas en m y presión intersticial en kPa; permeabilidad, infiltración y caudal nodal en una misma unidad coherente (m/s). Desde v0.1.200 cada modelo de permeabilidad toma su succión en la unidad de su propia definición: van Genuchten y Gardner en altura (α en 1/m), Brooks-Corey, Fredlund-Xing, Simple y la curva de usuario en succión matricial (kPa).

## Estadística, retroanálisis y optimización (`statistics`, desde v0.1.201)

| Herramienta | C | Para qué |
|---|---|---|
| `random_variable_list` | | Las entradas del modelo que pueden ser variables aleatorias, con su clave y su valor, y las ya definidas. |
| `random_variable_set` | | Hacer aleatoria una entrada o cambiarla: distribución, desviación, rango, correlación. La media es siempre el valor del modelo. |
| `random_variable_delete` | | Quitar una variable; las correlaciones que apuntaban a ella se limpian. |
| `statistics_run` | | *Compute Statistics* en segundo plano: el determinista y luego el probabilístico (PF, índice de fiabilidad) o el de sensibilidad, con los coeficientes de diseño y la semilla del modelo. |
| `back_analysis_run` | | La fuerza horizontal de sostenimiento necesaria para un factor objetivo, sobre la búsqueda configurada. |
| `optimize_run` | | Optimizar la superficie crítica no circular de un resultado con los ajustes y la semilla del modelo; el resultado es uno NUEVO. |

Los tres cálculos pasan por la misma puerta que `analysis_run`: sin norma de diseño dan exactamente lo mismo que antes, y con norma, el modelo factorizado.

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
| `results_query` | | Lo que pregunta la ventana de interpretación (desde v0.1.201): códigos de error (−120 tracción, −112 m-alfa, −111 sin convergencia, −101 otros) y censo de superficies rechazadas, datos brutos, superficies que pasan por un punto (medido sobre la superficie que se calculó, no sobre el círculo entero), mínimo por centro, factor a lo largo del talud, dovelas con los números del método, filtros; y de un resultado de estadística, histograma, convergencia, muestras con su índice y sensibilidad. |
| `surface_evaluate` | | El factor de seguridad de UNA superficie dada (círculo, tres puntos o polilínea), sin búsqueda. |

## Vista, historia y Python

| Herramienta | C | Para qué |
|---|---|---|
| `model_render` | C | Imagen PNG del modelo, con las superficies críticas de un resultado o con los contornos del campo de agua (`field`) y su superficie libre; con `--attach`, `source="window"` captura el lienzo real de la ventana. |
| `project_history` | | Deshacer, rehacer o listar las ediciones. |
| `python_exec` | C | Python contra el modelo, para lo que aún no tiene herramienta. Ver [seguridad.md](seguridad.md). |

## Recursos

| URI | Contenido |
|---|---|
| `ogr://guide` | La guía de modelado completa que lee el agente. |
| `ogr://catalog/{kind}` | `catalog(kind)` como recurso. |
