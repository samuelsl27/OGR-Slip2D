# OGR Slip2D v0.1.333

**Las razones por las que el motor descarta una superficie llevan un código estable, y la interfaz las
dice en castellano y las agrupa por condición (D314, primera parte); y los tres fallos de Linux de la CI
de 0.1.332 (D338).** Primera versión de la tanda P8j.

## 0. Lo que se encontró

- **D314, por qué no bastaba un `tr()`.**
  - Por qué una superficie no tiene factor de seguridad (`LEMResult.error_message`) y por qué una
    convergida es inadmisible (`admissibility_note`) llegaban a la pantalla como frases inglesas con los
    valores ya metidos dentro por un f-string.
  - No había clave con la que traducirlas.
  - Agrupar por la frase partía una misma condición en tantos grupos como valores. Medido en el segundo
    ejemplo trabajado, con Bishop y la rejilla de referencia: **49 grupos** de inválidas por texto.
    - Los 215 rechazos de m-alpha caían en un grupo por cada número de dovelas.
    - Los 46 «factor de seguridad sin sentido físico», en uno por valor.
- **Los códigos `REASON_*` no servían para traducir.**
  - Son más gruesos que las frases: `REASON_NON_PHYSICAL_FOS` reúne cinco frases distintas, y
    `REASON_DRAWDOWN_NOT_APPLICABLE` unas diez.
  - Partirlos movería los grupos del censo de D56 y lo que cuenta el banco.
  - Por eso va un **código de mensaje aparte, más fino**, y `reason` no se toca.
- **D338, la CI de 0.1.332, roja en Linux por tres tests nuevos** de la tanda P8i (run 39282372858). Además
  está el fallo de segmentación al salir, el de siempre desde 0.1.276. En Windows los tres pasaban.
  - **(a) El test de D326** fallaba en los tres Python. Era un fallo del test, no del programa: fuera de
    Windows, `multiprocessing.spawn.set_executable` guarda la ruta como *bytes* (leído en su código), y
    el test la comparaba con una cadena.
  - **(b) El censo de diálogos** fallaba en los tres Python. A su tamaño mínimo, *Importar DXF* dejaba sus
    dos cajas de tolerancia a 26 px de los 27 que piden.
    - La causa es la de D321: la etiqueta de vista previa parte su texto, y el diálogo no estaba entre los
      trece que llevan `hold_wrapped_height`.
    - **Reproducido en Windows** con la fuente medio punto mayor, que es lo que cambia en Linux: entre 1
      y 3 px por debajo con +0,5, +1, +1,5 y +2 puntos.
  - **(c) Las líneas de corriente** daban 13 de 22 terminaciones en el contorno con 3.11 y 11 con 3.12,
    frente a 17 en Windows. El test pedía tres cuartas partes.
    - **En 0.1.332 escribí algo falso.** Dije que las cinco terminaciones interiores eran «convergencia
      del campo discreto, no del trazador».
    - **Medido ahora**, con el mismo campo: un ruido relativo de 10⁻⁹ en las velocidades lleva el recuento
      de 16 a 19, y uno de 10⁻⁶, de 11 a 20. Toda parada interior era un nodo del que no sale
      estrictamente ninguna velocidad de sus elementos, y el redondeo decidía cuáles.
    - **Lo que se probó y se descartó:** suavizar la velocidad a los nodos e integrar ese campo continuo,
      lo habitual en el posproceso de elementos finitos. Dio 17 de 22, entre 13 y 16 con ruido, y un error
      tres veces mayor contra la solución cerrada.
    - **Un primer prototipo** de la solución que queda (seguir por la arista de salida) llegaba a 22 de 22,
      pero también deslizaba por el borde del modelo en los nodos del contorno: el 19 % del recorrido iba
      sobre aristas. Con la línea terminando en el contorno, el 5,4 %, y nada por el borde.
- **Lo que encontró la primera corrida de la suite (6257 de 6258):**
  - el test de términos de 0.1.323 busca «FoS» sin distinguir mayúsculas en cada valor del diccionario;
  - lo encontró en el **campo** `{fos:.3f}` de dos plantillas castellanas del desembalse;
  - el campo pasa a llamarse `{factor:.3f}`, y la frase no cambia.
- **Término incoherente** visto al escribir el castellano: el diccionario dice «desembalse rápido» y
  «descenso rápido» cinco veces cada una. Aquí se usa «desembalse rápido», y el resto va a D335.

## 1. Qué cambia

- **`ogr_core/messages.py`** (nuevo, sin Qt), el mecanismo, que también usará el DXF en 0.1.334:
  - `MessageSpec(code, english, group_by, kinds)`. `english` es una plantilla `str.format` con los
    mismos formatos que el f-string que sustituye (`"%.3g" % x` y `"{x:.3g}"` imprimen lo mismo);
  - `render` traduce, enseña los valores de un tipo declarado (un método por su nombre) y, con
    `elide`, da la etiqueta del grupo: los valores fuera de `group_by` pasan a «…»;
  - un mensaje puede ir dentro de otro (`nested`): el fallo de una etapa del desembalse lleva el de su
    método, con su código.
  - Nunca lanza ni pierde un mensaje: un código desconocido o una plantilla que no formatea dan la frase
    inglesa.
- **`ogr_slip2d/messages.py`** (nuevo), el catálogo del motor:
  - **41 códigos.** Los de cada método, los de la familia λ y de la inclinación prescrita, el fallo
    aritmético de la búsqueda, los tres cribados y los del desembalse;
  - **`failure(código, **valores)` e `inadmissible(…)`**: devuelven la frase y su código juntos, para que
    no se separen.
- **`LEMResult`** gana:
  - `message_code`, `message_args`, `note_code` y `note_args`, en `to_dict` (los valores no finitos,
    como cadena);
  - `set_error` y `set_note`, para lo que se escribe en un resultado ya construido.
- **El motor escribe sus razones por esas puertas:**
  - los siete métodos y `methods/base.py`;
  - la búsqueda;
  - los cribados: `checks.screen_verdict`, nuevo. `screen_surface` conserva su tupla de tres, que
    desempaquetan siete tests;
  - el desembalse: `RapidDrawdownError` lleva `code` y `values`, y `DrawdownStageFailed` anida el mensaje
    del método.
  - **El inglés no cambia ni un byte.**
- **El API** (`lem_summary`) añade los códigos solo cuando los hay. Una superficie válida se serializa como
  antes. `results_io` no cambia: es una exportación, y nadie la lee de vuelta.
- **`ogr_gui/core_messages.py`** (nuevo): traduce por código con `tr()` sobre la plantilla inglesa.
  - Los valores de tipo método salen con su nombre, y los modelos de resistencia, con el suyo.
  - Una frase sin código (la de un método de un tercero) sale tal cual.
- ***Interpretar*:**
  - **`invalid_reason` agrupa por la etiqueta del código.** En el segundo ejemplo, 49 grupos pasan a 3:
    «Momento motor nulo…», «m_alpha < 0.2 en … dovela(s)» y «Factor de seguridad sin sentido físico (…)
    en la iteración»;
  - la lectura al pasar el puntero, el resumen de inválidas y el combo «Código de error», en castellano;
  - **la ayuda de cada superficie inválida del lienzo** es su propia razón traducida, no la del grupo.
- **40 claves nuevas en el diccionario**, una por plantilla con palabras, con los mismos campos.
- **D338:**
  - (a) el test de D326 compara con `os.fsdecode`;
  - (b) *Importar DXF* lleva `hold_wrapped_height`;
  - (c) el trazador, en un nodo interior del que no sale ningún elemento, **sigue por la arista cuya media
    de elementos se aleja más deprisa** (`_node_outflow`), como ya hacía a lo largo de una arista.
    Termina en el contorno o en un sumidero: un nodo del que no sale ninguna arista.

## 2. Tests

- **`tests/test_core_messages_v1333.py`** (nuevo, 21 casos):
  - **el inglés de cada código, con una muestra, es igual a la expresión de 0.1.332, copiada literalmente
    en el test** (regla 1: la referencia es el código viejo, no lo que imprime el nuevo);
  - cada código tiene su muestra, y un castellano con los mismos campos que formatea;
  - **testigos en ejecución**, en los que la frase del código es la que lleva el resultado:
    - los nueve métodos sobre la masa simétrica de D56;
    - un desembalse cuya etapa falla;
    - los dos cribados, y uno que lanza;
    - un fallo aritmético;
    - y los códigos viajan por `to_dict` y el API;
  - **censo AST de `ogr_slip2d`:**
    - ningún `error_message=` ni `admissibility_note=` con una frase literal;
    - ninguna asignación fuera de `set_error` y `set_note`;
    - ningún `RapidDrawdownError` sin `code=`, salvo las dos negativas que no son de una superficie (a
      D335);
    - y un control de que el censo ve los más de cuarenta sitios;
  - **en castellano:**
    - tres rechazos de m-alpha con distinto número de dovelas son un grupo;
    - cada superficie conserva su frase;
    - un fallo de etapa sale en castellano en los dos niveles;
    - una frase sin código sale como está escrita;
    - y la ayuda del lienzo es la de cada superficie.
- **`tests/test_ci_linux_v1333.py`** (nuevo): *Importar DXF* con la fuente +0,5 y +1,5 puntos, sin caja
  aplastada. Deja la fuente como estaba.
- **`tests/test_streamlines_v1332.py`:** el caso del campo real pedía tres cuartas partes, un umbral leído
  en una máquina, y pasa a pedir lo que el trazador debe hacer:
  - toda terminación está en el contorno o en un sumidero;
  - el recuento no se mueve con un ruido relativo de 10⁻⁹.

  La validación cerrada no cambia (1,19 / 0,24 / 0,095 / 0,023 % con 10, 20, 40 y 80 divisiones).
- **`tests/test_console_language_demo_v1329.py`:** compara con `os.fsdecode`.

**Con el código de 0.1.332 fallan los 24 casos nuevos o cambiados:**
- los 21 de D314;
- el de *Importar DXF*: 25 de 26 y 24 de 27 px;
- los dos del campo real: el recuento sale 16, 17 y 18 con ruido.

Se corrió sobre un `git archive` de 0.1.332, sin el buscador editable.

## 3. Verificación

- **Los tests de esta versión:**
  - `test_core_messages_v1333`, 21/21;
  - `test_ci_linux_v1333`, 1/1;
  - `test_streamlines_v1332`, 9/9;
  - `test_console_language_demo_v1329`, 9/9.
- **Los vecinos**, 463/463 en 33 archivos (el diccionario, los censos de castellano, *Interpretar*, el
  desembalse, los cribados, los diálogos y los resultados), con el fallo del diccionario de §0 ya
  arreglado; y los 168 que leen las frases del motor en inglés (D56, el desembalse, los cribados, la
  familia λ, la falta de resistencia y m-alpha), antes de escribir el test.
- **Suite entera:**
  - la primera corrida, 6257/6258, con el fallo del campo `{fos}` (§0);
  - la segunda, 6258/6258, `EXIT=0`, 83 min.
- **Banco:**
  - `verificar_cierres.py` entero: 80 comprobaciones, 0 bajadas, y D338 **CUBIERTO POR TEST**. Su
    comprobación mide (c) en un campo propio, el talud de ejemplo con 146 elementos: 22 de 22
    terminaciones sin ruido y con cinco ruidos de 10⁻⁹, donde el trazador de 0.1.332 daba de 18 a 21;
  - instantánea `Evaluaciones/0.1.333`, D338 retirada, y D333–D337 abiertas en P8;
  - prompts (38) y auditorías con 0 ERROR en la raíz y en el 02.
- **Ningún número del motor cambia:** las frases son las de antes, byte a byte, y lo que se añade son
  campos. Las líneas de corriente son dibujo, y la validación cerrada no se mueve.

## 4. Pendiente

- **D314, segunda parte (0.1.334):** los problemas de la importación DXF, y la excepción del test de
  pantalla retirada.
- **D335** (abierta en esta versión): el resto de los mensajes del núcleo, familia a familia.
- **D333, D334, D336 y D337**, abiertas en esta versión al planificar la tanda.
- **La CI de Linux**, que hay que mirar tras el próximo *push*.
