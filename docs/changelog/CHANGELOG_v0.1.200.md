# OGR Slip2D v0.1.200

**F3a: el agente maneja el agua subterránea por elementos finitos, y cada
modelo de permeabilidad recibe la succión en la unidad de su propia
definición.**

- Once operaciones nuevas cubren las nueve acciones del menú de agua que
  quedaban pendientes: propiedades hidráulicas, malla, condiciones de
  contorno, transitorio, rejilla de presiones, cálculo, interpretación y
  barrido de desembalse. El agente alcanza 108 de las 136 acciones de la
  ventana (99 en v0.1.199); quedan 5, todas de F3b.
- Las unidades hidráulicas se corrigen por modelo, como decidió el
  propietario (2026-09-24). Cambian 4 modelos del banco, que se miden
  abajo.
- Por el camino aparecieron nueve defectos más: condiciones de etapa que
  sobrevivían a una malla nueva, un barrido de desembalse que ignoraba la
  norma de diseño, una nota del agente que afirmaba algo falso… Van
  detallados en §3.

---

## 1. Las unidades hidráulicas, por modelo

### Qué estaba mal

El solver evalúa k_r en la altura de presión P de cada elemento, en metros.
Las funciones de permeabilidad se documentaban todas en kPa y el solver les
pasaba a todas −P **en metros**:

- **van Genuchten (1980) y Gardner (1958)** se escriben en altura de
  succión, h en m. Para ellos el solver acertaba; lo que estaba mal era la
  etiqueta «kPa».
- **Brooks & Corey (1964), Fredlund & Xing (1994), Simple y la curva de
  usuario** se escriben en succión matricial, s en kPa. Recibían un factor
  γw (≈ 9,81) menos de succión del que tenían.

### El arreglo

- `HydraulicProperties.kr_at_pressure_head(P, γw)` es la única puerta del
  solver (`_element_kr`). Convierte s = −P·γw para los cuatro modelos en
  kPa y deja h = −P para los dos en metros.
- `permeability_models.SUCTION_UNIT` declara la unidad de cada modelo.
- El γw es el del solver, así que un proyecto en unidades imperiales usa
  62,4.

### La biblioteca de van Genuchten estaba en 1/cm

Sus α son los de la tabla de Carsel & Parrish (1988), que los da en
**1/cm** (arena 0,145 1/cm). Se guardaban tal cual, etiquetados como 1/kPa,
y el solver los leía como 1/m: una «arena» cien veces más retentiva de lo
que es.

- Pasan a 1/m (×100): arena 14,5; franco arenoso 7,5; limo 1,6; arcilla
  0,8…
- El α por defecto de un material nuevo pasa de 0,036 a 3,6 1/m: es el
  franco de la misma tabla (n = 1,56), en la unidad en que se evalúa.
- **El cargador no cambia.** `HydraulicProperties.from_dict` sigue leyendo
  0,036 cuando falta la clave, porque un archivo sin ella se escribió
  cuando ese era el defecto. Los modelos guardados llevan su α escrito y no
  se mueven.
- `water_content` (la curva de retención del transitorio, van Genuchten
  para todos los modelos) decía «succión matricial». Evalúa altura en
  metros, y lo dice ahora.

Esta parte va más allá de lo planeado. El plan decía que en van Genuchten y
Gardner «cambian las etiquetas y los números no», y eso sigue siendo cierto
para todo modelo guardado. Lo que cambia es el valor que la biblioteca
propone y el defecto de un material nuevo, que estaban en la unidad
equivocada.

### La interfaz

- Cada parámetro lleva su unidad en el diálogo: «Presión de burbujeo
  (kPa)», «A (kPa)», «a (1/m^n)», «alfa (1/m)».
- El eje de la gráfica dice «Altura de succión (m)» o «Succión matricial
  (kPa)» según el modelo.

### Medido: los 4 modelos del banco que cambian

A/B en el mismo proceso, sin escribir en el banco. De los 265 modelos vivos
cambian 4, todos del manual 05: tres con *Simple* y uno con curva de
usuario. van Genuchten y Gardner no se mueven, incluido el 102, el único con
elementos finitos del banco de taludes.

| Problema | Magnitud | Antes | Ahora | Slide | Analítica |
|---|---|---|---|---|---|
| 05-001, flujo entre dos ríos con lluvia (*Simple*) | x_a (m) | 4,152 | 4,227 | 4,06 | 3,98 |
| 05-004, presa con dren de pie (*Simple*) | y1 (m) | 0,01009 | 0,01009 | 0,442 | 0,48 |
| 05-005, flujo no saturado tras un terraplén (*Simple*) | presiones | — | +0,03 a +0,07 m | — | — |
| 05-014, columna no saturada (curva de usuario) | ver abajo | | | | |

- **05-001 se aleja** de las dos referencias con la unidad correcta:
  +6,2 % sobre la analítica, cuando antes era +4,3 %. No lo corrige esta
  versión. Deja una pregunta abierta sobre el modelo *Simple*: sus escalas
  de succión (`_SIMPLE_PARAMS`, 100 kPa para el suelo general) son una
  lectura cualitativa de la documentación, no una fórmula con fuente.
- **05-004 no cambia**, y sigue sin formar superficie libre (0,01 frente a
  0,48). Es una anomalía anterior, la misma de siempre.
- **05-014 muestra que el banco construyó su curva en metros.** Con el
  código nuevo da 0,23467. Con la curva pasada a kPa da **0,84136 frente a
  0,84143 de la analítica** (−0,008 %). El `construir_modelo.py` de ese
  problema tiene que convertir su tabla a kPa.
  - No se ha tocado: el banco está fuera del repositorio.

### Lo que no se ha comprobado

La forma funcional de Fredlund-Xing que usa el código,
1/[ln(e + (s/a)^b)]^c, es la curva de retención de Fredlund & Xing (1994)
con C(ψ) = 1, usada como k_r. Esta versión solo comprueba la unidad, no la
forma, y no se ha contrastado con una fuente. Los valores de Gardner de la
biblioteca tampoco citan unidad.

## 2. Movido al núcleo, y la interfaz lo llama

Una regla que imponía la interfaz pasa al núcleo, y el agente y la interfaz
preguntan lo mismo:

- **La malla** — `rules.set_fem_mesh` y `reset_fem_mesh`. Al cambiar la
  malla se borra lo que va por número de nodo (§3.1) y la función devuelve
  qué borró.
- **Las condiciones de contorno** — en `bc_targets`:
  - `boundary_sides`, los cuatro lados con nombre;
  - `assign_to_nodes` y `assign_side`;
  - `needs_value` y `allows_seepage_face`, que el diálogo tenía copiados;
  - `nodes_along`, los nodos del contorno sobre una polilínea (para quien
    conoce coordenadas y no números de nodo);
  - `fits_mesh`;
  - el embalse del diálogo pasa por el `apply_reservoir` que ya existía.
- **El transitorio** — las comprobaciones de etapas, en
  `GroundwaterSettings.set_transient`: todo o nada, y los mensajes pasan
  por `tr()` en el diálogo.
- **La rejilla de presiones** — `parse_grid_csv_text`.
- **El barrido de desembalse** — `analysis_runner.run_configured_drawdown_sweep`,
  por la misma puerta que `run_analysis`. También se trae la condición de
  la interfaz: sin desembalse rápido activo, no hay barrido.
- **La interpretación de agua** — `transient_stability.groundwater_query_solver`
  construye el solver cuando falta (§3.4).
- **Las propiedades hidráulicas** — `HydraulicProperties.problems()`, y
  `MODEL_FIELDS` / `COMMON_FIELDS` con los parámetros que lee cada modelo.
- **Qué materiales usa un nivel freático** —
  `water_surfaces.materials_using_surface`, con la respuesta del motor
  (§3.7).

## 3. Lo que se encontró

### 3.1 Una malla nueva dejaba las condiciones de las etapas en nodos ajenos

Las condiciones de contorno van por número de nodo. `set_fem_mesh`, y antes
la ventana, borraban las condiciones actuales al cambiar de malla. **No
borraban las de cada etapa del transitorio ni las del estado inicial**, que
van por número de nodo igual.

Medido en el talud de demostración:

- un embalse de etapa en la cara izquierda: 8 nodos de carga total en
  x = 0;
- se regenera la malla, de 300 a 600 elementos;
- esos 8 nodos quedan en la **coronación** (y = 25), y el transitorio los
  habría usado en silencio.

Ahora se borran con la malla. Las etapas conservan tiempo, etiqueta y
*Calculate SF*, y sin condiciones propias usan las actuales, como siempre.
La interfaz dice en la barra de estado qué se descartó. No mueve ningún
número guardado: un proyecto guardado conserva su malla.

### 3.2 El barrido de desembalse ignoraba la norma de diseño

El barrido de la interfaz buscaba sobre el proyecto **sin factorizar**:

- sin la copia con coeficientes;
- sin `check_analysis_settings`;
- sin los avisos de ajustes.

Así, con una norma activa, el barrido y un *Compute* contestaban dos
modelos distintos. Medido en Morgenstern (1963) con una rejilla gruesa, a
cinco cotas:

| Norma | Ruta vieja | Puerta única |
|---|---|---|
| desactivada | 2,6184 · 1,6799 · 1,3042 · 1,2245 · 1,2245 | **idéntica** |
| EC7 DA1-C2 | 2,6184 · … · 1,2245 | 2,0947 · 1,3436 · 1,0432 · 0,9803 · 0,9803 |

Con la norma activa, la interfaz daba **1,2245**, un «cumple», donde el
factor de sobrediseño es **0,9803**, un «no cumple». Sin norma no cambia
nada. El barrido no guarda resultados en el proyecto, así que ningún
número guardado se mueve.

### 3.3 Cancelar no cancelaba

- **Condiciones de contorno.** `_seepage_bcs()` devolvía el objeto vivo del
  proyecto: el diálogo lo editaba en su sitio y Cancelar no deshacía nada.
  Además, abrir el diálogo ya escribía las condiciones por defecto. Ahora
  el diálogo trabaja sobre una copia y la ventana guarda lo aceptado.
- **Capturar como estado inicial** escribía los ajustes al instante y
  sobrevivía a Cancelar. Ahora espera a Aceptar.
- **Borrar una etapa** dejaba sus condiciones pegadas a la siguiente, porque
  van por fila y las filas de debajo suben. Ahora se reindexan.

### 3.4 Tras reabrir un proyecto, la interpretación de agua enmudecía

La superficie libre y el caudal por una sección son métodos del solver, y
la ventana solo tenía el del último cálculo (`project._gw_solver`), que no
se guarda. Al reabrir un proyecto no dibujaba superficie libre y la sección
de caudal no hacía nada, sin decir nada. Las dos consultas solo leen la
malla y el campo, así que un solver construido sobre la malla del proyecto
contesta lo mismo. Comprobado: la superficie libre coincide a 10⁻⁶ m y el
caudal a 10⁻⁶ relativo (el archivo guarda nueve cifras por carga).

### 3.5 Las etiquetas de las etapas no llegaban a ningún sitio

El solver transitorio guardaba el tiempo y *Calculate SF* de cada etapa en
el resultado, pero **no su etiqueta**. La ventana de interpretación la
buscaba allí y nunca la encontraba. Ahora se guarda.

### 3.6 Asignar infiltración dos veces la duplicaba

Cada asignación añadía tramos sin quitar los que ya tenía la misma arista.
Ahora una arista con infiltración se sustituye.

### 3.7 Una nota del agente afirmaba algo falso

`project_validate` y `boundary_add` decían que un nivel freático «no está
asignado a ningún material y no produce presión intersticial» cuando ningún
material lo nombraba en `water_surface_id`.

Pero el motor (`resolve_water_surface`) da a un material con presión «nivel
freático» y sin superficie propia **el primer nivel freático del modelo**.
En el modelo de Morgenstern la nota lo negaba, y el factor de seguridad sí
incluía la presión. Ahora la nota pregunta al motor.

### 3.8 `results_get` sobre un resultado que no es de análisis

Contestaba «método desconocido» con una lista vacía. Ahora dice qué vistas
tiene ese resultado y remite a `groundwater_results`.

### 3.9 Comentarios obsoletos

En `Project`, el campo de filtración y los resultados del transitorio
seguían diciendo «no se serializa». Se guardan desde v0.1.78.

## 4. Las operaciones nuevas (toolset `groundwater`)

| Operación | Qué hace |
|---|---|
| `hydraulic_set` | Todas las propiedades de `HydraulicProperties`, también las que la interfaz no expone, y la biblioteca de cada modelo. Un parámetro de otro modelo se rechaza (regla 7) con la pista de cambiar el modelo en la misma llamada. |
| `mesh_generate` / `mesh_reset` | Por `set_fem_mesh`; dicen qué se borró y cuántos nodos tiene cada lado. |
| `seepage_bc_set` | Una condición en un lado, en nodos, a lo largo de una polilínea del contorno, o un embalse. El valor solo se admite donde se lee, igual que la marca de cara de filtración. |
| `seepage_bc_clear` | Las condiciones por defecto. Avisa de que no prescriben ninguna carga. |
| `transient_set` | Etapas con tiempo, *Calculate SF*, etiqueta y condiciones propias. Una etapa puede tomar las actuales, las de por defecto o esas mismas más una lista de asignaciones con el vocabulario de `seepage_bc_set`. También el estado inicial y las opciones. |
| `water_grid_set` / `water_grid_delete` | Puntos o un CSV leído como en la interfaz. Avisa cuando la rejilla no se leería: el método no es de rejilla, TPS con más de 300 puntos pasa a IDW… |
| `groundwater_run` | Trabajo en segundo plano: permanente, o el transitorio con el factor de seguridad de las etapas marcadas. |
| `groundwater_results` | Resumen, valores en un punto (H, P, u, velocidad, k_r), caudal por una sección con su convenio de signo, superficie libre, etapas y CSV de nodos. Lee el campo del modelo o uno guardado (`result_id`). |
| `drawdown_sweep_run` | Trabajo en segundo plano, por la puerta única. |

**`groundwater_run`, en detalle:**

- Se niega sin malla y sin condiciones: las de por defecto no prescriben
  ninguna carga y el problema permanente sería singular.
- También se niega con condiciones que nombran nodos que la malla no tiene.
- Al terminar, **el campo se escribe de vuelta en el modelo** en un paso de
  deshacer (atributos ligeros y pesados), que es lo que hace *Compute
  Groundwater* en la interfaz.
- Solo lo escribe si el modelo no cambió mientras tanto. Si cambió, no
  escribe y lo dice; el resultado guardado sigue legible por `result_id`.
- La huella del resultado escrito pasa a ser la del modelo con el campo,
  así que no sale como obsoleto. Los análisis anteriores sí, porque sus
  presiones ya no son las del modelo.

**Otros cambios del agente:**

- `model_render` gana `field` (carga total, carga de presión o presión
  intersticial) con la superficie libre, y `stage`.
- `material_set` edita ya la envolvente de desembalse
  (`drawdown_envelope`), que esperaba a F3. Dice cuándo nada la leería:
  solo la leen los métodos multietapa con `undrained_behaviour`.
- `hydraulic` remite a `hydraulic_set`.
- **El trabajador** despacha por tipo (`analysis`, `groundwater`,
  `drawdown_sweep`). `_job_answer` guarda el resultado según su tipo, y
  hace una sola vez lo que corresponde a ese tipo; la escritura de vuelta
  no se repite en cada `job_get`.
- **MCP:** 67 herramientas en `full` (56 antes); `compact` sigue con 14.
  `docs/mcp/` y la guía del agente, al día. Esa documentación decía además
  que una lente se rechazaba, lo que dejó de ser cierto en v0.1.197.

## 5. Reportado, sin corregir

- **Dos controles para lo mismo en la rejilla de presiones.**
  - El método de agua subterránea `grid_total_head` / `grid_pressure_head`
    / `grid_pore_pressure` solo activa la rejilla: el tipo de valor que se
    usa es el de la propia rejilla (`value_type`).
  - Con el método diciendo «carga total» y la rejilla «presión», manda la
    rejilla, y la mitad del método no se lee (regla 7).
  - `water_grid_set` lo avisa. Decidir cuál manda es del propietario.
- **05-001 se aleja con la unidad correcta** (§1): pregunta abierta sobre el
  modelo *Simple*.
- **El solver transitorio fija la relajación en 0,5.** Con tolerancia 10⁻⁹
  y 30 iteraciones, un caso lineal no converge («some time steps did not
  converge»). Con la tolerancia por defecto, 10⁻⁵, sí. Lo encontró el test
  erfc al pasar por la API, que no puede elegir la relajación.
- **Generar la malla en la interfaz no es un paso de deshacer.** Por el
  agente sí lo es.

## 6. Tests

`tests/test_groundwater_ops_v1200.py`, con 48 casos:

- **las unidades por modelo, con las formas cerradas de sus fuentes, por
  `_element_kr`**:
  - Brooks & Corey en kPa;
  - van Genuchten–Mualem y Gardner en metros;
  - la curva de usuario en kPa: 10^−0,5 en el punto medio, donde con metros
    daba 0,889;
  - la identidad de unidad de Fredlund-Xing y *Simple*;
  - el γw del solver;
- la biblioteca = 100 × Carsel & Parrish (1988);
- Darcy 1-D por la API: cargas exactas a 10⁻⁶ m, caudal a 10⁻⁶ relativo y
  el signo de la sección;
- capas en paralelo (media aritmética) y en serie (media armónica, con la
  carga en la interfaz);
- la respuesta erfc del acuífero confinado a 200 s y 1000 s (< 1 % de ΔH),
  y el permanente a tiempo largo (< 10⁻³ ΔH);
- el caudal de Charnyi en una presa rectangular (< 5 %), su superficie
  libre y su caudal tras guardar y reabrir;
- Morgenstern (1963) por `drawdown_sweep_run`: 1,20 ± 6 %, la mitad del
  desembalse más segura que el total, los mismos números que la puerta en
  proceso, y la norma de diseño que mueve el número (sin ella, idéntico al
  camino viejo);
- la escritura de vuelta:
  - un paso de deshacer exacto;
  - no se repite en cada `job_get`;
  - un modelo editado mientras tanto conserva su campo y el resultado
    guardado sigue legible;
- la malla nueva borra las condiciones de etapa y de estado inicial, y el
  deshacer las devuelve;
- cada rechazo deja el modelo intacto;
- la nota del nivel freático pregunta al motor;
- la interfaz:
  - el diálogo de condiciones trabaja sobre una copia;
  - la captura inicial espera a Aceptar;
  - borrar una etapa no mueve las condiciones de las demás;
  - el solver de interpretación existe tras reabrir.

**Tests existentes que se ajustaron:**

- `test_api_undo_v1194.py`: ejemplos de deshacer para las nueve operaciones
  nuevas que editan, `groundwater_run` incluido (su paso es el campo escrito
  de vuelta).
- `test_mcp_server_v1195.py`: `wait_seconds` lo consumen también las dos
  herramientas de trabajo nuevas.
- `test_i18n_coverage_v141.py`:
  - avisos sin envolver, de 67 a 64: los tres del diálogo de etapas pasan
    por `tr()` desde el núcleo;
  - «A (kPa):» y «a (1/m^n):» a la lista de notación idéntica, junto a
    «A:» y «a:».

**Verificación:** la suite entera, sin filtros, pasa 4485 de 4485. La tanda
dirigida de agua subterránea (16 archivos) pasó antes 396 de 396.

## Pendiente

F3b (v0.1.201): estadística, retroanálisis, optimización e interpretación
de superficies. Con ella, las 5 acciones pendientes llegan a 0.
