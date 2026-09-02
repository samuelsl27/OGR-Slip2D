# OGR Slip2D v0.1.147

**El encargo de D51 llegaba con el defecto ya cerrado desde hacía
dieciocho versiones.** Lo que de verdad faltaba era la mitad de su
criterio que nadie había escrito —el test que *mide* la diferencia— y
escribirla destapó dos faltas en la copia del filtro de área que tiene el
recocido. Una de ellas **tira superficies que el filtro acepta**.

---

## Lo primero fue comprobar el enunciado, y estaba caducado

El prompt afirmaba, con su comprobación de un segundo incluida, que
`min_area` llegaba a `PathSearch` como 1,0 dijera lo que dijera el
proyecto. Corrida hoy sobre los dos modelos del problema 86:

```
modelo.ogr        grid  50.0  GridSearch  50.0
modelo_path.ogr   path  50.0  PathSearch  50.0
```

Se arregló en **v0.1.129**, de paso al cerrar D33 y por el mismo patrón:
`min_area` viaja en `common` y su default por rama se resuelve una sola
vez en `_MIN_AREA_FALLBACK`. Las siete ramas devuelven 50,0 sobre ese
mismo proyecto, y el problema 86 publica desde entonces Spencer
**1,584134**, que es exactamente lo que el registro predecía.

De los cuatro puntos que pedía el criterio de cierre, tres estaban hechos.
El cuarto —*«un test de regla 7: mismo modelo, con y sin filtro, con la
diferencia medida»*— no: en toda la suite `min_area` sólo aparecía como
argumento de constructor y en dos aserciones sobre el **atributo**. Un
test que comprueba que el valor *llega* no demuestra que *haga* nada, que
es justo la distinción que la regla 7 existe para cobrar.

## Lo que sí faltaba

`TestMinimumAreaMovesTheNumber`, ocho ramas, misma semilla, `min_area = 0`
contra un umbral que muerde. Tres aserciones por rama: que la respuesta
sin filtro es una que el filtro habría rechazado, que la respuesta con
filtro es una masa que el filtro acepta, y que el número que lee el
usuario **es otro número**.

| búsqueda | sin filtro (fos / masa) | umbral | con filtro (fos / masa) |
|---|---|---|---|
| grid | 1,404986 / 545,5 | 790 | 1,427060 / 846,0 |
| slope | 1,398087 / 500,5 | 730 | 1,410675 / 916,8 |
| auto_refine | 1,434097 / 729,9 | 1060 | 1,459480 / 1112,0 |
| auto_refine_nc | 1,381270 / 716,6 | 1040 | 1,395700 / 1093,7 |
| block | 1,353433 / 1135,2 | 1650 | 1,512543 / 1882,4 |
| path | 1,235715 / 833,8 | 1210 | 1,265391 / 1233,9 |
| particle_swarm | 1,426210 / 487,0 | 710 | 1,504052 / 772,8 |
| simulated_annealing | 1,304561 / 420,8 | 440 | 1,524180 / 444,4 |

La masa es `Σ wᵢ·max(hᵢ,0)` sobre las dovelas de la superficie crítica, que
es **literalmente** la cantidad que filtra `_best_of_masses`, y no una
segunda opinión sobre ella: preguntar lo mismo de otra manera es como dos
respuestas se separan.

**El umbral del recocido tuvo que bajarse a 440 y eso no es cosmética.**
Con 300 el número también se movía (1,304561 → 1,309274), pero por la
razón equivocada: el umbral quedaba *por debajo* de la masa que la
búsqueda encuentra sin filtro, así que lo que se movía era la trayectoria
del paseo y no el veredicto sobre la superficie ganadora. El test lo
rechazó, que es lo que se le pedía.

Coste: **13 s** las ocho parejas. La cara es la Path Search (3,6 s), que
sigue dibujando hasta reunir su cupo de superficies **válidas** y el filtro
le tumba la mayoría; por eso aquí lleva `num_surfaces = 150` y en los tests
de foco de al lado lleva 250.

## El recocido tenía su propia copia del filtro, con dos faltas

`SimulatedAnnealingSearch._evaluate_polyline`, guarda (d):

```python
if abs(area) < max(self.min_area, 0.5):
```

**1 · El suelo de 0,5.** Un proyecto que declarara 0,2 recibía 0,5 en esta
búsqueda y 0,2 en las otras siete; uno que declarara 0 no podía apagar la
guarda. Regla 7 en pequeño, y la única de las dos faltas que mueve un
número por sí sola. Se fija con una identidad calculable a mano: cuatro
vértices a un metro sobre la cara del talud, los dos interiores hundidos
`d`, dan masa `2d` exacta — así que 0,30 pasa y 0,10 no pasa contra un 0,2
declarado, y las dos caían antes.

**2 · La cuerda en vez del terreno.** El área se integraba entre la
superficie y la **cuerda entrada-salida**, mientras el filtro de todas las
demás búsquedas —y el que este mismo candidato vuelve a encontrarse
después en `_best_of_masses`— es la masa contra el **terreno**. Coinciden
sólo si el terreno entre los dos extremos es una recta.

**Y aquí la lección, porque la dirección del error no es simétrica.**

- Cuando la cuerda **sobreestima** la masa, la falta es invisible: el
  candidato pasa la guarda (d) y `_best_of_masses` lo tira acto seguido
  sobre la masa verdadera. Medido en A/B en el mismo proceso, la versión
  nueva contra la vieja monkey-patcheada: **75 combinaciones de semilla y
  umbral, ni una distinta**. Si me hubiera quedado ahí, la conclusión
  habría sido «el arreglo no hace nada».
- Cuando la cuerda **subestima**, no hay nada aguas abajo que lo deshaga:
  la superficie desaparece **antes de analizarse**, y es una superficie
  cuya masa declarada **cumple**. Ejemplo fijado en el test, con las dos
  áreas calculables a mano sobre el perfil (0,10)-(25,10)-(60,40)-(85,40):
  cuerda **1245,0000**, terreno **1416,4286**. Con `min_area = 1330,7` el
  recocido la tiraba y su masa real la acepta.

## Lo que NO se ha tocado, y está medido

Con `min_area ≥ 450` el recocido devuelve **cero superficies**, mientras la
Path Search encuentra masas de 1200 sobre el mismo modelo. Parecía el
filtro y **no lo es**: de los 102 candidatos que el paseo llega a
construir, el mayor tiene masa 512, así que por encima de ahí su primer
paso no tiene nada que aceptar. El techo lo pone el alcance del paseo.
Queda **fijado como límite medido** (420 responde, 450 no devuelve nada, y
otra búsqueda sí encuentra masa suficiente al mismo umbral), no arreglado:
tocar el alcance del paseo es otro defecto con su propia decisión detrás.

## Riesgo, medido antes de tocar

**Ningún modelo del banco de verificación usa el recocido** — 141 grid, 33
path, 6 block, 6 particle_swarm, 4 auto_refine, **0** simulated_annealing —
así que las 486 filas de la comparativa no pueden moverse por este cambio.
Los otros dos cambios son un test y un comentario.

## Un comentario que llevaba dieciocho versiones mintiendo

`ProjectSettings.surface_filter_kwargs` seguía explicando que `min_area`
«deliberadamente NO está aquí … no puede viajar en un diccionario que todas
las ramas expanden igual». Desde v0.1.129 viaja exactamente así. Corregido
el texto, sin mover el campo: el fallback depende del **método de
búsqueda**, y convertir un ajuste en argumento de búsqueda es el trabajo de
`analysis_runner`, no el de `settings`.

## Qué se probó

- `tests/test_focus_all_searches_v1129.py`: 46 tests, verde. **14 son
  nuevos** (8 de regla 7, 3 de la guarda del recocido, 3 del techo).
- Los nueve archivos que cubren el recocido y las búsquedas
  (`annealing`, `sa_autorefine`, `search_algorithms`, `search_effort`,
  `surface_options`, `face_tie`): 103 tests, verde, **sin mover un dígito**
  — que es lo que la medida de las 75 combinaciones predecía.
- La suite completa, sin filtrar.

## Qué falta por probar

- El banco no se ha regenerado, y la razón está medida (cero modelos con
  recocido), no supuesta.
- El techo del paseo del recocido: fijado, no explicado. Por qué su
  generador no llega más hondo que 512 en un modelo donde hay masas de
  1900 es la pregunta siguiente.
