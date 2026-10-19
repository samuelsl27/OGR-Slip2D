# OGR Slip2D v0.1.328

**Una entrada gris de *Interpretar* dice por qué, y un mensaje largo de la barra de estado ya no queda
tapado por los indicadores (D324, D325).** Quinta versión de la tanda P8i.

## 0. Lo que se encontró

- **D324, las entradas grises de *Interpretar*.**
  - «Graficar FS con el tiempo…», «Análisis de la fuerza de soporte…» y «Diagrama de fuerza del
    soporte…» salían en gris y dejaban la barra de estado vacía (la tercera prueba de la interfaz, H3).
  - Su motivo era una ayuda emergente, que ningún menú enseña.
  - `DisabledReasonFilter` (D289), lo único que pone en la barra el motivo de una entrada desactivada
    con los estilos Fusion y windows11, vivía en `main_window` y solo se instalaba en sus menús. D289b
    solo había recorrido esa ventana.
  - **Medido con el test nuevo**, en *Interpretar* sin transitorio, soportes ni estadística, había **12**
    entradas desactivadas y mudas:
    - las tres de la prueba;
    - «Mostrar línea de empujes» (con Bishop);
    - el historial de iteraciones y la gráfica de convergencia del agua;
    - cuatro de estadística;
    - las dos de superficies GM, cuya ayuda dice qué hacen, no por qué están grises.
  - **De paso:** el filtro guardaba su ventana en un atributo, y la ventana guardaba el filtro. Es el
    ciclo que 0.1.326 quitó del filtro de altura (la familia de D310).
- **D325, los mensajes largos.**
  - `QStatusBar` dibuja su mensaje por debajo de los indicadores permanentes, así que SNAP / REJILLA /
    ORTO / OSNAP tapaban el final de los largos. El que vio la prueba acababa en «…, que ader».
  - **Medido:** en la ventana principal, los indicadores ocupan casi 900 px. A 900 px de ventana no queda
    sitio para ningún mensaje, ni ahora ni antes; a 1366 quedan 490, y a 1900, 1024.
  - Los tests de la ventana leen `currentMessage()` en ventanas que nunca se muestran, donde la barra no
    tiene ancho. Acortar ahí habría cambiado lo que leen.

### Dos trampas del test, no del programa

- **Un envoltorio de menú que deja de valer.** Un `QMenu` sacado de una acción de la barra de menús
  dentro de una expresión generadora salía «ya borrado» en cuanto el generador soltaba esa acción, aunque
  el menú seguía vivo (la barra lo enseñaba). El test llega al menú desde su propia acción
  (`associatedObjects()`), y recorre la barra devolviendo solo acciones.
- **Un menú que nunca se ha mostrado** no encuentra la acción bajo un punto (`actionAt`). El test lo abre
  con `popup()`, que no bloquea, mueve el puntero sobre la entrada y lo cierra.

## 1. Qué cambia

- **D324:**
  - **`ogr_gui/disabled_reasons.py`** (nuevo):
    - el filtro, que llega a su ventana como su padre de Qt y no guarda ninguna referencia Python a ella;
    - `install(ventana)`, que lo pone en todos los menús de una ventana;
    - `gate(acción, activa, motivo)`, que activa o desactiva y deja el motivo como `statusTip` solo
      mientras está desactivada, el convenio de D289b.

    `main_window` lo importa de ahí, y el nombre sigue importable desde `main_window`.
  - ***Interpretar*** instala el filtro, y todas sus entradas desactivables pasan por `gate`. Las ayudas
    emergentes se conservan.
  - **Las de superficies GM** llevan un motivo propio: un análisis probabilístico o de sensibilidad, o
    una búsqueda que informe de varios mínimos. Su castellano usa los términos que el programa ya tenía:
    «búsqueda multimodal», «Talud completo» e «informar de varios mínimos».
- **D325:**
  - **`ElidingStatusBar`**, en `ogr_gui/widgets/status_bar.py`:
    - el mensaje acaba en «…» donde empiezan los indicadores, y su texto entero es la ayuda de la barra
      mientras dura;
    - al cambiar de tamaño se vuelve a acortar sin reiniciar su tiempo;
    - `currentMessage()` responde el mensaje entero, o lo que enseñe la barra si lo puso Qt desde C++
      (la ayuda de estado de una acción);
    - sin mostrar, o sin sitio, no acorta nada.
  - **`OgrStatusBar` hereda de ella**, y *Interpretar* la usa como barra antes de escribir nada en ella.
- **Una clave nueva.**

## 2. Tests

`tests/test_interpret_reasons_status_v1328.py` (nuevo), 11 casos:

- ***Interpretar*, sobre una búsqueda pequeña del primer ejemplo trabajado:**
  - ninguna entrada desactivada de su barra de menús queda sin motivo;
  - las tres de la prueba lo dicen;
  - control: con un soporte, «Análisis de la fuerza de soporte…» está activa y no lleva motivo;
  - con el menú abierto, el puntero sobre una entrada gris pone su motivo en la barra;
  - el filtro no guarda su ventana en Python.
- **La barra, en la ventana principal a 1366 px:**
  - el mensaje más largo que vio la prueba acaba en «…», cabe en el sitio que dejan los indicadores, y
    su texto entero está en la ayuda y en `currentMessage()`;
  - control: uno corto sale entero y sin ayuda;
  - a 1900 px enseña más, sin reiniciar su tiempo;
  - la ayuda está mientras dura el mensaje y se va con él;
  - una ventana que nunca se muestra conserva el mensaje entero;
  - *Interpretar* tiene la misma barra.

**Con el código de 0.1.327 fallan 8 de los 11.** Los tres que pasan en los dos árboles son los dos
controles y la ventana que nunca se muestra. Se corrió sobre un `git archive` de 0.1.327, sin el buscador
editable.

## 3. Verificación

- **El test de esta versión**, 11/11, después de las dos trampas de §0.
- **Los vecinos**, 908/908 en 63 archivos:
  - *Interpretar*, la barra de estado, los motivos de lo desactivado, la ventana principal y los menús;
  - el castellano en pantalla y el censo de AST;
  - el informe de coeficientes y el resultado anterior;
  - la ayuda, deshacer, la estadística y los soportes.
- **Suite entera:** 6199/6199, `EXIT=0`, 89 min.
- **Banco:**
  - `verificar_cierres.py` entero: 74 comprobaciones, D324 y D325 **CUBIERTO POR TEST**.
  - **La primera corrida apartó una bajada: D289**, de CUBIERTO a SIGUE ABIERTO. Su comprobación buscaba
    `class DisabledReasonFilter` en `main_window.py`, de donde se ha mudado. La comprobación lo busca ahora
    también en `ogr_gui/disabled_reasons.py`, y la segunda corrida da 0 bajadas. Es lo mismo que pasó con
    `d282` en 0.1.315. El comportamiento lo siguen cubriendo `test_disabled_menus_v1288` y
    `test_disabled_reasons_v1294`, que pasan.
  - instantánea `Evaluaciones/0.1.328`, las dos fichas retiradas y podadas de P8;
  - prompts (37);
  - auditorías con 0 ERROR en la raíz y en el 02.
- **Ningún número del motor cambia:** son textos y la barra de estado.

## 4. Pendiente

- **D326–D329** (resto de P8i), y D314 después.
- **A mano, en la cuarta prueba de la interfaz:**
  - las entradas grises de *Interpretar* con el puntero encima;
  - un mensaje largo a la anchura de tu pantalla, con su ayuda.
