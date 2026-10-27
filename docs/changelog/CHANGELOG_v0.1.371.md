# OGR Slip2D v0.1.371

**La tabla de puntos de *Definir materiales* enseña tres filas y sus cabeceras enteras en los cuatro tipos
(puntos, tres columnas, c/φ y reglas). Para hacer sitio, la columna derecha del diálogo pasa a desplazarse
en vertical en vez de crecer la ventana. Es una decisión de la propietaria (D352, cerrada).** Novena y
última versión de la tanda P8l.

## 0. Lo que se encontró

- **Medido antes de escribir, en la pantalla de la ficha.** Es 1920 × 1080 al 125 %: 1536 × 816 lógicos
  libres. Se midió con la plataforma de Windows y el diálogo dispuesto sin llegar a pintarse
  (`WA_DontShowOnScreen`):

  | Modelo | Filas visibles | Alto del diálogo |
  |---|---|---|
  | Mohr-Coulomb, al abrir | — | 741 × 626 |
  | Función tangencial/normal | 1,2 | 676 |
  | Anisótropo y c/φ (tres columnas) | 1,0 | 676 |
  | Reglas del anisótropo generalizado | 0,5 | 738 |

  Las cabeceras tenían el ancho por defecto de Qt, 100 px. Hacían falta 141–165 px en Windows, y 172–330
  en offscreen.
- **Pedir altura no bastaba, y esto el plan no lo vio.** La primera versión del arreglo daba a la tabla un
  mínimo de tres filas. Medida, hacía crecer el diálogo hasta 756 px y, con las reglas, hasta 818, que no
  caben en 816. La columna derecha apila *General*, *Tipo de resistencia* y *Parámetros de agua* sin
  desplazamiento, así que la tabla solo podía crecer si crecía la ventana. Se paró y la propietaria
  eligió la columna con desplazamiento vertical, entre tres opciones: esa, dejar que creciera y dos filas
  en vez de tres.
- **La premisa de mi primer test era falsa.** El primer test exigía que el diálogo siguiera abriéndose a
  720 × 500. Hoy ya no se abre así: el contenido manda (741 × 626 en Windows, 1212 × 582 en offscreen), y
  `resize(720, 500)` solo era un suelo. Lo que el test protege ahora es que abre al tamaño que pide su
  contenido, y que no crece al elegir un modelo con tabla.
- **Estirar la última columna corta su cabecera sin barra.** Con `setStretchLastSection(True)` hay una
  franja de anchos en la que la última sección recibe lo que sobra, menos que su cabecera, y no aparece la
  barra horizontal: medido, 266 px para una cabecera de 316. Por eso las columnas van al ancho de su
  contenido y la última no se estira. El primer intento daba a todas el mínimo de la más ancha, y forzaba
  la barra en tablas que cabían.
- **Abrir al tamaño del contenido costó dos intentos.** Un área con desplazamiento pide casi nada de alto,
  así que se le pide la altura de lo que contiene, se mide y se suelta. Antes de mostrarse, el editor
  pedía 504 px de los 570 que ocupa:
  - pulirlo antes (`ensurePolished`) no cambió nada;
  - lo que faltaba era el panel de parámetros que acababa de rellenar el primer material. En una ventana
    que nunca se ha mostrado, el nuevo tamaño de un hijo solo llega al layout del padre cuando corre el
    bucle de eventos. Se activan los layouts de dentro hacia fuera antes de medir.
- **La altura mínima de la tabla no hace nada en *Definir materiales*, y sí en otro diálogo.** Dentro de la
  columna, el editor se dimensiona por altura según el ancho, porque la fórmula parte líneas, y la tabla
  recibe su altura preferida: sin mínimo enseña las mismas filas. La regla 7 pide que se vea que algo
  cambia. Se vio en *Función de resistencia* (las funciones de Snowden), que usa el mismo panel sin
  desplazamiento: encogido al mínimo, enseña 3 filas con el mínimo y un tercio de fila sin él.
- **Con la etiqueta encima, la función de Snowden se abría más estrecha.** Pasaba de 413 a 296 px, con
  barra horizontal. La tabla pide ahora el ancho de sus columnas (`AdjustToContents`), y se abre a 376
  y 486 px en Windows sin barra.
- **Una equivocación mía con el banco, sin efecto.** Lancé `verificar_cierres.py --help`. No tiene ayuda,
  así que empezó una corrida entera; se paró a los dos minutos, y el JSON siguió siendo el de las 11:52.

## 1. Qué cambia

Solo `ogr_gui/dialogs/material_properties_dialog.py`:

- **`_StrengthParamPanel._fit_table`:**
  - columnas al ancho de su contenido, cabecera incluida, sin estirar la última;
  - altura mínima de cabecera más tres filas, el marco y la barra horizontal;
  - la tabla pide el ancho de sus columnas.
- **El rótulo de la tabla** va encima y la tabla ocupa todo el ancho del formulario. Al lado, la columna
  de etiquetas se quedaba unos 200 px.
- **`MaterialPropertiesDialog`:** la columna derecha va en un `VerticalScrollArea`, el de
  `ogr_gui/dialog_size.py` que ya usan el diálogo hidráulico y *Configuración del proyecto*. Aceptar y
  Cancelar quedan fijos debajo. `_open_at_content_size` abre al tamaño que pide el contenido, nunca por
  debajo de 720 × 500 ni por encima de la pantalla.
- **Lo que se mueve, dicho:** el diálogo es 12 px más ancho (753 frente a 741 en Windows), que es lo que
  reserva la barra vertical para no tapar nada cuando aparece. El alto de apertura no cambia (626).

## 2. Tests

- **`tests/test_points_table_v1371.py`** (nuevo, 5 casos), con los diálogos mostrados, en castellano con
  el catálogo de Qt:
  - en *Definir materiales*, los cuatro tipos al abrir y al mínimo: tres filas, cabeceras enteras y la
    columna sin barra horizontal; también con la fuente un punto mayor;
  - abre al tamaño de su contenido: sin barra vertical con Mohr-Coulomb, y sin crecer al elegir un modelo
    con tabla;
  - *Función de resistencia*, al mínimo, con y sin la fuente mayor.

  **Con el código de 0.1.370 fallan los 5**, y por lo que enseñaba, no por un atributo:
  - 0,4–0,8 filas;
  - cabeceras de 100 px donde hacen falta 172–316;
  - el diálogo crecía de 582 a 628 px, y a 681 con las reglas.

## 3. Verificación

- **El test de esta versión:** 5/5 (0/5 en 0.1.370).
- **Los vecinos:** 528/528 en 29 archivos, entre ellos:
  - todo test que abre *Definir materiales* o *Función de resistencia*;
  - los censos de tamaño de D293/D321 y el de la fuente mayor de Linux;
  - los de traducciones y menús.

  Ninguno necesitó un cambio deliberado.
- **Suite entera:** 6622 de 6623, 151 min, con el mismo fallo de tiempo que en 0.1.370.
  `test_optimizations_v111.py::test_grid_completes_quickly` tardó 5,3 s con un límite de 5 s. Solo, el
  archivo pasa: 9/9. Esta versión no toca la búsqueda.
- **Un hallazgo sin arreglar: la suite es cada vez más lenta.** Los changelogs dan:

  | Versiones | Suite entera |
  |---|---|
  | 0.1.320–0.1.323 | 54–62 min |
  | 0.1.334–0.1.357 | 72–98 min |
  | 0.1.363–0.1.369 | 91–130 min |
  | 0.1.370 | unas 3 h 50 min |
  | 0.1.371 | 151 min |

  Al final de esta corrida el proceso del runner ocupaba 7,8 GB, en una máquina de 16 GB con 1,3 GB
  libres. **Eso no lo explica por sí solo.** Lo primero que pensé fue la memoria, y está medido que no es
  nueva: en 0.1.301 la suite ya acababa en 7,7 GB (CHANGELOG_v0.1.301 y 0.1.302), y entonces tardaba
  50–72 min. La causa no se ha medido. Queda para una ficha propia.
- **Una trampa al vigilar la suite:** el log va con búfer y llegó a quedarse 50 minutos sin escribir.
  Parecía colgada en `test_minor_menus_m5_v156.py`, y estaba 80 archivos más adelante. Lo enseñó
  `sys.remote_exec` de Python 3.14, con un script que vuelca la pila de cada hilo sin parar el proceso.
- **Banco:**
  - `verificar_cierres.py` de la raíz, entero: 106 comprobaciones, 0 bajadas. `d352()` da **CUBIERTO
    POR TEST**: 3,5 filas en los cuatro tipos al abrir y al mínimo, y 3,0 en la función de Snowden al
    mínimo. Lo demás, igual que en 0.1.370;
  - el del 02 en seco: 242 veredictos, los mismos. Solo crecen dos recuentos: un archivo de test más
    (605) y una cita más en el índice (292), la de D344;
  - D352 retirada: podada de `PAQUETES` y tachada en la cadena de P8; quedan 34 prompts;
  - `auditoria_invariantes.py`: 0 ERROR en la raíz (71 AVISO) y en el 02 (754 hallazgos, los de
    0.1.370);
  - instantáneas `Evaluaciones/0.1.371` (983 archivos en la raíz y 3284 en el 02, byte a byte).

## 4. Pendiente

- **A mano:** la tabla de puntos en tu pantalla al 125 %, en los cuatro tipos, y el desplazamiento de la
  columna al encoger la ventana.
- Con esta versión termina la tanda P8l.
