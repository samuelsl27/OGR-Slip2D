# OGR Slip2D v0.1.254

**D97: un tipo de soporte que se mide desde su coronación se lee desde el
extremo más alto, decidido con una tolerancia relativa. Lo deciden igual el
motor, el tooltip del lienzo, el diagrama de fuerzas y la nota del muro.**
Hasta 0.1.253 la regla estaba rota de cuatro maneras.

Quinta versión de la tanda Help + D85, D251/D252, D253, D97, D128 y D131. El
pilote Ito-Matsui al revés se sumó a D97 sin número nuevo, por decisión de la
propietaria (2026-10-03).

## 0. Lo que se encontró

Un muro EFP (presión desde la coronación hacia abajo) y un pilote Ito-Matsui
(«from the top of the pile», Cai y Ugai 2000) declaran
`MEASURED_FROM_TOP`: cuál es su coronación lo dice la geometría, no el orden
de dibujo. Un soporte a nivel no tiene coronación y se rechaza (`no_crest`,
desde D62).

- **A nivel, por igualdad exacta.** `compute_support_effects` preguntaba
  `tail.y == head.y`. Un muro 1e-12 de su longitud fuera de nivel se saltaba
  el rechazo, y se medía desde el extremo que el redondeo dejaba más alto:
  justo el número plausible y erróneo que el rechazo dice evitar.
  `reversed_support_notes` ya usaba 1e-6 de la longitud.
- **El pilote al revés se integraba desde la PUNTA.** El motor le daba la
  distancia desde la coronación, pero `build_bond_profile` muestrea de
  cabeza a cola, y `force_at`/`resultant_arm` integran desde 0. En el caso de
  Cai y Ugai (2000): 810,45 kN/m dibujado de abajo arriba frente a
  152,59 kN/m de arriba abajo (×5,31), y Bishop 3,034 frente a 1,507, del
  lado inseguro.
- **El tooltip y el diagrama leían desde la cabeza fuera cual fuera el
  tipo.**
  - La «fuerza en el punto medio» del pilote al revés integraba la mitad de
    abajo: 1431,9 frente a 540,4 kN/m.
  - El «en la superficie de rotura» del diagrama no era el número del motor,
    ni siquiera el del motor viejo: con el pilote al revés, 1819,7 frente a
    los 810,5 del motor viejo, cuando lo correcto son 152,6.
  - Para un soporte a nivel que el análisis deja fuera, los dos daban
    números.
- **La nota del muro** (`retaining_wall_notes`) repetía `head.y == tail.y`,
  y su frase en singular no tenía verbo.
- **Un test vacío.** `test_efp_wall_v1122::test_a_horizontal_wall_is_refused_
  rather_than_guessed` ponía el muro horizontal de 41,5 a 45,5 en y = 8,1, y
  su círculo corta y = 8,1 en x = 46,92. Ninguna superficie cruzaba el muro,
  así que el rechazo nunca se preguntaba, y el test pasaba por una razón que
  no tenía nada que ver con él.

## 1. Los cambios

- **`ogr_core/support/support.py`:**
  - `LEVEL_TOL = 1e-6`, relativo a la longitud del propio soporte;
  - `SupportInstance.is_level()`.
- **`BondProfile.flipped()`** (`ogr_core/support/bond.py`): el perfil medido
  desde la cola. El segmento `i` es el `n − 1 − i`, y una estación en `d`
  pasa a `L − d`. Se construye una vez y se guarda, porque una búsqueda lo
  pide en cada superficie. `build_bond_profile` y su caché siguen de cabeza
  a cola.
- **`ogr_core/support/crest.py`** (nuevo): `crest_reading(support, stype,
  bond)` dice desde qué extremo se lee y con qué perfil orientado igual, o
  None si el tipo se mide desde la coronación y el soporte está a nivel. Es
  la única regla, y la preguntan:
  - el motor, en `compute_support_effects`, para la fuerza y para el brazo de
    la resultante;
  - el tooltip del lienzo, que con un soporte a nivel lo dice con `tr()` en
    vez de dar números;
  - el diagrama de fuerzas, con el eje en «distancia desde la coronación»
    para esos tipos y con la misma frase para el soporte a nivel.
- **`retaining_wall_notes`** usa `is_level()` y gana su verbo.
- `reversed_support_notes` comparte la constante, no la pregunta.
- **Tests existentes, a propósito:**
  - `test_efp_wall_v1122`: el muro horizontal pasa adonde el círculo lo
    corta, de 45,5 a 55 en y = 9, y se afirma la premisa (el mismo muro 1e-3
    fuera de nivel sí se calcula). Por decisión de la propietaria.
  - `test_support_reversed_v1138`: el docstring decía «the capacity comes out
    the same either way» para todo pilote; se corrige.

## 2. Tests

**`tests/test_support_level_tolerance_v1254.py`**, 11 casos.
- La premisa: el círculo corta el muro casi a nivel.
- **1e-12 de la longitud es «a nivel»** en los dos sentidos y en los dos
  órdenes de dibujo: rechazo con `no_crest` y el factor del muro dibujado
  exactamente a nivel.
- **1e-3 es una coronación:** el mismo precio en los dos órdenes, y el muro
  mueve el factor (regla 7 al revés: la tolerancia no se traga una
  inclinación real).
- La tolerancia es relativa: lo mismo en metros que en milímetros.
- La nota nombra exactamente lo que el motor rechaza, con verbo.
- **El pilote al revés es el mismo pilote:** fuerza, punto de aplicación y
  factor a 1e-12, con la fuerza en la intersección y en el centroide. Además
  es la forma cerrada de v1123, integrada desde arriba.
- El perfil volteado es la imagen especular.
- El diagrama da la fuerza del motor con un pilote y con un muro al revés; el
  soporte a nivel no recibe número ni en el diagrama ni en el tooltip, y lo
  dice; el tooltip lee el pilote desde arriba en los dos sentidos.

**Discriminación** contra 0.1.253, con el envoltorio sin buscador editable:
**9 de 11 fallan**. Pasan los dos controles: la inclinación de 1e-3 y la
premisa.

## 3. El banco

- **Censo** de los 230 modelos (`_auditoria/P5_0254/censo_coronacion_d97.py`,
  con el predicado escrito a mano para que diga lo mismo con cualquier
  motor): 36 con soportes y 4 medidos desde la coronación (los pilotes
  Ito-Matsui del 106, verticales y con la cabeza arriba). Ninguno está a
  nivel ni a menos de 1e-6 de su longitud de estarlo, y ninguno al revés.
  Cada evaluación del banco toma la misma rama que antes.
- **A/B árbol contra árbol de todo el 02** (`ab_d97.py`, d93dda1 frente a
  este): 194 modelos, **0 de 1821** números reales distintos, incluidos los
  cuatro pilotes del 106. Sustituye a la re-corrida entera del 02 (unas 15,6
  h).
- **`d97()`:**
  - en vivo:
    - el pilote de Cai y Ugai al revés es el mismo que al derecho
      (152,5946 kN/m) y es la forma cerrada a 1e-3 (152,4775);
    - el muro a 1e-12 de su longitud se rechaza con `no_crest` en los dos
      órdenes de dibujo;
    - y a 1e-3 vale 125,2857 kN/m en los dos;
  - por el AST del motor instalado: ninguna comparación exacta entre las
    cotas de `head` y `tail`;
  - el censo, el A/B y la discriminación archivados.

  Veredicto CUBIERTO POR TEST. Con 0.1.253 da NO SE SOSTIENE: 810,45 frente
  a 152,59 kN/m, el muro sin rechazar, y las dos comparaciones exactas en
  `retaining_wall_notes.py` y `support_integration.py`.
- **La discriminación** se midió dentro de un `git archive` de d93dda1. Ese
  árbol difiere de la copia de trabajo en una veintena de archivos que nadie
  ha tocado: están en CRLF en la copia de trabajo (`w/crlf`, de una
  extracción antigua con `core.autocrlf=true`) y en LF en el índice. Son
  solo finales de línea, y Python los lee igual.
- **Verificación entera:** 224 cierres y 0 bajadas.
- **Cierre del ciclo:**
  - instantánea 0.1.254;
  - a la ficha se le añadió, antes de retirarla, una nota de cierre (la
    regla única, lo que daban el diagrama y el tooltip viejos, y el test
    vacío de v1122);
  - D97 retirada (218 cerradas);
  - `PAQUETES` de P5 podado y la cadena tachada;
  - prompts regenerados;
  - auditorías del 02 y de la raíz con 0 ERROR;
  - instantánea con `--forzar`;
  - `--seco` completo tras retirar: 224 claves, iguales al JSON clave a clave.

## 4. Verificación

- **Suite entera:** 5577 de 5577.
- **Selección** de soportes, muros, pilotes, perfiles de adherencia,
  anclajes helicoidales, i18n, menús, lienzo y diagramas: 581 de 581
  (30 archivos).
- **Discriminación:** 9 de 11 contra 0.1.253.

**Qué falta por probar:**
- **En pantalla:** el diagrama de fuerzas de un pilote dibujado de abajo
  arriba, y el tooltip de un muro a nivel.
