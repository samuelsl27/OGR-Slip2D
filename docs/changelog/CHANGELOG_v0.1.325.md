# OGR Slip2D v0.1.325

**Una forma para cada término y una sola voz, tuteo, en el castellano de la
interfaz (D318).** Segunda versión de la tanda P8i.

## 0. Lo que se encontró

La tercera prueba de la interfaz (§5 del informe) listó pares que decían lo mismo de dos maneras. Al
contarlos en el diccionario, una forma era siempre la más usada:

| Queda | Sale | Recuento |
|---|---|---|
| B-barra | B-bar | 4 frente a 3 (y las dos en el mismo diálogo) |
| elementos finitos | FEA | 16 frente a 1 |
| superficie de rotura | superficie de deslizamiento | 12 frente a 9; la cabecera del diccionario ya la llamaba estándar |
| por defecto | predeterminado (en texto propio) | 19 frente a 1 |
| solo, este | sólo, éste | 52 frente a 10 (la RAE las recomienda sin tilde desde 2010) |
| contorno exterior | contorno externo | 17 frente a 12 (salió en 0.1.324) |
| tuteo | usted | unos 90 frente a 45 |

- **Más cosas en el mismo saco:**
  - el nombre inglés de un método o de un modelo dentro de una frase castellana («con el método
    Block Search», «un material Generalized Anisotropic», «Tipo de superficie = Non-Circular»);
  - *Definir soporte* en el menú frente a «Definir propiedades de soporte» en el título y «Definir
    soportes» en un aviso;
  - el paso de deshacer de colocar un soporte, que se llamaba igual que el menú («Definir soporte»).
- **Concordancia:** el desplegable de la norma de diseño usaba la clave genérica «None», que se traduce
  «Ninguno», así que se leía «Norma de diseño: Ninguno».
- **El grupo de *Preferencias* se titulaba «File» («Archivo»)** y contiene el idioma y el tema.
- **Los parámetros de las variables aleatorias y las ayudas de datos** se leían en latín («phi b»,
  «c inf»).
- **Lo que no se toca, y por qué:**
  - «Superficie freática» es la superficie libre que calcula la solución por elementos finitos, otra
    cosa que el nivel freático;
  - «Restaurar los valores predeterminados» es el texto del catálogo de Qt, no nuestro.

## 1. Qué cambia

Por decisión de la propietaria, la forma más usada en cada par:

- **78 valores del diccionario cambian:**
  - las 45 entradas en usted pasan a tuteo, con sus pronombres y posesivos («Cámbielos» → «Cámbialos»,
    «introducir los suyos» → «introducir los tuyos»);
  - B-barra, elementos finitos, superficie de rotura, solo, este y contorno exterior en todo el
    diccionario;
  - «anisótropo generalizado» y «búsqueda por bloques» dentro del castellano;
  - «Definir soporte» en el título y en el aviso;
  - «Colocar soporte», el paso de deshacer.
- **Dos claves propias:**
  - **«Interface»** («Interfaz»), para el grupo de *Preferencias*;
  - **«No standard»** («Ninguna»), para la norma de diseño.

  En inglés, el grupo pasa de «File» a «Interface» y la norma de «None» a «No standard».
- **Los parámetros por su símbolo en castellano:** φ, φb, φ1, φ2, φ0, φr, c∞, su mín, k_h y k_v. En inglés
  se leen como siempre, con la clave.
- **12 claves nuevas.**
- **Dos tests esperan ya los textos nuevos:**
  - `test_supports_spanish_v1322`: «Tangente a la superficie de rotura»;
  - `test_labels_spanish_v1321`: «coeficiente sísmico k_h».

## 2. Tests

`tests/test_voice_and_terms_v1325.py` (nuevo), 6 casos:

- ningún valor del diccionario conserva una forma retirada;
- ningún valor usa un imperativo de usted;
- las formas que quedan están donde estaban las viejas, y el paso de deshacer ya no se llama como el
  menú;
- **control:** «Superficie freática» y «Malla de elementos finitos» conservan su nombre;
- los parámetros se leen por su símbolo en castellano, y en inglés como siempre;
- *Preferencias* titula su grupo «Interfaz» y la norma de diseño dice «Ninguna»; en inglés, «Interface»
  y «No standard».

**Con el código de 0.1.324 fallan 5 de los 6 casos;** el control pasa en los dos árboles. Se corrió
sobre un `git archive` de 0.1.324, sin el buscador editable.

## 3. Verificación

- **Los tests de esta versión y de 0.1.318–0.1.324**, 137/138 a la primera.
  - El que falló fijaba lo que se corrige: «coeficiente sísmico kh» es ahora «coeficiente sísmico k_h»,
    por el símbolo. Pasa a medir lo nuevo, y después 1/1.
- **Los vecinos**, 1489/1489, en 82 archivos. Son los diálogos cuyo castellano cambia: preferencias,
  ajustes de proyecto, DXF, anotaciones, variables aleatorias, estadística, *Interpretar*, transitorio,
  presión intersticial en exceso, soportes, optimización y los tests de idioma.
- **Suite entera:** 6163/6163, `EXIT=0`, 78 min.
- **Banco:**
  - `verificar_cierres.py` entero: 65 comprobaciones, D318 **CUBIERTO POR TEST** y 0 bajadas;
  - instantánea `Evaluaciones/0.1.325`, D318 retirada y podada de P8;
  - prompts (45);
  - auditorías con 0 ERROR en la raíz y en el 02.
- **Ningún número del motor cambia:** es texto de pantalla.

## 4. Pendiente

- **D319–D330** (resto de P8i).
- **A mano, en la cuarta prueba de la interfaz:** leer los textos de ayuda y los avisos en tuteo.
