# OGR Slip2D v0.1.418

**Nueve detalles de la quinta y la sexta prueba de la interfaz (D355).**

Dos notas acaban como frases. «corrida» pasa a «cálculo». Ajustes → Avanzado ya no enseña un código interno y
escribe los decimales con punto. Las dos entradas de Propiedades dicen cuál es cuál. Las dos ayudas de una región
empiezan igual. *Estirar soporte* tiene su icono. Preferencias se cierra antes de avisar. Los diálogos de archivo
empiezan en una carpeta con sentido. Y la barra de estado acorta también lo que pone Qt.

Es la segunda de la tanda P8o. La ficha sale de H9 y H14 de `INFORME_prueba_GUI_0.1.355.md` y, para Preferencias,
de H13 de `…0.1.357.md`. **Decisiones de la propietaria (2026-11-03):**
- el término es «cálculo»;
- en Propiedades se quedan las dos entradas, con nombres distintos.

Ningún número cambia. El inglés de las notas solo gana su punto final.

## 0. Lo que se encontró, punto por punto

1. **Las notas.**
   - La plantilla de la norma de diseño (`_factor_report_notes`) no llevaba punto final en ninguno de los dos
     idiomas. Tampoco sus dos gemelas: la de la línea de órdenes y la de la estadística («…not the factor of
     safety»).
   - «antes de darlo», en vez de «antes de darlo por bueno» («before quoting it»), no estaba en una nota sino en
     **cinco**: GRID_EDGE, DAYLIGHT_STEEP y los tres consejos de m-alfa (fuerzas, momentos y desconocido). Era la
     traducción la que se quedaba corta: el inglés, que congelan los tests de D335, estaba entero.
2. **«corrida»** salía en 10 frases. Todas traducían «run» y convivían con «cálculo» (25) y «análisis» (107).
3. **Avanzado.**
   - «…y las informa como error -112» decía qué hace la referencia con las superficies que rechaza, pero dejaba al
     lector un código que no es del programa.
   - «78,5°» (cinco frases) y «0,2» (una) llevaban coma, y el programa escribe los números con punto, también en esa
     pestaña («Comprobar m-alfa < 0.2»).
4. **Propiedades.**
   - «Asignar material» solo pone el lienzo en modo de asignar con clic.
   - «Asignar materiales» abre además el panel donde se elige el material. Sin ese panel, el modo dice «Elige primero
     un material en el panel».
   - Las dos llevaban el mismo pincel, y el mensaje del modo para un contorno que no es de material citaba la otra
     por su nombre.
5. **Las ayudas de una región.**
   - En los modos de dibujo, la ayuda del propio elemento del lienzo decía «Región / Material: Silty clay / Área:
     …».
   - En Seleccionar, la ayuda de datos dice «Silty clay  (región 1) / resistencia / …».
   - Las dos recorren `resolve_regions()` en el mismo orden, así que el número de región es el mismo.
6. ***Estirar soporte*** usaba la goma de *Eliminar soporte*.
7. **Preferencias.**
   - `_accept` emitía `language_changed` antes de `accept()`, así que el aviso «Idioma cambiado…» se abría con el
     diálogo aún en pantalla.
   - Para entonces Qt ya había cambiado su catálogo (D327): los botones decían «Save» y «Cancel», y el título y las
     etiquetas seguían en castellano.
   - El aviso es hijo de la ventana principal, y en Windows podía quedar detrás del diálogo.
   - Con el diálogo cerrado antes, la siguiente vez se abre entero en el idioma nuevo: `tr()` lee el idioma activo.
8. **Los diálogos de archivo.**
   - Los siete de la ventana principal y los seis de Interpretar recibían `""`, así que empezaban en la carpeta de
     trabajo del programa.
   - *Generar informe* proponía un nombre suelto, que se resolvía también contra esa carpeta.
   - Nada recordaba la última carpeta.
9. **La barra de estado, medida antes de tocarla.** Con el ejemplo, la ventana a 1366 px:
   - la barra deja al mensaje 447 px;
   - el motivo más largo de una acción desactivada mide 1262 px (151 caracteres);
   - puesto por la ventana, sale en 445 px con «…» y el texto entero de ayuda, que es D325;
   - puesto por Qt, como al pasar el puntero por un menú (`QStatusTipEvent`, desde C++, sin pasar por el
     `showMessage` de Python), **salía entero, sin «…» y sin ayuda**, y los indicadores tapaban su final.
   - Eso es lo que vio la prueba. El docstring de `ElidingStatusBar` ya lo decía («A message Qt shows by itself
     […] is not cut»).

## 1. Qué cambia

- **Las frases** (`ogr_gui/main_window.py`, `ogr_cli/__main__.py`, `ogr_gui/reported_quantity.py`,
  `ogr_gui/i18n/__init__.py`):
  - el punto final en las tres, y en sus claves;
  - «antes de darlo por bueno» en las cinco notas;
  - las diez frases de «corrida» dicen «cálculo», con su concordancia: «este cálculo», «entre cálculos», «cálculos
    sucesivos», «lo que el cálculo decidió».
- **Avanzado** (`ogr_gui/dialogs/project_settings_dialog.py` y su castellano):
  - la nota dice «Las superficies que rechaza se marcan como no admisibles» («are marked inadmissible»), sin el
    código;
  - las comas decimales de la pestaña pasan a punto.
  - **Cambio deliberado del inglés** de esa nota, que no es una nota de D335.
- **Propiedades:**
  - «Asignar material con clic» (*Assign Material by Clicking*), con su icono, el bote de pintura
    (`fa6s.fill-drip`);
  - «Panel de asignar materiales...» (*Assign Materials Panel...*), con el pincel;
  - el mensaje del modo cita la otra por su nombre nuevo;
  - el submenú «Asignar material» del botón derecho y el título del diálogo de un contorno de material no cambian.
- **Las ayudas de región:** `data_tips.region_heading(material, número)` da la cabecera de la ayuda de datos,
  «Silty clay  (región 1)», o la región y que no tiene material. La ayuda del lienzo empieza por ella y añade
  «área: … m²». La clave vieja «<b>Region</b>…» se retira, y también «(unassigned)», que se quedaba sin uso.
- ***Estirar soporte:*** su clave `stretch_support` en el catálogo de iconos (`fa6s.arrows-left-right-to-line`, en
  el morado de los soportes).
- **Preferencias:** `_accept` cierra el diálogo primero y luego avisa a la ventana.
- **Los diálogos de archivo:** el módulo nuevo `ogr_gui/file_folders.py`, con `start_folder`, `remember_folder`,
  `get_open_file_name` y `get_save_file_name`.
  - Un diálogo empieza en la última carpeta usada en esa ventana durante la sesión. Antes de usar ninguna, en la
    carpeta del proyecto si se guardó, y si no en Documentos.
  - *Generar informe* propone su nombre dentro de esa carpeta.
  - Los usan los trece diálogos. El de los datos brutos de Interpretar conserva su padre (el cuadro abierto) con
    `parent=`.
  - La carpeta se recuerda en la ventana y no en las preferencias guardadas, a propósito: si no, cada test que eligiera
    un archivo dejaría cambiado el archivo de ajustes, y el detector de fugas lo marcaría.
- **La barra de estado** (`ogr_gui/widgets/status_bar.py`): `ElidingStatusBar` vuelve a enseñar por `_show` un
  mensaje que pone Qt (el que llega por `messageChanged` y no es el suyo). Así se acorta igual, con el texto entero
  de ayuda, en la ventana principal y en Interpretar.
- **Cambiados a propósito:**
  - `test_design_factor_report_gui_v1165.py` usa la clave inglesa entera, que ahora lleva su punto;
  - `test_voice_and_terms_v1325.py`: «corrida» entra en `RETIRED`, con «cálculo»;
  - `test_canvas_redraw_v1327.py` (dos casos) buscaba «Region» en la ayuda del lienzo; ahora busca «(region 1)», la
    cabecera común;
  - `test_report_figures_v1339.py` (dos casos) sustituía `main_window.QFileDialog`. El diálogo se busca ahora en
    `ogr_gui.file_folders`, y es ahí donde se sustituye.
  - Los dos salieron en la primera suite entera, 7075 de 7079. Mi censo previo de cómo sustituyen los tests el
    diálogo buscaba la clase (`QFileDialog.getOpenFileName =`) y el alias `MW.`, y este test usa `mw.`.
  - Por eso el nombre `QFileDialog` desaparece de `main_window` e `interpret_window`: si se dejara, el falso de un
    test no llegaría al diálogo de verdad y la corrida se colgaría.
- **`tests/test_texts_details_v1418.py`,** nuevo, con 15 tests.
- El número en los nueve sitios y el contador de los dos README.

## 2. Qué no se tocó, y por qué

- **Otras comas decimales del castellano,** fuera de Avanzado: el rango de colores de la estadística, la razón de
  *Surface Altering*, la CDF de texto, los coeficientes sísmicos típicos y el coeficiente c del recocido. Son cinco
  entradas. La ficha nombraba la pestaña Avanzado; quedan dichas aquí.
- **`docs/mcp/seguridad.md`** también dice «corrida», pero es documentación y no un texto del programa.

## 3. Qué se probó

- **`tests/test_texts_details_v1418.py`**, un caso por punto con comportamiento, en castellano donde importa:
  - las frases y sus traducciones;
  - el diálogo de Ajustes real (las etiquetas y las ayudas de todos sus elementos);
  - la barra de menús real;
  - las ayudas del lienzo y de datos de la región 1 del ejemplo;
  - los iconos;
  - Preferencias mostrado, con lo que ve quien escucha sus señales;
  - los diálogos de archivo, sustituidos por falsos que apuntan la carpeta que reciben. Una guarda convierte en fallo
    cualquier ventana modal.
  - la barra a 1366 px con un `QStatusTipEvent` real.
  - **Una trampa al escribirlo:** el primer borrador probaba la carpeta con *Exportar DXF*, que abre antes su diálogo
    de opciones, modal, y la corrida se colgó. Ahora usa *Importar DXF*, que pide el archivo primero, y la guarda.
- **La discriminación,** con el árbol de 0.1.417 y el test copiado: **fallan los 15**.
- **Los vecinos:** la barra de estado, Preferencias, el idioma, el catálogo, el castellano, las traducciones, la norma
  de diseño, la estadística con norma, las ayudas, los iconos, los menús, las acciones, asignar materiales,
  Interpretar, los censos de diálogos, el DXF, exportar imagen, los ajustes del proyecto, las comprobaciones, m-alfa,
  las notas de método y de modelo, la línea de órdenes, los motivos y deshacer: 919 de 919.
- **La suite entera con `--jobs 4`:**
  - la primera dio 7075 de 7079, por los cuatro casos de tests cambiados a propósito (sección 1);
  - la segunda, **7079 de 7079**, `Failed: 0`, sin `Leaks` ni `Chunks died`, en 31 min;
  - la tercera, con la guarda de Preferencias en su forma final (ver abajo), es la que publica: **7079 de 7079**,
    `Failed: 0`, sin `Leaks` ni `Chunks died`.
  - La serie no toca: 19 commits desde la última.
  - El runner avisa de que `test_discrete_function_v1246.py` tardó 95,7 s y no está en `tests/_slow.txt`. No es de
    esta tanda, y en las corridas anteriores no salió. Se deja así; la lista la reescribe quien prepare la versión.
- **El banco:**
  - `d355()`, nueva en el `verificar_cierres.py` de la raíz, mide los nueve puntos con la ventana real.
    - Con 0.1.417 da SIGUE ABIERTO, 0 de 9.
    - Con 0.1.418 da CUBIERTO POR TEST, 9 de 9: «Asignar material con clic» / «Panel de asignar materiales...», y
      Abrir empieza en Documentos.
  - **Una bajada que traía mi primer borrador:** la primera corrida entera de la raíz apartó D290b, que pasaba de
    CUBIERTO POR TEST a SIGUE ABIERTO.
    - `d290b()` (0.1.291) busca en el código la guarda literal `if lang != current_language():`. Mi `_accept`
      guardaba esa comparación en una variable antes de cerrar.
    - El comportamiento era el mismo, pero el texto no estaba. Cerrar el diálogo no cambia el idioma activo, así que
      la guarda vuelve tal cual, después de `accept()`.
    - Con eso, D290b y D355 dan CUBIERTO POR TEST y los tests de Preferencias e idioma pasan, 30 de 30.
  - El VC de la raíz entero da 128 comprobaciones, con D290b como única bajada, y D290b se resolvió como se dice
    arriba.
  - El del 02 en seco da 242 de 242 veredictos iguales a los archivados, comparados por la primera línea de cada
    ficha.
  - D355 se cierra:
    - instantánea y retirada;
    - `PAQUETES` podado y la cadena tachada;
    - 38 prompts, con las 17 FALTA anteriores;
    - auditorías con 0 ERROR en la raíz y en el 02;
    - instantánea `--forzar`.

## 4. Qué falta

- **A mano:**
  - el aviso de idioma con el diálogo real y dos pantallas;
  - los diálogos nativos de archivo de Windows, que eligen su carpeta a su manera;
  - el motivo de una acción desactivada al pasar el ratón por el menú.
  - Van en el prompt de la prueba a mano del final de la tanda.
