# OGR Slip2D v0.1.411

**Las copias limpias del `SliceShare` de una rejilla grande se guardan como registros: el pico de una corrida con
varios métodos baja de 2,8 a 0,83 GB en el caso de la prueba de la interfaz (D393).**

Ningún número se mueve: la huella de los 23 casos del banco de pruebas es idéntica a 0.1.377, con los valores por
defecto y con el volcado forzado.

## 0. Lo que se encontró

- **El `SliceShare` de V18** (0.1.397) hace que una rejilla en serie se rebane una sola vez para todos los métodos de
  un Calcular. El primer método (el líder) guarda, para cada superficie, una copia limpia de sus dovelas para los
  métodos siguientes. Esas copias crecían hasta cubrir la rejilla entera mientras corría el líder.
- **Lo destapó D383.** Con la población en disco (0.1.408–0.1.410), las copias pasaron a ser el pico de la corrida;
  antes las tapaban los 57 kB que retenía cada evaluación.
- **Fase 0, medida antes de escribir** (`_auditoria/P8_interfaz/d393_medir.py` en el banco, `d393_pico.log`).
  Sustituye `SliceShare.slice` por cuatro variantes, cada una en su proceso porque el pico de bytes privados no se
  reinicia, y las cuatro dan el mismo digest de `huella.fingerprint`:

  | Caso | Variante | Corrida | Retenido | Pico |
  |---|---|---|---|---|
  | K03 (001 a 31×31×12), 2 métodos | copias (0.1.410) | 39,6 s | 333 MB | 851 MB |
  | | sin `SliceShare` | 48,2 s | 112 MB | 112 MB |
  | | registros en memoria | 40,4 s | 122 MB | 125 MB |
  | | registros en disco | 39,7 s | 123 MB | 123 MB |
  | K03, 4 métodos | copias | 134,2 s | 515 MB | 1033 MB |
  | | sin `SliceShare` | 165,4 s | 295 MB | 295 MB |
  | | registros en memoria | 141,1 s | 306 MB | 309 MB |
  | | registros en disco | 139,2 s | 307 MB | 307 MB |
  | Caso de la prueba (51×51×12, 4 métodos) | copias | 498,9 s | 1389 MB | 2805 MB |
  | | sin `SliceShare` | 632,7 s | 797 MB | 797 MB |
  | | registros en memoria | 520,8 s | 825 MB | 828 MB |
  | | registros en disco | 521,5 s | 824 MB | 826 MB |

  - **Las copias triplicaban lo retenido** (333 frente a 112 MB), por fragmentación: se liberan intercaladas con
    los objetos que se quedan.
  - **Un registro ocupa 3,1 kB**, frente a ~44 kB de una copia. Escribirlo cuesta ~0,18 ms y leerlo ~0,24 ms,
    frente al milisegundo largo de rebanar.
  - **En memoria y en disco empatan:** los registros se sueltan antes de que la población que se va quedando los
    supere, así que nunca marcan el pico.
- **Camino equivocado.** La primera tanda en el caso de la prueba dio la variante de copias en 369,9 s y las de
  registros en ~520 s: parecía que perdían 150 s del ahorro de V18, cuando lo que cuestan los registros explica unos
  30. Con el tiempo del recolector cíclico medido (`gc.callbacks`: 1,7 s con registros y 5,7 s con copias, así que
  no era él) y el orden invertido, la variante de copias dio 498,9 s. La primera corrida fue la anómala: con
  TextInputHost girando en un núcleo, la máquina varió un 35 % entre corridas.
- **La trampa de los materiales.** `detach_materials` reasigna la tabla del almacén de la corrida al terminar cada
  método (`SliceStore.detach`). Si los registros del `SliceShare` fueran a ese almacén, los métodos siguientes
  recibirían las copias separadas en lugar de los materiales del proyecto. Los registros llevan su propia tabla.
- **Decidido por la propietaria (2026-11-02):** los registros en memoria (sin carpeta, sin archivo y sin ciclo de
  vida, con el mismo pico y el mismo tiempo que en disco) y el umbral de D383 (`SPILL_MIN_CIRCLES`, 2000
  superficies planeadas por el líder), independiente de que la corrida guarde su población. Por debajo, las copias
  de siempre.

## 1. Qué cambia

- **`ogr_slip2d/slice_store.py`:**
  - **`SliceRecords`:** `Slices` enteros como registros en memoria (pickle con la tabla de materiales y zlib 1,
    el formato de D383) con una tabla propia. Cada lectura es un grafo nuevo cuyos materiales son los que se
    escribieron.
  - El volcado con tabla (`_material_reduce`, `_dumps`) pasa a una base común, `_Table`, que comparten
    `SliceStore` y `SliceRecords`, sin cambiar lo que hace.
- **`ogr_slip2d/search.py` · `SliceShare`:**
  - el líder decide en su primera superficie: si `wants_store` (lo que planea llega al umbral), guarda registros
    (`serialized`); si no, copias, como hasta ahora;
  - cada método siguiente lee el suyo, también en el último uso, que suelta el registro como antes;
  - estado y motivos, sin cambios.
- **`tests/test_slice_share_records_v1411.py`**, nuevo: 5 tests.
- El número en los nueve sitios y el contador de los dos README.

## 2. Qué se probó

- **`tests/test_slice_share_records_v1411.py`.** Usa el modelo de `test_slice_share_v1397`: ACADS 1(b) con su grieta
  llena de agua, 150 círculos, con el umbral a 0 para que esta rejilla pequeña lo pase.
  - **cada método responde como si hubiera rebanado solo:** los tres en un Calcular frente a cada uno solo, con
    `float.hex`; y los siguientes no rebanan;
  - **lo que lee un método siguiente es suyo, con los materiales que se escribieron:**
    - un grafo nuevo en cada lectura, la última también;
    - los mismos números que las dovelas del líder;
    - los mismos objetos `Material` del proyecto;
    - el registro se suelta en el último uso;
  - **el `SliceShare` no sostiene dovelas entre métodos.** Con el recolector apagado, al empezar el segundo método:
    - sobre el umbral, sus registros no alcanzan ningún `Slice` y el proceso tiene menos `Slices` que superficies la
      rejilla;
    - bajo el umbral, copias (regla 7: el umbral mueve el número).
  - El archivo tarda 4 s con el arranque. Los 9 tests de V18 siguen en verde sin tocarlos.
- **Mutantes** (`scratchpad/mutantes_v411.py`): caen los siete:
  - el registro vuelve a guardar la copia;
  - el umbral se ignora, en los dos sentidos;
  - la lectura con materiales copiados;
  - el registro sin sus escalares;
  - nunca se suelta;
  - un mismo grafo para todos los lectores.
- **Contra el árbol de 0.1.410:** fallan los dos tests de los registros, por comportamiento (1428 `Slice`
  sostenidos, el registro no son bytes). Los tres de equivalencia y de copias pasan, como deben.
- **Vecinos** (el almacén, el `SliceShare`, el paralelo y el pool compartido, el retroanálisis, el desembalse, la
  estadística, `run_analysis`, las rejillas, liberar resultados, el `.h5`, la validación ACADS): 613/613.
- **La huella del banco de pruebas** (`_auditoria/COMPUTO/bench`, `datos/v0.1.411_huella.log`): 23/23 idéntica a
  0.1.377 en las cuatro pasadas, con los valores por defecto y con el volcado forzado (`OGR_VOLCADO_FORZADO=1`, que
  pone el umbral a 0 y lleva al camino nuevo a todos los casos con varios métodos en serie), en paralelo y en serie.
  El manifiesto de entradas solo trae el cambio aceptado de D388.
- **El ahorro de V18** (`_auditoria/P8_interfaz/d393_ab.py`, `d393_ab.log`). Es un A/B en el mismo proceso sobre
  K03 a 31×31×12, en el orden registros, copias, sin `SliceShare`, registros. Todas las corridas dan los mismos
  factores, con todos sus dígitos.
  - **Con 4 métodos:**
    - registros 194,9 y 201,0 s (los dos controles difieren 6,1 s);
    - copias 190,8 s;
    - sin `SliceShare` 236,3 s.

    V18 ahorra un 19 % con copias y un 15–17 % con registros, así que conserva entre tres cuartos y nueve décimas
    de su ahorro.
  - **Con 2 métodos, no concluye** en dos intentos: los controles difieren en 10,9 s en el primero y en 12–16 s en el
    segundo, que repite cada variante y calienta antes el proceso. TextInputHost giraba en un núcleo (4,4 s de CPU
    en 5 s), y la máquina se fue acelerando dentro del mismo proceso. Las parejas contiguas dan +3,2 y +6,7 s a los
    registros sobre ~40–50 s.
  - **Por eso manda la cuenta del trabajo añadido** (`d393_trabajo.py`, `d393_reparto.py`), en caliente y por
    superficie:
    - una copia, 0,08 ms;
    - escribir un registro, 0,20 ms (pickle 0,11 y zlib 0,05);
    - leerlo, 0,25 ms (zlib 0,02 y deshacer el pickle 0,19);
    - rebanar de nuevo, ~1 ms (sin `SliceShare` menos copias, entre las ~11 500 superficies).

    Con 2 métodos los registros añaden como mucho 0,38 ms por superficie, ~4,4 s en K03: V18 conserva al menos
    tres quintos de su ahorro. Las corridas en procesos separados de la fase 0 dan nueve décimas (40,4 s frente a
    39,6 con copias y 48,2 sin `SliceShare`). La cuenta es una cota superior porque no incluye lo que las copias
    hacen trabajar al recolector: en el caso de la prueba fueron 5,7 s con copias y 1,7 con registros. Con
    4 métodos, la cota es 0,74 ms por superficie, ~8,5 s, que encaja con lo medido.
  - **Quitar zlib no compensa:** ahorraría 0,07 ms por superficie a cambio de registros 2,6 veces más grandes
    (8,2 frente a 3,15 kB). Casi todo el coste de leer un registro es crear los objetos, y eso no se puede evitar.
- **La suite entera con `--jobs 4`:** 7002/7002, sin fugas ni tramos muertos, en 28,6 min con TextInputHost girando
  en un núcleo.

## 3. El banco y el cierre de D393

- **`d393()`** en `_tools/verificar_cierres.py`. Mide con `tracemalloc` ACADS 1(a) (caso de validación 001) a
  8×8×6, con Bishop y Janbu corregido, en serie y con el umbral a 0. Hace la misma corrida con el `SliceShare` y con
  cada método rebanando por su cuenta.
  - **Pide:**
    - menos de 10 kB de pico de más por superficie del primer método;
    - lo retenido a menos de un 25 % de lo de sin él;
    - ningún `Slice` sostenido por los registros al empezar el segundo método;
    - el test.
  - **Con 0.1.411:** CUBIERTO POR TEST, con 2,5 kB de más por superficie (493), 4995 frente a 4910 kB retenidos y
    0 `Slice` en 578 registros.
  - **Con el árbol de 0.1.410:** SIGUE ABIERTO, con 99,4 kB de más por superficie y 15 028 `Slice` sostenidos.
    Fallan las tres condiciones.
- **La comprobación del pico es por superficie y no total,** para que no dependa de la rejilla. Las copias de
  0.1.410 suben el pico 40 veces más que los registros.

## Archivos

- `ogr_slip2d/slice_store.py`, `ogr_slip2d/search.py`
- `tests/test_slice_share_records_v1411.py` (nuevo)
- `docs/changelog/CHANGELOG_v0.1.411.md` (nuevo)
- `README.md`, `README.es.md`
- `pyproject.toml` y los `__init__.py` de `ogr_core`, `ogr_slip2d`, `ogr_fem2d`, `ogr_gui`, `ogr_cli`, `ogr_api` y
  `ogr_mcp` (el número; `ogr_gui/main_window.py` también lo lleva)
