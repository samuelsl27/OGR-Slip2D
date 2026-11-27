# OGR Slip2D v0.1.497

**D440: un registro sísmico elegido que no está en el proyecto se dice con su id.** Hasta esta
versión, la corrida decía «no seismic record is selected» también cuando sí había uno elegido,
solo que el proyecto no tenía ningún registro con ese id. No cambia ningún número: en los dos
casos no se integra nada, como antes.

## 0. Lo que se encontró

- **La medida de la ficha, repetida con 0.1.496** (`_auditoria/P10_D439_D440/medir_d439_d440.py`):
  el plano de `test_newmark_user_surfaces_v1429` con su registro y `record_id = "nope"` da
  `method.newmark_no_record`, «no seismic record is selected». Idéntico a 0.1.485 y 0.1.451.
- **Los caminos por los que se llega**, medidos (paso 0 de la ficha):
  - borrar un registro en la ventana (`SeismicRecordsDialog.apply`) y con `seismic_record_delete`
    pasa por `ogr_core.project.rules.set_seismic_records`, que **limpia** `record_id` si el
    registro borrado era el elegido. No dejan el id colgando;
  - `settings_set` sobre `seismic.record_id` rechaza un id que el proyecto no tiene
    (`DYNAMIC_CHOICES` de `ogr_api/settings_schema.py`);
  - queda el `.ogr` editado a mano, y un test que vacíe la lista sin pasar por la regla (ver §2).
- **Dos cosas medidas y dejadas como están**, porque la propietaria eligió solo la nota:
  - `project_validate` no dice nada del id colgando (`can_run: true`, sin avisos);
  - la página Seismic de Project Settings enseña «(none)» en el combo y, al aceptar, escribe
    `record_id = ""` sin avisar. Desde ahí la corrida da la nota de siempre, que ya es verdad.

## 1. Qué cambia

- `ogr_slip2d/method_note_messages.py`: código nuevo `method.newmark_record_missing`
  (`NEWMARK_RECORD_MISSING`), con el id en el campo `record_id`. Solo hay id, no nombre, así que
  no va por `joined_name`.
- `ogr_slip2d/analysis_runner.py`, `_seismic_lines`: dos ramas. Con `record_id` vacío sigue
  `NEWMARK_NO_RECORD`, con su inglés de siempre. Con un id que el proyecto no tiene, la nota nueva.
  Es la regla común de la corrida y de `evaluate_surfaces` (D406), así que la dicen las dos.
- `ogr_gui/i18n/__init__.py`: su castellano.

## 2. Tests

- `tests/test_newmark_record_missing_v1497.py` (nuevo, 6 tests, en el plano de v1429): con
  `"nope"`, la nota nueva con el id, en la corrida y en `evaluate_surfaces`, y nada integrado; con
  `""`, `NEWMARK_NO_RECORD`; con el id del registro, ninguna de las dos y el plano se mueve
  (regla 7). Contra 0.1.496 fallan 3 de 6.
- `tests/test_method_notes_v1348.py`: la muestra del código nuevo en `_V1347`.
- Cambiado a propósito: `tests/test_surface_evaluate_seismic_v1451.py`. Su caso «sin registro»
  vaciaba `seismic_records` a mano y dejaba `record_id` apuntando a un registro que ya no estaba:
  era el caso de D440, y ahora daba la nota nueva. Pasa por `set_seismic_records`, que es lo que
  hace el programa al borrar, y vuelve a probar el «ninguno elegido» que decía probar.
- Las áreas `newmark`, `method_notes`, `surface_evaluate_seismic`, `yield_acceleration`, `i18n`,
  `translation` y `seismic`: en verde.
- Banco: `d440()` en el `verificar_cierres.py` de la raíz.
