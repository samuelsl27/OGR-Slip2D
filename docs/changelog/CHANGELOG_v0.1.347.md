# OGR Slip2D v0.1.347

**Las notas del análisis sobre el modelo y las negativas de las reglas del proyecto llevan un código estable, y
la ventana las dice en castellano: el panel de notas, la barra de estado y los cuadros de Calcular (D335,
primera parte).** Octava versión de la tanda P8k.

## 0. Lo que se encontró

- **El panel de notas no traducía nada.**
  - Enseñaba cada nota tal como llegaba, sin pasarla por `tr()`, y la barra de estado igual.
  - El diccionario tenía una entrada para una de ellas, la del enjambre de partículas con *Optimize
    Surfaces* apagado. Nunca se enseñó: ninguna nota pasaba por `tr()`.
  - Esa entrada sale del bloque de la optimización y entra en el de las notas, con su castellano revisado.
    El viejo dejaba «Optimize Surfaces APAGADO» a medio traducir, y ahora dice «Optimizar superficies
    DESACTIVADO».
- **No bastaba con envolver en `tr()`.** Las notas son frases inglesas con los valores dentro: un número de
  bandas, un ángulo, el nombre de una capa. Una entrada por frase solo casaría con los valores con que se
  escribió. Así que cada nota es ahora un **código** con sus valores, y la plantilla castellana se rellena con
  ellos.
- **Seis frases pegaban al número un plural inglés**: `" is" if n == 1 else "s are"`, `"" if n == 1 else
  "s"`, `"1 weak layer" if n == 1 else f"{n} weak layers"`. Eso no se traduce a otra lengua. Cada una tiene
  ahora dos plantillas enteras, singular y plural, y el número elige.
- **Algunas frases se montaban por piezas.**
  - La de la dirección de rotura metía en la frase las palabras «Right to Left», «right» y «left». Ahora son
    dos plantillas, una por sentido.
  - La de Steffensen añadía o no una cláusula sobre Bishop. Ahora son dos plantillas.
  - Las comprobaciones de Ito y Matsui que no se pudieron hacer compartían una frase con la causa pegada. Ahora
    tienen una plantilla por causa.
- **Tres tests que dicen «el divisor REAL del panel» habrían pasado sin mirar nada.**
  - v1170, v1173 y v1174 llaman a `analysis_notes_panel._split`, y el primer borrador de esta versión hacía
    que el panel agrupase con otra función.
  - El panel vuelve a pasar por `_split`, y `_split` usa la regla nueva. Lo prueba un caso del test nuevo.
- **El marco de las notas de método no cabe en `CORE_MESSAGES`.** Esa tabla es la base de la que parten el
  catálogo de razones del motor (D314) y el de problemas del DXF (0.1.334), y sus tests exigen una muestra de
  cada código. Puesto allí, `note.method` aparecía en los dos como un código sin muestra. Tiene ahora tabla
  propia, `NOTE_FRAMES`, que solo junta la ventana.
- **La barra de estado no enseña la nota tras un cálculo con superficie crítica.** El rótulo del FS la
  sustituye en el mismo instante; así se decidió en v0.1.165 (D96), y está escrito en el código. El test lo
  mide registrando todo lo que recibe la barra, y no lo que le queda al final.
- **Dos variables muertas tras la conversión:** en `block_angle_notes` se calculaban todavía la palabra del
  lado y su dirección prohibida, que ahora van dentro de los dos códigos de cada lado. Fuera.

## 1. Qué cambia

- **El mecanismo** (`ogr_core/messages.py`, que amplía el de D314):
  - **`Coded(str)`** es la frase inglesa de siempre y lleva además `.code` y `.args`. La igualdad, el `in`, el
    `startswith`, el JSON y la impresión ven el inglés de siempre, así que los tests y las herramientas que lo
    leen no cambian. Se serializa con su código (`__reduce__`), porque los trabajos del API vuelven de un
    subproceso.
  - **`MessageSpec(one=, count=)`:** la plantilla del singular y el campo que la elige.
  - **`method_note(mid, nota)`:** la forma `"<método>: <nota>"`, con el método y la nota anidada. La usarán
    las notas de cada método (0.1.348). El panel agrupa una nota así bajo el **nombre** del método, traducido;
    hoy enseña el identificador.
- **Los catálogos:**
  - `ogr_slip2d/note_messages.py`: **58 códigos** `model.*`, para `settings_warnings` y sus módulos (rejilla y
    pasos, Steffensen, bloques, ángulos de base, optimización, perfil no drenado, foco, convenio entre
    dovelas, dirección de rotura, tipo de superficie, vértices de *Auto Refine*, capas débiles, muros, Ito y
    Matsui, anclajes helicoidales y soportes);
  - `ogr_core/project/messages.py`: **21 códigos** `rule.*`, para `compute_blockers`, `block_object_refusal`,
    los ángulos de la búsqueda por bloques, la región huérfana y los ajustes migrados de archivos viejos.
- **La ventana:**
  - el panel de notas, *Copiar todo* (copia lo que se ve) y la barra de estado tras calcular;
  - los cuadros de Calcular sin contorno y sin materiales;
  - la negativa de un objeto de búsqueda por bloques en la barra de estado.
- **El castellano:** 85 entradas, una por código más los 6 singulares, con los mismos campos que su plantilla.
  «Superficie de deslizamiento», término retirado, sale como «superficie de rotura».
- **El API:** los avisos siguen saliendo en inglés, y al lado va `warning_codes` (`index`, `code`, `args`)
  cuando alguno tiene código. Una corrida sin avisos con código se serializa como antes. Lo llevan
  `settings_get`, `settings_set`, `analysis_configure`, `project_validate`, `surface_evaluate`, el resumen de
  `analysis_run` y la vista `warnings` de `results_get`.

## 2. Tests

- **`tests/test_model_notes_v1347.py`** (nuevo, 16 casos):
  - **el inglés es el de 0.1.346, byte a byte:** para cada uno de los 79 códigos, con una muestra (85, contando
    singular y plural), la frase es igual a la que escribía 0.1.346 con los mismos valores. La referencia sale
    de evaluar la expresión vieja, tomada del fuente de esa versión, y queda congelada en el test;
  - una nota con código **es** su frase: igualdad, JSON, pickle; una concatenación pierde el código, y por eso
    las notas se construyen con `coded`;
  - cada código tiene su castellano, con los campos de la plantilla y distinto del inglés;
  - **censo AST:** ninguna frase de las funciones convertidas se construye sin código;
  - **el código sobrevive a la corrida:** de `settings_warnings` a `run_analysis` y, por el camino de Calcular
    (el trabajador real y `_on_compute_done`), hasta la ventana;
  - **en la ventana, en castellano:** la barra de estado, el panel y *Copiar todo* tras una corrida; las notas
    de una búsqueda por bloques; una nota de un método bajo su nombre; el cuadro de Calcular y la negativa de
    un objeto de bloques;
  - `warning_codes` en el API, y nada cuando no hay códigos.

  El censo admite, con nombre, cuatro formatos que son datos y no frases: el entrecomillado de un nombre y el
  nombre de un atributo.
- **`tests/test_steffensen_scope_v1174.py`, cambio deliberado.** Comprobaba que la clave retirada no dejó
  huérfanas exigiendo que solo dos claves del diccionario nombren Steffensen o Aitken. Ahora hay dos más,
  legítimas: las dos notas de Steffensen, traducidas por su código. Cuenta las entradas propias del ajuste y
  deja fuera las plantillas del catálogo.

**Con el código de 0.1.346 fallan los 16**: los del mecanismo y los catálogos porque no existen, y los de
comportamiento porque la negativa de Calcular, la del objeto de bloques y las notas del panel salían en
inglés.

## 3. Verificación

- **El test de esta versión**, 16/16. En el primer borrador fallaban dos, y los dos eran del test:
  - el censo veía cuatro formatos que son datos (el entrecomillado de un nombre, el nombre de un atributo);
  - la barra de estado no enseña la nota tras un cálculo con superficie crítica (D96, sección 0).
- **Los vecinos:** 1214 casos de 59 archivos: las notas del modelo, los bloques, los ángulos, las capas débiles,
  los muros, Ito y Matsui, los anclajes, los soportes, la migración de ajustes, el panel de notas, el API, la
  CLI y el castellano. Fallaron tres:
  - dos, por `note.method` en `CORE_MESSAGES` (sección 0);
  - y el recuento de Steffensen (cambio deliberado, sección 2).

  Con los dos arreglados, los cinco archivos afectados pasan, 102/102.
- **El inglés no cambia:**
  - las 85 muestras del test son la expresión de 0.1.346, evaluada;
  - en la comparación A/B, árbol contra árbol, sobre los 230 modelos del banco (`settings_warnings` con los
    métodos del modelo y con todos, `compute_blockers`, las regiones huérfanas y `check_analysis_settings`),
    las 107 frases salen idénticas y nada lanza.
- **Suite entera:** 6407/6407, `EXIT=0`, 87 min.
- **Banco:**
  - raíz: `verificar_cierres.py` entero, 87 comprobaciones, 0 bajadas;
  - manual 02: `verificar_cierres.py` entero, 238 fichas, 0 bajadas;
  - D335, con su primera parte apuntada;
  - instantánea `Evaluaciones/0.1.347`, prompts (33) y auditorías con 0 ERROR.
- **Ningún número del motor cambia:** solo cambia quién escribe la frase.

## 4. Pendiente

- **D335 sigue abierta.** Siguiente: las notas de cada método (0.1.348).
