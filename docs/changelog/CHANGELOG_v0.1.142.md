# OGR Slip2D v0.1.142

**Los dos Janbu no reproducían la cuña plana, y lo que llevaba veinte
versiones bloqueando el arreglo era que se estaba juzgando contra una
columna publicada cuando había dos, y discrepan entre sí más que el error
que se discutía.**

Cierra **D46** entero. La mitad de Bishop cerró en 0.1.137; ésta es la de
Janbu, que era la única que quedaba.

---

## El defecto

Una misma resultante, aplicada como **soporte** o como **carga**, daba dos
factores de seguridad distintos en Janbu simplificado y corregido: −0,096 %
congelado, sin encogerse al refinar, en `test_efp_wall_v1122`.

La nota al término en `janbu.py` tenía **cuatro combinaciones medidas** y se
paraba ahí, por escrito:

```
this pair (n_α outside, T_S raw)   Clouterre mean 1.76 %, load≡support -0.096 %
n_α outside, T_S·sec α             Clouterre 6.90 %
inside n_α, T_S raw                geotextiles -20 to -39 %
inside n_α, T_S·sec α (consistent) Clouterre 7.95 %, load≡support 0.000000
```

«La única combinación que reproduce los seis planos publicados de Clouterre
es la que no puede pasar su propia identidad, y la que la pasa exacta los
pierde. Elegir entre ellas necesita evidencia externa que esta tarea no
tiene.»

## La evidencia que faltaba no era un valor publicado

Los seis casos del problema 48 y el del 47 son **PLANOS**. Sobre un plano la
masa deslizante es **un solo sólido libre**: las fuerzas entre dovelas son
internas y se cancelan en la suma, así que lo que un método suponga sobre
ellas no puede cambiar la respuesta. El equilibrio límite tiene una sola
solución, y está en forma cerrada:

```
ACTIVO   F = ( c'·L + (W·cos α + T_N)·tan φ' ) / (W·sin α − T_S)
PASIVO   F = ( c'·L + (W·cos α + T_N)·tan φ' + T_S ) / (W·sin α)
```

Metiendo una fuerza externa `P = (P_h, P_v)` en el balance de Janbu
—`Σ S·sec α = Σ W·tan α`— sale

```
Σ (W − P_v)·tan α  +  Σ P_h   =   Σ S·sec α
```

y como `T_S = slide_sign·(P_h·cos α + P_v·sin α)`, el soporte le debe al lado
motor **exactamente `−T_S·sec α`**, con su parte normal llegando por `W_eff`
—que es literalmente lo que `support_vertical_load` devuelve, `down = −P_v`,
término a término. Sustituido en la forma de Janbu sobre un plano, el
resultado se cancela hasta la cuña de arriba, en activo y en pasivo. **La
combinación que satisface la identidad es la que es exacta.** Las otras tres
no eran opciones.

## Y bastaba con correr los otros ocho métodos, cosa que nadie había hecho

Los seis planos del 48 se evaluaban **sólo con `janbu_simplified`**. Sobre
ellos, hoy:

| plano | cuña cerrada | Corps#1 | Corps#2 | Lowe-K | Fellenius | **Janbu 0.1.141** |
|---|---|---|---|---|---|---|
| 45° | 1,0840 | 1,0840 | 1,0840 | 1,0840 | 1,0840 | **1,1265** |
| 55° | 0,9176 | 0,9176 | 0,9176 | 0,9176 | 0,9176 | **0,9815** |
| 70° | 0,8116 | 0,8116 | 0,8116 | 0,8116 | 0,8116 | **0,8819** |

Cuatro métodos reproducen la cuña **a seis decimales**. Janbu era el único
que no, y su error corre con el ángulo: **+3,9 % a 45°, +8,7 % a 70°**. Sobre
el mismo modelo **sin bulones** Janbu ya era exacto (−0,002 %), así que el
desacuerdo era el término del soporte y nada más.

Los últimos números de Spencer sobre esos planos que guardaba la ficha del 48
eran los de *sin bulones* (0,86713 contra 0,867367 a 45°): la vieja A48-1,
anterior a que el refuerzo llegara a superficie no circular. Nadie los había
vuelto a mirar.

## Lo que más enseña: la columna que no se usaba

El manual publica **dos** columnas para esos seis planos —la suya y la de
Sheahan (2003), la fuente original— y **discrepan entre sí hasta un 4,7 %**
(1,123 contra 1,176 a 45°; 0,923 contra 0,887 a 70°). Más que el hueco que se
estaba adjudicando. v0.1.113 comparó contra una sola y llamó ancla al
resultado; ése fue el error de método.

Aplicando a las dos columnas el mismo argumento que decidió v0.1.113 —*un
error de formulación deja tendencia a lo largo de los seis, uno de geometría
no*—:

| error contra | columna del manual | | columna de Sheahan | |
|---|---|---|---|---|
| | media | **rango** | media | **rango** |
| proyección horizontal (0.1.112) | 14,96 % | 16,2 | peor | — |
| sólo `T_S` (0.1.113 → 0.1.141) | 1,75 % | 4,76 | 1,38 % | 4,27 |
| **la cuña (0.1.142)** | 7,95 % | 8,29 | 7,73 % | **1,13** |

Contra la **fuente original**, la formulación corregida deja un residuo casi
constante —−7,9 −7,5 −7,1 −7,5 −8,1 −8,2 %—, que es la firma de la
geometría; y la geometría de este muro es justo lo que el manual **no**
publica: las siete longitudes de bulón y su inclinación de 10° se miden en
las figuras 48.1 y 48.2. La formulación a la que sustituye tenía una
tendencia de 4,3 puntos contra esa misma columna. Y reproduce además la
**forma** de Sheahan: su columna baja monótona hasta 70° y la del manual
repunta 0,001 en el último punto; la curva corregida baja monótona.

**Una hipótesis medida y RECHAZADA**, anotada para que no se reintente a
ciegas: *«los bulones son sencillamente más fuertes de lo modelado»*, la
lectura obvia de un desfase plano del −7,7 %. Escalando las tres capacidades
por un solo factor, la media contra la columna del manual baja a 1,97 % con
×1,20 — pero el rango contra la de Sheahan sube de 1,13 puntos a 4,82, y con
×1,40 a 9,99. **Ningún escalar único aplana las dos columnas**, así que el
desfase queda nombrado como no explicado, no explicado a conveniencia.

## El cambio

`ogr_slip2d/methods/janbu.py`, cuatro ediciones acopladas (las parciales son
peores que no tocar nada: `inside n_α, T_S raw` da −20 a −39 % en los
geotextiles):

1. `W_eff += support_vertical_load(...)` — el soporte es una carga lineal
   sobre su dovela y entra en el equilibrio vertical del que sale `n_α`,
   igual que Bishop desde 0.1.137;
2. el activo sale del denominador pesado por `sec α`, no crudo;
3. el pasivo entra en el numerador pesado por `sec α`;
4. **se borra** el `T_N·tan φ'` que se sumaba fuera de `n_α` desde v0.1.64:
   ahora sale del propio equilibrio de la dovela, y sumarlo otra vez fuera
   sería contarlo dos veces con el peso equivocado.

## Resultado

- La identidad carga ≡ soporte pasa de **−0,096 % congelado** a **0,0 / 0,0 /
  −1,4e-14 %** a 25, 100 y 400 dovelas. Y es **exacta, no decreciente**, que
  es más fuerte: por dovela el soporte le debe al lado motor
  `−T_S·sec α = −slide_sign·(P_h + P_v·tan α)` y la misma fuerza como carga
  le debe `−slide_sign·P_h` por `h_water` y `−slide_sign·P_v·tan α` por
  `w_total` — los mismos dos términos, no queda nada que discretizar. Bishop,
  Ordinary y Spencer llevan ahí un residuo de malla de 0,087 % que baja a
  0,002 %; sólo los tres de marcha están en la misma compañía.
- Sobre plano, con la tolerancia apretada, Janbu reproduce la cuña a
  **1e-13**, activo y pasivo, a cualquier número de dovelas.
- **Los nueve métodos resuelven ya un soporte de la misma manera.**

## Un hallazgo nuevo, medido y NO corregido

**Spencer y GLE no aterrizan en la cuña sobre un plano, y no es por el
soporte.** Están obligados por ella —cierran equilibrio de fuerzas— y no la
cumplen; lo delata que **apretar la tolerancia los aleja**: sobre el plano de
50° **sin ningún soporte**, el error crece de +6,7e-4 con la tolerancia de
serie (1e-3) a +2,8e-2 con 1e-10. Cuarenta veces peor para una solución
cuarenta veces más convergida, mientras Corps #1 se queda en 5e-10 en las dos
y Janbu pasa de 2e-5 a 2e-12. Tampoco es monótono: a 45° con soporte activo,
GLE hace −1,9e-4 → −1,0e-7 → −8,3e-12 y Spencer −6,6e-4 → −1,1e-3 → −2,7e-3.

Un solve acoplado que aterriza en otro punto cuando se estrecha el intervalo
es lo que parece una **raíz espuria**, y este proyecto ya se encontró una
(D10, 0.1.106). Queda congelado como hecho en
`TestSpencerAndGleDoNotSettleOnTheWedge`: si algún día se arregla, esos tests
fallan y hay que reescribir lo que se afirma ahí.

## Y una deuda que ya estaba, anotada al pasar

`base_forces_no_interslice_shear` no ve el soporte, ni en Janbu ni en Bishop:
las normales por dovela que se reportan —y que `rapid_drawdown._stage1_state`
lee— ignoran el refuerzo. Es anterior a esto y no se toca aquí.

## Tests

**Nuevo**: `tests/test_janbu_wedge_v1142.py`, 20 casos. La cuña cerrada sobre
planos de 35° a 50°, activo y pasivo, con `W` y `L` sacados de la
**geometría** —el área del triángulo, no del rebanador— para que el ancla no
se apoye en lo que vigila. Cuatro clases de control que valen tanto como la
afirmación: que Janbu ya era exacto sin soporte, que Bishop **no** está
obligado por la cuña y que eso no es un defecto (falla también sin ningún
soporte), que el residuo restante es la **iteración** y se desploma cinco
décadas al apretar la tolerancia, y que los métodos que sólo *encogen* en la
identidad son los que llegan a los dos canales por aritmética distinta.

**Reescritos**:

- `test_efp_wall_v1122.py` — el test que congelaba el desacuerdo afirma ahora
  el acuerdo, y exacto. Su propio docstring pedía que pasara esto.
- `test_support_projection_v1113.py` — el 48 y el 47 se re-enuncian. El ancla
  deja de ser una banda del 2,5 % contra una columna que el propio manual
  contradice, y pasa a ser la cuña cerrada (exacta) más el hecho medido de
  que el residuo contra la fuente original es **plano**. Se conserva sin
  cambio lo que esos casos sí sujetan: que la proyección es la **base** y no
  la horizontal, la forma de la curva, el caso sin bulones y
  `TestPassiveIsNotDividedByF` (el 85, que no se mueve). La banda del 47 pasa
  de 1 % a 3 % — que es la incertidumbre que la propia cabecera del fixture
  declara desde 0.1.112, porque las cabezas y la inclinación se leen de una
  figura. Una banda más estrecha que la incertidumbre declarada estaba
  midiendo la formulación contra una coincidencia.
- `test_support_normal_v1137.py`, `test_support_noncircular_v1140.py` y
  `ogr_slip2d/support_integration.py` — las tres notas que decían que Janbu
  seguía abierto.

**No se movieron**: el problema 85 (activo y pasivo), la grieta de tracción
(2 y 42), el 54 de Yamagami, los geotextiles y la identidad muro EFP ≡
`EndAnchored` bit a bit en los nueve.
