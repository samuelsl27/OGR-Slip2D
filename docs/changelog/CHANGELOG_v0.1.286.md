# OGR Slip2D v0.1.286

**La ventana ya no quita un material que usan regiones o capas débiles
(D287).** El API ya lo rechazaba. *Definir materiales* lo quitaba sin decir
nada y dejaba las regiones apuntando a un material que no existe.

## 0. Lo que se encontró

- **La prueba de la interfaz** de 0.1.284
  (`_auditoria/P6_0284/INFORME_prueba_GUI_0.1.284.md`, H6): *Propiedades →
  Definir materiales…* → «− Quitar» sobre un material asignado. No hubo
  pregunta ni aviso, y la región quedó en gris.
- **Dos puertas, dos reglas.**
  - `material_delete` del API rechazaba borrar un material que usan regiones,
    capas débiles o rangos anisótropos (y ofrece `reassign_to` o `force`).
  - `MaterialPropertiesDialog._remove_material` solo miraba los rangos (D218b).
- **Lo que pasaba después** (`_auditoria/P8_interfaz/repro_d287.py`, dos
  materiales, uno por región):
  - el agua lo rechazaba bien, por D284;
  - el equilibrio límite se quedaba sin factor, cuando antes daba Bishop
    1,5866 y Janbu 1,4885, y lo explicaba con «1562 surfaces were discarded
    because a slice base fell outside the External Boundary … the surfaces
    left the model», que no es la causa.
- **Decisión de la propietaria:** rechazar con el motivo, como el API sin
  argumentos y como el diálogo ya hacía con los rangos. Las otras opciones
  eran ofrecer reasignar, o quitar y dejar las regiones sin asignar.

## 1. Qué cambia

- **La regla pasa a `ogr_core/project/rules.py`:**
  - `material_users(project, material_id, materials=None)` devuelve las
    asignaciones de región, las capas débiles y los rangos que usan un
    material;
  - `material_link_users` hace los rangos;
  - `material_region_uses(project)` da, por material, `(regiones, capas)`.
- **El API** (`material_delete`) la pregunta. Su comportamiento y su mensaje no
  cambian.
- **La ventana** construye el diálogo en un solo sitio
  (`MainWindow._materials_dialog`) y le pasa `material_region_uses`. El
  diálogo no sabe nada del proyecto, como con las superficies de agua.
- **`_remove_material`** rechaza en su propia etiqueta, sin nada modal: «X no se
  puede quitar: lo usan N región(es) y M capa(s) débil(es). Asígnales otro
  material primero.»
  - La clave es `rules.MATERIAL_IN_USE` y lleva su traducción.
  - El caso de los rangos (D218b) sigue con su mensaje.

## 2. Tests

`tests/test_material_in_use_v1286.py`, 6 casos:
- la regla cuenta regiones, capas débiles y rangos;
- el API sigue rechazando, con el mismo mensaje;
- el diálogo, construido como lo abre el menú, no quita un material que usa
  una región ni uno que usa una capa débil, dice por qué en su etiqueta y lo
  deja en la lista;
- un material que nadie usa se quita.

## 3. Verificación

- **Suite entera:** 5885 / 5885, con código de salida del proceso 0.
- **Tests de materiales, del diálogo y del API** (24 archivos, 509 casos):
  verdes antes de la suite entera.
- **`verificar_cierres.py` de la raíz:** `d287()` da CUBIERTO POR TEST;
  30 comprobaciones, ninguna bajada.

## 4. Lo que se abrió

- **D298:** una región cuyo material no existe pasa la validación y confunde al
  equilibrio límite.
  - **Medido:** `project_validate` da `can_run: true` sin avisos sobre el modelo
    de la reproducción, y el análisis se queda sin factor y culpa a las
    superficies.
  - **Desde esta versión** la ventana ya no crea ese estado, pero un `.ogr`
    guardado hasta 0.1.285 puede traerlo.
