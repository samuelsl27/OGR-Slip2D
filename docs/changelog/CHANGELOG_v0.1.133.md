# OGR Slip2D v0.1.133

**El panel del Auto Refine anunciaba 1 000 superficies para una búsqueda
que genera 4 500.** El rótulo calculaba `divisiones × círculos ×
iteraciones`; el generador recorre los **pares** de divisiones,
`C(d,2) × círculos` por iteración. Un factor **4,5** con los valores por
defecto, y creciente: con 20 divisiones el rótulo decía 2 000 para una
búsqueda de 19 000.

Cierra **D07c(c)** del banco de verificación, el segundo de los tres que el
inventario de ajustes de v0.1.103 dejó señalados. **No mueve ningún factor
de seguridad** —es una cifra de pantalla—, pero quien dimensiona su
búsqueda por ella la dimensiona 4,5 veces corta y estima un coste que no va
a pagar.

Lo que merece recordarse no es la fórmula, que estaba a un `math.comb` de
distancia, sino tres cosas que aparecieron al mirar la referencia y el
código: **el rótulo, además de equivocado, estaba congelado**; la segunda
línea del rótulo **es texto real de la referencia y no está definida en
ninguna parte**; y **generadas no es analizadas**, así que la cifra
correcta sigue siendo una cota superior.

---

## 1 · De dónde sale el 4 500

De la propia guía de la referencia, que publica las dos fórmulas como
imágenes junto al texto (`Documentacion_Guia/Search_Option_Surface/`, y las
mismas en `WebHelp/image/model/equations/eq_autoref1.gif` y
`eq_autoref2.gif`):

| | |
|---|---|
| círculos por iteración | `y·x(x−1)/2` |
| total | `z·( y·x(x−1)/2 )` |

con `x` = divisiones a lo largo del talud, `y` = círculos por división y
`z` = número de iteraciones. Y en prosa, dos afirmaciones que sirven de
anclaje externo:

> The default values of x, y and z (10, 10, 10) often give good results.
> (This generates **4500** circles). […] the number of circles generated,
> is proportional to the **SQUARE** of the number of Divisions Along Slope.

El generador de OGR ya recorría los pares (`for i … for j in range(i+1, …)`
en `AutoRefineSearch._run`), así que el que contaba mal era el rótulo, y el
test contrasta contra esa aritmética publicada, no contra lo que OGR
imprime hoy.

## 2 · Lo que se cambió

- **`AutoRefineSearch.surfaces_per_iteration(d, c)`** y
  **`AutoRefineSearch.surfaces_generated(d, c, it)`**, al lado del bucle
  que genera la población y con los mismos pinzados que `__init__`
  (divisiones ≥ 2, el resto ≥ 1), para que la cifra responda por la
  búsqueda que de verdad se construiría.
- **`AutoRefineSearch._run` cuenta lo que intenta**: `result.attempts += 1`
  por candidato, antes de que la construcción pueda fallar.
  `SearchResult.attempts` ya significaba exactamente eso —«generation
  attempts made»— y no lo escribía nadie en esta búsqueda. Es lo que
  permite contrastar el número publicado contra una corrida real **sin
  parchear nada**: sin él, el test compararía una fórmula con otra fórmula,
  que es el defecto que se está cerrando.
- **El rótulo se deriva de ahí** (`_sync_ar_total` en `grid_dialogs.py`),
  y ya no hay ninguna fórmula paralela en la interfaz.
- **El rótulo sigue lo que el usuario teclea**: los tres `QSpinBox` están
  conectados a `valueChanged`.
- Las dos líneas y el tooltip pasan por `tr()`, con sus entradas en
  español; eran una f-string sin envolver.
- `tests/test_auto_refine_count_v1133.py`, 12 tests.

## 3 · Los tres hallazgos

### a) «Number of Surfaces Interpreted: 45» existe, y no está definido

La ficha del banco decía que el panel de la referencia publica dos líneas,
`Number of Surfaces Computed: 4500` y `Number of Surfaces Interpreted: 45`.
**Lo dudé al no encontrar la segunda en ninguna página de la ayuda**, y la
ficha tenía razón: las capturas del diálogo —panel circular y panel no
circular— la enseñan, y con esos mismos valores.

Lo que no aparece por ninguna parte es **qué es**. No está en la ayuda
antigua, ni en el espejo de la documentación actual, ni en el artículo de
métodos de búsqueda, ni en la web. Con el único punto de dato disponible
(10/10/10 → 45) coincide con `C(x,2)`, el número de pares de divisiones,
pero **un punto no fija una fórmula**, y ninguna lectura de ella describe
algo que OGR haga: OGR conserva **todas** las superficies evaluadas, no una
por par de divisiones, y cuántas conserva no se sabe hasta después de
correr.

Reproducir ese «45» habría sido reponer el mismo defecto con otro número.
La segunda línea pasa a ser **superficies por iteración** (450), que es la
otra magnitud que la referencia sí publica con fórmula y que OGR sí
calcula.

### b) El rótulo estaba congelado

No había ningún `valueChanged` conectado: la cifra se escribía una vez, al
construir el panel, con los valores que el proyecto traía. Cambiar las
divisiones de 10 a 20 no la movía. La referencia, en cambio, dice que el
número se muestra «as you enter the Auto Refine Search parameters», y es lo
único que hace útil un rótulo así. La ficha del defecto no lo mencionaba.

### c) Generadas no es analizadas, y la diferencia es grande

Un par y ángulo cuya construcción no tiene centro válido, y un círculo que
un foco rechaza, se saltan **sin contarse**. Medido:

| modelo | generadas | analizadas |
|---|---|---|
| problema 14 del banco (10/10/10) | 4 500 | **3 300** |
| talud del test (10/10/2) | 900 | 701 |
| talud del test (6/2/3) | 90 | 53 |

Así que el número correcto sigue siendo una **cota superior**, y el rótulo
lo dice en su tooltip. Sin esa frase, el usuario que compare las 4 500
anunciadas con las 3 300 del informe abre este mismo defecto otra vez.

## 4 · Por qué no se llama `total_count`

Porque ese nombre ya está ocupado por otra magnitud: `SearchResult.
total_count` es la población **analizada** (válidas + inválidas), que es la
que el banco de verificación registra como `generadas` en sus
`resultados.json`. Dos magnitudes distintas con el mismo nombre son el
defecto siguiente, y aquí se diferencian en un 27 % en el problema 14.

## 5 · Lo que no se ha movido

Ninguna población real y ningún factor de seguridad: el generador no se ha
tocado más que para llevar la cuenta de sus propios intentos, que no pasa
por `valid_count` ni por `invalid_count`. Los siete problemas del banco que
usan Auto Refine (14 a 20) conservan sus `generadas` exactas —14 → 3300,
15 → 3584/3474/3587, 16 → 3300, 17 → 3365, 18 → 8619, 19 → 6589,
20 → 18491— y `COMPARATIVA_Slide2_vs_OGR.md` y `PROGRESO.md` quedan
idénticos byte a byte.

Coste del `attempts += 1`: un incremento entero por candidato, frente a la
construcción y evaluación de un círculo por candidato. No es medible con el
cronómetro de la suite, que varía ±40 s entre corridas idénticas; manda el
razonamiento sobre el trabajo añadido.

## 6 · Qué se probó

- `tests/test_auto_refine_count_v1133.py` — 12 tests: la aritmética
  publicada (450 / 4 500 / 19 000), que es cuadrática, que no es
  `d × c × it`, el pinzado; dos juegos de valores corridos de verdad
  (4/3/2 → 36 y 6/2/3 → 90) contra `attempts`; la variante no circular
  generando lo mismo; el rótulo llevando los números del motor con **dos**
  juegos sobre el mismo diálogo (lo que fija también la actualización en
  vivo); el bucle diálogo → ajustes → búsqueda; y generadas ≥ analizadas.
- Suite entera sin filtrar, en `offscreen`.
- Banco: `generar_comparativa.py` y el recuento de `generadas` de los
  problemas 14 a 20.
