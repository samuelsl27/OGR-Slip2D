# OGR Slip2D v0.1.369

**La ventana nombra cada método por su nombre y da la fuerza del retroanálisis con sus unidades (D343), y
las tablas de superficies titulan su columna con lo que enseñan: FS, FSD con la norma de diseño, o Ky con
los valores de Ky en una búsqueda del coeficiente sísmico crítico (D345). Las dos, cerradas.** Séptima
versión de la tanda P8l.

## 0. Lo que se encontró

- **D343, en la quinta prueba de la interfaz** (H5 y H3):
  - la barra del retroanálisis decía «Retroanálisis (bishop_simplified): fuerza necesaria 101.1 …». La
    plantilla recibía `values["method_id"]` tal cual, y las tres fuerzas no llevaban unidades;
  - la leyenda de *Factor de seguridad frente al tiempo* decía «bishop_simplified» y «janbu_simplified».
    `fos_history` etiqueta cada serie con el identificador, que es lo que lee el API, y las dos ventanas lo
    pasaban al gráfico sin cambiar.
- **La misma familia, sin ficha:** el barrido de desembalse ponía el identificador en su barra («Nivel
  crítico de desembalse (bishop_simplified)»), en la leyenda de su gráfico y en su respaldo de texto, y
  Optimizar superficies lo ponía en su lista de métodos. Es la regla de D315, y entra aquí porque es el
  mismo arreglo. La lista de la optimización devuelve el identificador del nombre elegido.
- **Las unidades de una fuerza por unidad de longitud:** el resto de la interfaz escribe «kN/m» fijo, sin
  convertir. La propietaria decidió convertirla a las unidades del proyecto con la magnitud que el sistema
  de unidades llama así, `Quantity.BOND_STRENGTH` (kN/m, MN/m, lbs/ft…), como hace Interpretar con el
  desplazamiento de Newmark.
- **D345, en la quinta prueba** (H9): con el Eurocódigo 7 DA1-C1, la tabla *Superficies* de Interpretar
  titulaba «FS» una columna de factores de sobredimensionamiento. El resumen ya decía «Factor de
  sobredimensionamiento» y el PDF «FSD».
- **Lo que la ficha no vio:** en una búsqueda de Ky la tabla ordena las superficies por su Ky
  (`top_n` usa `surface_score`), pero escribía sus FS bajo «FS». Decisión de la propietaria: la columna
  dice «Ky» y da el Ky de cada superficie, en las dos tablas, la de Interpretar y el panel de resultados
  de la ventana principal.
- **El diseño de `fos_label` se respeta.** Su docstring explica por qué la barra de estado y la cabecera
  del panel principal escriben siempre el `.fos` del crítico: en una búsqueda de Ky ese número es un FS(0)
  de verdad, y ponerle encima «coeficiente sísmico crítico» sería engañoso. Las dos siguen igual. Lo que
  cambia es la COLUMNA, cuyo valor cambia con su rótulo, que es justo lo que ese docstring permite («the
  seismic question is asked only where the VALUE also changes»).

## 1. Qué cambia

- **`ogr_gui/reported_quantity.py`:** `column_caption` y `column_value`, con la regla de
  `reported_caption`: «FS» / «FSD» / «Ky», y el `.fos` o el Ky de cada superficie.
- **Las dos tablas** (`_ResultsTableDock` de Interpretar y `ResultsDock` de la ventana) ponen la cabecera
  y los valores con ellas cada vez que reciben un resultado. Interpretar les pasa su informe de la norma.
- **`ogr_gui/main_window.py`:**
  - la barra del retroanálisis usa `method_name` y convierte las fuerzas (`_force_per_length`), con la
    unidad en la plantilla;
  - el barrido y la lista de la optimización usan `method_name`.
- **Las dos leyendas de FS frente al tiempo** pasan cada serie por `method_name`; `fos_history` no
  cambia.
- **Castellano:** la plantilla del retroanálisis, con las unidades, y «Ky».
- **Ningún número cambia:** en la tabla, el valor de un FS o de un FSD es el de antes, y en Ky es el Ky
  que la búsqueda ya calculaba.

## 2. Tests

- **`tests/test_names_and_headings_v1369.py`** (nuevo, 6 casos), por las ventanas reales:
  - la barra del retroanálisis en castellano («Retroanálisis (Bishop simplificado) … 3 × kN/m») y en
    inglés con unidades imperiales (3 × lbs/ft: 2770,7 lbs/ft son los 40,43 kN/m del ejemplo);
  - las dos leyendas de FS frente al tiempo, con los nombres;
  - la cabecera de las dos tablas: «FS»/«FoS» sin norma, «FSD»/«ODF» con DA1-C1 (y el mismo valor), y
    «Ky» con el Ky en una búsqueda de Ky.
- **Cambio deliberado:** `test_fos_chart_v1308` esperaba la serie de `fos_history` tal cual en el
  gráfico. Ahora espera la misma serie con los nombres.

## 3. Verificación

- **Los tests de esta versión:** 6/6 nuevos y los de `test_fos_chart_v1308`. El primer intento de los
  nuevos esperaba «Bishop simplified»: en inglés es «Bishop Simplified», y el test lo pide ahora a
  `method_name`.
- **Con el código de 0.1.368 fallan los 6.**
- **Los vecinos:** 703 casos en Interpretar, los paneles de resultados, el castellano, la norma, el
  barrido, la optimización, los cálculos de 0.1.363–0.1.366, el retroanálisis, el transitorio y los
  gráficos de FS: 702 a la primera. **Un cambio deliberado:** `test_i18n_coverage_v141` admite menos de
  doce entradas cuyo castellano es igual a la clave sin justificar, y «Ky» era la duodécima. Pasa a su
  lista razonada, al lado de «Ky:», porque es el mismo símbolo.
- **Suite entera:** 6608/6608, `EXIT=0`, 130 min.
- **Banco:**
  - raíz: `verificar_cierres.py` entero, 104 comprobaciones (dos más, `d343` y `d345`), 0 bajadas. Las
    dos quedan **CUBIERTO POR TEST**:
    - la barra de un retroanálisis de verdad del ejemplo dice «Retroanálisis (Bishop simplificado):
      fuerza necesaria 40.4 kN/m…»;
    - la leyenda de FS frente al tiempo, «Bishop simplificado», «Janbu simplificado»;
    - las dos tablas: «FS» 1,0914 sin norma, «FSD» 0,9790 con DA1-C1 (el «0.979» que midió la prueba de
      la interfaz) y «Ky» 0,0810;
  - manual 02: `verificar_cierres.py --seco`, 238 veredictos iguales;
  - **D343 y D345 retiradas**, podadas de `PAQUETES` y tachadas en la cadena de P8;
  - instantáneas `Evaluaciones/0.1.369` (raíz 983 archivos, 02 3284), prompts (36) y auditorías con
    0 ERROR.

## 4. Pendiente

- La tanda sigue con D344 (0.1.370): los textos fijos que siguen en inglés.
