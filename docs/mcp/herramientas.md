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
| `boundary_add` | | Un contorno: exterior, de material, nivel freático, piezométrica, desembalse, grieta de tracción, objeto de Block Search, capa débil o superficie anisótropa. Un contorno de material **cerrado** (`closed=true`) es una lente: su propia región y un hueco en la de alrededor (desde v0.1.197). Un objeto de Block Search lleva su **tipo** en `block_object` (desde v0.1.232): `window`, `line`, `point` o `polyline`; la polilínea da a cada superficie dos puntos **y el tramo entre ellos**, y acepta `left_point`/`right_point` (`any`, `segment`, `end_point`). Dos puntos abiertos sin tipo son una línea, no una polilínea. Desde v0.1.233 lleva también su `group_id` (entero, 0 por defecto), que solo se lee con `search.block_multiple_groups` activado: entonces cada identificador se busca por separado, el número de superficies se reparte entre los grupos y las polilíneas de grupos distintos pueden solaparse en x. |
| `boundary_edit` | | Editar o borrar un contorno: vértices, traslación, tipo, nombre; `op=block_object` cambia el tipo de un objeto de Block Search. |
| `material_set` | | Crear o modificar un material, también su envolvente de desembalse rápido (`drawdown_envelope`, desde v0.1.200). Las propiedades hidráulicas van por `hydraulic_set`. Un tramo de Generalized Anisotropic toma un material del modelo por su nombre (`"material": "Arcilla"`, desde v0.1.228), y el análisis usa la resistencia de ese material tal como esté al calcular. |
| `material_delete` | | Borrar un material (se niega mientras lo usen regiones, capas débiles o tramos de un Generalized Anisotropic, salvo con `reassign_to` o `force`). |
| `material_assign` | | Asignar un material a la región que contiene un punto. |
| `external_reshape` | | Expandir o encoger el contorno exterior: desplazamiento paralelo, o una polilínea de relleno o excavación con los dos extremos sobre él. |
| `slope_angle_change` | | Cambiar el ángulo global de la cara del talud entre dos vértices del exterior (pie y coronación): solo se mueve la cara, proyectando en horizontal (por defecto), en vertical o girando; `keep_benches` conserva el ancho de las bermas. Los contornos que acaban en la cara la siguen; soportes y cargas no se mueven (se avisa). |
| `geometry_cleanup` | | Informe de vértices duplicados, autointersecciones y cruces entre contornos; con `apply`, los corrige. |

`boundary_edit` también copia, escala, rota y simplifica.

## Cargas (`loads`)

| Herramienta | C | Para qué |
|---|---|---|
| `load_set` | | Añadir o cambiar una carga repartida (kPa entre dos puntos) o lineal (kN/m en un punto), y su acción para la norma de diseño (`action`: permanente o variable). |
| `load_delete` | | Borrar cargas. |
| `seismic_set` | | Carga sísmica pseudoestática: kh, kv y si se aplica. Las dos fuerzas sobre el peso estático del SUELO (las cargas y el agua embalsada no llevan fuerza sísmica); kv positivo hacia abajo (el suelo pesa W·(1 + kv)); kh ≥ 0, una magnitud que actúa siempre en el sentido de la rotura; y \|k\| < 1. |
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
| `user_surface_add` | | Una superficie propia que se analiza junto a la búsqueda: un círculo con el tipo de superficie circular o, desde v0.1.427, una polilínea (`{'type': 'polyline', 'points': ...}`, con la x avanzando de un extremo al otro en cualquier sentido; se guarda de izquierda a derecha) con el no circular. Los extremos de la polilínea se llevan al contorno exterior al analizarla, como en `surface_evaluate`. |
| `user_surface_delete` | | Borrar una por id (círculo o polilínea), o todas. |

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
| `report_generate` | | Informe PDF de un análisis, con una figura por método (`figures`): su superficie crítica, la capa de anotaciones (`annotations`) y, con una rejilla de centros, las isolíneas en cada centro del número que da el cálculo (el factor mínimo; en un cálculo de Ky o de Newmark, desde v0.1.450, el Ky mínimo o el desplazamiento de Newmark máximo); encuadrada en el modelo o en el modelo y el área de búsqueda (`framing`). |
| `properties_import` | | Copiar materiales o tipos de soporte de otro `.ogr`. Un tramo de Generalized Anisotropic que tomaba un material se enlaza con su copia importada o con el material del mismo nombre; si no hay ninguno, conserva su resistencia sin enlace y lo dice una nota. |

## Agua subterránea (`groundwater`, desde v0.1.200)

| Herramienta | C | Para qué |
|---|---|---|
| `hydraulic_set` | | Propiedades hidráulicas de un material: permeabilidad saturada y anisotropía, modelo de la zona no saturada (con su biblioteca de suelos), contenidos de agua y almacenamiento. Un parámetro de otro modelo se rechaza. |
| `mesh_generate` | | Malla de elementos finitos. Sustituye a la anterior y borra sus condiciones de contorno y sus campos, también las de las etapas del transitorio: van por número de nodo. |
| `mesh_reset` | | Quitar la malla y todo lo calculado sobre ella. |
| `seepage_bc_set` | | Una condición de contorno en un lado (`left`, `right`, `bottom`, `ground`), en nodos, a lo largo de una polilínea del contorno, o un embalse a una cota. |
| `seepage_bc_clear` | | Volver a las condiciones por defecto (desconocida en la superficie, sin flujo en el resto), que no prescriben ninguna carga. |
| `transient_set` | | El transitorio por etapas: tiempos, condiciones de cada etapa, *Calculate SF* y estado inicial. Se puede guardar sin etapas mientras se prepara, pero `groundwater_run` no lo calcula hasta que tenga una. |
| `water_grid_set` | | Rejilla de presiones de agua (puntos o un CSV) y sus opciones de interpolación. |
| `water_grid_delete` | | Quitarla. |
| `groundwater_run` | | Resolver el agua (permanente, o las etapas del transitorio con su factor de seguridad) en segundo plano. El campo se escribe de vuelta en el modelo en un paso de deshacer, salvo que el modelo haya cambiado mientras tanto. |
| `groundwater_results` | | Leer el campo: resumen, valores en un punto, caudal por una sección, superficie libre, etapas con sus factores, o todos los nodos en CSV. `stage` es el número de etapa (desde 0) o `"initial"`, el estado del que partió el transitorio (t = 0). Funciona también tras reabrir el proyecto. |
| `drawdown_sweep_run` | | Desembalse rápido a varias cotas del embalse, porque el desembalse total no siempre es el peor; por la misma puerta que un análisis (coeficientes de diseño y comprobaciones). |

Unidades: cargas hidráulicas en m y presión intersticial en kPa; permeabilidad, infiltración y caudal nodal en una misma unidad coherente (m/s). Desde v0.1.200 cada modelo de permeabilidad toma su succión en la unidad de su propia definición: van Genuchten y Gardner en altura (α en 1/m), Brooks-Corey, Fredlund-Xing, Simple y la curva de usuario en succión matricial (kPa).

## Estadística, retroanálisis y optimización (`statistics`, desde v0.1.201)

| Herramienta | C | Para qué |
|---|---|---|
| `random_variable_list` | | Las entradas del modelo que pueden ser variables aleatorias, con su clave y su valor, y las ya definidas. Una variable hidráulica (`hydraulic:…`) no llega a ningún factor de seguridad, porque ningún análisis estadístico vuelve a resolver la filtración en cada muestra: si todas lo son, `statistics_run` se niega (`stat.vars_hydraulic_only`); mezclada con otras, avisa (`stat.vars_hydraulic`) y muestrea las demás (desde v0.1.423, D372). |
| `random_variable_set` | | Hacer aleatoria una entrada o cambiarla: distribución, desviación, rango, correlación. La media es siempre el valor del modelo. |
| `random_variable_delete` | | Quitar una variable; las correlaciones que apuntaban a ella se limpian. |
| `statistics_run` | | *Compute Statistics* en segundo plano: el determinista y luego el probabilístico (PF, índice de fiabilidad) o el de sensibilidad, con los coeficientes de diseño y la semilla del modelo. Cada método trae `surface_key`, la identidad de la superficie sobre la que se muestreó (tipo y geometría al último dígito; `null` en Overall Slope, donde cada muestra busca de nuevo). `switch_lines` dice cuáles de `note_lines` cuentan muestras que contestaron por otra masa o por otro caso de capa débil. |
| `back_analysis_run` | | La fuerza horizontal de sostenimiento necesaria para un factor objetivo, sobre las superficies admisibles de la corrida configurada, también las del usuario (desde v0.1.428), que están por debajo del objetivo y que la fuerza toca (desde v0.1.441). `notes` dice si la que gobierna es del usuario, si una inadmisible habría necesitado más fuerza y si Bishop dejó fuera superficies que no son círculos; `critical_surface` trae la geometría de la que gobierna. Desde v0.1.441 no se analizan las superficies que ya alcanzan el objetivo (`surfaces_above_target`) ni las que están por debajo y cuya masa no toca la fuerza (`surfaces_untouched`, con su nota: la fuerza no hace nada por ellas); `surfaces` cuenta solo las analizadas. `elevation` es una cota de la cara del talud: con la de por defecto, 0, lo normal es que la fuerza no toque ninguna masa, y entonces no hay fuerza (`required_force` nulo) y `notes.error` dice entre qué cotas llegan las masas al terreno. |
| `optimize_run` | | Optimizar la superficie crítica no circular de un resultado con los ajustes y la semilla del modelo; el resultado es uno NUEVO. La técnica es la del modelo (`search.optimize_technique`): `monte_carlo`, el paseo aleatorio, por defecto, o `surface_altering` (desde v0.1.260), que mueve los extremos por el terreno y rehace la superficie entera manteniéndola convexa, y no usa la semilla. El resumen dice cuál corrió (`technique`). |

Los tres cálculos pasan por la misma puerta que `analysis_run`: sin norma de diseño dan exactamente lo mismo que antes, y con norma, el modelo factorizado.

## Ajustes (`settings`)

| Herramienta | C | Para qué |
|---|---|---|
| `settings_get` | | Todos los ajustes con su valor, tipo y opciones. |
| `settings_set` | | Cualquier ajuste por ruta (`search.search_method`); todo o nada. Devuelve en `warnings` lo que el análisis no puede honrar tal como está escrito. Desde v0.1.256 eso incluye los ángulos de proyección de la Block Search (`search.block_*_angle_deg`): un par escrito al revés se lee como el arco entre los dos que apunta a su lado (45 → −45 a la derecha es −45..45; 315 es −45), y un ángulo fuera de los límites de la referencia (izquierda 95–175, hasta 265 si el talud mira a la izquierda; derecha 5–85, desde −85 si mira a la derecha) se usa tal cual. Los dos se avisan; ninguno se rechaza. |
| `analysis_configure` | C | Los ajustes de análisis más comunes en una llamada: métodos, tipo de superficie, búsqueda, dovelas, grid, dirección de rotura, norma. |

## Análisis (`analysis`)

| Herramienta | C | Para qué |
|---|---|---|
| `analysis_run` | C | Lanza el análisis en segundo plano; devuelve el resultado o un `job_id`. |
| `job_get` | C | Estado y progreso de un trabajo; su resultado al terminar. |
| `job_cancel` | C | Detiene un análisis y todos los procesos que arrancó. |
| `job_list` | | Los trabajos de la sesión. |
| `results_get` | C | Leer un resultado: resumen, superficie crítica con dovelas, mejores superficies, mínimos, avisos. |
| `results_query` | | Lo que pregunta la ventana de interpretación (desde v0.1.201): códigos de error (−120 tracción, −112 m-alfa, −111 sin convergencia, −103 círculo que sale del contorno exterior entre sus cortes con el terreno, desde v0.1.445, −101 otros) y censo de superficies rechazadas, datos brutos, superficies que pasan por un punto (medido sobre la superficie que se calculó, no sobre el círculo entero), mínimo por centro, factor a lo largo del talud, dovelas con los números del método, filtros. Desde v0.1.442 `filter` por factor y `raw_data` incluyen las superficies que dibujó el usuario (`filter`, las que ninguna comprobación rechazó; `raw_data`, todas, en sus últimas filas y con una séptima columna `user_defined` con `1` o `0`), y cada listado marca las suyas con `surface.user_defined` a `true`: esos dos, `surfaces_through_point`, `minimum_per_centre` y `slices`, que ya las incluían, el `critical` del resumen de `analysis_run` y el `critical` y el `top` de `results_get`. El censo (`error_codes`, `invalid_summary` y `filter` con `code`) sigue siendo solo de la búsqueda. El −103 y parte del −101 se cuentan antes de dovelar, sin superficie: `filter` con ese código no lista ninguna de ellas. Y de un resultado de estadística, histograma, convergencia, muestras con su índice y sensibilidad. |
| `surface_evaluate` | | El factor de seguridad de UNA superficie dada (círculo, tres puntos o polilínea), sin búsqueda. Desde v0.1.258, el primer y el último vértice de una polilínea que no estén sobre el contorno exterior se llevan al punto más próximo de él, como hace la referencia con una superficie introducida a mano, y `notes` lo dice (punto pedido, punto usado y distancia). Un método sin resultado dice en `notes` por qué: por ejemplo, un extremo bajo el terreno (el −101 de la referencia) o un extremo en el aire, en vez de «does not cut the model». Desde v0.1.446, si no se registró motivo y hay filtros activos (Área, Profundidad o Cota mínimas: los Límites del talud dicen siempre su motivo), `notes` los nombra como lo hace la corrida, con el valor por defecto del Área mínima dicho como tal; el techo del ángulo de base de una capa débil dice su motivo; y `notes` lleva también lo que la evaluación dejó dicho, como en una corrida (el techo con sus grados, el tope de casos de capa débil), haya o no resultado. Desde v0.1.427 la polilínea tiene que avanzar en x de un extremo al otro, en cualquier sentido, con la misma regla que `user_surface_add`: una que retrocede en x o tiene un tramo vertical se rechaza (`E_INVALID_ARGUMENT`), cuando antes se tasaba ordenada por x, que es otra superficie. |

## Vista, historia y Python

| Herramienta | C | Para qué |
|---|---|---|
| `model_render` | C | Imagen PNG del modelo, con las superficies críticas de un resultado o con los contornos del campo de agua (`field`, de una etapa o del estado inicial con `stage`) y su superficie libre, y la capa de anotaciones (`annotations`); con el programa abierto, `source="window"` captura el lienzo real de la ventana. |
| `project_history` | | Deshacer, rehacer o listar las ediciones. |
| `python_exec` | C | Python contra el modelo, para lo que aún no tiene herramienta. Ver [seguridad.md](seguridad.md). Desde v0.1.383, cada script deja caducos los índices con que se localiza un punto en las mallas, y desde v0.1.393 lo que un solucionador de filtración guarda de sus elementos, porque un script puede editar una malla en el sitio. Si un script edita una malla y vuelve a consultarla o a resolverla dentro de sí mismo, que llame antes a `forget_index()` de esa malla. |

## Recursos

| URI | Contenido |
|---|---|
| `ogr://guide` | La guía de modelado completa que lee el agente. |
| `ogr://catalog/{kind}` | `catalog(kind)` como recurso. |
