# OGR Slip2D v0.1.241

**D232: una carga repartida que apunta hacia arriba tira del terreno.** Hasta
0.1.240, la componente vertical de una carga repartida se sumaba al peso de
las dovelas con `abs(p·dy)`, así que una carga que apunta hacia arriba se
aplicaba hacia abajo. Su componente horizontal, el caso de un segmento
vertical y las cargas puntuales sí conservaban el signo. Ahora lo conserva
también la vertical, en el rebanador y en los otros dos sitios que leen esa
misma presión.

Primera versión de la tanda D226–D232 (plan aprobado el 2026-09-30), que
vuelve tras las dos partes de P5. D232 va delante de D226 porque D226b cambia
las cargas.

## 0. Lo que se encontró, y dónde

### La premisa, medida con 0.1.240

Talud φ = 0 de `test_tension_crack_truncation_v1109` sin grieta, su círculo,
Bishop a 1e-10 y 160 dovelas. 20 kPa sobre la meseta (x de 62 a 78, y = 40),
resultante 320 kN/m:

| Carga | Dirección | Δ peso (kN/m) | F |
|---|---|---|---|
| sin carga | — | — | 1,11093 |
| repartida hacia abajo (vertical, 270°, normal de izquierda a derecha) | (0, −1) | +318,06 | 1,02954 |
| repartida hacia ARRIBA (90°, normal de derecha a izquierda) | (0, +1) | **+318,06** | **1,02954**, la misma |
| repartida a 45° (arriba y a la derecha) | (0,71; 0,71) | **+224,90** | 1,12414 |
| puntual hacia abajo, 320 kN/m | — | +320 | 1,02908 |
| puntual hacia ARRIBA, 320 kN/m | — | **−320** | **1,20692** |

Una carga repartida hacia arriba daba el mismo número que si empujara, y la
puntual equivalente, un 17 % más. El rebanador dice en un comentario que una
carga puntual de P kN/m y una repartida de integral P dan el mismo peso de
dovela, y eso era falso para las que apuntan hacia arriba. La capa de
operaciones, al crear una carga normal dibujada de derecha a izquierda,
avisaba de que «tira del terreno», y el motor no lo hacía.

### Un tercer lector que el plan no nombraba

`ogr_core/support/bond.py::sigma_v_effective_at`, la tensión vertical con que
un soporte calcula su adherencia, suma la misma presión. Con el signo, una
carga que tira reduce esa tensión, y el recorte en cero de siempre impide que
la adherencia salga negativa.

### El banco no tiene ninguna

Censo de los 230 modelos de los bancos 02 a 07: 11 cargas repartidas en 9
modelos (009, 025, 026, 037, 060, 093 y 107), todas hacia abajo (dy = −1) y
de magnitud positiva. Con esos valores, `−p·dy` y `abs(p·dy)` son el mismo
doble, así que el cambio no puede mover un número del banco.

## 1. El motor

- **`slicer._surface_pressure_at`** suma `−p·dy`: hacia abajo es positivo y
  conserva el signo, el mismo convenio que el peso de la dovela y que
  `_line_load_components`.
- **`excess_pore_pressure.load_delta_sigma_v`** hace lo mismo y lee el mismo
  interruptor: los dos lectores de esa presión no pueden discrepar.
- **Interruptor `ogr_slip2d.slicer.SIGNED_SURFACE_PRESSURE`.** Apagado, el
  comportamiento de 0.1.240. Entra como el 33.º en `INTERRUPTORES` del banco.
- Una resultante neta hacia arriba en una dovela es un peso neto negativo,
  que los métodos ya tratan; no se ha visto en el banco.

## 2. La interfaz

Nada. El aviso de la capa de operaciones («the load points UPWARD (it pulls
the ground)») pasa a ser cierto, y un caso lo comprueba.

## 3. Tests

**`tests/test_upward_load_v1241.py`**, 9 casos sobre el talud φ = 0. Las
identidades no suponen la regla con que el rebanador reparte la carga:

- dovela a dovela, la carga que tira quita exactamente lo que la misma carga
  que empuja pone;
- los nueve métodos dan el mismo factor sobre esas dovelas que sobre las de
  sin carga con ese peso quitado a mano (1e-12);
- arriba es exactamente lo contrario de abajo;
- el orden físico: sin carga, con la que empuja y con la que tira;
- la inclinada a 45° conserva los dos signos;
- los otros dos lectores, el exceso de presión intersticial y la tensión de
  un soporte, esta recortada en cero;
- con el interruptor apagado, la que tira vuelve a empujar;
- la capa de operaciones avisa de que la carga tira, y el motor la aplica
  tirando.

**Discriminación** contra `git archive` d4d93b1 (0.1.240), con el runner de
ese árbol: **8 de 9 fallan**, todos por comportamiento. Pasa el del
interruptor apagado, que es lo que había.

## 4. El banco

- **Censo** (`_auditoria/P1_0241/censo_cargas_arriba.py`): ninguna carga
  apunta hacia arriba.
- **A/B del interruptor** (`ab_d232.py`, con la maquinaria de D189), espalda
  con espalda sobre los 9 modelos con cargas repartidas: 38 comparaciones (18
  círculos publicados y 20 críticas archivadas), **0 movidas** y los
  controles iguales.
- **Cierre: `d232()`, CUBIERTO POR TEST.** Comprueba en vivo el espejo y el
  orden de los factores (1,0295 < 1,1109 < 1,2063), el interruptor apagado,
  el censo, el A/B y la discriminación. D232 se retira al índice.
- **Ciclo de cierre:**
  - `verificar_cierres.py` entero: 214 cierres y 0 bajadas;
  - instantánea `Evaluaciones/0.1.241`;
  - D232 abierta y retirada en la misma versión, y tachada en la cadena P4;
  - prompts regenerados (44);
  - auditorías de invariantes con 0 ERROR en el 02 y en la raíz;
  - instantánea rehecha con `--forzar`;
  - `--seco` completo después de retirar.

## 5. Lo que se reporta y NO se corrige

Nada nuevo.

## 6. Verificación

- **Suite entera:** 5362 de 5362, en 42 min, con la verificación de los
  cierres en paralelo.
- **Selección** de cargas, exceso de presión intersticial, soportes,
  adherencia, operaciones, rebanador, sismo, cuñas ancladas, API y
  versiones: 685 de 685 en 44 archivos.
- **Discriminación:** 8 de 9 contra 0.1.240.
- **Banco:** censo, A/B (0 de 38), `d232()` CUBIERTO POR TEST y el ciclo de
  cierre (214 cierres, 0 bajadas).

**Qué falta por probar:**
- **Una carga que tira en la aplicación real:** dibujar una carga normal de
  derecha a izquierda en la interfaz y ver que el factor sube. Lo cubre el
  test por la capa de operaciones, no por la ventana.
- **Un caso publicado con carga hacia arriba:** el banco no tiene ninguno.
