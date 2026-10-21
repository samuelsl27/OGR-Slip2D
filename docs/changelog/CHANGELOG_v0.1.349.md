# OGR Slip2D v0.1.349

**Las notas que una búsqueda escribe sobre su propia corrida, y las de Optimizar superficies, llevan código,
y la ventana las dice en castellano (D335, tercera parte).** Décima versión de la tanda P8k.

## 0. Lo que se encontró

- **La búsqueda une sus motivos con «; » y no con «, ».** Dice qué superficies rechazó antes de calcularlas y
  qué paseos de la optimización volvieron inservibles. El campo de lista del mecanismo (0.1.348) admite ahora
  su separador: `MessageSpec(seps=…)`.
- **Las ventanas de los límites del talud llevan un «and» entre las dos.** Es una palabra de la frase, no
  un dato, así que hay un código por número de ventanas (ninguna, una, dos). Para más de dos, que los
  ajustes no permiten, hay un código de reserva.
- **Los filtros que pueden quitar un círculo del usuario se nombran por su ajuste** («Minimum Area 2.5»).
  Ese nombre es una etiqueta de la interfaz, y cada filtro es ahora un fragmento con su código.
- **La razón por la que una superficie no tiene FS venía como texto suelto.** El resultado ya la llevaba
  con su código de D314 (`message_code`, `note_code`); ahora la frase la anida con él, y el castellano
  enseña la razón traducida. `rep.notes["start_invalid"]` conserva la frase, que leen el API y el banco.
- **El resumen del informe de optimización también era inglés con valores** («1.2346 → 1.1111 (−0.1235)
  in 250 evaluations, 37 accepted»), y la barra de estado lo enseñaba tras «Optimizado:». Tiene código.
- **La caja de error de Optimizar superficies enseñaba el inglés del motor.** Pasa por `note_text`.
- **Cinco singulares ingleses dicen «1 surface were discarded» o «1 circle that do not cut».** Así los
  escribió el motor. **No se corrige aquí**, por la misma razón que el «inclinations was discarded» de
  0.1.348: esta versión no cambia ni un byte del inglés.
- **Dos términos para la misma cosa:** el diccionario decía una vez «superficie de prueba», y el castellano
  de 0.1.347 dice «superficie de tanteo», que es el término geotécnico habitual. La unificación, con su
  regla en `test_terms_spanish_v1323`, va en 0.1.354 junto a «desembalse rápido».
- **El círculo convertido a polilínea no es de `GridSearch`.** La frase de las superficies que no se dejan
  dividir, dicha en vértices por círculo, es de `AutoRefineNonCircularSearch`.

## 1. Qué cambia

- **`ogr_slip2d/search_note_messages.py`** (nuevo): **56 códigos** `search.*`:
  - lo que rechazaron el divisor en dovelas y las guardas: sin dividir, fuera del modelo, material
    huérfano, extremos fuera del terreno, base en el aire, base en el borde del modelo, capa débil
    demasiado empinada;
  - la corrida que no encontró nada, con sus motivos;
  - las superficies del usuario: no analizadas por el tipo, sin resultado con filtros o sin ellos, sin FS,
    la informada;
  - Optimizar superficies: los paseos perdidos, las negativas de partida y el resumen;
  - el grupo de procesos que corrió en uno;
  - por qué no se analizó una superficie dada: nueve motivos y el de por defecto. La tabla
    `BaseSearch._REFUSAL_TEXT` sale del motor.
- **`ogr_core/messages.py`:** `MessageSpec.seps` y `MessageSpec.sep()`.
- **`search.py`** (16 funciones) y **`optimize.py`** (`optimize_surface`, su `_finish` y
  `OptimizeReport.summary`).
- **La ventana:** el catálogo de `core_messages` incluye el nuevo; `_optimize_surfaces` lee el error y el
  resumen por `note_text`.
- **El castellano:** 64 entradas, una por código más los 8 singulares.

## 2. Tests

- **`tests/test_search_notes_v1349.py`** (nuevo, 11 casos):
  - **el inglés es el de 0.1.348, byte a byte:** 43 muestras de los 56 códigos, con los fragmentos y los
    motivos construidos con el catálogo nuevo;
  - cada código tiene su castellano, con los campos de la plantilla;
  - **una frase para cada negativa que una búsqueda registra**, y la tabla vieja ya no existe;
  - **censo AST** de las 19 funciones, salvo dos ventanas «[a, b]», que son datos;
  - **una corrida real** con un círculo del usuario lejos del terreno: la nota lleva su código bajo el
    método, y el panel la dice en castellano bajo «Bishop simplificado»;
  - la negativa de una técnica de optimización desconocida, en castellano.

**Con el código de 0.1.348 fallan los 11.** También los de comportamiento: la nota del círculo del usuario
salía en inglés dentro del grupo del método, y la negativa de la optimización era una cadena sin código.

## 3. Verificación

- **El test de esta versión**, 11/11. En el primer borrador fallaban cuatro, los cuatro del test:
  - `SlipCircle` se importa de `ogr_slip2d.surface` (el núcleo no lo exporta en su paquete);
  - `BaseSearch` es abstracta: la frase de la negativa se pide a un objeto simple;
  - la cobertura de los dos números no miraba dentro de los fragmentos anidados.
- **Los vecinos:** 917/917, de 51 archivos: las superficies del usuario, la optimización y su arranque,
  los rechazos del terreno, los límites del talud, el foco, la búsqueda en paralelo, la exportación DXF, los
  mensajes del núcleo y el castellano.
- **El inglés no cambia:** las 43 muestras del test son la expresión de 0.1.348, evaluada.
- **Suite entera:** 6428/6428, `EXIT=0`, 83 min.
- **Banco:**
  - raíz: `verificar_cierres.py` entero, 87 comprobaciones, 0 bajadas;
  - manual 02: `verificar_cierres.py` entero, 238 fichas, 0 bajadas (la comprobación de la optimización
    sigue encontrando `start_invalid` y `_optimisation_note`);
  - D335, con su tercera parte apuntada;
  - **se abre D341** (lo que el plan de la tanda llamaba hallazgo 2, medido en esta versión, ver 0.1.352);
  - instantánea `Evaluaciones/0.1.349`, prompts (34) y auditorías con 0 ERROR.
- **Ningún número del motor cambia:** solo cambia quién escribe la frase.

## 4. Pendiente

- **D335 sigue abierta.** Siguiente: las negativas de los ajustes (0.1.350).
- La gramática de los cinco singulares, si la propietaria quiere corregir el inglés aparte.
