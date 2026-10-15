# OGR Slip2D v0.1.316

**El tema oscuro se lee, y el claro no cambia (D301).** Cuarta y última
versión de la tanda P8g.

## 0. Lo que se encontró

- **La causa.** `apply_theme` solo ponía una hoja de estilo, nunca una
  `QPalette`. La hoja oscura no nombra `QLabel`, `QCheckBox`, `QRadioButton`,
  los paneles sueltos ni el lienzo, así que esos se quedaban con la paleta
  clara: texto oscuro sobre la ventana oscura.
- **Los iconos.** qtawesome colorea un icono sin color propio con el texto de
  la paleta en el momento de crearlo. Con la paleta clara salía negro sobre el
  menú oscuro, y además se quedaba en tres cachés (la de `icon()`, la de
  qtawesome y el icono de cada acción).
- **Unos 30 colores escritos a mano** en 14 archivos: la barra de estado, la
  terminal, la leyenda, las notas en gris de varios diálogos, los avisos en
  rojo… Más el fondo, la rejilla y la regla del lienzo.
- **Medido sin pantalla, antes de tocar nada.** Contraste (WCAG) entre el
  fondo de cada texto y su tinta, en la ventana principal, *Preferences*, el
  diálogo hidráulico y un `QMessageBox`:

  | | Claro | Oscuro |
  |---|---|---|
  | 0.1.315 | mínimo 4,08 | mínimo **1,28** (las coordenadas); 1,48 en «No results yet.», el mensaje, el diálogo hidráulico y todas las casillas de *Preferences* |
  | 0.1.316 | mínimo 4,08, el mismo widget a widget | mínimo **4,04** |

- **Un primer método de medida engañaba.** Capturaba cada etiqueta por
  separado (`grab()`), y Qt la pinta sobre el fondo de su propia paleta, no
  sobre el que la ventana pone debajo. Así el oscuro de 0.1.315 salía igual que
  el claro. Ahora se recorta cada texto de una captura de la ventana entera.

## 1. Qué cambia

- **`apply_theme` pone también una paleta.**
  - La oscura sale de los colores que la hoja oscura ya usaba.
  - La clara es la paleta que tenía la aplicación antes de cualquier tema, así
    que el tema claro no cambia.
- **`theme_color(papel)` y `current_theme()`** en `ogr_gui/themes`. En el tema
  claro, cada papel vale exactamente el literal que había, y el tema activo se
  lee de la hoja de la aplicación, no de una variable.
- **Los ~30 colores escritos a mano** piden ahora su papel: «apagado», «error»,
  «aviso», «tinta», «fondo de nota», los de la barra de estado y los del
  lienzo.
  - Los que pintan su propio fondo (los conmutadores encendidos de la barra de
    estado, la banda de resultados de un modelo anterior) se leen igual en los
    dos temas y no cambian.
- **Iconos.**
  - `apply_theme` vacía las dos cachés (`icons.reset_cache()`), y la ventana
    vuelve a poner el icono de cada acción.
  - En el tema oscuro, un icono con color fijo demasiado oscuro conserva el
    matiz pero aclarado, y un gris oscuro toma el color del texto (el contorno
    exterior era #2c2c2c).
- **El lienzo.** El fondo, la rejilla y la regla siguen el tema. Los colores de
  lo dibujado no (decisión de la propietaria).
- **Al cambiar de tema, la ventana vuelve a pintar lo que conserva**
  (`_retheme`): iconos, barra de estado y lienzo. Un diálogo se construye cada
  vez que se abre, así que ya toma el tema.
- **La terminal** escribe con la tinta del tema que haya al escribir.
- **Tres tests antiguos que aplicaban el tema** devuelven ahora también la
  paleta (regla 5): `test_disabled_menus_v1288`, `test_language_saved_v1289` y
  `test_qt_translations_v1292`.

## 2. Tests

`tests/test_dark_theme_v1316.py`, 7 casos:

- **en los dos temas,** todo texto habilitado y con letras de la muestra se lee
  con un contraste de al menos 4,0, que era el mínimo del tema claro (más de
  20 textos medidos);
- **el tema claro no cambió:**
  - su paleta es la de antes de cualquier tema;
  - el color de cada papel es el literal viejo;
  - el tema activo se lee de la hoja, así que un test que devuelve la hoja no
    deja colores del oscuro;
- **un icono sin color propio** se lee sobre el menú oscuro, y el gris del
  contorno exterior se aclara;
- **la ventana vuelve a construir sus iconos** al cambiar de tema;
- **el fondo del lienzo** sigue al tema, y los colores de los contornos no.

Todos restauran la hoja, la paleta, el idioma y las cachés de iconos.

**Con el código de 0.1.315 fallan los 7.** En el tema oscuro el contraste baja
a 1,28; el icono de *File* sale negro (0, 0, 0); el lienzo no cambia de fondo;
y lo nuevo no existe. Se corrió sobre una copia del árbol de 0.1.315 sin el
buscador editable.

## 3. Verificación

- **Suite entera:** 6107/6107, código de salida 0, a la primera (59 min).
- **Banco:** `d301()` en el `verificar_cierres.py` de la raíz: **CUBIERTO POR
  TEST**. Ciclo de cierre:
  - `verificar_cierres.py` entero: 58 comprobaciones, 0 bajadas;
  - instantánea `Evaluaciones/0.1.316` antes y después (`--forzar`);
  - `retirar_cerrados.py --escribir D301`;
  - poda de la lista P8 y D301 tachada en la fila P8;
  - `generar_prompts.py`: 35 prompts y las mismas 19 FALTA;
  - `auditoria_invariantes.py` en la raíz y en el 02, con 0 ERROR.
- **Tanda P8g terminada:** D313 (0.1.313), D305 (0.1.314), D293 (0.1.315) y
  D301 (0.1.316). En P8 quedan D299 y D300 (P8h).
- **Los tests vecinos**, antes de la suite: 393/393 (temas, menús, idioma,
  traducciones de Qt, barra de estado, *Interpret*, lienzo, estadística,
  terminal, leyenda, tamaños, grieta, soportes y materiales) y 172/172
  (materiales y soportes).
- **Ningún número cambia:** es presentación.

## 4. Pendiente

- **A mano, con el tema oscuro:** la ventana, *Preferences*, el diálogo
  hidráulico, los iconos y el lienzo. Los anchos y colores se midieron sin
  pantalla, con el estilo Fusion.
- **Una ventana de *Interpret* abierta mientras se cambia de tema** conserva
  sus iconos y su leyenda hasta que se vuelve a abrir.
- **La terminal** no recolorea el texto que ya había escrito.
