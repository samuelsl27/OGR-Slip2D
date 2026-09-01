# OGR Slip2D v0.1.143

**El encargo venía a cerrar un respaldo que se creía inalcanzable, y la
primera medición lo encontró disparándose 11 972 veces en los cuatro
primeros problemas del banco — ninguna de ellas por la causa que el
encargo nombraba.**

Cierra **D48r**, el residuo declarado de D48. Y por el camino aparece el
defecto que lo estaba tapando, que es el que de verdad estaba vivo.

---

## Lo que el encargo decía

Que `_material_at` entregaba el primer material del proyecto para un punto
fuera del dominio, sin decir nada; que el guardia geométrico de 0.1.126 ya
impedía que ninguna superficie del banco llegara ahí; y que por tanto
devolver `None` **no podía mover ningún número**, con una condición de
parada explícita: *si se mueve alguna, PARA — significa que hay una
superficie consultando fuera del dominio que nadie sabía.*

La condición de parada se cumplió antes de escribir una línea de código.

## La medición, que se hizo primero

Una copia instrumentada del repo —aritmética idéntica, solo un registro
añadido— recorriendo el banco. Resultado en los cuatro primeros problemas:

| sitio | consultas fuera del dominio |
|---|---|
| `_material_at` | **10 948** |
| `_column_weight` (bandas) | **1 024** |

Y la clasificación de las 11 972, que es lo que cambia el diagnóstico:

| dónde caían | cuántas |
|---|---|
| por debajo del firme (lo que D48 describe) | **0** |
| **por encima del terreno** | **11 972** |

## La causa no era que las superficies se salieran

Era la consulta. La línea lleva **desde la release inicial v0.1.59** sin
tocarse:

```python
mat = _material_at(project, Vertex(xc, base_y_mid + 0.01))
```

Ese `+ 0.01` existe para separar la consulta de la base y meterla en la
masa deslizante, de modo que una base que corre **a lo largo de un
contacto** tome el material de encima en vez de aterrizar sobre una arista
de región, donde el punto-en-polígono es ambiguo. Es correcto en su
intención y es **absoluto** en su implementación.

Donde la base corre a menos de 0,01 del terreno —las dovelas de los
extremos de **toda** superficie que entra o sale cerca de la tangente— el
salto pasa por encima de la superficie del terreno y pregunta por un punto
**en el aire**:

```
x = 25,9774   y consultada = 25,0003   terreno = 25,0000   firme = 20,0000
```

Tres diezmilésimas fuera. `material_at` contesta `None`, correctamente, y
el respaldo lo tapaba.

## Y el material que entregaba estaba mal 7 de cada 10 veces

Problema 3, **una** búsqueda de Bishop, contando qué daba el respaldo
contra qué hay de verdad en la base:

| daba | era de verdad | veces |
|---|---|---|
| Soil #1 | **Soil #3** | **301** |
| Soil #1 | Soil #1 | 130 |

## Lo más caro: el arreglo del encargo habría sido destructivo

El encargo pedía convertir el `None` en rechazo de la superficie. Con el
`+0.01` intacto eso habría **descartado cientos de superficies legítimas
por búsqueda**, porque el `None` casi nunca significaba «se salió del
modelo»: significaba «la consulta rebasó el terreno». El orden importaba
más que el arreglo, y sólo se supo midiendo antes.

## Lo que se cambió

**La consulta ya no rebasa.** Si el punto elevado cae fuera, se pregunta
otra vez **en la base**. Es exacto —usa el mismo test de regiones en vez de
reconstruir dónde está el terreno—, cuesta una segunda consulta sólo en la
dovela que rebasa, y **la consulta elevada mantiene la prioridad**, así que
el material elegido sobre un contacto no cambia en ningún sitio donde el
salto ya funcionaba.

**`_material_at` devuelve `None` fuera del dominio.** Las dos preguntas que
se contestaban igual quedan separadas: «¿qué hay en un punto de dentro que
ninguna región cubre?» la sigue contestando `Project._material_in` con el
primer material, por convención y sin tocar; «¿qué hay fuera del modelo?»
se contesta que no hay suelo.

**Sin suelo en la base, la superficie se rechaza entera.** Es el mismo
juicio que `water_surface_defined_at` hace desde v0.1.96 para una superficie
de agua que no llega a una abscisa, y está ochenta líneas más arriba en el
mismo bucle. Colocado **antes** de `_column_weight`: una dovela sin suelo no
llega a pesarse.

**El aviso no culpa a quien no es.** `slice_surface` devuelve `None` por
varias causas y la búsqueda escribía una nota culpando al **número de
dovelas** de todas ellas. Una superficie que se fue del modelo, a la que se
le dice que use más dovelas, es un aviso apuntando al culpable equivocado.
El motivo viaja ahora en una lista `reasons` del llamante —nada de estado
de módulo, que es la fuga que existe para impedir la regla 5— y el contador
y la nota son propios. La nota **sólo se emite si ocurrió**.

**Dos invenciones más de la misma familia**, encontradas por la sonda y no
por el encargo:

- `_column_weight`: una banda que ninguna región cubre heredaba
  `materials[0]`. Ocurre por una razón que la propia función se crea —
  `y_top` es la elevación **media** del terreno sobre la dovela (v0.1.96),
  así que donde el terreno sube la banda superior asoma por encima del
  terreno en `x`. La banda es real; lo que faltaba era su material, y es el
  de la banda **de debajo**. Además pesaba a **20,0 kN/m³** una columna sin
  materiales: un número que no pertenece a nada del modelo y que no se
  distingue de un peso específico de verdad. Ahora, sin suelo, no pesa.
  Medido: una columna de 100 unidades enteramente fuera del dominio pesaba
  **11 640 kN/m**; ahora pesa **0**.
- `excess_pore_pressure._loading_bands`: la misma herencia, y ahí decidía
  algo peor que un peso — `weight_creates_excess` es una bandera **por
  material**, así que la sustitución podía **encender o apagar** la carga no
  drenada de una banda que no es de ese material.

## Lo que cuesta la segunda consulta

Se razona, no se cronometra, que es lo que la regla del proyecto pide para
diferencias de este tamaño. La sonda midió que **rebasa el 1,9 % de las
dovelas** (10 948 consultas sobre ~580 000 en cuatro problemas), así que
sólo esa fracción paga una segunda consulta. Y la paga barata: todo
análisis corre dentro de `regions_frozen()`, donde la caché de regiones se
cree sin revalidar su firma — el bloque existe precisamente porque esa
firma era el 41 % de la búsqueda del Ej_2. Lo que se añade es un
punto-en-polígono sobre unas pocas regiones, en el 1,9 % de las dovelas,
contra los ~2,5 ms que cuesta resolver cada una.

## Lo que se movió, medido

A/B del banco: OGR 0.1.142 prístino contra este árbol, **30 modelos
multicapa** de los 106 que hay, 86 pares modelo/método. Los **84 modelos de
un solo material se saltan a propósito y se dicen**: con un único material
la sustitución silenciosa devolvía el material correcto por construcción,
así que ahí no puede haber cambiado nada. Los otros 76 multicapa no se han
corrido; esto es un subconjunto y no una cobertura.

**Los dos lados son deterministas**: dos corridas seguidas de cada uno dan
el mismo número hasta el último dígito, así que lo que sigue no es ruido.

| | antes | después | Δ |
|---|---|---|---|
| P020 `modelo.ogr` Bishop | 1,085978 | 1,086042 | **+0,0059 %** |
| P020 `modelo.ogr` Spencer | 1,091809 | 1,091808 | −0,0001 % |
| P020 `modelo_bloque.ogr` Bishop | 0,950423 | 0,950588 | **+0,0174 %** |
| P020 `modelo_bloque.ogr` Spencer | 1,049310 | 1,049369 | +0,0056 % |

**2 modelos de 30**, y los dos son el problema 20 — *«talud de 4 capas con
costura débil y freático»* (Greco 1996, ej. 5). Que sea justo ése no es
casualidad: es el modelo con más capas del subconjunto, y el error crecía
con el número de capas que la sustitución podía confundir.

**Y va hacia el valor publicado.** El panel de la figura 20.2 publica
Bishop **1,087**:

| | error contra 1,087 |
|---|---|
| antes | −0,094 % |
| **después** | **−0,088 %** |

Los otros 28 modelos no mueven un dígito. Los contadores sí se mueven en
otros cuatro (11, 12, 13, 15 y 19): de una a tres superficies cambian de
válida a inválida o al revés, y en el 15 (Path Search) y el 19 la búsqueda
llega a **generar** unas pocas superficies más, que es lo que se espera de
una búsqueda guiada cuando una evaluación cambia. El mínimo no se mueve en
ninguno de ellos — la misma lección de D21: quitar un filtro puede mover
las válidas sin mover el mínimo, y confundir las dos cosas es cómo se
diagnostica mal un síntoma.

**Ninguna superficie del banco activó la nota nueva: cero avisos de
fuera-del-modelo en los 30 modelos.** Esa mitad de la premisa del encargo
sí era cierta — el guardia de 0.1.126 hace su trabajo, y `_material_at` no
estaba viendo superficies fugadas. Estaba viendo su propia consulta
rebasando el terreno.

## Lo que queda anotado

- **El `+0.01` sigue siendo absoluto**, contra la convención del proyecto de
  que las tolerancias vayan relativas al tamaño del modelo. No se ha
  cambiado su magnitud a propósito: moverla cambia qué material recibe una
  base **cercana a un contacto** en toda dovela del banco, que es un cambio
  numérico con su propia validación. Lo que se ha quitado es su
  consecuencia silenciosa, no su valor.
- **Los 76 modelos multicapa restantes no se han corrido.** El A/B cubre 30.
  Que los cuatro únicos movimientos caigan en el modelo de más capas hace
  esperar que los que faltan se muevan poco o nada, pero eso es una
  expectativa y no una medida.
- **El banco no se ha vuelto a correr entero.** La comparativa
  (`generar_comparativa.py`) **no ejecuta OGR**: sólo lee los
  `resultados.json` que dejó `ejecutar_caso.py`, así que la receta de
  verificación del encargo no podía detectar un cambio aunque lo hubiera.
  Y esos archivos están a versiones mezcladas (el del 27, a 0.1.131). La
  evidencia aquí es la suite entera —**3052 de 3052, sin filtrar**— más
  el A/B medido arriba.

## Archivos

| ruta | qué |
|---|---|
| `ogr_slip2d/slicer.py` | la consulta que no rebasa, `_material_at` sin respaldo, el rechazo, `reasons`, `_column_weight` |
| `ogr_slip2d/search.py` | contador y nota propios del rechazo por salirse del modelo |
| `ogr_core/hydraulic/excess_pore_pressure.py` | banda sin material = sin carga |
| `tests/test_material_domain_v1143.py` | **nuevo**, 15 casos |
