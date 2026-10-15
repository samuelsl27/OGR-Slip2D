# OGR Slip2D v0.1.318

**Las ventanas de interpretación hablan castellano, y un test vigila todo el
texto visible de `ogr_gui` (D300, familia a).** Segunda versión de la tanda P8h.

## 0. Lo que se encontró

- **El tamaño del problema.** D291 y D291b tradujeron la ventana principal y
  lo fijan dos tests de AST que solo miran `main_window.py`. Fuera de ella, el
  censo de la ficha contó 116 textos en 26 archivos el 2026-10-09.
  - Uniendo sus tres detecciones (constructores y setters, mensajes y
    f-strings con letras), en 0.1.316 había unos 200 sitios en 32 archivos.
  - Con las reglas finales de esta versión, que miran también títulos de
    menús, barras de herramientas, docks y los `QInputDialog`, había **193 en
    0.1.317**.
- **Lo que NO es texto de interfaz** salía en la detección de f-strings de
  D291b, y el test lo excluye con su razón:
  - el CSS de `setStyleSheet` (23 sitios);
  - los mensajes de excepción;
  - el dato de un elemento de combo;
  - el `name=` que guarda el `.ogr`;
  - el nombre de un paso de deshacer, que el agente lee en inglés.
- **Notación que es la misma en castellano** («FS = …», «H: … …», «u: … …»,
  «t = …»): si se envolviera en `tr()` haría falta una traducción idéntica,
  que `test_i18n_coverage_v141` cuenta como olvido. Va a `EXCEPTIONS`, con su
  razón.
- **`plantillas.py` (D291) solo convierte mensajes.**
  - El convertidor de esta tanda, en el scratchpad, reescribe cualquier sitio
    que marque el test: un literal pasa a `tr("…")`, una f-string a
    `tr("plantilla").format(…)` con el formato de cada campo, y un `%` a
    `tr("…") % …`. El inglés queda idéntico.
  - Al escribirlo apareció una trampa: el AST cuenta las columnas en bytes
    UTF-8, así que una raya «—» descuadra los cortes si se hacen sobre la
    cadena. Se cortan los bytes.
- **Los dos títulos «Error»** de *Interpret* se envuelven en `tr()`: el
  diccionario ya tenía `'Error': 'Error'` como traducción admitida.

## 1. Qué cambia

- **97 textos pasan por `tr()`** en *Interpret*, *Interpret Groundwater*, la
  ventana de estadística, los gráficos y los diálogos de variables
  aleatorias y de la rejilla de presiones de agua:
  - el título, los menús «Agua subterránea» y «Estadística» y sus entradas;
  - las barras de herramientas;
  - el resumen del método;
  - las cabeceras de la tabla de resultados;
  - los mensajes de matplotlib ausente;
  - el resumen probabilista;
  - el caudal de la sección de descarga;
  - los diez mensajes que eran los últimos fuera de `tr()`.
- **82 claves nuevas con su castellano.** El factor de seguridad va como
  «FS», el término castellano, y se usan «dovela», «cara de rezume» y
  «diagrama de sólido libre».
  - Ninguna clave duplicada nueva. Los 20 duplicados viejos son de D240
    (0.1.321).
- **`tests/test_gui_spanish_v1318.py`** (nuevo) recorre todo `ogr_gui` con la
  unión de las tres reglas.
  - `EXCEPTIONS` lleva la razón de cada texto que no se traduce.
  - `BUDGET` solo baja: 193 en 0.1.317 y **94** ahora.
  - Las familias siguientes lo bajan hasta 0.
- **`test_i18n_coverage_v141`:** el presupuesto exacto de mensajes baja de 10
  a 0.

## 2. Tests

`tests/test_gui_spanish_v1318.py`, 5 casos:

- **el recuento** de todo `ogr_gui` está dentro del presupuesto, y lo iguala;
- **ninguna excepción es fantasma:** cada una sigue en el código, con su
  razón;
- ***Interpret* en castellano,** con la ventana real: «OGR Slip2D —
  Interpretar — …», los menús «Agua subterránea» y «Estadística» y la barra
  «Método»;
- **control:** en inglés, el título y los menús son los de antes.

**Con el código de 0.1.317 fallan 3 de los 5:** el recuento es 193 y la
ventana no sale en castellano. El control en inglés y el de las excepciones
pasan en los dos árboles. Se corrió sobre una copia del árbol de 0.1.317 sin el
buscador editable.

## 3. Verificación

- **Los tests vecinos**, antes de la suite: 363/363. Son *Interpret*,
  estadística, gráficos, variables aleatorias, rejilla de presiones, los dos
  tests de AST de la ventana, idioma, traducciones de Qt, el gráfico FS-tiempo
  e i18n.
- **Suite entera:** 6116/6116, `EXIT=0`, 58 min.
- **Banco:** `verificar_cierres.py` entero, 59 comprobaciones y 0 bajadas.
  D300 sigue abierta hasta 0.1.321.
- **Ningún número cambia:** son textos, y el inglés es idéntico.

## 4. Pendiente

- **Las familias (b), (c) y (d)** (0.1.319 y 0.1.320), y las etiquetas y D240
  (0.1.321).
- **A mano:** *Interpret* e *Interpret Groundwater* con Español guardado.
