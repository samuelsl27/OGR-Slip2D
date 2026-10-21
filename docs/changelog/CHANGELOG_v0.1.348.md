# OGR Slip2D v0.1.348

**Las notas sobre la superficie que informa cada método llevan código, y el panel de notas las agrupa bajo
el nombre del método y las dice en castellano (D335, segunda parte).** Novena versión de la tanda P8k.

## 0. Lo que se encontró

- **El panel agrupaba por el identificador.** Una nota de método llega como
  `"bishop_simplified: …"`, y el panel ponía `bishop_simplified` como título del grupo. Ahora la línea es
  un `method_note` (el mecanismo de 0.1.347), con el método y la nota anidada, y el panel enseña
  «Bishop simplificado».
- **Las notas se montaban por piezas inglesas:**
  - las de λ pegaban «inclination» o «inclinations», y «was» o «were», al número;
  - la de m-alpha juntaba un marco y cuatro cláusulas: dónde, cuánto margen, qué efecto y qué consejo según
    la familia del método;
  - la de los soportes que no aportan fuerza lista sus motivos, cada uno con su singular, su plural y su
    forma sin número, y uno de ellos con la excepción pegada detrás.

  Ahora:
  - cada número tiene dos plantillas enteras;
  - las cláusulas de m-alpha son códigos anidados (las combinaciones son 4 × 2 × 2 × 2);
  - los motivos van en un **campo de lista**, nuevo en el mecanismo: `is_nested_list`, que se une con «, »
    como hacía el motor.
- **Tres frases de λ dicen «inclinations was discarded».** Es inglés incorrecto, y está así desde que se
  escribieron. **No se corrige aquí**: esta versión no cambia ni un byte del inglés, que leen los tests y el
  banco. El castellano dice «se descartaron».
- **La nota del soporte invertido enseña la orientación por su identificador** («'tangent_to_slip'»). El
  inglés sigue igual; el castellano dice su etiqueta («Tangente a la superficie de rotura»).
- **Siete claves empiezan por un espacio**: las cláusulas de m-alpha, que se pegan detrás de un número. La
  herramienta que escribe las entradas del diccionario partía la frase por espacios y perdía el primero, así
  que la clave y su castellano no casaban nunca. Lo vio el test de los campos a la primera; la herramienta
  conserva ahora los espacios del principio.
- **Un motivo dice lo mismo para uno que para varios** («could not be priced at all»). Con su singular
  y su plural como dos plantillas, el diccionario recibía la misma clave dos veces, y en un literal de
  diccionario gana la segunda sin avisar. Lo vio `test_the_source_has_each_key_once`. Ese motivo tiene
  ahora una sola plantilla, y en castellano una forma que vale para cualquier número; el generador de
  entradas rechaza dos con la misma clave.
- **Las tablas de frases de los soportes salen del motor.** `_UNCONTRIBUTING_PHRASES`, `_SHEAR_FAILED_PHRASE`,
  `_BOND_FAILED_PHRASE` y `_BOND_RAISED` pasan a `ogr_slip2d/method_note_messages.py`, con sus comentarios.
  Una comprobación del manual 02 (D95) leía `_BOND_FAILED_PHRASE` buscando «zero-stress envelope»; ahora lee
  el catálogo, y la constante vieja en un árbol anterior.

## 1. Qué cambia

- **`ogr_slip2d/method_note_messages.py`** (nuevo): **56 códigos** `method.*`:
  - el método no registrado;
  - λ: la muestra más próxima, el intervalo que no cierra, las cuatro pérdidas, el refinado y la
    recuperación;
  - el afloramiento empinado;
  - m-alpha: el marco y sus nueve cláusulas;
  - las dovelas sin resistencia;
  - el centro en el borde de la rejilla;
  - los modos sísmicos (kh sustituido, superficies sin Ky, Newmark sin registro, registro inutilizable,
    polaridad desconocida);
  - los soportes: invertido, no calculable, que no llega, el único, ninguno, algunos, cortante perdido,
    perfil perdido, el fallo de cálculo, y los motivos.
- **`ogr_core/messages.py`:** el campo de lista (`LIST_SEP`, `is_nested_list`). Una lista vacía da «», como
  `", ".join([])`.
- **`analysis_runner.py`:** las ocho funciones de notas de método, y las líneas `"<método>: <nota>"` de
  `run_analysis` y `evaluate_surfaces`, que pasan por `method_note`. La razón de una superficie no evaluada
  y las notas de la búsqueda van anidadas sin código hasta 0.1.349.
- **`support_integration.py`:** `reversed_support_notes`, `uncontributing_support_notes` y
  `_failure_text`.
- **La ventana:** el catálogo de `core_messages` incluye el nuevo, y la orientación de la fuerza de un
  soporte se enseña con su etiqueta.
- **El castellano:** 73 entradas, una por código más los 17 singulares, con la terminología del programa
  (*descabezamiento*, *arrancamiento*, *perfil de adherencia*, *envolvente a tensión efectiva nula*,
  *rejilla de búsqueda*).

## 2. Tests

- **`tests/test_method_notes_v1348.py`** (nuevo, 10 casos):
  - **el inglés es el de 0.1.347, byte a byte:** 71 muestras de los 56 códigos, con los dos números donde
    los hay. La referencia sale de evaluar la expresión vieja del fuente de esa versión, y las cláusulas
    anidadas se construyen con el catálogo nuevo, así que la comparación cubre también sus plantillas;
  - cada código tiene su castellano, con los campos de la plantilla;
  - los motivos del catálogo son los valores `SUPPORT_*` del motor, en su orden;
  - **censo AST:** ninguna frase de esas funciones se construye sin código, salvo dos formatos de datos con
    nombre (`x = 900` y `s1 (TypeError…)`); las tablas de frases ya no están en el motor;
  - una línea con código viaja por pickle y JSON con sus cláusulas y su lista;
  - **una corrida real** con un clavo que no llega a la superficie: la nota lleva el método y sus códigos, y
    el panel la pone en castellano bajo «Bishop simplificado».

- **`tests/test_partial_method_loss_v1170.py`, cambio deliberado.** Comprobaba que el camino probabilístico
  usa las palabras del determinista buscando la frase del método no registrado en el fuente de
  `analysis_runner.py`. La frase está ahora en el catálogo, y `analysis_runner` la escribe por su código:
  el test mira las dos cosas.

**Con el código de 0.1.347 fallan los 10.** También los de la corrida real: la nota salía en inglés, y el
panel la agrupaba bajo `bishop_simplified (1)`.

## 3. Verificación

- **El test de esta versión**, 10/10. En el primer borrador fallaban dos:
  - el de los campos castellanos, por el espacio inicial que perdía la herramienta (sección 0);
  - el de pickle, que esperaba el marco de método en una muestra que no lo lleva.
- **Los vecinos:** 1159 casos de 69 archivos: λ y sus pérdidas, m-alpha, el afloramiento, las dovelas sin
  resistencia, el borde de la rejilla, el sismo y Newmark, los soportes, el panel de notas, el API, los
  mensajes del núcleo y el castellano.
  - La primera corrida se paró al 58 %, por la clave duplicada (sección 0).
  - La segunda dio 1158/1159; el fallo era `test_partial_method_loss_v1170`, cambio deliberado (sección 2),
    que después pasa: 34/34.
- **El inglés no cambia:** las 71 muestras del test son la expresión de 0.1.347, evaluada.
- **Una comparación A/B en corridas reales del banco se intentó y se paró:** los modelos con soportes, más
  los que usan Spencer o GLE, con la búsqueda acotada. Una sola rama pasó de 83 minutos sin terminar, y el
  plan no la pedía para esta versión. La prueba del inglés es la de las muestras, más los 1159 casos de los
  vecinos.
- **Suite entera:** 6417/6417, `EXIT=0`, 102 min. Lo de más se debe a la A/B, que corría al lado.
- **Banco:**
  - raíz: `verificar_cierres.py` entero, 87 comprobaciones, 0 bajadas;
  - manual 02: `verificar_cierres.py` entero, 238 fichas, 0 bajadas; D95 lee la frase en el catálogo;
  - D335, con su segunda parte apuntada;
  - instantánea `Evaluaciones/0.1.348`, prompts (33) y auditorías con 0 ERROR.
- **Ningún número del motor cambia:** solo cambia quién escribe la frase.

## 4. Pendiente

- **D335 sigue abierta.** Siguiente: las notas de la búsqueda y de la optimización (0.1.349).
- La gramática de «inclinations was discarded», si la propietaria quiere corregir el inglés aparte.
