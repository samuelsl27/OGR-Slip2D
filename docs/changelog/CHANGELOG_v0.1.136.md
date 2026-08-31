# OGR Slip2D v0.1.136

**Defecto D34.** Tres de los cuatro sitios que localizan la cara del talud
elegían entre dos caras igual de inclinadas por orden de iteración, y el ajuste
de dirección de rotura no podía hacer nada al respecto. Ya están los cuatro
compartiendo la misma regla. Pero **el caso concreto que el defecto llevaba dos
revisiones nombrando no existe**, y averiguar por qué costó más que el arreglo.

---

## 1. El caso del problema 75 no era un caso: la rama estaba muerta

La ficha decía «un solo caso concreto en el banco: el 75». El encargo, remedido
en 0.1.127, decía dos: el 75 y el 109. Son **cero**, y la razón es la misma
para los seis modelos de bloque del banco.

`BlockSearch` usa la cara del talud para **una sola cosa**: fijar `x_lo`/`x_hi`,
la banda horizontal de las ventanas **automáticas**. Y esas ventanas son la rama
`else` de

```python
if use_user_objects:     # search.py:2965
    ...                  # muestrea de los objetos dibujados
else:
    for k in range(self.num_groups):
        bx0 = x_lo + (x_hi - x_lo) * k / self.num_groups
```

Los **seis** modelos de bloque del banco —7, 8, 9, 20, 75 y 109— llevan
`BLOCK_SEARCH_OBJECT` dibujados. Con objetos dibujados `use_user_objects` es
cierto, `x_lo`/`x_hi` no se leen jamás y la cara del talud **no decide nada**.

Lo caro de esto es el diagnóstico que se dio por bueno. La ficha citaba como
síntoma que la búsqueda del 75 «da lo mismo se declare lo que se declare, A/B
bit a bit», y lo atribuía al desempate ausente. El A/B era correcto y la
atribución era falsa: **daba lo mismo porque el código de la cara no se
ejecutaba**. Un A/B nulo no distingue entre «el ajuste no se consulta» y «lo
que el ajuste decide no se usa», y aquí eran las dos cosas a la vez, en el
mismo modelo, con la segunda tapando a la primera.

## 2. El 109 tampoco, y D50 nunca fue el tapón

El encargo avisaba de que el 109 —el nuevo del inventario— podía estar tapado
por D50, que deja su búsqueda en 0 superficies válidas de 5000, y pedía
comprobarlo antes de tocar nada. No hace falta llegar ahí: el 109 declara
`R2L`, sus tres tramos empatados tienen sus pies en x = 14,473 · 15,602 ·
16,731, y la regla elige `min(toe_x)` = el primero, que es **exactamente el que
la comparación estricta ya elegía**. El desempate es un no-op en ese modelo por
sí solo, con D50 o sin él.

## 3. El inventario también estaba mal, y por una razón instructiva

El recuento del encargo se hacía sobre la polilínea EXTERNAL **cruda**, y el
código no recorre eso: recorre el **perfil superior** que devuelve
`_ground_profile` → `ground_surface`. Contando sobre lo que el código mira de
verdad:

| Búsqueda | Encargo | Medido |
|---|---|---|
| `grid` | 21 | **18** |
| `path` | 6 | 6 |
| `block` | 2 | 2 |
| `auto_refine` | 1 | 1 |
| `slope`, `annealing`, `particle_swarm` | 0 | 0 |

Los tres de más eran fondo y laterales del contorno contándose como «caras
empatadas». No cambia ninguna conclusión —ninguna de esas familias localiza
cara— pero un inventario que mide otra cosa es la clase de dato que sostiene
una decisión equivocada durante cincuenta versiones, como ya pasó con m-alpha.

## 4. Lo que sí se arregló

El desempate de `PathSearch` —el bloque que v0.1.73 escribió— sale a
`ogr_slip2d/failure_direction.py` como `steepest_face_index(top, project)`, y
los **cuatro** sitios lo llaman:

| Sitio | Qué decide |
|---|---|
| `slope_frame()` | pie, coronación, β y las ventanas → **Slope Search y Particle Swarm**, dos búsquedas de un solo sitio |
| `BlockSearch._run` | `face_lo_x`/`face_hi_x` → las ventanas automáticas |
| `PathSearch._run` | pie, coronación, rangos de Slope Limits, `hdir` |
| `SimulatedAnnealingSearch._run` | `x1`/`xN`, los extremos fijos de toda polilínea |

Misma tolerancia relativa `1e-6`, mismo criterio —la masa sale por el pie, así
que se toma la cara cuyo pie cae del lado hacia el que se declara que se
mueve—. **Una cara que gana de verdad sigue ganando** en las dos direcciones,
que es la mitad del invariante que había que proteger y no la que se ve.

### La guarda que no estaba en el encargo: terreno llano

`s >= steepest * (1 - 1e-6)` con `steepest` **cero** empata **todos** los
tramos, y entonces la dirección elegiría un extremo donde no hay cara ninguna.
No es hipotético: **23 modelos del banco** tienen el perfil superior
enteramente horizontal —los muros de geotextil 87 a 94, cuya cara es vertical y
por tanto no aparece como pendiente— y hoy están a salvo sólo porque todos usan
`grid`. La función devuelve el primer tramo no vertical cuando no hay cara, que
es lo que la comparación estricta devolvía. Es una guarda **más estrecha** que
el código que se extrae, y cierra ese flanco también en `PathSearch`.

## 5. La sonda: el arreglo muerde, y hubo que salirse del banco para verlo

Como el banco no puede mover un dígito, la evidencia sobre geometría real se
midió sobre una copia del `modelo_bloque.ogr` del 75 **sin su objeto de
bloque**, que es lo que resucita la rama de ventanas automáticas. Bishop, misma
semilla, 5000 candidatas:

```
                cara elegida            FoS       válidas
antes  R2L      tramo 1 (40,31)-(58,25)  0,640339    3928
antes  L2R      tramo 1 (40,31)-(58,25)  0,640339    3928   <- idénticas
después R2L     tramo 1 (40,31)-(58,25)  0,640339    3928   <- sin cambio
después L2R     tramo 3 (114,25)-(132,19) 0,421599   4401
```

El «antes» es la regla 7 en su forma más pura: dos declaraciones opuestas, el
mismo número dígito a dígito. El «después» conserva `R2L` intacto —que es el
predeterminado, así que ningún proyecto guardado cambia al reabrirse— y hace
que `L2R` trabaje la bancada que declara.

## 6. Hallazgo nuevo, medido y NO corregido

Los desplazamientos de las ventanas de `BlockSearch` son asimétricos —`-0,3` de
`face_w` por delante, `+0,5` por detrás (`search.py:2951-2952`)— y el
comentario dice que van «desde un poco antes del pie hasta un poco pasada la
coronación», o sea que suponen **el pie a la izquierda**. En las dos bancadas
del dique del 75 el pie está a la **derecha**, así que la mitad ancha cae
delante del pie, en el aire, tanto antes como después de este cambio.

Es **preexistente** y este arreglo no lo agrava —en la sonda las válidas suben
de 3928 a 4401—, así que se reporta y no se toca: v0.1.118 dejó esas fracciones
quietas a propósito porque **no tienen fuente documentada**, la referencia hace
que el usuario dibuje las ventanas y no ofrece alternativa. Cambiarlas sería
afinar hacia un número conocido.

## 7. Fuera de alcance, dicho a propósito

`ogr_core/geometry/transforms.py:173` tiene el mismo patrón de «el tramo más
inclinado», con el mismo `>` estricto. Sirve a una transformación de contorno
de la interfaz, no a una búsqueda, y no se ha tocado.

---

## Tests

`tests/test_face_tie_search_v1136.py`, 11 tests. El invariante tiene dos
mitades que tiran en sentidos opuestos, y las dos se afirman:

- **Rompe el empate**: en las **cinco** búsquedas que localizan cara, el mismo
  terraplén simétrico da dos búsquedas distintas según la declaración, y la
  `R2L` reproduce lo que daba el `>` estricto.
- **La trampa**: un talud de una sola cara da el mismo resultado **bit a bit**
  (`rel_tol=1e-12`) se declare lo que se declare, en las cinco. Es lo que
  mantiene los casos validados fuera del alcance del cambio.
- Sobre la función: el empate, la banda relativa por los dos lados (0,4995 no
  empata con 0,5; una parte en 1e9 sí, y a escala ×1000 igual), el terreno
  llano y un perfil sin ningún tramo utilizable.
- `TestTheEmbankmentTieIsBrokenByTheSetting` de
  `test_failure_direction_v173.py` sigue verde **sin tocarla**, que es la
  prueba de que la extracción fue una extracción.

El test compara contra la regla vieja **escrita en el propio test** en vez de
contra un número recordado: `_strict(top)` reimplementa el `>` de antes, y así
la afirmación «`R2L` no cambia nada» es comprobable y no una promesa.

## Verificación

- `tests/_runner.py face_tie` → 11/11.
- `tests/_runner.py search failure_direction annealing block slope multimodal
  noncircular` → 292/292, los 20 archivos que fijan hoy el comportamiento de
  los sitios tocados.
- Suite completa sin argumentos.
- Banco: **no se re-corre nada porque nada puede moverse**, y el argumento es
  de código, no de cronómetro — el desempate sólo se activa con
  `len(tied) > 1`, y eso no ocurre en ninguna búsqueda del banco que localice
  cara. `generar_comparativa.py` **lee** `resultados.json`, no re-ejecuta, así
  que por sí solo no habría probado nada.
