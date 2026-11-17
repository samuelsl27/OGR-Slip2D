# OGR Slip2D v0.1.468

**El informe y las exportaciones con cuñas (D357), y D453.** Lo que sale del programa ya no enseña un resultado de
Sarma como si sus cuñas fueran dovelas verticales, ni se deja las caras:
- **el informe PDF** tiene una tabla de las caras de las cuñas, los ajustes propios de Sarma y los números del método
  sobre la superficie crítica (Kc con F = 1, el menor |q|, el cociente de fuerzas, las cuñas y las caras hechas
  verticales);
- **el CSV de Interpretar** escribe un segundo archivo con las caras;
- **el API** da de cada cara su geometría, su resistencia y sus fuerzas, y de cada cuña su polígono y su área;
- **el HDF5** guarda de cada cara el ángulo, la resistencia y las fuerzas, además de la geometría.

Y **D453**, de antes de Sarma: la tabla de dovelas del informe titulaba «Base σ [kPa]» y «Shear str. [kPa]» e
imprimía fuerzas en kN/m, en todos los métodos. Ahora imprime tensiones. Ningún factor de seguridad cambia, de ningún
método.

Decisiones de la propietaria (2026-11-17):
- **D453 va aquí,** con el informe: la tabla imprime la fuerza entre la longitud de la base, como el panel de
  Interpretar, bajo sus [kPa].
- **El CSV de las caras va en un segundo archivo,** `<nombre>_faces.csv`, junto al elegido.

## 0. Lo que se encontró

### Las exploraciones del plan (solo lectura)

- **El informe** daba una fila por cuña con las columnas de una dovela y ninguna tabla de caras. Sus «Analysis
  Options» daban `methods.num_slices`, que Sarma no usa, y nada de `settings.sarma`. Sus «Global Minimums» no daban
  ningún número del método.
- **El CSV** daba una fila por cuña y ninguna cara. **El API** daba en `sarma_faces` solo E, E′ y X, sin geometría ni
  resistencia, y ninguna fila de `slices` decía el polígono de su cuña. **El HDF5** guardaba de cada cara la geometría
  y PW, sin θ, c̄, φ̄, E, E′ ni X.
- **D453:** `_slice_table` leía `base_normal_force` y `base_shear_strength` y no los dividía. El contrato de
  `LEMResult` (v0.1.107) dice que son fuerzas en kN/m; el panel de Interpretar sí dividía. En la fila 1 de la tabla de
  la referencia de Ej_2 (método ordinario), el informe imprimía 9,31 y 32,87 donde la referencia da σn = 8,80223 y
  τ_f = 31,082 kPa (base de 1,058 m). En las dovelas largas del mismo círculo (3,785 m) el error llega a ×3,8.

### Al escribir

- **La regla de las filas no podía quedarse en el motor.** El informe vive en `ogr_core`, que no importa
  `ogr_slip2d`. `per_slice` y `slice_stress` pasan de `ogr_slip2d/interpretation.py` (que las reimporta) a un módulo
  nuevo, `ogr_core/result_rows.py`, junto con `face_rows`. Lo leen el informe, el panel, el CSV, el API y el HDF5.
- **Ese módulo no podía ir dentro de `ogr_core/report/`.** El `__init__` de ese paquete importa el generador y, con
  él, reportlab: 0,65 s acumulados al importarlo. El API y el motor habrían cargado el informe para leer una fila.
- **El arnés de mutantes compilaba en una copia del espacio de nombres del módulo.** Así el `generate_report` mutado no
  veía el `Paragraph` que parchea el test, y los cuatro mutantes del informe «morían» por una razón falsa. Peor: el
  método del CSV mutado no veía el `get_save_file_name` parcheado, abría el diálogo modal de verdad y la corrida se
  colgaba (dos procesos quedaron parados; uno seguía vivo después de parar su tarea). Ahora se compila en el módulo
  mismo, con sus globales vivos. Una función importada por nombre en otros módulos se reenlaza también en ellos.

### La revisión adversaria (un agente)

No encontró ningún alto. D453 está bien en los diez métodos: sobre la rejilla del demo, el índice de cada dovela
coincide con su posición en los arrays del método. Encontró tres medios y varios bajos:
- **MEDIO — una grieta de tracción llena daba PW = 0 y E′ = E en la cara de cabeza.** El agua de la grieta es el empuje
  de cabeza, sobre una cara extrema cuyo PW es 0 por construcción. En la pendiente del test, con 4 cuñas, la fila decía
  PW = 0 y E′ = E = 78,5 = ½·9,81·4². Una grieta llena solo empuja agua, así que E′ = 0. Venía de 0.1.464 en el E′ del
  API y del panel; lo nuevo era la columna PW = 0 del informe, el CSV y el HDF5. Arreglado en el solver: el agua de la
  cara de cabeza es la de la grieta (`SarmaSolution.face_water`, `details["sarma_face_water"]`), y E′ = E − PW vale 0
  allí. F no se mueve: E′ no entra en la recurrencia. Cambian el E′ de esa cara en el API y en el panel y, solo si era
  la mayor fuerza, `sarma_max_force_ratio`.
- **MEDIO — «Number of Wedges» salía dos veces con dos significados.** Era el ajuste en «Analysis Options» y las cuñas
  de la crítica en «Global Minimums»: 25 y 19 en el 4 saturado con los ajustes por defecto. El ajuste se llama ahora
  como en la página de métodos, «Least Number of Wedges» («Número mínimo de cuñas»).
  - **Se dice, sin arreglar: ese nombre tampoco es cierto.** Las divisiones uniformes cuyas caras de política se cruzan
    se quitan (0.1.464), y por eso la crítica tiene 19 cuñas con un «mínimo» de 25. Viene de 0.1.464 y lo decide la
    propietaria.
- **MEDIO — las cuñas se numeraban desde 0 y las caras desde 1** en el API y en el CSV. Un agente que cruzara «la cuña
  k está entre las caras k y k + 1» se desplazaba una posición. Las caras cuentan ahora desde 0, como las cuñas; el
  informe numera las dos tablas desde 1.
- **BAJOS:**
  - El test dejaba vivos tres mutantes: el bloque de Sarma imprimiendo las iteraciones de los métodos, «Faces Made
    Vertical» fijado a 0 y el hueco del HDF5 como un 0. Ahora mueren: el test cambia la tolerancia y las iteraciones de
    los métodos y las de Sarma por separado, cuenta la cara hecha vertical del caso de `test_sarma_method_v1464` y
    escribe una superficie sin fuerzas.
  - Con dos cuñas el ajuste y el recuento coincidían, y el test no distinguía las dos filas. El informe del test usa
    ahora las 25 del ajuste, de las que la crítica conserva menos.
  - «Desde el pie» era falso cuando la masa desliza hacia +x: las caras van en x creciente, y la primera es entonces la
    de cabeza. Lo dicen ahora el docstring de `face_rows` y `docs/mcp/herramientas.md`, con el convenio de θ y que E y X
    van en el marco del método (la imagen especular da los mismos valores).
  - **Graph Query de Interpretar copiaba la regla N/l.** Dividía una base de longitud nula por 1e-12 y pintaba un 0
    donde no había número. Ahora pregunta a `slice_stress` y deja un hueco (NaN).
  - El API publica `sarma_faces` también en superficies sin factor, con E, E′ y X a `null`. Se queda así, porque la
    geometría sirve, y la documentación lo dice.
  - Los nombres de las columnas del HDF5 (`theta_deg`, `tan_phi`) no eran los del API ni los del CSV. Ahora son los
    mismos (`angle_deg`, `friction_angle` en grados): el HDF5 escribe las filas de `face_rows`.
  - El docstring de `face_rows` decía que una población volcada da las caras «de su registro»; salen de los campos
    que guarda su sustituto (`wedge_fields`).
- **Se declara, sin cambio:**
  - El CSV de Interpretar reemplaza sin preguntar un `<nombre>_faces.csv` que ya exista. El diálogo de guardar
    pregunta por el archivo principal, y un aviso modal no puede ir en un camino que ejecuta un test. La barra de
    estado nombra los dos archivos.
  - La tabla de dovelas titula el peso «Weight [kN]», al lado de la tabla de caras en kN/m. Ya existía, y cambiarlo
    movería el texto fijado del informe; queda para la propietaria.

## 1. El cambio

- **`ogr_core/result_rows.py` (nuevo):** `per_slice`, `slice_stress` y `face_rows`.
- **`ogr_core/report/report_generator.py`:**
  - D453: «Base σ» y «Shear str.» son `slice_stress`, en todos los métodos; los rótulos no cambian;
  - con Sarma: el bloque de sus ajustes (`_sarma_settings_rows`), sus filas en «Global Minimums»
    (`_sarma_result_rows`) y la tabla de caras (`_face_table`, #, x e y de la base, θ, longitud, PW, c̄, φ̄, E, E′ y X).
- **`ogr_gui/interpret_window.py`:**
  - el CSV de dovelas escribe además `<nombre>_faces.csv` con Sarma, y la barra de estado nombra los dos;
  - Graph Query pregunta a `slice_stress`.
- **`ogr_api/results.py`:**
  - `sarma_faces` lleva las filas de `face_rows`, y conserva las tres claves de 0.1.464;
  - las filas de una cuña en `slice_table` llevan `area` y `polygon`.
- **`ogr_core/project/results_io.py`:** el conjunto `faces` pasa de 6 a 12 columnas, con su atributo `columns`. Un
  archivo sin Sarma no cambia.
- **`ogr_slip2d/sarma/solver.py` y `methods/sarma.py`:** el agua de una grieta como PW de la cara de cabeza
  (`face_water`, `sarma_face_water`).
- **Español** de cada rótulo nuevo; `docs/mcp/herramientas.md` (la fila de `results_get`); la spec 009, tarea 28b.

## 2. El test

`tests/test_sarma_report_v1468.py`, 21 casos. Comprueba:
- **D453:**
  - la fila 1 de la tabla de la referencia de Ej_2;
  - cada celda de un Bishop y de un Sarma es N/l y S/l, divididos a mano;
  - Graph Query da los mismos números y un hueco donde no hay número;
- **las caras del problema 4** (Hoek 1987):
  - la interfaz de la figura en forma cerrada: θ = 116,48°, la longitud y PW = ½·γw·(y_wt − y)·L;
  - c̄ = 100 y φ̄ = 42 del material, E′ = E − PW, las fuerzas del método y la numeración desde 0;
  - la población volcada;
  - la grieta en los dos sentidos;
- **el informe:**
  - la tabla de caras, celda a celda;
  - el bloque de ajustes, con cada ajuste moviendo su fila;
  - las filas de la crítica, la cara hecha vertical, y nada de eso sin Sarma;
- **el CSV:** el segundo archivo igual a `face_rows`, y ninguno sin Sarma;
- **el API y el HDF5:**
  - las claves nuevas y las viejas;
  - el área de la cuña del pie, el triángulo en forma cerrada;
  - las doce columnas con sus valores y el NaN de una fuerza que falta;
- **el español.**

Mutantes: `_auditoria/P9_D357/mutants_v1468.py` del banco, con su log. Son 35, contando los diez de la revisión, y no
vive ninguno.

## 3. La suite

- `test_sarma_solver_v1461`: su comprobación E′ = E − PW lleva el agua de la grieta en la cara de cabeza
  (`_equilibrium(head=)`), en el caso que la tiene.
- **La primera suite entera dio tres fallos, ninguno de un número:**
  - `test_gui_spanish_v1318` contaba como texto sin `tr()` el sufijo `"_faces.csv"`, que la barra de estado nombra
    dentro de la ruta. Entra en sus excepciones con su razón, como la extensión `".csv"`: es un nombre fijo, por
    decisión de la propietaria, que un guion puede buscar, como las claves de sus columnas.
  - `test_shared_test_caches_v1378` vio que el test nuevo leía la caché de `test_sarma_interpret_v1467`. En la corrida
    en serie habría recibido el objeto que calculó ese archivo, y con `--jobs` uno nuevo. Ahora resuelve sus casos él
    mismo.
  - Se repitió la suite entera.

## 4. Verificación

- **La suite entera, `--jobs 4`, tras la revisión:** la primera dio los tres fallos del apartado 3. La segunda: 7971
  casos, pasan 7970 y uno queda saltado, sin fugas ni tramos muertos. La última serie en verde es de hace 46 commits.
- **El test nuevo:** 21 de 21. **Mutantes:** 35, ninguno vivo.
- **Los README:** 7949 → 7970 tests.

## 5. Lo que queda

- El banco, tras el commit:
  - `d453()` en el `verificar_cierres.py` de la raíz, discriminado con 0.1.467, y retirar D453;
  - el progreso de D357.
- **Para la propietaria:**
  - el nombre «Número mínimo de cuñas» de la página de métodos, que no es un mínimo cuando se quitan caras que se
    cruzan;
  - el «Weight [kN]» de la tabla de dovelas.
- **Prueba a mano para la propietaria:** el informe PDF del 4 saturado con Sarma (las dos tablas y el bloque de
  ajustes) y el CSV doble desde Interpretar.
- 0.1.469: la herramienta de ángulos y el menú contextual del vértice.
