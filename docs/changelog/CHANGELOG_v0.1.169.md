# OGR Slip2D v0.1.169 — un muestreo sin muestras no publica un número

Cierra **D127** (P-D127, paquete P1). Cero dígitos movidos, y **demostrado re-corriendo el
banco**, no razonado: a diferencia de v0.1.166-168, este cambio entra en `ogr_core`.

---

## 1 · Qué estaba mal

Cuando **todas** las muestras de un método fallaban, el análisis probabilístico devolvía
`ok = True`, `PF = nan` y `β = −inf`, sin ningún error, y la barra de estado imprimía
exactamente eso. Reproducido contra 0.1.168 con la receta de la ficha:

```
ok=True n=0 pf=nan beta=-inf failed=20 notes={}
m.notes={'warning': '20 of 20 samples could not be evaluated; check the variable ranges.'}
json: {..., "mean_fos": NaN, "pf": NaN, "reliability_index": -Infinity, ...}
```

Tres piezas lo fabricaban, y la del medio es la que nadie había mirado:

- `SampleStatistics` contestaba `nan` a la media y a la probabilidad de fallo, un `0.0`
  pelado a la desviación típica, y **`−inf`** al índice de fiabilidad — este último porque
  `std_dev` cortocircuita a `0.0` con `n < 2` y después `nan >= 1.0` es **False**. Es
  decir: un muestreo sin un solo dato se publicaba como «el fallo es seguro»;
- `run_global_minimum` metía el método en `by_method` igualmente;
- `ProbabilisticResult.ok` era `bool(self.by_method)`, de modo que una clave sin nada
  detrás **era** un resultado.

Es la política de **D56** (v0.1.152, `fos: Optional[float]`) aplicada al muestreador.
**D59** (v0.1.154) quitó *una* causa de ese estado —la compuesta sin su opción— y no la
puerta.

---

## 2 · Lo que la ficha daba por sentado y la medición desmiente

Doce cosas. **Seis cambian el trabajo.**

1. **Su paso 2 es IMPOSIBLE tal como está escrito, y lo impide un test que ella misma
   declara intocable.** Manda no añadir el método a `by_method` también en
   `run_overall_slope`; pero `test_overall_slope_v137.test_failed_searches_counted` hace
   fallar **las cinco de cinco** búsquedas y luego afirma
   `res.by_method[mid].failed_samples == 5`. Eso **es** el estado de D127 en Overall
   Slope, está verde hoy, y sacar la entrada da `KeyError`. De modo que las dos funciones
   **divergen a propósito**: en Global Minimum el método sale del diccionario, en Overall
   Slope se queda y lo que apaga la corrida es `ok`. Va con comentario en el código que
   nombra el test, y con un caso de conservación que replica su aserción, porque «unificar
   los dos bucles» es exactamente lo que alguien propondrá.

2. **«Guardar la razón de la última muestra fallida (el `except` la tiene)» pide menos de
   lo que la casa ya ofrece, y en un caso pide algo que no existe.** Medido: una muestra
   cuyo `LEMResult` vuelve con `is_valid` falso **no pasa por el `except`**, y antes de
   esta versión las dos rutas producían un estado idéntico —`ok` verdadero, `pf` nan,
   `notes` vacío—. Pero desde **D56** un resultado inválido lleva `reason`, una de
   `ALL_REASONS`, puesta ahí literalmente para que quien llama pueda *«GROUP by reason
   instead of matching free text»*. Son **tres** desenlaces distinguibles —lanzó,
   devolvió `None`, devolvió inválido con razón— y lo correcto no es quedarse con el
   último sino **contarlos**: `raised RuntimeError x 20`, que es la forma en que la
   referencia informa de sus propios códigos de error.

3. **`mres.notes[...]` no lo lee NADIE** (verificado por grep en todo el repositorio):
   `main_window` lee `res.notes`, las del **resultado**. El paso 1 manda escribir la razón
   donde nadie mira, y además el `mres` de un método que no sobrevive se descarta entero,
   así que no quedaría ni objeto que la llevase. La clave es `result.notes[mid]`, igual
   que el rechazo de D59, porque ésa sí participa del roll-up. Es el estado que
   `test_statistical_rebuild_v1154` llama «una nota que nadie enseña es una nota que no
   existe».

4. **Su caso (b) es inalcanzable.** Pide que «3 de 20 fallando» dé el aviso de hoy. El
   aviso es `failed > 0.2 * num_samples`: `3 > 4` es **falso**, y `4 > 4` también. Hacen
   falta **cinco**. El test fija los **dos** lados del borde, precisamente porque 3 y 4
   caen los dos del lado mudo y la ficha eligió el número que no distingue nada.

5. **`test_statistics_v133.test_empty_statistics_are_safe` fijaba el defecto como
   invariante, y lo llamaba «safe».** Hacía `assert math.isnan(st.probability_of_failure())`
   sobre el estadístico vacío. La ficha no lo nombra y no está entre sus intocables. Se
   actualiza, con la razón escrita: una instantánea del comportamiento de hoy consagra el
   bug, que es la regla 1 en negativo.

6. **La ficha no nombra `interpret_window.py`**, que tenía **tres** sitios eligiendo
   método con `next(iter(prob.by_method))`. En Overall Slope el método vacío conserva su
   entrada, así que los tres podían caer justo en él: la gráfica de convergencia y el
   diálogo de superficie crítica decían «No probabilistic result» **habiendo** resultado,
   y la exportación escribía un CSV con cabecera y cero filas.

**Citas caducadas o inexistentes** — por eso nada en este cambio ni en su test se localiza
por número de línea, todo por nombre de símbolo:

7. **`to_dict()` no existe** en ninguna dataclass de `probabilistic.py` ni en
   `SampleStatistics`; el único serializador es `summary()`. La ficha lo cita dos veces.
8. El aviso del 20 % no está en `389-392` sino en **441-444**; `59-64`, `70-88`,
   `418-423`, `439-470`, `380-392` y `596-607` están todas corridas.
9. `ogr_gui/main_window.py:1657-1662` es hoy **1708-1713**.
10. **`d127()` no existía**, aunque el criterio de cierre la cite como escrita — igual que
    D91, D95, D96, D98, D101, D102 y D103.
11. El determinista que publica (**1,017227**) es de 0.1.159; hoy ese mismo círculo da
    **1,0174891839718099**, porque 0.1.160 metió la tolerancia en cada `.ogr` y movió 83
    problemas. La línea base es **`Evaluaciones/0.1.160`** y no la 0.1.159 que nombra el
    criterio de cierre: mismo re-anclaje que `d94()`, `d95()`, `d96()` y `d98()`.
12. El test no es `_v1160` sino **`_v1169`** (`_vNNNN` es la versión en que ATERRIZA), y
    **`ogr_cli` no importa `ogr_core.statistics`**: cero trabajo de línea de órdenes.

---

## 3 · Hasta dónde llega el «no-número», y por qué no más allá

La ficha pide `Optional[float]` sólo para `probability_of_failure` y `reliability_index`.
Se amplía a **los siete** miembros de `SampleStatistics` con `n == 0`, y la decisión no es
de gusto: la toma la documentación que este repositorio ya tiene escrita.

- `test_no_number_v1152` fija el criterio de aceptación de esta política en una frase:
  **«`allow_nan=False` is the whole test»**. Y como el método vacío **no puede salir** de
  `by_method` en Overall Slope (punto 1), su `summary()` sale de verdad: con el alcance
  mínimo seguiría llevando `"mean_fos": NaN` al lado de `"pf": null`, y la política
  quedaría declarada en vez de aplicada.
- D56 nombra un `0.0` sin datos como la forma de **D20**, *«a fallback wearing the clothes
  of a result»*, y explícitamente **peor** que un `nan`. `std_dev` devolvía exactamente eso
  con cero muestras.
- `docs/PLAN_PROBABILISTICO.md` define `PF = nº de casos con FS < 1 / N`. Con `N = 0` la
  cantidad **no existe**; no es que se desconozca.

**Dónde para la guarda, dicho en voz alta en tres sitios** (el docstring de la clase, el
test nuevo y `d127()`): cubre `n == 0` y nada más. Con **una** muestra la desviación típica
sigue siendo `0.0` y el índice de fiabilidad sigue siendo `±inf`, así que con 19 de 20
muestras fallidas `summary()` **todavía puede** no serializar con `allow_nan=False`. Son
cantidades definidas y degeneradas, no cantidades que faltan — y el `beta inf` de un
muestreo sin dispersión es justo la señal con la que **v0.1.164 (D91)** caza una variable
aleatoria que ha dejado de escribir; borrarla borraría el diagnóstico. `d127()` comprueba
ese límite además del caso vacío, para que un futuro «completar el arreglo» se ponga rojo.
Prometer una cobertura más ancha que la que la guarda da es lo que costó dos versiones en
v0.1.82-84.

---

## 4 · Qué se ha hecho

**`ogr_core/statistics/distributions.py`** — los siete miembros pasan a `Optional[float]` y
devuelven `None` sin muestras. El único error fácil de cometer aquí está comentado donde
toca: en `reliability_index` la guarda `if not self.n` va **la primera**, antes de leer
`std_dev`, que ahora es `None` y reventaría en `s <= 0` con `TypeError`.

**`ogr_core/statistics/probabilistic.py`** — cinco ayudantes compartidos por las dos
funciones. `_sample_failure` y `_search_failure` etiquetan la causa de perder una muestra o
una búsqueda; `_counted_reasons` las ordena por frecuencia y luego por nombre, para que dos
corridas del mismo dato se lean igual; `_no_sample_note` redacta la frase, con `_STEM_GM` /
`_STEM_OS` como constantes y **sin** nombrar los rangos de las variables, que es la lección
de D59; `_publish_method_losses` decide entre `notes["error"]` (nadie sobrevivió) y
`notes["warning"]` (alguno sí), **concatenando** en el segundo caso y nunca asignando,
porque el aviso de variables rancias de D91 puede estar ya en esa clave y sobrescribirlo
sería cerrar un silencio abriendo el anterior. La lista `lost` es **explícita** y la
rellenan los bucles: deducirla preguntando qué claves de `notes` no son `"error"` ni
`"warning"` sería despachar por la forma del diccionario, que es literalmente D59.

`ok` deja de ser `bool(self.by_method)` y pasa a `self.reported is not None`, donde
`reported` es el primer método **con muestras**. Se definen juntos para que no puedan
separarse, y `reported` es además lo que evita escribir ramas «—» que nadie ve: pasado un
`ok` comprobado nunca es `None`, así que ningún consumidor formatea un número ausente ni
tiene que fingir que podría.

**`ogr_gui`** — cuatro sitios y ninguna rama muerta. `main_window` usa `res.reported` en vez
de `next(iter(...))`, que era **obligatorio**: en Overall Slope el primer método puede ser
el vacío, y `pf * 100` con `None` habría sido un `TypeError` donde antes imprimía
`PF = nan %`. Su rama de error mete la razón también en `last_statistics_notes`, no sólo en
la barra de estado, donde duraba doce segundos. Los tres de `interpret_window` pasan a
`reported`. **`statistics_window` no se toca**: ya está protegido por `if st is None or not
st.values: return`, y añadir algo allí sería código muerto.

Cero texto visible nuevo, así que **cero entradas de i18n** y ningún presupuesto movido; las
notas nacen en `ogr_core`, que no puede importar `ogr_gui.i18n`. **Regla 3**: no hay acción
nueva.

---

## 5 · Qué se ha probado

- **Suite entera y sin argumentos**: `3628/3628` (0.1.168 traía 3596; los 32 nuevos son 31
  de este archivo y 1 de `test_statistics_v133`).
- **El test discrimina**: contra el árbol de 0.1.168, con sólo el archivo nuevo presente,
  fallan **20** y pasan **11**. Los 11 son justo los que deben: las identidades que el
  cambio **conserva** —el aviso del 20 % palabra por palabra y sus dos lados del borde, la
  entrada y el recuento que Overall Slope no puede perder, un método con 5 fallos que sigue
  siendo un resultado, la corrida sana que no dice nada nuevo, la aritmética ordinaria
  recalculada—, el **límite honesto** (con `n = 1` β sigue siendo `inf`) y la lección de D59
  (la razón no culpa a los rangos).
- **`d127()` discrimina y no pasa en vacío**: contra el árbol sin el arreglo da
  **`NO SE SOSTIENE`**, y mide **ejecutando** el estadístico vacío en vez de leerlo, porque
  eso es lo único que separa la política aplicada de la declarada.
- **El banco re-corrido**: las once corridas probabilísticas, 2294 s, y **189 números
  comparados contra `Evaluaciones/0.1.160` —24 de ellos PF o β— con CERO movidos**. Que el
  cero sea **consecuencia y no suerte** lo dice el propio verificador con el número
  delante: **0 de 11** corridas pierden una sola muestra, así que la guarda nueva no tiene
  dónde dispararse. Veredicto de `d127()`: **CUBIERTO POR TEST**.

Ninguna aserción fija un factor de seguridad: lo que se comprueba son identidades, nombres
y recuentos recalculados en el propio test.

### Errores propios, detectados antes de publicar

- La primera redacción de `_invalid()` construía un `LEMResult` sin `surface` ni `slices`,
  que son **posicionales y obligatorios**, de modo que reventaba con `TypeError` y el fallo
  se contaba como `raised` — justo el desenlace que ese ayudante existe para **distinguir**
  de una excepción. Lo delató el caso que compara las dos rutas, que es la razón de
  escribirlo.
- La corrida mixta elegía el método perdido preguntando `search.method.method_id`, y
  medido **un `LEMMethod` no expone `method_id`**. Se elige por **orden de llamada**, que
  es lo que `run_global_minimum` garantiza al recorrer `critical_surfaces` en orden de
  inserción.
- La primera suite completa se lanzó en segundo plano y **se hicieron dos `git stash`
  mientras corría**, lo que invalida su resultado; se descartó y se relanzó con el árbol
  quieto. Es el mismo ruido autoinfligido que AGENTS.md documenta para las mediciones de
  coste, con el árbol en vez de con los núcleos.
- El `sed` del número de versión **no** se usó en bloque: `main_window.py` lleva **seis**
  comentarios históricos `v0.1.168 (D101)` que una sustitución global habría reescrito,
  falsificando en qué versión se hizo aquello. Es el error que v0.1.168 documentó; aquí los
  siete sitios se cambiaron uno a uno con guarda de aparición única, y los seis comentarios
  se comprobaron intactos después.

---

## 6 · Reportado y no corregido (regla 6)

- **El límite de la guarda**, arriba: `β = ±inf` con `n ≥ 1` y dispersión nula, y el índice
  lognormal `nan` con menos de dos valores positivos. Medido, alcanzable sin parchear nada,
  y deliberadamente intacto.
- **`deterministic_fos` sigue pudiendo ser `nan`**: sale de `getattr(det, "fos", math.nan)`,
  así que una corrida de Overall Slope sin determinista lo publica. Es un no-número de la
  misma familia pero de otra causa —«no hay resultado determinista», no «no hay muestras»—
  y moverlo toca el formateo de `statistics_window`. Fuera de alcance.
- **El aviso del 20 % vive en `mres.notes`, que nadie lee.** Esta versión abre el canal para
  la caída total y la parcial, no para él; su frase y su umbral no se tocan, que es lo que
  la ficha prohíbe.
- **D129** (rechazo parcial por método) queda cerrada sólo en su mitad probabilística, la
  que esta versión crea.
- **Los dos umbrales siguen siendo distintos** a propósito: `> 0.2 * num_samples` en Global
  Minimum y `if ores.failed_samples:` en Overall Slope.
- **`probabilistic.py`: `surface is None` tras pasar `_cannot_reevaluate` es inalcanzable**
  —el rechazo sólo deja pasar circle/composite/polyline y `_rebuild_surface` siembra los
  tres—, así que no se le pone nota: sería rama muerta, y eso es la regla 7 con el signo
  cambiado.
- **Dos esquemas incompatibles conviven bajo `ProbabilisticResult.summary()`**: Global
  Minimum trae `reliability_index_lognormal` y Overall Slope no, y a cambio éste trae
  `distinct_global_minima`. Hoy es inerte, porque **nadie consume `summary()` en
  producción** — sólo los tests.
