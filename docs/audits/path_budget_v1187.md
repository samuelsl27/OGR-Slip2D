# El presupuesto de la búsqueda de camino — censo de OGR 0.1.187 (D160)

Medido el 2026-09-22 con `_tools/censo_presupuesto_d160.py` (SOLO MIDE) sobre el
banco de verificación del manual 02, cuya mitad no circular la escribió 0.1.185.

## La pregunta

D160 dice que `PathSearch._run` para en el número de superficies **válidas**
(`ogr_slip2d/search.py`, bucle `while result.valid_count < self.num_surfaces and
attempts < max_attempts`, con `max_attempts = num_surfaces × 20`), de modo que el
tamaño de la muestra es función de la tasa de validez del evaluador: **un motor
que hace converger más superficies llega antes a la cuota y recorre menos
secuencia**. Eso es cierto y está medido en el 085 (38 461 → 34 175 generadas
entre 0.1.178 y 0.1.181, con Bishop inmóvil como control nulo).

La pregunta que el censo contesta es la otra: **cuántas filas del banco están de
verdad asfixiadas por su techo de intentos, y cuántas llegan a la cuota.**

## Los dos denominadores, y por qué hay dos

| | filas `path` | por techo | por cuota | con foco | por techo **con foco** |
|---|---|---|---|---|---|
| todas | 88 | 17 | 71 | 36 | **17 de 17** |
| solo reproducibles | 85 | 14 | 71 | 33 | **14 de 14** |

La diferencia son **exactamente tres filas**: el escenario `3b` del problema 078
está declarado **no reproducible**, lo midió 0.1.147, y sus tres filas paran por
techo con **cero** válidas. Contarlo o no mueve el titular de 85/14 a 88/17.

Esto no es una curiosidad de contabilidad: **dos recuentos independientes de este
mismo censo discreparon justo en eso** antes de que la herramienta existiera, y
la discrepancia (88/85 y 17/14) era el escenario no reproducible entero. Los 71
por cuota coincidían al dígito en los dos.

El denominador de filas también tiene dos valores según lo que se cuente: **100
filas de método** con población archivada y **97** con `fos`. Las tres de
diferencia son las mismas del `3b`.

## El resultado, y no es el que la ficha esperaba

**Ninguna fila sin objeto de enfoque llega al techo.** Todas las que llegan lo
tienen — 14 de 14, o 17 de 17 con el no reproducible dentro. Entre las que
alcanzan la cuota, `generadas` va del **5,81 % al 65,03 %** del techo: ninguna
está cerca.

Pero el foco es **necesario y no suficiente**: **33 filas lo tienen y solo 14
mueren por techo**. Lo que cierra el presupuesto es foco × tasa de aceptación.

O sea: **hoy el presupuesto lo cierra el filtro de foco, no la tasa de validez
del evaluador.** El mecanismo que D160 describe es real y está medido, pero sobre
este banco es **latente**: ninguna fila está al borde de perder su cola.

### Las filas que paran por techo

| prob | escenario | métodos | válidas de 5000 | generadas de 100 000 |
|---|---|---|---|---|
| 077 | caso2_piezometrica | bishop, spencer | 1101 | 28 870 |
| 078 | 1b | bishop, gle, spencer | 1363 | 38 429 |
| 078 | 2b | bishop, gle, spencer | 170 | 37 110 |
| 078 | 3b *(no reproducible, 0.1.147)* | bishop, gle, spencer | **0** | 37 692 |
| 079 | caso1_profunda | bishop, gle, spencer | 934-935 | 17 271 |
| 081 | caso1_profunda | bishop, gle, spencer | 2069-2070 | 22 011 |

## Lo que este censo NO puede medir, y es la razón del cambio de v0.1.187

**La holgura de las 19 filas que llegaron a cuota teniendo foco.** El campo
`generadas` de los resultados es `valid_count + invalid_count`, y el rechazo por
objeto de enfoque hace `continue` **sin tocar ninguno de los dos**, de modo que

    attempts = generadas + rechazadas_por_foco

y el segundo sumando no se archivaba en ningún sitio. Con `focus = 0` la resta es
cero y `generadas` **es** el esfuerzo; con foco, `generadas` es solo una cota
inferior. Para las 14 que mueren por techo sabemos `attempts = 100 000` por la
condición de salida, y las rechazadas por foco salen por aritmética (71 130 en el
077, 61 571 en el 078·1b, 62 890 en el 2b, 82 729 en el 079, 77 989 en el 081).
Para las 19 con foco que llegaron a cuota **no hay forma de saber cuánto margen
les quedaba**.

**Y la aritmética quedó confirmada por medida en cuanto el campo existió.** El
079 · caso1_profunda, re-corrido con 0.1.187, archiva `intentos = 100 000`,
`generadas = 17 271` y **`rechazos_foco = 82 729`** en los tres métodos — el
mismo 82 729 que este informe había deducido restando. La inferencia era
correcta y ahora es un dato.

Dos notas de coste, que van aquí porque las dos son la misma lección de
AGENTS.md: el 079·2 tardó **467 s** contra los 324 s archivados, un +44 % que
parecía del motor y **era contención mía** —había otras cosas corriendo—; el
079·1, lanzado con la máquina libre, dio **301 s contra 304 s**. El reloj total
no es una medida.

Eso es lo que v0.1.187 arregla: `attempts` lo rellenan ahora las siete búsquedas
y `focus_rejected` es un campo propio, los dos publicados en HDF5, CLI, informe,
interfaz y en los resultados del banco.

## La decisión

**Se toma la rama 2 del criterio de cierre de D160**, y las razones son cuatro:

1. **La semántica es la de la referencia**, documentada en el código desde
   v0.1.24 con su referencia detrás, y fijada por tres asserts de
   `tests/test_search_effort_v1103.py` más la clase de migración
   `TestStoredModelsMigrate`, que registra que tres modelos del banco fijan a
   propósito el nombre retirado `path_num_paths`.
2. **El 20× no es un ajuste**: vive en el constructor de `PathSearch` y no en
   `SearchSettings`. Un «modo de presupuesto de generación fijo» tendría que ser
   además un ajuste **visible**, o sería un modo que nadie puede elegir — regla 7
   al revés.
3. **El censo dice que hoy el techo lo cierra el foco**, así que cambiar el
   criterio de parada re-apuntaría 85 filas del banco a cambio de nada medible.
4. **La reconciliación honesta no es cambiar `PathSearch`.** La cabecera de
   `tests/test_acads_validation_v178.py` documenta que «Number of Surfaces» ya
   significa **dos cosas** —generadas en Slope Search, aceptadas en Path Search—
   y que *nada en la interfaz las distingue*. Cambiar Path Search dejaría la
   interfaz igual de ambigua. Publicar los dos números arregla lo que falla.

**Lo que queda reportado y no corregido**: las dos semánticas del mismo ajuste.
Publicar el esfuerzo hace la diferencia legible; no la elimina.

## Qué mide ahora el motor, y con qué identidades

| búsqueda | `attempts` | comprobable como |
|---|---|---|
| Grid | (nx+1)(ny+1)(rinc+1) | identidad exacta |
| Slope | `num_surfaces` (el muestreo; el refinamiento local **no** cuenta) | identidad exacta |
| Auto Refine | ya lo contaba desde v0.1.133 | `y·x(x−1)/2` |
| Block | `num_surfaces` | identidad exacta, presupuesto de GENERACIÓN fijo |
| Path | intentos reales | `attempts − total_count == focus_rejected` |
| Annealing | K × Ngen | fijado antes de la primera evaluación |
| Particle Swarm | `num_iterations × num_particles` | el `total` de su propia barra |

`focus_rejected` cuenta **generación y solo generación**. Un rechazo por foco
dentro de un paseo —el refinamiento local de Slope Search, una propuesta del
recocido, un paso del paseo de *Optimize Surfaces*— no es miembro de la población
y no se cuenta; cada uno de esos sitios lo dice donde se salta.

**La trampa que esto tiene, y que un test ejecuta**: el sitio evidente para el
incremento es dentro de `BaseSearch._focus_rejects`, y es **incorrecto**, porque
`ogr_slip2d/optimize.py` llega a ese método por `getattr` — los rechazos del
paseo de optimización se sumarían a la población de la búsqueda.
`TestAWalkIsNotPopulation` corre la misma búsqueda con la optimización encendida
y apagada y exige que el contador no se mueva.
