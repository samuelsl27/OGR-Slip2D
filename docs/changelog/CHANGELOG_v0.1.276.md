# OGR Slip2D v0.1.276

**Lo que encontró la prueba manual de D191 y D271.** Una sesión de Claude
con control del escritorio ejecutó en la aplicación real el procedimiento
de la prueba pendiente. Las 15 comprobaciones del diálogo y las cuatro
cifras esperadas de la barra de estado coincidieron al pie de la letra.
Para llegar a ellas tuvo que sortear un fallo de interfaz anterior a la
tanda, y destapó varios más. Ningún número del motor cambia.

## 0. Lo que se encontró

- **D281 · el menú Groundwater no funcionaba tras abrir un proyecto.**
  - **Síntoma:** tras File > Open de un `.ogr` con método FEA y malla, Define
    Hydraulic Properties, Set Boundary Conditions, Transient, Compute e
    Interpret Groundwater no hacían nada.
  - **Causa:** `_update_groundwater_actions` solo la llamaban los propios
    comandos de agua, Project Settings y el arranque, cuando el proyecto
    está vacío. `refresh_action_availability`, que es lo que llaman Open,
    New, la demo y cada evento del proyecto, no las tocaba. El menú se
    quedaba con el estado del arranque.
  - **Rodeo:** Project Settings > OK sin cambiar nada.
  - **Por qué ningún test lo vio:** ninguno adjuntaba un proyecto con malla
    y miraba después el menú.
  - **Sin verificar:** la sesión dice que los elementos deshabilitados no se
    veían en gris. No hay hoja de estilos que lo explique y no se ha podido
    reproducir sin pantalla.
- **D282 · el diálogo de propiedades hidráulicas no cabía en una pantalla de
  portátil.** Con el grupo de contenido de agua de D191 y la tabla de D271
  medía 842 px, y 974 px con una curva, en una pantalla útil de 816 px. La
  barra de título quedaba fuera de la pantalla y no se podía mover. Además,
  en el mismo diálogo:
  - la cabecera «Matric suction (kPa)» salía cortada;
  - la línea del *Plot* empezaba en 0,1 kPa y dejaba suelto el primer
    punto, que se dibuja en 0,01;
  - cada apertura dejaba vivo el diálogo anterior, oculto.
- **D283 · la aplicación se cierra sin preguntar si se guardan los
  cambios.** `closeEvent` no mira `is_dirty`. Queda abierta, porque decidir
  si se pregunta, y cómo hacerlo sin un modal que cuelgue los tests, le
  toca a la propietaria.
- **Lo que no era un defecto.** Entre 0 y 10 kPa la curva del *Plot* sale
  curva en ejes log-log. Es correcto: la curva de usuario se interpola
  lineal en log k frente a la succión, y la gráfica usa la misma función que
  el solver.

## 1. Qué cambia

- **`MainWindow.refresh_action_availability`** refresca también las
  acciones de agua. Abrir, Nuevo, la demo y cualquier evento del proyecto
  (la API, el puente de agentes) dejan el menú al día.
- **Diálogo hidráulico:**
  - los parámetros van dentro de un `QScrollArea`, con los avisos y
    Aceptar/Cancelar fuera, siempre a la vista;
  - la primera columna de la curva toma el ancho de su cabecera;
  - la línea del *Plot* empieza en el primer punto.
- **`_define_hydraulic_properties`** libera el diálogo al cerrarlo
  (`deleteLater`), y con él sus ventanas de gráfica.

## 2. Tests

`tests/test_groundwater_menu_after_open_v1276.py`, 8 casos. Los 7 que se
pueden correr con 0.1.275 fallan allí. El del *Plot* no se corre contra
0.1.275 porque su `exec()` modal lo colgaría.

- **El menú:**
  - adjuntar un proyecto FEA con malla habilita propiedades, contornos,
    transitorio y cálculo, y deja Interpret deshabilitado porque aún no hay
    resultado;
  - uno sin malla deshabilita el cálculo;
  - un evento del proyecto (la malla creada desde fuera) lo refresca.
- **El diálogo:**
  - los parámetros se desplazan y los botones no;
  - con una curva de 12 puntos cabe por debajo de 600 px;
  - la primera columna se ajusta a su cabecera;
  - la línea y el primer punto empiezan en (0,01; 1e-5);
  - la ventana no deja diálogos vivos tras dos aperturas.

Suite entera: **5807 de 5807**.

## 3. Banco

- **D281 y D282** se abren y se cierran en esta versión, fuera de la lista
  de paquetes, como D272. `d281()` y `d282()` del `verificar_cierres.py` de
  la raíz dan **CUBIERTO POR TEST**.
- **D283** queda abierta en P1.
- La última ficha es D283; la siguiente libre, D284.
