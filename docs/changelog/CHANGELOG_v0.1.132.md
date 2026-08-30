# OGR Slip2D v0.1.132

**El recocido paraba en 3 pasadas sin mejora, el usuario podía escribir
cuántas quería, y el número que escribía no lo leía nadie.**
`SearchSettings` declaraba `sa_num_fos_compared_before_stopping = 5`, el
diálogo de opciones de superficie lo enseñaba, lo escribía y lo guardaba en
el `.ogr`, y `_vfsa` cortaba el bucle con un `no_improve_passes >= 3`
escrito a mano. Ni una sola lectura del campo en todo `ogr_slip2d`.

Cierra **D07c(a)** del banco de verificación, el primero de los tres que el
inventario de ajustes de v0.1.103 dejó señalados sin arreglar. Es la
**regla 7** en su forma más pura: un control configurable que no afecta al
resultado es peor que no tenerlo, porque el usuario cree que el análisis lo
respeta.

Lo que merece recordarse no es el arreglo —tres líneas— sino tres cosas que
salieron al medirlo: **el signo que el defecto afirmaba es falso**, el valor
por defecto del paper **no puede dispararse** con el presupuesto por defecto
del motor, y hay una **quinta desviación** del paper que se reporta y no se
toca.

---

## 1 · De dónde salen el significado y el 5

No hubo que inventar ninguno de los dos: los dos están escritos en el paper
de la formulación, Su, X. (2009), *Global Optimization of General Failure
Surfaces in Slope Analysis by Hybrid Simulated Annealing*, University of
Waterloo, que está en
`referencias/Documentacion_Guia/Search_Option_Surface/`.

**Sección 2.1.7, «Stopping Criterion»** (p. 19):

> The values of f_opt[k] are compared with f_opt[k − j], where j is an
> integer between 0 and n_ε. If the difference f_opt[k] − f_opt[k − j] <
> f_tol for all j, the search is stopped… In other words, if there has not
> been any visible improvement for the global optimum in the previous n_ε
> consecutive runs, the algorithm is to be stopped.

El `no_improve_passes >= N` de OGR **es** exactamente ese criterio, así que
el ajuste **es** n_ε y no hay ningún desfase de uno que negociar. Esa era la
duda razonable —«número de factores comparados» podían ser n_ε+1 valores— y
la resuelve la segunda frase del párrafo, no el razonamiento.

**Sección 3.1** (p. 26), los parámetros con los que el paper corrió sus
casos de verificación:

> VFSA: Ngen = 1000n …, c = 8, T_in = 1.0, with stopping criterion N_ε = 5
> … A safety factor tolerance of 1e-06 was used, and a stopping criterion
> tolerance of 1e-04 was chosen.

De ahí sale el 5 que el campo ya declaraba (y el `sa_tolerance = 1e-4`). El
3 no salía de ningún sitio.

## 2 · Lo que se cambió

- `SimulatedAnnealingSearch.__init__` acepta
  `num_fos_compared_before_stopping`, **por defecto 5**, pinzado a ≥ 1
  («menos de 1 no es un criterio: pararía sin haber comparado nada»).
  Mismo patrón que `temperature_coefficient` en v0.1.103: el nombre del
  ajuste sin el prefijo `sa_`, para no crear un séptimo par de nombres.
- El criterio de parada lee el atributo.
- `build_search` pasa el ajuste. Era el **único** `sa_*` que faltaba en esa
  llamada; los otros cinco ya estaban.
- La interfaz no se tocó: ya leía, escribía y restauraba el campo.
- `tests/test_settings_coverage_v1103.py` — el inventario congelado de
  campos sin lector adelgaza en uno. Ese test compara el conjunto exacto en
  las dos direcciones, así que se pone rojo tanto si aparece un campo nuevo
  sin lector como si uno de la lista gana lector y nadie lo saca: cerrar el
  defecto **obliga** a tocarlo.

## 3 · Qué le hace al número, medido

A/B en el mismo proceso, espalda con espalda, cinco semillas, 300 pasos de
generación, Optimize Surfaces activo (lo que da un proyecto de recocido
desde v0.1.119). n_ε = 3 es lo que hacía el código; n_ε = 5 es lo que hace
ahora:

| modelo | semilla | n_ε = 3 | n_ε = 5 |
|---|---|---|---|
| talud D22 (Bishop) | 1234 | 1,0990 | 1,0990 |
| | 2024 | 1,0998 | 1,0998 |
| | **7** | **1,0808** | **1,0927** |
| | 99 | 1,1117 | 1,1117 |
| | 31337 | 1,0788 | 1,0788 |
| caso 002 (Spencer) | **1234** | **1,3325** | **1,3317** |
| | 2024 | 1,3295 | 1,3295 |
| | **7** | **1,3416** | **1,3394** |
| | 99 | 1,3298 | 1,3298 |
| | **31337** | **1,3397** | **1,3385** |

Se mueven 4 de 10; el mejor de las cinco semillas **no cambia** en ninguno
de los dos modelos (1,0788 y 1,3295).

**Y con eso, el signo que el enunciado del defecto daba por seguro es
falso.** El encargo decía que alargar la búsqueda sólo puede bajar el factor
o dejarlo, de modo que el defecto era «inseguro» sin más. Las tres del caso
002 sí bajan, pero **la del talud D22 sube un 1,1 %** con el mismo número de
evaluaciones (554 → 555). No es una anomalía: el recocido es estocástico y
la fase local arranca donde la global la deja, así que parar en otro sitio
es descender por otra cuenca. Es la misma no monotonía que
`docs/PENDIENTES.md` §0b tiene medida para `generation_steps`. La dirección
del error sigue siendo la que dice el encargo **en promedio**, pero no
seguro por seguro, y esa diferencia es la que separa un argumento de una
medición.

## 4 · El hallazgo estructural: el defecto del paper no siempre puede dispararse

Contando las pasadas externas con `progress_cb` (300 pasos, sin
optimización, semillas 1234/2024/7/99):

| n_ε | dónde para |
|---|---|
| 2 | pasada 2, 2, 2 y 5 |
| 3 | sólo la semilla 7, en la pasada 3 |
| 5 | ninguna |
| 20 | ninguna |

Ninguna semilla para con n_ε = 5 porque el bucle externo sólo tiene
`K = max(4, generation_steps / 50)` pasadas — seis con 300 pasos. **El
criterio sólo muerde mientras n_ε < K**, y con el defecto del motor
(200 pasos, K = 4) el N_ε = 5 del paper **no puede dispararse jamás**: el
bucle se agota antes. No es un defecto nuevo del ajuste, es la misma cuerda
que §0b tiene tirante —`generation_steps` gobierna a la vez las pasadas
externas y el presupuesto del LMC—, y queda anotada allí.

Por eso el test de la regla 7 **no** contrasta 3 contra 5: §0b ya había
medido que 5 no movía dos de tres semillas, y ahora se sabe por qué.
Contrasta **2 contra 20**, que mueve las tres semillas del test, y añade una
comprobación determinista que no depende de la suerte: hasta que la n_ε
pequeña corta, las dos corridas son idénticas bit a bit, así que la pequeña
**nunca** puede dar más pasadas que la grande y tiene que dar menos al menos
una vez.

## 5 · Regla 6: una quinta desviación del paper, reportada y sin tocar

`docs/PENDIENTES.md` §0c lleva cuatro desviaciones medidas frente a Su
(2009). Ésta es la quinta, encontrada al leer §3.1 para el valor por
defecto: el paper usa **dos** tolerancias distintas —`f_tol` = 1e-4 para la
parada y 1e-6 para el factor de seguridad— y `_vfsa` usa `self.tolerance`
para las dos cosas: decide qué cuenta como mejora del óptimo y decide la
parada. Con el defecto del proyecto (1e-4) eso significa que **una mejora de
menos de 1e-4 no se guarda como mejor superficie**, cuando el paper la
guardaría y sólo no la contaría para parar. No se ha medido su efecto y no
se toca aquí.

## 6 · Qué se probó

- `tests/test_annealing_stopping_v1132.py`, nuevo: el ajuste llega, el
  defecto es el del paper en los dos sitios, menos de 1 se pinza, el
  criterio corta el bucle antes y **mueve el número** (regla 7).
- Suite entera sin argumentos: **2909 pruebas, 0 fallos**.
- El caso `002-yamagami-ueta-1988` sigue dentro de la banda publicada
  (Yamagami y Ueta 1,338–1,348; Greco 1,327–1,333):
  `test_annealing_inequality_v1119` pasa.
- Banco de verificación: `generar_comparativa.py` deja
  `COMPARATIVA_Slide2_vs_OGR.md` y `PROGRESO.md` **idénticos byte a byte**
  (mismo md5 antes y después). Conviene decir qué prueba y qué no: esa
  herramienta **reconstruye la tabla desde los `resultados.json`
  guardados**, no vuelve a ejecutar el motor, así que lo que garantiza es
  que no se ha tocado el dato. Que ninguna fila **pueda** moverse se apoya
  en otras dos cosas, medidas: ningún modelo del banco usa Simulated
  Annealing —contados los `search_method` de los 563 `.ogr` del árbol del
  manual: 420 `grid`, 96 `path`, 18 `particle_swarm`, 17 `block`, 12
  `auto_refine` y **cero** `simulated_annealing`— y
  `SimulatedAnnealingSearch` **no tiene subclases**, de modo que el cambio
  no tiene por dónde llegar a otra búsqueda.
