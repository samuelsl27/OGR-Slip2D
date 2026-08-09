# OGR Slip2D v0.1.73 — la dirección de rotura, dibujada y por fin con efecto

## El punto de partida: un ajuste casi decorativo

`failure_direction` existía desde v0.1.8, se guardaba en el `.ogr`, se
elegía en un desplegable de dos elementos… y se leía en **dos sitios**:
el ángulo de la fuerza de un sostenimiento
(`support_integration.py:353-360`) y una línea del informe PDF
(`report_generator.py:201`).

Todos los métodos de análisis deducen el sentido del deslizamiento de la
geometría de cada superficie (`slide_sign`, del signo de `Σ W·sin α`), así
que **en un modelo sin sostenimientos, invertir el ajuste no movía ningún
número**. Regla 7 en estado puro: un control que el usuario cree que el
análisis respeta y que el análisis ignora.

## La decisión que ordena esta versión, y lo que NO se hizo

La salida fácil habría sido enrutar el cálculo a través del ajuste. Sería
un error, y merece quedar escrito por qué:

- la deducción geométrica es **por superficie**, y un interruptor de
  proyecto no puede serlo;
- es más robusta: no hay forma de declarar mal la dirección y obtener un
  resultado silenciosamente equivocado;
- y la propia referencia lo confirma donde más se nota: dice que Path
  Search arranca **siempre** en el pie *con independencia* de la Failure
  Direction.

Cablear un ajuste a una pregunta que la geometría ya responde bien no lo
hace más honesto, lo hace peor. Lo que sí faltaba es lo contrario: los
sitios donde la geometría es **genuinamente ambigua** y algo tiene que
desempatar. Son pocos, y ahora son estos.

El convenio queda fijado en **un solo sitio**, el módulo nuevo
`ogr_slip2d/failure_direction.py`: *RIGHT_TO_LEFT significa que la masa se
mueve hacia x decreciente — coronación a la derecha, pie a la izquierda*.
No es una elección nueva: es el convenio contra el que ya estaba escrito
`support_integration` desde v0.1.64, y hay un test que obliga a los dos a
significar lo mismo.

## Corrección a lo que yo mismo había planificado

El plan decía cablear Path Search para que la dirección eligiera **qué
mitad de los slope limits** genera los puntos de inicio. Al leer el código
resultó estar equivocado: `search.py:1518-1523` ya deduce el pie como el
extremo más bajo de la cara del talud, que es exactamente lo correcto.
Cablearlo ahí habría deshecho el arreglo de la anomalía A1 (v0.1.24) y
puesto en riesgo `test_a2_slope_search_matches_reference`.

La ambigüedad real estaba **una línea antes**, y es más interesante.

## Cambios

### 1. Selector con dibujo, en lugar de un desplegable

`_FailureDirectionSelector` en la página General: dos opciones y un
dibujo del talud con una flecha en el sentido en que se espera que se
mueva la masa. Un desplegable de dos elementos se lee como una
preferencia; la dirección es una afirmación sobre el modelo, y «R2L» no
la dice.

Dibujado con `QPainter`, **sin ficheros de imagen**: cuarenta líneas pesan
menos que dos PNG, escalan con el DPI en vez de emborronarse en una
pantalla densa, y toman los colores de la paleta activa, así que el
widget sigue un tema oscuro sin un segundo juego de recursos. El perfil se
dibuja una sola vez —para coronación a la derecha— y se **espeja** sobre
la vertical para el otro caso: una forma, una transformación, y los dos
casos no pueden separarse con el tiempo.

### 2. La grieta de tracción ya no supone de qué lado está la coronación

`slicer.py` elegía la dovela aguas arriba iterando `reversed(slices)`,
bajo un comentario que admitía ser una suposición: *«assume rightward …
the up-slope end is on the right for a typical slope»*. Ahora lo decide
la dirección declarada.

Detalle importante: **solo se decide la ELECCIÓN de dovela**. El sentido
del empuje se deriva de la geometría desde v0.1.61 y no se ha tocado.

### 3. El terraplén simétrico deja de decidirse por orden de iteración

Path Search localiza la cara del talud como «el segmento de terreno más
inclinado», con un `>` estricto. En un terraplén simétrico —dos caras de
idéntica inclinación— **ganaba siempre la izquierda, por orden de
iteración y nada más**. Ese es el único punto de esta búsqueda donde la
geometría de verdad no basta, y donde la dirección es información que
falta en vez de una segunda opinión sobre algo ya resuelto.

El desempate se aplica **solo a empates** (dentro de 1e-6 relativo): una
cara que es genuinamente la más inclinada sigue ganando se ponga el ajuste
donde se ponga, así que un talud corriente de una sola cara —y con él los
casos validados— queda fuera del alcance de este cambio. Hay un test que
lo comprueba explícitamente.

### 4. Ambos cables se reducen al comportamiento anterior por defecto

No es casualidad, es el criterio con el que se eligieron: `reversed()`
= extremo derecho = coronación a la derecha = `RIGHT_TO_LEFT`, y «primera
cara más inclinada» = cara izquierda = pie a la izquierda = otra vez
`RIGHT_TO_LEFT`, que es el valor por defecto. **Ningún proyecto guardado
puede cambiar de factor de seguridad al reabrirse.**

## El hallazgo: por qué la suposición sobrevivió 66 versiones

El primer test de «esto mueve el número» **falló**, con los dos valores
idénticos hasta el último bit. La causa resultó ser instructiva.

El empuje llega a los métodos como una fuerza horizontal cuyo momento
respecto del centro del círculo es `y_c·F − F·y` (`slicer.py:111`): una
función de la fuerza y de la **altura de su línea de acción**, y de nada
más. Con una base de grieta **horizontal**, `F` y `y` son idénticos en
los dos extremos de la zona, así que qué dovela carga el empuje **no
cambia absolutamente ningún número**.

Es decir: la suposición era incorrecta desde v0.1.7 y, en todo modelo con
la grieta horizontal —que son casi todos, incluido el test que ya
existía—, **invisible en el resultado**. Solo cuando la base de la grieta
se inclina varían la altura mojada y el brazo con la abscisa, y entonces
el efecto es grande: en el modelo del test, `½·γw·hw²` pasa de 61 kN/m en
un extremo de la zona a 352 kN/m en el otro, y el factor de seguridad de
1.2053 a 1.1420 (5,3 %).

Eso está ahora fijado **como test**
(`test_a_horizontal_crack_hides_the_choice_entirely`), no como comentario,
porque además es el límite honesto de lo que esta versión arregla.

## Camino equivocado, y el que ya advertía la suite

El primer borrador del test de la grieta usaba un bloque rectangular de
100 × 30 como «talud». El factor de seguridad salió **−154**: sobre un
terreno horizontal el momento motor es cero y el cociente no significa
nada. Es exactamente la trampa que el docstring de
`test_material_sat_uw_v160` ya describía —«el terreno tiene que tener
pendiente: en un bloque horizontal el momento motor es cero»—, y aun así
volvió a aparecer. El test lleva ahora una comprobación de cordura
(`0.5 < FS < 3.0`) para que un fixture degenerado no pueda volver a pasar
por una comparación válida.

## Tests

`tests/test_failure_direction_v173.py` — 16 tests, uno por afirmación:

- **el convenio**, incluida la comprobación de que el módulo nuevo y
  `support_integration` significan lo mismo por las mismas palabras;
- **la grieta**: los dos extremos, el defecto que reproduce el
  comportamiento antiguo, el factor de seguridad que se mueve, y el caso
  horizontal que no se mueve y explica por qué;
- **el terraplén**: que las dos caras son de verdad igual de inclinadas
  (si no, el test estaría midiendo la comparación de pendientes en lugar
  del desempate), que cada dirección arranca de su lado, que el defecto
  conserva la cara antigua, y que **un talud de una sola cara es
  indiferente al ajuste**;
- **la interfaz**: que abre en la dirección del proyecto, que escribe al
  aplicar, que el dibujo se pinta en los dos estados —es código, no un
  recurso, así que puede fallar en ejecución como un PNG no puede— y que
  las dos etiquetas están traducidas.

**Probado**: la suite completa y los casos de validación.

**Falta por probar**: cómo se ve el dibujo en un tema oscuro real y en una
pantalla de alta densidad. Toma los colores de la paleta y escala con el
DPI por construcción, pero eso es un argumento, no una comprobación.

## Pendiente que esta versión deja anotado

**El rechazo de superficies contradictorias.** El efecto principal que la
referencia documenta para este ajuste es invalidar, con un código de
error, las superficies cuyo momento motor tenga signo opuesto a la
dirección declarada (su error −107). No se ha hecho aquí, por decisión
explícita: cambia qué superficies son admisibles y por tanto el mínimo
global, así que **antes hay que comprobar si rechazaría algún círculo de
los casos validados y reportarlo** (regla 6). Queda como candidato a
v0.1.76.
