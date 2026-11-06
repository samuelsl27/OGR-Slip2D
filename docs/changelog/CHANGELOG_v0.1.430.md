# OGR Slip2D v0.1.430

**Con una norma de diseño, cada puerta llama a lo que imprime por lo que es. Un coeficiente sísmico crítico o un
desplazamiento de Newmark no son un factor de sobredimensionamiento, ni tienen que superar 1; el factor de la crítica,
sí (D405).**
- **La línea de órdenes** resolvía la precedencia al revés desde 0.1.127 (`if seismic_objective and not factored`):
  - con norma y Newmark ponía «Over-design factor» encima de un desplazamiento en centímetros: 187,2311 para un
    talud que se mueve 1,87 m, medido por la revisión de 0.1.429;
  - y debajo de una nota que decía que el valor «must exceed 1». Se leía del lado inseguro.
  - v0.1.165 lo reportó para Ky y no lo corrigió, porque la ficha de entonces (D96) prohibía tocar la salida de la
    línea de órdenes.
  - 0.1.429 le dio más alcance: con la crítica del usuario imprimía su Ky (0,1556, que no supera 1) y pasó a
    imprimir sus centímetros (que sí).
  - Ahora la columna es «Newmark disp. (cm)» o «Critical Ky», y la nota dice que el valor está calculado con los
    coeficientes parciales y que no es un factor de sobredimensionamiento.
- **La ventana** enseña las dos cosas: el factor de la crítica en la barra de estado y en Resultados (D96 lo quiso
  así, y con norma es un factor de sobredimensionamiento), y el Ky o el desplazamiento en Interpretar. Su primera nota
  decía solo lo del factor. Ahora dice las dos: el Ky (y el desplazamiento) se calculan con los coeficientes
  parciales, y el factor de la crítica es de sobredimensionamiento y debe superar 1.
- **Las demás puertas, por decisión de la propietaria:**
  - Interpretar llama «ODF(0)» («FSD(0)» en castellano) al factor de la crítica con norma, no «FS(0)»;
  - un análisis de un agente pintado en la ventana lleva la misma nota y refresca el panel de notas abierto;
  - la guía del servidor MCP ya no dice que con norma «the number» debe superar 1;
  - la nota se guarda con su código, y el panel la dice en el idioma del momento.
- **Una regla para todas:** `ogr_slip2d/reported.py`, donde ya estaba `reported_caption`:
  - `run_caption` da el rótulo de una corrida de varios métodos;
  - `standard_note` da la frase de la norma con código (`reported.*`), según lo que imprime cada puerta.
- **La línea de órdenes escapa lo que imprime del modelo.** Un registro sísmico llamado «El Centro [/NS]» abortaba
  `compute` con un `MarkupError`, sin tabla ni resultados guardados, y «Clay [weathered]» perdía los corchetes sin
  aviso.
- **Los README** decían que la suite tarda «50 a 90 minutos» («unos 35 frente a 70», «unos 13»). Ahora dan las cifras
  medidas en v0.1.397 que trae AGENTS.md. Es decisión de la propietaria.
- **Ningún número cambia.** Cambian rótulos y frases de las corridas con norma y Ky o Newmark, y lo que la línea de
  órdenes ya no se come.

Es la tercera versión de la tanda P10, y la primera de las dos fichas que añadió la revisión de 0.1.429.

## 0. Lo que se encontró

- **El defecto de la línea de órdenes**, con la regla en el sitio equivocado. `reported_caption` existía desde
  v0.1.194 para que el API y la ventana decidieran el rótulo en un solo sitio, y la línea de órdenes nunca lo
  preguntó. Su propio docstring y el de `reported_quantity` lo contaban como defecto «reported, not copied here».
- **La nota de la ventana:** `_factor_report_notes` recibía solo el informe de la norma. Sin el resultado no podía
  saber qué había calculado la corrida, y escribía siempre la frase del factor. Cuadraba con la barra, pero no con
  Interpretar.
- **Caminos equivocados:**
  - **Mi primera versión daba a la ventana la frase de la línea de órdenes** («the reported value is the critical
    seismic coefficient … not an over-design factor»), justo al lado de una barra que imprime un factor de
    sobredimensionamiento. Partía de una premisa falsa, que llegué a darle a la propietaria al preguntarle: que la
    ventana ya rotulaba el Ky. Solo lo hace Interpretar.
    - La barra y Resultados imprimen `critical.fos` a propósito (D96: «quien arregla la barra es el rótulo»).
    - Lo encontraron por separado dos lentes de la revisión.
    - El test comparaba la nota con la línea de órdenes y no miraba la barra. Ahora la mira, con su número.
  - **Se descartó** dejar las frases en cada puerta con sus variantes: eran copias de la regla, que es como empezó el
    defecto.
  - **Se descartó también** que el test de la ventana llamara a `_factor_report_notes` con los resultados. Es barato,
    pero en el árbol de 0.1.429 habría fallado por la firma y no por lo que dice. Recorre el camino real de fin de
    cálculo (`_on_compute_done`).
  - **La discriminación** falló primero entera con `ModuleNotFoundError`. El test importa los ayudantes de
    `test_newmark_user_surfaces_v1429`, y el arnés (`runpy` del runner) no ponía `tests/` en `sys.path`, como sí
    hace `python tests/_runner.py`. Se corrigió el arnés, no el test.
  - **El test de la ventana se topó con D401:** el panel de Resultados dice «No results yet.» cuando el foco deja la
    búsqueda sin población y la crítica es del usuario. Es una ficha posterior de la tanda. Se comprueba la barra,
    que dice lo mismo por el mismo `fos_label`.
  - **La tolerancia** decía «el 1e-6 del motor», y el factor de Janbu en este plano se aparta 2,6e-6 de la forma
    cerrada; pasaba por el redondeo. Ahora es la media unidad del último decimal más 1e-5, con los residuos medidos.
  - **`d405()` buscaba en la rejilla por defecto del talud de ejemplo:** 1859 círculos, un pool de procesos en cada
    orden. Mi arnés para probarla sin escribir nada no tenía guarda `__main__`, así que cada trabajador del pool
    repetía la comprobación entera. Ahora usa una rejilla de 3×3×3, y el arnés tiene su guarda.
- **Cifras de los README que no eran ciertas, además de la que pidió la propietaria:**
  - «`--jobs 4` takes about 35 minutes against 70 in series»: eran 20,1 y 39,7 en v0.1.397;
  - «`--fast --jobs 4` leaves out the 42 slowest files (737 of the tests) and takes about 13 minutes»: son 37
    archivos desde v0.1.382, y en v0.1.397 dejaba fuera 664 de 6926 tests y tardaba 9,8.
  - Al copiar de AGENTS.md salió que su «de los 134 min, la mitad era la máquina» no cuadra con sus propias cifras:
    sin el proceso colgado eran 87,6, así que la máquina era un tercio. El README dice la cifra, no la fracción.
    AGENTS.md no se toca sin decisión.

## 1. Qué cambia

- **`ogr_slip2d/reported.py`:**
  - `run_caption(results, factor_report)`: `reported_caption` de cada resultado, y NEWMARK si la crítica de algún
    método lleva desplazamiento (la regla de 0.1.429, D397, que estaba escrita en la línea de órdenes);
  - `REPORTED_NOTES`, cinco códigos:
    - `reported.standard_overdesign`, la frase de siempre;
    - para la línea de órdenes, que imprime solo el Ky o el desplazamiento: `reported.standard_ky` y
      `reported.standard_newmark` («the reported value is … with the partial factors applied, not an over-design
      factor»);
    - para la ventana, que imprime además el factor de la crítica: `reported.standard_ky_factor` y
      `reported.standard_newmark_factor` («… computed with the partial factors applied, and the factor shown for the
      critical surface is an over-design factor, not a factor of safety, and must exceed 1»);
  - `standard_note(caption, factor_report, *, shows_factor=False)`: la frase, con el resumen de la norma anidado con
    su código, o None si no se aplicó ninguna.
- **`ogr_cli/__main__.py`:**
  - el rótulo sale de `run_caption` por una tabla de cuatro;
  - la nota sale de `standard_note`, con el mismo realce de antes;
  - las filas no cambian;
  - se conservan los literales que fija `test_seismic_interface_v1127`;
  - todo lo que imprime del modelo pasa por `rich.markup.escape`: notas, motivos, rutas, nombres del proyecto y de
    los materiales, autor y empresa.
- **`ogr_gui/main_window.py`:**
  - `_factor_report_notes(report, results=())` toma los resultados de la corrida, y `_on_compute_done` se los da;
  - la frase es la de la ventana (`shows_factor=True`) y se guarda con su código. Sin resultados, la del factor,
    como antes.
- **`ogr_gui/agent_bridge.py` `show_analysis`:** las notas como en un cálculo de la ventana (la norma primero) y el
  panel de notas refrescado.
- **`ogr_gui/interpret_window.py` `_reported_value`:** recibe el informe de la norma; con norma, «ODF(0)», por `tr()`.
  Sus tres llamadas se lo pasan.
- **`ogr_gui/core_messages.py`:** el catálogo incluye `REPORTED_NOTES`.
- **`ogr_gui/i18n`:**
  - la frase de siempre cambia de clave (`%s` → `{summary}`, por el código);
  - hay cuatro frases nuevas, con «coeficientes parciales» y su punto final (D355).
- **`ogr_mcp/guide.py`:** «a factor is an OVER-DESIGN factor … a Ky or a Newmark displacement stays what it is».
- **Docstrings:** los de `reported_caption`, `reported_quantity` y `fos_label`.
- **Tests cambiados a propósito:**
  - `test_design_factor_report_gui_v1165`: el docstring que pedía no unificar sin leerlo (ya se leyó y se decidió),
    y la clave de la frase traducida;
  - `test_texts_details_v1418`: la clave fija de la nota pasa a las plantillas, leídas del motor.
- **`README.md` y `README.es.md`:** los tiempos de la suite.
- **`tests/test_cli_reported_caption_v1430.py`,** nuevo.
- **`spec/features/009-sarma-dovelas-no-verticales/`:** las versiones de Sarma pasan a 0.1.441–0.1.447, porque la
  propietaria añadió a la tanda P10 la ficha del informe PDF y la del factor que Interpretar llama FS(0) (§3).
- El número en los nueve sitios y el contador de los dos README.

## 2. Qué se probó

- **`tests/test_cli_reported_caption_v1430.py`,** 16 tests. Casi todo su coste es importar la interfaz y construir
  una ventana, compartida.
  - **La referencia:** el plano de 0.1.429 (arena seca, φ = 30°, la polilínea del usuario, un foco que la deja como
    única superficie) con una norma custom que divide tan φ por 1,25. Formas cerradas:
    - el factor, tan φd / tan β = 1,616581;
    - Ky = tan(φd − β) = 0,155628 (Newmark 1965), que la corrida da a 1,5e-7;
    - el desplazamiento del pulso rectangular a ese Ky, 542,4997 cm.
    - Cada número que se imprime se compara con su forma cerrada, a la media unidad de su último decimal más 1e-5
      relativo, por encima de los residuos medidos: 2,6e-6 en el factor, 1,5e-7 en el Ky y 2,3e-7 en el
      desplazamiento.
  - **Línea de órdenes, con la corrida real:**
    - con norma y Newmark: «Newmark disp. (cm)», su valor y la frase del desplazamiento, sin «must exceed 1»;
    - con norma y Ky: «Critical Ky», su valor y la frase del coeficiente;
    - con la norma sola: «Over-design factor» y la frase de siempre (control);
    - sin norma: «Critical FoS» o «Critical Ky», con su valor, y ninguna nota (control);
    - un registro llamado «El Centro [/NS]» que no se puede integrar: la orden termina y lo nombra;
    - un material «Clay [weathered]» en `info`: sale entero.
  - **La ventana, por el camino real de fin de cálculo:**
    - con Ky, la nota es la de la ventana y dice las dos cosas; la barra dice «Over-design factor (…)» con el factor
      en forma cerrada;
    - lo mismo con Newmark, y con la norma sola la frase de siempre;
    - calculada en inglés, el panel la dice en castellano tras cambiar de idioma;
    - Interpretar, en el talud circular de 0.1.165: su resumen dice «ODF(0)» junto al factor de la crítica con
      norma, y «FS(0)» sin ella. En el plano dice «No results to display.» (D401). En el plano, el Ky y el ODF(0) que
      escribe se comparan con sus formas cerradas.
  - **El puente del agente:** con un panel abierto de una corrida anterior, `show_analysis` deja primero la nota de la
    norma, el resto detrás, y el panel la enseña.
  - **La guía MCP** dice que un Ky o un desplazamiento no tienen que superar 1.
  - **El censo de los códigos `reported.*`:**
    - uno por rótulo y puerta, y ninguno sin norma;
    - están en el catálogo;
    - cada uno tiene su español con los mismos campos;
    - en español acaban en punto y no dejan inglés;
    - las dos de la línea de órdenes no dicen «mayor que 1», y las tres de la ventana sí.
- **Discriminación en el árbol de 0.1.429** (`git archive` de 6bc2ef0, sin el buscador editable, `__file__`
  comprobados): fallan 13 de 16.
  - Por lo que dicen, diez:
    - la línea de órdenes con Ky y con Newmark (rótulo «Over-design factor»);
    - las dos del escape (la orden sale con 1, y los corchetes se pierden);
    - la ventana con Ky y con Newmark, y el cambio de idioma;
    - Interpretar («FS(0)»);
    - el puente del agente (sin la nota de la norma);
    - la guía MCP.
  - Por nombre, los tres del censo, porque los códigos no existían.
  - Pasan los tres controles.
- **Vecinos:**
  - norma de diseño, sismo, notas estadísticas, textos, mensajes con código, i18n, español, línea de órdenes,
    Newmark, lo publicado, render del API, voz y términos, nombres y rótulos, notas de las corridas, el puente del
    agente, la guía MCP, Interpretar, las cachés de los tests y la ventana por defecto: 539 de 539 en 39 archivos;
  - con la primera redacción dieron 353 de 354. El que fallaba fijaba la clave vieja (`test_texts_details_v1418`).
- **Suite entera con `--jobs 4`: 7224 en verde, 1 saltado y 0 fallos,** sin fugas ni tramos muertos, sobre el árbol
  final, con la máquina libre. La primera corrida, antes de la revisión, dio 7216 en verde y avisó de un archivo
  lento, `test_mcp_transports_v1195.py` con 111 s. El equipo se suspendió mientras corrían sus dos tests de 62 y 32 s,
  y la segunda corrida no lo repite. La última serie en verde fue hace 8 commits, y toca a los 100.
- **Banco, en seco:**
  - D96, D225, D224, D126 y D58 del manual 02, y D345, D397, D314, D337 y D355 de la raíz: todas CUBIERTO POR TEST;
  - `d405()`, aún sin aplicar al verificador (se añade al cerrar la ficha), probada dentro de él sin escribir nada:
    - con el árbol vivo, CUBIERTO POR TEST: las tres órdenes con su columna y su nota;
    - con el de 0.1.429, SIGUE ABIERTO por lo que imprime: «Over-design factor» y «must exceed 1» en las tres.
- **Revisión adversaria:** tres lentes (la regla y la línea de órdenes, la ventana y las traducciones, y tests,
  changelog y banco) y dos escépticos por hallazgo, 27 agentes. El equipo se suspendió a mitad, y la revisión siguió
  al volver. Salieron 12 hallazgos, 9 distintos.
  - **Confirmados y corregidos:**
    - la nota de la ventana que contradecía a la barra: dos lentes, 4 de 4 votos. La propietaria decidió la frase
      propia;
    - la tolerancia y la cabecera del test, que prometían más de lo que se probaba;
    - `d405()` con la rejilla grande y el arnés sin guarda.
  - **Preexistentes que la propietaria metió en D405:** la guía MCP, el puente del agente, el «FS(0)» de
    Interpretar, la nota sin código y el escape de la línea de órdenes.
  - **Preexistente que va a una ficha nueva:** el informe PDF (alta, 2 de 2): D408.
  - **Para el cierre del banco:** el comentario de `d96()` en el verificador del 02 dice que la interfaz diverge de la
    línea de órdenes a propósito (2 de 2). Desde esta versión ya no es cierto.

## 3. Qué queda

- **El resto de la tanda P10, con lo que decidió la propietaria el 2026-11-06:**
  - D398 (el lienzo a mitad de un dibujo) en 0.1.431, y D399–D404 en 0.1.432–0.1.437;
  - **D408, nueva, en 0.1.438.** El informe PDF de una corrida Ky o Newmark no da el Ky ni el desplazamiento, y su
    «Global Minimums» publica como mínimo el factor de la superficie de menor Ky. En la sonda de la revisión eran
    1,5463, cuando el mínimo de la corrida era 1,4559: un 6 % del lado inseguro. Es preexistente, la misma sección
    del informe que D404;
  - D406 (`surface_evaluate`) en 0.1.439;
  - **D409, nueva, en 0.1.440:** el factor que Interpretar escribe junto al Ky, «FS(0)» u «ODF(0)», es el del kh del
    proyecto cuando este aplica el suyo (punto de abajo);
  - D407 (el rebanador) sigue sin versión;
  - Sarma pasa a 0.1.441–0.1.447.
- **Prueba a mano, para la propietaria:** con una norma y Ky o Newmark, la barra, el panel de notas e Interpretar
  deben decir cosas que cuadren, en los dos idiomas.
- **AGENTS.md** dice «de los 134 min, la mitad era la máquina», y sus cifras dan un tercio (§0). Se corrige en
  0.1.431, por decisión de la propietaria.
- **Preexistentes que vio la revisión (regla 6):**
  - **El «(0)» de FS(0) y ODF(0) es falso cuando el proyecto aplica su propio kh con Compute Ky.** Entonces `.fos`
    es el factor a ese kh (`search.py:1186-1187`). Con kh = 0,10, el resumen dice «FS(0) = 0.988», y el factor a
    kh = 0 es 1,1334. Viene de 0.1.127, y esta versión lo hereda al cambiar el rótulo. **Decidido:** ficha nueva D409,
    al final de P10 (0.1.440).
  - Una corrida Ky con norma sin ningún resultado (su único método no está registrado) sale con 4, «Over-design
    factor» y «must exceed 1» sobre una tabla vacía. Pasaba igual en 0.1.429.
  - La ayuda de `compute` dice «report the critical FoS».
