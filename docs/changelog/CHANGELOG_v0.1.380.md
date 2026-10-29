# OGR Slip2D v0.1.380

**Los dos archivos de Overall Slope comparten las corridas que repetían.**
- **Medido:** `test_overall_slope_v137` y `test_surface_key_endpoints_v1237`, solos y juntos, pasan de 119,1 s a
  **88,6 s (−26 %)**, con los mismos 46 tests.
  - `test_overall_slope_v137`: de 73,6 a 47,5 s.
  - `test_surface_key_endpoints_v1237`: de 42,5 a 38,6 s.

Es la V3 de la fase 3 de la auditoría del cómputo (`docs/audits/AUDITORIA_COMPUTO_v0.1.377.md`). **Ningún
módulo del programa cambia**, salvo el número de versión.

## 0. Lo que se encontró y lo que se decidió

- **Las decisiones de la propietaria (2026-10-30):** V3, y **sin compartir `_det`**, la corrida determinista
  que se repite unas 19 veces y cuesta ~1,5 s en total.
- **Lo que se comparte en `test_overall_slope_v137`:**
  - `_run(n)` sobre un modelo Ej_1 recién construido, para n = 16, 10 y 14 (dos, cuatro y tres lectores);
  - el par Global Minimum / Overall Slope de `TestPhysicalInvariant` (dos lectores), **tal como lo calculaban
    sus tests**: el mismo objeto de variables pasa primero por el Global Minimum y luego por el Overall Slope.
    No se funde con `_run(n=16)`, que usa variables recién construidas: si el primero dejara algo escrito en
    las variables, serían cálculos distintos.
- **Lo que se comparte en `test_surface_key_endpoints_v1237`:** con la clave de hoy y fuera de cualquier
  parche de `P._surface_key`, la corrida `test_overall_slope_v137._run(n=16, wide=True)` (dos lectores) y el
  Overall Slope por defecto de las dos masas (dos lectores). Es un memo local que llama al `_run` de v137, no
  al memo de v137.
- **Lo que conserva su corrida:**
  - `test_project_is_not_modified`, cuyo sentido es el proyecto que le pasa a `_run`;
  - los lectores únicos;
  - toda llamada con su propia semilla u opción;
  - las corridas bajo la clave vieja, que son el contraste de la regla 7.
- **El ayudante sigue sin memoizar.** `_run` de v137 lo llama `test_surface_key_endpoints_v1237`, una vez con
  la clave parcheada.
- **La ganancia, medida.** Los dos archivos solos, antes y después, seguidos y con `TEMP`/`TMP` redirigidos:
  119,1 s → 88,6 s (−30,5 s).
  - **El diseñador estimaba ~41 s:** contaba compartir casi todas las búsquedas repetidas. Lo que queda
    calcula de nuevo a propósito, como se dice arriba.
  - **Según la proyección calibrada del informe:** la serie −0,5 min y `--jobs 4` −0,4 min. Con V1 y V2
    medidas, la serie queda en ~65,0 min y `--jobs 4` en ~33,4.
- **La guarda (`test_shared_test_caches_v1378`) no encuentra ningún alcance nuevo** (12 de 12): los memos
  nuevos son locales y nadie más los alcanza.
- **La huella del banco de pruebas no aplica:** ningún módulo `ogr_*` cambia salvo la línea del número.

## 1. Qué cambia

- `tests/test_overall_slope_v137.py`: `_SHARED`, `_shared_run()` y `_shared_gm_os()`; once tests leen lo
  compartido.
- `tests/test_surface_key_endpoints_v1237.py`: `_SHARED`, `_shared_v137_16()` y `_shared_overall_ab()`; cuatro
  lecturas.
- El número, en los nueve sitios.

## 2. Qué se probó

- Los dos archivos solos, antes y después: 46 de 46 las dos veces.
- `test_shared_test_caches_v1378` solo: 12 de 12.
- La suite entera con `--jobs 4`: **6724 de 6724, `Failed: 0`**, sin `Leaks` ni `Chunks died`, en 28,1 min (el reloj
  de una sola corrida no mide la ganancia). La última serie en verde fue `8c4dcd3`, hace 4 commits.
- **Sin correr:**
  - la serie entera, que no toca;
  - la huella de los 23 casos, porque no aplica.

## 3. Lo que queda

- **V4,** la última versión de tests: las rejillas, el enjambre y las superficies de usuario. Después, el
  arreglo de la clave de `_det` y las versiones del motor. Cada una con su OK.

## Archivos

- `tests/test_overall_slope_v137.py`
- `tests/test_surface_key_endpoints_v1237.py`
- `docs/changelog/CHANGELOG_v0.1.380.md` (nuevo)
- `pyproject.toml`, `ogr_gui/main_window.py` y los `__init__.py` de `ogr_core`, `ogr_slip2d`, `ogr_fem2d`,
  `ogr_gui`, `ogr_cli`, `ogr_api` y `ogr_mcp` (el número)
