# OGR Slip2D v0.1.375

**`python tests/_runner.py --jobs N` reparte la suite en N procesos y no deja que un tramo muerto pase por
un verde.** Con `--jobs 4`, la suite entera tarda **35,2 min** frente a los 74,6 en serie. Es la etapa 3 del
plan de la auditoría de la suite (`docs/audits/AUDITORIA_SUITE_v0.1.372.md`). **Ningún módulo del programa
cambia**, salvo el número de versión. La corrida en serie, sin `--jobs`, sigue siendo la de la CI y la que
exige publicar: si `--jobs` vale también para eso es decisión de la propietaria en la etapa 4.

## 0. Lo que se encontró

- **Partir la suite destapó cuatro fugas que la corrida en serie esconde por el orden.** Las dio la primera
  suite entera con `--jobs 4`: 6676/6676 y `Leaks: 4`. Ninguna es un test nuevo mal escrito. Son estados
  que en serie se fijan siempre en el mismo archivo, y en un tramo en otro.
  - **Estado que se crea una vez por proceso**, en el primer archivo que lo usa:
    - `builtins.qApp: None → QApplication` en `test_pick_ampersand_v1287`. PySide6 nombra ahí la aplicación al
      crearla.
    - `ogr_gui.core_messages._CATALOGUE: len=0 → len=482` en `test_dxf_export_census_v1354`. Es la tabla de
      todos los códigos de mensaje, que se llena una vez desde tablas constantes.

    En serie, el primer uso cae en el archivo que importa por primera vez el módulo, y el detector no compara
    una clave nueva. En un tramo, un archivo importó y otro llenó. Van a la lista blanca solo para ese cambio:
    de `None` a la aplicación y de vacío a lleno en el mismo objeto. Cualquier otro cambio sigue siendo fuga, y
    hay un test de cada regla.
  - **Un archivo de test cambiaba el backend de matplotlib al importarse.** `test_interpret_i3_v153` y
    `test_statistics_gui_v138` hacían `matplotlib.use("Agg")` a nivel de módulo, y otros archivos los importan
    como bibliotecas de ayuda (4 y 7).
    - En serie el archivo original ya se había cargado, y la importación no hacía nada.
    - En el tramo 4, `test_streamlines_v1332` lo importó por primera vez y dejó `QtAgg → Agg`. Después,
      `test_support_level_tolerance_v1254` abrió una gráfica y el programa volvió a `QtAgg`.
    - Ninguno de los dos archivos dibuja con `pyplot`. Las ventanas que prueban fijan `QtAgg` y usan
      `FigureCanvasQTAgg` explícitamente, así que se quita la llamada y lo que validan no cambia.
    - Otros doce archivos llaman a `matplotlib.use("Agg")`. Lo hacen dentro de una función que a
      continuación abre una ventana del programa, o en un archivo que nadie importa. En las tres suites
      enteras, su archivo termina como empezó. Se quedan como están, y si eso cambiara el detector los
      nombraría.
- **En esta máquina ninguna N evita la paginación, ni siquiera la serie.** El plan pedía tomar por defecto
  «el mayor N que no pagine». Pero la corrida en serie ya bajaba a 359 MB libres en 0.1.373.
  - Con N tramos, la suma de memoria privada de los procesos de la suite llega a 13,5–15,3 GB, frente a los
    12,6 de la serie medida igual, con los trabajadores de sus pools (§2). La máquina tiene 15,9 GB.
  - Manda entonces el reloj: N=4 es la más rápida medida (§2), y **no hay N por defecto**. `--jobs` pide el
    número, y el README da la medida.
  - De los 6,2 GB libres al empezar, faltaban 3 GB ocupados por procesos de Python ajenos a la suite:
    10 servidores MCP `ogr-slip2d-mcp`, cada uno de una sesión de Claude Code en VS Code, abiertos
    entre el 22 y el 27 de octubre. *Corregido en 0.1.376: esto decía «11 procesos» y «de Claude
    Desktop».*
- **La duración de un archivo en serie no predice la que tiene en un tramo.** Con N=4 se esperaban unos
  17 min por tramo, a partir de las duraciones de 0.1.373, y cada uno tardó 27–34 min.
  - Compiten por 4 núcleos físicos los tramos y los pools de procesos que abren sus tests, y además pagina.
  - El reparto sigue siendo útil, porque equilibra proporciones. Las duraciones se reescriben tras cada
    corrida, en serie o en paralelo.
- **Un camino equivocado mío, al escribir el reparto.** El relleno voraz con el tope óptimo puede usar menos
  tramos que N: `[1, 3, 1, 4, 1]` en 3 daba 2. Lo vio el test al pedir tres procesos. Ahora se parte el
  tramo más pesado de dos archivos o más por su punto más equilibrado, que nunca sube el máximo, hasta tener N.
- **Dos cambios respecto al plan:**
  - En el carril en serie van solo los tres archivos que se comparan con el reloj, no los tests del runner:
    estos no dependen de correr solos, y en un tramo prueban el mismo código.
  - El hijo recibe la lista exacta de sus archivos en un JSON (`--child`) en vez de `--chunk k/N`. Así, el
    reparto no puede salir distinto en el padre y en el hijo si las duraciones cambian entre los dos.

## 1. Qué cambia

**`tests/_runner.py`:**

- **`--jobs N`.** Toma los archivos de la selección que no van al carril en serie y los parte en N tramos
  contiguos del orden alfabético. El tramo más pesado es lo más ligero posible: es el problema de la
  partición lineal, resuelto con bisección sobre la capacidad y relleno voraz.
  - El peso de cada archivo es lo que tardó la última vez. Un archivo nunca medido pesa sus tests por la
    mediana de segundos por test de los medidos.
  - Las duraciones viven en `%TEMP%/ogr-slip2d-test-durations.json` y no en el repositorio: describen la
    máquina, no el código. Las escribe cada corrida sin `-k` de la carpeta propia del runner. Una corrida
    filtrada actualiza sus archivos y deja los demás.
  - Cada tramo es un proceso hijo con el mismo runner (`--child SPEC`) y el mismo bucle, ahora
    `_run_files`: la misma colección y congelación, la misma restauración, el mismo detector de fugas.
  - El padre copia la salida de cada tramo en orden, a medida que se escribe, con la numeración de toda la
    corrida. Se lee como una corrida en serie.
  - El hijo hereda la consola a propósito. Sin consola, el programa manda sus pools a `pythonw.exe`
    (`ogr_slip2d.processes`), y un tramo probaría algo distinto que la serie.
- **El carril en serie.** Los archivos con `SERIAL_LANE = True` a nivel de módulo, leído del código fuente
  sin importarlo, corren al final, solos, en su propio proceso. Son tres:
  - `test_optimizations_v111`: una rejilla en menos de 5 s;
  - `test_jobs_file_race_v1198`: una escritura en menos de 5 s;
  - `test_remote_oauth_v1204`: 40 s para que arranque su servidor.
- **La completitud.** La corrida pasa solo si se cumplen tres condiciones; si no, sale
  `✗ [CHUNK] chunk 1/2 died: exit 3 in test_x.py, after test_w.py; 3 of its 4 file(s) did not finish (log: …)`,
  `Chunks died: N` en los totales y código 1. El registro del tramo se conserva.
  - Cada tramo anota cada archivo que termina y su propio final.
  - Cada tramo sale con el código que piden sus resultados.
  - Los tests corridos suman los que declara el código fuente.
- **`--list --jobs N`** enseña los tramos sin correr nada. Tras los totales, una línea recuerda que una
  versión sigue exigiendo la corrida en serie.

**Tres archivos de test** llevan `SERIAL_LANE = True`, con su porqué.

**`test_interpret_i3_v153` y `test_statistics_gui_v138`** dejan de cambiar el backend de matplotlib al
importarse.

**`tests/_leaks.py`:** dos entradas más, con la regla nueva `FILLED_ONCE`; `ALLOWED` tiene ahora 22.

**`tests/test_runner_jobs_v1375.py` (22 casos)**, sobre archivos desechables y con hijos de verdad:

- los mismos totales que la serie, cada archivo una vez, en orden, con el carril al final y la numeración
  de toda la corrida;
- tres procesos, cada uno un trozo contiguo; el carril en otro proceso, después de todos;
- el reparto, óptimo frente a una búsqueda exhaustiva y con tantos tramos como se piden;
- la marca del carril, leída sin ejecutar el archivo;
- las cuatro fugas inyectadas de 0.1.374 fallan dentro de un tramo como en serie;
- un `os._exit(3)` en el segundo test de un archivo da el mensaje de arriba, y el otro tramo sigue informando;
- un test que el código fuente no declara (heredado de una clase que no es `Test`) hace fallar la corrida;
- las duraciones no se escriben para archivos desechables, y se fusionan.

**`tests/test_leaks_v1374.py`:** dos casos, uno por regla nueva.

**Los dos README:** un párrafo sobre `--jobs`, con la medida.

## 2. Medida

Suites enteras el 2026-10-28, en el portátil de desarrollo (4 núcleos físicos y 8 lógicos, 15,9 GB), una
cada vez:

| Corrida | Casos | Resultado | Reloj | Mínimo libre | Tiempo con < 1 GB libre | Pico privado de la suite |
|---|---|---|---|---|---|---|
| Serie 0.1.374 | 6654 | verde | 74,6 min | — | — | — |
| `--jobs 4`, primera | 6676 | `Leaks: 4` (§0) | **35,2 min** | 229 MB | 9,6 min | ~13,5 GB |
| `--jobs 3`, con los arreglos | 6678 | verde | 40,9 min | 349 MB | 10,7 min | ~15,3 GB |
| Serie 0.1.375 | 6678 | verde, sin fugas | 68,6 min | 446 MB | 9,1 min | ~12,6 GB |

- **×2,1 con N=4.** La estimación de la auditoría era de 20–25 min. No se alcanza por la competencia por
  los núcleos y por la paginación (§0).
- **La serie de 0.1.375 no es más rápida que la de 0.1.374,** aunque el reloj diga 68,6 frente a 74,6 min:
  dos corridas iguales de 0.1.374 difirieron 3,7 min, y esta versión no quita trabajo a la serie. Lo que
  añade es escribir las duraciones al final, una vez.
- **No corro N=2.** También pagina, porque lo hace hasta la serie, y sería más lenta que N=3.
- El «pico privado» es la suma de la memoria privada de todos los procesos de Python, menos los 3 GB de los
  servidores ajenos. Incluye memoria ya paginada.

## 3. Qué no cambia

- **Ningún número del programa.** Cambian el runner, el detector, siete archivos de test, uno nuevo, la
  versión y los README.
- **`python tests/_runner.py` sin argumentos** corre los mismos archivos, en el mismo orden, con la misma
  salida y el mismo veredicto. El bucle pasó a una función, y los dos tests que leen su código (el de
  `gc_guard` y el de 0.1.373) siguen pasando sin tocarlos. Lo único nuevo es que escribe las duraciones en
  `%TEMP%`.
- **La CI** sigue en serie.
- **Pendiente para la etapa 4:**
  - la decisión de la propietaria sobre si `--jobs` vale para publicar;
  - `--rapido`;
  - AGENTS.md.

  Si la memoria limita, la palanca que queda es liberar las ventanas entre archivos, descartada en el plan
  salvo que pasara justo esto: se propondrá como ficha aparte.
