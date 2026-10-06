# OGR Slip2D v0.1.262

**Una rejilla lanzada con *Compute* se reparte entre procesos como cualquier
otra, y si no puede, lo dice (D247).** En la demo, *Compute* pasa de 12,0 s
a 7,3 s, con el mismo número.

## 0. Lo que se encontró

### D247: la ventana calculaba toda rejilla en serie, en silencio

- **El síntoma.** `_parallel_grid_run` serializa `(search, project, …)` para
  cada lote. El proyecto de la ventana lleva en `_listeners` una lambda del
  lienzo (`CanvasView.set_project`) y un método de la propia ventana, y
  ninguno de los dos se serializa.
- **El fallo no se veía.** La función devolvía `None` ante cualquier
  excepción, y la búsqueda seguía en serie sin decir nada. Así que *Compute*
  ha calculado la rejilla en un solo proceso desde que existe la búsqueda en
  paralelo.
- **Medido hoy con una `MainWindow` offscreen:** de los atributos del
  proyecto de la ventana, **solo `_listeners`** no se serializa. Una copia
  superficial con los atributos de `copies.NOT_COPIED` vacíos se serializa
  (5,6 KB en la demo) y deja intactos los oyentes del original.
- **La decisión** venía del plan de la tanda P5 (la propietaria, el
  2026-10-04): la búsqueda manda una copia superficial sin `NOT_COPIED`, con
  una receta nueva en `copies.py` y las cachés calientes.
- **Al planificar salió una segunda cosa.** Con `spawn`, cada proceso hijo
  reimporta el módulo principal del padre. Con `python -m ogr_gui`, ese
  módulo era `ogr_gui/__main__.py`, que importaba PySide6 y la ventana al
  cargarse: **1,43 s por proceso** antes de hacer nada.

## 1. Lo que cambia

- **`ogr_core/project/copies.py`: `shippable_copy(project)`.** Es un
  `copy.copy` con `_listeners = []` y `_gw_solver = None` en la copia.
  - Las cachés de regiones viajan calientes.
  - Es superficial a propósito: comparte contornos y materiales con el
    original, así que no es para editarla. Sirve para serializarla al
    instante; todo lo demás usa `detached_copy`.
- **`_parallel_grid_run`.**
  - Los lotes llevan esa copia, hecha una sola vez.
  - **Si el pool falla igualmente, la búsqueda lo dice**: «The Grid Search
    was to be split across N processes and ran in one, because the process
    pool failed (<tipo>: <mensaje>)». La nota llega a la ventana, a la CLI y
    a la API.
  - Pocos centros para los procesos no es un fallo, y sigue sin nota.
- **`ogr_gui/__main__.py`.** PySide6, la ventana y el tema se importan dentro
  de `start_window` y `main`, así que un proceso hijo que reimporta el módulo
  ya no carga la interfaz. `main()` empieza con
  `multiprocessing.freeze_support()`, que no hace nada fuera de un ejecutable
  compilado; hoy no existe ninguno.
- **`_ComputeWorker` no cambia.** La puerta es la búsqueda, como se decidió,
  y así sirve igual a la API y a los scripts.

## 2. La medida

**El tiempo de *Compute* en la demo**, desde una `MainWindow` offscreen, por
el `_ComputeWorker` como hilo real. Es un A/B en el mismo proceso, espalda
con espalda (`_auditoria/P5_0262/tiempo_compute_d247.py`), en el que la
corrida B reproduce 0.1.261 haciendo que `shippable_copy` devuelva el
proyecto tal cual:

| corrida | tiempo | rejilla | Bishop | Janbu |
|---|---|---|---|---|
| A (0.1.262) | 7,26 s | repartida | 1,0914331494631124 | 1,0434262254619202 |
| B (0.1.261) | 12,04 s | en serie, con la nota | idéntico | idéntico |
| A′ (control) | 6,64 s | repartida | idéntico | idéntico |

- **La medida resuelve:** los dos controles difieren en 0,6 s y el efecto es
  de unos 5 s.
- **La nota de la corrida B** nombra la causa que antes se tragaba:
  `TypeError: cannot pickle 'MainWindow' object`.

## 3. Tests

**`tests/test_window_grid_parallel_v1262.py`, 6 casos:**
- **la premisa** con una ventana real: su proyecto no se serializa y la copia
  sí, sin tocar sus oyentes;
- **la rejilla del proyecto de la ventana se reparte y responde como en
  serie**, bit a bit (`evaluations`, cuentas, crítica y notas), por la
  búsqueda y por el `_ComputeWorker` como hilo real;
- **el pool roto da el mismo número y una nota**, y el sano no da ninguna;
- **un intérprete nuevo que importa `ogr_gui.__main__` no carga PySide6.**

Se saltan en una máquina de un solo proceso.

**Discriminación** contra un `git archive` de 0.1.261 (557fc58): fallan 5 de
6. Pasa el control del pool sano. En 0.1.261, el espía ve que el reparto
devuelve `None` (`[False]`).

**Selección:** 13 archivos, 190 casos (búsqueda en paralelo, estadística,
ventana, coherencia de versión, copias y los de 0.1.261).

## 4. Banco, el mismo día (sin versión de motor)

- **D243 cerrada** (decisión de la propietaria: «contradicción; objetivo la
  figura»).
  - La tabla 109.2 tiene la huella de un círculo: su Spencer/Bishop es
    1,0022, el del circular del 108.
  - El objetivo no circular del 109 es la figura 109.2, Bishop 1,516.
  - El 109 con los extremos libres reproduce la tabla no circular del 108 a
    menos del 0,75 % y la figura a +0,19 %.
  - La fila queda a +42,7 % con el flujo del banco, que optimiza con los
    extremos fijos. Esa distancia es **D264**, abierta para medir antes de
    decidir.
- **D245 cerrada como premisa refutada y absorbida en D264.** El 15, con
  cinco semillas y los extremos libres, llega al manual (Janbu simplificado
  0,3942–0,4004 frente a 0,396) sin tocar la heurística de la Path Search.
  Con los extremos fijos queda entre +1,4 y +10 %.
- **D247 se cierra en el banco con esta versión** (`d247()`, CUBIERTO POR
  TEST).

## 5. Lo que queda sin probar

**La prueba manual en la aplicación real.**
- *Compute* lanzado desde `ogr-slip2d.exe` (el *console script*) y con
  `python -m ogr_gui`, con una rejilla de más de 400 círculos.
- Que no aparezca la nota de «ran in one».
- Que no se abran ventanas de más.
- Que el número sea el mismo que en serie.
