# OGR Slip2D v0.1.269

**El permanente no saturado publica su historia de convergencia, y
*Iteration History…* y *Convergence Plot…* la dibujan (D265).** Las dos
entradas del menú *Groundwater* de la ventana de interpretación existían
desde v0.1.53, se podían pulsar y nunca habían enseñado nada: leían
`notes["history"]`, una clave que nadie escribía. Un test fijaba el agujero.
Ningún número del motor cambia: la serie se lee de las cargas y no las toca.

## 0. Lo que se encontró

- **El bucle ya calculaba la serie y la tiraba.** `solve_unsaturated` metía
  el cambio de cada pasada en una lista local y publicaba solo el último
  (`picard_delta`).
- **Ese cambio es el RELAJADO**, ω·max|H_nuevo − H|, y es con el que se para
  el bucle (D267). Publicarlo tal cual habría hecho que la gráfica dependiera
  de ω. La serie publicada es el cambio **sin relajar**, max|H_nuevo − H|, que
  es lo que pide el propio mapa de Picard.
- **Un bucle convergido termina POR ENCIMA de la tolerancia** en esa medida.
  En la presa de Gardner (ω = 0,4, tol 1e-5) la última entrada es 1,6e-5: el
  bucle se para cuando el relajado baja de tol, o sea cuando el sin relajar
  baja de tol/ω = 2,5e-5. Por eso la línea que dibuja *Convergence Plot* es
  **tol/ω**, el umbral real de parada, y no tol, que haría parecer no
  convergida una corrida que sí lo está.
- **El rescate de 0.1.266 (D124) mide otra cosa en cada camino.** Anderson
  evalúa el mapa en cada paso y su residuo max|G(H) − H| es la misma magnitud
  que la del bucle, así que entra entera. La continuación con Newton resuelve
  problemas intermedios (kr elevado a t < 1); sus correcciones no son
  comparables, y de ella solo entra el residuo final.
- **Las dos ventanas pintaban la misma serie con dos rótulos**: «Maximum
  change» y «Residual». No es un residuo. Ahora *Iteration History* la dibuja
  en escala lineal, con una serie por tramo (bucle y caminos del rescate), y
  *Convergence Plot* en escala logarítmica con las líneas de parada del bucle
  (tol/ω) y del rescate (tol).
- **`_json_safe` dejaba pasar NaN e inf.** `json.dumps` los acepta por defecto
  y escribe `NaN`, que no es JSON, en un `.ogr` declarado JSON puro: un
  `picard_delta` de un bucle que no llegó a correr o el residuo de un rescate
  cuyo último solve falló (inf). Ahora se escriben como `null`; el resultado
  en memoria no cambia.
- **Las ventanas de interpretación leen siempre el campo gobernante**, que en
  un transitorio es la última etapa: no tienen selector de etapa. Por eso cada
  etapa lleva la historia de **su último paso**, con el mismo significado.

## 1. Qué cambia

### Motor (`ogr_fem2d/solvers/seepage.py`)

- `solve_unsaturated` publica, documentado en su docstring:
  - `notes["history"]`: una entrada por pasada, el cambio sin relajar, a
    cuatro cifras (None donde no hay número); detrás, el rescate si corrió;
  - `notes["history_segments"]`: `[nombre, primer índice]` de cada tramo
    (`picard`, `anderson <profundidad>`, `continuation`);
  - `notes["tolerance"]`.
- `picard_delta` conserva su significado: el último cambio RELAJADO, mientras
  D267 siga abierta.
- `_rescue` y `_anderson` devuelven además su parte de la serie.
- `TransientSeepageSolver.step` deja la historia de sus pasadas, la
  tolerancia y la relajación en las notas de su última solución lineal, que
  es el resultado de la etapa. La tupla que devuelve no cambia (la desempaquetan
  los tests de Celia y de retención).
- `SeepageResult._json_safe` escribe como `null` todo número no finito, a
  cualquier profundidad de listas y diccionarios.

### Interfaz (`ogr_gui/interpret_window.py`)

- `_plot_xy` admite `yscale`. Dibujar log₁₀ de los valores habría convertido
  un cambio nulo en −∞.
- *Iteration History* y *Convergence Plot* como se describe arriba; la
  vuelta al resumen (`_info`) queda para los resultados que no traen historia
  (un `.ogr` anterior o un solve lineal).
- Rótulos nuevos con `tr()` y su entrada en español; «Maximum change» y
  «Residual» se retiran del diccionario porque nadie los usa ya.

### Banco

- `_tools/ejecutar_filtracion.py` no copia a `resultados.json` las notas que
  son listas: recortadas a 200 caracteres no son nada.

## 2. Tamaño en el `.ogr`

La historia viaja con las notas, entera. Medido con el redondeo a cuatro
cifras: 1000 pasadas ocupan 9,8 KB, entre el 16 y el 33 % de un campo de
800–1700 nodos. Con los presupuestos por defecto (200 pasadas, 300
evaluaciones de Anderson) el máximo ronda las 500 entradas (~5 KB), y lo
habitual son 20–70 (menos de 1 KB). Una etapa transitoria guarda como mucho
`max_picard` entradas (30 por defecto, 300 B) junto a su propio campo. No se
recorta.

## 3. Tests

- `tests/test_picard_history_v1269.py` (11 casos; los 11 fallan con 0.1.268):
  - una entrada por pasada en la presa de Gardner, y la identidad
    `history[-1]·ω = picard_delta` a cuatro cifras;
  - la última entrada de un bucle convergido queda entre tol y tol/ω;
  - el rescate (con `max_iterations=1`) marca su tramo, tiene una entrada por
    evaluación y acaba por debajo de tol;
  - la historia sobrevive a `to_dict`/`from_dict`, y un `.ogr` con notas no
    finitas sigue siendo JSON;
  - una etapa transitoria trae la historia de su último paso;
  - las dos entradas del menú van a `_plot_xy` (con `_info` y `_plot_xy`
    sombreados en la instancia) con la serie, los tramos y las líneas de
    parada, y la ventana real se abre.
- `test_interpret_i3_v153::test_iteration_history_has_no_recorded_series`
  **cambia a propósito**: pasa a llamarse
  `test_iteration_history_is_recorded_and_drawn` y exige lo contrario.

Suite entera: **5747 de 5747**.

## 4. A/B: cero dígitos

Un cambio sin interruptor no se mide apagado y encendido en el mismo proceso:
se compararon dos árboles, cada uno en su proceso, con
`_auditoria/P6_0269/ab_arbol.py` del banco (nuevo, reutilizable). El script
quita el buscador de la instalación editable y comprueba con un `assert` de
qué árbol sale `ogr_fem2d`.

- **Filas:** el 05 entero, con todas las variantes y las dos mallas (60); el
  02-010; el 02-038 en sus tres alturas y cuatro curvas (12); y la presa del
  102, permanente a 3000 elementos y desembalse a 700.
- **Resultado:** 75 filas, **0 distintas**. Las cargas son iguales al bit, y
  `converged`, `iterations` y las notas viejas no cambian. Las únicas claves
  nuevas son `history`, `history_segments`, `tolerance` y `relaxation` (esta
  última en las etapas transitorias).

## 5. Cierre en el banco

`d265()` en el `verificar_cierres.py` de la raíz. Corre la presa de Gardner
(27 pasadas, 27 entradas), busca un test que llame a `_gw_iteration_history`
y compruebe `_plot_xy`, y exige que `test_interpret_i3_v153` ya no fije el
agujero. Veredicto: **CUBIERTO POR TEST**. D265 retirada.

La cadena de P6 cambia de orden (plan aprobado):
`D268 → D270 → D267 → D266 → D269 → D271`. D266, que tiene que decir si ω
importa, solo se puede medir sobre mallas sanas (D270) y con el 0,129 m de
D267 ya explicado.
