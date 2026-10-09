# OGR Slip2D v0.1.292

**Los textos propios de Qt siguen el idioma guardado (D302).** Con la
interfaz en castellano, los botones estándar salían en inglés: «Yes», «No»,
«Save», «Cancel».

## 0. Lo que se encontró

- **La segunda prueba de la interfaz**
  (`_auditoria/P8_interfaz/INFORME_prueba_GUI_0.1.290.md`, H8 y §4):
  - la pregunta de *Cargar talud de ejemplo* llevaba «Yes» y «No»;
  - *Preferences* tenía «Save» y «Cancel», y *Generate FE Mesh*, «Cancel».
- **La causa.** Esos botones los escribe Qt y se traducen con el catálogo del
  propio Qt, no con `ogr_gui/i18n`. PySide6 trae `qtbase_es.qm` en su carpeta
  de traducciones (comprobado), y ningún `QTranslator` lo cargaba.
- **Medido sin pantalla:** con el catálogo cargado, «&Yes» pasa a «&Sí», «Save»
  a «Guardar» y «Cancel» a «Cancelar». Al quitarlo, vuelve el inglés.

## 1. Qué cambia

- **`ogr_gui.__main__.install_qt_translator(app, lang)`** carga `qtbase_<lang>`
  desde la carpeta de traducciones de Qt.
  - Lo instala en la aplicación y lo devuelve.
  - Con inglés, o si el catálogo no existe, no hace nada y devuelve None.
- **`apply_saved_preferences`** lo llama con el idioma guardado (D290), antes de
  construir la ventana, y devuelve el traductor instalado.
- **`test_language_saved_v1289`** quita los traductores que instala al aplicar el
  castellano, para que no se filtren a los tests siguientes (regla 5).

## 2. Tests

`tests/test_qt_translations_v1292.py`, 3 casos:
- con el castellano, el «Yes» de un cuadro de mensaje es «&Sí», y el «Save» y el
  «Cancel» de una botonera son «Guardar» y «Cancelar»; al quitar el traductor,
  vuelve «&Yes»;
- el inglés no carga nada;
- `apply_saved_preferences` con el castellano guardado lo instala.

## 3. Verificación

- **Suite entera:** 5912 / 5912, con código de salida del proceso 0.
- **`verificar_cierres.py` de la raíz:** `d302()` da CUBIERTO POR TEST;
  39 comprobaciones, ninguna bajada.
- **Tests de idioma y traducción** (4 archivos, 31 casos): verdes.

## 4. Lo que no se ha probado

- **A mano:** con el castellano guardado, la pregunta de *Cargar talud de ejemplo*
  y los botones de *Preferences*.
