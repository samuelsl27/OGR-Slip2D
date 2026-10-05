# OGR Slip2D v0.1.259

**Una base que asoma al aire entre los dos extremos se rechaza con su razón
(D256). La guarda de los puntos de la Block Search es relativa al modelo
(D257). Y la API pone en el contorno todo extremo que no esté en él.**

Las tres cosas salieron al medir D243, el problema 109 del banco frente al
manual (2026-10-05). Las tres tratan de qué quiere decir «sobre el terreno», y
cada una lo decía de una manera.

## 0. Lo que se encontró

### D256: el rebanador no daba razón para una base interior al aire

- **El rechazo ya existía.** `slice_surface` rechaza una superficie cuando una
  esquina de la base de una dovela queda por encima del terreno más de
  1e-6 del ancho. Desde D244 (0.1.258) daba razón solo si esa esquina era uno
  de los dos extremos. Una esquina interior no dejaba razón.
- **Así que la búsqueda lo contaba mal.** Lo contaba entre las superficies
  que «could not be sliced», y la nota pedía más dovelas o menos vértices.
- **Medido en el 109, con las juntas de antes de D243:**
  - **Las 4000 «no rebanables» de 5088 salían todas de esa comprobación,** en
    una dovela interior: 3988 casos de capa débil y 12 poligonales.
  - **Más dovelas no las arreglaban:** de 40 por clave re-rebanadas con 500,
    no se rebanó ninguna.
  - **Todas tenían la base al aire sobre la huella de una junta**, por el
    redondeo del modelo: 2634 sobre la de la junta 3, 1085 sobre la de la 2 y
    281 sobre la de la 1. Asomaban de 3,5e-5 a 1,07e-3 m. El modelo se
    corrigió en el banco con D243.
- **Por qué es un defecto.** Rechazarla es correcto: con la base en el aire,
  parte de la masa no está en el suelo. Lo que estaba mal era la razón y el
  remedio que daba el aviso.

### D257: la guarda de la Block Search era absoluta

- **La guarda.** `BlockSearch._run` tira el punto que da un objeto de bloque
  si está por encima del terreno más de **1e-6 en las unidades del modelo**
  (`py > gy + 1e-6`).
- **Depende de las unidades.** El mismo modelo en metros y en milímetros no se
  quedaba con las mismas candidatas. AGENTS.md pide tolerancias relativas, y
  D238 ya había fijado una para la misma pregunta: `BLOCK_ON_GROUND_REL`, 1e-6
  de la diagonal.
- **Medido en el 109, con las juntas viejas y 20 000 cadenas por junta:**
  - en la junta 1, que asomaba 3,5e-5 m, se tiraba el 43 % de las cadenas con
    la guarda absoluta y el 5 % con la relativa;
  - en las juntas 2 y 3, que asomaban 1e-3 m, se tiraba el 56 % y el 76 % con
    las dos tolerancias;
  - con las juntas corregidas no asoma nada.

### La tolerancia de extremo de la API no era la del rebanador

- **Dos medidas para la misma pregunta.** `surface_evaluate` (D244) dejaba tal
  cual un extremo a menos de 1e-6 de la diagonal del modelo, medido **en
  perpendicular** al contorno. El rebanador juzga la distancia **vertical**
  frente a 1e-6 del ancho de la superficie.
- **En una cara empinada no coinciden.** La vertical es varias veces la
  perpendicular: unas 7 en la cara de 82° del gavión del 109. Así que la API
  podía dejar un extremo que el rebanador rechazaba después.
- **Le pasó a la poligonal optimizada de Bishop del 109.** Archivada a cuatro
  decimales, volvía «not analysed: its first or last vertex is above the
  ground».

## 1. Los cambios

### Rebanador (`ogr_slip2d/slicer.py`)
- La razón nueva `REFUSED_BASE_ABOVE_GROUND = "base_above_ground"`, para una
  esquina interior por encima del terreno.
- La tolerancia de 1e-6 del ancho pasa a tener nombre, `ABOVE_GROUND_REL`, sin
  cambiar de valor.
- Ningún número se mueve: esas superficies ya se rechazaban.

### Búsqueda (`ogr_slip2d/search.py`)
- Un contador propio, `_base_above_ground`, y un campo en el resultado,
  `SearchResult.bases_above_ground`.
- Una nota propia, `_base_above_ground_note`, que no culpa a las dovelas.
- Un texto para `refusal_text()`, que es lo que lee la API.
- La guarda de los puntos de cadena pasa a `chain_tol = ground_tol`, es decir,
  `BLOCK_ON_GROUND_REL` de la diagonal, bajo el interruptor de módulo
  `BLOCK_CHAIN_GUARD_RELATIVE`. Con el interruptor apagado vuelve el 1e-6
  absoluto.

### Censo de inválidas (`ogr_slip2d/interpretation.invalid_summary`)
Cuenta esas superficies bajo −101 («cualquier otro rechazo» en OGR), con la
razón «the base rises above the ground surface between the ends».

### API (`ogr_api/ops/analysis._snap_polyline_ends`)
- **Lleva al contorno todo extremo que no esté en él.** Solo deja tal cual el
  que está a menos de `_ON_RING_REL` = 1e-9 del ancho, que es redondeo. Tras
  el movimiento, el extremo queda sobre el contorno y el rebanador ya no puede
  rechazarlo.
- **La nota sale solo si el movimiento supera la tolerancia del rebanador.**
  Por debajo de `ABOVE_GROUND_REL` del ancho, el propio rebanador lo habría
  pegado al terreno sin decir nada.
- **Se descartó copiar en la API la regla del rebanador.** Habría sido una
  regla en dos sitios.

## 2. Tests

Test nuevo `tests/test_ground_refusals_v1259.py`, con 10 casos:

- **D256:**
  - el rebanador da la razón nueva;
  - 30, 120 y 500 dovelas no lo arreglan (es la premisa de la nota nueva);
  - la búsqueda lo cuenta aparte y lo dice;
  - por `BaseSearch.run`, la nota nombra la causa, ninguna pide más dovelas,
    y el censo lo cuenta con su razón;
  - controles: dentro de la tolerancia se rebana sin razón, y un extremo al
    aire conserva la razón de D244.
- **API**, con una cara de 80°:
  - la premisa: un extremo 4e-5 a la izquierda de la cara está a 3,9e-5 de
    ella, dentro de la tolerancia vieja (6,3e-5), y 2,3e-4 por encima en su
    x, fuera de la del rebanador (2,5e-5);
  - ese extremo se lleva a la cara y se calcula, con el mismo factor que con
    el extremo exacto a 1e-4;
  - un extremo sobre la cara no recibe nota.
- **D257**, con un objeto de bloque que asoma 5e-7 m en el mismo modelo en
  metros y en milímetros:
  - la premisa: con la guarda absoluta, en milímetros llegan menos candidatas
    a evaluarse que en metros;
  - con la relativa, llegan las mismas.

**Discriminación** contra un `git archive` de 0.1.258 (eb331ca), con el
envoltorio sin buscador editable: **fallan 5 de 10**, los cinco por
comportamiento. Pasan los dos controles y las tres premisas.

## 3. El banco

- **A/B de D257 en el mismo proceso** (`_auditoria/P5_0259/ab_d257.py` →
  `ab_d257_0.1.259.json`). Se corrió la Block Search de los 12 modelos de
  bloque del banco (seis del 02 y seis del 03), con todos sus métodos y el
  interruptor apagado y encendido.
  - De **55 filas, ninguna se mueve.** Tampoco cambia ningún recuento de
    válidas ni de evaluadas, y ninguna fila revienta.
  - Ningún modelo del banco tiene hoy un objeto de bloque que asome por
    encima del terreno entre 1e-6 y la tolerancia relativa.
  - El 109, que es el que lo ejercitaba, ya tiene las juntas corregidas
    (D243).
- **D256 no mueve ningún número por construcción:** solo da la razón de un
  rechazo que ya existía. En las 55 filas del A/B no hay ni una base al aire.
- **Interruptor** `search.BLOCK_CHAIN_GUARD_RELATIVE` en `INTERRUPTORES` con
  (0, 1, 259). Ya son 43.
- **`d256()`, en el verificador del 02:**
  - en vivo, el bulto de 1e-3 sobre la cara se rechaza como base al aire,
    contado aparte, y 500 dovelas no lo arreglan;
  - en vivo, la Block Search de Bishop sobre el 109 con las juntas de antes
    de D243 (`_auditoria/P5_0258/modelo_109_antes_d243.ogr`) da 5306 bases
    al aire con su nota, 0 «sin rebanar» y ninguna nota que pida más
    dovelas. Son más que las 4000 de la medida de 0.1.258 porque la guarda
    relativa de D257 deja pasar más cadenas de la junta 1;
  - la discriminación.

  Veredicto: CUBIERTO POR TEST.
- **`d257()`:**
  - en vivo, el talud de los tests en metros y en milímetros, con un objeto
    que asoma 5e-7 m: con la guarda relativa se evalúan 40 candidatas en los
    dos; con la absoluta, 40 en metros y 15 en milímetros;
  - el A/B;
  - la discriminación.

  Veredicto: CUBIERTO POR TEST.
- **La poligonal optimizada de Bishop del 109,** que antes no se podía
  re-evaluar, pasa ahora por la API. Con los cuatro métodos da Bishop 2,163,
  Janbu 2,025, Spencer 2,820 y GLE 2,700. Es la medida del cruce de críticas
  entre métodos (D258, abierta).

## 4. Verificación

- **El test nuevo**, 10 de 10.
- **Selección** de los tests relacionados, 241 de 241: `ground_refusals`,
  `polyline_endpoints`, `block`, `surface_evaluate`, `f3b_ops`,
  `version_consistency`, `unsliceable`, `interpretation`, `invalid`,
  `search_effort`, `outside_model` y `model_edge`.
- **Suite entera**, 5647 de 5647.

**Qué falta por probar:** nada en pantalla. La versión no toca la interfaz, y
la nota nueva sale en las notas del análisis como las demás.
