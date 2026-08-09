# OGR Slip2D v0.1.70 — el nivel de desembalse crítico, y el tope drenado convergido

Las tres cosas que v0.1.69 dejó anotadas. Medidas antes de tocar nada, y
la medición cambió el orden de importancia: **dos eran reales, una ya
estaba cerrada, y por el camino apareció una opción de la interfaz que
llevaba tiempo reventando.**

> **AVISO PARA PROYECTOS CON DESEMBALSE MULTIETAPA.** El tope drenado
> pasa a iterarse hasta converger. Los factores de seguridad de los
> procedimientos Corps y Duncan-Wright-Wong **suben ligeramente** —en los
> casos publicados, entre un +0.05 % y un +1.2 %— y se acercan a los
> valores de referencia. Lowe-Karafiath no lleva tope y no cambia.

---

## 1. El desembalse total no siempre es el caso crítico

Lo anotado era una sospecha. La documentación de referencia contiene
**los dos comportamientos opuestos**, que es lo que zanja la cuestión:

* Verificaciones #100/#101 (Morgenstern 1963, talud homogéneo): el
  desembalse **total** es el peor, 1.20 frente a 1.41 a media altura.
* Tutorial 13, pág. 13-9, literal: *«For this example, the minimum safety
  factor at partial drawdown is lower than the minimum safety factor at
  full drawdown […] For this particular model, a minimum safety factor
  therefore exists at some intermediate drawdown level.»* El mecanismo
  que da es el espaldón granular drenante: con el embalse vacío drena a
  presión intersticial nula, pero un desembalse parcial le deja un nivel
  freático dentro cerca del pie.

Reproducido construyendo esa presa zonada (núcleo no drenado B̄ = 1 +
espaldón granular drenante aguas arriba), barrido fino:

| Nivel final | 0 | 10 | 20 | **30** | 40 | 50 | 70 | 90 |
|---|---|---|---|---|---|---|---|---|
| FS crítico | 1.4803 | 1.3810 | 1.3085 | **1.3043** | 1.3488 | 1.4002 | 1.5913 | 1.9240 |

Analizar solo el desembalse total reporta **1.4803** cuando el peor caso
real es **1.3043**: un **11.9 % del lado inseguro**. Y el círculo crítico
no es el mismo: se muda del pie hacia arriba.

El programa de referencia no lo resuelve tampoco — solo admite una línea
de desembalse, la línea de desembalse no está entre sus variables de
sensibilidad, y el desembalse rápido es excluyente con el transitorio.
Su tutorial construye tres archivos a mano.

### El camino equivocado, que casi se toma

`run_sensitivity` ya barre un parámetro y grafica FS. Reutilizarlo
habría sido un error, y de los caros: **fija la superficie crítica** y
solo la reevalúa. Medido sobre la presa zonada, sosteniendo la superficie
del desembalse total:

| Nivel | Barrido | Superficie fija | Exceso |
|---|---|---|---|
| 100 | 2.0248 | 2.6539 | **+31.1 %** |
| 67 | 1.5505 | 1.8072 | +16.6 % |
| 33 | 1.3244 | 1.3452 | +1.6 % |
| total | 1.4887 | 1.4887 | +0.0 % |

Lo insidioso es la última fila: **el error se anula exactamente donde se
encontró la superficie**, así que el único nivel que un usuario
comprobaría a mano concuerda a la perfección. Hay un test que mide esto y
que existe para que nadie «simplifique» el barrido convirtiéndolo en una
variable de sensibilidad.

### Lo que se ha añadido

`run_drawdown_sweep` (`ogr_core/statistics/drawdown_sweep.py`) **repite
la búsqueda completa en cada nivel**. Es caro y es el precio de que la
respuesta sea correcta; `run_overall_slope` paga lo mismo por la misma
razón, y de él se toma el arreglo de `search_factory` para que `ogr_core`
siga sin importar `ogr_slip2d`.

`project_at_level` (`ogr_core/hydraulic/drawdown_levels.py`) mueve la
línea de desembalse **rígidamente**: una línea inclinada conserva su
forma y solo cambia su cota media, como hace `_shift_water_table` con el
nivel freático. Si no hay línea dibujada la sintetiza, porque el proyecto
sin línea es justamente aquel cuyo usuario solo ha visto la respuesta del
desembalse total.

En la interfaz: **Groundwater → Barrido de niveles de desembalse**,
habilitado solo con desembalse rápido activo. Corre en un `QThread` con
barra de progreso —no como `_compute_statistics`, que congela la ventana—
y reutiliza `_ComputeWorker.build_search` para respetar la búsqueda que
el usuario configuró. El resultado sale en una gráfica de FS frente a
cota y un mensaje que dice cuánto sobrestimaría analizar solo el total.

---

## 2. El tope drenado, convergido

Iterar el tope **oscila** con amplitud decreciente en vez de converger de
forma monótona (apéndice G, Corps: 1.3335 → 1.3638 → 1.3412 → 1.3548 →
… → 1.3494). Con subrelajación

```
τ ← (1−ω)·τ + ω·min(τ_no drenada, τ_drenada(σ'_posterior))
```

la oscilación desaparece. **La medición que importa no es la velocidad
sino que el punto fijo no depende de ω**, que es lo que convierte el
valor convergido en una propiedad del modelo y no de la constante:

| ω | Ap. G Corps | Ap. G DWW | Pilarcitos Corps |
|---|---|---|---|
| 1.00 (sin amortiguar) | 1.3493 (18 pasadas) | 1.4455 (16) | 0.8656 (40, sin converger) |
| **0.70** | **1.3494 (9)** | **1.4456 (8)** | **0.8658 (6)** |
| 0.50 | 1.3495 (12) | 1.4457 (11) | 0.8658 (4) |
| 0.35 | 1.3496 (16) | 1.4458 (14) | 0.8658 (5) |

Resultado sobre los casos publicados:

| Caso | 1 pasada | Convergido | Programa de referencia | Árbitro |
|---|---|---|---|---|
| Ap. G Corps, círculo fijo | 1.3335 (−1.0 %) | **1.3494 (+0.18 %)** | 1.347 | 1.35 |
| Ap. G DWW, círculo fijo | 1.4333 (−0.67 %) | **1.4456 (+0.18 %)** | 1.443 | 1.44 |
| Pilarcitos Corps, mínimo | 0.8379 | 0.8383 | 0.823 | 0.824 |
| Pilarcitos DWW, mínimo | 1.0822 | 1.0847 | 1.043 | 1.05 |

Que el valor convergido coincida con el programa de referencia a
**+0.18 % en los dos casos del apéndice G** es difícil de atribuir al
azar. En Pilarcitos no cambia nada porque allí el tope apenas muerde —
que es también por lo que Pilarcitos no podía haber detectado esto.

**Lo que dice la referencia, y hay que decirlo**: describe exactamente
tres etapas y **una sola** re-ejecución (*«the analysis is rerun»*, en
singular), el método se llama literalmente «3 stage», y no hay criterio
de convergencia ni mención de iteración en toda la ayuda. Se adopta la
versión convergida porque reproduce mejor los dos casos publicados, y
tanto eso como lo que dice la referencia quedan escritos en el docstring
de `CAP_RELAXATION`.

Dos detalles que son decisiones:

* El tope se toma **siempre contra la resistencia no drenada original**,
  nunca contra la ya topada: realimentar la topada la haría descender sin
  fondo en vez de asentarse en `min(no drenada, drenada)`.
* Por eso cada iterado es una combinación convexa de la no drenada y algo
  que no la supera, así que `τ ≤ τ_no drenada` en toda pasada y
  **`FS_DWW ≤ FS_LK` sigue siendo estructural**.

Los tres procedimientos quedan diferenciándose en una sola cosa cada uno:

| Procedimiento | Envolvente no drenada | Tope drenado |
|---|---|---|
| Lowe y Karafiath (1960) | Kc = 1 interpolada por K_c | no |
| Duncan, Wright y Wong (1990) | ídem | sí, convergido |
| Cuerpo de Ingenieros (1970) | R directa | sí, convergido |

---

## 3. La contradicción 103/110 ft — cerrada sin trabajo

Ya estaba medida en v0.1.69 (0.5 % de diferencia, un orden de magnitud
por debajo del acuerdo que se reclama) y el test lo comprueba en vez de
suponerlo. **No se ha tocado nada**, y eso es el resultado: una deuda que
se cierra midiendo, no escribiendo código.

---

## 4. Hallazgo colateral: una opción de la interfaz que reventaba

`MultiLineDialog` leía `self.fig`, que la clase base no define — es
`self.figure`. **Toda** construcción lanzaba `AttributeError`. Su único
uso es *Show Values Along Surface* de la ventana de interpretación, y esa
llamada se protegía con `except ImportError`, que no captura eso: la
opción salía con una excepción no controlada en vez de caer a su tabla de
texto.

Llevaba así desde que se escribió el diálogo, porque **ningún test
construía uno**. Ahora hay un archivo que construye los siete diálogos de
gráfica del módulo, y el `except` se ha ampliado: los números son lo que
el usuario pidió, la gráfica es solo cómo se enseñan.

---

## Archivos

| Archivo | Qué cambia |
|---|---|
| `ogr_core/statistics/drawdown_sweep.py` | **Nuevo.** El barrido, con re-búsqueda por nivel |
| `ogr_core/hydraulic/drawdown_levels.py` | `project_at_level`, `model_x_span`, `ground_elevation_span` |
| `ogr_slip2d/rapid_drawdown.py` | El tope drenado como punto fijo amortiguado; `CAP_RELAXATION` |
| `ogr_core/materials/drawdown_envelopes.py` | Docstring de `composite_strength`: por qué se itera |
| `ogr_gui/main_window.py` | `_DrawdownSweepWorker`, la acción, el diálogo y la gráfica |
| `ogr_gui/dialogs/chart_dialogs.py` | `MultiLineDialog` arreglado |
| `ogr_gui/interpret_window.py` | El `except` que solo capturaba `ImportError` |
| `tests/test_drawdown_sweep_v170.py` | **Nuevo.** Los dos taludes, y la trampa de la superficie fija |
| `tests/test_chart_dialogs_v170.py` | **Nuevo.** Los siete diálogos se construyen |
| `tests/test_rapid_drawdown_v168.py` | El punto fijo no depende de ω |

## Coste

**El cronómetro no sirvió, y el error fue el que ya está documentado.**
Se midió un A/B en el mismo proceso mientras la suite completa corría de
fondo: las dos corridas de control difirieron un **173 %** entre sí, o
sea que la medida no resuelve nada. Es exactamente la trampa que
AGENTS.md registra —dos procesos peleándose por los mismos núcleos— y se
cayó en ella otra vez.

Manda entonces **contar el trabajo añadido**, que no depende de la
máquina. Sobre la rejilla de Pilarcitos (729 candidatos, 185 superficies
válidas), evaluaciones LEM de la etapa 2 en adelante:

| Procedimiento | v0.1.69 | v0.1.70 | Factor | Pasadas (media / máx) | Sin topar |
|---|---|---|---|---|---|
| Duncan-Wright-Wong | 266 | 700 | **×2.63** | 2.8 / 20 | 104 de 185 |
| Cuerpo de Ingenieros | 271 | 798 | **×2.94** | 3.3 / 20 | 99 de 185 |

Más de la mitad de las superficies **no pagan nada**: si el tope no
muerde en ninguna dovela, se sale sin resolver de nuevo, que era el
camino rápido de antes y se ha conservado a propósito.

| Archivo | Coste | Qué lo domina |
|---|---|---|
| `test_drawdown_sweep_v170.py` | ~20 s | 2 barridos × 5 niveles × 1 búsqueda |
| `test_chart_dialogs_v170.py` | < 1 s | construir diálogos sin mostrarlos |

El barrido es intrínsecamente N búsquedas. Su rejilla de test es la más
barata que **sigue resolviendo el mínimo intermedio** (3 × 4 centros,
pasos de radio de 70 ft, 18 dovelas), y cada barrido se calcula una vez y
lo comparten todos los tests que lo leen — el mismo truco que bajó un
archivo de filtración de 48 s a 12 s.

---

## Lo que queda anotado

* **El barrido no busca el nivel crítico, lo tabula.** Con pocos niveles
  el mínimo cae entre dos puntos y se subestima la caída. Un refinamiento
  alrededor del mínimo (sección áurea sobre la cota) daría el mismo
  resultado con menos búsquedas, y no se ha hecho.
* **El barrido usa la misma rejilla de búsqueda en todos los niveles.**
  Como el círculo crítico se muda hacia arriba con el nivel, una rejilla
  centrada en el crítico del desembalse total puede quedarse corta en los
  niveles altos. No se ha medido cuánto importa.
* **Algunas superficies agotan el presupuesto de 20 pasadas.** En la
  rejilla de Pilarcitos son 8 de 185 con DWW y 12 de 185 con el Corps.
  **Ninguna es crítica ni se le acerca**: la más baja de ellas da 1.2547
  frente a un crítico de 1.0847 (DWW) y 1.0035 frente a 0.8383 (Corps),
  y los críticos convergen en 4 pasadas. Así que el mínimo reportado no
  depende de ellas — pero no se ha investigado por qué esas oscilan más,
  y `n_cap_passes` está en el resultado precisamente para que se vea.
* **La cancelación sigue sin implementarse.** `ComputeProgressDialog`
  tiene botón Cancel y bandera `cancelled`, y **nadie la consulta** — ni
  el barrido nuevo ni el `_ComputeWorker` que ya existía. En un barrido
  largo eso se nota mucho más que en un cálculo normal.
