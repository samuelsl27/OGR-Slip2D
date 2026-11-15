# OGR Slip2D v0.1.460

**`tension_crack_arm` es una cota, y un test fija la recta de acción del agua de la grieta (D428).** El comentario del
campo `Slices.tension_crack_arm` decía «vertical distance from the crack base to the centroid of the water column (for
moment)», y estaba mal dos veces:
- `_apply_tension_crack` guarda en él `crack_bottom_y + h_w / 3`, una **cota**, no una distancia desde el fondo de la
  grieta;
- h/3 es el centroide del diagrama triangular de presiones (Terzaghi 1943), no el de la columna de agua, que está a h/2.

**El momento era correcto.** Ningún método lee el campo: leen el momento que `add_water_force(f_h, y=...)` deja en la
dovela de la pared, a esa cota. Lo que faltaba es un test de esa recta de acción. Medido con 0.1.435, sobre los 127
tests de los nueve archivos de grieta:
- la recta a h/2 (+0,31 % en la forma cerrada) no la veía ninguno;
- la recta a h/3 sobre y = 0 (−9,6 %) la veía uno solo, una búsqueda contra una banda de ±5 %.

Por decisión de la propietaria (opción b del prompt), van el comentario, el docstring del test de v1110 y un test nuevo
del momento contra la forma cerrada.

**Ningún número cambia:** son un comentario, un docstring y un test. Es la trigésima tercera versión de la tanda P10 y
la última del plan del 2026-11-15 (D407, D427 y D428). Con ella P10 queda en D429–D446, sin versión, y Sarma
(0.1.461–0.1.467).

## 0. Lo que se encontró

- **El REPRODÚCELO con `--mutantes`** (`_auditoria/P10_D419_D428/medir_d428.py` del banco, su log de 0.1.459 al lado):
  - sobre d678ddb da lo de 0.1.435, en las secciones 2 a 5 línea a línea. En la 1 solo cambian los números de línea;
  - el empuje es ½·γw·h² = 176,58 kN/m, y su recta de acción, la cota 36: a la mano, en el momento de la dovela y en el
    campo;
  - la forma cerrada da 0,99779733, y los cuatro métodos 0,99779885 con 640 dovelas (+1,5e-6);
  - con NaN en el campo, los nueve métodos dan el 002 bit a bit;
  - de los 127 tests de grieta fallan 0 con la recta a h/2 y 1 con la recta a h/3 sobre y = 0.
- **Quién nombra el campo:** lo escriben `_apply_tension_crack` y `slice_store._SCALARS`, y lo nombran cuatro tests
  (`test_tension_crack_thrust_v1110` y los tres del almacén de dovelas). No cambia ninguno.
- **Las comprobaciones del banco que leen `slicer.py` como texto,** que un comentario nuevo podría tumbar en falso,
  como pasó con `d340`: `d428` en la raíz y `d223` en el 02. `d223` sigue CUBIERTO POR TEST.
- **Un camino equivocado de la comprobación del banco:** el comentario nuevo cita el viejo entre comillas para decir
  qué decía, así que la primera `d428()`, que buscaba «vertical distance from the» cerca del campo, lo habría tomado por
  el viejo. Ahora busca el comentario viejo en su sitio, pegado al campo.
- **La revisión adversaria (un agente)** no encontró nada alto. Encontró:
  - **(media) con la grieta llena sola, el test no distinguía la altura del agua de la de la pared,** que son entonces
    el mismo número. Dos mutantes que solo tocan el `y` del empuje vivían en los 5 casos nuevos y en los diez archivos
    de grieta:
    - la recta a un tercio de la pared;
    - la recta a la coronación menos dos tercios del agua.

    Con la grieta medio llena se desvían 8,3e-4 y 2,5e-3 de la forma cerrada. Ahora el test la pide también al 50 % y
    al 25 %, y los dos mueren;
  - **(baja) el caso a mano no comprobaba los signos** (usaba `abs`) y llamaba a `Slice.water_moment_about`, que el
    motor no usa: los métodos llaman a `SliceForces.water_moment_about`. Ahora comprueba el signo de la fuerza (−x,
    hacia fuera del talud) y del momento, por `slice_forces`;
  - **(baja) el margen de la forma cerrada:** 1e-5 sobre 6,1e-6 medidos dejaba 1,6 veces, y un cambio legítimo del
    rebanado podía tumbarlo. Pasa a 3e-5, que sigue 27 veces por debajo del mutante más estrecho (8e-4). `d428()`
    también;
  - **(baja) tres frases de la cabecera:**
    - «nothing else was ever wrong»: el momento era correcto en 0.1.459, no siempre. Hasta 0.1.61 el empuje no llegaba
      a ningún método;
    - «written here»: el terreno y el círculo se importan de v1109;
    - el coste no casaba con el changelog;
  - **(baja) un `==` sobre dobles** en la premisa de la pared, exacto por construcción. Ahora `isclose`, que es la regla
    de la casa;
  - **(baja) dos matices del comentario:**
    - el momento lo leen los métodos de momentos, y los de equilibrio de fuerzas solo la fuerza;
    - el 0.0 por defecto es ahora una cota de verdad, inofensiva porque el empuje es nulo.
  - **Una anterior, arreglada al paso porque es solo un comentario:** el de `tension_crack_force`, de 0.1.7, decía «the
    uppermost slice» y «when the slip surface intersects a Tension Crack boundary». Desde 0.1.109 se calcula solo para
    una pared que dejó el truncado y solo con agua, y se aplica en la dovela de esa pared;
  - **sin hallazgos:**
    - la forma cerrada es correcta en signo y en M_suelo, y vale para los cuatro métodos de momentos (Janbu, los Corps y
      Lowe-Karafiath no la cumplen, y no se les pide);
    - cada método tiene su camino y el test lo ve (un mutante de `interslice.py` mata solo a Spencer y GLE, uno de
      `ordinary.py` solo al Ordinario);
    - el caso a mano se gana su sitio: una fuerza en otra dovela solo la ve él;
    - no hay fugas, la guarda de memorias compartidas está en verde y la cabecera SPDX está;
    - «ningún método lee el campo» es cierto en todo el repositorio;
  - visto de paso: las copias de trabajo están en CRLF por `core.autocrlf=true`, y git las deja en LF al hacer commit.
    No es de esta versión.

## 1. El arreglo

- `ogr_slip2d/slicer.py`, el comentario de `Slices.tension_crack_arm`:
  - es la cota de la recta de acción del empuje, `crack_bottom_y + h_w / 3`;
  - es el centroide del diagrama triangular (Terzaghi 1943) y el mismo `y` que recibe `add_water_force`;
  - qué decía antes y por qué estaba mal;
  - que ningún método lo lee: los de momentos leen el momento de la dovela de la pared, y los de fuerzas solo la
    fuerza.
- El comentario de `tension_crack_force`, al lado, desfasado desde 0.1.109 (arriba).
- `tests/test_tension_crack_thrust_v1110.py`: el docstring de `test_the_line_of_action_is_a_third_of_the_way_up`
  dice cota. Su comprobación no cambia.

## 2. El test

`tests/test_tension_crack_moment_v1460.py`, 6 casos, sin Qt, unos 0,7 s en el runner. Invariante: el agua de la grieta
actúa a un tercio de la altura del AGUA sobre el fondo de la grieta, y los métodos toman ahí su momento. Pasa también con
el árbol de 0.1.459, porque el momento ya era correcto, y su cabecera lo dice.

- **La forma cerrada.** El talud φ = 0 de v1109 (su terreno, su círculo, su cohesión y su peso), con la grieta a la
  cota 34 y el agua h_w sobre su fondo: F = c·L_arco·R / (M_suelo + ½·γw·h_w²·(y_c − y_fondo − h_w/3)) (Bishop 1955),
  sea cual sea la hipótesis entre dovelas.
  - Los extremos, L_arco y la cuadratura de Simpson de M_suelo están escritos en el test.
  - γw = 9,81 va escrito aparte, con la premisa de que es el del proyecto.
  - Llena, Bishop, Spencer, GLE y el Ordinario, con 320 dovelas, a 3e-5 de ella (6,1e-6 medido).
  - Medio llena y a un cuarto, Bishop y el Ordinario.
- **El momento a la mano**, en la dovela de la pared, llena, medio llena y a un cuarto, a 1e-9:
  - el empuje, −½·γw·h_w², hacia fuera del talud;
  - su recta de acción, a la cota y_fondo + h_w/3 (`water_force_h_moment / water_force_h`);
  - su momento respecto del centro, por `slice_forces`, el camino de los métodos.
- **El campo** es esa misma cota, en los tres llenados.
- **Las premisas:** γw es el del proyecto, y el rebanador termina el círculo en la línea de la grieta, en los extremos
  de la mano.

Discriminación, por los mutantes de `mutants_d428.py` del banco y no por el `git archive`, donde pasa. Mueren los
cinco:
- la recta a h/2 y la recta a h/3 sobre y = 0: cada una en tres casos, entre ellos la forma cerrada;
- el campo guardado como la distancia que decía el comentario, con el momento intacto: en el caso del campo;
- la recta a un tercio de la pared y a la coronación menos dos tercios del agua (los de la revisión): en el caso a mano
  y en el de los llenados parciales.

## 3. Lo que no cambia

- Ningún número: ni en la suite ni en el banco.
- `slice_store._SCALARS` y su orden.
- Los `test_slide_validation_*`.
- Ninguna cadena de la interfaz, ajuste ni acción.

## 4. Verificación

- El test solo: 6 de 6. Con el árbol de 0.1.459 también pasa, como dice su cabecera. Sus mutantes, arriba.
- Los vecinos, con cada patrón comprobado con `--list` (D431): `tension_crack slice_store ponded_water
  corps_one_crack weak_layer_tension_crack failure_direction shared_test_caches test_license_v143
  test_version_consistency slide_validation`: 233 casos, en verde.
- **La suite entera con `--jobs 4`,** tras los arreglos de la revisión, sola en la máquina:
  - 7784 casos: 7783 en verde y 1 saltado, `Failed: 0`;
  - sin `Leaks` ni `Chunks died`, y sin el aviso `SLOW, NOT IN tests/_slow.txt`;
  - la última serie en verde fue hace 38 commits (bea135c), así que no toca serie;
  - los contadores de los dos README pasan de 7777 a 7783: los 6 casos nuevos.

## 5. Banco

- `d428()` en el `verificar_cierres.py` de la raíz, registrada en `COMPROBACIONES`. Mide en vivo:
  - el comentario del campo en el `slicer.py` que se ha importado, para que discrimine con otro árbol;
  - la forma cerrada con Bishop a 3e-5;
  - y exige las tres clases del test.

  Resultado:
  - con el árbol nuevo: CUBIERTO POR TEST (6,1e-6);
  - con el de 0.1.459 (d678ddb): SIGUE ABIERTO, por el comentario. El momento ya era el bueno.
- `d223` del 02, que lee `slicer.py` como texto: CUBIERTO POR TEST, igual que en su archivo.
- Los dos VC enteros no se re-corren: esta versión no cambia ninguna línea de código del motor, solo un comentario,
  y las dos comprobaciones que leen ese archivo como texto se han corrido.
