# OGR Slip2D v0.1.296

**Cerrar el programa con cambios sin guardar pregunta antes (D283):
Guardar / Descartar / Cancelar, la misma pregunta que ya hacía _Nuevo
proyecto_.**

## 0. Lo que se encontró

- **La primera vez,** en la prueba manual de D191 (0.1.276): se cerró la ventana
  con la X tras cambiar propiedades y el programa terminó sin preguntar nada.
- **La segunda prueba de la interfaz**
  (`_auditoria/P8_interfaz/INFORME_prueba_GUI_0.1.290.md`, H1) lo repitió tres
  veces con *Archivo → Salir* y Ctrl+Q: con un modelo definido por MCP, tras
  cambiar el tema y con el talud de ejemplo.
  - *Nuevo proyecto* y *Cargar talud de ejemplo* sí preguntaban.
- **El código.** `MainWindow.closeEvent` solo desregistraba la sesión y paraba el
  puente del agente. *Salir* es `self.close`, así que todo pasa por ahí.
- **Por qué no se hizo antes.** Una pregunta modal al cerrar bloquearía la suite,
  que cierra cientos de ventanas con el proyecto cambiado.
- **Un comentario caducado.** El docstring de `ogr_api.snapshot.document_hash`
  decía que `is_dirty` no sirve, porque guardar lo limpia y la notificación lo
  vuelve a poner. Eso se arregló en 0.1.203 (`Project._notify`). Medido hoy:
  tras guardar, `is_dirty` es `False`.
- **Decisión de la propietaria:** preguntar como *Nuevo proyecto*, y solo con
  cambios sin guardar.

## 1. Qué cambia

- **`MainWindow._ask_unsaved(title, text)`:** una sola pregunta Guardar /
  Descartar / Cancelar, que devuelve `"save"`, `"discard"` o `"cancel"`.
  - Sin pantalla (la plataforma `offscreen` de la suite) nadie puede contestar,
    así que devuelve `"discard"` sin abrir nada.
  - *Nuevo proyecto* pasa a usarla, con el mismo texto.
- **`closeEvent`:** con cambios sin guardar pregunta «Salir» / «El proyecto tiene
  cambios sin guardar. ¿Guardar primero?».
  - **Cancelar:** no cierra.
  - **Guardar:** guarda, y si no se guardó (*Guardar como* cancelado, un error),
    no cierra.
  - **Descartar:** cierra.
  - La sesión se desregistra y el puente se para solo si la ventana se cierra de
    verdad.
- **El docstring de `document_hash`** dice ya que `is_dirty` es fiable desde
  0.1.203.

## 2. Tests

`tests/test_close_asks_v1296.py`, 7 casos, con la pregunta sustituida:
- un proyecto sin cambios se cierra sin preguntar;
- con cambios, Cancelar mantiene la ventana (el evento queda ignorado y la sesión
  no se desregistra);
- Descartar cierra;
- Guardar con archivo guarda y cierra;
- Guardar con *Guardar como* cancelado no cierra;
- *Archivo → Salir* pasa por la pregunta;
- sin pantalla, la pregunta contesta Descartar sola y no bloquea.

Con el código de 0.1.295 fallan cinco.

## 3. Verificación

- **Suite entera:** 5927 / 5927, con código de salida del proceso 0.
- **`verificar_cierres.py` de la raíz:** `d283()` da CUBIERTO POR TEST;
  40 comprobaciones, ninguna bajada. D283 estaba en P1, la abrió la prueba
  manual de 0.1.276.

## 4. Lo que no se ha probado

- **A mano:** cambiar algo y pulsar *Archivo → Salir* (debe salir la pregunta;
  Cancelar no cierra; Guardar guarda y cierra), y lo mismo con la X.
