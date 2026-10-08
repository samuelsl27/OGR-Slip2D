# OGR Slip2D v0.1.278

**La curva de retención del transitorio tiene un α propio, `wc_alpha`, que
leen todos los modelos de permeabilidad menos van Genuchten (D275).** Hasta
esta versión, `vg_alpha` era a la vez el parámetro de PERMEABILIDAD de van
Genuchten y la retención de CUALQUIER modelo. Su valor por defecto desde
v0.1.200, 3,6 1/m (el franco de Carsel y Parrish 1988), daba a un material
nuevo una retención con mucho almacenamiento no saturado. En el problema 18
del manual de agua (la presa sin dren bajo un embalse que sube), la carga
sobre el talud a 19 656 h queda a 2,77 m de la figura publicada con ese
valor, y a 0,61 m con 0,036.

## 0. Lo que se encontró

- **El censo de constructores, antes de tocar nada** (la lección de
  v0.1.200, cuando cambiar este mismo valor por defecto movió el 05-017–020
  hasta un −49 % sin cambiar ningún archivo).
  - `HydraulicProperties(` aparece 116 veces en el repositorio, 43 en el
    banco vivo y 1231 en sus instantáneas.
  - Toman el α por defecto **y** llegan a un transitorio que lee la
    retención:
    - los tres respaldos de producción (`seepage.py`, `transient_stability`
      y `hydraulic_set` del API) y el diálogo, es decir, todo material
      nuevo;
    - once tests;
    - dos herramientas del banco.
  - Los transitorios del banco (05-017–020) usan curva de usuario y fijan
    0,036 en su script. El 02-102 y Celia son van Genuchten con α explícito.
- **Las opciones, con la medida delante** (decisión de la propietaria:
  la (a) parcial):
  - **(a) total**, un α de retención para todos los modelos: rompe la pareja
    de Mualem-van Genuchten de un material VG nuevo (kr de un franco y θ de
    otro suelo) y mueve Celia y el acoplamiento de v1125;
  - **(b)**, bajar `vg_alpha` a 0,036: un VG nuevo deja de ser ninguna
    textura (0,036 1/m es el franco en 1/cm leído en 1/m) y mueve el factor
    publicado de `test_transient_coupling_v1125`;
  - **(c)**, avisar: el defecto se queda;
  - **(a) parcial**, la elegida: `wc_alpha` solo donde la retención no es la
    del propio modelo de permeabilidad. Con van Genuchten, van Genuchten
    (1980) deriva kr de esa misma curva, así que un único α sirve para las
    dos.
- **`_auto_time_steps` lee la retención** (`storage_at(-1.0)`): el número
  automático de pasos de todo transitorio de la interfaz o el API depende de
  ella, también en un modelo saturado. Con el α nuevo, un material que no
  es van Genuchten da otro número de pasos automáticos. El banco fija sus
  pasos.
- **La regla 7 alcanzaba a n y m, y no estaba escrita.** Con un modelo que no
  es van Genuchten y sin transitorio, n y m no mueven nada, y el diálogo los
  dejaba activos.

## 1. Qué cambia

### Núcleo

- **`HydraulicProperties.wc_alpha`** (1/m, por defecto 0,036) y
  **`retention_alpha()`**, la única puerta: `vg_alpha` con van Genuchten y
  `wc_alpha` con los demás. La leen `water_content` y
  `specific_moisture_capacity`, y con ellas el almacenamiento, el balance y
  los pasos automáticos.
  - Interruptor `RETENTION_OWN_ALPHA`, con alta en `INTERRUPTORES`,
    (0, 1, 278).
  - **Un archivo sin la clave** lee `wc_alpha = vg_alpha` del propio
    archivo (0,036 si tampoco está): conserva lo que significaba.
  - `problems()` exige `wc_alpha > 0`.
  - El valor por defecto es un **convenio de OGR**, como la curva: es el α
    que mejor reproduce los transitorios publicados 17 y 18 entre las
    lecturas medidas en v0.1.268, y no es ninguna textura. Está escrito en el
    docstring de `retention_alpha`.
- **`MODEL_FIELDS` / `COMMON_FIELDS`:** `vg_alpha` pasa a ser solo de van
  Genuchten y `wc_alpha` lo leen todos los demás.
- **`rules.retention_field_is_read(project, model, field)`**: qué α, n o m
  mueve un número según el modelo y el análisis. La pregunta el diálogo.
- `random_variables`: `wc_alpha` se puede aleatorizar, como `wc_sat`.

### API y MCP

- `hydraulic_set` rechaza `wc_alpha` en un material van Genuchten y
  `vg_alpha` en uno que no lo es («would move nothing»). La pista dice qué α
  lee la retención de ese modelo.
- La nota de la retención nombra `wc_alpha`. La descripción del MCP lo
  añade a la lista de campos.

### Interfaz

- El grupo *Water content function* edita `wc_alpha`. La página de van
  Genuchten recupera su propio α (`vg_alpha`), con una nota que dice que, con
  ese modelo, la curva usa ese α.
- α, n y m se ponen en gris donde no mueven nada. 3 cadenas nuevas, con su
  español; una vieja sustituida.

### Banco (fuera de git)

- `filtracion_comun.retencion(alfa)` pasa la cifra a `vg_alpha` y, si el
  campo existe, a `wc_alpha`: el mismo script reconstruye el motor viejo y
  el nuevo.
- Los scripts del 05-017–020 la usan, y su `retencion.fuente` lo dice.
- `d275()` en el `verificar_cierres.py` de la raíz.

## 2. Tests

`tests/test_retention_alpha_v1278.py`, 23 casos.

- **El ancla externa (regla 1).** El problema 18 se rehace dentro del test y
  se compara con los once puntos de su fig. 18.5, digitalizados a 300 ppp.
  - Un material NUEVO queda a menos de 0,8 m (medido: 0,614).
  - El α viejo, 3,6, queda a más de 2 m (2,768).
  - Con 300 elementos y 20 pasos, las dos cifras se mueven menos de
    0,002 m frente a las 800 / 60 del banco (0,613 y 2,769), a un séptimo
    del coste: unos 12 s por corrida.
- **Regla 7:**
  - `wc_alpha` mueve el transitorio de una curva de usuario y no su
    permanente (al bit);
  - con van Genuchten no mueve nada (al bit);
  - `vg_alpha` mueve el permanente de van Genuchten y no mueve nada con una
    curva de usuario.
- **Un archivo sin la clave** da la misma retención que 0.1.277, con el
  interruptor apagado como testigo.
- La identidad de van Genuchten (1980) para cada modelo y la derivada.
- El API, el diálogo y la tabla de la regla.

**Tests existentes que cambian, cada uno con su razón:**

- `test_retention_dialog_v1268`: el α del grupo es `wc_alpha`, y la regla
  de los grises la dicta el modelo.
- `test_gw_gui_v129::test_custom_m_gates_the_m_field` comprueba la puerta de
  m con van Genuchten, donde m se lee en un proyecto permanente.
- `test_groundwater_ops_v1200::test_the_retention_curve_is_in_metres` usa
  `wc_alpha`: el material es Constant.
- `test_transient_v130`: los cuatro tests de la curva pasaban `vg_alpha`
  pensando en la retención de un material Constant, y ahora pasan
  `wc_alpha`. Lo mismo con el Gardner de 0,1.
- La presa de Gardner de v1269, v1270, v1273 y v1274 fija `wc_alpha=3.6`,
  la retención con la que se midieron sus cifras («measured 2.5 cm»).

## 3. A/B

Árbol contra árbol con `_auditoria/P6_0278/ab_arbol.py` de la raíz del
banco: 0.1.277 sacado con `git archive` frente al árbol de trabajo.
- **Qué cubre:** el 05 entero (todas las variantes, las dos mallas), el
  02-010, el 02-038 (tres alturas por cuatro curvas) y la presa del 102, en
  permanente y en transitorio.
- **Resultado:** **75 filas, 0 distintas**, con cargas al bit, `converged`,
  iteraciones y notas iguales.
- **Por qué no se mueve nada:**
  - el 05-017–020 fija su retención con `filtracion_comun.retencion`;
  - el 05-015, el 016 y el 021 son saturados;
  - la presa del 102 es van Genuchten, que conserva su α.
- El volcado nuevo lleva el rótulo 0.1.277 porque el número se subió después
  de lanzarlo, pero el motor que cargó es el del árbol de trabajo (lo
  comprueba la propia herramienta).

**El banco.** `ejecutar_filtracion.py --banco 05 15 16 17 18 19 20 21
--forzar` corre los 12 casos sin fallos, y la comparativa de la raíz no
cambia en ninguna fila.

## 4. Verificación

- **Suite entera:** 5830 / 5830, con código de salida del proceso 0.
- **El test nuevo en el árbol de 0.1.277:** 22 de 23 fallan.
  - El que pasa es `test_vg_alpha_moves_the_steady_state_of_van_genuchten`,
    que ya era cierto antes del cambio.

## 5. Lo que no se ha probado

- La prueba manual del diálogo: el α en la página van Genuchten y en el
  grupo, y los grises al cambiar de modelo.
