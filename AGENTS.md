# OGR Slip2D

Estabilidad de taludes por equilibrio límite, flujo subterráneo por
elementos finitos y análisis probabilístico.

**Dos niveles de nombre, y conviene no confundirlos**: *OpenGeoRock* (u
*OGR Suite*) es el paraguas de cinco programas planificados; **OGR Slip2D**
es este programa, y es lo que contiene este repositorio. El paquete
instalable se llama `ogr-slip2d`. El núcleo compartido `ogr_core` vive aquí
por ahora, y se extraerá a su propio paquete cuando exista un segundo
programa que lo use — no antes.

Autor y titular del copyright: Samuel Sáez López (UPCT). Licencia
AGPL-3.0-or-later.

> Este archivo es el **contrato de trabajo** con cualquier agente de IA.
> Se consulta antes de cada acción. Si algo aquí contradice lo que parece
> razonable, gana este archivo — y si de verdad está mal, dilo antes de
> saltártelo.

---

## Stack

- **Lenguaje**: Python 3.11+, con anotaciones de tipo donde aclaren.
- **GUI**: PySide6 (Qt 6).
- **Geometría**: Shapely. **Numérico**: NumPy, SciPy.
- **Gráficas**: Matplotlib. **Informes**: reportlab. **CAD**: ezdxf.
- **Tests**: runner propio en `tests/_runner.py` (aporta un `pytest`
  simulado; **no** hay pytest real instalado).
- **Formato de proyecto**: `.ogr`, JSON puro.

## Comandos

```bash
QT_QPA_PLATFORM=offscreen python tests/_runner.py --jobs 4  # toda la suite, en 4 procesos
QT_QPA_PLATFORM=offscreen python tests/_runner.py   # toda la suite, en serie (la CI)
python -m ogr_gui                                    # abrir la aplicación
python -m ogr_cli --help                             # interfaz de terminal
pip install -e .                                     # instalar en editable
pip install -e ".[mcp]"                              # + servidor MCP (agentes)
python -m ogr_mcp --help                             # servidor MCP
```

`QT_QPA_PLATFORM=offscreen` es **obligatorio** para los tests: construyen
widgets Qt reales, solo que nunca llegan a una pantalla.

Durante el desarrollo se puede ejecutar solo una parte (desde v0.1.80):

```bash
python tests/_runner.py transient          # archivos que contengan eso
python tests/_runner.py transient seepage  # unión de los dos
python tests/_runner.py -k erfc            # solo tests con ese nombre
python tests/_runner.py --list transient   # enseña la selección, no ejecuta
python tests/_runner.py --fast --jobs 4    # todo menos los lentos (desde v0.1.376)
```

El patrón admite fragmento, nombre de archivo o ruta —`transient`,
`test_transient_v130.py` y `tests/test_transient_v130.py` seleccionan lo
mismo— y no distingue mayúsculas. Un patrón que no case con nada **sale
con código 2**, para que una errata no se lea como una suite en verde.

**Una ejecución filtrada no es evidencia para publicar**, y `--fast`
tampoco. Lleva un aviso `FILTERED RUN` antes y después de los totales
precisamente por eso: antes de una versión, la suite entera con
`--jobs 4`, y en serie cuando el runner lo pida (ver «Coste de los
tests»).

## Estructura del proyecto

| Ruta | Contenido |
|---|---|
| `ogr_core/` | Geometría, materiales, cargas, soportes, proyecto, hidráulica, estadística, anotaciones, DXF |
| `ogr_slip2d/` | Motor LEM: 9 métodos, 7 búsquedas, rebanado, foco, optimización, retroanálisis |
| `ogr_fem2d/` | Elementos finitos: mallado y solvers de filtración |
| `ogr_gui/` | Interfaz PySide6: lienzo, ~30 diálogos, ventanas de interpretación, i18n |
| `ogr_cli/` | Interfaz de línea de comandos |
| `ogr_api/` | Capa de operaciones sin Qt (spec 008): *handles*, validación, deshacer, trabajos en subproceso, render PNG, `python_exec`. La usan el servidor MCP y un script; **no** importa PySide6, `ogr_gui` ni `mcp` |
| `ogr_mcp/` | Servidor MCP para agentes de IA (extra `[mcp]`, comando `ogr-slip2d-mcp`): una herramienta por operación de `ogr_api`, stdio y HTTP con token. Guías en `docs/mcp/` |
| `tests/` | Un archivo por área funcional |
| `docs/` | Planes, auditorías, changelog |
| `spec/` | Especificaciones SDD (constitución y features) |

Capas en un solo sentido: `ogr_core → ogr_slip2d / ogr_fem2d → ogr_api →
{ogr_gui, ogr_cli, ogr_mcp}`. Una regla que hoy solo impone la interfaz se
**mueve** a `ogr_core/project/rules.py` y la interfaz pasa a preguntarla;
copiarla es cómo acaban diciendo cosas distintas.

---

## Las siete reglas

Cada una existe porque su ausencia causó un problema real en este
proyecto. No son burocracia; son cicatrices.

### 1. El trabajo numérico se valida contra algo EXTERNO

Un método de análisis, un solver o una fórmula necesitan un **valor de
referencia**: un caso publicado, una solución cerrada o una identidad
analítica. **Nunca** una captura de lo que el código imprime hoy: un test
de instantánea consagra el bug.

Ejemplos de lo que sí cuenta, todos ya en la suite:

- el factor de seguridad de referencia de un caso conocido (los métodos
  LEM están validados así, con error < 0.7 %; los dos Corps of Engineers,
  contra las tablas dovela a dovela de la EM 1110-2-1902);
- una solución cerrada (el solver de filtración se contrasta con la
  respuesta escalón erfc y con las medias armónica y aritmética por
  capas);
- una identidad analítica (el retroanálisis se comprueba porque la fuerza
  activa y la pasiva deben coincidir **exactamente** con factor objetivo
  1.0);
- consistencia asintótica con un camino ya validado (el transitorio a
  tiempo grande debe reproducir el permanente).

### 2. Todo texto visible pasa por `tr()`

```python
from ogr_gui.i18n import tr
label = QLabel(tr("Number of slices:"))
```

y necesita su entrada en español en `ogr_gui/i18n/__init__.py`. Hay un
test que falla si una clave envuelta no tiene traducción, y otro de
presupuesto que falla si crece el número de cadenas **sin** envolver.

La terminología importa más que la traducción literal: usa el término
geotécnico castellano estándar (*dovela*, *nivel freático*, *grieta de
tracción*, *coeficiente parcial*).

### 3. Toda acción debe ser alcanzable desde un menú

Un módulo entero se implementó, se testeó y se publicó **invisible**
porque sus acciones estaban registradas pero nunca añadidas a la barra de
menús (12 acciones, corregido en v0.1.42). Hay un test que recorre la
barra real y falla ante cualquier acción inalcanzable.

### 4. Cada archivo lleva su cabecera de licencia

```python
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
```

Comprobado por un test y, por separado, en CI.

### 5. Los tests no filtran estado

Cualquier cosa global —el idioma activo, las unidades, una caché de
módulo— debe restaurarse. Un test que dejó el idioma en español hizo
fallar tests de menús no relacionados **solo al ejecutar la suite
completa**, que es el peor fallo posible de diagnosticar.

Desde v0.1.374 lo comprueba el runner archivo a archivo
(`tests/_leaks.py`): lo que un archivo deja cambiado sale como
`✗ [LEAK] clave: antes → después` bajo ese archivo y hace fallar la
corrida. Se arregla en el test; solo un cambio que no es del test (lo que
hace una librería al importarse, una caché acotada del programa) va a la
lista blanca, **con su porqué**.

### 6. Las anomalías se reportan ANTES de corregirlas

Si encuentras comportamiento que parece incorrecto, **dilo y muestra la
evidencia** antes de cambiarlo. Dos de los hallazgos más instructivos del
proyecto salieron de esa disciplina:

- una comprobación de m-alpha que habría **rechazado el círculo crítico
  validado contra la referencia**. Tardó cincuenta versiones en tener
  diagnóstico (v0.1.82): `m_alpha` no es simétrica en α, así que solo
  significa algo evaluada con el mismo sentido de deslizamiento que usó el
  solver, y la comprobación omitía ese factor. Con el signo correcto el
  círculo pasa (min m_alpha +0,93 en vez de −0,01). Quedó desactivada por
  defecto «porque así la trae la referencia», y eso era falso: los
  informes de los dos ejemplos trabajados filtran con ella por defecto y
  la cuentan como error −112 (97 superficies en Ej_1 bishop, 225 en Ej_2).
  Activada por defecto en v0.1.84. La lección no es el signo: es que una
  medición equivocada se quedó dos versiones justificando una decisión;
- un arranque de Simulated Annealing que dependía de la suerte: 200
  rechazos consecutivos con semillas desafortunadas.

Ambos habrían quedado tapados por un arreglo rápido.

### 7. Ningún ajuste puede no hacer nada

Un control configurable que no afecta al resultado es **peor** que no
tenerlo, porque el usuario cree que el análisis lo respeta. Los
coeficientes parciales de la norma de diseño estuvieron dos versiones
siendo configurables sin aplicarse (v0.1.52 → v0.1.57). Si añades una
opción, añade también el test que demuestra que **mueve el número**.

---

## Flujo de trabajo

- **Antes de una tarea no trivial, propón un plan y espera mi OK.** Usa
  plan mode.
- **Una tarea a la vez.** Al terminar, dime qué cambiaste y qué probaste.
- **Si no estás seguro al 80 %, pregunta. No inventes** — sobre todo en
  fórmulas geotécnicas: una ecuación plausible pero incorrecta es el peor
  resultado posible aquí, porque parece que funciona.
- **Sé escéptico con lo que te pido.** Si algo huele mal, dilo.
- **Al terminar, lista qué probaste y qué falta por probar.**
- Cada versión sube el número en **nueve** sitios y añade un changelog en
  `docs/changelog/`: `pyproject.toml`, `ogr_gui/main_window.py`
  (`MainWindow.VERSION`) y el `__version__` de `ogr_core`, `ogr_slip2d`,
  `ogr_fem2d`, `ogr_gui`, `ogr_cli`, `ogr_api` (desde v0.1.194) y
  `ogr_mcp` (desde v0.1.195). Esta lista decía cuatro hasta v0.1.76, y los
  tres que omitía llevaban congelados en 0.1.59 desde v0.1.59. Hay un test
  que falla si discrepan (`tests/test_version_consistency_v176.py`, que es
  la lista que manda), porque una lista en un documento solo vale lo que
  valga la atención de quien la lee.

### Sobre los changelogs

Registran **qué se encontró**, no solo qué se escribió: los caminos
equivocados son la parte que merece recordarse. Un changelog que solo
lista funciones añadidas ha desperdiciado la mitad de su valor.

---

## No hagas

- **No instales dependencias sin preguntar.** Y comprueba la licencia: la
  librería `triangle` se descartó por ser incompatible con AGPL, y se usa
  `scipy.spatial.Delaunay` en su lugar.
- **No uses `pytest` directamente**: no está instalado. El runner del
  proyecto aporta un `pytest` simulado y los módulos de test **no** se
  pueden importar fuera de él.
- **No abras diálogos modales en código que un test vaya a ejecutar.**
  `QMessageBox` y `QDialog.exec()` bloquean indefinidamente sin pantalla.
  Los gráficos informativos van **no modales**.
- **No conviertas anotaciones en geometría automáticamente.** El único
  puente es *Convert Tool to Boundary*, explícito y en un solo sentido.
- **No modifiques el proyecto del usuario dentro de un cálculo.** Los
  coeficientes de diseño se aplican a una **copia**.
- **No cambies `LICENSE`, `CLA.md` ni las cabeceras SPDX** sin pedírmelo.
- **No añadas telemetría ni llamadas de red** que no haya pedido
  explícitamente. *Check for Updates* no contacta con ningún servidor, a
  propósito.
- **No quites el token del HTTP del servidor MCP** ni lo hagas opcional
  fuera de *loopback*: `python_exec` está siempre disponible (decisión del
  propietario), así que quien alcance ese puerto ejecuta código como el
  usuario. Ver `docs/mcp/seguridad.md`.
- **No toques los casos de validación** (`tests/test_slide_validation_*`)
  para hacer pasar un cambio. Si un caso de referencia falla, el fallo
  está en el código.

---

## Convenciones de código

- Comentarios que explican **por qué**, no qué. Un comentario que da una
  razón no obvia —un convenio de signos, una guarda numérica, una
  restricción de licencia— vale por diez que describen sintaxis.
- Docstrings en funciones públicas, **con la referencia de toda fórmula**
  (autor y año).
- Tests en `tests/test_<area>_v<version>.py`, con una cabecera que explique
  **qué invariante** protegen y por qué.
- Nombres en inglés en el código; español solo en las traducciones.
- Las tolerancias geométricas van **relativas** al tamaño del modelo, no
  absolutas: la misma tolerancia se comporta distinto en milímetros y en
  metros.
- Las tolerancias de pantalla van **en píxeles** convertidos a unidades de
  modelo, para que el comportamiento no dependa del zoom.

## Coste de los tests

Medido en el portátil de desarrollo (Windows, 4 núcleos físicos y 8
lógicos, 15,9 GB):

| Corrida | Orden | Tiempo |
|---|---|---|
| Entera, en serie | `python tests/_runner.py` | 68,6 min (6678 casos, v0.1.375) |
| Entera, en 4 procesos | `python tests/_runner.py --jobs 4` | 34,6 min (6708 casos, v0.1.376) |
| Sin los lentos, en 4 procesos | `python tests/_runner.py --fast --jobs 4` | 12,7 min (5971 casos, v0.1.376) |
| CI (Linux), en serie | — | ~1 h 10 por versión de Python |

Era «entre 5 y 7½» en v0.1.80, unos 25 min en v0.1.175–0.1.193, 50–72
en v0.1.278–0.1.300 y 134 en v0.1.372. Cada cifra siguió escrita aquí
muchas versiones después de dejar de ser cierta, y en v0.1.191 se leyó
como anomalía un tiempo normal. De los 134 min, la mitad era la máquina:
`TextInputHost.exe` llevaba días colgado girando en un núcleo, y sin él
eran 87,6. Unos 20 de esos 87,6 eran estado acumulado en el proceso, que
v0.1.373 cortó (`docs/audits/AUDITORIA_SUITE_v0.1.372.md`). **Antes de
llamar anomalía a una duración, mira la CPU de los procesos de la
máquina.** El reloj total no es una medida, es una comprobación de que
la suite termina: dos corridas iguales de v0.1.374 difirieron 3,7 min.

### Qué corrida pide cada momento

1. **Desarrollo:** `python tests/_runner.py --fast --jobs 4`, o un área
   con patrones o `-k`. `--fast` deja fuera los archivos de
   `tests/_slow.txt` y lo dice con `FILTERED RUN`: no vale para publicar.
2. **Publicar una versión:** la suite entera con
   `python tests/_runner.py --jobs 4` (decisión de la propietaria,
   v0.1.376). Lleva el detector de fugas archivo a archivo, y sale en rojo
   si a un tramo se le muere el proceso o le faltan tests. Verde es
   `Failed: 0` sin `Leaks` ni `Chunks died`.
3. **En serie, cada 100 commits:** `python tests/_runner.py`, sin
   argumentos. Es la única corrida que mantiene la suite entera en un solo
   proceso: así se vio el aborto de v0.1.302, que con la suite repartida
   habría quedado escondido. Es también la que ejecuta la CI. Cada
   corrida entera con `--jobs` termina diciendo cuántos commits hace de la
   última serie en verde en esta máquina. A partir de 100 dice
   `SERIAL RUN DUE`, y también cuando no puede saberlo: sin registro, o
   con un commit que no está en la historia. Con ese aviso, la versión se
   publica con la serie. La serie en verde se apunta sola al terminar
   (`full serial run recorded`), con el commit en
   `%TEMP%/ogr-slip2d-serial-run.json`.

La CI corre en serie en cada push y sigue siendo la referencia.

Lanza la suite en segundo plano, guarda el código de salida del proceso
(`echo EXIT=$?`) y no toques el programa mientras corre. Nunca lances dos
corridas a la vez: compiten por los mismos núcleos y falsean el tiempo, y
la máquina se comparte con la sesión de OGR-FEM2D. **Nunca uses
`PYTHONFAULTHANDLER=1` ni `-X faulthandler` con la suite:** llegan a los
trabajadores `pythonw.exe` de un test, que mueren al arrancar sin decir
nada, y la suite se cuelga.

### Dónde y cómo van los tests nuevos

La suite pasó de 25 a 70 minutos sin que nadie lo decidiera. Un test
nuevo cuesta en las tres corridas. Para que el tiempo no vuelva a crecer
sin verse:

- **Dónde:** en `tests/test_<area>_v<version>.py`, uno por área, con la
  cabecera del invariante (ver «Convenciones de código»). El orden
  alfabético no cuenta para el tiempo, porque `--jobs` reparte según lo
  que tardó cada archivo la última vez.
- **Cuánto:** un test nuevo debería tardar menos de 1 s. Si pasa de 5 s,
  que sea porque valida contra una referencia (regla 1), y que su
  cabecera lo diga. Mídelo solo: `python tests/_runner.py <archivo>`.
- **Comparte lo caro** entre los casos de un archivo: el modelo, la malla
  y la búsqueda, calculados una vez a nivel de módulo o de clase. Un
  archivo bajó de 48 s a 12 s compartiendo la superficie de partida, sin
  perder ningún caso. Pero **nunca bajes mallas, dovelas ni tolerancias de
  un test de validación** para ganar segundos: su finura puede ser el
  invariante.
- **Prueba en la capa más baja que tenga la regla:** `ogr_core`,
  `ogr_slip2d` u `ogr_api`, sin Qt. Abre una `MainWindow` solo para
  probar la ventana: cada una sigue viva hasta el final del proceso, en
  memoria, y un cambio de tema las recorre todas.
- **Búsquedas pequeñas:** una rejilla de 400 círculos o más abre un pool
  de procesos (`_PARALLEL_MIN_CIRCLES`, en `ogr_slip2d/search.py`). En
  Windows cada pool cuesta 0,6–0,8 s en arrancar, y más con la máquina
  cargada. Úsala solo si el test es del camino en paralelo.
- **Mallas de filtración gruesas,** salvo que el test valide la
  convergencia: mallar y resolver es lo más caro de la suite.
- **Nada de segundos en un test,** salvo que el reloj sea lo que se
  prueba. Entonces el archivo lleva `SERIAL_LANE = True` con su porqué, y
  en una corrida con `--jobs` corre solo, al final.
- **Archivos en carpetas temporales** (`tmp_path`, `tempfile`), nunca en
  una ruta fija: dos tramos de `--jobs` chocarían en ella.
- **Restaura todo estado global** (regla 5): el runner falla el archivo
  que lo deje cambiado.

**Un archivo lento nuevo sigue en `--fast` hasta que alguien lo decida.**
`tests/_slow.txt` se versiona, y solo lo escribe
`python tests/_runner.py --write-slow-list`. Por defecto mete los archivos
de 45 s o más en su última corrida en esta máquina, que suele ser una
entera con `--jobs 4`: con cuatro tramos a la vez cada test tarda casi el
doble que solo. Van archivos enteros y no tests sueltos porque los tests
de un archivo comparten lo caro: si se quita el que lo pagaba, lo paga el
siguiente (v0.1.376). Lo reescribe quien prepara una versión, a propósito,
y el changelog cuenta qué entra y qué sale. Para que no se olvide, cada
corrida entera termina con `SLOW, NOT IN tests/_slow.txt` y los archivos
de 90 s o más que la lista deja dentro: o se abaratan, o se reescribe la
lista.

**Un corte sin totales con código 127** no es un test fallado: en Git Bash,
127 es un proceso que terminó con 0xC0000409, lo que hace `abort()`. En
v0.1.300 y v0.1.301 la suite abortaba así una vez de cada dos, al abrir un
pool de procesos: el recolector de basura de un hilo del pool destruía
objetos de Qt que los tests dejaban en ciclos. Lo resolvió v0.1.302 con
`ogr_gui/gc_guard.py`, que instalan la ventana y el runner. Si vuelve a
pasar, es otra causa. Para ver la pila nativa hace falta un manejador de
SIGABRT del CRT, y `faulthandler` no basta en Windows
(`docs/changelog/CHANGELOG_v0.1.302.md`). Al abortar quedan trabajadores
`spawn_main` huérfanos que hay que cerrar.

### Cómo medir el coste de un cambio

Dos formas de medir ya han engañado a este proyecto, y las dos parecían
razonables:

1. **El cronómetro de la suite** varía ±40 s entre corridas idénticas. Para
   diferencias por debajo del 10 % no distingue nada. (Parte de ese ruido
   fue autoinfligido: lanzar tests dirigidos mientras una suite completa
   corría de fondo, dos procesos peleándose por los mismos núcleos.)
2. **Los bucles calientes entre sesiones tampoco valen.** `_column_weight`
   midió 32.5 µs un día y 40 µs otro **sin que se tocara el código**: la
   máquina deriva.

Lo único fiable es un **A/B en el mismo proceso, espalda con espalda**:
la versión nueva, la vieja monkey-patcheada, y otra vez la nueva como
control. Si las dos corridas de control difieren entre sí tanto como el
efecto que buscas, la medida no resuelve nada — y entonces **manda el
razonamiento sobre cuánto trabajo se ha añadido**, no el número.

Ejemplo de las dos cosas, en v0.1.65: el A/B daba +8.7 % con los controles
difiriendo un 5 % entre sí (no concluyente), mientras que contar el trabajo
añadido —una consulta de atributo por dovela, ~0.2 µs sobre 2.5 ms— daba
~0.2 %. Ganó el razonamiento. En la misma medición apareció una mejora real
y comprobable: 0.819 → 0.390 µs, un 2.1×, que sí se distinguía del ruido.

---

## Documentación de referencia

En `docs/reference/` (fuera del control de versiones) hay documentación de
software comercial usada como guía de interfaz y de formulación.

**Regla estricta**: puedes leerla para entender **qué** hace una función y
**cómo debería comportarse la interfaz**, pero **el código no puede
contener ninguna referencia a esos productos ni a sus marcas**, ni copiar
su texto. Las fórmulas se citan por su **fuente científica original**
(Bishop 1955, Spencer 1967, Hoek et al. 2002, Greco 1996, Celia et al.
1990), no por el programa que las implementa.

---

© 2026 Samuel Sáez López — UPCT — AGPL-3.0-or-later
