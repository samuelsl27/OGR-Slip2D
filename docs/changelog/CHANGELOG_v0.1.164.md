# OGR Slip2D v0.1.164

**El encargo de P-D91 pedía leer el entero que `apply_sample` lleva
devolviendo desde que existe —su propio docstring dice para qué: «so the
caller can detect a definition that no longer matches the model»— y está
hecho en los tres sitios. Pero la medición que la ficha publica como prueba
del defecto no lo prueba: muestrea el Embankment del problema 12, y el
círculo publicado de ese problema tiene sus 30 dovelas en Soft Clay, así que
esa cohesión no mueve el factor tampoco con el objetivo INTACTO. Las dos
corridas que la ficha contrasta salen iguales salvo el contador, y de todo
lo que imprime sólo `apply_sample -> 0` distingue una cosa de la otra.**

Cierra **D91**. **Cero dígitos movidos**, y medido: las once corridas
probabilísticas del banco contra `Evaluaciones/0.1.160`.

---

## 1. El defecto, y la medición que sí lo prueba

`ogr_core/statistics/random_variables.py:319` devuelve cuántos parámetros
escribió; `set_value` (`:165`) devuelve `False` cuando el objetivo o el
parámetro ya no existen. Los tres llamadores tiraban el valor:
`probabilistic.py:371` (`run_global_minimum`), `:596`
(`run_overall_slope`) y `sensitivity.py:244` (`run_sensitivity`).

La consecuencia es la regla 7 en su forma pura. Medido el 2026-09-13 con
0.1.163 sobre el problema 12, sobre el círculo publicado de Bishop, con la
cohesión de **`materials[1]` (Soft Clay)**, que es el material que el
círculo sí cruza — misma semilla, mismo modelo, misma distribución, y lo
único distinto un `target_id` que ya no casa:

```
VALIDA    apply_sample=1 | media=0.996063021 std=0.190636922 pf=0.450 beta=-0.020651714 distintos=20
HUERFANA  apply_sample=0 | media=1.017489184 std=0.000000000 pf=0.000 beta=inf          distintos=1
```

Una probabilidad de rotura del **45 % contestada como 0 %**, β −0,02 como
∞, con `ok` verdadero y `notes` vacío. Un resultado perfectamente creíble
sobre un muestreo que no muestreó nada.

## 2. Lo que la ficha da por sentado y la medición desmiente

Seis cosas, y la primera invalida su propia prueba.

**(1) Su reproducción no distingue el defecto del modelo.** La ficha
muestrea `p.materials[0]`, el Embankment. Medido: el círculo publicado
(25,193 / 15,283 / r 7,715) tiene las 30 dovelas en Soft Clay, de modo que
el Embankment no se cruza y su resistencia no mueve nada —`cohesion` 0 y
50, `friction_angle` 5 y 45 dan los cuatro 1,017489—. Con el objetivo
intacto sale exactamente el bloque que la ficha ofrece como evidencia:

```
VALIDA    apply_sample=1 | ok=True n=20 std=0 pf=0.000 beta=inf notes={} distintos=1
HUERFANA  apply_sample=0 | ok=True n=20 std=0 pf=0.000 beta=inf notes={} distintos=1
```

No es un defecto del motor: es geometría del problema 12. Pero significa
que «20 muestras idénticas, PF = 0, β = ∞» no era una medida de nada, y que
una curva plana no puede usarse como prueba en este expediente. El test no
la usa.

**(2) Sus dígitos son de 0.1.159.** Publica 1,017227; hoy ese círculo da
1,0174891839718099, porque 0.1.160 metió la tolerancia en cada `.ogr` y
movió 83 problemas. La línea base es `Evaluaciones/0.1.160` y no la
`0.1.159` que su criterio de cierre nombra: mismo re-anclaje que `d79()`,
`d94()`, `d98()` y `d95()`.

**(3) `d91()` no existía**, aunque el criterio de cierre la cita como si
estuviera escrita. Se escribe aquí.

**(4) El test no es `_v1160`.** `_vNNNN` es la versión en que el test
aterriza, precedente escrito en 0.1.162 y 0.1.163:
`tests/test_random_variable_target_v1164.py`.

**(5) Su paso 3(b) es intermitente tal como está redactado.** Pide que las
estadísticas de la variable sana sean «idénticas a una corrida sin la
huérfana (misma semilla)». Sólo se cumple si la sana va **primera**:
`sample_variables` consume el `Random` una vez por clave en orden de
inserción, así que una huérfana delante se lleva el sorteo que le tocaba a
la sana. Medido, con semilla 5 y 8 muestras:

```
buena SOLA        [19.473320426, 13.842465439, 15.699914328, ...]
[buena, huerfana] idénticas
[huerfana, buena] distintas
```

Es un hecho del muestreador, no un defecto; queda fijado en
`test_the_order_is_why` para que nadie «simplifique» el orden.

**(6) El censo del banco no estaba hecho**, y es lo que convierte «cero
dígitos movidos» en consecuencia y no en coincidencia: recorridos los
`.ogr`, **6 modelos declaran variables aleatorias, 22 variables, y CERO
dejan de escribir**. La guarda no se dispara en ninguna.

## 3. El arreglo

`unwritable_variables(project, variables, sample)` en `random_variables.py`,
junto a `apply_sample`. `apply_sample` y `set_value` **no se tocan**: la
ficha lo pide y tiene razón, el defecto es de quien no los lee.

El ayudante mide con `set_value` y no con `get_value`, y no por comodidad:
`get_value` no es su espejo. Su rama `WATER_TABLE` devuelve `0.0`
incondicionalmente (`:160-161`) mientras `set_value` va a
`_shift_water_table`, que contesta `False` cuando el proyecto ya no tiene
nivel freático — o sea que una sonda basada en `get_value` daría por sana
justo la clase de definición que esta versión persigue.

Mide sobre un clon de usar y tirar por dos razones, y la segunda no es la
obvia: `set_value` **escribe**, así que el proyecto del usuario no puede ser
la sonda; y la variable de nivel freático es un **desplazamiento**, de modo
que preguntarle dos veces al mismo clon movería la lámina el doble y
contestaría sobre un modelo que nunca existió.

### Por qué la comprobación va izada y no en `i == 0`

La ficha manda leer el retorno «en la primera muestra». Va **una vez por
corrida, antes del bucle de métodos**, y hay que decirlo porque quien
difunda las líneas 371 y 596 no encontrará nada nuevo en ellas:

- **el veredicto no depende de la muestra.** `set_value` contesta lo mismo
  para cualquier valor: su única rama que mira el valor es
  `project.seismic.enabled = True`, que no cambia el retorno. Leer el
  contador en la muestra *i* > 0 no puede decir nada que la 0 no dijera, y
  una comparación que no puede ser falsa es código muerto — la forma que la
  regla 7 existe para dejar fuera;
- **el desajuste es del proyecto y de las variables, no del método**, así
  que preguntarlo dentro del bucle de métodos repite la misma respuesta;
- **`ok` no es un campo**, es `bool(self.by_method)`. Volver desde ahí deja
  `by_method` vacío de forma demostrable, sin depender de en qué iteración
  se estaba;
- el `grep` del criterio de cierre sigue encontrando **exactamente dos
  líneas** de `= apply_sample(`, una por función.

Cuesta **un `deepcopy` por corrida** (dos cuando la guarda salta, y
entonces no se evalúa ninguna muestra) frente a `num_samples × métodos`
dentro del bucle: 0,1 % con el `num_samples = 1000` por defecto, invisible
en Overall Slope, donde la referencia es una búsqueda entera por muestra.
Se cuenta el trabajo añadido y no el cronómetro, que para esto no
distingue nada.

### El contador es el disparador, nunca el veredicto

`applied < len(active)` también se queda corto cuando dos variables
comparten `key`, porque el diccionario del muestreador las colapsa en una
columna. Por eso decide la **lista medida**: si `unwritable_variables`
vuelve vacía no se dice nada. Un aviso que culpe a una huérfana que no
existe sería el mismo defecto con el signo cambiado.

### Sensibilidad

`VariableSensitivity` gana `note: str`, y la variable huérfana se guarda
**con su nota y cero puntos**: `ranking()` la salta, porque un recorrido de
cero que nunca se midió no puede sentarse en la cola de la tabla como si se
hubiera medido y hubiera salido irrelevante. Barrerla costaba
`intervals + 1` clones y otras tantas evaluaciones para producir una línea
plana; ahora cuesta un clon y ninguna.

La frase del run se emite **una sola vez al final** y con `usable` de
denominador, no por variable y por método: las primeras redacciones metían
una entrada por clave de variable en `res.notes`, que es un tercer espacio
de nombres en un diccionario cuya convención son `"error"` y `<método>`, y
además dejaba `notes["error"]` con una frase de forma distinta a la que
dice el motor probabilístico. Cuando no sobrevive ningún método la frase va
bajo su propia clave y **no** directamente en `"error"`, para que el
*roll-up* de 0.1.154 siga recogiendo al lado un rechazo por método en vez de
encontrar `"error"` ocupado y perderlo.

## 4. Los dos gemelos de la interfaz, y un tercero que el arreglo crea

Por decisión del propietario. Sin esto el `warning` existía y no lo leía
nadie, que es el estado que
`test_statistical_rebuild_v1154.py:454` llama «una nota que nadie enseña es
una nota que no existe».

- `main_window.py`: `last_statistics_notes`, alimentada desde las **dos**
  ramas `if res.ok:` y vaciada con la corrida que la produce (los tres
  sitios que ya vaciaban `last_compute_warnings`). *Analysis Notes* enseña
  las dos listas. Lista aparte y no fusionada porque
  `last_compute_warnings` la reescribe cada cálculo determinista, y
  *Compute Statistics* lanza uno para obtener sus superficies críticas: la
  corrida habría borrado su propia nota;
- `statistics_window.py`: `_plot_sensitivity` no dibuja una barrida sin
  puntos y la nombra en la línea de estado;
- **y un tercero que no estaba en el encargo**:
  `interpret_window.py:_sensitivity_plot` arma su `series` con **todas** las
  barridas. Es el defecto de esta misma versión un escalón más abajo —una
  entrada de leyenda sin curva, en la ventana que el usuario mira en
  segundo lugar—, y lo crea este arreglo, así que se corrige aquí.

`tr()` sólo hace falta en el literal nuevo de la línea de estado, con su
entrada española. Las notas nacen en `ogr_core`, que no puede importar
`ogr_gui.i18n`, y pasan sin traducir exactamente como ya hacía
`main_window.py:1664`.

**Reportado y no corregido (regla 6):** `_compute_statistics` **no envuelve
en `tr()` ni uno** de sus siete literales visibles —«Define at least one
random variable first.», «probabilistic run failed», «most sensitive: …» y
cuatro más—, y el presupuesto de `test_i18n_coverage_v141.py` no lo ve
porque sus patrones sólo miran `QLabel(`, `setText(`, `addRow(` y
compañía: `showMessage` y las f-strings le son invisibles. Es trabajo de
otra ficha y no se hace aquí.

## 5. Lo que se probó

- **Suite entera 3488/3488** (0.1.163 traía 3464; los 24 nuevos son este
  archivo).
- **El test nuevo falla 12 de sus 24 casos contra el árbol de 0.1.163**,
  que es la prueba de que mide algo. Los 12 que pasan son los que deben
  pasar: la premisa (`apply_sample` devuelve 0), el orden del muestreador,
  las dos medidas del nivel freático, los gemelos de la regla 7 y la
  identidad de las estadísticas — invariantes que el arreglo tiene que
  **conservar**, no crear.
- **Las once corridas probabilísticas del banco rehechas** (2363 s, de los
  cuales 1698 s la del 36, la única con Overall Slope): **189 números
  contra `Evaluaciones/0.1.160`, 24 de ellos PF o β, CERO distintos**, cero
  claves sin pareja y cero claves nuevas. Y el censo que lo convierte en
  consecuencia: ninguna de las once escribió `global_minimum.error`, o sea
  que la guarda **no se disparó ni una vez**.
- Ninguna aserción fija un factor de seguridad. Lo que se comprueba son
  identidades: los valores de una corrida con huérfana al lado son, uno a
  uno, los de la corrida sin ella con la misma semilla; y los de una
  corrida sana son los que sale de aplicar las mismas muestras a mano.

## 6. Reportado y no corregido (regla 6)

- El `progress_cb` no se lleva a `(total, total)` en el retorno temprano,
  igual que en los dos retornos tempranos que ya había. Hoy no tiene
  consecuencia visible porque `_compute_statistics` no pasa ninguno.
- `VariableSensitivity.is_increasing` contesta `True` con menos de dos
  puntos, así que una huérfana «crece». Nadie lo lee para una barrida
  noteada; el contrato es mirar `note` primero, y queda escrito donde se
  declara el campo.
- D127 sigue en pie y no es de aquí: con `st.n == 0` el probabilístico
  sigue publicando `PF = nan` y `β = −inf`. Esta versión quita **una** causa
  de que un muestreo no muestree, no la puerta.
- El rechazo PARCIAL por método (D129) sigue mudo: esta versión abre el
  canal para la clave que escribe, y no hace el trabajo por método que esa
  ficha pide.
