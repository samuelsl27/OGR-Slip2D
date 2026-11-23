# OGR Slip2D v0.1.483

**D395: PySide6 6.12.0 queda excluida en Python 3.11.** El fallo no es del programa: en Linux, la
ligadura de PySide6 6.12.0 quita una referencia a `None` en casi cada setter de `QGraphicsItem`.
En 3.11 `None` no es inmortal todavía (PEP 683 lo hace inmortal en 3.12), y el intérprete aborta
con `none_dealloc` tras unas decenas de redibujados de un modelo calculado. No se mueve ningún
número del programa, ni el suelo de Python.

## 0. Lo que se encontró

Ficha D395, abierta en 0.1.422 al bisecar D370. La propietaria había decidido medir antes de
decidir (2026-11-04).

- **La ficha llevaba datos que no salían de su medida.** La sonda de 739885e
  (`tests/_d370_none.py`) corría todos los candidatos en un solo proceso. En 3.11 abortó con 134
  tras los dos primeros (run 41707080912: `QGraphicsLineItem.setPen` y `QGraphicsRectItem.setPen`,
  −1 por llamada, y luego `Fatal Python error`). El resto de candidatos «a 0», incluido el path
  item, y el redibujado «de unas 1500» no salen de ese run en 3.11. Los que sí da para los demás
  candidatos son de 3.12, donde `None` es inmortal y el contador no se mueve.
- **Por eso un comentario de `canvas_view.py` decía algo falso.** v0.1.427 escribió que no se había
  medido si un `QGraphicsPathItem` pierde referencias, y era verdad. v0.1.428 lo «corrigió» con la
  ficha: según eso, el path item daba 0. **No es así:** también pierde una. Corregidos aquí ese
  comentario y los dos que apoyaban en él la elección de path items (líneas de las polilíneas del
  usuario, rayos de Sarma y vista previa del ángulo). Los path items se quedan: son menos objetos
  y menos llamadas. Pero no protegen de D395.
- **En Windows no aparece.** Con Python 3.11.18 (de uv) y las ruedas `cp310-abi3-win_amd64` de
  6.12.0, 6.11.3 y 6.10.3, en entornos desechables fuera del proyecto, la sonda da 0 por llamada en
  todos los setters. El medidor funciona: un `Py_DecRef(None)` deliberado da −1. Este PC no tiene
  Linux (ni WSL ni Docker), así que la medida en Linux se hizo con una rama corta.
- **Medida en Linux** (run 45127694244, rama `dev/d395-medida`, archivada en la etiqueta
  `archivo/dev-d395-medida` y borrada): Python 3.11.18 en tres trabajos, uno por versión de
  PySide6, con cada candidato en su propio subproceso para que un aborto no tape el resto.

  | Linux, Python 3.11.18 | 6.12.0 | 6.11.3 | 6.10.3 |
  |---|---|---|---|
  | `setPen` de line, rect, path, polygon y ellipse item | −1 por llamada | 0 | 0 |
  | `setBrush`, `setPos`, `setZValue`, `setToolTip`, `setVisible`, `setLine`, `setRect`, `QPen.setWidthF` | −1 | 0 | 0 |
  | `addItem`, `addLine`, `addRect`, `pen()`, `QPen(QColor)` | 0 | 0 (`addItem` +1) | 0 (`addItem` +1) |
  | ejemplo: un redibujado sin calcular | −73 | +1167 | +1167 |
  | ejemplo: un redibujado tras calcular | −9616 | +2073 | +2073 |
  | 5000 redibujados seguidos | **aborta (134) hacia el 880** | sin abortar | sin abortar |
  | cargar, calcular, interpretar y cerrar | **aborta (134) al cerrar** | sale con 0 | sale con 0 |

  Con el modelo calculado, ~455 000 referencias a `None` dan para unos 47 redibujados, y en uso
  normal cada zoom y cada edición redibujan. Un usuario de Linux con 3.11 y 6.12.0 vería cerrarse
  el programa sin mensaje en pocos minutos.
- **De paso:** con las versiones buenas, el contador de `None` crece unas 1167 referencias por
  redibujado, en Windows y en Linux, sin que crezcan los objetos que sigue el recolector ni los
  elementos de la escena (352 antes y después). Es una referencia de más que da la ligadura, no
  una fuga de objetos. Para `None` no hace daño: el contador no llega a desbordarse. No se abre
  ficha.
- macOS queda sin medir: la CI no tiene ese sistema y la propietaria no lo pidió.

## 1. Decisión de la propietaria (2026-11-23)

De las tres opciones de la ficha: **excluir 6.12.0 por debajo de 3.12, en todas las
plataformas**. En Windows no hace falta, pero macOS no está medido, y una regla por plataforma
deja expuesto justo lo que no se ha visto. Se descartaron excluir solo en Linux, subir el suelo a
3.12 y solo documentarlo. La rama de la medida se archivó en una etiqueta y se borró («solo vive
main»).

## 2. Lo que cambia

- `pyproject.toml`: `PySide6>=6.6,!=6.12.0; python_version < '3.12'` y `PySide6>=6.6;
  python_version >= '3.12'`, con el porqué y la corrida en el comentario. La CI de 3.11 se
  instala sola una buena (hoy la 6.11.3, la última que permite).
- `README.md`: una línea en los requisitos, con cómo arreglar un entorno que ya tenga 6.12.0.
- `ogr_gui/canvas/canvas_view.py`: los tres comentarios de D395 (solo comentarios).
- Versión en los siete sitios.

## 3. Tests

`tests/test_pyside_none_refcount_v1483.py`, 4 casos:

- **la exclusión** (3): 6.12.0 excluida con `python_version < '3.12'`, solo ahí, y las dos
  entradas cubren cualquier Python con el mismo suelo;
- **la identidad** (1): con `None` mortal, catorce setters que usa el lienzo dejan su contador
  exactamente donde estaba (50 llamadas cada uno, pocas para que una ligadura mala no lo lleve a
  cero). Con `None` inmortal se salta diciendo por qué. Así la CI de 3.11 cazaría una 6.12.x mala
  futura que la exclusión no nombre.

Comprobado en entornos desechables de Python 3.11.18: en Windows pasa con 6.12.0 (allí no hay
fallo) y en el `.venv` (3.14) se salta. Con un mutante que hace que el `setPen` de
`QAbstractGraphicsShapeItem` quite una referencia a `None` (un `sitecustomize` con
`ctypes.pythonapi.Py_DecRef`), falla y nombra rect, path y ellipse con −1.

## 4. En el banco (fuera de git)

`d395()` en el `verificar_cierres.py` de la raíz, registrada en `COMPROBACIONES`: lee el
`pyproject.toml` del árbol (exclusión, marcadores y suelo), este changelog (corrida, etiqueta y
versiones buenas) y el test. Sale **CUBIERTO POR TEST**.
