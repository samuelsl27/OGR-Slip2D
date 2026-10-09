# OGR Slip2D v0.1.290

**Todas las entradas de menú y todos los mensajes de la ventana principal
tienen su castellano (D291).** Con D290 (0.1.289) la elección de idioma ya se
guarda. Ahora la barra de menús sale entera en castellano, y también lo que
dice la ventana.

## 0. Lo que se encontró

- **Las 26 acciones.** 26 de las 130 acciones de `MainWindow._mk` no tenían
  entrada en castellano, entre ellas todo el flujo del agua (*Define Hydraulic
  Properties…*, *Generate FE Mesh…*, *Compute Groundwater*, *Interpret
  Groundwater*…). Varias tenían la clave sin puntos suspensivos y no la que se
  usa.
- **Los mensajes.** En `main_window.py`, 121 argumentos de mensaje (barra de
  estado, `_info` y cuadros de mensaje) eran literales o f-strings que nunca
  pasaban por `tr()`.
  - De ellos, 52 eran f-strings, que `test_i18n_coverage_v141` no veía: solo
    cuenta literales.
  - `_info` no traducía su mensaje.
- **Por qué no lo vio ningún test.** El de cobertura lee llamadas `tr("…")`
  con el texto escrito, y `_mk` recibe el texto como variable.
- **Un error del inglés de paso:** «External Boundary successfully
  <b>{mode}ed</b>» construía «shrinked».
- **Decisión de la propietaria:** este alcance (los menús y los mensajes de la
  ventana). Lo de los demás diálogos se ha medido y va a D300.

## 1. Qué cambia

- **Las 26 entradas** del diccionario, con los términos que ya usaba («Malla»,
  «Retroanálisis de la fuerza de soporte», «Agua subterránea transitoria»).
  «Terminal» pasa a «Terminal de Python».
- **Los 119 mensajes con letras de la ventana** pasan a plantillas, por
  ejemplo `tr("Groundwater solved in {0} iterations; u from {1:.1f} to
  {2:.1f}{3}").format(…)`.
  - Se convirtieron leyendo el AST, así que el texto inglés es el mismo
    carácter a carácter.
  - Llevan 104 claves nuevas con su castellano.
  - Dos plantillas sin letras («{0}: {1}») se quedan como están.
- **Dos arreglos a mano:**
  - el «on/off» del mensaje del transitorio se traduce;
  - el participio de expandir y contraer sale de un diccionario por idioma
    («expanded» / «shrunk»; «expandido» / «contraído»). En inglés, «shrinked»
    pasa a «shrunk».
- **`test_i18n_coverage_v141`:** el presupuesto de mensajes sin traducir baja
  de 62 a 16, y los 16 que quedan están en diálogos.

## 2. Tests

`tests/test_menus_spanish_v1290.py`, 3 casos:
- **la barra de menús REAL:** cada título y cada entrada tiene castellano
  distinto del inglés.
  - Se excluyen «Zoom» y «Terminal», que se escriben igual, y las entradas
    del menú *Window*, que son nombres de ventanas.
  - Es la regla 2 con el mismo método que la regla 3.
- **ningún argumento de mensaje** de `main_window.py` es un literal o una
  f-string con letras fuera de `tr()`, leído con el AST;
- **dos mensajes por el camino real,** con el castellano activo: calcular el
  agua sin malla dice «Genera primero la malla de elementos finitos.», y borrar
  una malla que no existe pone «No hay malla de elementos finitos que borrar».

## 3. Verificación

- **Suite entera:** 5906 / 5906, con código de salida del proceso 0.
- **Tests de traducción, menús y preferencias** (5 archivos, 40 casos): verdes.
- **`verificar_cierres.py` de la raíz:** `d291()` da CUBIERTO POR TEST (130
  acciones, 0 sin castellano); 34 comprobaciones, ninguna bajada.

## 4. Lo que se abrió

- **D300:** el texto visible sin `tr()` fuera de la ventana. Son 116 textos en
  26 archivos, y es un mínimo, porque solo mira los constructores y setters
  habituales. Los que más tienen:

  | Archivo | Textos |
  |---|---|
  | `interpret_window.py` | 34 |
  | `canvas_view.py` | 12 |
  | `transient_stages_dialog.py` | 12 |
  | `interpret_groundwater_window.py` | 7 |
  | `grid_dialogs.py` | 7 |

  Además:
  - las claves internas «cohesion:» y «friction_angle:» de *Definir
    materiales*;
  - las texturas de las bibliotecas de «Elegir…».

## 5. Lo que no se ha probado

- **A mano:** con Español guardado, abrir el programa y recorrer los menús y el
  flujo del agua.
