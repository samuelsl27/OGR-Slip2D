# OGR Slip2D v0.1.507

**D443: convertir o borrar un contorno lleva consigo los enlaces de los materiales, por la regla del
núcleo, en la ventana y en el agente, y se dice.** La regla es la B, decidida por la propietaria el
2026-11-27, y está en OGR Core 0.2.14 (`relink_on_conversion`, `unlink_on_removal` y
`stale_surface_links`). Slip2D la fija desde 0.1.505.

## 0. Lo que se encontró

- **El defecto, medido con 0.1.455** con el guion del banco `_auditoria/P10_D443_D444/medir_d443_d444.py`:
  - el nivel freático del talud de ejemplo convertido en línea piezométrica deja u en (25; 0,5) en
    0 kPa, donde antes era 73,6. Pasa por las dos puertas y nadie lo dice;
  - una superficie anisótropa convertida en capa débil deja su enlace colgando;
  - el control: el Borrar del agente limpia el enlace y lo dice.

  El test nuevo lo reproduce contra 0.1.506: fallan 6 de sus 11 casos.
- **El Borrar de la ventana tampoco limpiaba nada.** Dejaba los materiales apuntando a un contorno
  que ya no estaba. La limpieza vivía solo en el agente, escrita a mano (`ogr_api/ops/model.py`).
  Ahora las dos puertas preguntan la misma función del núcleo.
- **El orden importa.** Un material sin `water_surface_id` lee el primer nivel freático del modelo
  (la vuelta atrás). El núcleo lo encuentra a través del contorno, así que los enlaces se tocan antes
  de quitar o sustituir el contorno, y en el mismo paso de deshacer.

## 1. Qué cambia

- `ogr_api/link_notes.py` (nuevo): `link_change_notes`, el único sitio que escribe las notas de los
  cambios:
  - para lo limpiado, las frases que ya decía el agente («Materials that used it now have no water
    surface: …» y «'X' lost its anisotropic surface.»);
  - para lo que sigue al contorno, una nueva: «Materials that used it now read it as a Piezometric
    Line: …».

  La ventana le pasa su `tr` y su nombre del tipo; el agente lee el inglés.
- `ogr_gui/main_window.py`:
  - `_apply_conversion` (los dos Convertir) y `_do_delete_boundary` hacen el cambio de enlaces y el
    contorno en un solo paso de deshacer. Es un `MacroCommand` con el `SnapshotCommand` de los
    materiales y el comando de siempre, así que Deshacer devuelve el contorno y el enlace a la vez,
    y Borrar sigue devolviendo el mismo objeto;
  - la barra añade las notas, y en ese caso dura 8 s;
  - `_with_link_notes` es nuevo.
- `ogr_api/ops/model.py`:
  - `boundary_edit` con `op="delete"` usa `unlink_on_removal`;
  - con `op="change_type"` usa `relink_on_conversion`, después de todas las comprobaciones de la
    edición (el paso es atómico de todos modos).

  Las dos escriben sus `notes` con `link_change_notes`.
- `ogr_api/ops/project.py`: `project_validate` avisa con `stale_surface_links` (con código) de un
  enlace que un `.ogr` viejo trae a un contorno de un tipo que no lo lee.
- `ogr_gui/i18n/__init__.py`: el castellano de las tres frases.
- `docs/mcp/herramientas.md`: `boundary_edit` lo dice.

El rechazo nuevo del núcleo, convertir una superficie anisótropa que lee una junta, llega por el
camino que ya tenían los dos Convertir.

## 2. Lista de comprobación de la guía de interfaz

- Mensaje: la barra dice qué ha pasado con cada material, en el idioma del lector y con los términos
  del programa («superficie de agua», «superficie anisótropa»).
- Deshacer: un solo paso para el contorno y sus enlaces (test).
- Ninguna acción nueva, ningún diálogo modal en el camino que corre el test.
- Paridad entre puertas: la ventana y el agente dicen lo mismo, porque leen la misma regla y las
  mismas frases.

## 3. Tests

- `tests/test_conversion_links_d443_v1507.py` (nuevo, 11 tests, una ventana para todo el archivo):
  - la premisa;
  - el nivel freático hecho línea piezométrica, en la ventana y en el agente: u = γw·(8 − 0,5) =
    73,6 kPa, la solución cerrada del test del núcleo. Lo dicen la barra y las notas;
  - Deshacer lo devuelve todo;
  - un tipo sin lector limpia el enlace, en las dos puertas;
  - el Borrar de la ventana limpia, lo dice, y un solo Deshacer lo devuelve todo;
  - el Borrar del agente dice lo mismo que antes;
  - `project_validate` avisa de un enlace viejo, y el control no.

  Contra 0.1.506 fallan 6. Pasan la premisa, el Deshacer (allí no había nada que devolver), el Borrar
  del agente y el control.
- Áreas `convert`, `boundary`, `water`, `undo`, `anisotropic`, `i18n`, `translation`, `texts`,
  `terms`, `voice`, `budget`, `wrap`, `mcp` y `api`, con `--jobs 4`: 645 en verde.

## 4. Suite

La suite entera se corre al final de la tanda.
