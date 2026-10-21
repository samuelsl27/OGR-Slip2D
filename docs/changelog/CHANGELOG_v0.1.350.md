# OGR Slip2D v0.1.350

**Por qué un proyecto no se puede analizar tal como está configurado lleva un código estable, y los
cuadros de negativa de la ventana lo dicen en castellano (D335, cuarta parte).** Undécima versión de la
tanda P8k.

## 0. Lo que se encontró

- **Los cuadros de negativa pasaban cada frase por `tr()`**, y `tr()` no encontraba nada. La clave
  llevaba los valores dentro («kh must not be negative, got -0.1.…»), así que no había entrada que casara.
  Lo hacían el retroanálisis, la estadística y la optimización. Calcular, el barrido de desembalse y el
  transitorio ni lo intentaban: unían las frases tal como venían.
- **Las dos negativas del desembalse para todo el cálculo no llevaban código.** D314 las dejó fuera a
  propósito (`_RUN_LEVEL_REFUSALS` en `test_core_messages_v1333`), y ahora lo llevan: esa excepción queda
  vacía.
- **Algunas frases mezclaban palabras inglesas que eran parte de la frase:**
  - el tipo de valor de la rejilla de presiones («total head»);
  - el nombre de un coeficiente parcial («permanent actions, unfavourable»);
  - el de la clase de un objeto de búsqueda por bloques.

  Ahora hay una plantilla por tipo y por coeficiente, y la etiqueta del objeto va con su traducción.
- **El nombre que el usuario da a un objeto no se traduce.** La etiqueta de un objeto de bloques es su
  nombre si lo tiene, y si no el nombre de su clase. Son dos códigos: el primero enseña el nombre tal cual,
  el segundo lo pasa por la traducción.
- **Un fallo mío, visto antes de probar nada:** `_compute_transient` usaba `note_text` sin importarlo, y
  habría lanzado `NameError` justo al negarse. La herramienta de nombres sin definir no lo veía, porque
  mira el módulo y no la función; ahora hay una que mira las importaciones locales.

## 1. Qué cambia

- **`ogr_core/project/messages.py`:** una tabla nueva, `REFUSALS`, con **24 códigos** `rule.*`: la técnica de
  optimización, las ventanas de los límites que se solapan, los objetos de búsqueda por bloques y sus
  etiquetas, los coeficientes sísmicos, los coeficientes parciales de la norma y las cargas lineales fuera
  del terreno. Va aparte de `RULES` porque el test de 0.1.347 exige una muestra de 0.1.346 para cada código
  de esa tabla, y estos códigos no existían entonces.
- **`ogr_slip2d/setting_messages.py`** (nuevo), **13 códigos** `setting.*`:
  - la rejilla de presiones de un tipo que el método contradice;
  - la carga lineal que hay que mover;
  - el campo de filtración que falta;
  - el coeficiente sísmico de la norma;
  - los ajustes retirados;
  - el desembalse: el procedimiento desconocido, el método de agua equivocado, sin materiales no drenados,
    la línea por encima del nivel freático y el método que no hace el desembalse.
- **`rules.py`, `loads.py`, `analysis_runner.py`, `rapid_drawdown.py` y `search.py`:** cada negativa con su
  código; las de todo el cálculo lanzan `RapidDrawdownError` con `code=`.
- **La ventana:** los seis cuadros (Calcular, barrido, retroanálisis, estadística, optimización y
  transitorio) pasan cada negativa por `note_text`; el método de agua se enseña con su etiqueta.
- **El castellano:** 34 entradas (los 37 códigos menos los 3 que no tienen palabras).

## 2. Tests

- **`tests/test_setting_refusals_v1350.py`** (nuevo, 9 casos):
  - **el inglés es el de 0.1.349, byte a byte:** 33 muestras de los 37 códigos, con las etiquetas y las
    negativas anidadas construidas con los catálogos nuevos;
  - cada código tiene su castellano, con los campos de la plantilla;
  - **censo AST** de las 12 funciones;
  - la negativa del desembalse para todo el cálculo lleva su código;
  - los seis cuadros de la ventana leen los códigos;
  - **en la ventana, en castellano:** el cuadro de Calcular con un coeficiente sísmico negativo, que solo un
    archivo puede dejar así; el API sigue respondiendo en inglés.
- **`tests/test_core_messages_v1333.py`, cambio deliberado:** `_RUN_LEVEL_REFUSALS` queda vacío.

**Con el código de 0.1.349 fallan los 9.** También los de comportamiento: el cuadro de Calcular decía en
inglés que kh no puede ser negativo, y la negativa del desembalse para todo el cálculo no llevaba código.

## 3. Verificación

- **El test de esta versión**, 9/9.
- **Los vecinos:** 935 de 936, en 48 archivos: los ajustes y sus negativas, el desembalse, los coeficientes
  de cálculo, el sismo, los bloques, la optimización, los límites del talud, las cargas, los mensajes del
  núcleo y el castellano. El que fallaba era `test_terms_spanish_v1323` (`test_a_magnitude_is_a_magnitude`):
  el castellano de la negativa de kh negativo decía «módulo» donde la regla del diccionario pide «magnitud».
  Corregida la entrada, 13/13 en ese archivo.
- **El inglés no cambia:** las 33 muestras del test son la expresión de 0.1.349, evaluada.
- **Suite entera:** 6437/6437, `EXIT=0`, 77 min.
- **Banco:**
  - raíz: `verificar_cierres.py` entero, 87 comprobaciones, 0 bajadas;
  - manual 02: `verificar_cierres.py` entero, 238 fichas, 0 bajadas;
  - D335, con su cuarta parte apuntada;
  - instantánea `Evaluaciones/0.1.350`, prompts (34) y auditorías con 0 ERROR.
- **Ningún número del motor cambia:** solo cambia quién escribe la frase.

## 4. Pendiente

- **D335 sigue abierta.** Siguiente: las negativas de los modelos de resistencia (0.1.351).
