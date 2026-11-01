# OGR Slip2D v0.1.400

**El archivo de resultados de un Calcular se escribe fuera del hilo de la ventana, que ya no se congela al terminar
(D385).**

Es la tercera versión del plan que salió de la prueba de la interfaz de 0.1.397. La decisión de la propietaria:
cerrar la ventana espera a que el archivo termine de escribirse, en vez de abandonarlo.

Ningún número se mueve, y el archivo tampoco: el mismo `save_results`, el mismo formato y los mismos bytes.

## 0. Lo que se encontró

- **Lo que vio la prueba (DUDA 3):** tras cerrarse el diálogo de progreso, la ventana se quedó en «No responde» de 1 a
  3 minutos, con el panel todavía en «Todavía no hay resultados.».
- **La causa:**
  - `_on_compute_done` llamaba a `save_results` en el hilo de la ventana siempre que el proyecto tenía ruta;
  - escribe un grupo HDF5 por superficie, con sus atributos y un dataset comprimido.
  - El `.h5` de la prueba (207 MB) lleva fecha 04:13:50, el final del cuelgue de 04:11:55–04:13:52. La auditoría del
    cómputo lo había medido: 47,2 s para el Bishop de K03.
- **La puerta, antes de tocar nada** (`_auditoria/P8_interfaz/d385_guardado_h5.py`, el Bishop de K03, 28 759
  evaluaciones, 207 MB):
  - en línea, **55,2 s**; en un hilo, **55,4 s**: el hilo no lo hace más lento. Hoy, con la máquina frenada, va algo
    por encima de los 47 s de la auditoría;
  - con un latido de 50 ms en el hilo principal mientras escribe el hilo: 881 latidos, **el hueco mayor 0,095 s**,
    ninguno por encima de 0,2 s. El umbral para cambiar de plan era 0,5 s;
  - los dos archivos son **idénticos byte a byte**.
- **Cuánto puede tardar la espera al cerrar:** lo que le quede al guardado, unos 1,6–1,9 ms por superficie del primer
  método, que es el único que se guarda:
  - ~7 s en una rejilla de 20×20×10;
  - ~19 s en una de 31×31×12;
  - ~50–55 s en una de 51×51×12;
  - ~2 min con la RAM llena.
- **Lo que no cambia:** solo se guarda el primer método, y nada en la ventana vuelve a leer el archivo.

## 1. Qué cambia

- **`ogr_gui/background.py`:**
  - **`write_results_file(path, result, project_id)`:** `save_results` en `<nombre>.h5.tmp`, que luego se mueve encima
    con `os.replace`. Devuelve '' o lo que falló, y en ese caso borra el `.tmp`. Una escritura cortada no deja medio
    archivo con el nombre del de resultados, y una que falla deja el anterior como estaba.
  - **`ResultsWriter`:** el `QThread` que la llama. No retiene el resultado más allá de la escritura y avisa con
    `written`.
- **`ogr_gui/main_window.py`:**
  - **`_write_results`:** el resultado se publica al momento y el archivo lo escribe un `ResultsWriter`. Sin pantalla
    (los tests y las comprobaciones del banco) se escribe en el sitio, como antes, por la misma función.
  - **`_wait_results_writer`:** espera a la escritura en curso, con «Guardando el archivo de resultados...» en la barra
    y el cursor de espera, sin diálogo modal. La llaman la escritura siguiente (un archivo cada vez, que es además lo
    que mantiene vivo el `QThread` hasta que termina) y `closeEvent`, tras la pregunta de los cambios sin guardar.
  - **`_on_results_written`:** si la escritura falla lo dice («No se pudo guardar el archivo de resultados: …»). Antes
    se callaba.
  - El `save_results` que la ventana importaba ya no se usa.
- **`ogr_gui/i18n/__init__.py`:** las dos frases, con su castellano.
- **`tests/test_results_writer_v1400.py`**, nuevo: 5 tests.
- El número en los nueve sitios y el contador de los dos README.

**Dos cosas del plan que cambiaron al escribirlo:**
- **Calcular de nuevo y abrir otro proyecto no esperan.** El escritor tiene su ruta y su resultado, así que no hace
  falta. Solo espera la escritura siguiente, que es la que podría pisar el archivo, y el cierre de la ventana.
- **No se avisa al terminar bien.** La barra de estado guarda un solo mensaje y en ese momento es el del factor de
  seguridad (la lección de D96): en un guardado de un segundo, el aviso lo habría tapado. Sí se avisa si falla.

## 2. Qué se probó

- **`tests/test_results_writer_v1400.py`,** con la ventana real. Las escrituras las retiene un evento que el test
  suelta, nunca un reloj; donde la ventana espera, lo suelta un temporizador corto y lo que se comprueba es el orden.
  - Con pantalla, el resultado está en la ventana mientras el archivo aún no existe, y el archivo que aparece es byte
    a byte el de `save_results`.
  - Un archivo cada vez: la segunda escritura empieza después de que acabe la primera.
  - Cerrar espera al archivo, y no deja ni `.tmp` ni hilo.
  - Una escritura que falla se dice en la barra, no deja `.tmp` y deja el archivo anterior intacto.
  - Sin pantalla, el archivo está escrito al volver de `_on_compute_done`, con los mismos bytes.
- **La discriminación:** con la ventana y `background.py` de 0.1.399 fallan los 5.
- **Cuatro mutantes, cada uno cazado:**
  - escribir siempre en línea: 2 fallos;
  - cerrar sin esperar: 1;
  - escribir sin `.tmp`: 1, después de añadir al test el archivo anterior;
  - callar el fallo: 1.
  - Dos mutantes se dejaron fuera a propósito: no esperar antes de la escritura siguiente, y quitar la espera de
    dentro de `_wait_results_writer`. Destruirían un `QThread` en marcha, y eso aborta el proceso (D362).
- **Un camino equivocado, mío:** la primera versión del test esperaba ver `a.h5.tmp` en el registro de escrituras,
  pero la función recibe el nombre definitivo. El orden era el correcto.
- **Los vecinos:** traducciones, tareas en hilo, Cancelar, resultados caducos y D382, 80 de 80.
- **La suite entera con `--jobs 4`:** **6941 de 6941, `Failed: 0`**, sin `Leaks` ni `Chunks died`, en 25 min. La
  serie no se repite: la versión no toca el pool, y la última en verde es la de 0.1.399, un commit atrás.

## 3. El banco

- **D385 cerrada,** CUBIERTO POR TEST.
  - `d385()` en el `verificar_cierres.py` de la raíz, con la ventana real y el Calcular de demostración:
    - con la escritura retenida, el resultado está en la ventana y el archivo todavía no;
    - soltada, el archivo es byte a byte el de `save_results`;
    - cerrar con otra escritura retenida espera al archivo.
  - Discriminada: con el árbol de 0.1.397, cuya ventana guarda igual que la de 0.1.399, da SIGUE ABIERTO («el archivo
    se escribe en el hilo de la ventana»); con este, CUBIERTO POR TEST.
  - Instantáneas `Evaluaciones/0.1.400` en la raíz y en el 02, el índice de cerrados, `PAQUETES` podado, la cadena de
    P8 tachada y los prompts regenerados.
  - `auditoria_invariantes.py` sin ERROR en los dos bancos.
- La puerta queda en `_auditoria/P8_interfaz/d385_guardado_h5.py`.

## 4. Lo que queda

- **El plan, en orden:** D386 (el ajuste de paralelo no caduca el resultado, si la propietaria está de acuerdo) y
  D387 (un análisis del agente se deserializa una vez).
- **Después:** la prueba a mano redimensionada a 31×31×12, que comprobará en pantalla que la ventana responde tras
  Calcular, y D383 con su revisión de diseño.

## Archivos

- `ogr_gui/background.py`, `ogr_gui/main_window.py`, `ogr_gui/i18n/__init__.py`
- `tests/test_results_writer_v1400.py` (nuevo)
- `docs/changelog/CHANGELOG_v0.1.400.md` (nuevo)
- `README.md`, `README.es.md`
- `pyproject.toml`, `ogr_gui/main_window.py` y los `__init__.py` de `ogr_core`, `ogr_slip2d`, `ogr_fem2d`, `ogr_gui`,
  `ogr_cli`, `ogr_api` y `ogr_mcp` (el número)
