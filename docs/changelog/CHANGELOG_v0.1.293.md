# OGR Slip2D v0.1.293

**Lo que D291 dejó en inglés en la ventana principal pasa por `tr()` (D291b).**
El test de D291 solo leía los argumentos directos de los mensajes. Así se le
escapaban los textos armados antes en una variable, los títulos y etiquetas
de los diálogos de entrada, los informes y un motivo que viene del núcleo.

## 0. Lo que se encontró

- **Visto en la segunda prueba de la interfaz**, con la interfaz en castellano
  (`_auditoria/P8_interfaz/INFORME_prueba_GUI_0.1.290.md`, H3 y §4):
  - el motivo de *Malla de presiones de agua…*. Viene de `rules.grid_refusal`;
    la ventana le aplica `tr()`, pero la clave no tenía castellano;
  - «(default properties used for: …)»;
  - «FS crítico (…): …  (2 methods computed — open Interpret …)», a medias.
- **Medido con el AST,** contando todas las f-strings con letras de
  `main_window.py`:
  - «FE mesh: N elements…», con lo descartado en inglés porque sus nombres
    vienen de `rules.set_fem_mesh`;
  - «Transient: N stage(s) solved…» y «(stages not converged…)»;
  - «External {mode}ed.», que también hacía «shrinked»;
  - el menú contextual de una región;
  - el informe de limpieza de la geometría;
  - el *Info Viewer*;
  - la lista de cargas para borrar;
  - los mensajes de la estadística («PF = … beta = …», «most sensitive: …»);
  - el nivel de desembalse crítico;
  - las anotaciones convertibles;
  - los títulos y etiquetas de *Generate FE Mesh*, *Move Boundary*, *Expand /
    Shrink External* y *Select Boundary*;
  - el filtro de imágenes.

## 1. Qué cambia

- **Plantillas con `tr()`.** Cada uno de esos textos pasa a
  `tr("…").format(…)`, con el inglés igual y su castellano: 37 claves nuevas.
  - Los nombres de lo que descarta una malla nueva se traducen en la ventana.
    `rules` sigue devolviendo las claves inglesas, que también lee el API.
  - El participio de expandir y contraer sale de un diccionario por idioma,
    como en la pregunta de D291.
- **Lo que se queda, por ser datos y no interfaz:**
  - el título de la ventana: el nombre del producto y el del proyecto, porque
    un proyecto nuevo se llama «Untitled» y el de ejemplo «Demo slope»;
  - el nombre del archivo del informe;
  - los nombres de los pasos de deshacer, que el agente lee en
    `project_history`;
  - los nombres por defecto de las cargas, que guarda el `.ogr`.

## 2. Tests

`tests/test_window_english_left_v1293.py`, 3 casos:
- **los motivos:** cada acción desactivada de un proyecto nuevo que lleva
  motivo lo lleva traducido. La misma ventana construida en inglés y en
  castellano enseña dos textos de estado distintos;
- **la malla:** generarla desde la ventana, con el castellano activo, lo dice
  en castellano («Malla de elementos finitos: …»);
- **ninguna f-string con letras** queda en `main_window.py`, leído con el AST,
  fuera de los datos de arriba, que el test lista con su razón. No cuentan los
  formatos de número (`:.1f`) ni las etiquetas HTML.

Con el código de 0.1.292 falla el último caso, con unas 30 f-strings.

## 3. Verificación

- **Suite entera:** 5915 / 5915, con código de salida del proceso 0.
- **`verificar_cierres.py` de la raíz:** `d291b()` da CUBIERTO POR TEST;
  39 comprobaciones, ninguna bajada.
- **Tests de traducción, menús y ventana** (7 archivos, 198 casos): verdes.

## 4. Lo que no se ha probado

- **A mano:** con el castellano guardado, mallar, calcular un transitorio y abrir
  el *Info Viewer* y la limpieza de la geometría.
