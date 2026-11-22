# OGR Slip2D v0.1.479

**Los tests de DXF escriben en una carpeta temporal propia, no en `/tmp`.** Solo cambian tests: ni el
programa ni un número se mueven.

## 0. Lo que se encontró

- Tres archivos escribían y leían en la ruta fija `/tmp`, que en Windows es `C:\tmp`:
  - `tests/test_dxf_import_v146.py`: `_DXF`, y además dos rutas que **no deben existir**
    (`/tmp/definitely_absent.dxf`, `/tmp/absent.dxf`), las de los casos del archivo ausente. Si un
    día existieran, esos casos dejarían de probar lo que dicen.
  - `tests/test_dxf_problems_v147.py`: `_MESSY` y `_CLEAN`.
  - `tests/test_dxf_export_v148.py`: `_OUT`.
- Va contra «Dónde y cómo van los tests nuevos» de AGENTS.md por dos motivos: `C:\tmp` no tiene por
  qué existir (en el PC del 2026-11-22 se creó a mano), y dos tramos de `--jobs` que coincidieran
  compartirían los mismos archivos.
- En `C:\tmp` quedan además `ogr_not_a_dxf.txt` y `ogr_test_model.dxf`, que no son de esta suite:
  los escribe `tests/test_dxf_reader_v144.py` de **OGR-Core**, el mismo defecto que allí dio 22
  fallos hasta crear la carpeta. Se arregla en OGR-Core; aquí no se toca.

## 1. Cambios (solo tests)

- Cada uno de los tres módulos crea al importarse su carpeta con `tempfile.mkdtemp`
  (`ogr_dxf_import_…`, `ogr_dxf_problems_…`, `ogr_dxf_export_…`), la borra con `atexit`, y todas
  sus rutas, también las ausentes, cuelgan de ella.
- Fuera de Windows, el runner termina con `os._exit` (desde v0.1.377) y el `atexit` no corre: en la
  CI quedan tres carpetas vacías o casi en el temporal del sistema. Se acepta: es el temporal del
  sistema y no una ruta fija.

## 2. Qué se probó

- Los tres archivos con `C:\tmp` **renombrada** durante la corrida: 79 casos, 79 pasan, sin fugas,
  y `C:\tmp` no se vuelve a crear. Después se restauró, porque OGR-Core todavía la necesita.
- `grep` de `/tmp` en `tests/`: ninguna.
- Suite entera, `--jobs 4`: ver §3.

## 3. Suite

Suite entera con `--jobs 4`, fuera de pantalla, en el `.venv` (`shared: ogr_core 0.2.2 …
(installed, no git tree)`): **7548 casos, 7546 pasan, 0 fallan, 2 saltados**, sin fugas ni tramos
muertos, código de salida 0 (`SERIAL RUN DUE`, como en la 0.1.478).
