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
QT_QPA_PLATFORM=offscreen python tests/_runner.py   # toda la suite
python -m ogr_gui                                    # abrir la aplicación
python -m ogr_cli --help                             # interfaz de terminal
pip install -e .                                     # instalar en editable
```

`QT_QPA_PLATFORM=offscreen` es **obligatorio** para los tests: construyen
widgets Qt reales, solo que nunca llegan a una pantalla.

Durante el desarrollo se puede ejecutar solo una parte (desde v0.1.80):

```bash
python tests/_runner.py transient          # archivos que contengan eso
python tests/_runner.py transient seepage  # unión de los dos
python tests/_runner.py -k erfc            # solo tests con ese nombre
python tests/_runner.py --list transient   # enseña la selección, no ejecuta
```

El patrón admite fragmento, nombre de archivo o ruta —`transient`,
`test_transient_v130.py` y `tests/test_transient_v130.py` seleccionan lo
mismo— y no distingue mayúsculas. Un patrón que no case con nada **sale
con código 2**, para que una errata no se lea como una suite en verde.

**Una ejecución filtrada no es evidencia para publicar.** Lleva un aviso
`FILTERED RUN` antes y después de los totales precisamente por eso: antes
de una versión, la suite entera y sin argumentos.

## Estructura del proyecto

| Ruta | Contenido |
|---|---|
| `ogr_core/` | Geometría, materiales, cargas, soportes, proyecto, hidráulica, estadística, anotaciones, DXF |
| `ogr_slip2d/` | Motor LEM: 7 métodos, 6 búsquedas, rebanado, foco, optimización, retroanálisis |
| `ogr_fem2d/` | Elementos finitos: mallado y solvers de filtración |
| `ogr_gui/` | Interfaz PySide6: lienzo, ~30 diálogos, ventanas de interpretación, i18n |
| `ogr_cli/` | Interfaz de línea de comandos |
| `tests/` | Un archivo por área funcional |
| `docs/` | Planes, auditorías, changelog |
| `spec/` | Especificaciones SDD (constitución y features) |

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

- el factor de seguridad de referencia de un caso conocido (los 7 métodos
  LEM están validados así, con error < 0.7 %);
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

### 6. Las anomalías se reportan ANTES de corregirlas

Si encuentras comportamiento que parece incorrecto, **dilo y muestra la
evidencia** antes de cambiarlo. Dos de los hallazgos más instructivos del
proyecto salieron de esa disciplina:

- una comprobación de m-alpha que habría **rechazado el círculo crítico
  validado contra la referencia**. Tardó cincuenta versiones en tener
  diagnóstico (v0.1.82): `m_alpha` no es simétrica en α, así que solo
  significa algo evaluada con el mismo sentido de deslizamiento que usó el
  solver, y la comprobación omitía ese factor. Con el signo correcto el
  círculo pasa (min m_alpha +0,93 en vez de −0,01). Sigue desactivada por
  defecto porque así la trae la referencia, no porque rechace nada;
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
- Cada versión sube el número en **siete** sitios y añade un changelog en
  `docs/changelog/`: `pyproject.toml`, `ogr_gui/main_window.py`
  (`MainWindow.VERSION`) y el `__version__` de `ogr_core`, `ogr_slip2d`,
  `ogr_fem2d`, `ogr_gui` y `ogr_cli`. Esta lista decía cuatro hasta
  v0.1.76, y los tres que omitía llevaban congelados en 0.1.59 desde
  v0.1.59. Hay un test que falla si discrepan, porque una lista en un
  documento solo vale lo que valga la atención de quien la lee.

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

La suite entera tarda **entre 5 y 7½ minutos**, y esa horquilla es lo
honesto: el mismo código, sin tocar nada, ha dado 5:55, 6:19, 6:41 y 7:22
en la misma máquina. **El reloj total no es una medida**, es una
comprobación de que la suite termina.

Que el tiempo suba no es un problema por sí solo. Lo que sí importa es no
meter un test caro sin darse cuenta: los caros son los que mallan y
resuelven filtración. Un archivo que tardaba 48 s bajó a 12 s compartiendo
la superficie de partida entre casos, sin perder ninguno.

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
