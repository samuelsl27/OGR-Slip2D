# OGR Slip2D v0.1.486

**El núcleo fijado sube de `ogr-core` 0.2.2 a 0.2.7.** `pyproject.toml` pasa a fijar
`ogr-core @ git+https://github.com/samuelsl27/OGR-Core@v0.2.7` (etiqueta anotada `1b03b8f` →
`e1198dc`, comprobada en GitHub con `git ls-remote`). Lo pide la sesión de OGR-Core.

Según la §2 de los changelogs 0.2.3 a 0.2.7 del núcleo, **Slip2D no tiene que cambiar nada en el
código**. `git diff --stat v0.2.2 v0.2.7 -- ogr_core` (16 de los 55 commits entre las dos etiquetas) toca ocho archivos:

| Archivo | Qué es | Para Slip2D |
|---|---|---|
| `fem/refine.py` (nuevo, +1601) y `fem/messages.py` (+126) | Mallador de calidad y sus mensajes (0.2.5), arcos del PSLG (0.2.6) | No lo usa |
| `fem/mesh.py` (+109), `fem/__init__.py` | Medidas nuevas de calidad del triángulo y métodos añadidos a `Element` y `Mesh` | Solo añade: `generate_mesh` no cambia |
| `dxf/reader.py` (+228/−) | `keep_arcs` (apagada por defecto) y la lectura correcta de dos casos de bulge | **Aviso de salida**: §0 |
| `dxf/sanitiser.py` | Solo el docstring: un dibujo leído con `keep_arcs=True` pierde sus arcos al sanearlo | Nada: Slip2D lee aplanado |
| `testing/runner.py` (+34/−) | El runner compartido | Nada que pedir |

## 0. Lo que se encontró

**El aviso de la 0.2.7 no afecta a ningún DXF de Slip2D.** La importación de DXF da otra geometría,
la correcta, en dos casos. Un bulge de más de media vuelta (|b| > 1) llegaba antes como el arco menor
de la circunferencia simétrica. Una `POLYLINE` 2-D con bulge llegaba como cuerdas. En el resto de los
dibujos la salida no cambia, bit a bit. Antes de dar la subida por buena se ha hecho un censo con
`ezdxf` (regla 6): bulges con |b| > 1 en `LWPOLYLINE` y `POLYLINE`, y bulges distintos de 0 en las
`POLYLINE` 2-D.

- **El repositorio, `referencias/` y `historico/` no tienen ningún `.dxf`.** `referencias/` incluye
  el banco (`referencias/Ejemplos/…`).
- **En todo `C:\Desarrollo` hay un solo DXF**: `Slip2D/proyectos-mcp/prueba_gui_0355/H_export.dxf`,
  que exportó el propio programa (sus capas son las `OGR_*` del exportador). Tiene 4 `LWPOLYLINE` y 2 `TEXT`, ningún bulge con
  |b| > 1 y ninguna `POLYLINE` 2-D con bulge.
- **Fuera de `C:\Desarrollo`**: Documents, Desktop, `C:\Notas_IA` y `C:\OGR_Slip2D_MCP` no tienen
  ninguno. En Downloads hay dos, y son plantillas de GDAL de otro programa (`gdal/data/header.dxf` y
  `trailer.dxf`). `ezdxf.readfile` no las abre porque son fragmentos. Con `ezdxf.recover` salen sin
  entidades.
- **Los tests dibujan sus propios DXF**, con `add_lwpolyline` (7), `add_line` (5) y `add_circle` (1),
  y ninguno lleva bulge. Un grep de `xyb`, `bulge` y `add_polyline2d` en `tests/` y `ogr_*` no
  encuentra nada. El único `bulge` del programa está en el tooltip del diálogo de importación
  («Segments per full circle used to discretise arcs, circles, splines and polyline bulges»), que
  sigue siendo cierto.
- Conclusión: **nada de lo calculado en el banco ni en los ejemplos viene de una geometría que
  cambie**. Un `.ogr` guarda su geometría: volver a calcularlo no vuelve a importar el DXF. **No hay
  huella del banco que tomar.**

**Hay un «0.2.2» que se queda donde está.** `_PIN = {"ogr_core": "0.2.2"}` en
`tests/test_version_consistency_v176.py` es una fijación inventada para los casos de
`TestWhatTheCheckOfThePinAccepts`, «so that they say the same whatever this repository pins». Si se
cambiara, esos casos pasarían a probar una cosa distinta. Las menciones de `0.2.2` en
`tests/test_labels_spanish_v1321.py` están en docstrings: el patrón se construye con la versión del
núcleo importado.

## 1. Qué cambia

- **Fijación**: `pyproject.toml`, `@v0.2.2` → `@v0.2.7`, con una línea más en su comentario.
- **Entorno**: en el `.venv`, `pip install --no-deps --force-reinstall "ogr-core @ git+…@v0.2.7"`. El
  núcleo importado es `0.2.7`, de `.venv\Lib\site-packages`. La cabecera del runner dice
  `shared: ogr_core 0.2.7 … (installed, no git tree)`.
- **`AGENTS.md`**: las dos menciones de la fijación pasan a 0.2.7, la del Stack y el ejemplo de
  cabecera. El archivo sigue teniendo 499 líneas.
- **Versión** en los siete sitios.

## 2. Pendiente, sin tocar

- **La recomendación de la 0.2.3 del núcleo**: el test de cabeceras de licencia que lee «todos los
  `.py`» no debería entrar en las carpetas ocultas. Hoy las carpetas ocultas del árbol, sin contar
  `.git` y `.venv`, son `.claude`, `.github` y `.vscode`, y ninguna tiene un `.py`: el test no falla.
  No se aplica en esta versión, para hacer una tarea a la vez. En `docs/consumidores.md` de OGR-Core
  sigue como «pendiente».
- **La fila de Slip2D en `docs/consumidores.md` de OGR-Core** se corrige allí, con el commit de esta
  versión. Hasta entonces, el trabajo `pins` de OGR-Core está en rojo, y es lo esperado.

## 3. Pruebas

- **Suite entera con `--jobs 4`, sin `--dev-core`, en el `.venv` y fuera de pantalla**: 7577 casos, 7575 pasan, 0 fallan, 2 saltados por la plataforma,
  sin fugas y sin tramos muertos. Código de salida 0. La cabecera dice
  `shared: ogr_core 0.2.7 …\.venv\Lib\site-packages\ogr_core (installed, no git tree)`. Última serie
  en verde: `7aff40b`, hace 13 commits, así que no toca serie.
- **Evidencia anterior**, de la sesión de OGR-Core:
  - la suite entera de Slip2D en `2cb7efd`, con `--jobs 4 --dev-core` contra un núcleo con el mismo
    `ogr_core` que la v0.2.7: 7575 de 7577, 2 saltados por la plataforma, sin fugas;
  - la CI de la PR 28 del núcleo, que corrió Slip2D contra la 0.2.7 final, en verde.
