# OGR Slip2D v0.1.381

**La última versión de tests: cinco archivos dejan de repetir corridas iguales.**
- **Medido:** solos y juntos pasan de 181,8 s a **116,1 s (−36 %)**, con los mismos 85 tests.

| Archivo | Antes (s) | Después (s) |
|---|---:|---:|
| `test_reverse_curvature_v182` | 32,2 | 12,6 |
| `test_published_cases_v179` | 47,5 | 33,4 |
| `test_slope_search_v117` | 22,8 | 16,8 |
| `test_multimodal_v1126` | 49,5 | 35,1 |
| `test_user_surfaces_v1157` | 29,7 | 18,1 |

Es la V4 de la fase 3 de la auditoría del cómputo (`docs/audits/AUDITORIA_COMPUTO_v0.1.377.md`). Cierra el
bloque de tests: V1–V4 ahorran 282 s en los archivos solos, frente a los ~295 estimados. **Ningún módulo del
programa cambia**, salvo el número de versión.

## 0. Lo que se encontró y lo que se decidió

- **Las decisiones de la propietaria (2026-10-30):**
  - V4;
  - **las dos corridas de un test de reproducibilidad se calculan en su momento**: ninguna sale del memo;
  - **de las rejillas grandes se guarda un resumen, no el resultado**: 4851 círculos de reverse_curvature y
    8788 de 30 dovelas del caso 004 vivirían hasta el final del proceso.
- **Lo que se comparte, y en qué forma:**
  - **`test_reverse_curvature_v182`:** la rejilla por defecto de 4851 círculos sobre Ej_1, con las grietas
    de curvatura inversa encendidas, que es el valor por defecto. La leen cuatro tests, uno de ellos el lado
    «encendido» de la regla 7. Se guarda lo que leen: los recuentos, el número de evaluaciones y el círculo
    crítico (factor, superficie y si es de curvatura inversa). El lado «apagado» conserva su corrida.
  - **`test_published_cases_v179`:** la rejilla declarada del caso 004. Dos tests leen solo su factor crítico,
    y eso se guarda.
  - **`test_slope_search_v117`:** el Slope Search de 1500 superficies con semilla 42. Dos tests leen su factor
    y su centro, y eso se guarda. Cada uno sigue comparando con su propia rejilla, que son distintas.
  - **`test_multimodal_v1126`:** dos corridas del enjambre sobre el modelo con cu2 = 90. La de varios mínimos
    tiene cuatro lectores; la de los valores por defecto (un mínimo y el algoritmo mejorado), tres, uno de
    ellos el lado «encendido» de la regla 7 del algoritmo mejorado. Se guardan los mínimos y el resultado
    crítico, no las evaluaciones del enjambre.
  - **`test_user_surfaces_v1157`:** las corridas que solo leen un proyecto recién construido, en uno de cuatro
    estados: sin superficie, con la ganadora, con una lejana o con la ganadora en análisis no circular.
- **Lo que conserva su corrida, porque su sentido es el mismo objeto o el cambio de un mismo proyecto**, todo
  ello en `test_user_surfaces_v1157`:
  - las dos puertas sobre un proyecto;
  - quitar la superficie y recuperar el mínimo exacto;
  - la pareja que demuestra inerte un proyecto sin superficies;
  - el círculo guardado sin extremos tras correr;
  - la misma superficie dos veces.

  Y, en todos los archivos, los lados «apagado» de la regla 7, las corridas con su propia semilla u opción, y
  los tests de reproducibilidad.
- **Un error mío, cazado al medir:** el resumen de la rejilla de reverse_curvature omitía un dato que leía un
  test, si el círculo crítico es de curvatura inversa. El test falló con `AttributeError` y el dato entró en
  el resumen. Es la razón de guardar solo lo que se lee: un dato que falta no pasa en silencio.
- **Finales de línea:** cuatro de los cinco archivos tenían CRLF en la copia de trabajo, y `test_multimodal_v1126`
  los tenía mezclados. El índice de git los guarda en LF (`eol=lf` en `.gitattributes`), y el commit los deja
  así.
- **La ganancia, medida.** Los cinco archivos solos, antes y después, seguidos y con `TEMP`/`TMP` redirigidos:
  181,8 s → 116,1 s (−65,7 s).
  - **Según la proyección calibrada del informe:** esta versión baja la serie ~1,1 min, `--jobs 4` ~0,5 y
    `--fast` ~0,1, porque `test_slope_search_v117` corre en `--fast`.
  - **Con V1–V4 medidas:** la serie queda en ~63,9 min, `--jobs 4` en ~32,8 y `--fast` en ~12,6.
- **La guarda (`test_shared_test_caches_v1378`) no encuentra alcances nuevos** (12 de 12).
- **La huella del banco de pruebas no aplica:** ningún módulo `ogr_*` cambia salvo la línea del número.

## 1. Qué cambia

- `tests/test_reverse_curvature_v182.py`, `tests/test_published_cases_v179.py`, `tests/test_slope_search_v117.py`,
  `tests/test_multimodal_v1126.py` y `tests/test_user_surfaces_v1157.py`: un `_SHARED` local y sus `_shared_*`.
- El número, en los nueve sitios.

## 2. Qué se probó

- Los cinco archivos solos, antes y después: 85 de 85. Tras el arreglo del resumen, `test_reverse_curvature_v182`
  solo: 14 de 14.
- `test_shared_test_caches_v1378` solo: 12 de 12.
- La suite entera con `--jobs 4`: **6724 de 6724, `Failed: 0`**, sin `Leaks` ni `Chunks died`, en 27,7 min (el reloj
  de una sola corrida no mide la ganancia). La última serie en verde fue `8c4dcd3`, hace 5 commits.
- **Sin correr:**
  - la serie entera, que no toca;
  - la huella de los 23 casos, porque no aplica.

## 3. Lo que queda

- **El arreglo de la clave de `_det`** de `test_probabilistic_all_failed_v1169`, decidido para después de V4.
  Quitaría de la lista blanca de la guarda sus dos entradas latentes.
- **`tests/_slow.txt`,** que la propietaria decide tras dos corridas enteras con `--jobs 4`. Con lo compartido,
  `test_reverse_curvature_v182` y `test_fos_chart_v1308` bajarían de los 45 s.
- **Después, las versiones del motor (V5–V18)**, cada una con su OK.

## Archivos

- `tests/test_reverse_curvature_v182.py`
- `tests/test_published_cases_v179.py`
- `tests/test_slope_search_v117.py`
- `tests/test_multimodal_v1126.py`
- `tests/test_user_surfaces_v1157.py`
- `docs/changelog/CHANGELOG_v0.1.381.md` (nuevo)
- `pyproject.toml`, `ogr_gui/main_window.py` y los `__init__.py` de `ogr_core`, `ogr_slip2d`, `ogr_fem2d`,
  `ogr_gui`, `ogr_cli`, `ogr_api` y `ogr_mcp` (el número)
