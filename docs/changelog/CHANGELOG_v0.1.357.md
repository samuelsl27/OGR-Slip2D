# OGR Slip2D v0.1.357

**La resistencia al corte de los dos Hoek-Brown es la envolvente de Mohr de su criterio, evaluada
exacta (D171). Las constantes con las que esa envolvente no existe se rechazan con código.**

Hasta 0.1.356, los dos modelos calculaban

    h = 1 + a·mb·(mb·σn/σci + s)^(a−1),   τ = σn·(h − 1)·√h/(h + 1)

Es la forma paramétrica de Balmer (1952) con σ3 sustituida por σn y σ1 − σ3 por σn·(h − 1), y no
es la envolvente:
- con las constantes de serie da τ(0) = 0, donde el criterio tiene 307,5 kPa;
- en σn = 145 kPa deja la resistencia dentro del círculo de compresión simple del propio macizo.

Ahora, para cada σ′n se resuelve el σ′3 de su círculo de rotura tangente en la paramétrica de
Balmer, tal como la corrigen Hoek, Carranza-Torres y Corkum (2002, ecs. 8-10). La pendiente sale
de tan φi = (k − 1)/(2·√k), con k = dσ′1/dσ′3 (Hoek 1990, ec. 11, con a = 0,5).

La tanda P7b cerró además, en el banco y sin versión, D130 (la unidad de la fig. 9.6 del manual de
agua) y D358 (la presa 2 del problema 9 mal transcrita). Ninguna de las dos toca este repositorio.

## 0. Lo que se encontró

- **La tabla de la ficha se reproduce.** La envolvente exacta da 307,5 / 440,9 / 661,4 / 3342,1 /
  10073,1 kPa en σn = 0 / 50 / 145 / 2000 / 10000. La de 0.1.356 daba 0 / 179,9 / 443,2 /
  2913,2 / 7779,2.
- **Había casos publicados con los que validarla, y en abierto.** La ficha no conocía ninguno, y
  el banco no tiene ningún material Hoek-Brown: 0 de 264 `.ogr`. Se guardaron en
  `referencias/Documentacion_Guia/Hoek_Brown/`, con su fila en `INDICE.md`:
  - **Hoek (1990)**, *Int. J. Rock Mech. Min. Sci.* 27(3), p. 229. Ejemplo trabajado: con
    σc 60 MPa, m 0,238 y s 0,000063, en σ′n 0,5 MPa, τ 0,6610 MPa, φi 41,896° y ci 0,2124 MPa.
    Hoy sale 660,98 kPa, 41,8967° y 212,41 kPa. En 0.1.356 salía **541,2 kPa (−18 %)**. El
    segundo ejemplo (σ′3 0,25 MPa: σ′n 0,5940, τ 0,7429) cuadra igual.
  - **Hoek, Carranza-Torres y Corkum (2002)**: ecs. 8-10 (Balmer corregido) y ec. 7
    (σt = −s·σci/mb).
  - **Hammah, Yacoub, Corkum y Curran (2005)**, ARMA/USRMS 05-810, Tabla 2. Talud homogéneo de
    10 m a 45°, con γ 25 kN/m³, σci 30 MPa, mb 0,067, s 2,5·10⁻⁵ y a 0,619. Equilibrio límite:
    **Bishop 1,153 y Spencer 1,152**.
    - La geometría de su fig. 3, medida a 300 ppp (25,5 px/m en x y 25,2 en y): pie y coronación
      de 15 m y cimentación de 8 m.

    | | Bishop | Spencer |
    |---|---|---|
    | publicado | 1,153 | 1,152 |
    | 0.1.356 | 0,788 (−31,6 %) | 0,787 (−31,7 %) |
    | 0.1.357 (rejilla y refinado local con cuatro arranques) | **1,1488 (−0,36 %)** | **1,1495 (−0,21 %)** |

    Con la cimentación a 5 m o los extremos a 10 m, la variación queda por debajo del 0,4 %.
- **El ejemplo 2 de Hammah no se reproduce, y queda en la ficha nueva D359.** Es el mismo talud
  con una capa Mohr-Coulomb de 1 m (c = 0, φ = 25°) en el pie. Publicado, no circular: Bishop
  0,934 y Spencer 0,963.
  - Con superficies de tres tramos que siguen la capa, la envolvente exacta da 1,0016 (+7,2 %) y
    1,0282 (+6,8 %).
  - Con la búsqueda por caminos, 1,044 y 1,091.
  - Con la de 0.1.356, 0,768 y 0,823.

  Como el ejemplo 1 cuadra al 0,4 %, la diferencia no parece de la envolvente. Puede estar en el
  mecanismo, en la búsqueda o en datos de la capa que el artículo no da, como su γ. No se ha
  ajustado nada.
- **La suite no lo veía.** Con un prototipo exacto inyectado en memoria pasaban todas las
  aserciones de Hoek-Brown existentes: ningún test fijaba un número de la envolvente contra una
  referencia.
- **El factor de seguridad no ve la tangente.** En el punto fijo de `ENVELOPE_AT_OWN_STRESS` (D84)
  F depende solo de τ. Una tangente que olvidara el divisor de diseño movía F en 3e-10, así que la
  tangente se comprueba a nivel del modelo.
- **La precisión cerca de σt la fija la propia entrada, no el algoritmo.** Con g escrita como
  (σn − σt)/σci, a partir de 1e-5·|σt| por encima de σt el error queda en 2e-11, y en σn ≥ 0, que es
  donde evalúa `local_c_phi`, en 1e-15. Converge en 5 iteraciones como máximo (4 de media).
- **Tracción.** `local_c_phi` linealiza en σ′ = 0 una base en tracción y extiende la recta. Con
  τ(0) > 0, esa recta queda un poco por encima de la envolvente exacta en [σt, 0). Linealizar
  Hoek-Brown en la σ′ de la propia base da el mismo F, a 16 cifras, en los dos ejemplos de Hammah y
  en los dos métodos. Por decisión de la propietaria, `local_c_phi` no se toca.

## 1. El cambio

- **`ogr_core/materials/builtin_models.py`.**
  - `_hoek_brown_mohr(σn, σci, mb, s, a) → (τ, dτ/dσn)`: Newton en x = mb·σ′3/σci + s,
    salvaguardado por la horquilla [0, mb·σn/σci + s]. g es creciente y cóncava para 0 < a ≤ 1, así
    que la raíz es única.
  - τ = 0 en σt y por debajo, que es la tracción de `tensile_strength` (D165).
  - Los dos modelos la usan (el clásico con a = 0,5 y mb = m), así que no pueden separarse.
  - La tangente es analítica y se divide ella misma por `design_divisor`. Con s = 0, en σn = 0 la
    envolvente es vertical, y toma la secante sobre el paso de antes.
  - Docstrings con sus fuentes. En `tensile_strength`, Hoek et al. (2002) consta ya como leído y
    Hoek (1983) sigue citado y sin leer. Sale el aviso de D171.
- **El dominio** (`ogr_core/project/rules.py`, `hoek_brown_refusal`, llamada desde
  `strength_model_refusal`). Se rechazan σci ≤ 0, mb o m ≤ 0, s < 0, a ∉ (0, 1] y los valores no
  finitos.
  - Llevan los códigos `strength.hoek_brown.domain` y `strength.hoek_brown_classic.domain`, con su
    castellano.
  - El rechazo llega al análisis (`check_analysis_settings`), al API y al diálogo de materiales.
  - Hasta hoy esas constantes calculaban en silencio. Con a > 1 la inversión no tiene raíz única.
- **Sin interruptor**, como en 0.1.218 (modelos de resistencia de `ogr_core`, cero filas del
  banco). La comparación con lo de antes se hizo sobre un `git archive` de 0.1.356.

## 2. Lo que se mueve

- **El F de cualquier talud con Hoek-Brown sube.**
  - El talud del test de la norma de diseño, entre +18,5 % y +21,9 %.
  - Con las constantes de serie, entre +72 % y +84 %.
  - El de Hammah, un +46 %.
- **Janbu corregido**: con τ(0) > 0 el suelo pasa a ser «c-φ» (D80), y b1 pasa de 0,31 a 0,50.
- **Una llamada directa a `shear_strength` con σn < 0** daba τ(1e-6) ≈ 0. Ahora da la τ exacta en
  (σt, 0), y 0 por debajo de σt.
- **Las constantes fuera de dominio** dejan de calcular: el análisis las rechaza y lo dice.
- **Ningún número del banco.**

## 3. Coste

A/B en el mismo proceso (nuevo, viejo, nuevo), sobre el talud de Hammah:

| | 0.1.356 | 0.1.357 |
|---|---|---|
| `shear_strength` | 0,61 µs | 3,7 µs |
| `tangent_slope` | 1,54 µs | 3,7 µs |
| `local_c_phi` | 3,39 µs | 8,4 µs |
| una resolución de Bishop (50 dovelas) | 20,6 ms | 37–39 ms |
| rejilla de 2197 círculos, en serie | 18,6 s | 35,9 s |

Solo lo pagan los materiales Hoek-Brown. La propietaria lo aceptó sin atajos. Se descartaron la
forma cerrada para a = 0,5 y una memoria de una entrada, que ahorrarían alrededor del 40 % en
`local_c_phi`.

## 4. Caminos equivocados

- **La primera rejilla «exacta» dio el F de la envolvente vieja.** La búsqueda en rejilla corre en
  procesos hijos, que importan el motor sin el parche de la medida. Se midió en serie, con
  `ogr_slip2d.search._PARALLEL_MIN_CIRCLES` alto.
- **La primera formulación del prototipo resolvía g a través de σ′3.** Junto a σt cancelaba, y
  llegó a necesitar 55 iteraciones. La de (σn − σt) converge en 5 o menos.
- **El refinado local de Bishop se quedó una vez en 1,1521.** En otro arranque bajó a 1,1488. Por
  eso el test exige que los seis vecinos a ±0,2 m del círculo archivado no den menos.
- **Hoek (1990) imprime φi 41,896 y el valor exacto es 41,89668**, que redondearía a 41,897: el
  artículo arrastra intermedios redondeados (h 1,1927; θ 46,7174 frente a 46,7173). El test admite
  una unidad de la última cifra impresa, no media.
- **El test de la v1351** («cada código se alcanza») no conocía los dos códigos nuevos. Se excluyen
  ahí con la razón escrita: nacieron después de 0.1.350 y no tienen frase congelada que meter en su
  tabla. Los alcanza el test nuevo, y la comprobación de que todo código tiene su castellano con
  sus campos ya los cubría.

## 5. Pruebas

- **`tests/test_hoek_brown_envelope_v1357.py`**, 15 casos:
  - la paramétrica de Balmer, generada desde σ′3 sin inversión, a 1e-9 con a ∈ {0,5; 0,6; 0,619} y
    en las dos clases;
  - la tangente;
  - Hoek (1990), el ejemplo y su forma cerrada;
  - el extremo en σt y la tangencia al círculo de compresión simple, con todos los círculos del
    criterio por debajo;
  - s = 0 y el divisor de diseño en τ y en la tangente;
  - Hammah, ejemplo 1, a ±2 %, con sus mínimos locales;
  - el rechazo: código, análisis y castellano.
- **Discriminación.** Copiado a un `git archive` de 0.1.356 y lanzado sin el buscador editable,
  fallan 12 de los 15. Los tres que pasan allí son guardas.
- **Selección de los tests de Hoek-Brown**, resistencia, tracción, norma de diseño, `local_c_phi`,
  anclajes helicoidales, Ito-Matsui, rechazos y versión: 312 de 312.
- **Suite entera**: 6519 de 6519, en 83,5 min. Parte del tiempo compartió la máquina con la
  regresión del VC del 02.
- **Banco.**
  - `d171()` del VC del 02 da CUBIERTO POR TEST.
  - Contra el árbol de 0.1.356 (motor y fuente del árbol viejo) da NO SE SOSTIENE en todas sus
    partes.
  - El VC del 02 entero, con el motor nuevo: 241 claves y 0 bajadas; solo sube D171.
  - Las comprobaciones que usan Hoek-Brown (D165, D176, D180 y D181) no dependen de la
    envolvente y salen con el mismo detalle.
  - D171 queda retirada al índice, P7 se poda y D359 se abre.

## 6. Qué queda

- **D359**, abierta en P7: el ejemplo 2 de Hammah.
- **La linealización en tracción de las envolventes curvas** (`local_c_phi`) sigue como está; en
  los casos medidos no mueve nada.
- **La CI de Linux**, cuando se suba.
