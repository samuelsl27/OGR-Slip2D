# OGR Slip2D v0.1.450

**La figura del informe de una corrida sísmica marca el mínimo de lo que dibuja (D423).** En una corrida «Calcular
Ky» o Newmark, la figura de cada método contorneaba en cada centro de la rejilla el menor FACTOR, y ponía la estrella
«critical centre» en el centro de la crítica, que es la de menor Ky. La estrella no estaba en ningún mínimo de lo
dibujado. Medido con 0.1.449 (8b3ce6d) y `medir_d423.py` del banco en el caso de la ficha: el talud de ejemplo con
c = 20 kPa, una rejilla 5×5×6 (252 círculos) y Bishop.

| corrida | 0.1.449: lo contorneado, su mínimo y la estrella | ahora |
|---|---|---|
| sin Ky, norma 1,05 | el menor factor; 1,4559 en (34, 29); estrella en (34, 29) | igual, byte a byte |
| Ky, norma 1,05 | el menor factor; 1,4559 en (34, 29); estrella en (40, 45), sobre 1,5463 | el menor Ky; 0,2601 en (40, 45), bajo la estrella; escala «minimum Ky» |
| Ky, sin norma | el menor factor; 1,5287 en (34, 29); estrella en (40, 45) | el menor Ky; 0,2941 en (40, 45) |
| Newmark, norma 1,05 | el menor factor; estrella en (40, 45) | el mayor desplazamiento; 1,2163 cm en (40, 45), bajo la estrella; escala «maximum Newmark displacement [cm]», con el rojo en el extremo crítico |

Por decisión de la propietaria es la opción (a), solo en la figura. Interpretar, Minimum Surfaces del lienzo y la
vista `minimum_per_centre` del API siguen con el factor: van a la ficha nueva D438, que se abre al cerrar esta.
**Ningún número cambia.** Es la vigesimotercera versión de la tanda P10 y la tercera del plan aprobado el
2026-11-14.

## 0. Lo que se encontró

- **Paso 0, sobre 0.1.449:** `medir_d423.py` da la tabla de la ficha (medida con 0.1.435). Con el árbol nuevo, la
  estrella está en el mínimo de lo contorneado en los cuatro bloques. La línea «identidad de v1339» del guion mide
  factores, así que con (a) solo vale sin Ky, y ahí sigue en True.
- **Con Newmark, el mayor desplazamiento de cada centro, contado tal cual.** El plan decía «el extremo de cada centro
  según el objetivo» (`score`, el Ky). Para un bloque rígido es la misma superficie, porque el desplazamiento no crece
  con el Ky (Newmark 1965). Con «Permitir desplazamiento talud arriba» no lo es: el desplazamiento es neto, y eso es
  D437, abierta en 0.1.449. Contando el desplazamiento tal cual, la escala «desplazamiento máximo» dice la verdad
  también con esa opción. La estrella sigue en la crítica de la búsqueda, y con talud arriba puede no estar en el
  máximo: es D437.
- **La rejilla del test no es la que decía el plan.** Con la 3×3×2 (48 círculos), en cada uno de sus 12 centros la
  superficie de menor factor es también la de menor Ky, y ningún centro tiene dos desplazamientos. Dos mutantes de la
  regla sobrevivían: «el factor de cada centro» y «el menor desplazamiento». Medidas ocho rejillas: la 4×4×4 ponía la
  estrella en el menor factor, y la 3×3×6 (112 círculos, 0,6 s) cumple las tres condiciones. Allí la estrella está en
  (40, 45) y el menor factor en (40, 38,33), un centro distingue las dos reglas y otro tiene dos desplazamientos. Dos
  premisas del test lo comprueban. El `d423()` del banco usa la 3×3×2 de la ficha, que basta para la estrella y la
  escala.
- **La primera discriminación fallaba por la firma** (`grid_data` recibe ahora el proyecto) y no por lo que mide, y el
  control también fallaba con 0.1.449. El test llama a `grid_data(sr)`, que con un proyecto métrico da lo mismo, y lee
  lo dibujado por la clave que lo lleve. El caso imperial pasa por `method_figures`, que es quien entrega el proyecto.
- **La revisión adversaria (un agente) encontró en el primer borrador una alta, tres medias y tres bajas.** Todas son
  del propio cambio, menos la última, que es anterior. Arregladas:
  - **(alta) un coste cuadrático.** `reported_value` preguntaba el rótulo de la corrida por cada superficie, y
    preguntarlo lee `critical`, que recorre todas. Medido: con 4746 superficies, más o menos la rejilla de Ej_1,
    `grid_data` y `has_centres` tardaban 8 s cada una (antes 0,01). El diálogo del informe llama a `has_centres` al
    abrirse, y la figura lo repite por método. Ahora el rótulo se pregunta una vez y se pasa (`caption=`), y un caso
    cuenta las llamadas;
  - **(media) con menos de tres centros con Ky, la figura perdía la rejilla entera, estrella incluida.** El diálogo
    apagaba «Modelo y área de búsqueda» con la razón falsa «ninguna búsqueda tiene rejilla». Medido con c = 72 kPa:
    dos centros con Ky. Ahora que haya rejilla depende de los centros evaluados, como en una corrida de factores, y no
    de cuántos tienen Ky;
  - **(media) un talud que el registro no mueve** (todo a 0 cm) se contorneaba entero en la mitad crítica de los
    colores, con una escala de −2e-14 a 2e-14 cm. Ahora un campo constante no se contornea: quedan los puntos y la
    estrella;
  - **(media-baja) el caso de Newmark era casi degenerado.** A 0,3 g, 11 de los 12 centros estaban a 0 cm, y el mutante
    «el desplazamiento de la superficie de menor factor» sobrevivía. El test usa ahora 0,6 g: se mueven 7 centros, y
    en uno la de menor factor no es la que más se mueve, con su premisa escrita;
  - (baja) textos que seguían diciendo «factor mínimo» de una figura sísmica: el tooltip del diálogo del informe y su
    castellano, `docs/mcp/herramientas.md`, la cabecera de `report_figures.py`, dos docstrings, y la escala por
    defecto de `_draw_grid` para una rejilla dibujada sin rótulo, que ahora la da por su magnitud;
  - (baja) un centro sin ningún Ky perdía su punto. Ahora todos los centros evaluados tienen su punto, y solo se
    contornean los que tienen el número;
  - (baja, anterior) `valid()` incluye superficies inadmisibles y `critical` no, así que una inadmisible de menor Ky
    ganaría su centro. Con factores pasaba igual, y en los casos medidos no hay ninguna. Se reporta sin tocar.

## 1. Qué cambia

- **El motor** (`ogr_slip2d/interpretation.py`):
  - `critical_per_centre`, la superficie que dibuja cada centro según lo que informa la corrida: el menor factor
    (`minimum_per_centre`, el mismo objeto), el menor Ky o el mayor desplazamiento de Newmark;
  - `reported_value`, el número de una superficie bajo ese rótulo.

  Las dos reciben el rótulo de quien ya lo tiene (`caption=`).

  `minimum_per_centre` no cambia.
- **La figura** (`ogr_api/report_figures.py`, `ogr_api/render.py`):
  - `grid_data(search_result, project=None)`: sin Ky, el diccionario de siempre. Con Ky o Newmark, `values` en lugar
    de `fos` (nada lee un Ky como factor), `quantity`, `centres` (todos los centros evaluados), y con Newmark `unit` y
    `cmap` `RdYlBu_r`. Hay rejilla si la búsqueda evaluó al menos tres centros;
  - `method_figures` pasa el proyecto y pone la escala: «minimum Ky», o «maximum Newmark displacement [cm]» con la
    unidad del proyecto;
  - `_draw_grid` contornea `values` cuando están, con su paleta, salvo que sean constantes. Pone un punto en cada centro
    evaluado, y sin rótulo nombra la escala por su magnitud.

  Ningún argumento nuevo en las dos llamadas (la ventana y `report_generate`).
- **El tooltip** «Superficie crítica de cada método» del diálogo del informe dice qué contornea, con su castellano;
  también `docs/mcp/herramientas.md`.
- **Castellano:** «Ky mínimo» y «desplazamiento de Newmark máximo».

## 2. Qué se probó

- **`tests/test_report_figures_seismic_v1450.py`** (19 casos, unos 4 s). Referencia por identidad, como la de v1339:
  - **Ky:** lo contorneado es el menor Ky de cada centro, recontado en el test desde `sr.valid()`. Su mínimo es el Ky
    de la crítica, la estrella está en su centro, la figura dibuja esos valores y la escala los nombra;
  - **Newmark:** el mayor desplazamiento de cada centro, recontado. Su máximo es el de la crítica, el rojo queda en el
    extremo crítico, y la unidad es la del proyecto (pulgadas en un proyecto imperial, por la puerta de la figura);
  - **sin Ky:** `grid_data` y los bytes del PNG son los de las funciones de 0.1.449, copiadas y sustituidas en el mismo
    proceso;
  - las palabras de la escala, en castellano;
  - `minimum_per_centre` no se mueve con Ky, y en una corrida de factores la regla nueva es esa misma;
  - dos premisas: la estrella no está en el menor factor, y el caso distingue las reglas, con Ky y con Newmark;
  - lo de la revisión: el rótulo se pregunta una vez; con dos centros de Ky quedan la rejilla y la estrella, y
    `has_centres`; un talud que no se mueve no se contornea; cada centro evaluado tiene su punto; y la escala sin
    rótulo dice su magnitud.
- **Discriminación:** en el árbol de 0.1.449, sin el buscador editable, fallan 14 de 19. Uno falla porque la regla
  nueva no existe, y los de la revisión fallan porque prueban lo que el borrador hacía. Pasan las dos premisas,
  `minimum_per_centre` y los dos controles.
- **Mutantes** (`mutants_d423.py`, en el banco): 15, todos muertos:
  - el factor de cada centro en toda corrida;
  - el menor desplazamiento;
  - el número de la corrida bajo la clave de un factor;
  - el desplazamiento siempre en cm;
  - la paleta sin invertir, en el diccionario o en el dibujo;
  - la escala de un factor con Ky;
  - la escala del desplazamiento sin unidad;
  - la figura sin el proyecto;
  - y los seis de la revisión: Newmark con el desplazamiento del menor factor, el rótulo por superficie, la rejilla
    perdida con pocos centros de Ky, un campo constante contorneado, los puntos solo donde hay número, y la escala
    por defecto de un factor.

  «Newmark dibuja el desplazamiento del menor Ky de cada centro» se deja fuera por equivalente con estos datos (sin
  talud arriba, D437).
- **Vecinos**, con los patrones `report_figures report seismic newmark render spanish_paths f3b_ops results_query i18n
  voice_and_terms version_consistency` (cada uno comprobado con `--list`; `interpretation` y `minimum_per_centre` no
  casan con nada, D431), más `mcp_server` por la guía del agente: 402 casos en verde en 25 archivos.
- **La suite entera** con `--jobs 4`, tras los arreglos de la revisión: **7652 casos, 7651 en verde, 0 fallos y 1
  omitido**, sin fugas ni tramos muertos. La serie no toca (28 commits desde la última).

## 3. Qué queda

- La siguiente es D406 (0.1.451): `surface_evaluate` no da el desplazamiento de Newmark ni las notas sísmicas.
- **D438**, que se abre al cerrar esta ficha (decisión de la propietaria): Interpretar (`_draw_fos_heatmap` y su
  leyenda), Minimum Surfaces del lienzo y la vista `minimum_per_centre` del API, en una corrida con Ky, siguen con el
  factor. Recoge el hallazgo sin ficha de D400, «`minimum_per_centre` ordena solo por factor».
- **Reportado y sin tocar:** con talud arriba, la estrella (la crítica de la búsqueda) puede no estar en el máximo
  contorneado (D437).
