# OGR Slip2D v0.1.394

**Un paso del transitorio guarda el sistema eliminado mientras se repite** (V15 de la fase 3 de la auditoría del
cómputo, `docs/audits/AUDITORIA_COMPUTO_v0.1.377.md`).

**Lo medido** en K16 (banco 05/015, consolidación 1-D transitoria, mallas de 600 y 2400 elementos), con una corrida
por proceso nuevo:
- en orden ABBA, de 35,6 y 34,4 s a **16,2 y 18,9 s**;
- en orden BAAB, de 34,3 y 30,6 s a **17,3 y 16,3 s**.

Es un **−49 a −50 %**, con el mismo hash de todos los campos publicados (cargas, presiones, velocidades,
gradientes, reacciones, `kr` y contadores) en las ocho corridas. El lado viejo es 0.1.393, que en el A/B de V14
medía 29,4 y 31,4 s: la máquina va hoy más lenta, y por eso se mide lado contra lado. K15 (presa permanente) no
tiene transitorio y no cambia.

Clase B: la misma función sobre las mismas entradas. Lo demuestra la huella de los 23 casos, 23 de 23 idénticos a
0.1.377.

## 0. Lo que se encontró

- **La puerta de medida, tras V14.** K16 tardaba 29,8 s, y 22,3 de ellos dentro de `_solve_linear_step`, que se
  llamaba 1600 veces:
  - **construir la matriz dispersa** (`_csr`, desde los tripletes): **7,1 s, más que resolverla** (`spsolve`,
    3,4 s);
  - `assemble`: 1,5 s (tras V14);
  - los bucles de Python (las dos pasadas de la eliminación de las cargas fijas sobre todos los tripletes, las
    copias y las reacciones): unos 9,9 s;
  - fuera del paso lineal: `_element_kr` 3,7 s, la masa concentrada 1,15 s (840 veces) y las propiedades nodales
    0,31 s.
- **1590 de los 1600 sistemas eran el anterior,** bit a bit. En una columna saturada solo se mueve el lado derecho:
  `kr` vale 1, la diagonal de almacenamiento solo cambia con `dt`, y los nodos fijos son siempre los mismos. El plan
  esperaba ~98,7 % de aciertos.
- **Más de lo que preveía el plan** (de −5 a −10 % en K16). Su cifra se hizo en 0.1.377 sin separar la construcción
  de la matriz de su resolución, y sin contar las dos pasadas de la eliminación.
- **La clave: lo ensamblado, no las entradas.** El plan proponía como clave `kr`, la diagonal, el conjunto activo y
  las condiciones, más la malla y la correspondencia elemento–material. Esa clave no vería un material editado en
  el sitio: la correspondencia sigue igual, y lo que cambia son sus propiedades.
  - Lo que se elimina es función pura de los tripletes ensamblados (con la diagonal) y de qué nodos están fijos, y
    en qué orden. La clave es exactamente eso: los bits y los tipos de `vals`, `rows` y `cols`, la tupla de nodos
    fijos, `n` y la `_csr` del módulo.
  - Así cualquier cosa que mueva lo ensamblado obliga a reconstruir: la malla, un material, `kr`, `dt`.
  - Los valores de las cargas fijas no entran en la clave: solo llegan al lado derecho, que se calcula en cada
    llamada.
- **Lo que se sigue haciendo en cada llamada,** con las mismas operaciones y en el mismo orden:
  - el ensamblado;
  - el lado derecho: las restas de la eliminación, en el orden de los tripletes, y luego las cargas fijas;
  - `spsolve`;
  - las reacciones, con los tripletes guardados, que son los mismos bit a bit.
- **Estricta en bits y en tipos, que son las lecciones de V14.**
  - `==` funde `0.0` y `-0.0`: se comparan los bits.
  - `struct` (igual que `array('d')`, que es lo que señalaron los revisores) acepta un número de numpy como el
    mismo double. Un sistema con números de numpy da reacciones de numpy, así que no se guarda: solo se guarda un
    sistema de floats de Python, y eso se comprueba con `set(map(type, …))`.
  - El orden de las comprobaciones: primero `==`, que cuesta 0,02 ms y resuelve casi todos los fallos; los bits y
    los tipos, unos 0,9 ms, solo cuando lo demás coincide.
- **Las condiciones del plan, cumplidas:**
  - **`_reuse_ok` cubre `_linear_solve`:** si una subclase o un test lo redefine, en la clase o en la instancia, no
    se guarda nada, y se le llama en cada resolución con listas propias.
  - **Un fallo al construir la CSC no cuenta como acierto:** se vuelve a intentar en cada llamada, como hasta ahora,
    hasta el último respaldo (eliminación gaussiana).
  - La caché vive en el solucionador, nunca en un módulo.
- **`spsolve` llama a `A.sum_duplicates()` sobre la matriz que recibe.** Tras `tocsc()` la matriz ya está en forma
  canónica, así que no hace nada, y la segunda llamada encuentra lo mismo que la primera. Lo fija un test con la
  SciPy instalada (1.18): los datos de la matriz no cambian, y la solución es la de una matriz recién construida. La
  CI usa otras versiones, y el test lo comprobará en cada una.
- **La masa concentrada se guarda con la validez de V14,** y se entrega como una lista nueva. La regla de validez
  de la malla (las listas por `is`, las longitudes, la época de los scripts y `forget_index`) pasa a un ayudante
  compartido, `_mesh_stamp`, en lugar de copiarse.
- **Las propiedades nodales no se guardan:** comprobar que la correspondencia elemento–material no ha cambiado
  cuesta lo mismo que calcularlas (0,31 s en K16).
- **Fuera de V15:**
  - `_element_kr` (3,7 s): vectorizarlo es de clase D, fuera de este plan;
  - el bucle de las reacciones: hacerlo con numpy cambiaría el orden de las sumas, y es de clase C.

## 1. Qué cambia

- `ogr_fem2d/solvers/seepage.py`:
  - **`_EliminatedSystem`:** la eliminación de un sistema ensamblado (tripletes copiados, restas al lado derecho
    en orden, tripletes reducidos, matriz CSC) y `repeats`, la clave estricta;
  - **`_float_bits`:** los bits de una lista de floats de Python, o `None`;
  - **`_reuse_ok`:** `_linear_solve` es el de `SeepageSolver`;
  - **`SeepageSolver._linear_solve_from(csc, …)`:** los pasos de `_linear_solve`, con la matriz ya construida o
    construyéndola, y devolviendo la que usó. `_linear_solve` lo llama con `None`;
  - **`TransientSeepageSolver._solve_linear_step`:** toma el sistema guardado si se repite;
  - **`TransientSeepageSolver._lumped_mass`:** guardada por solucionador;
  - **`_mesh_stamp` y `_stamp_fits`:** la regla de validez de V14, compartida.
- `tests/test_transient_system_reuse_v1394.py`, nuevo: 15 tests.
- El número, en los nueve sitios, y el contador de los dos README.

## 2. Qué se probó

- **`tests/test_transient_system_reuse_v1394.py`,** con `_solve_linear_step`, `_linear_solve` y `_lumped_mass` de
  0.1.393 copiados literalmente como referencia:
  - **cada resolución es la de 0.1.393, bit a bit:** cargas, presiones y reacciones (también sus tipos), a lo largo
    de una secuencia que:
    - repite el sistema;
    - cambia solo el lado derecho o una carga fija;
    - cambia `dt`, `kr`, los nodos fijos o su orden;
    - pasa a no llevar `kr`;

    contando con `_csr` cuándo se construye. Y en casos sueltos:
    - los mismos valores de la diagonal en otros nodos;
    - una conductividad editada;
    - un cero que cambia de signo;
    - una diagonal de números de numpy;
    - dos transitorios enteros, uno saturado (que repite su sistema) y otro con zona no saturada;
  - **la clave es estricta, y un fallo no es un acierto:**
    - un `_csr` que lanza se intenta en cada resolución;
    - también cuando falla además la resolución densa y resuelve la eliminación gaussiana;
    - un `_csr` sustituido entre dos resoluciones es el que se usa;
  - **un `_linear_solve` redefinido** (en la instancia y en una subclase) se llama en cada resolución, con listas
    propias;
  - **`spsolve` deja la matriz como la recibió;**
  - **la masa:** la de 0.1.393, una vez por malla, como lista nueva, y caduca con la geometría (nodo movido con
    `forget_index`, época, malla nueva), con su control;
  - **un nodo fijo fuera de la malla** lanza lo mismo, en la primera llamada y con un sistema guardado.

  El archivo entero tarda 1,3 s, con el arranque del intérprete.
- **Catorce mutantes,** todos cazados:
  - la clave sin los bits;
  - con el conjunto de nodos fijos en vez de su orden;
  - sin `_csr`;
  - sin `rows` y `cols`;
  - los bits sin la comprobación de tipos;
  - las restas al lado derecho en orden inverso;
  - un `_linear_solve` redefinido saltado;
  - un fallo de construcción guardado como acierto, en el respaldo denso y en el gaussiano (dos mutantes);
  - la masa entregada como la lista guardada;
  - la masa sin la marca de la malla;
  - la marca sin `forget_index`;
  - la marca sin la época;
  - un sistema con números de numpy guardado.

  Uno sobrevivió en la primera tanda: el del respaldo gaussiano, al que ningún test llegaba. El test añadido llega
  con un `_np` sustituido en el módulo, cuya resolución densa falla.
- **Los tests de filtración, hidráulica, no saturado, transitorio, rescate, agua subterránea, malla, acoplamiento y
  desembalse,** juntos: 620 de 620.
- **El banco:** la huella de los 23 casos frente a 0.1.377, 23 de 23 idénticos (`all identical`, código 0), ninguna
  corrida contaminada. En las corridas de identidad, frente a las de 0.1.393:
  - K16, de 29,8 a 16,6 s;
  - K18, de 7,0 a 6,3 s;
  - K15, igual (5,2 s).

  El contador que pedía el plan, en K16: 10 sistemas construidos (y 10 matrices CSR) para 1600 resoluciones,
  así que 1590 aciertos. La masa se suma una vez por malla.
- **La suite entera con `--jobs 4`:** **6900 de 6900, `Failed: 0`**, sin `Leaks` ni `Chunks died`, en 20 min.

## 3. Lo que queda

- **V16–V18,** cada una con su OK. La siguiente es V16: los materiales de la etapa 2 del desembalse, por prototipo.

## Archivos

- `ogr_fem2d/solvers/seepage.py`
- `tests/test_transient_system_reuse_v1394.py` (nuevo)
- `docs/changelog/CHANGELOG_v0.1.394.md` (nuevo)
- `README.md`, `README.es.md`
- `pyproject.toml`, `ogr_gui/main_window.py` y los `__init__.py` de `ogr_core`, `ogr_slip2d`, `ogr_fem2d`,
  `ogr_gui`, `ogr_cli`, `ogr_api` y `ogr_mcp` (el número)
