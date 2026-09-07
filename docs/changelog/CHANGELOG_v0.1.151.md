# OGR Slip2D v0.1.151

**El encargo de D64 decía que la guarda de D48r leía la tangencia exacta con
un vértice del contorno como «fuera del modelo», y que hacía falta darle una
tolerancia. La guarda no era la causa: contestaba bien. Lo que había eran DOS
comparaciones absolutas más arriba, y la segunda es que el punto-en-polígono
no estaba fallando —estaba preguntando por un polígono cuya esquina el
constructor de regiones había movido media celda de su propia rejilla.** El
agujero medido son 5,8 µm de radio, 58 de 1001 radios barridos; con las dos
tolerancias hechas relativas, cero. Ningún número que hoy se dé se mueve.

---

## Lo que había

Problema 67 del banco (USACE 2003, ejemplo F-5). El vértice (0 · 100) es
donde el terreno inclinado se junta con el llano **y** donde arranca el
contorno de material. Un círculo de centro (101 · 359):

```
R = 277,9     -> 1,322210   razones: []
R = 277,9964  -> None       razones: ['outside_model']
R = 278,0     -> 1,320817   razones: []
```

Una décima de milímetro entre un número y ninguno, con superficie aceptada a
los dos lados, y una razón que dice que la superficie se sale del modelo
cuando lo que hace es tocarlo. Barriendo 1001 radios a paso 1e-7 alrededor
del radio exacto por el vértice (R₀ = 277,996402854425): **58 rechazados**,
todos en una banda de 5,8 µm por debajo de R₀.

El 277,9964 no es del manual —el panel publica 278,000— sino que lo derivó el
banco preguntando «¿qué radio pasa por el pie?». Por eso **ninguna fila del
banco dependía de este defecto**: es de motor, y le pasa a quien teclee ese
radio.

## Lo que la medición encontró, y no era lo que decía el encargo

### 1 · Un `1e-9` absoluto fabricaba una dovela de 3,6 µm

Traza del troceado en el filo:

```
R = 277,9964   cortes con el terreno   x_l = 0,000004235872   x_r = 317,228228716124
               cortes con el contorno de material: [0,000007856634 · 201,999992143366]
               primeras fronteras: [0,000004235872 · 0,000007856634 · 6,516136 · ...]

R = 278,0      x_l = -0,009900504852 ; un solo corte de material, en 202,0099
```

En el filo el círculo corta la **envolvente del terreno** y el **contorno de
material** a 3,6 µm uno de otro: dos curvas distintas que se juntan en ese
vértice. `slicer.py` conservaba el segundo corte porque su prueba de «corte
que sólo roza un extremo» era absoluta:

```python
if x_l + 1e-9 < x < x_r - 1e-9:
```

3,6 µm no es un roce con esa vara —y son **1,1e-8 del ancho de rotura**—, así
que nacía una primera dovela de 3,6 µm. La tolerancia de fusión once líneas
más abajo (`tol = 1e-3 * width`) ya era relativa y lo decía en su comentario
desde v0.1.66; la del extremo se había quedado atrás.

### 2 · El punto-en-polígono no fallaba: la esquina se había movido

`ogr_core/geometry/regions.py` redondea **todos** los nodos de la subdivisión
planar a una rejilla antes de poligonizar:

```python
grid_size = max(diag * 1e-8, 1e-12)
merged = set_precision(merged, grid_size)
```

Medido sobre esta geometría (`diag` = 535,239199, `grid` = 5,352392e-06):

```
esquina dibujada en (0 · 100)
  -> guardada en (0 · 99,99999733577782) en LAS DOS regiones que se juntan ahí
     desplazada 2,664e-06 = 0,498 celdas
```

El punto medio de la base de la astilla, (0,000006046 · 100,000000706),
quedaba **por encima** de la esquina guardada. Estaba de verdad fuera de los
dos polígonos. `_material_at` contestaba `None` correctamente, la guarda de
D48r hacía su trabajo y tiraba la superficie entera.

**Esto convierte la elección de tolerancia en una derivación y no en un
ajuste.** El suelo de la meseta medida *es* la rejilla del constructor:

| profundidad de sonda | contra `grid` | medido |
|---|---|---|
| `1e-9 · diag` | 0,1 celdas | **no** rescata |
| `1e-8 · diag` | 1 celda | rescata |
| `1e-7 · diag` | 10 celdas | rescata, mismo factor |
| `1e-6 · diag` | 100 celdas | rescata, mismo factor a seis cifras |

Lo mismo por el otro lado: el corte de roce se tira desde `1e-7 · ancho` y no
antes (la separación son 3,6 µm de 317 m), y de `1e-7` a `1e-3` el número no
se mueve.

### 3 · La sonda hacia abajo devuelve la capa de DEBAJO (regla 6)

El `+0,01` existe para que una base sobre un contacto tome el material de
**encima**, y hay un test que lo fija (`test_material_domain_v1143.py`). La
tercera consulta hace lo contrario. Se acepta, y queda escrito, porque una
base que llega a la tercera pregunta cabe dentro de **una celda** de la
rejilla del propio modelo: la dovela que rescata es más estrecha que la
resolución de las regiones que consulta y **pesa exactamente cero**. No puede
mover un dígito. Pero es una desviación de un convenio que este proyecto
tiene testeado, y no se descubre después.

## Qué cambia

Las dos tolerancias son **la misma cantidad derivada**, `_model_grid_tol` =
`1e-6 · diag`: cien veces la rejilla con la que se construyeron las regiones
que se están consultando. Una constante, un porqué.

- **`_slice_boundaries`** — la prueba de roce del extremo pasa de `1e-9`
  absoluto a `grid_tol`. Un corte más cerca de un extremo que la rejilla con
  la que se construyeron las regiones deja un trozo que el modelo de regiones
  no puede resolver: no separa nada, sólo hace una astilla. Se deriva
  **dentro** de la función, que ya recibe el proyecto, en vez de pasarse: un
  llamante al que hay que decirle la tolerancia es un llamante que puede
  dársela mal.
- **`_base_material`** — las tres consultas de material salen de dentro del
  bucle de dovelas y pasan a una función con nombre, para que se lean juntas
  y para que la tercera sea comprobable sin pasar por el troceado. La tercera
  pregunta **hacia abajo** y sólo hacia abajo: es lo que impide reabrir D48,
  porque una base por debajo del fondo sigue por debajo al mirar más abajo.
- **`TOUCHED_MODEL_EDGE`** — el rescate viaja en la misma lista `reasons`,
  **en una superficie que se devuelve, no que se rechaza**. El contrato de
  `reasons` pasa de «por qué se rechazó» a «lo que el troceador tuvo que
  decidir, el rechazo incluido». Los llamantes prueban pertenencia del motivo
  que les importa, así que una cadena más es inerte para quien no la busca.
- **`BaseSearch._on_model_edge_note()`** — aviso propio, contador propio,
  emitido **sólo si ocurrió**. Deliberadamente distinto del de
  `outside_model`, porque dicen lo contrario: aquí no se descartó nada.

## Qué se probó

`tests/test_material_domain_corner_v1151.py`, 21 casos. El fixture se
construye **desde coordenadas** —el banco está fuera de git— y reproduce el
modelo del 67 exactamente: con R = 278,0 da 1,320817 / 1,316834 / 1,316577 /
1,340820 en los cuatro métodos, **+0,0000 %** contra los cuatro valores
registrados del banco.

Con el motor de 0.1.150, **13 de los 21 fallan**. Los que pasan antes y
después son los discriminadores y los controles de D48, que es exactamente lo
que tienen que hacer:

```
✗ test_the_knife_edge_radius_is_sliced
✗ test_it_daylights_on_the_vertex_from_the_other_side_too
✗ test_no_sliver_slice_survives
✗ test_the_mirror_gives_the_same_factor
✗ test_the_rescued_radius_lies_between_its_neighbours
✗ test_it_lies_between_its_two_IMMEDIATE_neighbours
✗ test_the_verdict_does_not_depend_on_the_units   (rechazada a escala 0,001)
✓ test_the_published_case_still_reproduces        (el ancla, antes y después)
✓ test_a_surface_below_the_floor_of_the_model_is_still_refused
✓ test_the_refusal_holds_where_the_probe_is_deeper_than_the_lift
```

**Los anclajes son identidades, no números capturados.** El único número
absoluto del archivo es el **1,332 publicado** por USACE (2003) F-5, y se
afirma al 1 % sobre el radio que ya evaluaba. Todo lo demás:

- **continuidad de FoS(R)**: el radio rescatado tiene que caer entre los
  factores de los dos radios que lo flanquean (1,320872 y 1,320817). Cae:
  1,320850;
- **simetría de reflexión**: el modelo con todas las x negadas tiene que dar
  el mismo factor, y lo da;
- **invariancia de escala del VEREDICTO**: ×0,001 y ×1000, los seis casos
  troceados. Con una tolerancia absoluta discreparían — que es el sentido de
  la regla. El *factor* no se compara entre escalas, y el docstring dice por
  qué: la cohesión no escala con la longitud;
- **la sonda no llega más lejos que su tolerancia**: en un modelo de 10 km la
  sonda vale 0,0141 y **supera** el `+0,01`, así que ahí es la más profunda de
  las tres. A 0,9 · tol, 1,5 · tol y 100 · tol por debajo del fondo la
  superficie se sigue rechazando; a 0,5 · tol se sigue aceptando, que es el
  control que impide que los otros tres sean vacuos.

Barrido de radios sobre el 67, hoy contra ahora — **ni un dígito** en los
que ya evaluaban:

| R | 0.1.150 | 0.1.151 |
|---|---|---|
| 277,5 · 277,9 · 277,99 · 277,996 | 1,327843 · 1,322210 · 1,320955 · 1,320872 | idénticos |
| **277,9964** | **None** | **1,320850** |
| 278,0 · 278,01 · 279,0 | 1,320817 · 1,320726 · 1,311888 | idénticos |

**Suite entera, sin argumentos: 3188/3188, cero fallos.** Y las áreas
vecinas por separado, 223/223 (`slicer`, `slice_`, `tangent_surface`,
`slide_validation`, `license`, `version_consistency`, `material_domain`).
**Ningún test existente necesitó cambiarse**: `test_material_domain_v1143.py`
pasa sus 15 sin tocarlo.

Una cosa que sí obligó a elegir: `test_slice_cuts_v166.py` sustituye
`_slice_boundaries` por un doble con la firma de cinco argumentos. Pasarle la
tolerancia habría roto ese test, así que se deriva **dentro** de la función,
que ya recibe el proyecto. Es mejor diseño por su cuenta —la función tiene
todo lo que necesita— y de paso no toca un test que no va de esto.

## Banco

`_tools/medir_d64.py`, nuevo: una pasada instrumentada que **no escribe ningún
`resultados*.json`** y que, sin cambiar el comportamiento, anota en cada
superficie si alguno de los dos cambios la habría alterado. Fuerza la búsqueda
secuencial —la instrumentación no viaja a los procesos hijos del pool— y corre
un método por modelo, porque el troceado no depende del método.

**194 archivos de modelo, 0 fallos.** El cambio 1 —el único que puede alterar
una superficie que hoy se acepta— toca **6 archivos y 43 superficies**:

| problema | modelo | superficies con astilla |
|---|---|---|
| 016 | `modelo.ogr` | 4 |
| 042 | `modelo.ogr` · `modelo_sin_grieta.ogr` | 3 · 1 |
| 055 | `modelo.ogr` | 1 |
| 107 | `modelo.ogr` | 27 |
| 108 | `modelo.ogr` | 7 |

### El A/B: esos seis, más dos de control, con el motor cambiado

Los dos lados en el mismo árbol, intercambiando **sólo** `slicer.py` y
`search.py` por los de 0.1.150 (`git show HEAD~1`), con paralelismo puesto en
los dos. Un método por modelo:

| modelo | FoS antes | FoS después | descartadas antes → después | bases en el borde |
|---|---|---|---|---|
| 016 `modelo.ogr` | 1,1166786289902662 | **idéntico** | 3 → **0** | 10 |
| 016 `modelo_path.ogr` | 1,0188807108803868 | **idéntico** | 107 → **106** | 1 |
| 042 `modelo.ogr` | 1,9214502824533628 | **idéntico** | 0 → 0 | 0 |
| 042 `modelo_sin_grieta.ogr` | 1,9155527987811856 | **idéntico** | 0 → 0 | 0 |
| 055 `modelo.ogr` | 1,2986624655812777 | **idéntico** | 0 → 0 | 0 |
| 107 `modelo.ogr` | 1,3736677092866260 | **idéntico** | 0 → 0 | 0 |
| 108 `modelo.ogr` | 1,7802598882952558 | **idéntico** | 0 → 0 | 0 |
| 014 `modelo.ogr` | 1,4059518588270135 | **idéntico** | 6 → **1** | 42 |

**Idéntico quiere decir idéntico**: el mismo `float`, dígito a dígito, y el
mismo círculo crítico en los ocho. El recuento de válidas e inválidas también
coincide en siete de los ocho; el que cambia es `016/modelo_path.ogr`, que pasa
de 2553 inválidas a 2552 — la superficie recuperada, que no era el mínimo.

Y lo que sí cambia, que es el objeto del arreglo: **el motor deja de tirar
superficies legítimas**. Nueve en estos tres modelos —3, 1 y 5—, ninguna de
ellas el mínimo, y las 106 que le quedan al `016/modelo_path` se siguen
rechazando porque de verdad se van del modelo.

### Una corrección, porque el número que publiqué primero era mío y estaba mal

La columna «rescatadas» de `medir_d64.py` dice **1 en los 194 modelos**, y de
ahí salió una lectura equivocada: que la tercera consulta casi nunca se usa.
No mide eso. El instrumento sólo vuelve a probar las superficies que el motor
**ya arreglado** rechaza, así que no ve ninguna de las que la sonda salva antes
de llegar al rechazo. La medida buena es el aviso del propio motor: **42 bases
en el 14, 10 en el 016, 1 en el `016_path`**. La red se usa, y bastante más de
lo que decía mi primera lectura.

## Fontanería: los tres números de los README estaban viejos

`README.md` y `README.es.md` decían **1729 tests**, **43 600 líneas** de
implementación y **23 400 de tests**. Lo real es **3188**, **71 500** y
**61 800**. No es que hayan crecido con esta versión —los 21 casos nuevos son
21— sino que llevaban viejos desde mucho antes, y un número que nadie
actualiza es un número que nadie cree.

## Qué falta

- **La corrida completa del banco con esta versión.** El A/B de arriba mide
  los ocho modelos que podían moverse; los otros 186 siguen con sus
  `resultados*.json` de 0.1.147, y la comparativa mezcla versiones hasta
  que se rehaga. El 67 sí está rehecho: 1,320817 / 1,316834 / 1,316577 /
  1,340820, sus cuatro filas en `OK` a −0,84 / −0,84 / −0,79 / −0,31 %.
- **El `+0,01` sigue absoluto.** Moverlo cambia qué material recibe una base
  cercana a un contacto en toda dovela del banco: cambio numérico con su
  propia validación, como ya dejó escrito 0.1.143.
- **`_material_in` depende del orden de las regiones** junto a una esquina
  redondeada: las dos regiones que se juntan ahí llevan el mismo vértice
  guardado, y gana la primera de la lista. Reportado, no tocado.
- **`ogr_slip2d/surface.py` tiene el mismo `x_l + 1e-9` absoluto** en otra
  función. Hermano del que se ha arreglado aquí.
- **`rapid_drawdown.py` llama a `slice_surface` sin `reasons`** en tres
  sitios: un rechazo por `outside_model` ahí sigue siendo invisible.
- **Los avisos del motor no pasan por `tr()`** y la interfaz enseña sólo el
  primero, en la barra de estado. El aviso nuevo sigue esa práctica; el hueco
  se anota, no se amplía.
- **Los contadores de aviso parecen perderse cuando la rejilla paraleliza, y
  eso es anterior a esta versión.** `_parallel_grid_run` funde de cada parte
  sólo `evaluations`, `valid_count`, `invalid_count` y `attempts`; los
  contadores viven en el objeto `search`, del que cada proceso hijo tiene una
  copia, y esas copias mueren con el proceso. Si es así, el aviso de D48r
  (v0.1.143) y el de dovelas (v0.1.135) llevan desde entonces sin salir en
  ninguna búsqueda de rejilla que paralelice — y el nuevo tampoco saldría.

  La evidencia que hay: la lectura de esas seis líneas, y que **los nueve
  archivos del banco que llevan escrito el aviso de `outside_model` en 70,
  74, 78, 79, 81 y 82 son todos `resultados_no_circular*.json`**, que no
  pasan por ese camino. No está confirmado con una medida directa: hace falta
  un modelo de rejilla que sí rechace, y el banco no tiene ninguno registrado
  — lo que es, precisamente, lo que predice el defecto. Se reporta antes de
  tocarlo, como pide la regla 6, y necesita su propia medición.
