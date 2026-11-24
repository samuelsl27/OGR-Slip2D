# OGR Slip2D v0.1.490

**La línea de órdenes dice por qué no puede abrir un `.ogr`, en una línea, en vez de acabar en una
traza de Python (D430).** `info` y `compute` leían con un `Project.load` sin ningún `except`.
Ahora pasan por `_open_project`, que llama a `ogr_api.ops.project.load_ogr`, el lector que ya
usan el agente y la ventana (D422). Imprimen `Cannot open project: <motivo>` y salen con 1. Ningún
número cambia: son archivos que la CLI no podía abrir.

## 0. Lo que se encontró

- **Medido otra vez antes de tocar nada** (regla 6), con 0.1.489 y ogr-core 0.2.10. Los seis casos
  de la ficha (`info` y `compute` × una carpeta `carpeta.ogr`, una raíz lista y un JSON cortado)
  salían con `EXIT=1` y una traza de 52 a 63 líneas. El código 1 lo daba la propia traza.
- **Los dos casos que la ficha no midió en la CLI**, bytes que no son UTF-8 y raíz `null`, daban
  lo mismo. Ahora dicen `UnicodeDecodeError: 'utf-8' codec can't decode byte 0xff …` y `… it is
  null, not an object.`, las frases de `load_ogr`.
- **`rich` partía el motivo en tres líneas.** Envuelve a 80 columnas cuando la salida no es una
  consola, y una ruta de `%TEMP%` ya ocupa media línea. Se imprime con `soft_wrap=True`: el
  criterio de la ficha es «el motivo en una línea», y un motivo partido es lo que un script no
  encuentra con grep.
- **`compute` no deja nada en `--output`** cuando la lectura falla, porque lee antes de escribir.
  Ahora lo comprueba el test.
- **Solo `info` y `compute` leen un `.ogr`** (`grep -n "Project.load" ogr_cli/`).

## 1. Qué cambia

- `ogr_cli/__main__.py`: `_open_project(path)`.
  - Si la ruta no existe, sigue el `File not found` con código 1.
  - Si `load_ogr` la rechaza, imprime `[red]Cannot open project:[/red]` y su `message`, sin el
    prefijo `[E_INVALID_ARGUMENT]` del agente, y sale con 1.
  - El 1 es decisión de la propietaria: «no existe» y «no se puede leer» quieren decir lo mismo,
    que el archivo no se pudo abrir.
  - La lista de lo que cuenta como ilegible sigue siendo una sola, la de D422. La CLI importa
    `ogr_api`, que no importa ni PySide6 ni `mcp` (comprobado), y las capas se respetan.
- `tests/test_cli_unreadable_v1490.py` (nuevo, 4 tests):
  - los cinco casos por `info` y por `compute`: sin `Traceback`, código 1, una sola línea con la
    frase de `load_ogr` calculada llamándola (la referencia no es una captura de la CLI) y nada en
    `--output`;
  - una ruta que no existe sigue diciendo `File not found`;
  - el proyecto de ejemplo sigue saliendo con su tabla y código 0.
  - Sin el arreglo, los dos tests de los casos ilegibles fallan.
- La versión, en siete sitios.

## 2. Qué se probó

- El REPRODÚCELO de la ficha, más bytes y `null`: los diez salen sin traza y con código 1, y el
  ejemplo con 0.
- `tests/_runner.py cli_unreadable`: 4 de 4.
- La suite entera con `--jobs 4`: 7588 casos, 7586 pasan, 0 fallan, 2 saltados, sin fugas ni tramos muertos.
- `d430()` en el `verificar_cierres.py` de la raíz del banco (fuera de git), registrada en
  `COMPROBACIONES`: CUBIERTO POR TEST.

## 3. Pendiente

- D429 (0.1.491, la parte del motor) y D431 (OGR-Core).
