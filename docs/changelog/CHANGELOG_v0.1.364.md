# OGR Slip2D v0.1.364

**Un campo de filtración guardado conserva los códigos de sus notas, y *Interpretar agua subterránea* las
dice en castellano también después de abrir el archivo (D342, cerrada).** Segunda versión de la tanda
P8l.

## 0. Lo que se encontró

- **Medido en 0.1.352 y repetido aquí:**
  - desde esa versión las notas del solver llevan código (`ogr_fem2d/messages.py`);
  - `SeepageResult.to_dict` las escribía como su frase inglesa y `from_dict` las leía como `str`, sin
    código;
  - una nota `seepage.stage_steps` con `k = 1`, después de `to_dict` → JSON → `from_dict`, volvía como
    `str` y en castellano salía en inglés.

  No es una regresión: antes de 0.1.352 salían en inglés siempre.
- **Con el código solo no bastaba: faltaba deshacer `json_args`.** Un valor no finito se guarda como su
  `repr` (`"nan"`, `"inf"`), porque JSON no tiene número para él. Si se lee de vuelta como cadena, la
  plantilla (`{change:.3e}`) no le da formato y `render` cae a la frase inglesa. Por eso
  `args_from_json` (`ogr_core/messages.py`) deshace exactamente lo que `json_args` cambia. Una tupla vuelve
  como lista, que se formatea igual.
- **Las huellas del banco, medidas antes de elegir el formato** (paso 4 de la ficha):
  - `model_hash` hashea `to_dict` y la `modelo_huella` del banco hashea el `.ogr` entero, con los
    resultados;
  - de 22 844 `.ogr` del banco, 183 guardan un campo y **ninguno** tiene notas de las que llevan código
    (`error`, `warning`, `mesh_warning`, `initial_state_warning`, `fos_warning`);
  - como la clave nueva solo se escribe cuando alguna nota lleva código, ninguna huella cambia, y tampoco
    la regeneración de resultados (D78).
- **Dónde más se guardan notas** (paso 3 de la ficha, reportado y sin arreglar aquí):
  - los resultados del transitorio (`transient_results`, `transient_initial_result`) usan el mismo
    `to_dict`, así que este cambio los cubre;
  - los resultados de Calcular no van al `.ogr`. El primer método va al `.h5`, que guarda `error` y
    `reason` en inglés sin código, y solo se relee como metadato (`load_summary`);
  - la estadística, el retroanálisis, el barrido y la optimización no se guardan;
  - en el API, el `summary.json` de agua y de estadística escribe las frases sin código. Los resultados
    completos de un trabajo viajan por *pickle* y lo conservan.

## 1. Qué cambia

- **`ogr_core/fem/seepage_data.py`:**
  - `to_dict` añade `"note_codes": {clave: {"code", "args"}}` **solo si alguna nota lleva código**. La
    frase sigue en `notes`, igual que antes, y `SCHEMA` no cambia;
  - `from_dict` reconstruye `Coded(frase, código, valores)` de cada nota que lo tenga;
  - una clave de `note_codes` sin nota en `notes` se ignora.
- **`ogr_core/messages.py`:** `args_from_json`, el inverso de `json_args` para lo que este cambia.
- **Compatibilidad, medida con los dos árboles:**
  - un `.ogr` escrito por esta versión, abierto con 0.1.363, da las mismas tres frases como `str` y el
    campo entero (58 nodos): la versión anterior lee sin mirar la clave nueva;
  - un `.ogr` sin la clave se lee como siempre.
- **Ningún número cambia, ni la frase inglesa en el archivo ni en el API.**

## 2. Tests

- **`tests/test_seepage_note_codes_v1364.py`** (nuevo, 10 casos):
  - la reproducción de la ficha vuelve como `Coded` con su código y sus valores;
  - la frase inglesa del archivo es la de antes, y es `str` en el JSON;
  - una razón anidada (`initial_failed_why`) y un valor NaN vuelven y se dicen en castellano;
  - `args_from_json` deshace `json_args`;
  - un campo sin notas con código no escribe la clave nueva, un diccionario sin ella se lee como siempre,
    y un código sin su nota se ignora;
  - las etapas del transitorio y su estado inicial, por `Project.to_dict`/`from_dict`;
  - **por `Project.save`/`load` y `InterpretGroundwaterWindow._summary`**, las notas en castellano
    después de abrir el archivo.

**Con el código de 0.1.363 fallan 7.** Los otros 3 son los invariantes de lo que no cambia y pasan en
los dos árboles, como deben.

## 3. Verificación

- **El test de esta versión:** 10/10.
- **Los vecinos:** 256/256 en 16 archivos: serialización del campo, historia de Picard, notas de
  filtración, estado inicial del transitorio, el transitorio, las operaciones de agua del API, los
  resultados desfasados, las capas del núcleo, los catálogos de mensajes, el PDF en castellano y la
  ventana de agua subterránea.
- **Suite entera:** 6568/6568, `EXIT=0`, 93 min.
- **Banco:**
  - raíz: `verificar_cierres.py` entero, 98 comprobaciones (una más, `d342`), 0 bajadas.
    - D342 queda **CUBIERTO POR TEST**: la ida y vuelta de la ficha devuelve un `Coded` con su código, y
      un campo resuelto de verdad, por `Project.save`/`load`, sale en castellano en el resumen;
  - manual 02: `verificar_cierres.py --seco`, 238 veredictos iguales a los archivados;
  - **D342 retirada** al índice de cerrados, podada de `PAQUETES` y tachada en la cadena de P8;
  - instantáneas `Evaluaciones/0.1.364` (raíz 979 archivos, 02 3284), prompts (42) y auditorías con
    0 ERROR.

## 4. Pendiente

- La tanda sigue con D348 (0.1.365): la estadística, el agua subterránea, el retroanálisis y la
  optimización, fuera del hilo de la ventana.
