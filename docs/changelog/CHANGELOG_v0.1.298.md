# OGR Slip2D v0.1.298

**Una región asignada a un material que ya no existe se dice, con su remedio,
por todas las puertas, y la ventana pregunta antes de calcular (D298).**
Primera versión de la tanda P8d (núcleo, API y MCP).

## 0. Lo que se encontró

- **Cómo se llega a ese estado.** Hasta 0.1.285, *Definir materiales* quitaba un
  material en uso y dejaba sus regiones apuntando a él (D287, corregido en
  0.1.286). Un `.ogr` guardado entonces lo conserva.
- **Por qué no se notaba:**
  - `resolve_regions` copia el `material_id` sin comprobarlo, y `material_at` da
    None en esa región;
  - el trozador rechazaba toda superficie que la cruzara como «fuera del
    contorno exterior»;
  - `project_validate` decía que el modelo podía calcularse.
- **Medido** (`_auditoria/P8_interfaz/repro_d298.py`):
  - `can_run: true`, sin avisos;
  - Bishop y Janbu sin factor, cuando el modelo sano da 1,5866 y 1,4885;
  - la nota, «1562 surfaces were discarded because a slice base fell outside the
    External Boundary … the surfaces left the model».
- **Censo:** de los 264 modelos del banco, ninguno tiene una región así. No se
  mueve ningún número.
- **Decisión de la propietaria:** avisar, decir qué está mal y qué cambiar, y
  dejar calcular igualmente. No bloquear.

## 1. Qué cambia

- **`ogr_core/project/rules.py`:**
  - `orphan_assignments(project)`: las asignaciones cuyo material no está;
  - el aviso `ORPHAN_ASSIGNMENT`, con el punto de la región y el remedio
    (*Propiedades > Asignar materiales*);
  - `in_orphan_region(project, x, y)`: distingue un punto en esa región de uno
    fuera del modelo.
- **`Project.region_material_id_at(x, y)`:** el id que resuelve una región,
  aunque ningún material lo tenga.
- **El trozador y la búsqueda:**
  - una base sin material dentro de una región huérfana es
    `REFUSED_ORPHAN_MATERIAL`, no `REFUSED_OUTSIDE_MODEL`;
  - la búsqueda la cuenta aparte (`_orphan_material`, en `_RUN_COUNTERS`, así
    que la rejilla en paralelo también la suma);
  - la nota dice «… a slice base fell in a region whose material no longer
    exists. Assign that region another material».
  - Solo se pregunta al rechazar una base, así que en un modelo sano no cuesta
    nada.
- **`run_analysis` y `evaluate_surfaces`** ponen el aviso el primero de sus
  notas.
- **`project_validate`** lo da como aviso, sin bloquear: `can_run` sigue siendo
  true.
- **La ventana:**
  - *Calcular* pregunta «… ¿Calcular de todos modos? Se descartará toda
    superficie que cruce esa región.», y No no calcula. Sin pantalla no
    pregunta;
  - al abrir un archivo así lo dice en la barra de estado.

## 2. Tests

`tests/test_orphan_material_v1298.py`, 8 casos:
- **la regla:** encuentra la asignación, y distingue un punto en la región
  huérfana de uno fuera del modelo y de uno en una región sana;
- **un modelo sano** no tiene ninguna;
- **`project_validate`** avisa sin bloquear;
- **el análisis** pone el aviso el primero, y sus notas nombran la causa real,
  sin «left the model»;
- **un modelo sano** no avisa de nada;
- **la ventana:** sin pantalla no pregunta; con pantalla pregunta, y con No no
  arranca ningún cálculo;
- **abrir un archivo así** lo dice en la barra de estado.

Con el código de 0.1.297 fallan siete.

## 3. Verificación

- **Suite entera:** 5940 / 5940, con código de salida del proceso 0.
- **`verificar_cierres.py` de la raíz:** `d298()` da CUBIERTO POR TEST;
  42 comprobaciones, ninguna bajada.
- **Tests de rechazos, notas y dominio de materiales** (4 archivos, 69 casos):
  verdes.
