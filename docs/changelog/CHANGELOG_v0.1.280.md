# OGR Slip2D v0.1.280

**Una malla de elementos finitos guardada que ya no es la del modelo se
rechaza, en vez de calcularse con las propiedades hidráulicas por defecto
(D284).** Hasta esta versión, `project.fem_mesh` solo lo descartaban
*Generate* y *Reset*. Si se borraba o se sustituía un material, sus
elementos quedaban apuntando a un identificador que el solver no conocía, y
`SeepageSolver.props_for` los calculaba en silencio con
`HydraulicProperties()` (Constant, Ks 1e-6). Si se editaba la geometría, se
calculaba una malla de la geometría vieja.

## 0. Lo que se encontró

- **Cómo salió.** En la puerta de medida de D274, la primera corrida malló
  un proyecto y resolvió con las propiedades de otro (cada `construir()`
  crea materiales con identificadores nuevos). El 004 salió saturado entero
  (kr_min 1,0) y nada lo dijo.
- **Reproducido por el API** (`_auditoria/P6_0277/repro_d284.py` del
  banco). En una caja de 20 × 10, la región pasa de B (Ks 1e-7) a A
  (Ks 1e-5) con `material_delete(B, reassign_to=A)`:
  - 190 de 190 elementos quedan huérfanos;
  - el caudal sale 3e-6 (el Ks por defecto) en vez de 3e-5;
  - un factor 10, sin una nota.
- **Era más ancho que eso.**
  - Dejan elementos huérfanos `material_delete`, `model_define`, que con
    `replace` deja huérfanos TODOS los elementos, y el diálogo de
    materiales de la ventana.
  - Ninguna edición de la geometría descarta la malla. El lienzo mueve
    vértices en sitio y sin notificar (`Project.regions_frozen` lo
    explica), así que un contador de revisiones no serviría.
  - El acoplamiento con el equilibrio límite interpola por geometría y no
    mira el material del elemento.

## 1. Qué cambia (decisión de la propietaria: firma y rechazo)

- **`rules.fe_model_signature(project)`** es la huella de lo que se malla:
  las regiones resueltas, con su contorno, sus huecos y el material de cada
  una.
  - `generate_mesh_for_project` la guarda en `mesh.notes["model_signature"]`,
    que viaja en el `.ogr` con las demás notas.
  - Cambiar una permeabilidad no la cambia, porque las propiedades se leen
    al resolver. Guardar y abrir tampoco.
- **`rules.mesh_mismatch(project)`** dice por qué la malla no es la del
  modelo, o devuelve None. Hace dos comprobaciones:
  - elementos de un material que ya no existe, en cualquier malla, también
    las guardadas antes de esta versión;
  - la firma guardada frente a la del modelo, en las mallas de esta
    versión en adelante.
  - Sus dos frases son claves en inglés que la ventana traduce.
- **Las tres puertas rechazan:**
  - el API, con un `Conflict` en `groundwater_run` antes de mirar las
    condiciones;
  - el motor, porque `solve_project_groundwater` lanza
    `AnalysisNotConfigured` (también por el camino del transitorio);
  - la ventana, con un mensaje en la barra de estado, sin calcular nada y
    sin ventana modal.
- **El solver, construido directamente** (un script, una medida), anota
  `default_props_elements` cuando algún elemento toma `default_props`. Es el
  patrón de la nota de triángulos planos de D270, y pasa a la respuesta del
  API.

## 2. Tests

`tests/test_mesh_signature_v1280.py`, 13 casos:
- **Rechazan:** el material borrado, `model_define`, una región pintada con
  otro material, un vértice movido en sitio y una malla sin firma (solo con
  la comprobación de huérfanos).
- **No rechazan:** una permeabilidad nueva y guardar y abrir.
- **Las tres puertas rechazan.**
- **La nota del solver** aparece.
- **El caudal de Darcy, tras regenerar la malla:** q = K·Δh/L·H con el Ks del
  material de la región, a 1e-6 relativo. La tolerancia es la escala a la que
  el registro de nodos del mallador cuantiza las coordenadas: el borde
  derecho queda en x = 19,99999998.

**Un test existente cambia.** `test_transient_initial_state_v1270::TestTheWarningReachesTheCaller._project`
armaba un `Project()` sin materiales con una malla hecha a mano de material
«m». Es exactamente lo que ahora rechaza la ventana: la primera suite falló en
`test_the_transient_summary_carries_it` con «1104 element(s) of the mesh belong
to a material that no longer exists». El *fixture* pasa a darle al proyecto el
material «m». El test sigue comprobando lo suyo, el aviso del permanente en la
barra de estado.

## 3. Verificación

- **A/B árbol contra árbol** (`_auditoria/P6_0280/ab_arbol.py`, 0.1.278 frente
  a 0.1.280): 75 filas, 0 distintas y ninguna clave de nota nueva. Las mallas
  del banco se generan al momento y todos sus elementos tienen material, así que
  `default_props_elements` no aparece.
- **Suite entera:** 5851 / 5851, con código de salida del proceso 0.
- **El test nuevo en el árbol de 0.1.277:** fallan los 13 (no existen ni
  `rules.mesh_mismatch` ni la firma).

**D278, en el banco y sin tocar el programa:**
- La primera etapa (4,6 s) del 05-020 no convergía porque el script no fijaba
  `max_picard`, y los pasos 2–4 piden 31 pasadas frente a las 30 del solver.
- Medida en `_auditoria/P6_0280/medida_d278.py`: con 100 o 300 converge, con
  una pasada máxima de 31, y con 80 pasos de tiempo bastan 29.
- El script pasa a `max_picard=100`, como el 017–019. La primera etapa se
  mueve como mucho 2,5e-8 m.

## 4. Lo que no se ha probado

- La prueba manual en la ventana: borrar un material o mover un vértice con
  la malla hecha, y pulsar *Compute*.
