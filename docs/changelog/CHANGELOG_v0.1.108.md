# OGR Slip2D v0.1.108

**El desembalse rápido ya no se puede perder en silencio: se cierra la
puerta que quedaba abierta (A98-1), aparecen otras dos que nadie había
mirado —una de ellas es la que usa la interfaz— y el defecto del encargo
llegaba ya arreglado.**

El encargo describía dos defectos medidos en **0.1.97**. Lo primero fue
volver a medirlos en 0.1.107, y de los dos sólo uno seguía existiendo.

---

## 0 · El defecto 1 ya estaba cerrado, y conviene decir por qué

El encargo decía que `rapid_drawdown._stage1_state` lee `result.base_normal`
y que sólo Bishop y Fellenius la rellenan, así que con cualquier otro método
la lista llega vacía, el bucle se rompe en la primera vuelta y la etapa 2 no
aplica resistencia sin drenar a ninguna dovela. Eso era cierto en 0.1.97.
**D11, cerrado en 0.1.107, lo arregló**: los nueve métodos rellenan la
columna, y la línea lee `base_normal_force`.

Medido hoy sobre el círculo publicado del problema 95 (169,5 · 210,0 ·
R 209,9; 50 dovelas; Corps de dos etapas; publicado **1,347**):

| método | sin desembalse | con desembalse | dovelas sin drenar |
|---|---|---|---|
| bishop_simplified | 2,1971 | 1,3499 | 50 |
| ordinary_fellenius | 1,8941 | 1,1461 | 50 |
| spencer | 2,2013 | **1,3498** | 50 |
| gle_morgenstern_price | 2,2005 | 1,3507 | 50 |
| janbu_simplified | 1,9180 | 1,2098 | 50 |
| janbu_corrected | 2,0581 | 1,3036 | 50 |
| lowe_karafiath | 2,1961 | 1,3594 | 50 |
| corps_engineers_1 | 2,2197 | 1,3991 | 50 |
| corps_engineers_2 | 2,2603 | 1,4229 | 50 |

Spencer daba 2,0773 (+54 %) y ahora da 1,3498 (**+0,2 %**). El criterio de
cierre que pedía el encargo —Spencer a 1,35 ± 3 % y las 50 dovelas sin drenar
en todos los métodos— ya se cumplía antes de tocar nada.

**La pregunta que el encargo dejaba abierta la responde la fuente.**
Preguntaba si el estado de consolidación debe salir del método que eligió el
usuario o de un análisis drenado propio. La EM 1110-2-1902 (2003) resuelve su
propio ejemplo del apéndice G con Spencer y **tabula una inclinación entre
dovelas distinta para cada una de las tres etapas** (6,0° / 12,2° / 13,7°), y
el §G-7a dice que las cantidades de la etapa 1 coinciden con las del método
de 1970 *«except for differences resulting from the assumed interslice force
inclination»*. Cada etapa se resuelve con el procedimiento de rebanadas en
uso; que la etapa 1 difiera entre métodos es una consecuencia que la fuente
nombra, no un defecto. **No se ha tocado.**

Lo que sí se ha cambiado es **la forma en que se degradaba**: el `break`
mudo. Una lista de normales más corta que las dovelas es ahora un
`RapidDrawdownError` con el método nombrado, tanto en `_stage1_state` como en
el bucle del tope drenado, donde la misma condición dejaba la dovela con su
resistencia sin capar. Si un décimo método olvida la columna, el desembalse
falla y no analiza otra cosa.

---

## 1 · A98-1: la puerta que seguía abierta

`build_method` es el único punto que envuelve el desembalse —lo dice su
propio *docstring*— así que instanciar la clase del registro y pasársela a
una búsqueda devolvía un análisis drenado normal, sin excepción ni aviso.
Medido hoy, mismo círculo, Spencer:

```
GridSearch(method=method_registry()["spencer"](), …).evaluate_circle(…)
        -> 2,2017      drenado, en silencio
GridSearch(method=build_method(p, "spencer", 50), …).evaluate_circle(…)
        -> 1,3498      el desembalse
```

**+63 %, del lado inseguro.** Y no es sólo una trampa para quien escribe
*scripts*: la ventana de terminal de la propia aplicación enseña
`GridSearch(BishopSimplified(), …)` como ejemplo.

La guarda va en `BaseSearch._analyse`, que es la puerta única y así lo
documenta: por ahí pasan `evaluate_circle`, `evaluate_surface`, las seis
búsquedas, *Optimize Surfaces* y el muestreador probabilístico. La pregunta
es sobre el **par** (proyecto, método) —ninguno de los dos está mal por
separado, lo que no puede ser es que se junten calladamente— así que la
función nueva se llama `drawdown_gap(project, method)` y devuelve el motivo o
`None`.

**Lanza** en vez de devolver una superficie inválida, y es deliberado: no es
un hecho sobre esta superficie, sino sobre el objeto método, así que todas
las superficies de la corrida darían lo mismo y el usuario leería «ninguna
superficie válida» con la causa enterrada en el informe de inválidas. El
mensaje nombra `build_method`.

Los dos envoltorios se marcan con `PERFORMS_DRAWDOWN = True` en vez de
comprobarse con `isinstance`: un cuarto procedimiento que llegue como clase
propia queda cubierto declarándolo, no acordándose de ensanchar una tupla en
otro archivo.

**Coste**: una lectura de atributo por superficie en el camino normal
(`rapid_drawdown` es `False`), ~0,2 µs sobre un cálculo de milisegundos. No
se ha cronometrado porque está por debajo de lo que el cronómetro de la suite
distingue; manda el recuento del trabajo añadido, como en v0.1.65.

---

## 2 · Segunda vía, y ésta la usa la interfaz

Buscando quién más construye métodos apareció esto, que el encargo no
mencionaba:

`run_global_minimum` y `run_sensitivity` instanciaban el método con
`registry[mid]()` cuando no recibían un `method_factory`, y **nadie en todo
el repositorio les pasaba uno** — tampoco `main_window._compute_statistics`,
que es lo que hay detrás de *Statistics → Compute Statistics*. Así que el
análisis probabilístico y el de sensibilidad de un modelo con desembalse eran
los de un modelo **drenado**, en silencio, y de paso perdían `tolerance`,
`max_iterations` e `initial_fos` (el mismo defecto que v0.1.74 cerró en las
búsquedas, todavía abierto por este camino).

El `_make_method` por defecto pasa a ser `build_method(project, mid,
num_slices)`. Comprobado: con el comportamiento anterior la media sale `nan`
y las cuatro muestras fallan; con el nuevo, 1,3564, que es el valor
determinista con desembalse sobre el mismo círculo.

## 3 · Tercera vía: un procedimiento mal escrito

`check_drawdown_settings` devolvía `None` —«se puede analizar»— cuando
`rapid_drawdown_method` no era ninguno de los cuatro conocidos, y
`wrap_for_drawdown` devolvía el método sin envolver por la misma condición.
Un nombre de procedimiento con una errata en un `.ogr` daba un análisis
drenado sin una palabra: el mismo silencio de A98-1, alcanzado por un error
de tecleo. Ahora se nombra y se listan los cuatro válidos.

## 4 · `check_drawdown_settings` se ejecuta siempre

Lo pedía el encargo y era el tercer punto: la función lleva desde v0.1.68
diciendo con todas las letras por qué un proyecto no puede correr un
desembalse —material sin drenar sin marcar, Ru o rejilla de presiones, las
dos líneas cambiadas de sitio— pero sólo si alguien la llama. La llaman la
interfaz y el CLI, a través de `check_analysis_settings`; `build_method` a
pelo devolvía un número.

Ahora la llama `wrap_for_drawdown`, que es donde se aplica el envoltorio, y
lanza `RapidDrawdownError` con el mensaje. Las dos puertas de siempre no
cambian: ambas siguen enseñando la lista de problemas antes de llegar aquí.

---

## 5 · Los tests

`tests/test_drawdown_methods_v1108.py`, 27 tests, ~4 s. Sobre el modelo del
apéndice G de la EM, con **el círculo dado y sin búsqueda**, que es lo que
hace la comparación honesta: la misma geometría lleva **dos** valores
publicados por dos procedimientos, Corps de dos etapas **1,35** y
Duncan-Wright-Wong de tres **1,44**.

Medido, 50 dovelas:

| método | corps_2 (pub. 1,35) | duncan_wright (pub. 1,44) |
|---|---|---|
| bishop_simplified | 1,3493 (−0,05 %) | 1,4455 (+0,38 %) |
| spencer | 1,3503 (+0,02 %) | 1,4444 (+0,30 %) |
| gle_morgenstern_price | 1,3506 (+0,04 %) | 1,4466 (+0,46 %) |
| lowe_karafiath | 1,3598 (+0,73 %) | 1,4579 (+1,24 %) |
| janbu_corrected | 1,3031 (−3,48 %) | 1,3836 (−3,92 %) |
| janbu_simplified | 1,2093 (−10,4 %) | 1,2744 (−11,5 %) |
| ordinary_fellenius | 1,1456 (−15,1 %) | 1,1098 (−22,9 %) |
| corps_engineers_1 | 1,3986 (+3,60 %) | 1,4919 (+3,60 %) |
| corps_engineers_2 | 1,4245 (+5,52 %) | 1,5196 (+5,53 %) |

**Sólo cuatro se comparan contra el valor publicado**, y no es una excusa
para los demás: exigir 1,35 a Fellenius sería exigir que Fellenius deje de
ser Fellenius. El método ordinario desprecia las fuerzas entre dovelas y
infravalora el factor en superficies circulares con presión intersticial alta
(Whitman y Bailey 1967; Duncan y Wright 2005), y Janbu simplificado es
justamente el que no lleva el factor de corrección f₀ de Janbu (1973) — que
es lo que se comprueba: el corregido tiene que quedar **más cerca** del valor
publicado que el simplificado, y queda. De los dos Corps se comprueba que
estén por encima de Bishop, porque la propia figura G-9 de la EM da un
Modified Swedish un 6,0 % por encima de Bishop sobre sus doce dovelas
publicadas.

El resto: regla 7 (el desembalse mueve el número y marca las 50 dovelas en
**los nueve**), que la etapa 1 sea el análisis drenado y la caída sea cosa de
la etapa 2, la guarda A98-1 por las tres puertas —`evaluate_circle`,
`evaluate_surface` y `run`—, que un proyecto **sin** desembalse siga
aceptando un método a pelo (todo test y todo ejemplo de este repositorio
construye su búsqueda a mano), los cinco motivos de
`check_drawdown_settings`, la estadística, y un método falso que devuelve la
columna vacía para comprobar que ya no se degrada.

### Dos cosas que salieron al escribirlos

**El círculo del enunciado no cabe en su propio talud.** El manual dice
R = 210 y el panel imprime 209,900. A 210 exactos el arco es **tangente a la
cimentación** en y = 0, así que el redondeo en coma flotante deja un trozo un
pelo por debajo del contorno externo y `leaves_soil_region` descarta el
círculo — correctamente. `test_drawdown_usace_v169` no se topaba con ello
porque llama al procedimiento directamente; estos tests entran por la
búsqueda, que es la puerta donde vive el defecto. Los dos radios se
diferencian en un 0,05 % y sus factores en un 0,04 %.

**La ordenación `corps < dww ≤ lk` no es estructural entera.** La segunda
mitad sí: Duncan-Wright-Wong **es** Lowe-Karafiath con el tope drenado
puesto, una función y una bandera, y el tope sólo puede restar. Dónde cae el
Corps no: lee una envolvente R donde los otros dos interpolan una de K_c = 1,
así que cuál sale menor depende de dónde se crucen las dos envolventes, y eso
depende de las tensiones de la etapa 1. Medido: el Corps es el menor de los
tres en ocho métodos y **el mayor en Fellenius** (1,1456 contra 1,1098 y
1,1434), cuyo factor de etapa 1 está un 14 % por debajo del de los demás. El
primer intento de test afirmaba el orden completo en los nueve y lo afirmaba
sin base; se ha quedado con lo que sí es una propiedad del código.

---

## 6 · Lo que rompió en la suite, que es la parte interesante

Cuatro tests de 2272, y **ninguno era un fallo del cambio**: los cuatro
midieron su consecuencia.

**Dos por el mismo motivo, y el motivo importa.** El defecto de `LEMMethod`
es `tolerance = 0.001`; el del proyecto, `settings.methods.tolerance`, es
**0.005**. Así que `build_method` no sólo añade el desembalse: aprieta o
afloja la convergencia a lo que el usuario configuró. `test_probabilistic` y
`test_sensitivity` construían su corrida «determinista» con la clase a pelo y
la comparaban con lo que devuelve el motor, y esas identidades se comprueban
a 1e-6:

```
test_values_match_an_independent_recomputation   0,8931799 vs 0,8928818
test_midpoint_reproduces_the_deterministic_factor  (misma causa)
test_sweeping_one_variable_does_not_move_the_others
```

Es decir: **la estadística llevaba corriendo a una tolerancia distinta de la
del análisis determinista del mismo proyecto**, y lo que lo tapaba era que
los tests reproducían el defecto a los dos lados de la igualdad. Los helpers
`_deterministic` de los dos archivos pasan a usar `build_method`, con lo que
«determinista» significa en el test lo que significa en el programa.

**El tercero** (`test_a_freely_draining_material_retains_no_excess`) compara
el factor con y sin `undrained_behaviour` sobre un modelo con desembalse, y
la variante sin marcar es justo la que `check_drawdown_settings` rechaza. El
rechazo no es nuevo: las dos puertas de entrada lo bloquean desde v0.1.68, y
lo que cambia es que ahora el motor está de acuerdo con ellas. El test mide
las presiones intersticiales, no los ajustes, así que construye
`BBarDrawdownMethod` directamente.

Y ahí aparece un matiz que el mensaje de rechazo no dice, anotado en el test
en vez de callado: **sin material sin drenar, una corrida B-bar sigue siendo
un análisis de verdad y sigue moviendo el número**, porque la carga del
embalse y las presiones son las del nivel bajo. Lo que no mueve es ninguna
*resistencia*, que es de lo que habla el mensaje.

---

## Lo que NO entra

- **El +3,6 % y el +5,5 % de Corps #1 y #2** frente al panel del problema 95.
  La ficha del banco ya tiene ese análisis con causa nombrada, y apunta a la
  atribución de la referencia, no al método.
- **Los problemas 96 y 98 del banco no tienen `.ogr` generado**, así que las
  cifras del encargo para ellos (1,4989 y 0,8830) no se pueden reproducir sin
  regenerarlos. La geometría del 96 es la del 95 con procedimiento DWW y
  sobre el círculo publicado da 1,4455 contra 1,44, **+0,38 %**.

## Archivos

| Archivo | Cambio |
|---|---|
| `ogr_slip2d/rapid_drawdown.py` | `drawdown_gap`, `performs_drawdown`, `PERFORMS_DRAWDOWN`, las dos negativas por columna corta, `wrap_for_drawdown` comprueba los ajustes, procedimiento desconocido nombrado |
| `ogr_slip2d/search.py` | la guarda en `BaseSearch._analyse` |
| `ogr_core/statistics/probabilistic.py` | `_make_method` por defecto = `build_method` |
| `ogr_core/statistics/sensitivity.py` | igual |
| `tests/test_drawdown_methods_v1108.py` | nuevo, 27 tests |
| `tests/test_probabilistic_v135.py`, `tests/test_sensitivity_v136.py` | su corrida «determinista» se construye con `build_method`, que es lo que hace ahora el motor |
| `tests/test_drawdown_bbar_v169.py` | la variante sin material sin drenar va por `BBarDrawdownMethod` directo |
| Los siete archivos de versión | 0.1.108 |
