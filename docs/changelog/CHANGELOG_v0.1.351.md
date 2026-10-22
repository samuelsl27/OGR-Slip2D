# OGR Slip2D v0.1.351

**Por qué el modelo de resistencia de un material no se puede calcular lleva un código estable, y el
diálogo de materiales lo dice en castellano con sus valores (D335, quinta parte).** Duodécima versión de la
tanda P8k.

## 0. Lo que se encontró

- **El diálogo de materiales traducía estas negativas sin sus valores.** `_TABLE_REFUSALS` tenía 35 frases
  fijas, una por código de negativa: «la cohesión tiene que ser cero o más», pero no qué fila ni cuánto valía.
  Ahora el diálogo dice la negativa entera por su código, y la tabla sale con sus 32 entradas del
  diccionario (tres frases se repetían entre códigos).
- **El marco «Material 'x', <modelo>:» habría repetido el nombre.** El diálogo ya escribe «En el material
  x:», así que la negativa enmarcada se dice sin el marco, como hacían las frases fijas.
- **Cinco frases eran la misma en dos funciones**: el valor no finito de una fila y el de un punto, la
  resistencia de una fila y el final del último rango, en tablas distintas. Cada una es un código: dos
  plantillas con el mismo inglés serían la misma clave del diccionario.
- **Las razones por las que Snowden no construye una de sus dos funciones** (`IncompleteSnowden`) eran
  inglés que acababa dentro de la negativa como texto suelto. Tienen código, uno por papel
  (estratificación o macizo rocoso), y la negativa las anida.
- **Una etiqueta no la alcanza ninguna entrada**: «Rule n» con mayúscula inicial. La comprobación por ángulo o
  superficie recorre solo la base y las juntas. Se conserva, y el test sostiene las seis etiquetas contra las
  palabras del propio modelo (`GeneralizedAnisotropic.child_label`).
- **Una referencia distinta en esta versión:** en vez de evaluar cada expresión vieja, cada negativa se
  dispara con una entrada que la provoca, en el árbol de 0.1.350 y en este. Se compara la función entera
  (84 entradas), no cada plantilla.

## 1. Qué cambia

- **`ogr_core/project/messages.py`:** `STRENGTH_REFUSALS`, **76 códigos** `strength.*`:
  - el marco del material;
  - las tablas de la función tangencial/normal y la escalonada, la discreta, la c/φ y la de resistencia
    anisótropa;
  - Snowden: A y B, sus dos funciones y por qué no se construyen;
  - el lineal anisótropo;
  - el anisótropo generalizado: sus reglas, su entrada por ángulo o superficie con las etiquetas de cada
    hijo, sus vínculos y sus superficies;
  - las tres notas de archivos guardados por versiones anteriores.
- **`rules.py`** (13 funciones) y **`builtin_models.py`** (`SnowdenModifiedAnisotropicLinear.function`): cada
  negativa con su código; el código de cada `Refusal` no cambia.
- **El diálogo de materiales:** las dos negativas pasan por los códigos, y `_TABLE_REFUSALS` sale.
- **El castellano:** 76 entradas nuevas.

## 2. Tests

- **`tests/test_strength_refusals_v1351.py`** (nuevo, 8 casos):
  - **la frase y el código de cada negativa son los de 0.1.350**: 84 entradas que la provocan, con lo que
    dijo 0.1.350 congelado;
  - todo código se alcanza (salvo «Rule n», por lo dicho), y las etiquetas son las del modelo;
  - cada código tiene su castellano, con sus campos, y cada entrada se rechaza en castellano;
  - **censo AST** de las 14 funciones, salvo los nombres de las excepciones, que son datos;
  - **en el diálogo, en castellano:** la negativa de un vínculo con sus valores; la tabla de frases fijas ya
    no existe.
- **`tests/test_generalized_anisotropic_honest_v1225.py`, cambio deliberado:** comprobaba que cada frase de
  `_TABLE_REFUSALS` tuviera castellano.

**Con el código de 0.1.350 fallan los 8.** También los de comportamiento: el diálogo decía la negativa de un
vínculo con una frase fija, sin sus valores, y la tabla de frases fijas existía.

## 3. Verificación

- **El test de esta versión**, 8/8. En el primer intento fallaba uno, por el propio test: daba por mala
  cualquier llave en la frase, y el valor que rechaza una negativa de Snowden es un diccionario
  (`{'model_id': ...}`), que sale tal cual en los dos idiomas. Ahora busca un campo sin rellenar
  (`{nombre}`), que es lo que de verdad indica una plantilla rota.
- **Los vecinos:** 581/581, en 38 archivos: los modelos de resistencia, el diálogo de materiales, el
  anisótropo generalizado, Snowden, las funciones discretas, los materiales y el castellano.
- **El inglés y el código de cada negativa no cambian:** las 84 entradas dan lo mismo que en 0.1.350.
- **Suite entera:** 6445/6445, `EXIT=0`, 88 min.
- **Banco:**
  - raíz: `verificar_cierres.py` entero, 87 comprobaciones, 0 bajadas;
  - manual 02: `verificar_cierres.py` entero, 238 fichas, 0 bajadas;
  - D335, con su quinta parte apuntada;
  - instantánea `Evaluaciones/0.1.351`, prompts (34) y auditorías con 0 ERROR.
- **Ningún número del motor cambia:** solo cambia quién escribe la frase.

## 4. Pendiente

- **D335 sigue abierta.** Siguiente: filtración, transitorio, retroanálisis, barrido y Hoek-Brown (0.1.352).
