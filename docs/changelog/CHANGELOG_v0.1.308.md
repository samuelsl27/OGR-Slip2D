# OGR Slip2D v0.1.308

**«FoS vs time…» de *Interpret Groundwater* deja de ser modal, y las dos
ventanas de interpretación dibujan una sola serie (D311).** Tercera versión de
la tanda P8f.

## 0. Lo que se encontró

- **El gráfico modal.** Se encontró al planificar la tanda y se reportó antes
  de tocarlo. `InterpretGroundwaterWindow._plot_fos_history` abría su gráfico
  en un `QDialog` con `exec()`:
  - bloqueaba la aplicación, así que no se podía comparar con el modelo de al
    lado ni tener dos abiertos;
  - sin pantalla se queda esperando para siempre;
  - si no había factores, lo decía con un `QMessageBox` modal, en inglés y sin
    `tr()`.
- **El gemelo ya estaba bien.** *Interpret > Graph SF with Time*
  (`InterpretWindow._graph_sf_with_time` → `_plot_xy`) es no modal, guarda su
  ventana para que Qt no la recoja y está traducido.
- **Dos series.** Cada ventana construía la serie del factor contra el tiempo
  a su manera, a partir de las mismas `notes["fos"]`. La de *Interpret
  Groundwater* titulaba el eje «Critical factor of safety», y la otra «Factor
  of safety».

## 1. Qué cambia

- **`fos_history(results, initial=None)`** en
  `ogr_slip2d/transient_stability.py`, sin Qt: una serie por método, `[(método,
  tiempos, factores)]`, con las etapas que tienen factor. También lleva el
  estado inicial en t = 0 cuando tenga factor; eso lo calcula D312.
- **`ogr_gui/xy_chart.py`, `show_xy_chart(...)`:** el gráfico XY no modal que
  era `InterpretWindow._plot_xy`, que ahora delega en él.
- ***Interpret Groundwater*:**
  - «FoS vs time…» usa los dos y devuelve la ventana;
  - sin factores, lo dice la barra de estado, traducido;
  - los títulos y los ejes son los de *Interpret*, que ya tenían castellano.
- **El presupuesto exacto de mensajes sin `tr()` baja de 12 a 10.**

## 2. Tests

`tests/test_fos_chart_v1308.py`:
- **la serie:**
  - una por método, solo con las etapas que tienen factor;
  - el estado inicial va primero, en t = 0, si tiene factor, y si no, no
    añade nada;
- **sin nada modal:** el botón no llama a `exec()`, que se sustituye por uno
  que falla, y la ventana queda abierta, no modal y referenciada;
- **sin factores, la barra de estado,** también en castellano;
- **las dos ventanas dan al gráfico la misma serie, la de `fos_history`:**
  *Interpret Groundwater* por su botón, e *Interpret* por
  `_graph_sf_with_time`.

**Con el código de 0.1.307 fallan los 5,** cada uno por la causa exacta:
- los dos caminos modales (`exec()` y el `QMessageBox` de «sin factores»), que
  el test convierte en fallo en lugar de esperar;
- el módulo `ogr_gui.xy_chart` y la función `fos_history`, que no existían.

Se corrió sobre una copia del árbol de 0.1.307 sin el buscador editable.

## 3. Verificación

- **Suite entera:** 6053/6053, código de salida 0, a la primera.
- **Banco:** `d311()` en el `verificar_cierres.py` de la raíz, registrada en
  `COMPROBACIONES`: **CUBIERTO POR TEST**. Ciclo de cierre:
  - `verificar_cierres.py` entero: 50 comprobaciones, 0 bajadas;
  - instantánea `Evaluaciones/0.1.308` antes y después (`--forzar`);
  - `retirar_cerrados.py --escribir D311`;
  - poda de la lista P8 y D311 tachada en la fila P8;
  - `generar_prompts.py`: 42 prompts y las mismas 19 FALTA de paquetes
    anteriores;
  - `auditoria_invariantes.py` en la raíz y en el 02, con 0 ERROR.
- **Los tests vecinos**, antes de lanzarla: 368/368. Son todas las ventanas de
  *Interpret*, que comparten ahora el gráfico, el transitorio, i18n, agua en la
  GUI, gráficos y menús.
- **Ningún número cambia:** es interfaz. La serie es la misma que dibujaban
  las dos ventanas.

## 4. Pendiente

- A mano: «FoS vs time…» con la ventana del modelo usable a la vez.
