# OGR Slip2D v0.1.397

**Los métodos de un Compute rebanan una sola vez la rejilla en serie** (V18, la última de la fase 3 de la auditoría
del cómputo, `docs/audits/AUDITORIA_COMPUTO_v0.1.377.md`).

**Lo medido**, en serie, con una corrida por proceso nuevo. El lado viejo vuelve a rebanar siempre, que es el
camino de 0.1.396:
- **K03** (caso 001 a 51 × 51 × 12, Bishop y Janbu Corregido), en orden BAAB: de 106,1 y 104,1 s a **79,9 y
  78,9 s (−25 %)**, con controles que difieren 1 s. Dos pares ABBA anteriores dieron −18 %, con controles que
  diferían 7–12 s;
- **K01** (caso 001 a 6 × 6 × 11, cuatro métodos): de 6,3 y 6,9 s a **4,9 y 5,1 s (−24 %)**. Un par anterior, con
  la copia lenta y la máquina más descargada, dio de 4,1 y 4,1 s a 3,4 y 3,3 s;
- **la memoria no sube:** el pico del proceso pasa de 130 a 122 MB en K01 y de 3682 a 3591 MB en K03.

El hash de todas las evaluaciones (factor, validez, dovelas y extremos), los contadores y las notas son idénticos en
todas las corridas.

Clase B: lo que da la misma función sobre la misma entrada. Lo demuestran la huella de los 23 casos y la de los
gemelos en serie de los 12 casos con pool, que son justo los que pasan por el reparto con varios métodos.

## 0. Lo que se encontró

- **La puerta de medida,** en serie:
  - **K01:** 4,2 s, cuatro métodos que rebanan 0,3–0,4 s cada uno las mismas 393 superficies;
  - **K03:** 112,3 s. Bishop rebana 32,7 s de 52,3 y Janbu 34,0 de 58,8, las mismas 32 053 superficies;
  - con la misma clave en todos los métodos (393 de 393, 32 053 de 32 053).
- **Las decisiones de la propietaria:**
  - **una copia por método,** y no el objeto `Slices` compartido;
  - **solo la rejilla:** en las búsquedas que se guían por su propio factor, cada método sigue un camino distinto.
- **Cómo queda:** `run_analysis` da a sus rejillas un `search.SliceShare`.
  - El primer método que rebana (el que manda) apunta, por cada superficie de prueba, cuatro cosas: el estado
    exacto que tenía antes de rebanar, una copia limpia de sus dovelas (tomada antes de que ningún método escriba en
    ellas), los motivos del rebanador y el estado completo de la superficie después.
  - Un método posterior que encuentra el mismo estado toma eso en lugar de rebanar. Su superficie queda como la
    habría dejado el rebanador, sus motivos son los del rebanador y sus dovelas son una copia suya.
  - El apunte se suelta en su último uso, y el último método se lleva la copia limpia misma.
  - Todo lo que viene después del rebanado corre en el código de cada método, sin tocar.
- **La clave** es todo el estado de la superficie menos su `id` (cada búsqueda construye sus círculos, cada uno con
  su `uuid4`), más el número de dovelas, escrito bit a bit y tipo a tipo:
  - los floats, por sus bytes, porque `0.0 == -0.0` fundiría dos superficies;
  - el tipo distingue 1 de 1.0 y 1 de `True`;
  - las tuplas y listas se escriben elemento a elemento: el muro de la grieta y cada grieta;
  - un atributo que sea un objeto deja la superficie sin clave, y se rebana como siempre. Lo mismo un estado
    posterior que no se pueda escribir exactamente.
- **Solo en serie.** Una búsqueda viaja entera en cada lote de un pool, y el `SliceShare` se serializa como `None`,
  así que cada trabajador rebana por su cuenta, como antes. «Rebanar una vez con pool» queda en el plan como
  candidato aparte, de riesgo alto.
- **Precondición:** el proyecto no cambia entre los métodos de un mismo Compute. La ventana lo garantiza con su
  diálogo modal de progreso.
- **Correcciones a lo que dije al plantear la decisión:**
  - `design_actions` escribe *dentro* de `slice_surface`, así que forma parte de lo apuntado;
  - el B-bar no escribe en las dovelas de la búsqueda: vuelve a rebanar sobre el nivel desembalsado y escribe en
    las suyas;
  - el que escribe después en las dovelas de la búsqueda es `detach_materials` (D381), que al acabar cada búsqueda
    cambia sus materiales por copias. Por él la copia limpia se toma al rebanar, y no al dársela al seguidor.
- **El estado posterior, en la rejilla, no cambia nada:** `_candidate_surfaces` entrega las masas ya resueltas y
  recortadas por la grieta, y el rebanador reconoce su propio trabajo. Restaurarlo hace falta en general (una
  superficie sin resolver sí cambia), y lo prueba un test unitario con círculos sin resolver.
- **El coste de la copia:**
  - con `copy.copy`, 124 µs por superficie, frente a 894 de rebanarla;
  - con `_shallow` (`__new__` más el diccionario, que es lo que `copy.copy` hace para estas clases sin su despacho
    genérico), 84 µs. Un test vigila que `Slice` y `Slices` no tengan `__slots__` ni ganchos de copia.
  - El estado de la superficie se copia lista a lista, sin `deepcopy`.

## 1. Qué cambia

- `ogr_slip2d/search.py`:
  - **`SliceShare`:** `slice`, que se serializa como `None`;
  - **`_exact` y `_state_key`:** la clave;
  - **`_shallow` y `_copy_slices`:** la copia;
  - **`_fresh`:** el estado con listas propias;
  - **`BaseSearch._slice_trial`:** la entrada al rebanador desde `_best_of_masses`;
  - **`GridSearch._run_centres`:** activa el reparto mientras evalúa sus centros (el `if True:` que ya envolvía el
    bucle pasa a ser un `try`).
- `ogr_slip2d/analysis_runner.py`: `run_analysis` crea el reparto cuando hay más de un método y se lo da a sus
  rejillas.
- `tests/test_slice_share_v1397.py`, nuevo: 9 tests.
- `AGENTS.md`: la tabla de «Coste de los tests», con las tres corridas de esta versión, y su historia.
- El número, en los nueve sitios, y el contador de los dos README.

## 2. Qué se probó

- **`tests/test_slice_share_v1397.py`,** sobre ACADS 1(b) (Giam y Donald 1989) con su grieta llena de agua, en una
  rejilla de 150 círculos en serie:
  - **cada método responde como si hubiera rebanado solo:** Bishop, Janbu Simplificado y el Ordinario, juntos y
    cada uno por su cuenta. Se comparan cada evaluación (factor, convergencia, validez, todo el estado de la
    superficie salvo su id y cada dovela), los contadores, las notas y la crítica, con `float.hex`;
  - **los métodos posteriores no rebanan:** el Compute de tres rebana lo que uno solo;
  - **sus dovelas son suyas:** ningún `Slices`, `Slice`, lista, material ni lista de grietas se comparte entre los
    resultados de dos métodos;
  - **la clave es exacta:** 0.0 y −0.0, 1 y 1.0, 1 y `True`, una grieta con cada cero, otro número de dovelas; un
    objeto, sin clave;
  - **`_shallow` es `copy.copy`,** y la guarda sobre `Slice` y `Slices`;
  - **un reparto se serializa como `None`;**
  - **el apunte se suelta en el último uso,** y los círculos sin resolver de los métodos posteriores quedan en el
    estado que dejó el rebanador, con sus listas propias;
  - **los motivos llegan a los métodos posteriores** (con un rebanador falso que rechaza);
  - **un estado posterior que no se puede escribir no se apunta.**

  El archivo tarda 1,0 s solo (`python tests/_runner.py test_slice_share_v1397`): los nueve tests comparten el
  Compute de tres métodos y los tres de un método, calculados una vez.
- **Trece mutantes,** todos cazados:
  - la clave por el valor del float;
  - los enteros y los booleanos con la misma clave;
  - la clave sin el número de dovelas;
  - el apunte que guarda las dovelas del que manda;
  - los seguidores compartiendo el apunte;
  - el estado no restaurado;
  - los motivos no restaurados;
  - los apuntes nunca soltados;
  - la rejilla sin reparto;
  - `run_analysis` sin reparto;
  - una copia que no copia;
  - las listas del estado compartidas;
  - cualquier estado apuntado.

  Tres sobrevivieron en la primera tanda: los enteros y los booleanos (el float ya llevaba su propia etiqueta), el
  estado (que en la rejilla no cambia) y los motivos (las superficies de ACADS no dejan ninguno). Cada uno tiene
  ahora su test.
- **Los tests de validación, casos publicados, superficies de usuario, m-alpha, desembalse, paralelo, rejilla y el
  censo de notas,** juntos: 509 de 509, incluidos los `test_slide_validation_*`, sin tocarlos.
- **El banco:**
  - la huella de los 23 casos frente a 0.1.377: 23 de 23 idénticos (`all identical`, código 0);
  - los gemelos en serie de los 12 casos con pool (`version_serie`), que son los que pasan por el reparto con
    varios métodos: 12 de 12 idénticos a los de 0.1.377, y en serie igual que en paralelo (`all identical`,
    código 0);
  - ninguna corrida contaminada.
- **La suite entera con `--jobs 4`:** 6926 de 6926 en 20,1 min, sin fugas ni tramos caídos.
- **`--fast --jobs 4`:** 6262 de 6262 en 9,8 min (`FILTERED RUN`: 37 archivos lentos fuera).
- **La serie entera:** 6926 de 6926 en 39,7 min, apuntada (`full serial run recorded`; con el commit de 0.1.396,
  porque corrió sobre el árbol de esta versión antes de su commit). Avisa de `test_points_table_v1371.py`, 93,9 s
  fuera de `tests/_slow.txt`.

## 3. Al terminar las 18 versiones

El plan pide, al terminar las 18 versiones, cronometrar otra vez los 23 casos frente a la tabla del informe, y
actualizar la tabla de «Coste de los tests» de AGENTS.md con una serie y una `--jobs 4` enteras.

**Los casos del banco**, con el tiempo interno de cada uno en la corrida de identidad (con su pool por defecto),
frente a la huella base de 0.1.377. Son corridas sueltas: el ruido de esta máquina es de varios segundos en los
casos largos.

| Caso | Qué mide | 0.1.377 | 0.1.397 | Cambio |
|---|---|---|---|---|
| K01 | rejilla 6×6×11, 4 métodos, en serie | 4,3 s | 3,5 s | −18 % |
| K01b | rejilla 7×7×11, 4 métodos, pool | 5,3 s | 2,9 s | −46 % |
| K02 | caso 001 tal cual, 4 métodos | 38,5 s | 31,7 s | −18 % |
| K03 | rejilla 51×51×12, Bishop y Janbu | 63,4 s | 52,8 s | −17 % |
| K04 | foco de tangente, 4 métodos | 2,7 s | 1,1 s | −58 % |
| K05 | Ru con sismo y foco de punto | 6,8 s | 6,8 s | +1 % |
| K06 | pilotes de Ito-Matsui | 28,0 s | 23,7 s | −16 % |
| K07 | desembalse en varias etapas | 81,7 s | 70,1 s | −14 % |
| K08 | rejilla de presiones | 29,5 s | 24,0 s | −19 % |
| K09 | bloque y Optimize | 32,3 s | 24,1 s | −25 % |
| K10 | no circular, Spencer y GLE | 94,5 s | 72,7 s | −23 % |
| K11 | no circular, paseos de Optimize | 115,5 s | 85,8 s | −26 % |
| K12 | no circular, Bishop | 9,1 s | 7,7 s | −15 % |
| K13 | Generalized Anisotropic | 63,9 s | 29,0 s | −55 % |
| K14 | los nueve métodos (reloj total; el registro no guarda el interno) | 1,7 s | 1,9 s | — |
| K15 | presa permanente no saturada | 12,3 s | 5,0 s | −59 % |
| K16 | consolidación transitoria | 62,9 s | 15,2 s | −76 % |
| K17 | presiones del MEF en la rejilla | 8,3 s | 0,9 s | −89 % |
| K18 | agua subterránea y factores por etapa | 18,8 s | 4,9 s | −74 % |
| K19 | Global Minimum | 15,7 s | 9,1 s | −42 % |
| K20 | Overall Slope y Global Minimum | 128,3 s | 93,5 s | −27 % |
| K21 | barrido del desembalse | 16,5 s | 12,2 s | −26 % |
| K22 | retroanálisis | 6,7 s | 5,5 s | −17 % |
| **Total** (sin K14) | | **845,0 s** | **582,5 s** | **−31 %** |

Las cifras de 0.1.377 son las de la huella de la fase 2 (`datos/orquesta-huella_*.jsonl`), en otra sesión de la
máquina; cada versión se midió además lado contra lado, y esas son las cifras de su changelog.

**La suite**, con las tres corridas de esta versión, una tras otra y sin otra medida en la máquina, frente a la
tabla que AGENTS.md traía de v0.1.375–0.1.376:

| Corrida | Antes | 0.1.397 | Cambio | Lo que el plan esperaba [H] |
|---|---|---|---|---|
| Entera, en serie | 68,6 min (6678 casos, v0.1.375) | 39,7 min (6926 casos) | −42 % | ~57–60 min |
| Entera, `--jobs 4` | 34,6 min (6708 casos, v0.1.376) | 20,1 min (6926 casos) | −42 % | ~27–29 min |
| `--fast --jobs 4` | 12,7 min (5971 casos, v0.1.376) | 9,8 min (6262 casos) | −23 % | ~12,5 min |

- **Con 218 a 291 casos más,** según la fila, bajó bastante más de lo que el plan esperaba.
- **Por qué el plan se quedó corto:** sumaba solo lo que podía atribuir a cada versión. A las del motor les ponía
  «parte» o «sin medir», y a `--fast` le daba cero porque las versiones de tests atacaban archivos lentos. Pero lo
  que el motor deja de rehacer lo deja de rehacer cada test que pasa por él, también los rápidos.
- **No se reparte entre versiones.** Ninguna se midió por separado en la suite, y el reloj total no es una medida:
  dos corridas iguales de v0.1.374 difirieron 3,7 min. Lo que sí resuelve es la magnitud, 29 min en la serie
  frente a ese ruido.
- **V18 sola no se ve en la suite:** la serie de 0.1.396 ya tardó 39,7 min. Pocos tests corren rejillas en serie
  con varios métodos.
- **La fila de la CI se queda como estaba,** porque no se ha medido: la CI no se vigila desde el 2026-10-29.

Con estas cifras se reescribe la tabla de AGENTS.md, y la frase de su historia añade el paso de 68,6 a 39,7.

## 4. Lo que queda

- **La prueba a mano en la ventana** (propietaria), la de V17 y la del final del plan: una búsqueda grande con
  varios métodos, Calcular y Cancelar a mitad de rejilla y durante la optimización, el *hover* y el guardado.
- **`test_points_table_v1371.py`** sigue fuera de `tests/_slow.txt` con 93,9 s en la serie de esta versión,
  pendiente de decisión: abaratarlo o reescribir la lista.
- **Lo que el plan dejó «para más adelante»,** solo con medida o decisión de la propietaria: rebanar una vez con
  pool, Overall Slope con un pool exterior, los paseos de Optimize en paralelo y la interfaz.

## Archivos

- `ogr_slip2d/search.py`, `ogr_slip2d/analysis_runner.py`
- `tests/test_slice_share_v1397.py` (nuevo)
- `docs/changelog/CHANGELOG_v0.1.397.md` (nuevo)
- `AGENTS.md` (la tabla de «Coste de los tests» y su historia)
- `README.md`, `README.es.md`
- `pyproject.toml`, `ogr_gui/main_window.py` y los `__init__.py` de `ogr_core`, `ogr_slip2d`, `ogr_fem2d`,
  `ogr_gui`, `ogr_cli`, `ogr_api` y `ogr_mcp` (el número)
