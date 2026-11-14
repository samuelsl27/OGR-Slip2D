# OGR Slip2D v0.1.449

**El informe PDF de una corrida Ky o Newmark dice qué número es cada uno (D408).** En una corrida «Calcular Ky» o
Newmark, la crítica es la superficie de menor Ky, y su factor no tiene por qué ser el menor. El informe no preguntaba
qué había minimizado la corrida. Escribía el factor de la crítica bajo el rótulo de la norma, como si fuera el mínimo,
y no daba el Ky ni el desplazamiento en ninguna parte. Medido con 0.1.448 (26ed20c) en el caso de la ficha: el talud
de ejemplo con c = 20 kPa, una rejilla 5×5×6 (252 círculos), Bishop, la norma custom de 1,05 y la sinusoide de 0,3 g,
2 Hz y 4 s.

| corrida | 0.1.448 | ahora |
|---|---|---|
| Ky | «Over-design Factor 1.5463» (el menor factor admisible es 1,4559, un 6 % más bajo) y nada del Ky | «Critical seismic coefficient 0.2601», «Critical surface: the one with the lowest Ky of this method», «Over-design Factor of this surface 1.5463» |
| Newmark | lo mismo | además, delante, «Newmark displacement 1.216 cm» |
| encabezado de «Slice Data» y pie de figura | «— ODF = 1.5463» | «— Ky = 0.2601» y «— Newmark displacement = 1.216 cm» |
| «Design Standard», con norma | el resumen y sus notas | además, la frase del panel de notas de la ventana: el Ky y el desplazamiento llevan los coeficientes parciales, y el factor de la superficie es un factor de sobredimensionamiento |

Sin Ky ni Newmark, el informe no cambia un carácter. **Ningún número cambia:** es lo que el informe escribe. Es la
vigesimosegunda versión de la tanda P10 y la segunda del plan aprobado el 2026-11-14.

## 0. Lo que se encontró

- **Paso 0:** el REPRODÚCELO da la salida del prompt. Se midió con 0.1.447 al planificar, y con el árbol de 0.1.448 lo
  confirma `d408()` del banco («Over-design Factor | 1.5463», sin el Ky).
- **La puerta.** El núcleo no puede importar `ogr_slip2d.reported`. **Por decisión de la propietaria (opción b)**, la
  regla baja al núcleo (`ogr_core/project/reported.py`): `reported_caption`, `run_caption`, `standard_note` y sus
  constantes.
  - `ogr_slip2d.reported` reexporta todos los nombres, y el motor, el API, la línea de órdenes y la ventana siguen
    importando de él.
  - No va a `ogr_core/report/`, cuyo `__init__` importa el generador y reportlab.
  - `test_api_render_results_v1194`, que sustituye `reported_caption` en `ogr_slip2d.reported` para ver que la ventana
    delega, sigue en verde. `run_caption`, ya en el núcleo, llama a la del núcleo.
- **Dos reglas más bajan con ella**, porque el informe las necesita y vivían en la ventana:
  - `displacement_in_units`, la conversión de `_reported_value` palabra por palabra: `Quantity.SMALL_LENGTH`, y cm sin
    proyecto o si la conversión falla. Interpretar la pregunta ahora, con la misma salida;
  - `factor_kh`, el kh con el que se calculó el factor (`details["kh"]`, que guardan los nueve métodos). Interpretar no
    la usa todavía: su «FS(0)» es D409, la siguiente de esta familia.
- **El factor que acompaña al Ky** es el del kh del proyecto, y solo es el de kh = 0 si el proyecto no aplica ninguno
  (D409). Por decisión de la propietaria, el informe lo escribe como dato de la superficie («of this surface»), nunca
  como mínimo ni como «(0)». Con un kh propio lo dice: «…, kh = 0.1». Se lee del resultado y no del proyecto abierto
  (la regla de 0.1.127), y un caso lo comprueba cambiando el kh del proyecto después de calcular.
- **La frase de la norma** (decisión de la propietaria) es `standard_note(…, shows_factor=True)`, la que escribe el
  panel de notas de la ventana (`MainWindow._factor_report_notes`) junto al factor de la crítica. Va por el cálculo
  (`run_caption`): el desplazamiento de cualquier método lo hace un cálculo de Newmark (D397). Solo sale con Ky o
  Newmark y si algún método tiene crítica. Sin Ky ni Newmark, el informe de un cálculo con norma sigue sin esa frase.
- **Las palabras** son las de la ventana. «Critical seismic coefficient», «Newmark displacement», «Critical surface» y
  «Ky» ya tenían su castellano. Las nuevas son tres: «the one with the lowest Ky of this method» («la de menor Ky de
  este método») y las dos del factor «of this surface».
- **El mutante de D424 «Slice Data back to the kept heading»** se anclaba en el texto del encabezado, que esta versión
  reescribe. Se reancla en lo que no cambia, y los 14 siguen muriendo.
- **La revisión adversaria (un agente)** no encontró nada grave. Reprodujo las cifras, el «no cambia un carácter» sin
  Ky (A/B de los párrafos frente a 0.1.448, en los dos idiomas) y la puerta del API por subproceso. Encontró:
  - **(media) «which moves the most» era falso** con «Permitir desplazamiento talud arriba»: el desplazamiento es
    neto, no decrece con el Ky, y midió superficies de Ky mayor que se mueven más (4 de 152 en un caso). La fila decía
    de la crítica de Newmark que es «la que más se mueve». Ahora dice lo que hace la búsqueda: la de menor Ky. **Lo de
    fondo es anterior y se reporta sin tocar:** con esa opción, la búsqueda minimiza el Ky y no busca la que más se
    mueve (`search.py`, desde 0.1.127);
  - «of the run» era falso en un cálculo de varios métodos: cada bloque da el menor Ky de su método. Ahora dice «of
    this method»;
  - un mutante sobrevivía: la frase decidida por el primer método y no por el cálculo. Ahora un caso lo mata, con un
    primer método sin crítica y el segundo con desplazamiento;
  - con norma y sin ningún Ky, la frase hablaba de un Ky y un factor que el informe no enseña. Ahora no sale;
  - textos: «la frase de Interpretar» (es la del panel de notas), un comentario que decía que Interpretar pregunta
    `factor_kh`, la cifra de cuánto se aparta Janbu de las cuñas en la cabecera del test, la versión de la medida, y
    dos docstrings.

## 1. Qué cambia

- **Núcleo** (`ogr_core/project/reported.py`, nuevo): la regla de qué es el número de una corrida, más `factor_kh` y
  `displacement_in_units`. `ogr_slip2d/reported.py` reexporta.
- **El informe** (`ogr_core/report/report_generator.py`). Cada sitio que escribía `crit.fos` pregunta
  `reported_caption` de su método:
  - en «Global Minimums», `_seismic_rows` da la cabecera (el desplazamiento, el Ky y por qué es la crítica), y el
    factor va después de la fila de D404, «of this surface»;
  - en «Slice Data» y en los pies de figura, `_headline` da el número de la corrida;
  - en «Design Standard», la frase de la norma, con Ky o Newmark y alguna crítica.
- **Interpretar** (`_reported_value`) pregunta `displacement_in_units`. Ya no importa `Quantity`.
- **Castellano:** tres claves nuevas en el bloque del informe.

## 2. Qué se probó

- **`tests/test_report_seismic_v1449.py`** (21 casos, unos 4 s), contra Newmark (1965), en el plano de 0.1.429 y en
  forma cerrada:
  - el Ky a tan(φd − β), 0,155628 con la norma de ÷1,25, y a tan(φ − β) sin ella;
  - el desplazamiento al pulso rectangular, 542,4997 cm con la norma;
  - el factor de la cuña, tan φ / tan β;
  - cada uno en el bloque, en «Slice Data» y en el pie de figura, en inglés y en castellano;
  - **«no lo llama mínimo»:** dos planos del usuario con c = 5 kPa, cuñas rígidas en forma cerrada. A, con Ky 0,458506
    y F 3,862921, es la crítica; B, con Ky 0,489749 y F 1,854131, tiene el menor factor. Con la tolerancia del método
    a 1e-8, Janbu da las dos cuñas (6e-11 y 9e-10 en el factor). El informe da el Ky de A y su factor como de A, y el
    de B en ninguna parte;
  - **con el kh del proyecto** (0,10): el rótulo lo dice, y el número es la cuña a 0,10 (1,454067), no a 0 (2,020726).
    Se lee del resultado, no del proyecto;
  - la frase de la norma con Ky y con Newmark; la del cálculo con un primer método sin crítica; ninguna sin crítica, y
    ninguna sin Ky;
  - un proyecto imperial: el informe e Interpretar dan las mismas pulgadas;
  - la regla, del núcleo: el motor reparte los mismos objetos;
  - **el control:** un cálculo de factor con norma, como siempre. El texto a texto `_V1354` de v1355 sigue en verde.
- **Discriminación:** en el árbol de 0.1.448, sin el buscador editable, fallan 18 de 21. Diecisiete fallan por lo que
  miden, y uno porque el módulo del núcleo no existe. Pasan la premisa de las dos cuñas, el control y «sin crítica no
  hay frase» (0.1.448 no escribía ninguna).
- **Mutantes** (`mutants_d408.py`, en el banco): 17, todos muertos:
  - el bloque con el factor otra vez;
  - sin desplazamiento, y el desplazamiento siempre en cm;
  - el kh nunca dicho, leído como cero o leído del proyecto;
  - el factor siempre «de seguridad»;
  - «Slice Data» y los pies con el factor;
  - la frase de la norma ausente, la de una puerta sin el factor, en todo cálculo con norma, decidida por el primer
    método, o sin crítica;
  - Interpretar con su propia conversión;
  - el motor con su propia regla.

  Los 10 de D404 y los 14 de D424 siguen muriendo.
- **Vecinos**, con los patrones `report newmark seismic core_layering reported_caption api_render interpret
  material_tables_units spanish_paths voice_and_terms i18n version_consistency` (cada uno comprobado con `--list`;
  `interpret_window` no casa con nada, D431 otra vez): 534 casos en verde en 35 archivos.
- **La suite entera** con `--jobs 4`: **7633 casos, 7632 en verde, 0 fallos y 1 omitido**, sin fugas ni tramos
  muertos. La serie no toca (27 commits desde la última).

## 3. Qué queda

- La siguiente es D423 (0.1.450): la figura de una corrida sísmica contornea el factor y pone la estrella en el centro
  de menor Ky. El pie de esa figura ya dice el Ky.
- **Reportado y sin tocar:**
  - con «Permitir desplazamiento talud arriba», la crítica de Newmark es la de menor Ky y puede no ser la que más se
    mueve (la búsqueda, desde 0.1.127). Por decisión de la propietaria, va a una ficha nueva, D437, al final de P10
    y sin versión;
  - un cálculo Ky con norma y sin ningún Ky dice «No valid critical surface found.», como antes.
