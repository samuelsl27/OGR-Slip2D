# OGR Slip2D v0.1.448

**El informe dice de quién es el mínimo global de cada método (D404).** La crítica de una corrida compite sobre todas
las superficies analizadas, las de la búsqueda y las que dibujó el usuario (D58: los círculos desde 0.1.157, las
polilíneas desde 0.1.427), así que una superficie dibujada a mano puede ser el mínimo global. El bloque «Global
Minimums» del PDF la escribía igual que una de la búsqueda. Ahora una fila lo dice, justo después del factor. Medido
con 0.1.447 (9c90902) en el talud de ejemplo no circular (Path Search de 5) con la polilínea de
`test_user_polylines_v1427`, el informe en inglés:

| método | crítica | 0.1.447 | ahora |
|---|---|---|---|
| Bishop | 1,1789, la del usuario (la búsqueda sola da 1,3834) | factor, eje, extremos y área | además, tras el factor, «Surface — Defined by the user» |
| Corps of Engineers #2 | 1,4150, de la búsqueda | factor, extremos y área | igual, carácter a carácter |

En castellano, «Superficie — Definida por el usuario». **Ningún número cambia:** es una fila del informe. Es la
vigesimoprimera versión de la tanda P10 y la primera del plan aprobado el 2026-11-14 (D404, D408, D423, D406 y D409).

## 0. Lo que se encontró

- **Paso 0, sobre 0.1.447:** el REPRODÚCELO del prompt da su salida carácter a carácter. Las dos críticas son
  polilíneas, la del usuario y una de 6 vértices de la búsqueda. Sus bloques no son iguales en forma desde D424, pero
  la diferencia viene del método y no del autor: Bishop guarda el eje de sus momentos y Corps of Engineers #2 no. Nada
  decía de quién era cada superficie.
- **Las palabras ya existían.** D401 (0.1.443) marcó en las ventanas la crítica del usuario con «Defined by the user»
  («Definida por el usuario», `surface_note`), y «Surface» («Superficie») también está en el diccionario. `note_text`
  traduce un texto sin código por `tr`, así que la fila no estrena ninguna cadena. Como las `T()` del núcleo no están
  en el censo de cadenas, el test comprueba las dos traducciones.
- **El «ningún test existente cambia a propósito» del prompt no se podía cumplir.** El test de D424
  (`tests/test_report_global_minimums_v1447.py`, `TestTheReferencePolyline`) corre Ej_1 con su polilínea dibujada a
  mano, que es del usuario (su premisa lo comprueba), y fija el bloque celda a celda. Con la fila, fallaban los tres
  asserts previstos al planificar (Bishop, el Ordinario, y Janbu con Spencer), y ninguno más. Por decisión de la
  propietaria, la fila va donde decía el plan, tras el factor, y los tres asserts **cambian a propósito**: ganan la
  fila (`_USERS`) y conservan todo lo demás.
- **El barrido de páginas de v1447 sigue discriminando.** Su polilínea de 51 vértices también es del usuario, y la
  fila baja una línea el bloque de Bishop. Los 14 mutantes de D424 (`mutants_d424.py`) siguen muriendo con la fila
  puesta, también los cuatro de la maquetación.
- **La pregunta.** El núcleo no importa el motor (`test_core_layering_v1340`, `_closed_v1346`). El primer borrador,
  como pedía la ficha, preguntaba al resultado su propio método, `res.is_user_surface(crit)`, por `getattr`. La
  revisión hizo ver que así había dos reglas: las ventanas, el API y el retroanálisis preguntan `is_user_surface_of`,
  que mira la lista `user_evaluations`. Con un resultado real responden igual, pero con un doble que solo tuviera la
  lista, las ventanas decían «Defined by the user» y el informe no, y el test fijaba esa diferencia. **Por decisión de
  la propietaria, la regla baja al núcleo** (`ogr_core/project/user_surfaces.py`), `ogr_slip2d.search` la reexporta con
  su nombre, y el informe pregunta esa misma.
- **La revisión adversaria (un agente) no encontró defectos del código.** Recorrió las puertas que llegan al informe:
  - Compute de la ventana y el puente del agente;
  - `report_generate` del API, ejecutado de verdad: la identidad sobrevive al pickle del subproceso, porque
    `critical` se recalcula sobre las listas;
  - Optimizar superficies.

  En todas, la fila sale si y solo si la crítica es del usuario. Encontró las dos reglas de arriba y cuatro frases
  falsas o sin prueba en este cambio, todo arreglado:
  - la cabecera del test decía que nada distinguía los dos bloques salvo sus números (Bishop lleva además su eje);
  - este changelog daba a entender que solo la del usuario es una polilínea;
  - la cabecera anunciaba que «Valid / Invalid Surfaces» sigue contando la búsqueda y ningún caso lo comprobaba
    (ahora lo comprueba uno, con su mutante);
  - se citaba `TestWhoPassesIt` como prueba de que la llamada no cambia.

  Se reporta y no se toca: «Surface» es la misma clave que usa el desplegable de anisotropía generalizada
  (`material_properties_dialog.py:246`). Si se retradujera para ese diálogo, cambiaría también esta fila, y el test lo
  vería.

## 1. Qué cambia

- **El bloque** (`ogr_core/report/report_generator.py`): tras la fila del factor, «Surface | Defined by the user»
  cuando la crítica del método es una de las superficies del usuario. Va delante del centro, el eje, los extremos y el
  área.
- **La regla** `is_user_surface_of` (por identidad, sobre la lista `user_evaluations`) pasa de `ogr_slip2d/search.py` a
  `ogr_core/project/user_surfaces.py`, nuevo. El motor la reexporta con el mismo nombre, y ningún otro llamador cambia
  su import.

No cambian:
- «Valid / Invalid Surfaces», que sigue contando la búsqueda (D58);
- un informe sin superficies del usuario (`_V1354` de `test_report_spanish_v1355`);
- la llamada de la ventana: no tiene ningún argumento nuevo. En `ogr_gui/main_window.py` solo cambia `VERSION`. No se
  cita `TestWhoPassesIt` como prueba, porque busca subcadenas y no vería un argumento metido entre dos de ellas;
- el informe del API, en inglés y sin `translate`.

## 2. Qué se probó

- **`tests/test_report_user_surface_v1448.py`** (12 casos, unos 3 s). Referencia por identidad: la fila sale si y
  solo si `res.is_user_surface(res.critical)`.
  - El caso de la ficha, compartido en el módulo: la fila bajo Bishop (1,1789) justo tras su factor, y no bajo Corps of
    Engineers #2 (1,4150), en inglés y en castellano.
  - Un círculo del usuario: el de `test_user_surfaces_v1157` sobre su rejilla gruesa, con Bishop.
  - Una regla para el informe y las ventanas:
    - un doble con la lista del usuario lleva la fila, y `surface_note` dice lo mismo;
    - uno sin la lista no la lleva y no falla;
    - el motor reparte la regla del núcleo.
  - Las dos palabras con su castellano.
  - «Valid / Invalid Surfaces» con los recuentos de la búsqueda, sin la superficie del usuario.
- **Discriminación:** en el árbol de 0.1.447, sin el buscador editable, fallan seis:
  - cinco por lo que miden: Bishop, el círculo, el castellano, la identidad y el doble con la lista;
  - uno porque el módulo del núcleo no existe.

  Pasan Corps of Engineers #2, el doble sin la lista, las premisas, las palabras y los recuentos.
- **Mutantes** (`mutants_d404.py`, en el banco): 10, todos muertos:
  - la fila nunca o siempre;
  - el primer borrador (preguntar al resultado su método);
  - la lista leída sin `getattr`;
  - una copia de la regla en el motor;
  - cada palabra sin traducir, y otra palabra;
  - la fila tras el área;
  - la superficie del usuario sumada a «Valid».
- **Vecinos**, con los patrones `report user_polylines user_surfaces spanish_paths version_consistency core_layering`
  y los de los consumidores de la regla, `windows_user_surfaces results_query_user_surfaces
  back_analysis_user_surfaces user_circles_parity` (cada uno comprobado con `--list`): 330 casos en verde en 18
  archivos.
- **La suite entera** con `--jobs 4`: **7612 casos, 7611 en verde, 0 fallos y 1 omitido**, sin fugas ni tramos
  muertos. La serie no toca (26 commits desde la última).

## 3. Qué queda

- La siguiente es D408 (0.1.449): el informe de una corrida Ky o Newmark no da el Ky ni el desplazamiento. Conserva esta
  fila.
- **Reportado y sin tocar:** el pie de la figura y el encabezado de «Slice Data» de una crítica del usuario siguen sin
  decir de quién es. La ficha pedía «Global Minimums», que es donde el bloque identifica la superficie.
