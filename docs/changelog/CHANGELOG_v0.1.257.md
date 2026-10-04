# OGR Slip2D v0.1.257

**D238: la proyección de la Block Search sale del suelo por el corte exacto
de su rayo con el terreno, y ningún extremo de una superficie de prueba
queda bajo el terreno.** Hasta 0.1.256, `BlockSearch._project_to_top`
avanzaba por el rayo a pasos absolutos de 0,5 y devolvía el terreno bajo el
paso, no el corte. En el problema 109 del banco eso dejaba el extremo de la
crítica 0,99 m bajo la esquina del muro.

Segunda versión de la tanda P5.

## 0. Lo que se encontró

- **La marcha tenía cuatro defectos, y el peor no era el paso.**
  - El paso (0,5) y los márgenes (±1,0) eran absolutos: medio metro en un
    modelo en metros y medio milímetro en uno en milímetros.
  - Al cruzar el perfil devolvía `Vertex(x, top_y)`: la x del paso, hasta
    medio paso fuera del corte, y en una cara inclinada la cota del terreno
    en esa x, no la del rayo.
  - **El retorno del primer paso.** Si el primer paso ya caía sobre el
    terreno, devolvía `Vertex(x0, top_y)`: la x del PUNTO DE PARTIDA con la
    cota del terreno en el PASO. Se disparaba con cualquier punto de partida
    a menos de 0,5·sen(ángulo) del terreno, no solo con uno que estuviera
    sobre él. En una cara escalonada, esa cota es la del escalón de abajo.
  - Después, la ordenación por x y la deduplicación a 1e-3 absoluto
    conservaban el primero de dos puntos con la misma x. En el 109 se
    quedaba el extremo enterrado y se tiraba el arranque de la junta.
- **El arranque sobre el terreno es su propia salida.** Las juntas del 109
  empiezan en la esquina exterior de cada huella. Desde ahí, los rayos de
  135° y de 225° apuntan los dos al aire, así que la superficie termina en la
  propia esquina. El prompt pedía «saltarse el cruce trivial en t = 0», pero
  saltarlo siempre haría que el rayo de 225° «saliera» por el pie después de
  cruzar el aire: eso es una entrada, no una salida. La regla correcta es la
  primera transición de dentro a fuera del suelo a lo largo del rayo, con
  t ≥ 0.
- **«Sobre el terreno» se mide en perpendicular.** En las contrahuellas del
  109, inclinadas unos 8° respecto a la vertical, la distancia vertical es
  unas siete veces la verdadera.
- **El A/B lo confirma en el 109, y en ningún otro modelo había extremos
  enterrados.** Con la marcha vieja, 293 extremos de las superficies
  evaluadas del 109 quedaban bajo el terreno en su x; con el corte exacto,
  ninguno, ni en el 109 ni en los otros once modelos de bloque.
- **El 109 SUBE, y se aleja aún más del manual.** La crítica vieja ganaba
  factor arrancando 0,99 m bajo la esquina del muro, con una cara vertical
  sin resistencia (que es D244). Bishop pasa de 4,684 a 4,906. D238 no
  explica la distancia del 109 al manual (1,799), como ya medía la variante
  «d238» de 0.1.233 (5,17); queda en D243.
- **Una sorpresa, investigada antes de seguir (regla 6): el Sarma 3 en
  Spencer salta de 1,5237 a 2,2241 (+46 %)**, mientras Bishop se mueve
  +0,33 % y GLE +0,54 % en el mismo modelo. No es D238. Emparejando las
  candidatas de los dos métodos, con el interruptor apagado y encendido
  (`_auditoria/P5_0257/sarma3_spencer_d238.py`):
  - la candidata crítica de Bishop cambia un poco de forma con el corte
    exacto (Bishop 1,2254 → 1,2294);
  - en la nueva, Spencer no cierra λ: −111, «the λ bracket did not close;
    F_f − F_m is 0,0156 at λ = 0,507». Es el salto de g(λ) de D254 (abierta
    en P2), que con 0.1.255 caía solo en candidatas de factor alto;
  - sin ella, el mínimo de Spencer cae a la candidata siguiente (Bishop
    1,4531, Spencer 2,2241).

  Se anota en la ficha de D254, sin número nuevo: «no mueve ningún mínimo»
  deja de ser cierto. La fila del Sarma 3 no se mueve, porque la comparativa
  toma el mínimo de sus dos búsquedas y manda la circular (Spencer 1,0272).

## 1. Los cambios

- **`ogr_core/geometry/ground.py`: `ray_ground_exit(profile, x0, y0, angle,
  tol)`**, exportada desde `ogr_core.geometry`:
  - recoge cada parámetro t ≥ 0 donde el rayo toca un segmento del perfil
    (también los verticales, y los dos extremos de un tramo colineal), más
    el punto donde el rayo sale del tramo en x del perfil;
  - funde los cortes más cercanos que `tol` (un vértice lo tocan sus dos
    segmentos);
  - clasifica cada tramo entre cortes por su punto medio con `envelope_y_at`;
  - la salida es la primera transición de dentro a fuera, y se devuelve el
    punto **del rayo**, que está sobre el perfil: en una cara, en un llano o
    a media altura de un escalón vertical;
  - devuelve `None` si el rayo se mete en el suelo y no vuelve a salir, si
    deja el tramo del perfil antes, o si el punto de partida está en el aire.
- **`BlockSearch._exact_ends`**: con el interruptor encendido, cada extremo
  es la salida del rayo desde el punto de cadena más exterior.
  - Si la salida es el propio punto (arranca sobre el terreno y el rayo sale
    al aire), la superficie termina ahí.
  - Si queda más allá del punto, de su lado, es el vértice extremo nuevo.
  - En otro caso la candidata se rechaza: una salida con la misma x y otra
    altura es un tramo vertical, que la referencia prohíbe, y una salida del
    lado contrario es un rayo que vuelve sobre la superficie. Hasta 0.1.256
    la ordenación la metía en medio y construía otra superficie sin decirlo.
  - Los puntos de cadena conservan su deduplicación de siempre.
- **La tolerancia de «sobre el terreno»**, `BLOCK_ON_GROUND_REL = 1e-6` de la
  diagonal del modelo, la misma fracción que la rejilla del rebanador.
- **Interruptor `ogr_slip2d.search.BLOCK_EXACT_EXIT = True`.** Al apagarlo
  vuelve la marcha vieja entera. Entra en `INTERRUPTORES` del banco con
  (0, 1, 257). **El número de sorteos no cambia**: el corte decide dónde
  termina una superficie, no cuántos números aleatorios se sacan.

## 2. Tests

**Nuevo `tests/test_block_exit_v1257.py`**, 14 casos:
- sobre un perfil a mano ((0,10)-(20,10), escalón vertical a (20,20), cara
  1:2 a (40,30) y coronación a (60,30)), el corte calculado a mano:
  - por la cara (x = 70/3);
  - por la coronación (x = 55);
  - a media altura del escalón vertical (y = 12 + 5·tan 10°);
  - desde el terreno, hacia dentro del suelo y fuera otra vez;
  - un rayo que se mete en el suelo y uno que parte del aire no tienen
    salida;
  - el mismo punto en proporción con el perfil ×1000;
- desde la cima del escalón, los rayos de 135° y de 225° salen en el propio
  punto (el de 225° aterrizaría en el pie después de cruzar el aire);
- sobre un escalonado con contrahuellas inclinadas, como el 109, y una
  polilínea de bloque que arranca en la esquina de la huella, con las
  candidatas registradas en lugar de evaluadas:
  - toda superficie empieza en la esquina;
  - ningún extremo queda bajo el terreno en su x;
  - el extremo derecho está sobre el perfil y sobre la recta de 45° desde el
    último punto de cadena;
  - el modelo en milímetros da las mismas superficies en proporción;
- con el interruptor encendido y apagado, los mismos sorteos y las mismas
  60 candidatas (control).

Una suposición mía corregida al escribirlo: el caso del extremo derecho
pedía y = 7, la coronación. Cerca de la esquina, la junta del modelo pasa un
milímetro por debajo de la huella, que buza hacia atrás, y los rayos de 45°
salen por la huella. La identidad que se comprueba es la del punto sobre el
perfil y sobre la recta del rayo.

**Discriminación** contra un árbol de 0.1.256 (el de trabajo antes de D238),
con el envoltorio sin buscador editable: **fallan 12 de 14**. Cuatro fallan
por comportamiento, con el arranque en (10,2; 5,0), un metro bajo la
esquina: la esquina, ningún extremo enterrado, el extremo derecho y los
milímetros. Los otros ocho fallan porque la función es nueva. Pasan la
premisa y el control de los sorteos.

## 3. El banco

- **A/B en el mismo proceso, con el interruptor** (`_auditoria/P5_0257/
  ab_d238.py` → `ab_d238_0.1.257.json`): los 12 modelos con Block Search,
  todos sus métodos, 55 filas. Ninguna búsqueda de bloque se reparte entre
  procesos, así que el interruptor llega a todo lo que se mide.

  | modelo | método | marcha vieja | corte exacto | cambio |
  |---|---|---|---|---|
  | 007 | Bishop | 1,235199 | 1,234908 | −0,02 % |
  | 007 / 008 | Spencer | 1,292996 | 1,296274 | +0,25 % |
  | 007 / 008 | GLE | 1,281597 | 1,281588 | −0,001 % |
  | 007 / 008 | Janbu corregido | 1,310139 | 1,309872 | −0,02 % |
  | 009 | Spencer | 0,710061 | 0,708226 | −0,26 % |
  | 009 | GLE | 0,681768 | 0,679707 | −0,30 % |
  | 009 | Janbu corregido | 0,695630 | 0,693343 | −0,33 % |
  | 020 (bloque) | Bishop | 0,942034 | 0,941515 | −0,06 % |
  | 020 (bloque) | Spencer | 1,049876 | 1,050725 | +0,08 % |
  | 075 (bloque) | Bishop | 1,130242 | 1,130161 | −0,01 % |
  | 075 (bloque) | Spencer | 1,200111 | 1,200654 | +0,05 % |
  | 075 (bloque) | GLE | 1,176474 | 1,176562 | +0,01 % |
  | **109** | Bishop | 4,684206 | 4,906490 | **+4,75 %** |
  | **109** | Janbu simplificado | 4,301805 | 4,578378 | **+6,43 %** |
  | **109** | Spencer | 4,848857 | 5,053822 | **+4,23 %** |
  | **109** | GLE | 4,870487 | 5,138818 | **+5,51 %** |
  | Sarma 1 | seis métodos | — | — | de −0,41 % a +1,92 % |
  | **Sarma 3** | Spencer | 1,523696 | 2,224077 | **+46 %** (D254, arriba) |
  | Sarma 3 | los otros cinco | — | — | de −0,68 % a +0,54 % |
  | Sarma 4 y 5 | los que tienen factor | — | — | de −0,19 % a +1,86 % |

  - Los extremos evaluados bajo el terreno: 293 en cada método del 109 con
    la marcha vieja, 0 con el corte exacto; 0 y 0 en los demás modelos.
  - Las válidas del 109 se duplican (Bishop 533 → 1042): las candidatas que
    la marcha vieja tiraba ya no se tiran.
  - El 008 da, en los tres métodos que comparte con el 007, los mismos
    números que el 007.
  - En el Sarma 4 (los dos modelos) y en el `modelo_gw981` del 5, Bishop,
    Spencer y GLE no dan ninguna superficie de bloque válida, ni con la
    marcha vieja ni con la nueva. Sus filas del banco son de superficie
    publicada (`--solo-publicado`) y no usan esta búsqueda.
- **Las re-corridas con 0.1.257:**
  - del 02: `ejecutar_caso.py` de 007, 008, 009 y 109, y
    `correr_no_circular.py --forzar 20 75` (con su optimización);
  - de la raíz: `correr_banco.py --banco 03 1 3 4 5 --forzar`. Los
    `resultados.json` del 4 y del 5 eran de 0.1.159 y son de superficie
    publicada, así que lo que cambian entre 0.1.159 y 0.1.257 es de las
    versiones intermedias, no de D238, que solo toca la Block Search;
  - las comparativas del 02 y de la raíz, regeneradas.
- **`d238()`**, en el verificador del 02:
  - en vivo, los tres cortes a mano, en metros y en milímetros;
  - el 109 corrido con 0.1.257: ningún extremo de la crítica de ningún
    método bajo el terreno;
  - el A/B: las 55 filas medidas en los dos estados y 0 extremos enterrados
    con el corte exacto;
  - la discriminación.

- **Una bajada en la raíz, deshecha midiendo otra vez.** La re-corrida dejó
  en 0.1.257 el `resultados.json` del Sarma 3, y el cierre de D131 (CIERRE
  DOCUMENTAL, 0.1.255) exige el censo por candidata de esa misma versión. En
  seco pasaba a SIGUE ABIERTO. Se repitió `_tools/medir_bloque_sarma3.py`
  con 0.1.257 (`_auditoria/SARMA3_BLOQUE_0.1.257.json` de la raíz):
  - el rechazo geométrico común baja de 2079 a 2065;
  - Spencer pierde 133 de las válidas de Bishop y GLE 36, y abrir λ no
    recupera ninguna (no es D143);
  - entre las de Spencer está ahora la crítica de Bishop.

  Las notas del 3 lo dicen con un párrafo para 0.1.257, que deja el de
  0.1.255 tal cual porque era cierto con aquel motor. D131 vuelve a cerrar.
- **Verificación entera del 02:** 227 cierres y 0 bajadas. **De la raíz:**
  0 bajadas (cierran D121 y D131).
- **Cierre del ciclo:**
  - instantánea 0.1.257 del 02 y de la raíz;
  - D238 retirada, con su nota de cierre en la ficha;
  - `PAQUETES` de P5 podado y la cadena tachada;
  - prompts regenerados (las 15 FALTA de siempre);
  - auditorías del 02 y de la raíz con 0 ERROR. Los cuatro AVISO nuevos del
    02 son de frescura: las fichas `.md` del 007 y del 109 citan los
    factores viejos;
  - instantánea del 02 con `--forzar`;
  - `--seco` completo comprobación a comprobación contra una copia del motor
    de este árbol: los 227 veredictos, iguales al JSON. Tres detalles
    difieren en los contadores que crece el propio cierre (los `.ogr` de
    D96, las claves de D186, las citas del índice de D188: 173 → 174).

## 4. Verificación

- **Suite entera:** 5623 de 5623.
- **Selección** de Block Search, terreno, geometría, desigualdad de
  búsquedas, *Surface Options* y versión: 300 de 300 (20 archivos).

**Qué falta por probar:** nada en pantalla. La versión no toca la interfaz.
