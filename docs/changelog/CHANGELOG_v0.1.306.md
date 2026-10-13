# OGR Slip2D v0.1.306

**Un transitorio sin etapas se puede guardar, y ya no se calcula en silencio
(D294).** Primera versión de la tanda P8f (el transitorio): 0.1.306 D294,
0.1.307 D295, 0.1.308 D311 y 0.1.309 D312.

## 0. Lo que se encontró

- **El rechazo no estaba en el diálogo, sino en el núcleo.** La prueba de la
  interfaz de 0.1.284 (H10) marcó el transitorio, pulsó «Capturar como estado
  inicial» y Aceptar respondió «Defina al menos una etapa o desactive el
  análisis transitorio.».
  - La comprobación vive en `GroundwaterSettings.set_transient` desde 0.1.200,
    compartida con el `transient_set` del agente.
  - El flujo natural no se podía seguir sin inventar una etapa provisional:
    capturar el estado inicial → cerrar → cambiar las condiciones en su
    diálogo, que no se abre con este abierto → volver y añadir la etapa.
- **La otra mitad, que no estaba en la ficha: el cálculo en silencio.** Un
  transitorio sin etapas ya se podía alcanzar por cuatro caminos:
  - el botón de radio de *Project Settings > Groundwater*;
  - `settings_set` con `groundwater.advanced_option = "transient"`;
  - un `.ogr`;
  - un script.

  Las tres puertas que calculan el agua tenían la misma guarda (`transient
  and transient_stages`) y caían a un PERMANENTE con las condiciones
  actuales. Ignoraban el estado inicial capturado y no decían nada:
  - la ventana: `_compute_groundwater`;
  - el núcleo: `solve_project_groundwater`;
  - el API: `groundwater_run` y su trabajador.

  El único aviso de «sin etapas» estaba en `run_transient_stability`, y
  ninguna puerta lo alcanzaba.
- **Qué guardaba el diálogo en cada salida** (leído y medido con el test
  nuevo sobre 0.1.305):
  - Aceptar sin etapas: nada, con un aviso modal;
  - Cancelar: nada;
  - desmarcado: las etapas y la captura.

  La captura se confirmaba con otro aviso modal, en inglés y sin `tr()`, que
  decía «stored» de algo que solo se guarda al Aceptar.
- **Qué hace la referencia** (tutoriales 18 y 19 de su ayuda; solo para
  entender el comportamiento):
  - el estado inicial no es una etapa, sino lo que da un «método» propio;
  - las etapas son los tiempos a los que se observa, todos positivos;
  - *Interpret* enseña primero el estado inicial y después las etapas;
  - el caso de cero etapas no está documentado.

  Nuestro solver ya lo trata así: `solve_transient([])` devuelve `[]`.
- **Por qué no calcular solo t = 0.** Era la alternativa. El estado inicial
  pasaría a ser el campo que lee la estabilidad (`seepage_result`), y la
  estabilidad pesa el agua embalsada con las condiciones ACTUALES
  (`ponded_water._fea_ponding_runs`). Es justo el caso de quien captura el
  estado inicial y DESPUÉS cambia las condiciones: el campo de un embalse con
  el peso de otro, lo que `with_stage_water` existe para evitar.
- **El banco no se mueve.** De los 19 166 `.ogr` del banco, ninguno tiene el
  transitorio activado. Sus transitorios (05-15 a 05-21 y el 02-102) viven en
  sus guiones, que llaman al solver o a la puerta con etapas.

## 1. Qué cambia

**Decisión de la propietaria (2026-10-13): el diálogo guarda; las puertas se
niegan y lo dicen.**

- **`set_transient` acepta el transitorio sin etapas.**
  - Siguen las demás comprobaciones: tiempos positivos y distintos,
    tolerancia, iteraciones y pasos.
  - La clave «Define at least one stage…» desaparece con su traducción.
- **`rules.transient_without_stages(project)`** con la clave
  `TRANSIENT_WITHOUT_STAGES`: «El análisis transitorio está activado y no
  tiene etapas: no hay nada que calcular. Añade una etapa en Agua subterránea
  > Agua subterránea transitoria, o desactiva el análisis transitorio.».
  Sigue el patrón de `mesh_mismatch` (D284).
- **Las tres puertas la preguntan:**
  - `solve_project_groundwater` lanza `AnalysisNotConfigured`;
  - *Calcular agua subterránea* lo dice en la barra de estado, traducido y no
    modal, y no deja paso de deshacer;
  - `groundwater_run` da `NotConfigured` antes de arrancar el trabajo.
- **El agente lo sabe antes:**
  - `transient_set` sin etapas acepta y lo dice en `notes`;
  - `project_validate` lo lleva en `model_notes`;
  - la descripción de `transient_set`, la guía del MCP y
    `docs/mcp/herramientas.md` lo cuentan.
- **El diálogo *Transient Groundwater*:**
  - una línea dice de qué estado inicial parte el transitorio: «las
    condiciones de contorno actuales (no se ha capturado ninguno)» o «las
    condiciones capturadas (N nodos, M segmentos)»;
  - **Borrar estado inicial** junto a esa línea. Aceptar escribe siempre lo
    que hay, así que borrar también se guarda, y Cancelar sigue sin escribir
    nada;
  - otra línea avisa, con el transitorio marcado y sin etapas: «Aún no hay
    etapas: Calcular agua subterránea se negará hasta que añadas una.»;
  - la captura deja de abrir un aviso modal;
  - sin malla, los dos botones de captura quedan en gris con su motivo, en
    lugar de dos avisos modales «No boundary conditions defined yet.»;
  - «Select a stage first.», las dos ayudas de captura y el aviso de
    exclusividad pasan por `tr()`, con castellano.
- **El presupuesto exacto de mensajes sin `tr()` baja de 16 a 12:** eran los
  cuatro avisos de este diálogo.

## 2. Tests

`tests/test_transient_no_stages_v1306.py`, 12 casos, sin nada modal
(`_no_modals()` convierte cualquier `QMessageBox` en un fallo):

- **el orden de trabajo de H10 por la ventana real:**
  - capturar el estado inicial y Aceptar sin etapas deja un paso
    «Transient groundwater», con el transitorio activo y el estado inicial
    capturado;
  - después se cambian las condiciones, se vuelve, se añade una etapa con
    «Capture current BCs» y se acepta;
  - el estado inicial sigue siendo el capturado y la etapa lleva las
    condiciones nuevas;
- **el diálogo:**
  - acepta sin etapas;
  - borrar se escribe al Aceptar, y Cancelar no escribe nada;
  - las dos líneas dicen lo que toca, también en castellano;
  - sin malla no hay captura ni aviso modal;
- **las tres puertas se niegan, lo dicen y no escriben nada:**
  - la ventana: la barra de estado, también en castellano, sin campo y sin
    paso;
  - el transitorio activado por el botón de radio de *Project Settings*
    (diálogo real);
  - el núcleo: `AnalysisNotConfigured` con la clave;
  - el API: `groundwater_run`, también con el transitorio activado por
    `settings_set`, y `project_validate` lo avisa antes;
- **control:** con una etapa calculan la ventana, el núcleo y el API, y
  `project_validate` no avisa.

**Tests antiguos que cambian, por la decisión:**
- `test_groundwater_ops_v1200::test_transient_checks_are_the_cores`:
  `stages=[]` sale de la lista de rechazos y pasa a «se acepta, con la
  nota»;
- `test_i18n_coverage_v141`: el presupuesto de mensajes, 16 → 12.

**Con el código de 0.1.305 fallan 10 de los 12 casos,** cada uno por la causa
exacta:
- el aviso modal de la captura;
- `transient_set` rechazando sin etapas;
- `groundwater_run` calculando sin etapas;
- las líneas y el botón que no existían.

Los dos que pasan son los controles con una etapa, que tienen que pasar en
los dos árboles.

Se corrió sobre una copia del árbol de 0.1.305 sin el buscador editable.
Primero se colgó: el aviso modal de 0.1.305 espera para siempre sin pantalla.
Por eso el test lleva `_no_modals()`.

## 3. Verificación

- **Suite entera:** 6034/6034, código de salida 0, a la primera (unos 52
  minutos).
- **Los tests vecinos**, antes de lanzarla: 416/416. Son transitorio,
  operaciones de agua, estado inicial, deshacer, i18n, ajustes del API y de
  proyecto, MCP, agua en la GUI, firma de malla y menús en gris.
- **Banco:** `d294()` en el `verificar_cierres.py` de la raíz, registrada en
  `COMPROBACIONES`: **CUBIERTO POR TEST**. Ciclo de cierre:
  - `verificar_cierres.py` entero: 48 comprobaciones, 0 bajadas;
  - instantánea `Evaluaciones/0.1.306` antes y después (`--forzar`);
  - `retirar_cerrados.py --escribir D294`;
  - poda de la lista P8 de `generar_prompts.py`, y D294 tachada en la fila P8;
  - `generar_prompts.py`: 44 prompts y 19 FALTA, todas de paquetes
    anteriores;
  - `auditoria_invariantes.py` en la raíz y en el 02, con 0 ERROR.

  En el mismo ciclo se abrieron D311 y D312 en P8, con su prompt largo. Salieron
  al planificar e investigar esta tanda y se resuelven en ella (0.1.308 y
  0.1.309).
- **Ningún número del motor se mueve:** un transitorio con etapas recorre el
  mismo código. Lo único que cambia de resultado es lo pedido: un transitorio
  sin etapas deja de calcular un permanente.

## 4. Pendiente

- **A mano:** el flujo de H10 en la ventana (capturar → Aceptar sin etapas →
  cambiar las condiciones → añadir la etapa) y las dos líneas del diálogo en
  castellano.
- **D293 (P8g):** la fila de botones del diálogo ya se cortaba en castellano.
  *Borrar estado inicial* va en su propia línea para no empeorarla.
