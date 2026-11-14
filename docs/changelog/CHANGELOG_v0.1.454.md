# OGR Slip2D v0.1.454

**La superficie probabilística crítica del Overall Slope se elige entre todas las superficies analizadas, también las
del usuario (D417).** En un análisis Overall Slope cada muestra repite la búsqueda entera.
- El factor de la muestra es el de su crítica (`run.critical`), que incluye las superficies del usuario: la búsqueda
  las evalúa después de su población.
- Pero la contabilidad por superficie (`_accumulate_surfaces`) recorría solo `run.evaluations`.
- Así una superficie del usuario nunca acumulaba factor y nunca era candidata a superficie probabilística crítica.
  Cuando era el mínimo de una muestra, `times_global_minimum` no se le contaba.

Medido con 0.1.453 (d3e5be1), igual que con 0.1.435. Es el talud de ejemplo con Path Search de 5, Janbu, la cohesión
Normal con una desviación del 20 % de la media y 40 muestras LHS:

| | FS determinista | PF de la corrida | superficie probabilística crítica | PF | β | veces mínimo global | `surfaces_tracked` |
|---|---|---|---|---|---|---|---|
| sin polilínea | 1,3094 | 0 | de la búsqueda | 0 | 2,831 | 4 | 5 |
| con la polilínea, 0.1.453 | 1,1232 | 0,025 | **la misma de la búsqueda** | **0** | 2,831 | **0** | 5 |
| con la polilínea, ahora | 1,1232 | 0,025 | **la polilínea** | **0,025** | 1,907 | **40** | 6 |

La polilínea es el único mínimo global de las 40 muestras: la corrida daba PF 2,5 % y su superficie probabilística
crítica, PF 0, del lado inseguro y sin ninguna nota.

**Por decisión de la propietaria (opción a), las superficies del usuario acumulan como las de la búsqueda**, por
`all_evaluations_of`. Lo que la búsqueda optimizó (`steered`, `optimized`) sigue fuera, como deja fuera la referencia
sus superficies optimizadas.

**Ningún número del banco se mueve:** ninguno de sus `.ogr` lleva superficies del usuario (medido el 2026-11-10). Sin
superficies del usuario el resultado es el de antes, bit a bit. Es la vigesimoséptima versión de la tanda P10 y la
segunda del plan aprobado el 2026-11-14.

## 0. Lo que se encontró

- **Paso 0, sobre 0.1.453:** `medir_d417.py` da lo de 0.1.435 línea a línea.
- **La definición de la referencia,** en su ayuda local (la página «Critical Probabilistic Surface» de Interpret): la
  de menor índice de fiabilidad de todas las superficies analizadas, con una condición, que exista en todas las
  muestras.
  - Deja fuera las optimizadas, porque cambian de una muestra a otra.
  - Dice que se calcula con las superficies que generó la búsqueda, y no habla de las del usuario. Contarlas es la
    opción (a) de la propietaria, no algo que diga la ayuda.
  - Una superficie del usuario conserva su geometría de una muestra a otra, así que PUEDE cumplir la condición. Si la
    cumple se decide como para cualquier otra, por tener factor en todas las muestras: un círculo que en alguna
    muestra contesta por otra de sus masas tiene otra clave ahí, y una que se descarta en alguna muestra no tiene
    factor ahí.
- **Una superficie del usuario igual a una de la búsqueda se cuenta una vez:** el `seen` de `_accumulate_surfaces`
  va por la clave de la superficie (tipo y geometría al último dígito). Lo comprueba un caso.
- **El recuento por la otra puerta es el mismo número, bit a bit.** Re-evaluar la polilínea en cada muestra con
  `evaluate_surfaces`, la puerta de `surface_evaluate`, da el factor que guarda la corrida: la misma aritmética sobre
  el mismo modelo muestreado.
- **Los tests que fijan la superficie probabilística crítica** no usan superficies del usuario: `test_overall_slope_v137`,
  `test_surface_key_endpoints_v1237`, `test_interpret_i3_v153` y `test_dxf_export_census_v1354`. Siguen en verde.
- **La revisión adversaria (un agente) no encontró fallos del cambio en el caso que arregla.** Encontró:
  - **(media) con la semilla del reloj, la del usuario se publicaba como crítica porque no tenía competencia.** Con
    Números aleatorios = «aleatorio», `analysis_seed()` es None y Path, Slope y Block dibujan superficies distintas en
    cada muestra.
    - Hasta 0.1.453 eso daba la nota «ninguna superficie tiene factor en todas las muestras» y ninguna crítica.
    - Con el borrador, la polilínea del usuario era la única candidata y salía publicada con PF 0, β 15,4 y media de
      FS 2,26, nunca mínimo global de una muestra, con un FS determinista de 1,14.
    - Las búsquedas que se guían por sus factores (Recocido, Enjambre, Auto Refine) siguen sin crítica.
    - **Por decisión de la propietaria,** una búsqueda que dibuja sus superficies con la semilla del reloj no tiene
      superficie probabilística crítica, con la nota de siempre, aunque haya superficies del usuario
      (`_draws_from_the_clock`).
    - Se decide al elegir y no antes de la contabilidad, así que una corrida sin superficies del usuario conserva
      `surfaces_tracked` y su nota. La rejilla, que no sortea, conserva la del usuario.
    - La Slope Search no guardaba su semilla (solo su generador). Ahora la guarda en `seed`, como Block y Path.
  - **(media-baja) un mutante sobrevivía:** contar una superficie del usuario solo en las muestras en que gobierna,
    el sesgo que prohíbe D87. Sobrevivía porque la polilínea del test gobierna todas las muestras. Ahora hay una
    segunda polilínea que no gobierna nunca, y el caso hecho a mano tiene una del usuario que no es la menor.
  - **(baja) frases:**
    - «una superficie del usuario se analiza en todas las muestras con la misma geometría, así que la cumple» no es
      siempre verdad, y ahora el docstring dice cómo se decide;
    - «la ayuda deja fuera solo las optimizadas» callaba que la ayuda habla de las superficies de la búsqueda;
    - los docstrings de `SurfaceProbability` y de `all_evaluations_of` se habían quedado viejos.
- **Se reporta sin tocar:**
  - **(baja, anterior) el conmutador «Superficie probabilística crítica» de Interpretar no dibuja nada**
    (`interpret_window.py`): solo pone el PF y el β en la barra, así que no se ve que la crítica es la polilínea. Va a
    una ficha nueva, por decisión de la propietaria;
  - con una búsqueda que se guía por sus factores no hay superficie probabilística crítica, tampoco la del usuario.
    Es la exclusión de la referencia, y se queda;
  - el inglés de dos notas: `stat.cps_not_in_every_sample` dice «no surface of the search» y `stat.cps_steered` dice
    que ninguna tiene un PF propio, cuando las del usuario ahora pueden tenerlo. Está congelado desde 0.1.352
    (`_V1352` de `test_stat_notes_v1353`), y las dos siguen siendo ciertas de las superficies de la búsqueda.

## 1. Qué cambia

- **`ogr_slip2d/probabilistic.py`:**
  - `_accumulate_surfaces` recorre `all_evaluations_of(run)` (`ogr_slip2d/search.py`), el acceso tolerante de 0.1.428,
    en vez de `run.evaluations`. Las `steered` y la `optimized` siguen fuera, y el docstring cita la definición de la
    referencia;
  - `_draws_from_the_clock`: una búsqueda con `seed` None no tiene superficie probabilística crítica, y lo dice con la
    nota de siempre.
- **`ogr_slip2d/search.py`:** la Slope Search guarda su semilla en `seed`. Nadie la leía antes, y no cambia lo que
  dibuja.
- **Lo que mueve, a propósito, solo con superficies del usuario:** la superficie probabilística crítica publicada, su
  PF, su β, sus veces mínimo global y `surfaces_tracked`. Con la semilla del reloj, nada: no hay crítica, como antes.

## 2. Qué se probó

- **`tests/test_overall_slope_user_surfaces_v1454.py`** (12 casos, 5,1 s en el runner con los imports: cada corrida
  es un análisis estadístico por su puerta, con la búsqueda determinista, y cada caso es una identidad de la
  definición).
  - **La referencia son identidades de la definición,** en el caso del REPRODÚCELO con más dispersión: desviación del
    30 %, rango de ±60 % y 30 muestras. La premisa, medida: la polilínea gobierna todas las muestras y falla en 3.
  - El PF de la superficie probabilística crítica es la fracción de muestras con el factor de la polilínea por
    debajo de 1, recontada re-evaluando la polilínea en cada muestra; sus factores son los del recuento, bit a bit.
  - `times_global_minimum` es el número de muestras cuya crítica es la polilínea: aquellas en que su factor es el de
    la muestra.
  - La regla de 0.1.453, sustituida en el mismo proceso, publica una de la búsqueda con PF 0 y 0 veces.
  - Sin superficies del usuario, el resultado es el de la función de 0.1.453, bit a bit: muestras, factores, la
    superficie, su PF, su β, sus veces, `surfaces_tracked` y las notas.
  - **La regla, sobre una corrida hecha a mano:** las del usuario acumulan aunque no sean la menor, las `steered` y la
    `optimized` no, y una del usuario igual a una de la búsqueda se cuenta una vez.
  - Una segunda polilínea que no gobierna nunca se cuenta en todas las muestras (`surfaces_tracked` 7).
  - **La semilla del reloj:** Path no tiene crítica, con polilínea y sin ella, y con la nota de siempre; la rejilla
    conserva el círculo del usuario; y, sin calcular, qué búsquedas que construye la corrida sortean con el reloj
    (Slope, Block y Path con «aleatorio»; ninguna con «pseudoaleatorio»; la rejilla nunca).
- **Discriminación:** en el árbol de 0.1.453, sin el buscador editable, fallan 7 de los 12 casos: 6 por lo que hacen
  (los de la superficie del usuario, la polilínea que no gobierna y el círculo de la rejilla) y 1 por un nombre
  nuevo. Pasan la premisa, el control bit a bit, el defecto reproducido, la cuenta única y Path con la semilla del
  reloj, que en 0.1.453 ya no tenía crítica.
- **Mutantes** (`mutants_d417.py`, en el banco): 10, todos muertos:
  - solo la población de la búsqueda (0.1.453);
  - las `steered` que acumulan, o la `optimized`;
  - una superficie que se cuenta dos veces;
  - solo las del usuario;
  - el mínimo global sin contar;
  - y los cuatro de la revisión: la del usuario contada solo donde gobierna, el reloj sin preguntar, una búsqueda sin
    semilla (la rejilla) tomada por reloj, y la Slope Search sin su semilla.
- **Vecinos**, con los patrones `overall_slope surface_key interpret_i3 dxf_export_census probabilistic user_surfaces
  user_polylines statistics slope_search seed` (cada uno comprobado con `--list`): 463 casos en verde.
- **La suite entera** con `--jobs 4`, una sola vez y tras la revisión: **7711 casos, 7710 en verde, 0 fallos y 1
  omitido**, sin fugas ni tramos muertos. La serie no toca (32 commits desde la última).

## 3. Qué queda

- La ficha nueva del conmutador de Interpretar que no dibuja la superficie probabilística crítica.
- En el plan del 2026-11-14 siguen D410 (0.1.455), D425 y D426.
