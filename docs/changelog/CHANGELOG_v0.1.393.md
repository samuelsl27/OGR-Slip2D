# OGR Slip2D v0.1.393

**El ensamblado de la filtración guarda la geometría y la matriz saturada de cada elemento, una vez por
solucionador** (V14 de la fase 3 de la auditoría del cómputo, `docs/audits/AUDITORIA_COMPUTO_v0.1.377.md`).

**Lo medido**, con una corrida por proceso nuevo y en orden ABBA:
- **K16** (banco 05/015, consolidación 1-D transitoria, mallas de 600 y 2400 elementos): de 43,7 y 44,5 s a
  **29,4 y 31,4 s (−31 %)**. Un primer ABBA dio 58,2 y 47,2 s frente a 36,4 y 31,3: con la máquina cargada en
  ese momento, se repitió en orden inverso.
- **K15** (banco 05/004, presa permanente no saturada con dren de pie, 2400 y 9600 elementos): de 7,1 y 7,4 s a
  **5,7 y 5,9 s (−21 %)**.
- En los dos casos son idénticos todos los campos publicados (cargas, velocidades, gradientes, reacciones y
  contadores), con el mismo hash.

Clase B: la misma expresión sobre los mismos floats. Lo demuestra la huella de los 23 casos, 23 de 23 idénticos a
0.1.377.

## 0. Lo que se encontró

- **La puerta de medida.** En K16, `SeepageSolver.assemble` se llamaba 1600 veces y se llevaba 13,7 s de 46,4. Cada
  llamada volvía a calcular, para cada elemento, los gradientes de forma y el área, buscaba el tensor de
  conductividad de su material y formaba sus nueve entradas. De los 2 460 800 elementos ensamblados, **todos**
  tenían `kr` = 1: la columna de K16 está saturada. En K15, 11 724 iban sin `kr`, 233 911 con `kr` = 1 y 101 471
  con una `kr` fraccionaria.
- **Lo que se guarda, y por qué es el mismo número.**
  - Por solucionador: la geometría de cada elemento (gradientes y área) y las posiciones de sus tripletes.
  - Por elemento: su matriz con la conductividad saturada (`K0`), la primera vez que hace falta.
  - Un elemento sin `kr`, o con `kr` exactamente igual al float 1,0, toma `K0` tal cual, porque `x * 1.0` es `x`
    bit a bit. Todos los demás se forman con la misma expresión sobre la geometría guardada.
  - El tensor se lee una vez por material y llamada.
  - Las dos importaciones que `relative_permeability` y `suction_unit` hacían en cada llamada suben al módulo:
    2,46 millones de llamadas cada una en K16.
- **La validez de la caché es la del índice de `Mesh.locate` (V5):**
  - las listas de nodos y elementos se comparan por `is`, junto con sus longitudes;
  - la época de los scripts (`invalidate_mesh_indexes`);
  - **y, nuevo, `Mesh.forget_index()`.** La guía de `python_exec` pide a un script que edita una malla en el sitio
    y vuelve a usarla que llame a `forget_index()`. Sin este cambio, un script que reutilizara el mismo
    solucionador habría seguido ensamblando la geometría vieja aunque lo llamara.
  - Ahora `forget_index` mueve un contador propio de la malla (`_forgets`), que el solucionador compara.
    `__getstate__` lo deja fuera, como el índice, así que lo serializado tiene los mismos bytes. El programa no
    llama nunca a `forget_index`, así que en sus corridas el contador no existe.
- **Los caminos equivocados, todos en el código antes de publicarlo:**
  - **Comparar los tensores con `==`,** como hacía la primera versión, funde `0.0` con `-0.0`. Un material
    isótropo cuyo ángulo pasa de `0.0` a `-0.0` cambia solo el signo del cero de `kxy`: los tensores son iguales
    con `==`, y la `K0` formada con el otro cero se habría reutilizado. En un elemento girado en el otro sentido
    (determinante negativo), dos de sus nueve entradas cambian de `0.0` a `-0.0`; lo encontró una búsqueda sobre
    las seis orientaciones de un triángulo. Es la misma lección que los revisores pusieron como condición de V18.
    - **El arreglo:** se comparan los bits del tensor, y solo cuando sus tres componentes son floats de Python.
    - Cualquier otro tensor se forma en cada llamada, como siempre, y así tampoco cambia qué excepción sale ni
      dónde.
  - **El atajo de `kr` = 1 aceptaba cualquier cosa igual a 1,0.** Con un `numpy.float64(1.0)`, 0.1.392 daba
    entradas de numpy: los mismos valores, pero otro tipo. El atajo solo toma un float de Python.
  - **La primera versión formaba `K0` en el primer ensamblado aunque llevara una `kr` fraccionaria,** que es
    aritmética de más. Además, ante una conductividad editada entre llamadas, volvía a formar el elemento en todas
    las llamadas siguientes.
    - Ahora `K0` se forma la primera vez que un elemento la necesita, con el tensor de ese momento, y se guarda
      con él.
    - La matriz del primer ensamblado se aprovecha cuando ya es `K0` (sin `kr`, o con `kr` = 1,0).
- **Las condiciones del plan, cumplidas:**
  - la caché caduca con la geometría y se guarda por referencia (`is`), no por `id`;
  - se construye en la misma pasada que el bucle de siempre, y en su orden, así que una malla mala, un material
    malo o una `kr` corta lanzan lo mismo en el mismo sitio;
  - vive en el solucionador, nunca en un módulo.

## 1. Qué cambia

- `ogr_fem2d/solvers/seepage.py`:
  - **`_element_matrix`:** las nueve entradas de un T3, con la expresión y el orden de siempre;
  - **`_tensor_bits`:** los bits de un tensor de tres floats de Python, o `None`;
  - **`SeepageSolver.assemble`:** el camino con caché, con el tensor leído una vez por material y llamada;
  - **`_element_matrices`:** lo guardado, si sigue valiendo;
  - **`_assemble_and_keep`:** el bucle de siempre, que además guarda.
- `ogr_core/fem/mesh.py`: `Mesh.forget_index` cuenta sus llamadas (`_forgets`) y `Mesh.__getstate__` deja fuera la
  cuenta. El docstring de `invalidate_mesh_indexes` dice que también caduca lo que guarda un solucionador.
- `ogr_core/hydraulic/hydraulic_properties.py`: `_MODEL_FUNCS` y `SUCTION_UNIT` se importan con el módulo.
  `register_model` añade a `_MODEL_FUNCS` en el sitio, y nadie reasigna ninguno de los dos.
- `docs/mcp/herramientas.md`: la línea de `python_exec` dice que `forget_index()` también alcanza al solucionador.
- `tests/test_seepage_element_cache_v1393.py`, nuevo: 15 tests.
- El número, en los nueve sitios, y el contador de los dos README.

## 2. Qué se probó

- **`tests/test_seepage_element_cache_v1393.py`,** con el `assemble` de 0.1.392 copiado literal como referencia:
  - **el ensamblado es el de 0.1.392, bit a bit:** tripletes y lado derecho con `float.hex`, en la primera llamada
    y en las siguientes. Se prueba sin `kr`, con `kr` = 1, fraccionaria y mixta, con un material anisótropo, un
    elemento plano y cargas. También con una `kr` de numpy, donde coinciden además los tipos de las entradas;
  - **lo guardado no caduca sin verse:**
    - una conductividad editada en el sitio;
    - un elemento con otro material;
    - una malla nueva;
    - una malla editada por un script (la época se movió);
    - una malla editada y declarada con `forget_index`, con su control: sin `forget_index`, el ensamblado es el
      viejo, que es lo documentado;
    - un `kxy` de `0.0` a `-0.0`;
  - **la cuenta de `forget_index` no viaja:** los mismos bytes serializados, y ni la copia ni la copia profunda la
    llevan;
  - **las listas devueltas son del llamador:** cambiarlas no llega a la llamada siguiente;
  - **el trabajo, contado:**
    - la geometría, una vez por elemento y solucionador;
    - el tensor, una vez por material y llamada;
    - las matrices formadas: ninguna con `kr` = 1 una vez guardada, una por elemento con `kr` fraccionaria, y una
      por elemento editado, solo una vez;
  - **lo que lanza una entrada mala:** un elemento sobre un nodo que no existe y una `kr` corta, en la primera
    llamada y con caché.

  El archivo entero tarda 1 s, con el arranque del intérprete.
- **Trece mutantes,** todos cazados:
  - los tensores comparados con `==`;
  - el atajo de `kr` con cualquier cosa igual a 1,0;
  - sin la cuenta de `forget_index` en la comprobación;
  - sin la época;
  - `K0` reformada sin guardar;
  - `K0` tomada sea cual sea el tensor;
  - el primer ensamblado guardando como `K0` una matriz escalada por una `kr` fraccionaria;
  - los tripletes guardados entregados tal cual, filas y columnas (dos mutantes);
  - las filas de la primera llamada guardadas sin copiar;
  - `forget_index` sin contar;
  - la cuenta viajando con la copia;
  - `j` antes que `i`.

  Uno sobrevivió en la primera tanda: las filas guardadas, entregadas tal cual. El test solo cambiaba las listas de
  la primera llamada, que salen de otro camino. Ahora cambia también las de las llamadas servidas desde la caché.
- **Los tests de filtración, hidráulica, no saturado, transitorio, rescate, agua subterránea, malla y
  acoplamiento,** juntos: 450 de 450.
- **El banco:** la huella de los 23 casos frente a 0.1.377, 23 de 23 idénticos (`all identical`, código 0), ninguna
  corrida contaminada. En las corridas de identidad, frente a las de 0.1.392:
  - K16, de 45,9 a 29,8 s;
  - K15, de 6,8 a 5,2 s;
  - K18, de 6,8 a 7,0 s, que es ruido: su tiempo no está en el ensamblado.
- **La suite entera con `--jobs 4`:** **6885 de 6885, `Failed: 0`**, sin `Leaks` ni `Chunks died`, en 20 min.

## 3. Lo que queda

- **V15–V18,** cada una con su OK. La siguiente es V15: reutilizar el sistema ensamblado y eliminado del
  transitorio con la clave estricta.

## Archivos

- `ogr_fem2d/solvers/seepage.py`
- `ogr_core/fem/mesh.py`
- `ogr_core/hydraulic/hydraulic_properties.py`
- `docs/mcp/herramientas.md`
- `tests/test_seepage_element_cache_v1393.py` (nuevo)
- `docs/changelog/CHANGELOG_v0.1.393.md` (nuevo)
- `README.md`, `README.es.md`
- `pyproject.toml`, `ogr_gui/main_window.py` y los `__init__.py` de `ogr_core`, `ogr_slip2d`, `ogr_fem2d`,
  `ogr_gui`, `ogr_cli`, `ogr_api` y `ogr_mcp` (el número)
