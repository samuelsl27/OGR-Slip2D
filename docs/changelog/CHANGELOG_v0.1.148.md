# OGR Slip2D v0.1.148

**El encargo de D77 pedía cambiar la regla de radios de la rejilla para que
generase los ocho círculos publicados de los muros 87–94, y proponía la
regla que había que poner. Medida la premisa, era falsa; corrido el
programa de referencia sobre el muro, el defecto era real pero estaba en
otro sitio: en la generación con DOS juegos de límites, que desde v0.1.146
existe y nunca se había medido.** Con un juego, la regla de v0.1.88 es
exacta también en un muro con caras verticales.

---

## Lo primero fue medir lo que el encargo daba por hecho

El encargo decía que la calibración de v0.1.88 «no distingue el primer
límite alcanzado del límite del lado de la salida» y que la regla buena era
«el mayor radio cuyo círculo todavía aflora» (el círculo por el pie). Dos
cosas comprobables contra los `.s01` de la calibración de agosto, que
listan todos los radios que emite la referencia en 949 + 34 centros:

- **Sí distingue.** En Ej_1 el centro (40 · 120) tiene el límite más
  cercano en el lado de la coronación y la referencia tapa ahí, en 80,62 m
  (el lejano está a 124). Estaba en el test desde v0.1.88.
- **La regla del pie está refutada.** Prototipada como recuento de cortes
  y contrastada: se separa de la referencia en 26 centros de Ej_1 y 16 de
  Ej_2 (hasta 6,7 m) y en 8 más con límites movidos. En (−29,52 · 135) de
  Ej_2 la referencia para en el punto límite aunque un círculo mayor siga
  cortando el terreno dos veces. Exactamente la configuración del muro.

Y un tercer dato que apuntaba a otro lado: los ocho radios publicados caían
los ocho en la banda del 5 % entre `r_max` y la distancia al pie, que
ninguna horquilla con ese inset muestrea. Se leyó como firma de Auto
Refine. **Era la firma de un inset del 0,1 %**, que aún no se conocía.

## Lo que decidió: cinco modelos en el programa de referencia

El propietario corrió el muro del 87 (`referencias/Ejemplos/
00_2026_09_06_Test_Muro_D77`) con la rejilla en el centro publicado y
Radius Increment 1 (A) y 10 (B), la rejilla del banco (C), Auto Refine (D)
y la rejilla A con **un solo juego** de límites (E). Los `.s01` traen todos
los radios.

| modelo | centros | regla de v0.1.88 | veredicto |
|---|---|---|---|
| E, un juego | 440 | **9,4e-14** | la regla es exacta con caras verticales |
| A, dos juegos, rinc 1 | 440 | 3,7 m | otra regla |
| C, dos juegos, rejilla del banco | 342 | 6,8 m | otra regla |

Desde (−5,713 · 20,432) la referencia emite [17,264, 18,568] donde este
motor emitía [15,142, 15,502]. El 18,547 publicado cabe. **D77 es de la
generación con dos ventanas**, no de `_radius_bracket` en general.

## La regla, despejada centro a centro

Cuatro lecturas se cayeron antes de la buena, cada una con el centro que la
tumbó; están en `docs/audits/grid_radius_two_windows_v1148.md`. La que
reproduce A entero (440/440, 8,9e-14) y los 299 centros de C que tienen
círculos válidos (5,0e-10):

1. la superficie de cada ventana son los segmentos del perfil que **solapan**
   su intervalo (un límite en mitad de un segmento lo incluye entero, hasta el
   vértice siguiente) más las caras verticales **interiores**; nada del hueco
   entre ventanas ni la cara vertical que está justo en el borde;
2. un radio es válido si el círculo corta esas superficies en dos puntos
   consecutivos, **entrando** en el suelo por la ventana 1 y **saliendo** por
   la 2;
3. `r_min = R_lo · 1,001` si el extremo lo fija una esquina del perfil y
   `R_lo` si lo fija un punto límite; `r_max` igual con `0,999`;
4. si los márgenes se cruzan se repite `r_min`; si no hay radio válido se
   emite un radio degenerado que no resuelve, como hace la referencia en
   sus 40 centros así (61 círculos cada uno, 0 válidos).

La validez sólo cambia en las distancias a vértices, puntos límite y pies de
perpendicular, así que se lee de esa lista sin barrer nada: unas veinte
comprobaciones por centro.

## Lo que no es de esta versión y hay que decir

Sobre el modelo del banco, la referencia da Bishop **1,078** con la rejilla
del banco y con Auto Refine, y **1,102** sobre el círculo publicado. El
manual publica 1,040. **El modelo reconstruido del 87 no es el del manual**,
y la variable es el refuerzo. Y **este motor evalúa un 5–7 % por debajo de la
referencia sobre el mismo círculo del mismo modelo** (1,029 frente a 1,102).
El 1,033 de OGR contra el 1,040 del manual era la resta de dos errores. Va a
D38 / D44 / D37 del banco, con los círculos y los factores de la referencia
anotados: por primera vez hay factores suyos sobre un modelo cuyo `.ogr`
gemelo existe.

## Qué cambia

- `GridSearch._radius_bracket` se bifurca cuando `slope_limit_sets` tiene dos
  juegos; el camino de un juego es el mismo código que antes.
- `_radius_bracket_two_windows`, `_window_segments`, `_circle_crossings` y
  `_two_window_circle_is_valid`, con la medida en el docstring.
- `TWO_WINDOW_INSET = 0.001`, medido como `RADIUS_INSET` lo fue.

## Qué se probó

- `tests/test_grid_radius_two_windows_v1148.py`: extremos de A (5 centros),
  C (6, incluidos un extremo en punto límite, uno en la esquina con la
  banqueta y = 12 cruzada y uno colapsado) y E (2) leídos del `.s01`; que el
  camino de un juego es la aritmética de v0.1.88 al bit; los círculos
  publicados de 87, 91 y 94 dentro de la horquilla de su centro; población
  `(nx+1)(ny+1)(rinc+1)` con 0 válidas en la zona sin radio válido; regla 7:
  declarar la segunda ventana mueve la horquilla 3 m; y las dos cláusulas de
  la superficie de ventana.
- `test_grid_radius_rule_v188`, `test_slope_limits_two_sets_v1146`,
  `test_grid_search_v117`: 40/40 sin cambios.
- El lector del banco (`_tools/leer_slim_d77.py`) sobre A, B, C, E con el
  motor nuevo: 440/440, 440/440 más espaciado 9e-14, 301/342 (los 41 sin
  válidos en la referencia), 440/440.
- La suite completa.

## Qué falta

- Regenerar y correr 87–94 en el banco; su fila de búsqueda se compara con la
  referencia sobre el **mismo** modelo (1,078), no con el 1,040 publicado.
- Un límite exterior en mitad de un segmento con dos juegos (los del muro
  caen en vértices) y centros con más de un intervalo válido (ninguno en los
  782 medidos): no medidos, y dicho en el docstring.
