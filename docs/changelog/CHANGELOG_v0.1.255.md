# OGR Slip2D v0.1.255

**D128: el test de Global Minimum vigila por fin la superficie de cada
método, y la ventana de estadísticas la enseña.** Hasta 0.1.254,
`test_each_method_keeps_its_own_surface` no comprobaba lo que su nombre
promete, y `MethodProbabilisticResult.surface` no lo leía nadie fuera de los
tests.

Sexta versión de la tanda Help + D85, D251/D252, D253, D97, D128 y D131. La
propietaria decidió (2026-10-03) que la superficie se enseñe.

## 0. Lo que se encontró

- **El test era verde y no vigilaba nada.** Corría Global Minimum con Bishop
  y Spencer y solo comprobaba que la superficie no fuera None y que el
  factor determinista se hubiera copiado. Pasaba con una compuesta degradada
  a círculo (D59) y pasaría si los dos métodos se muestrearan sobre el mismo
  círculo. Además corría en una rejilla de 4 × 4 donde Bishop y Spencer
  eligen **el mismo círculo**, así que no había nada que distinguir.
- **Medido al planificar:** con una rejilla de 6 × 6 × 8 se separan.
  - Bishop elige (90; 76,67; R 53,44).
  - Spencer elige (80; 60; R 35,12).
- **La comprobación nueva falla cuando debe, y la vieja no.** Medido en vivo
  con `d128()`: con la semilla de Bishop para los dos métodos y la sonda de
  D88 apagada, Spencer se muestrea sobre el círculo de Bishop. La
  comprobación vieja da por buena la corrida, y la nueva ve que las 30
  evaluaciones de Spencer van sobre otra superficie. Con solo la semilla
  saboteada, la sonda de D88 ya rechaza a Spencer.
- **La superficie no la leía nadie.** El motor la escribe desde 0.1.35, pero
  la ventana decía qué daban las muestras y nunca sobre qué superficie.
- **Los avisos de cambio de masa (D89) y de caso de capa débil (D85)** salían
  bajo «Lo que esta corrida no pudo hacer:», aunque no son algo que no se
  pudo hacer: son algo que la corrida hizo.
- **Un supuesto mío corregido en el test:** el talud con muesca de v1154 da
  una superficie **compuesta**, no un círculo. El caso de la clave lo
  comprueba ahora contra el tipo que trae el propio diccionario.

## 1. Los cambios

- **Motor** (`ogr_core/statistics/`):
  - `summary()["surface_key"]`: la identidad de la superficie muestreada
    (`_surface_key`, tipo y geometría al último dígito, extremos incluidos).
    Es None en Overall Slope, donde cada muestra busca de nuevo.
  - `switch_lines`, en `ProbabilisticResult` y en `SensitivityResult`: las
    líneas de cambio de masa o de caso. Siguen también en `note_lines`, donde
    las leen el panel de notas, la API y el banco (v1238 lo fija).
- **Ventana de estadísticas:**
  - en Global Minimum, una línea con la superficie muestreada, escrita por
    un formateador nuevo, `surface_text(sd, project)`:
    - el círculo por su centro y su radio;
    - la compuesta por el círculo del que se recortó;
    - la poligonal por sus vértices;
    - la de capa débil por sus capas, nombradas por su material, y por su
      base;
    - todas con los extremos de la masa.

    No se reutiliza `minimum_row_text`, que numera filas de una tabla.
  - los avisos de cambio salen del rótulo «Lo que esta corrida no pudo
    hacer:» y pasan a uno propio, «Muestras que contestaron por otro
    mecanismo:», sin rojo. La ventana pregunta la separación al motor y no
    analiza ninguna frase.
  - Con una corrida sana, la ventana es la de siempre.
  - Textos con `tr()` y su entrada en español.
- **API:** el resumen de `statistics_run` trae `switch_lines`, y cada método
  su `surface_key`. La fila de la guía del MCP lo dice.

## 2. Tests

- **`test_each_method_keeps_its_own_surface`, reescrito**, con cabecera de
  invariante (D59 y D128):
  - un determinista propio en la rejilla de 6 × 6 × 8 (`_deterministic` gana
    un parámetro `grid`; los otros siete tests siguen en 4 × 4);
  - registra la superficie de cada evaluación espiando `_evaluate_on`, y lo
    restaura en `finally`;
  - exige como premisas claves deterministas distintas y ningún cambio de
    masa;
  - y que cada evaluación de cada método sea de su propia superficie, con
    la misma clave en `summary()`.
- **`test_a_shared_seed_is_denounced`:** la comprobación falla con la
  semilla de Bishop para los dos métodos, de las dos maneras (Spencer
  rechazado por la sonda, y Spencer muestreado sobre otro círculo).
- **Nuevo `tests/test_statistics_surface_line_v1255.py`**, 12 casos:
  - el texto de cada tipo de superficie;
  - la clave en el resumen;
  - la línea solo en Global Minimum;
  - el título propio de los cambios, en Global Minimum y en la
    sensibilidad;
  - una corrida sana sin ninguna de las dos etiquetas;
  - la traducción.

**Discriminación** contra un `git archive` de d733d38 (0.1.254), con el
envoltorio sin buscador editable: de los 14 casos nuevos o reescritos
**fallan 13**. Pasa, a propósito, el control de Overall Slope: allí nunca
hubo línea de superficie. Los 16 casos de v135 que no cambian pasan.
Los dos de v135 fallan por `KeyError: 'surface_key'`, es decir, por
símbolo. Lo que demuestra que la comprobación falla ante el defecto es
la meta-prueba, y `d128()` lo mide en vivo.

## 3. El banco

- **Sin dígitos que mover**, así que no hay A/B ni re-corrida del lote
  probabilístico: el motor solo añade una clave al resumen y una lista
  paralela de líneas. Si algún día se re-corre el lote, `surface_key` es una
  cadena, y los cierres de D88 y D89 solo comparan hojas numéricas
  (`_numeros_d89`).
- **`d128()`:**
  - por el AST del test instalado: compara `_surface_key` de cada
    evaluación y tiene su meta-prueba;
  - en vivo, sobre Ej_1 en la rejilla de 6 × 6 × 8: cada método se muestrea
    sobre su superficie. Con la semilla de Bishop para los dos y la sonda
    apagada, la comprobación vieja da por buena la corrida, y 30 de 30
    evaluaciones de Spencer son de otra superficie;
  - y la discriminación archivada.

  Veredicto CUBIERTO POR TEST. Con 0.1.254 da NO SE SOSTIENE (el motor no
  tiene `surface_key`).
- **Verificación entera:** 225 cierres y 0 bajadas.
- **Cierre del ciclo:**
  - instantánea 0.1.255;
  - D128 retirada (219 cerradas). La nota de cierre no llegó a la ficha por
    una errata en la edición, y se añadió a la sección archivada en
    `Evaluaciones/0.1.255/`;
  - `PAQUETES` de P5 podado y la cadena tachada;
  - prompts regenerados;
  - auditorías del 02 y de la raíz con 0 ERROR;
  - instantánea con `--forzar`;
  - `--seco` completo tras retirar: 225 claves, iguales al JSON clave a clave.

## 4. Verificación

- **Suite entera:** 5590 de 5590.
- **Selección** de probabilística, estadística, sensibilidad, cambios de
  masa, pérdidas parciales, API, MCP, i18n, menús y reconstrucción de
  superficies: 475 de 475 (27 archivos).

**Qué falta por probar:**
- **En pantalla:** la ventana de estadísticas de un Global Minimum real con
  dos métodos en superficies distintas, y una corrida con cambios de masa.
