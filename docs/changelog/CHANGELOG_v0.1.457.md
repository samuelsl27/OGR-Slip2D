# OGR Slip2D v0.1.457

**El talud de `examples/quick_slope.py` declara la dirección de rotura que da su terreno (D426).** `build_demo_slope`
construía a mano, desde 0.1.59, una segunda copia del talud de ejemplo con la dirección por defecto, «De derecha a
izquierda», cuando su terreno es más alto a la izquierda (y = 25 en x = 0 frente a y = 15 en x = 50). Cada corrida suya
por la puerta del análisis (`run_analysis`, la que usan la ventana, el agente y los tests), y `project_validate`,
llevaban el aviso `model.failure_direction_r2l`: «puts the crest on the right, but the ground surface is higher on the
left». El propio `main()` del ejemplo llama a `GridSearch.run`, que no lo daba. El talud del núcleo, `build_demo_project`, declara «De izquierda a derecha» desde
0.1.329 (D328).

Por decisión de la propietaria (opción a del prompt), el ejemplo **es** ahora ese talud con su nombre:
`build_demo_slope` devuelve `build_demo_project(name="Demo homogeneous slope")`. Hay un solo talud de ejemplo.

Medido con 0.1.456 (24e46be) y `_auditoria/P10_D419_D428/medir_d426.py` del banco, con sus logs de 0.1.456 y 0.1.457:

| | 0.1.456 | ahora |
|---|---|---|
| dirección del ejemplo | `RIGHT_TO_LEFT` | `LEFT_TO_RIGHT` |
| aviso de dirección en la corrida y en `project_validate` | sí | no |
| Path de 5 con Janbu, el factor | `0x1.4f3678903d37fp+0` | el mismo |
| las 18 críticas de nueve búsquedas, Bishop y Janbu, con las dos direcciones | iguales bit a bit | iguales |
| los REPRODÚCELO de D400, D401, D404, D406 y D408 | — | los mismos bit a bit |

**Ningún número cambia.** La dirección la leen pocas decisiones, y ninguna está en este talud: una grieta (su empuje
de agua y el extremo que recorta), el sentido de un soporte y, cuando dos caras empatan, la cara de partida de Path
Search y los límites de ángulo de Block Search. Es la
trigésima versión de la tanda P10 y la quinta y última del plan aprobado el 2026-11-14.

## 0. Lo que se encontró

- **El paso 0 da con 0.1.456 lo de 0.1.435.** El fragmento del prompt da `RIGHT_TO_LEFT 0x1.4f3678903d37fp+0` con el
  aviso. El guion da 0 de 18 casos movidos y cinco veces «same bits».
- **El censo de quién usa el ejemplo ha crecido, como dijo el plan.** Lo usan 11 archivos de tests (el prompt decía
  cuatro) y 13 comprobaciones del banco (d396, d397, d398, d400, d401, d404, d405, d406, d408, d418, d419, d423 y
  d424), más `d328`, que mide el talud del núcleo. Lo usan también ocho guiones de medida del banco, que no son
  comprobaciones (`medir_d417`, `medir_d418`, `medir_d418_criterios`, `medir_d419`, `medir_d423`, `medir_d424`,
  `medir_d437` y `mutants_d426`). Se corrieron antes y después del cambio:
  - los 11 archivos, más `console_language_demo` y `model_notes`: los mismos 280 casos en verde;
  - las 14 comprobaciones: la misma salida byte a byte.
- **Lo que cambia del ejemplo, medido campo a campo frente a 0.1.456**, además de la dirección:
  - el color del material, de #a0522d al del talud del núcleo, #d4a373;
  - el proyecto nace sin cambios por guardar (`is_dirty` False);
  - los vértices del exterior y del nivel freático son enteros, como los escribe `build_demo_project`: (0, 0) en vez
    de (0.0, 0.0). Cambia lo que se escribe, no los números:
    - `main()` imprime `bbox = (0, 0, 50, 25)` en vez de `(0.0, 0.0, 50.0, 25.0)`;
    - el `.ogr` guarda `0` en vez de `0.0`, y al abrirlo sigue siendo un entero;
    - la «List of Coordinates» del informe PDF escribe `0` donde escribía `0.000` (lo vio la revisión).

    Ningún número se mueve:
    la copia vieja del ejemplo (vértices reales) y la nueva (enteros) dan el mismo factor, la misma superficie y las
    mismas cuentas bit a bit, con el mismo motor y en un mismo proceso. Se comprobó en la rejilla de `main()`, en una
    rejilla con Bishop, Janbu y Spencer, en Path y en Block;
  - por el cambio del ejemplo, `main()` imprime lo mismo que con 0.1.456 (FoS 1.1331, el mismo círculo), salvo esa
    línea y la ruta del archivo de resultados. La línea de la población cambia aparte, por el punto siguiente.
- **El docstring del ejemplo estaba mal:** nombraba (50, 25) y (25, 15), que no son vértices, dibujaba la coronación
  hasta (50, 25) y decía «slope 1:2» de una cara 1:1. Ahora dice los seis vértices de verdad y la cara 1V:1H, como el
  docstring de `build_demo_project`.
- **(baja, anterior) `main()` imprimía una cuenta que no cuadraba:** «Evaluated 118 surfaces (valid: 90, invalid:
  57)», y 90 + 57 = 147. 118 era `len(evaluations)`, las superficies rebanadas, y las inválidas incluyen las 29
  rechazadas antes de rebanar, que no dejan evaluación. Salía igual con 0.1.456. **Por decisión de la propietaria
  entra en 0.1.457:** ahora dice «Generated 147 surfaces (valid: 90, invalid: 57)», con el censo del motor. Las
  generadas son `total_count`. Las válidas son `analysed_count`: convergidas y aprobadas por las comprobaciones,
  las que pueden ser críticas. Las demás son inválidas, como las cuenta el informe de la referencia: una superficie
  que una comprobación descarta cuenta como inválida aunque convergiera.
- **La revisión adversaria (un agente)** no encontró fallos del código.
  - Comparó el ejemplo viejo y el nuevo, con el mismo motor y en un mismo proceso, en 23 configuraciones: los nueve
    métodos, las siete búsquedas, sismo, Ky y Newmark, una norma, cargas, soportes, retroanálisis, los dos análisis
    probabilísticos y la malla de elementos finitos. Las poblaciones enteras salen iguales bit a bit, también
    distinguiendo un entero de un real, y el `.h5` de `main()` es idéntico.
  - Las 15 comprobaciones del banco dicen lo mismo con los dos ejemplos, salvo `d426`, que cierra.

  Encontró, y se arregló:
  - **(baja, del test) una declaración que moviera solo las superficies no críticas pasaba,** porque el caso de D328
    comparaba solo la crítica. Ahora compara todas las que la búsqueda analizó, con su factor y su geometría, en una
    rejilla de 64 círculos: tarda la mitad;
  - **(baja) seis frases:**
    - «cada corrida suya llevaba el aviso», que no lo daba el propio `main()`;
    - «solo tres decisiones» leen la dirección, y faltaban el extremo que recorta una grieta y los límites de ángulo
      de Block Search;
    - el docstring del ejemplo, que no decía los vértices enteros y citaba una medida que no era la de enteros frente
      a reales;
    - el docstring del módulo, que decía que el ejemplo construye el talud;
    - «well under a second» en la cabecera del test;
    - «los vértices del exterior», cuando lo son también los del nivel freático.
- **Se reporta sin tocar** (lo vio la revisión):
  - **(baja, anterior) el informe PDF escribe un entero sin decimales.** `_fmt` (`ogr_core/report/report_generator.py`)
    pasa un entero por `str()`. Lo hace ya *Cargar talud de ejemplo*, y un modelo con vértices enteros y reales (el
    talud de ejemplo con un vértice editado) mezcla `0` y `0.000` en la misma tabla;
  - **(informativo) un modelo hecho desde el ejemplo que lea la dirección sí se mueve, y en el sentido correcto.** La
    declaración de antes contradecía la geometría.
    - Con un pilote tangente a la superficie, Bishop pasa de 1,0372 a 1,3039 (+25,7 %), y el ejemplo nuevo con «De
      derecha a izquierda» reproduce el viejo bit a bit.
    - Con una grieta cambian, en unos 1e-13, cinco o seis superficies no críticas de unas 42 por método: las de los
      dos extremos a la misma cota. La crítica no cambia.

    Ningún test ni ninguna comprobación añaden al ejemplo nada que lea la dirección.

## 1. Qué cambia

- **`examples/quick_slope.py`:** `build_demo_slope` devuelve `build_demo_project(name="Demo homogeneous slope")`. El
  docstring dice los vértices, la cara 1V:1H, por qué delega y qué cambia (el color, `is_dirty` y los vértices
  enteros). El del módulo dice que el ejemplo toma el talud, no que lo construye. Fuera los imports que quedaban sin
  uso.
- **`examples/quick_slope.py`, `main()`:** la línea de la población la escribe `surface_counts(result)`, nueva:
  generadas, válidas e inválidas, por `total_count` y `analysed_count`. `main()` devuelve ahora el resultado de su
  búsqueda (antes, `None`), para que el test lea lo que imprimió. El resto de lo que imprime no cambia.
- Ninguna cadena nueva de la interfaz, ningún ajuste ni ninguna acción nuevos. No cambia ningún código del programa:
  el motor, el núcleo y las interfaces son los de 0.1.456.

## 2. Qué se probó

- **`tests/test_quick_slope_example_v1457.py`** (6 casos; 0,5 s el caso de D328, 0,9 s el de `main()`, y nada los
  otros). No abre ninguna ventana. La rejilla del caso de D328 es de 16 centros y 64 círculos, y el de `main()` corre
  el ejemplo en una carpeta temporal.
  - **La referencia son dos identidades:**
    - la declaración es la que da el terreno, leída de los dos extremos del contorno exterior y no de la regla del
      motor, y la regla (`_failure_direction_note`) no dice nada;
    - la de D328: cada superficie que la búsqueda analizó, con su factor y su geometría, es la misma bit a bit con las
      dos declaraciones, en un mismo proceso.
  - **El control:** con la declaración al revés, la regla avisa con su código.
  - **Un solo talud:** el ejemplo es el talud del núcleo campo a campo, con los `id` y la fecha enmascarados, y nace
    sin cambios por guardar.
  - **Lo que imprime `main()`:**
    - la línea de la población suma, y sus tres números son los del censo del motor (`invalid_summary`: generadas,
      válidas y rechazadas), en un caso en que las rebanadas no son todas;
    - y una superficie que una comprobación descarta cuenta como inválida, con un resultado de prueba en que
      `valid_count` y `analysed_count` difieren. En el talud de ejemplo coinciden, y sin este caso los dos mutantes
      que cambian una cuenta por otra vivían.
- **Discriminación:** en el árbol de 0.1.456, sin el buscador editable, fallan 5 de los 6 casos: cuatro por lo que
  hacen y uno por el nombre nuevo (`surface_counts`). Pasa el control de D328: el factor ya era el mismo con las dos
  declaraciones.
- **Mutantes** (`mutants_d426.py`, en el banco): 11, todos muertos:
  - el ejemplo de 0.1.456 (a mano, «De derecha a izquierda»);
  - su copia propia con «De izquierda a derecha» puesta a mano (la otra forma de la opción a, que deja dos taludes);
  - el ejemplo que declara «De derecha a izquierda», con el nombre del talud del núcleo, o con cambios por guardar;
  - el talud del núcleo que vuelve a «De derecha a izquierda» (D328 deshecha, en el núcleo y en el ejemplo);
  - la regla que no avisa nunca;
  - de la revisión, una declaración que mueve solo una superficie no crítica;
  - y, de la línea de `main()`: la de 0.1.456, las válidas por `valid_count` y las inválidas por `invalid_count`.
- **Vecinos:** los 11 archivos que usan el ejemplo, `console_language_demo`, `model_notes` y el test nuevo (cada
  patrón comprobado con `--list`).
- **Banco:** las 14 comprobaciones que usan los dos taludes dicen lo mismo byte a byte antes y después.
- **La suite entera** con `--jobs 4`. Se corrió una vez tras la revisión (7744 casos, 7743 en verde) y otra tras el
  arreglo de la línea de `main()`, que la propietaria decidió después: **7746 casos, 7745 en verde, 0 fallos y 1
  omitido**, sin fugas ni tramos muertos. La serie no toca (35 commits desde la última).
- **Se reporta sin tocar:** la segunda corrida terminó con «SLOW, NOT IN tests/_slow.txt»: `test_sa_autorefine_v117`
  (122 s) y `test_mcp_server_v1195` (119 s) pasaron de 90 s. No los toca esta versión, y las dos corridas anteriores
  (la de 0.1.456 y la primera de esta) no lo dijeron. Al terminar, ningún proceso cargaba la máquina (el que más,
  0,09 núcleos). La lista no se reescribe aquí: se reescribe a propósito al preparar una versión, y la decisión es de
  la propietaria.

## 3. Qué queda

- El plan del 2026-11-14 (D416, D417, D410, D425 y D426) está terminado. En P10 siguen D407, D427 y D428
  (0.1.458–0.1.460), y D429–D445 sin versión. Sarma va en 0.1.461–0.1.467.
