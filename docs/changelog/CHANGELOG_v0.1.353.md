# OGR Slip2D v0.1.353

**Lo que dicen los análisis estadísticos, la norma de cálculo y el factorizado de cada modelo de resistencia
lleva un código estable, y la ventana lo dice en castellano (D335, séptima parte).** Decimocuarta versión de
la tanda P8k.

## 0. Lo que se encontró

- **El panel de notas no podía traducir ninguna de estas líneas.** Los análisis estadísticos les ponían el
  prefijo del método a mano (`"%s: %s" % (mid, …)`) y unían varias frases con «; » en un solo titular para la
  barra de estado, así que la frase que llegaba a la ventana ya no era la que se había escrito. Ahora:
  - una línea sobre un método es `method_note`;
  - un titular es una lista (`stat.joined`) en la que cada frase conserva su código.
- **Cambio visible en el panel:** una línea estadística sobre un método se archiva bajo el **nombre** del
  método, como las notas del análisis desde 0.1.348, y no bajo su identificador. Por eso
  `test_partial_method_loss_v1170` cambia a propósito: espera el nombre.
- **Los dos causantes de pérdida tenían un fragmento inglés pegado en una frase compartida** («all %d samples
  %s»). Ahora son dos códigos, uno por tipo de análisis; `_STEM_GM` y `_STEM_OS` pasan a ser esos códigos.
- **Las causas contadas** («zero_driving x 17, raised ValueError x 3») son etiquetas con su código. La razón
  del motor (`zero_driving`) es un identificador y se enseña tal cual.
- **`_NOT_ITSELF` lo leen el banco y tres tests**, que toman la cabeza de la frase antes del primer « (». Queda
  como la plantilla del catálogo, con la misma cabeza; la frase la escribe su código.
- **El plan pedía que ningún castellano de esta familia llevara «: »**, porque el panel cortaba por ahí. Medido:
  desde 0.1.348 el panel agrupa una nota con código por su código y no corta su texto (`note_group`). La regla
  solo afectaba a las notas sin código, y de esta familia ya no queda ninguna. Así que el castellano sigue al
  inglés, que lleva «: » en varias frases.
- **Las notas de la norma «llegaban en inglés y se quedaban en inglés»**, como decía el comentario de
  `_factor_report_notes`. El resumen («eurocode7_da1c1: 1 material(s)…») iba dentro de un marco traducido.
  Ahora:
  - el resumen se dice en castellano;
  - las notas llegan al panel con su código, y antes `str()` se lo quitaba.
- **El factorizado de un anisótropo generalizado o de Snowden** unía con «; » las notas de sus hijos y sus
  funciones, y el papel de una función de Snowden («bedding», «rock mass») eran palabras de la frase. Ahora:
  - un código por papel;
  - la etiqueta del hijo, anidada con su código de 0.1.351.
- **Los tres textos de `run_configured_statistics`** (activar el análisis, definir una variable, sin
  superficie crítica determinista) ya se traducían, porque eran frases fijas. Llevan código como los demás.
- **Sin corregir:** el castellano de `stat.cps_steered` nombra las búsquedas en inglés («Grid, Slope, Path y
  Block»). Ya estaba así, y el generador no deja cambiar una entrada que existe. Va con los términos en
  0.1.354.

## 1. Qué cambia

- **`ogr_slip2d/stat_messages.py`** (nuevo), **58 códigos** `stat.*`:
  - las negativas antes de muestrear;
  - por qué no se muestreó un método;
  - la superficie probabilística crítica;
  - los cambios de masa y de caso de capas débiles, con su cabeza, sus tramos y sus casos anidados;
  - las causas contadas;
  - el titular unido.
- **`ogr_core/project/design_messages.py`** (nuevo), **10 códigos** `design.*`: el resumen, el marco del
  material, el sismo, el peso del terreno, las cargas y la norma que no cambia nada.
- **`ogr_core/materials/messages.py`:** **10 códigos** `factoring.*`: las tablas guardadas por versiones
  anteriores, el modelo sin coeficientes, el hijo que no se construye, las dos funciones de Snowden por papel
  y la lista unida.
- **`probabilistic.py`, `sensitivity.py`, `analysis_runner.py`** (`run_configured_statistics`),
  **`design_factors.py`, `strength_model.py` y `builtin_models.py`:** cada frase con su código.
- **La ventana:**
  - la barra de estado de la estadística dice sus avisos y errores por su código;
  - lo dicen igual las dos etiquetas de la ventana Estadística y la razón por método que enseña;
  - lo mismo la razón de la superficie probabilística crítica en *Interpretar*;
  - y las líneas que añade la norma, deterministas y estadísticas.
- **El castellano:** 66 entradas nuevas, más las 8 frases que ya tenían la suya.

## 2. Tests

- **`tests/test_stat_notes_v1353.py`** (nuevo, 15 casos):
  - **el inglés es el de 0.1.352, byte a byte:** 84 muestras que cubren todos los códigos. Son las
    expresiones y las definiciones de 0.1.352 (las dos clases de cambios de masa y de caso, el recuento de
    causas, el titular), leídas de su código fuente y ejecutadas con esas entradas;
  - cada código tiene su castellano, con los campos de la plantilla;
  - **censo AST** de 29 funciones; las claves de un diccionario de cambios son datos;
  - las constantes del módulo llevan su código, y la cabeza de `_NOT_ITSELF` es la de siempre;
  - **en castellano, con una corrida real:** la del notched de v1170, en la que Janbu se rechaza y Bishop se
    muestrea. Se mira:
    - la línea del panel, bajo el nombre del método;
    - el titular de la barra de estado;
    - la ventana Estadística;
  - también en castellano: una corrida sin variables aleatorias, y las líneas de la norma (EC7 DA1-C1) en
    Calcular y en la estadística;
  - el API sigue leyendo inglés.
- **Cambios deliberados**, todos porque una línea sobre un método se enseña con su nombre:
  - **`tests/test_partial_method_loss_v1170.py`:** el panel archiva la línea de un método bajo su nombre
    (`_shown`), y la ventana Estadística la enseña así;
  - **`tests/test_statistics_surface_line_v1255.py`:** la ventana Estadística enseña cada línea como la
    dice `note_line`, con el nombre del método y no con su identificador.

**Con el código de 0.1.352 fallan 14 de los 15.** El que pasa es el control de que el API sigue en inglés,
que tiene que pasar en los dos árboles. También fallan los de comportamiento:
- la línea del método perdido decía «janbu_simplified: The deterministic critical surface is a composite
  one…»;
- la ventana Estadística decía lo mismo en inglés bajo un título en castellano;
- las líneas de la norma decían «… 0 material(s) and 0 load(s) factored» dentro de un marco traducido.

## 3. Verificación

- **El test de esta versión**, 15/15 al primer intento.
- **Los vecinos:** 562 de 565, en 31 archivos: la estadística, el probabilístico, la sensibilidad, la pérdida
  parcial de métodos, la simetría de la reevaluación, las capas débiles en la estadística, la superficie
  probabilística crítica, la norma de diseño y sus coeficientes, el factorizado, la pendiente global, el
  castellano, los mensajes del núcleo, las capas, el API y la línea de órdenes. Los tres que fallaban
  esperaban que la ventana Estadística enseñara el identificador del método; corregidos a propósito (§2),
  46/46 en sus dos archivos.
- **El inglés no cambia:** las 84 muestras del test son las expresiones y las definiciones de 0.1.352,
  ejecutadas.
- **Suite entera:** 6477/6477, `EXIT=0`, 91 min.
- **Banco:**
  - raíz: `verificar_cierres.py` entero, 88 comprobaciones, 0 bajadas;
  - manual 02: la primera corrida **apartó dos bajadas**, D129 y D186. La comprobación de D129 esperaba que
    el panel archivara el método rechazado bajo su identificador («bishop_simplified»), y desde esta versión
    va bajo su nombre: es el cambio deliberado de §0. D186 caía solo porque D129 no cerraba. Se reancla
    D129: la línea va bajo su método, por su identificador hasta 0.1.352 o por su nombre desde 0.1.353, y
    sigue sin admitir «Modelo». Con eso, D129 y D186 cierran otra vez: 238 fichas, 0 bajadas;
  - D335, con su séptima parte apuntada;
  - instantánea `Evaluaciones/0.1.353`, prompts (34) y auditorías con 0 ERROR.
- **Ningún número del motor cambia:** solo cambia quién escribe la frase.

## 4. Pendiente

- **D335 sigue abierta.** Siguiente: el DXF, `invalid_summary` y los términos (0.1.354).
