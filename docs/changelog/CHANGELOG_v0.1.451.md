# OGR Slip2D v0.1.451

**La puerta de una superficie da, en los modos sísmicos, lo que da la corrida para ella (D406).** El docstring de
`evaluate_surfaces`, que es la puerta de `surface_evaluate` en el API y en el servidor MCP, dice que pasa por
exactamente lo mismo que `run_analysis`. En «Calcular Ky» y Newmark calculaba el Ky y se paraba ahí: ni desplazamiento
ni ninguna de las cinco notas sísmicas. Medido con 0.1.450 (624031d) en el talud de ejemplo no circular (Path de 5,
Bishop) con la polilínea del usuario y la sinusoide de 0,3 g y 2 Hz durante 4 s:

| caso | corrida | `surface_evaluate` con 0.1.450 | ahora |
|---|---|---|---|
| con registro | Ky 0,10141, 0,3475 m | Ky 0,10141, sin desplazamiento | Ky 0,10141, 0,347549 m |
| sin registro y kh = 0,10 | las notas «the project applies a horizontal…» y «Newmark displacements were requested…» | ninguna | las dos, con sus códigos |

**Ningún número cambia:** la puerta da un dato que faltaba. La corrida no cambia. Es la vigesimocuarta versión de la
tanda P10 y la cuarta del plan aprobado el 2026-11-14.

## 0. Lo que se encontró

- **Paso 0, sobre 0.1.450:** el REPRODÚCELO da su salida, la misma que con 0.1.435 y con 0.1.447.
- **Una regla para las dos puertas.** El cuerpo de `_seismic_notes` pasa a `_seismic_lines(project, method_id,
  evaluations)`. La corrida le da todas sus superficies (`all_evaluations_of`, como desde D397), y
  `evaluate_surfaces` le da la superficie de cada método. El Ky de las dos puertas ya era el mismo, bit a bit; ahora
  también el desplazamiento.
- **Un método sin resultado sigue sin nota sísmica:** dice por qué no hay resultado (`_given_refusal`), y nada más.
  La razón no es la de la corrida, cuya población nunca es None y que dice siempre las notas del modelo (la revisión
  lo midió: «como en la corrida» era falso). En esta puerta None es un rechazo, y `surface_evaluate` toma cada nota
  de un método rechazado como el motivo del rechazo (`notes`), cosa que una nota sísmica no es. Un resultado inválido
  sí es un resultado, y lleva sus notas.
- **La superficie sin Ky tiene su frase**, `method.seismic_no_ky_given`: «the surface has no critical seismic
  coefficient below 1: no coefficient up to it brings its factor of safety down to the target, so it has no Ky.»,
  con su castellano. La de la corrida («1 of 1 surfaces have … excluded from the ranking») hablaba de una
  clasificación que la puerta no tiene. La corrida conserva la suya, palabra por palabra.
- **El API no se toca.** `lem_summary` ya exporta `newmark_displacement` cuando existe, y `with_warning_codes` da el
  código de cada nota. El JSON redondea a seis decimales, así que la comparación bit a bit va en el motor.
- **Cambia a propósito `tests/test_method_notes_v1348.py`, y es el único test existente que cambia:** `_seismic_lines`
  entra en `_CODED`, y `_V1347` gana la muestra del código nuevo, escrita con esta versión y así marcada.
- **La revisión adversaria (un agente)** repitió en A/B la puerta contra 0.1.450: 12 variantes × 4 superficies × 3
  métodos. Sin modos sísmicos sale byte a byte igual, y con ellos solo añade cosas. La corrida, en 7 variantes
  sísmicas, da los mismos avisos y `details` bit a bit. Encontró, y se arregló:
  - la justificación falsa de arriba;
  - que ningún caso protegía que un método rechazado no diga nada sísmico: un mutante sobrevivía, y ahora hay un caso
    con su mutante;
  - que el test de «una regla» solo medía la puerta: una corrida con su propia copia pasaba, y ahora mide las dos;
  - la frase de la superficie sin Ky;
  - la fila de `surface_evaluate` de `docs/mcp/herramientas.md`, que lleva sus cambios por versión;
  - que `_seismic_notes` construía la lista antes de su guarda.

  Vio también, y se reportan sin tocar porque son anteriores:
  - con FS(0) ≤ el objetivo, el Ky es 0 y Newmark integra a ky = 0 sin nota. Con la norma de 1,25 los tres métodos
    dan 0,935224 m: es el desplazamiento de un bloque estáticamente inestable, y la corrida hace lo mismo desde
    0.1.127;
  - con un `record_id` que no existe, la nota dice «no seismic record is selected».

  Por decisión de la propietaria, van a dos fichas nuevas, D439 y D440, al final de P10 y sin versión. Las mide
  `_auditoria/P10_D439_D440/medir_d439_d440.py` del banco. En el plano de 0.1.429 con una norma de ÷2,5, el factor
  a kh = 0 es 0,808 (forma cerrada 0,808290), el Ky sale 0 y Newmark da 22,04 m sin ninguna nota.

## 1. Qué cambia

- **`ogr_slip2d/analysis_runner.py`:**
  - `_seismic_lines`, nuevo, con el cuerpo de `_seismic_notes`, que pasa a llamarlo tras su guarda;
  - `evaluate_surfaces`, tras cada resultado que no sea None, añade sus líneas a `warnings` sin repetirlas, con la
    frase de una superficie sin Ky (`one_surface=True`);
  - el docstring de `evaluate_surfaces` dice ya que pasa por la regla sísmica.
- **`ogr_slip2d/method_note_messages.py`:** el código `method.seismic_no_ky_given`, con su castellano en
  `ogr_gui/i18n/__init__.py`.
- **`docs/mcp/herramientas.md`:** la fila de `surface_evaluate`.

## 2. Qué se probó

- **`tests/test_surface_evaluate_seismic_v1451.py`** (11 casos, unos 2 s), contra Newmark (1965) en el plano de 0.1.429:
  - por la corrida y por `evaluate_surfaces`, el mismo Ky y el mismo desplazamiento, bit a bit (`float.hex`);
  - el Ky a tan(φ − β) y el desplazamiento al pulso rectangular, u = V²/(2gN)·(1 − N/A), los dos a 1e-6;
  - el API: `details.newmark_displacement`, el del motor redondeado a seis decimales, y las notas con sus códigos;
  - las notas: sin registro, `method.newmark_no_record`; con kh = 0,10, `method.seismic_kh_replaced`, las mismas que da
    la corrida; con c = 500 kPa, la frase de una superficie sin Ky, y la corrida la suya;
  - una superficie rechazada (un círculo fuera del modelo, con kh y sin registro) dice solo por qué, también en el
    API;
  - sin modos sísmicos, nada sísmico se dice ni se añade;
  - una regla: la corrida pregunta a `_seismic_lines` con todas sus superficies, y la puerta con la suya.
- **Discriminación:** en el árbol de 0.1.450, sin el buscador editable, fallan 8 de 11. Siete fallan por lo que miden y
  uno porque la regla nueva no existe. Pasan la premisa, el control sin modos sísmicos y el rechazo, que 0.1.450 ya
  cumplía.
- **Mutantes** (`mutants_d406.py`, en el banco): 10, todos muertos:
  - la puerta sin la regla;
  - sin desplazamiento;
  - sin la nota del kh;
  - sin la del registro;
  - sin la de las superficies sin Ky, en la puerta o en la corrida;
  - la regla de la corrida solo sobre la población de la búsqueda;
  - y los tres de la revisión: un rechazo con notas sísmicas, la frase de la corrida en la puerta, y una corrida con
    su propia copia de la regla.
- **Vecinos**, con los patrones `newmark yield_acceleration seismic method_notes f2_ops user_polylines polyline_endpoints
  surface_evaluate frozen_evaluation api_jobs version_consistency mcp_server i18n voice_and_terms` (cada uno
  comprobado con `--list`): 369 casos en verde en 22 archivos.
- **La suite entera** con `--jobs 4`, tras los arreglos de la revisión: **7663 casos, 7662 en verde, 0 fallos y 1
  omitido**, sin fugas ni tramos muertos. La serie no toca (29 commits desde la última).

## 3. Qué queda

- La siguiente es D409 (0.1.452), la última del plan: el factor que Interpretar escribe junto al Ky dice con qué kh se
  calculó.
