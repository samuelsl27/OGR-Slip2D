# OGR Slip2D v0.1.289

**El idioma y el tema elegidos en *Preferences* se guardan y se aplican al
arrancar (D290).** Hasta ahora el aviso «Restart the application to fully
apply translations» era falso: no se guardaba nada, y al reiniciar volvía el
inglés.

## 0. Lo que se encontró

- **La prueba de la interfaz** de 0.1.284
  (`_auditoria/P6_0284/INFORME_prueba_GUI_0.1.284.md`, H1):
  1. *File → Preferences… → Language: Español → Save*.
  2. Salía el aviso en inglés y los menús seguían en inglés.
  3. Tras reiniciar, *Preferences* decía «Language: English».
- **El código:**
  - `ogr_gui/i18n` arranca con `_LANG = "en"`;
  - `_apply_language` cambiaba el idioma de la sesión y abría el aviso;
  - nada lo guardaba ni lo leía al arrancar, y el tema tampoco;
  - los menús, la barra de herramientas y la barra de estado toman sus textos
    de `tr()` una sola vez, al construirse, así que un idioma puesto después
    no los alcanza.
- **El efecto:** la interfaz entera en castellano no existía. Nunca desde el
  arranque; en caliente, solo los diálogos que se abrían después.
- **Decisión de la propietaria:** guardar y reiniciar, sin retraducir en
  caliente.
- **Hallazgo nuevo, de la regla 7:** las tres casillas de *Preferences*
  («Show Tabs for Multiple Windows», «Mark file as modified after importing» y
  «Default to compressed format when saving») no las lee nadie. Se abre como
  D299, sin tocarlas.

## 1. Qué cambia

- **`ogr_gui/user_prefs.py`** (nuevo) guarda el idioma y el tema.
  - Usa `QSettings("OpenGeoRock Suite", "OGR Slip2D")`: el registro del usuario
    en Windows y un archivo local en otros sistemas. Nada sale del equipo.
  - Con la variable `OGR_SETTINGS_DIR` usa un INI en esa carpeta.
  - Un valor que esta versión no conoce se ignora.
- **`ogr_gui.__main__.apply_saved_preferences(app)`** pone el idioma y el tema
  guardados ANTES de construir la ventana. Sin nada guardado, inglés y el tema
  claro, como siempre.
- **`_apply_language`** guarda la elección y avisa en el idioma recién
  elegido: «Idioma cambiado. Reinicia OGR Slip2D para ver en él los menús y las
  barras de herramientas.».
- **`_apply_theme`** guarda el tema, y la ventana arranca con el guardado.
- **El runner** (`tests/_runner.py`) pone `OGR_SETTINGS_DIR` en una carpeta
  propia, junto a `OGR_BRIDGE_DIR`: ningún test toca las preferencias del
  usuario. Los tests que construyen una ventana directamente no leen nada y
  siguen en inglés.

## 2. Tests

`tests/test_language_saved_v1289.py`, 8 casos:
- sin nada guardado no se lee nada;
- lo guardado se lee de vuelta, en la carpeta indicada;
- un idioma o un tema desconocidos se ignoran;
- `apply_saved_preferences` pone el idioma y el tema guardados;
- una ventana construida después tiene la barra en castellano («Ajustes de
  proyecto...», «Agua subterránea»);
- sin nada guardado, arranca en inglés y con el tema claro;
- elegir un idioma lo guarda y avisa en ese idioma;
- elegir un tema lo guarda.

Con el código de 0.1.288, el archivo no puede ni importarse.

**`test_i18n_coverage_v141`:** el presupuesto de mensajes sin traducir baja de
63 a 62, porque el aviso de idioma ya pasa por `tr()`.

## 3. Verificación

- **Suite entera:** 5903 / 5903, con código de salida del proceso 0.
- **`verificar_cierres.py` de la raíz:** `d290()` da CUBIERTO POR TEST;
  33 comprobaciones, ninguna bajada.

## 4. Lo que se abrió

- **D299:** las tres casillas de *Preferences* que nadie lee. Está en P8, con
  prompt largo.

## 5. Lo que no se ha probado

- **A mano:** elegir Español, cerrar, abrir y ver los menús en castellano.
  Hasta D291, 26 entradas de menú siguen en inglés porque no tienen
  traducción.
