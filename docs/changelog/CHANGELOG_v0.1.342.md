# OGR Slip2D v0.1.342

**La malla de elementos finitos y los datos de filtración que guarda el proyecto bajan al núcleo
(`ogr_core.fem`), y un `.ogr` con malla, campo y etapas se carga sin importar el motor (D337, tercera
parte).** Tercera versión de la tanda P8k.

## 0. Lo que se encontró

- **El cargador del proyecto importaba `ogr_fem2d` en tres sitios** (`Project.from_dict`): para la malla, las
  condiciones de contorno de la filtración y los resultados. Son datos, y las identidades cerradas que
  reconstruyen sus campos derivados.
- **`restore_derived` construía un solucionador** solo para llamar a su bucle de flujos.
- **La velocidad restaurada no es la del campo en memoria, y nunca lo fue.**
  - El archivo guarda las alturas y el `kr` con nueve cifras significativas (`SeepageResult._round`), a
    propósito.
  - Medido en el campo del test, la velocidad restaurada se aparta de la del solucionador hasta 5,8·10⁻⁷ en
    relativo, en 272 de 273 elementos. Es así en 0.1.341 exactamente igual que ahora.
  - Lo exacto es que la velocidad restaurada es la que da el solucionador sobre lo guardado. Eso es lo que
    exige el test.
- **Ningún registro de decodificadores.** Si el motor rellenara uno al importarse, cargar un modelo antes de
  importarlo dejaría `fem_mesh = None`, y el siguiente guardado borraría la malla sin aviso.

## 1. Qué cambia

- **`ogr_core/fem/`** (nuevo):
  - `mesh.py`: `Mesh`, `Node`, `Element`, `triangle_shape_ratio` y `DEGENERATE_SHAPE_RATIO`, movidos enteros
    de `ogr_fem2d/mesh/mesh.py`;
  - `seepage_data.py`: `BCType`, `NodeBC`, `SegmentBC`, `SeepageBoundaryConditions`, `SeepageResult`,
    `restore_derived` e `hydraulic_props_of`, palabra por palabra, más `element_fluxes`. Este último es el
    bucle de flujos del solucionador (v = −K·∇H; Bathe y Khoshgoftaar 1979).
- **`ogr_fem2d` reexporta todos esos nombres en sus rutas viejas.** Son los mismos objetos, así que
  `isinstance` y todas las importaciones siguen valiendo. `SeepageSolver._element_fluxes` llama a
  `element_fluxes`.
- **`Project.from_dict`** los importa del núcleo.

**Cambios deliberados en tests:**
- `test_core_layering_v1340` pierde las tres entradas;
- `test_no_convergence_advice_v1273`, que busca consejos retirados en las cadenas del módulo de filtración,
  mira también el módulo nuevo, para cubrir lo mismo que antes.

## 2. Tests

- **`tests/test_fem_data_in_core_v1342.py`** (nuevo, 5 casos):
  - **una clase en las dos rutas:** cada nombre de `ogr_fem2d.mesh`, `ogr_fem2d.mesh.mesh`,
    `ogr_fem2d.solvers` y `ogr_fem2d.solvers.seepage` es el objeto de `ogr_core.fem`;
  - **los flujos del solucionador son la función del núcleo:** los mismos números, exactamente, y los mismos
    que el campo resuelto;
  - **un modelo con malla, campo y etapas se carga sin el motor:**
    - en un intérprete nuevo, `Project.load` no trae ni `ogr_fem2d` ni `ogr_slip2d` a `sys.modules`;
    - las velocidades son los flujos del solucionador sobre lo guardado, cifra a cifra;
  - una malla y un resultado pasados por pickle vuelven con la misma clase;
  - el cargador ya no importa `ogr_fem2d`.

**Con el código de 0.1.341 fallan los 5.** El del intérprete nuevo enseña allí `ogr_fem2d` y sus
submódulos cargados.

## 3. Verificación

- **El test de esta versión**, 5/5.
  - A la primera falló uno: exigía la velocidad del campo en memoria, y la del archivo nunca lo fue
    (sección 0).
  - El cargador sin motor ya pasaba entonces.
- **Los vecinos:** 303 casos de la filtración, el transitorio, la malla, el agua, el consejo sin
  convergencia y el censo de capas. El único fallo fue esa suposición del test nuevo.
- **Comparación A/B, árbol contra árbol.**
  - Se cargaron con 0.1.341 y con 0.1.342 los dos modelos del banco que guardan una malla en su `.ogr`:
    02-010 `modelo_fem` y 02-102.
  - Salen idénticos el `to_dict`, las presiones intersticiales y las velocidades restauradas.
  - Los demás modelos de filtración generan la malla con su script al construirse, así que no la tienen
    guardada.
- **Suite entera:** 6371/6371, `EXIT=0`, 74 min.
- **Banco:**
  - `verificar_cierres.py` entero: 86 comprobaciones, 0 bajadas;
  - D337, con su tercera parte apuntada;
  - instantánea `Evaluaciones/0.1.342`, prompts (34) y auditorías con 0 ERROR.
- **Ningún número del motor cambia:** el código se mueve palabra por palabra, y el solucionador llama a la
  misma función que antes llevaba dentro.

## 4. Pendiente

- **0.1.343:** los objetos de foco y `SlipCircle` bajan al núcleo (D337).
