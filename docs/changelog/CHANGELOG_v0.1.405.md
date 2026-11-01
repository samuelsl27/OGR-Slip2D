# OGR Slip2D v0.1.405

**Un cálculo no empieza mientras se escribe el archivo de resultados del último Calcular (D390).**

Es la tercera versión del plan que salió de la prueba de la interfaz de 0.1.402. Corrige lo que D385 (0.1.400) dejó
abierto al llevar el `.h5` a un hilo.

Ningún número se mueve, ni el contenido del archivo.

## 0. Lo que se encontró

- **Lo que vio la prueba (hallazgo 5):**
  - el `.h5` del Calcular en serie de B.7 no apareció en los más de 6 minutos de cálculos seguidos que lo siguieron
    (C.1, C.2 y C.3);
  - en F.1, sin otro cálculo detrás, se escribió unos 30 s después.
- **La causa, medida** (`_auditoria/P8_interfaz/h5_escritor_concurrente.py`, con la guarda del recolector instalada
  como en la ventana):
  - el `.h5` del Bishop de ACADS 1(a) a 25×25×12 (7421 evaluaciones) se escribe en 24,6 s con el escritor solo, y en
    **122,3 s** con un Calcular en serie a la vez;
  - el escritor comparte el intérprete con el hilo del cálculo, y hace decenas de miles de llamadas cortas a HDF5,
    cada una esperando a recuperar su turno;
  - antes de 0.1.400 el archivo se escribía siempre antes del cálculo siguiente.
- **El hallazgo 3 (+692 MB tras el Cancelar en serie de C.1) no es el escritor:**
  - medido, con la sonda `h5_memoria_escritor.py` ya corregida, el escritor añade **39 MB** de pico (de 741 a 780 MB
    privados);
  - la primera versión de esa sonda leía ceros: dejaba el pseudo-handle del proceso (-1) a la conversión por defecto
    de `ctypes` y la llamada fallaba;
  - lo más probable es el asignador: tras el Cancelar los objetos se liberan (D382 lo comprueba con 0 resultados
    vivos), pero la memoria privada se queda en el máximo alcanzado hasta que el asignador devuelve las páginas, lo que
    encaja con los −759 MB de golpe de C.2. No se toca.

## 1. Qué cambia

- **`ogr_gui/background.py`:**
  - **`wait_for_results_file(window)`:** si el `ResultsWriter` de la ventana sigue escribiendo, enseña un diálogo
    modal de ventana con «Guardando el archivo de resultados...», barra de actividad y sin Cancelar, y espera en un
    bucle de eventos local a que termine. La ventana sigue respondiendo, y el modelo no se puede editar entretanto. Sin
    escritor en marcha, no hace nada.
    - Se conecta a `finished` antes de preguntar si el hilo sigue en marcha, para que un final que llegue entre medias
      no deje el bucle esperando para siempre.
  - **`run_task`** la llama antes de arrancar su hilo. Es la puerta de todas las tareas de la ventana: Calcular, el
    barrido, la estadística, el agua subterránea, el retroanálisis y la optimización. Todas compiten con el escritor.
- **`tests/test_results_file_first_v1405.py`**, nuevo: 2 tests.
- El número en los nueve sitios y el contador de los dos README.

**Una diferencia con el plan:** la ficha pedía que también Abrir esperase al archivo pendiente, y no lo hace.
- Abrir otro proyecto no compite por el intérprete: carga un `.ogr` en un momento.
- El escritor ya tiene su ruta y su resultado, y no pisa nada del proyecto nuevo.
- El cálculo siguiente, en ese proyecto o en otro, espera por `run_task`.

## 2. Qué se probó

- **`tests/test_results_file_first_v1405.py`,** con la ventana real y la escritura retenida por un evento que suelta un
  temporizador corto mientras la ventana espera:
  - un cálculo pedido mientras se escribe el archivo se ejecuta después de escrito, y aparece el diálogo de espera;
  - sin escritura en marcha, el cálculo empieza en el acto y no aparece ese diálogo.
- **La discriminación:** con el `background.py` de 0.1.404, el primero falla con `['calculation', 'file written']`.
- **Los vecinos:** tareas en hilo, Cancelar, D382, el escritor de D385, el progreso y cerrar con cambios: 49 de 49.
- **La suite entera con `--jobs 4`:** **6958 de 6958, `Failed: 0`**, sin `Leaks` ni `Chunks died`, en 24 min. La serie
  no se repite: la versión no toca el pool.

## 3. El banco

- **D390 cerrada,** CUBIERTO POR TEST.
  - `d390()` en el `verificar_cierres.py` de la raíz, con la ventana real: con la escritura retenida, el orden es
    «archivo → cálculo».
  - Discriminada contra 0.1.404, que es donde vive el defecto: da SIGUE ABIERTO («cálculo → archivo»). Contra 0.1.397
    no discrimina nada útil, porque ese árbol aún escribía el archivo en el hilo de la ventana, antes de volver de
    `_on_compute_done`.
  - Instantáneas `Evaluaciones/0.1.405` en la raíz y en el 02, el índice de cerrados, `PAQUETES` podado, la cadena de
    P8 tachada y los prompts regenerados.
  - `auditoria_invariantes.py` sin ERROR en los dos bancos.

## 4. Lo que queda

- **El plan:** D391 (Abrir pregunta si guardar). Después, D383.

## Archivos

- `ogr_gui/background.py`
- `tests/test_results_file_first_v1405.py` (nuevo)
- `docs/changelog/CHANGELOG_v0.1.405.md` (nuevo)
- `README.md`, `README.es.md`
- `pyproject.toml`, `ogr_gui/main_window.py` y los `__init__.py` de `ogr_core`, `ogr_slip2d`, `ogr_fem2d`, `ogr_gui`,
  `ogr_cli`, `ogr_api` y `ogr_mcp` (el número)
