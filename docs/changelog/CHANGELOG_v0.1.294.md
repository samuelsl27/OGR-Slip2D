# OGR Slip2D v0.1.294

**Toda entrada de menú desactivada dice por qué en la barra de estado
(D289b).** D289 (0.1.288) se lo dio a las entradas del agua. En un proyecto
nuevo quedaban nueve entradas desactivadas sin motivo visible.

## 0. Lo que se encontró

- **La segunda prueba de la interfaz**
  (`_auditoria/P8_interfaz/INFORME_prueba_GUI_0.1.290.md`, H5) vio que *Drawdown
  Level Sweep…* estaba en gris y, al pasar el puntero, la barra conservaba el
  motivo de la entrada anterior.
- **Medido en un proyecto nuevo,** recorriendo todas las acciones:
  - *Add Drawdown Line*, *Drawdown Level Sweep* y los cuatro objetos de *Block
    Search* llevaban el motivo solo como ayuda emergente, que ningún menú
    enseña. Dos de ellas, además, fuera de `tr()`;
  - *Random Variables*, *Compute Statistics* y *Show Statistics* no tenían
    ningún motivo.
- **Por qué hace falta el texto de estado.** Con los estilos Fusion y windows11,
  Qt no activa una entrada desactivada (D289). Solo `DisabledReasonFilter`, que
  lee el texto de estado, puede decir algo.

## 1. Qué cambia

- **Las nueve llevan su motivo como texto de estado traducido,** y lo quitan al
  activarse:
  - *Add Drawdown Line* y *Drawdown Level Sweep*: «… only available when Project
    Settings > Groundwater > Advanced > Rapid Drawdown is enabled.». Antes, en
    tres líneas y sin `tr()`;
  - *Add Drawdown Line* con una línea ya dibujada: «Only one Drawdown Line is
    allowed.»;
  - los objetos de *Block Search*: el motivo que ya tenían en la ayuda;
  - *Random Variables* y *Compute Statistics* sin análisis activado: «Needs a
    probabilistic or sensitivity analysis: enable one in Project Settings >
    Statistics.»;
  - *Compute Statistics* sin variables: «Needs random variables: Statistics >
    Random Variables.»;
  - *Show Statistics* sin resultado: «Needs a statistics result: compute the
    statistics first.»
- **5 claves nuevas** con su castellano.

## 2. Tests

`tests/test_disabled_reasons_v1294.py`, 3 casos:
- en un proyecto nuevo, toda acción desactivada que está en la barra de menús
  tiene texto de estado;
- con el desembalse rápido activado, las dos entradas del desembalse se activan
  y no lo llevan;
- con un análisis probabilista y sin variables, *Random Variables* se activa sin
  motivo y *Compute Statistics* dice que necesita variables.

Con el código de 0.1.293 fallan dos: el primero encuentra las nueve entradas
mudas.

## 3. Verificación

- **Suite entera:** 5918 / 5918, con código de salida del proceso 0.
- **`verificar_cierres.py` de la raíz:** `d289b()` da CUBIERTO POR TEST;
  39 comprobaciones, ninguna bajada.
- **Tests de menús, traducción, estadística y desembalse** (502 casos): verdes.
