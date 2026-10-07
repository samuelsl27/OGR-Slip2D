# OGR Slip2D v0.1.270

**Un transitorio dice si el permanente del que arranca convergió (D268).**
Sin `initial_head`, `solve_transient` toma el estado inicial de un permanente
y solo comprobaba que hubiera cargas, no que hubiera convergido. Un estado
inicial no convergido, o con la cara de rezume sin asentar, se hacía
evolucionar en silencio, y todas las etapas salían «convergidas», sin nota ni
aviso. Ahora cada etapa lo dice, y el aviso llega a la barra de estado, a
`run_transient_stability` y a la API. Ninguna carga cambia.

## 0. Lo que se encontró

- **Bajar `converged` habría tenido un precio que el prompt no veía.**
  `SeepageResult.ok` exige `converged`. Una etapa marcada como no convergida
  pierde la superficie libre (`free_surface_points`), el caudal
  (`flux_through_segment`) y las consultas de punto de la API. En cambio, los
  factores de seguridad de esas etapas se siguen calculando: el equilibrio
  límite solo lee la presión intersticial. Se habrían publicado factores sobre
  campos que la interfaz se niega a enseñar.
- **Decisión de la propietaria: ANOTAR, sin bajar `converged`.** Las etapas
  convergieron desde donde arrancaron. Lo dudoso es el punto de partida, y eso
  es lo que se anota.
- **Una excepción que no es política, sino corrección.** Una etapa de
  duración nula anterior al primer paso **es** el campo del permanente, sin
  evolucionar. Salía con `converged = True` aunque ese campo no hubiera
  convergido. Ahora lleva el `converged` y las notas del permanente.
- **El aviso no puede ir en `warning`.** Esa clave es de la etapa, y la
  escribe la propia etapa cuando sus pasos no convergen, así que lo
  sobrescribiría. Va en una clave aparte.
- **La barra de estado se sobrescribía.** `_compute_transient` enseña los
  avisos del motor, pero `_compute_groundwater` los reemplaza enseguida con su
  resumen de etapas. Un aviso que solo estuviera en `outcome.warnings` no lo
  habría visto nadie, así que el resumen lo lleva también.
- **La API no exponía el aviso de una etapa.** `stage_rows` no llevaba
  `warning`.

## 1. Qué cambia

### Motor (`ogr_fem2d/solvers/seepage.py`, `solve_transient`)

Cuando el estado inicial sale del permanente, todas las etapas (las de
duración nula, las que avanzan y la de «no time step computed») llevan:
- `notes["initial_state_converged"]`, verdadero o falso;
- `notes["initial_state_warning"]` si no convergió, con la razón del propio
  permanente: su `warning` o su `error`.

Además:
- `converged` no cambia, salvo en las etapas de duración nula previas al
  primer paso, que toman el del permanente y sus notas (historia,
  `unsettled_nodes`, etc.).
- Un `initial_head` dado no se juzga: lo da el usuario, y no lleva nota.

### Quién lo ve

- **`run_transient_stability`** añade a sus avisos la frase fija
  `INITIAL_STATE_NOT_CONVERGED`, traducida en la interfaz (los avisos del
  motor se traducen usándolos como clave).
- **La barra de estado del transitorio** la añade a su resumen de etapas.
- **La ventana de interpretación de agua** enseña el aviso del estado inicial
  debajo del de la etapa.
- **La API:**
  - `stage_rows` gana `warning`, `initial_state_converged` e
    `initial_state_warning`;
  - `seepage_field_summary` deja pasar las dos últimas.

## 2. Tests

`tests/test_transient_initial_state_v1270.py`, 12 casos (8 fallan con
0.1.269). Los otros 4 son las invariantes que tienen que valer en las dos
versiones.

- **La reproducción del prompt:** la presa de Gardner, dos pasadas y el
  rescate apagado (restaurado en `finally`).
  - Todas las etapas dicen `initial_state_converged = False` con el aviso.
  - La etapa que avanzó conserva `converged = True` y `ok`.
  - La de t = 0 es el campo del permanente: mismas cargas, `converged = False`
    y sus diagnósticos.
- **Un arranque convergido:**
  - todas dicen `True`, sin aviso;
  - **anotar no mueve nada**: el transitorio arrancado del permanente da, al
    bit, las cargas, `converged` e `iterations` del mismo transitorio con las
    cargas de ese permanente dadas como `initial_head`;
  - con `initial_head` no hay nota.
- **El aviso llega:**
  - a `run_transient_stability`, y no llega cuando el permanente convergió;
  - a `stage_rows` y al resumen de campo;
  - al diccionario en español;
  - a la barra de estado de la ventana principal (con
    `solve_project_groundwater` sustituido y restaurado, como en
    `test_transient_coupling_v1125`).

## 3. A/B y censo

Árbol contra árbol, con `_auditoria/P6_0269/ab_arbol.py` del banco: 0.1.269
frente a 0.1.270, sobre los transitorios del 05 (015–021, con todas sus
variantes) y la presa del 102 (permanente y desembalse).

- **Resultado:** 14 filas, **0 distintas**. Cargas, `converged` e
  `iterations` iguales al bit. La única clave nueva es
  `initial_state_converged`.
- **Censo:** los transitorios que arrancan de un permanente (05-017, 018 y
  020, y el desembalse del 102) dicen `True` en todas sus etapas. Los demás
  (015, 016, 019, 021) arrancan de un `initial_head` dado y no llevan nota.
  Ninguno cambia de estado, como se esperaba.
- **Ninguna fila del banco tiene una etapa de duración nula previa al primer
  paso que arranque de un permanente**, así que la excepción no toca el
  banco.

Suite entera: **5759 de 5759**.

## 4. Cierre en el banco

`d268()` en el `verificar_cierres.py` de la raíz corre la reproducción del
prompt y exige que todas las etapas digan `initial_state_converged = False`
con su aviso, y que un test del repositorio lo fije. Veredicto: **CUBIERTO
POR TEST**. D268 retirada.
