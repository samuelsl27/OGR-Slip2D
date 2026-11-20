# OGR Slip2D v0.1.476

**La CI de Linux, en verde en los tres Python.** Lo pide la sesión de OGR-Core: añade esta suite a su
CI, contra el núcleo de cada commit suyo, cuando salga en verde en Linux, porque un trabajo en rojo
por una razón conocida enseña a no mirarlo. Medido por esa sesión sobre `55a1771` (run
44753192997): 5 fallos en 3.11 y 3.12 y 4 en 3.13, ninguna fuga; en Windows, 0. Eran dos defectos,
uno del programa y uno de un test, y ninguno movía un número.

Los intentos fueron a una rama corta, `dev/ci-linux-verde` (la CI se dispara en `dev/**`), por
decisión de la propietaria, para no llenar `main` de intentos.

## 0. Lo que se encontró

### El servidor MCP mandaba la sangría de los docstrings (programa)

`test_the_compact_profile_stays_small` (`tests/test_mcp_server_v1195.py`) medía **14 060** en 3.11 y
3.12 sobre un presupuesto de 14 000, y pasaba en 3.13.

- El SDK de MCP toma la descripción de una herramienta de `fn.__doc__` tal cual
  (`func_doc = description or fn.__doc__`). Python quita al compilar la sangría común de los
  docstrings **solo desde 3.13**; en 3.11 y 3.12 cada línea de continuación llevaba ocho espacios al
  contexto del modelo.
- Medido en el `.venv` (3.14), con los docstrings crudos del fuente leídos por `ast` en lugar de los
  que da el compilador: 13 972 + 88 = **14 060**, al carácter lo que midió la CI. Son las ocho
  herramientas del perfil compacto con descripción de varias líneas.
- No era el test: el presupuesto mide algo real, lo que ocupa la lista de herramientas en el contexto
  de un modelo, y el mismo servidor decía distinto texto según el intérprete que lo sirviera. No se
  ha tocado.

Arreglo: `_tool_description(fn)` en `ogr_mcp/server.py`, `inspect.cleandoc` del docstring, pasado como
`description=` en el único registro de herramientas. Comprobado que `cleandoc` del docstring crudo
coincide con lo que se envía en 3.14 en todas las herramientas, así que 3.11 mide ahora 13 972 como
3.13 y 3.14 (lo confirmó el primer intento: el test pasa en los tres).

**Para la propietaria**: 13 972 deja **28 caracteres** de margen. El presupuesto se escribió con
12 774 (v0.1.195), y el comentario dice que el margen es para retocar descripciones, no para
herramientas nuevas. No se ha subido.

### El lector de la tabla solo conocía la raya fina (test)

Los cuatro de `TestTheCommandLine` (`tests/test_cli_reported_caption_v1430.py`) morían en los tres
Python con `StopIteration` en `_heading_and_value`, sin enseñar nada.

- Primer intento: que el test enseñara la salida al fallar (se queda). La salida de Linux era **la
  tabla entera y correcta**: `Over-design factor 1.6166`, `Critical Ky 0.1556`, cada encabezado el
  que pide su test.
- rich dibuja su tabla por defecto (`box.HEAVY_HEAD`) con la raya gruesa `┃` (U+2503) en la fila de
  cabecera y la fina `│` (U+2502) en el cuerpo. La consola de `ogr_cli` en Windows tiene
  `legacy_windows` a `True` (medido), y rich sustituye entonces la caja por `SQUARE`, fina en todas
  las filas. El lector partía solo por `│`: en Linux la fila `┃ Method ┃ …` nunca se encontraba.
- No era el programa: el CLI imprime lo que debe en los dos sistemas. Cambiarlo para que lo lea un
  test sería el arreglo al revés.

Arreglo: el lector parte por `│` o `┃`, y `TestTheTableReader` le pasa las dos tablas escritas a mano
(la de Linux y la de una consola antigua de Windows), para que el arreglo tenga diente en cualquier
sistema. El mutante «solo `│`» muere en Windows con el mismo mensaje que daba Linux.

**No se cubre la caja ASCII (`|`), a propósito** (pregunta de la propietaria). rich cae a ella solo
cuando el flujo no es UTF (`options.ascii_only`), y `CliRunner` captura en UTF-8 en todo sistema
(`charset="utf-8"` por defecto; medido dentro: `encoding utf-8`, `ascii_only False`), así que este
test no puede verla. Partir por `|` además cortaría una celda que llevara una barra. Si esa tabla
llegara algún día, el test falla enseñándola, que es lo que no hacía antes.

### Anotado, no tocado

- La CI pasa `PYTHONFAULTHANDLER=1` a la suite. AGENTS.md lo prohíbe en Windows porque mata a los
  trabajadores `pythonw.exe`; en Linux no ha dado problemas, y la CI no corre en Windows.
- El `.venv` lleva typer 0.27.1 y la CI 0.29.2. No era la causa (rich 15.0.0 en los dos, y la
  diferencia es de consola), pero las dos máquinas no prueban las mismas versiones.

## 1. Los tests

- `tests/test_mcp_descriptions_v1476.py` (nuevo, 4 casos): la sangría del fuente no llega al modelo
  (con un `__doc__` asignado en ejecución, que el compilador no ve, así que muere en cualquier Python);
  sin docstring no hay descripción; cada herramienta se registra a través de `_tool_description` (la
  marca y la busca en el protocolo); ninguna línea de ninguna descripción empieza ni acaba en
  espacio, en `compact` y `full`. Tres mutantes, uno a uno: devolver `fn.__doc__`, quitar
  `description=` del registro, devolver `""` sin docstring. Mueren los tres en 3.14.
- `tests/test_cli_reported_caption_v1430.py`: el lector y su fallo con la salida; `TestTheTableReader`
  (2 casos). Un mutante, muere.

## 2. Versión

0.1.476 en los siete sitios. Núcleo fijado sin cambios: `ogr-core` 0.2.2.

## 3. Verificación

- Suite entera en Windows, `--jobs 4`, fuera de pantalla, en el `.venv` (`shared: ogr_core 0.2.2 …
  installed`): **7547 casos, 7545 pasan, 0 fallan, 2 saltados, sin fugas** ni tramos muertos (6
  casos nuevos sobre los 7541 de 0.1.475). El runner avisa de un archivo de 90 s o más fuera de
  `tests/_slow.txt`, `test_dialogs_fit_v1315.py` con 126,4 s; no lo toca esta versión y la lista no
  se reescribe aquí.
- Primer intento en la CI (run 44784829031, `b60202c`, sin el arreglo del lector): el perfil
  compacto pasa en 3.11, 3.12 y 3.13; quedan los cuatro del CLI en los tres, con la tabla a la
  vista.
- CI de Linux en los tres Python: PENDIENTE.
