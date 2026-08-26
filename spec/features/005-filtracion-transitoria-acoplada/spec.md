# Filtración transitoria no saturada acoplada al LEM

## Qué hace

Permite **decir dónde está el embalse** y llevar el campo de presiones de cada
instante de una filtración transitoria al análisis de estabilidad, con la
resistencia no saturada de Fredlund gobernada por φ_b.

Tres piezas:

1. **El embalse como condición de contorno geométrica.** Hasta ahora una
   condición sólo se podía asignar a uno de cuatro lados enteros —izquierdo,
   derecho, inferior y *la superficie del terreno completa*—, así que «carga
   total = 24,41 sobre el paramento sumergido» **no era expresable**: la habría
   puesto también sobre el coronamiento y el talud de aguas abajo. Un embalse
   pasa a ser **un número y un lado**, y el perímetro mojado sale de la
   geometría. Un desembalse es la misma orden con una cota menor.
2. **Un camino programático.** Toda la cadena —mallar, resolver, escalonar,
   calcular el factor por etapa— vivía dentro de `MainWindow`. Se extrae a
   `ogr_slip2d.transient_stability`, sin Qt, y la interfaz pasa a llamarla.
3. **El tope de succión** que la referencia documenta y OGR no tenía, para que
   φ_b no pueda convertir metros de succión en una cohesión que nadie midió.

## Por qué

El solver transitorio, el no saturado, φ_b en los nueve métodos, el acople
FEM→LEM y la serialización del campo existen y están validados desde v0.1.30.
Lo que faltaba no era la física: era **poder enunciar el problema** y **poder
correrlo desde fuera de la ventana**.

Es el hueco **D30** del banco de verificación (problema 102), una presa de
tierra homogénea con desembalse rápido.

## Criterios de aceptación

### La geometría, antes que ningún factor

Los seis círculos publicados dan dieciséis ecuaciones cerradas: cada
`(centro, radio)` corta el terreno exactamente en sus dos extremos publicados.
Eso **deriva** el coronamiento (28,600) y la explanada de aguas abajo (7,300),
donde los rótulos de la figura dicen 29 y 7.

### Los cuatro valores publicados que no dependen de k_s

| | Publicado | Criterio |
|---|---|---|
| Seco, Spencer | 2,455 | ±1 % |
| Permanente inicial, φ_b = 0 | 1,745 | ±2 % |
| Permanente inicial, φ_b = 37 | 1,815 | ±2 % |
| Permanente final (drenado), φ_b = 0 | 2,376 | ±2 % |
| Cociente φ_b, efecto solo | 1,0401 | ±1 % |

El manual publica 26 factores y **ningún parámetro hidráulico**, y el artículo
del que los toma es de pago. Un régimen permanente no depende de k_s, así que
esos cuatro sí están determinados por lo publicado y son el criterio de cierre.
Los 22 intermedios se miden y se publican como **medición**, nunca como
validación.

### El quinto no es un quinto

A 1500 h con φ_b = 37 el manual da 2,612, y **no es el permanente**: la leyenda
de su propia figura declara succión máxima 9,1 m donde el permanente exige 21,3,
y la columna de Huang y Jia sigue subiendo entre 1000 y 1500 h mientras que la
de φ_b = 0 ya no se mueve. Sólo se afirma la desigualdad que de ahí se sigue.

### Identidades

- Una cara de filtración y una carga prescrita **a la misma cota** son la misma
  condición: el factor no puede depender de cuál se escriba (≤ 0,2 %).
- El nivel embalsado **no existe** donde no se ha prescrito agua, igual que ya
  ocurría con las superficies dibujadas.
- Dos cuerpos de agua distintos no se interpolan el uno en el otro.
- Un desembalse es un subconjunto estricto del perímetro mojado anterior.

### Regla 7

El tope de succión mueve el número con φ_b = 37 y **no puede moverlo** con
φ_b = 0; el signo con que se escriba no cambia su significado; la cota del
embalse mueve el número; las condiciones de cada etapa viajan con la etapa, y
sin eso un desembalse conserva el peso del embalse vaciado.

## Fuera de alcance, y por qué

- **Los 22 factores intermedios como criterio.** Necesitan k_s, θ(ψ) y S_s, que
  no están publicados. Queda como **A102-1**.
- **Carga total variando linealmente** a lo largo de un contorno: la referencia
  le da página y ecuaciones propias y el 102 no la necesita.
- **Picar segmentos en el lienzo.** Es el mecanismo general de la referencia;
  el destino geométrico cubre el caso y el picado es trabajo de interfaz con su
  propia validación.
- **Un mando de tiempo continuo para el desembalse.** La referencia tampoco lo
  tiene: su ayuda dice que las condiciones se definen *en cada etapa*.
