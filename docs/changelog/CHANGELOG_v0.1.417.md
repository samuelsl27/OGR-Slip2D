# OGR Slip2D v0.1.417

**El informe PDF lleva la fecha de creación en hora local y con el formato de la de generación, «Archivo» dice la
ruta del proyecto guardado (o «sin guardar»), el texto va en DejaVu Sans incrustada y ningún título se queda solo al
pie de una página (D351).**

Es la primera de la tanda P8o (D351, D355, D361, D360, D363 y D370). La ficha sale de la quinta prueba de la interfaz
(H11 de `INFORME_prueba_GUI_0.1.355.md`). Decisión de la propietaria (2026-11-03): la ruta completa si el proyecto
se guardó; si no, la fila sigue y dice «sin guardar».

Ningún número del informe cambia. El texto tampoco, fuera de las dos filas de la ficha. El pie sigue diciendo
AGPL-3.0-or-later.

## 0. Lo que se encontró

- **La fecha de creación** era el sello guardado tal cual: `Project.__init__` lo escribe con
  `datetime.utcnow().isoformat()`, en UTC y con microsegundos («2026-10-22T15:16:13.558375»). La de generación,
  justo debajo, salía en hora local y como «22/10/2026, 17:17:28».
  - `utcnow` está obsoleto desde Python 3.12. Se cambia por `datetime.now(timezone.utc).replace(tzinfo=None)`, que
    escribe exactamente el mismo texto: el sello guardado no cambia de forma, y un `.ogr` viejo se lee y se escribe
    igual.
- **«Archivo»** imprimía `project.name`. El proyecto sí sabe dónde está guardado (`Project.file_path`, que rellenan
  Guardar y Abrir, en la ventana y en el API), así que no hacía falta cambiar ninguna firma.
- **Las fuentes** eran las estándar de reportlab (Helvetica), que no se incrustan y se escriben en WinAnsi.
  - ² y ³ existen en WinAnsi, y pdfium los extrae bien: el fallo era del visor que no tenía la fuente.
  - σ, φ, α y ≤ no existen en WinAnsi. reportlab los resolvía con la fuente Symbol.
- **El título huérfano.** `section()` añadía el título y la raya sin decir que iban con lo siguiente, y los títulos
  de método («Método: …») tampoco. Medido con el modelo de `test_report_spanish_v1355`, barriendo los comentarios
  del resumen para mover los títulos por el pie de la página:
  - con 0.1.416, «Global Minimums» queda solo al pie con 0 líneas, es decir, en el propio informe del test;
  - con otro número de líneas le pasa lo mismo a «Method: Bishop Simplified».
- **La raya cruzaba la tabla.** La raya era una tabla de una celda de 174 mm, el ancho de la página menos los
  márgenes, y la tabla de válidas/inválidas medía 164 mm. Las dos van centradas, así que la raya sobresalía 5 mm por
  cada lado.
  - Al medirlo salió otra cosa: el marco de reportlab rellena 6 pt por lado, así que el ancho útil es 169,8 mm. La
    raya, las tablas de propiedades, de dovelas y de clave–valor, y las figuras medían 174 mm y se salían del marco
    unos 2 mm por cada lado.
- **Fuera de la ficha, reportado al planear:** «Comentarios» imprimía la lista de Python tal cual (`['a', 'b']`),
  porque `summary.comments` es una lista.

## 1. Qué cambia

- **`ogr_core/report/report_generator.py`:**
  - `report_fonts()` registra una sola vez las cuatro caras de **DejaVu Sans** (normal, negrita, oblicua y negrita
    oblicua) como una familia, para que `<b>` e `<i>` encuentren la suya. Las usan los estilos, las tablas
    (`_grid_style`) y el pie.
    - Los archivos son la copia que trae matplotlib (`matplotlib.get_data_path()/fonts/ttf`), que ya era
      dependencia: **no se instala nada**.
    - **Licencia:** la de Bitstream Vera, y los cambios de DejaVu son de dominio público
      (`mpl-data/fonts/ttf/LICENSE_DEJAVU`). Permite usarla e incrustarla; el programa no redistribuye los
      archivos, solo el subconjunto que reportlab incrusta en cada PDF.
    - Si los archivos no se pudieran leer, el informe sigue con Helvetica, como antes.
  - `local_timestamp(text)` convierte el sello a hora local con el formato del informe, `dd/mm/YYYY, HH:MM:SS`.
    - Un sello sin zona se lee como UTC, que es como se ha escrito siempre; uno con zona se lee con ella.
    - Un texto libre, o una fecha sin hora (las dos se pueden escribir por el API), se enseña como está.
  - «File» es `str(project.file_path)`, escapado, o `T("not saved")`.
  - Los títulos de sección y de método llevan `keepWithNext`, y la raya también. El documento mete título, raya y lo
    que sigue en un mismo `KeepTogether` (`handle_keepWithNext` de platypus).
  - La raya es un `HRFlowable` del ancho útil del marco. `project_width()` devuelve ese ancho (A4 menos los márgenes
    y menos el relleno del marco), y lo usan la raya, todas las tablas de ancho completo y las figuras. La tabla de
    válidas/inválidas reparte sus columnas en ese ancho, en la misma proporción.
  - Los comentarios van uno por línea, escapados.
- **`ogr_core/project/project.py`:** el sello de creación sin `utcnow`, con el mismo texto.
- **`ogr_gui/i18n/__init__.py`:** «not saved» → «sin guardar».
- **`tests/_leaks.py`:** `report_generator._FONTS` entra en `ALLOWED` con la regla `FILLED_ONCE`, como
  `core_messages._CATALOGUE`. Es una caché del programa: los cuatro nombres de fuente, que se llenan una vez con el
  primer informe y solo dependen de las fuentes instaladas de matplotlib.
- **`tests/test_report_pdf_v1417.py`,** nuevo, con 14 tests.
- **Cambiados a propósito:**
  - `test_report_figures_v1339::test_each_figure_has_its_caption` buscaba el guion largo como el octal 227 de WinAnsi
    en el flujo de contenido. En la fuente incrustada el guion es un glifo del subconjunto, así que ahora lee el texto
    con pdfium (QtPdf). El ayudante `_page_text`, que no tenía otro uso, se retira.
  - `test_report_spanish_v1355::test_text_for_text` cambia en dos entradas, que se escriben en el propio test:
    - entra `('p', 'not saved')` tras «File». Antes el valor era el nombre del proyecto, «Report», igual que el
      título, y por eso no salía como entrada nueva;
    - el primer `<date>` sube a la fila de la fecha de creación. Antes, el sello ISO no tenía letras y el test lo
      descartaba.
    - La paginación de las celdas no cambia.
- El número en los nueve sitios y el contador de los dos README.

## 2. Qué se probó

- **`tests/test_report_pdf_v1417.py`**, que lee el PDF con pdfium (QtPdf) y con los bytes:
  - todo texto que se muestra va en un subconjunto TrueType incrustado (`ABCDEF+DejaVuSans…`, con su `/FontFile2`).
    Se mira la fuente activa en cada `Tj`/`TJ`, porque el preámbulo de cada página elige `/F1` (Helvetica) sin
    escribir nada;
  - «[kN/m³]» y «m²» salen enteros del texto;
  - un sello ISO sin zona sale en hora local y con el formato; uno con zona se lee con ella; un texto libre, una fecha
    sin hora y el vacío salen como están; un proyecto nuevo guarda el sello con la misma forma; un `.ogr` conserva el
    suyo al leerlo y escribirlo;
  - «File not saved», «Archivo sin guardar» en castellano, y la ruta de un proyecto guardado;
  - ningún título es lo último de su página, barriendo de 0 a 39 líneas de comentario de 3 en 3, con un gancho en
    `afterFlowable` que apunta la página de cada elemento;
  - toda tabla y toda raya caben en el marco, y la raya de válidas/inválidas mide lo mismo que su tabla;
  - los comentarios, uno por línea.
- **La discriminación,** con el árbol de 0.1.416 y el test copiado dentro: **fallan 11 de 14**.
  - Pasan los dos de compatibilidad, que deben pasar en los dos árboles: el sello de un proyecto nuevo y el `.ogr` que
    conserva el suyo.
  - Pasa también «[kN/m³] sale entero», porque pdfium conoce la codificación de Helvetica. Queda como guarda. El que
    separa los dos árboles es el de la fuente incrustada.
- **Los vecinos:** el informe, el castellano, las traducciones, las capas del núcleo, los cachés compartidos de los
  tests, el detector de fugas, el informe de los coeficientes y de las cargas, el sueco modificado, la validación del
  ej. 1, los ajustes del proyecto y restaurar valores por defecto: 367 de 367.
- **La suite entera con `--jobs 4`:** **7064 de 7064, `Failed: 0`**, sin `Leaks` ni `Chunks died`, en unos 34 min.
  La serie no toca: 18 commits desde la última.
- **El banco:**
  - `d351()`, nueva en el `verificar_cierres.py` de la raíz, mide sobre el talud de ejemplo sin guardar, leído con
    pdfium. Comprueba la fecha local, «File not saved», las fuentes con que se muestra el texto y ningún título
    solo al pie en 14 posiciones del barrido.
    - Con 0.1.416 da SIGUE ABIERTO en los cuatro puntos: la fecha en ISO, «Archivo» con el nombre, Helvetica,
      Helvetica-Bold, Helvetica-BoldOblique y Symbol sin incrustar, y títulos solos en 5 de 14 posiciones.
    - Con 0.1.417 da CUBIERTO POR TEST.
  - El `verificar_cierres.py` de la raíz entero da 127 comprobaciones con 0 bajadas.
  - El del 02 en seco da 242 de 242 veredictos iguales a los archivados, comparados por la PRIMERA línea de cada
    ficha.
  - D351 se cierra:
    - instantánea y retirada;
    - `PAQUETES` podado y la cadena tachada;
    - prompts regenerados: 39, con las 17 FALTA anteriores y ninguna de la tanda;
    - auditorías con 0 ERROR en la raíz y en el 02;
    - instantánea `--forzar`.

## 3. Qué falta

- **A mano:** el PDF en dos visores, uno de ellos pdfium o QtPdf, con ² y ³ a la vista. Va en el prompt de la prueba
  a mano del final de la tanda.
