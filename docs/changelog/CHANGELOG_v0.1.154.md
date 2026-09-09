# OGR Slip2D v0.1.154 — D59: despachar por el campo `type`, no por la forma

El encargo P-D59 señalaba una línea de `_rebuild_surface`
(`ogr_core/statistics/probabilistic.py`) y pedía reconstruir la superficie
compuesta. La línea estaba mal, y la degradación es real:

```
to_dict['type'] = composite | 'radius' in dict: True
_rebuild_surface -> SlipCircle | es CompositeSurface: False
```

Pero **el arreglo que pedía es el equivocado**, y medirlo antes de escribir
es lo que ha dado la versión.

---

## 1 · Las cuatro premisas del encargo que se cayeron

**(1) «Con la opción puesta se vuelve a componer y no se nota; sin ella, sí»
— la primera mitad es exacta, y por eso el arreglo pedido sobra.**
`_evaluate_on` manda el círculo pelado a `evaluate_circle`, que vuelve a
recorrer las cuerdas y a llamar a `compose_with_bedrock`: la compuesta se
**rehace**. Medido sobre los modelos compuestos del banco, 8 filas
método-modelo, con el arreglo puesto:

```
022/modelo.ogr            bishop  det=1.3813894713319512  muestra=1.3813894713319512  delta=0.000e+00
022/modelo.ogr            spencer det=1.3808279219525601  muestra=1.3808279219525601  delta=0.000e+00
045/modelo_mc.ogr         janbu   det=2.8256116118519556  muestra=2.8256116118519556  delta=0.000e+00
057/modelo_compuesto.ogr  bishop  det=1.4340304828981731  muestra=1.4340304828981731  delta=0.000e+00
057/modelo_compuesto.ogr  spencer det=1.4414060965086726  muestra=1.4414060965086726  delta=0.000e+00
```

**(2) Reconstruir la `CompositeSurface` habría metido un error.** Su
`to_dict()` no serializa `tension_crack_wall`, y como los extremos llegarían
ya truncados el slicer no lo vuelve a deducir: con la grieta llena eso vale
**+0,3546 % del lado inseguro** en el modelo compuesto del 57, donde
re-recortar acierta +0,0000 %. Además fijaría la masa, que es justo lo que
v0.1.131 (D36) quitó a propósito. **Se conserva la semilla —el círculo— y se
arregla la condición.**

**(3) Pasar el proyecto a `_rebuild_surface` no hace falta.** Sólo lo
necesitaba la reconstrucción. La firma no cambia y
`tests/test_surface_purity_v1131.py:298` —la invariante de D36/D53— no se ha
tocado ni un carácter.

**(4) `_evaluate_on` no se toca.** `CompositeSurface` no es subclase de
`SlipCircle` (decisión explícita, `surface.py:611-624`), así que ya iría por
`evaluate_surface`. El punto 2 del encargo pedía un cambio que no había que
hacer.

Y una quinta, que es la que más sorprende: **el arreglo de una línea —mirar
`type` y borrar `or "radius" in surface_dict`— no da un número peor: revienta
las compuestas con `KeyError('polyline')`.** Esa cláusula defectuosa era hoy
lo único que las salvaba.

Corrección de hecho: los modelos con compuestas del banco son **22, 45 y 57**.
El encargo dice «el 57 y el 61»; el 61 las trae **apagadas** en sus dos
modelos, y su subtítulo del manual habla de compuestas por el título de la
referencia, no por el ajuste.

---

## 2 · Lo que sí rompía, y no era D59

La causa raíz —despachar por la **forma** del diccionario— tiene dos hermanos
en el mismo archivo, y esos **sí matan una función pública hoy**:

```
_rebuild_surface(weak_layer) -> LANZA KeyError 'polyline'
_surface_key(polyline)       -> LANZA TypeError list indices must be integers or slices, not str
_surface_key(weak_layer)     -> 'p:'
```

- **D85** — la llamada de `probabilistic.py:221` y `sensitivity.py:210` está
  **fuera** del `try` del bucle de muestras, así que una crítica de capa débil
  se llevaba *Compute Statistics* entera, los dos análisis y todos los
  métodos, sin diálogo ni barra de estado. Alcanzable desde el menú
  (*Draw Weak Layer*, Ctrl+7).
- **D86** — `_surface_key` leía `v["x"]` y `Polyline.to_dict` escribe `[x, y]`,
  y siempre lo ha hecho. El bucle que lo llama (`probabilistic.py:447-459`)
  está **fuera** del `try` de la línea 431, así que `run_overall_slope` moría
  por su puerta pública con cualquier búsqueda no circular (Block, Path, Auto
  Refine) o superficie optimizada. Alcanzable desde Project Settings →
  *Overall Slope*. Y todas las superficies de capa débil colapsaban en la
  clave vacía `'p:'`, mezclando poblaciones que no son la misma superficie.

D59 en sí es **latente**: la interfaz recalcula el determinista en la misma
llamada (`_deterministic_criticals`), no hay `processEvents` en todo el árbol,
`ogr_cli` no tiene estadística y `results_io` sólo escribe superficies. Nadie
llega hoy al escenario. Pero es una trampa armada y medida.

---

## 3 · Lo que se ha hecho

Los cuatro tipos serializados se enumeran por su campo `type`. `circle` y
`composite` siembran un círculo **sin extremos** (D36 intacto), `polyline`
siembra su poligonal, y lo que no se sabe sembrar se **rechaza con su razón
escrita** en vez de degradarse en silencio o reventar. Un diccionario sin
`type` pero con `radius` sigue leyéndose como círculo, a propósito:
`run_global_minimum` acepta un dict pelado como `det.surface`, y romper ese
contrato de refilón habría sido un efecto colateral, no una decisión.

El rechazo cubre además la **condición perdida**: una compuesta sembrada desde
su círculo sólo vuelve a ser compuesta mientras Composite Surfaces siga
encendida en el proyecto donde corren las muestras. Sin ese rechazo, lo medido
es:

- **una masa** (los cuatro modelos compuestos del banco): 10 muestras de 10
  perdidas, con `PF=nan`, `beta=-inf`, `ok=True` y un aviso que culpa a los
  **rangos de las variables**, que son inocentes. En sensibilidad el barrido
  entero desaparece: `ok=False`, 0 puntos, `notes={}`;
- **dos masas**: el motor tira sólo la masa que se sale y **contesta por la
  otra**, `3.3584888466014458` contra `1.3822805259349988` = **+142,97 %**,
  con cero muestras fallidas y ninguna nota.

Rechazar —y no forzar el ajuste en el clon— es lo que implica D36: una
superficie contesta por el proyecto por el que se le pregunta.

`run_sensitivity` comparte la llamada, el defecto y el arreglo. Y en los dos,
si no sobrevive ningún método, la razón sube a `notes["error"]`, que es la
única clave que la interfaz imprime.

---

## 4 · Alcance honesto, y lo que NO entra

**Con la opción encendida el arreglo no mueve un solo dígito** (las 8 filas de
arriba, delta 0). Su valor es (a) quitar una trampa armada que vale +142,97 %
en silencio y (b) cerrar las dos roturas alcanzables hoy.

**El cambio de interfaz que el diseño proponía no entra, y esto es una medida,
no una omisión.** El mensaje nuevo sólo se imprimiría con un rechazo
**parcial** —un método rechazado y otro no—, y desde la interfaz eso exige que
dos métodos den críticas de **tipo distinto** sobre el mismo modelo. El único
modelo del banco con capas débiles es el 109, y sus tres métodos que corren dan
los tres `SlipSurface`:

```
bishop_simplified  critica=SlipSurface  fos=6.576615
spencer            critica=SlipSurface  fos=6.730225
janbu_simplified   critica=SlipSurface  fos=6.088912
```

No se ha encontrado la puerta, así que añadir el control habría sido un ajuste
que no hace nada (regla 7). Queda anotado como hueco: **con un rechazo parcial
el usuario vería un método menos sin que nada se lo diga**. Es mejor que el
`KeyError` mudo de hoy, pero no es visible.

**Los textos de las notas van sin `tr()`**, siguiendo la convención del módulo
—`ogr_core` no puede importar `ogr_gui.i18n`, y los avisos que ya viven ahí
tampoco están traducidos—. Es deuda conocida que esta versión no crea pero
aumenta en dos cadenas.

**Cambio de contrato**: `run_global_minimum` y `run_sensitivity` pueden ahora
devolver cero métodos con una nota donde antes devolvían un método con todas
sus muestras fallidas, o con un número de otra masa.

---

## 5 · El test — `tests/test_statistical_rebuild_v1154.py`

22 comprobaciones, geometría del problema 22 construida en el propio archivo.
Todo número se ancla a Fredlund y Krahn (1977) tabla 22.3 (1,377 Bishop,
1,373 Spencer, al 2 %) o a una identidad (determinista == muestra, `rel=1e-12`).
El modelo de dos masas va declarado **sintético**, sin ningún número publicado
asociado, y con dos tests de premisa delante.

Lo que el archivo **no** afirma, dicho en su cabecera: el rechazo cubre un
**ajuste** perdido, no un mecanismo cambiado. Con la opción encendida en las
dos corridas una muestra puede seguir contestando por otra masa del mismo
círculo sólo porque su propia resistencia bajó —`_best_of_masses` se queda con
el menor factor y D36 quitó los extremos a propósito—. Prometer lo contrario en
un docstring habría sido repetir el error de m-alpha (v0.1.82-84), que costó
dos versiones justificando una decisión con una medición equivocada.

**Con 0.1.153 fallan 12 de las 22**, y conviene nombrarlas porque cuatro fallan
sólo por `ImportError` (la función de rechazo no existía) y ocho fallan por
**comportamiento**:

| Test | Con 0.1.153 |
|---|---|
| `test_none_of_them_raises` | `TypeError` |
| `test_a_polyline_gets_a_key_instead_of_a_TypeError` | `TypeError` |
| `test_two_different_polylines_are_two_different_keys` | `TypeError` |
| `test_weak_layer_surfaces_no_longer_collapse_onto_one_key` | la clave era `'p:'` |
| `test_a_weak_layer_critical_no_longer_takes_the_run_down` | **`KeyError: 'polyline'`** |
| `test_the_probabilistic_run_refuses_and_names_the_option` | «a number came back for a surface this project cannot form» |
| `test_the_reason_reaches_the_key_the_interface_prints` | sin nota |
| `test_the_sensitivity_run_refuses_it_too` | sin nota |
| `test_a_bare_dictionary_without_a_type_is_still_a_circle` | `ImportError` |
| `test_an_empty_surface_is_refused_and_not_seeded` | `ImportError` |
| `test_each_one_either_seeds_or_is_refused_by_name` | `ImportError` |
| `test_without_the_option_the_other_mass_is_refused_not_reported` | `ImportError` |

---

## 6 · No regresión, medida

| Qué | Resultado |
|---|---|
| Suite completa, sin filtrar | **3228 / 3228** |
| Las 8 filas método-modelo de los modelos compuestos del banco (22, 45 ×3, 57), determinista contra muestra | delta **0,000e+00** en las ocho |
| Las **diez** corridas del 028 replicadas a 5000 muestras contra su registro de 0.1.153 | **110 valores comparados, 0 movidos**, `notas={}` en las diez |
| El 036 —la única con *Overall Slope*, y por tanto la única que ejercita `_surface_key`— en A/B código viejo contra nuevo, misma semilla | 28 valores; `distinct_minima` 3→3, `pf` 0,05→0,05; la única diferencia es un `uuid4`, que cambia en cada corrida por construcción |
| `verificar_cierres.py D36 D53` | `SE SOSTIENE`, 1.4065765613393215 las dos veces |
| `verificar_cierres.py D49` | `PENDIENTE DE CORRIDA` — sólo porque los JSON dicen 0.1.153 y lo instalado es 0.1.154; su contenido está verificado en la fila de arriba |
| `auditoria_invariantes` del banco | **ERROR = 0** (705 hallazgos: 487 AVISO, 218 INFO) |
| `tests/test_slide_validation_*` y `test_surface_purity_v1131.py` | sin tocar una tolerancia |

El 036 se comparó en A/B contra el código y no contra su JSON **a propósito**:
ese archivo está congelado en **0.1.147**, así que no sirve de base para juzgar
0.1.153 → 0.1.154.

---

## 7 · Defectos nuevos, reportados y NO corregidos

Van con número propio en el banco (`ERRORES_Y_DISCREPANCIAS.md`), continuando
la serie desde D84:

| # | Qué | Estado |
|---|---|---|
| **D85** | Una crítica de capa débil mataba *Compute Statistics* entera. Alcanzable desde el menú (*Draw Weak Layer*, Ctrl+7) | **Síntoma CERRADO** aquí; abierto el residuo: la capa débil sigue **sin estadística** |
| **D86** | `_surface_key` leía `v["x"]` sobre vértices `[x, y]` y mataba *Overall Slope* con cualquier superficie no circular | **CERRADO** aquí |
| **D87** | La clave de identidad no separa las dos masas disjuntas de un círculo, ni una compuesta de su círculo sin recortar | ABIERTO — meter los extremos reagruparía las muestras de todo modelo circular |
| **D88** | El rechazo de esta versión es **asimétrico**: al revés (determinista con la opción apagada, muestras con ella encendida) vuelve un número de otra masa, **−58,84 %** en una evaluación y **−59,52 %** en la corrida, con cero fallidas y notas vacías | ABIERTO — hacerlo simétrico exige saber con qué ajuste se obtuvo el determinista, y eso no viaja |
| **D89** | Con la opción **igual** en las dos corridas, una muestra salta de masa por su propio valor, en silencio; el cruce medido está entre c = 200 y c = 100 | ABIERTO |
| **D90** | `SlipSurface.to_dict` tampoco serializa `tension_crack_wall`, y esa rama **sí** reconstruye el objeto: la poligonal vuelve sin su muro | ABIERTO, efecto numérico NO MEDIDO |
| **D91** | Los dos muestreadores tiran el retorno de `apply_sample`/`set_value`, que existe «so the caller can detect a definition that no longer matches the model» | ABIERTO — N muestras idénticas, σ = 0, PF = 0 y ninguna nota |
| **D92** | La búsqueda del muestreador es un `GridSearch` pelado: **los Surface Filters y los Slope Limits del usuario no se aplican** en la corrida estadística | ABIERTO — 140 círculos del 037 que la configurada rechaza |
| **D93** | La crítica sale del proyecto **factorizado** y las muestras se evalúan sobre el **sin factorizar** | ABIERTO, NO MEDIDO: no hay modelo del banco con norma de diseño |

Y tres observaciones sin número propio: `SampleStatistics` entrega `PF = nan` y
`beta = -inf` con `ok=True` (la guarda de D56 no llega hasta ahí, y esta versión
quita **una** causa, no la puerta); un rechazo **parcial** sigue siendo mudo en
la interfaz, y no se ha añadido el aviso porque **no se ha encontrado la puerta
que lo dispare**; y `test_each_method_keeps_its_own_surface` no comprueba lo que
su nombre promete —pasaba igual con una compuesta degradada—.

**D88 y D92 se leen juntos**: arreglar D92 cambia lo que la guarda de D88
debería comparar, así que va antes.

---

© 2026 Samuel Sáez López — UPCT — AGPL-3.0-or-later
