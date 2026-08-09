# OGR Slip2D v0.1.75 — el exceso de presión intersticial, y las cargas lineales que por fin cargan

## Qué se buscaba

Implementar el **exceso de presión intersticial por carga no drenada**
(método B̄), la única casilla de *Project Settings* que seguía sin motor
tras la auditoría de v0.1.74.

## Lo que apareció por el camino, y por qué acabaron juntas dos cosas

Al ir a añadir la casilla «esta carga genera exceso de presión
intersticial» a los diálogos de carga, la comprobación previa dio un
resultado que cambió el alcance de la versión:

> **`ogr_slip2d` ignoraba las cargas lineales por completo.**

Cero referencias en todo el motor de equilibrio límite. Existían en el
modelo, se dibujaban, se guardaban, se exportaban a DXF y las minoraban
los coeficientes parciales de la norma de diseño — y el cálculo nunca las
leía. Medido antes de tocar nada:

| Modelo | FS |
|---|---|
| Sin carga | 1.218890 |
| **Carga lineal de 5000 kN/m** | **1.218890** (cambio: 0.00e+00) |
| Carga distribuida equivalente | 0.839161 |

Es la regla 7 en su forma más grave de las encontradas en estas cuatro
versiones: no es una casilla de ajustes, es **una carga que el usuario
dibuja sobre el modelo** y que el análisis descarta en silencio. Y falla
del lado inseguro, porque el usuario cree haber cargado el talud.

No tenía sentido añadir «esta carga genera exceso» a una carga que no
generaba ni siquiera peso, así que las dos cosas van en esta versión.

## Cargas lineales: cómo entran

- La **componente vertical** se suma a `weight`, exactamente como el
  recargo de una carga distribuida. Eso hace que las dos clases de carga
  sean consistentes entre sí, y el test lo fija con una **identidad**:
  una carga lineal de P y una distribuida cuya integral sobre la misma
  dovela sea P producen el mismo peso de dovela.
- La **componente horizontal** entra por el canal de fuerzas
  horizontales con brazo, el mismo que ya usaban el agua embalsada y el
  empuje de la grieta de tracción. Lo que ese canal modela es «una
  fuerza horizontal a una altura», que es precisamente esto.
- El intervalo de asignación a dovela es **semiabierto**. Una carga justo
  sobre un borde de dovela tiene que contarse una vez, ni dos ni
  ninguna; hay un test que lo comprueba sobre un borde real.

## Exceso de presión intersticial: la formulación

Skempton (1954): **Δu = B̄ · Δσv**, sumado a la presión intersticial
inicial que dé el método de agua del proyecto.

**El modelo de tensiones es unidimensional y no difunde.** Δσv en un
punto es la tensión vertical añadida directamente encima, transmitida
hacia abajo sin disminuir con la profundidad. No es una simplificación
elegida aquí: es lo que supone el método B̄, y la documentación de
referencia lo dice explícitamente — una carga «creará exceso en cualquier
material **debajo de la carga**». Nada de bulbo de Boussinesq.

Esto se investigó **antes** de escribir la fórmula, precisamente porque
el contrato del proyecto prohíbe inventar formulaciones geotécnicas: una
ecuación plausible pero incorrecta es el peor resultado posible aquí.
Mezclar un reparto elástico en un término mientras el del peso del suelo
seguía siendo edométrico habrían sido dos teorías distintas dentro de la
misma suma.

Tres fuentes, todas opcionales:

- **peso del material** — un material con `weight_creates_excess` carga
  todo lo que tiene debajo;
- **cargas externas** — distribuidas y lineales marcadas, solo componente
  vertical;
- **sismo vertical** — solo `kv`. El horizontal no contribuye nunca,
  marque lo que marque la casilla, porque no cambia ninguna tensión
  vertical.

**Las dos casillas del material responden a preguntas distintas**, y esa
es la distinción que más cuesta ver: `weight_creates_excess` dice si este
material **carga a los de debajo**; `b_bar` dice si este material
**desarrolla exceso él mismo**. Un terraplén sobre cimiento arcilloso
lleva la primera activada y B̄ = 0.

## Validación externa (regla 1)

Ninguna captura de lo que el código imprime hoy.

**1. Identidad de carga unidimensional.** Carga uniforme q = 37 kPa con
B̄ = 1: Δu = 37.0000000000 kPa **a 0.5, 1, 10, 25 y 29.5 m de
profundidad**, con error 0.00e+00. Esa es toda la afirmación de «no
difunde» en una sola aserción. Y Δu escala linealmente con B̄, exacto,
para cinco valores.

**2. El ejemplo del propio manual de referencia**, reproducido en
geometría. Terraplén de γ = 21 y 10 m sobre cimiento arcilloso:

| Punto | Δu |
|---|---|
| Arcilla, a −1, −5, −15 y −29.5 m | **210.0000 kPa** = 21 × 10, exacto y constante con la profundidad |
| Dentro del terraplén | **0.0000 kPa**, porque su propio B̄ = 0 |

La segunda fila es el detalle que separa las dos casillas, y el manual lo
narra con esas mismas palabras.

**3. B̄ = 0 no desarrolla nada**, con una carga de 5000 kPa encima.
Drenante libre por definición.

**4. La carga lineal pesa lo que debe**, por la identidad con la
distribuida equivalente descrita arriba.

## Un aviso que va junto a la fórmula, no en este archivo

Una **carga lineal es una fuerza concentrada**, así que la *tensión*
vertical que produce depende del ancho sobre el que se reparta — aquí, la
dovela. Refinar el rebanado hace crecer Δu bajo la carga. No es un
artefacto de esta implementación: la solución elástica también es
singular bajo una carga puntual. Pero significa que **una carga
distribuida es la forma correcta de modelar un recargo cuyo exceso de
presión importe**, y por eso el aviso vive en el docstring del módulo,
donde lo lee quien va a usarlo.

## Dos bugs que los tests cazaron al pasar

1. **`Modify Load` sobre una carga lineal existente reventaba siempre.**
   `_BaseLoadDialog` leía `existing.magnitude_1`, que solo tiene la carga
   distribuida; la lineal se llama `magnitude`. `AttributeError`, y el
   diálogo no llegaba a abrirse. Presente **desde v0.1.59, la primera
   versión pública**. Lo encontró el test que comprueba que la casilla de
   exceso se rellena al reabrir una carga.

2. **La casilla de exceso de los diálogos de carga no llegaba a ningún
   sitio.** `excess_pp()` existía y no lo llamaba nadie; el campo del
   modelo no existía. Además, al reabrir una carga se leía `excess_pp`,
   un atributo que ninguna clase de carga ha tenido nunca, así que
   siempre aparecía desmarcada — lo que nadie notó, porque tampoco se
   guardaba.

## Camino equivocado, otra vez el mismo

El primer test de «el exceso baja el factor de seguridad» comparó
`inf < inf`. El fixture era el bloque plano de 100 × 30 que uso para las
identidades 1-D, y sobre terreno horizontal el momento motor es cero. Es
la tercera vez que esta trampa aparece en cuatro versiones —ya la
documentaba `test_material_sat_uw_v160`—, así que el test lleva ahora una
comprobación de cordura `0.3 < FS < 3.0` **y** el comentario que dice por
qué el fixture tiene que tener pendiente.

Merece la pena decirlo claro: las identidades 1-D **necesitan** el bloque
plano, y la comparación de factores de seguridad **necesita** el talud.
Son dos fixtures porque son dos preguntas.

## Tests

`tests/test_excess_pore_pressure_v175.py` — 29 tests: la identidad 1-D,
el ejemplo del terraplén, el sismo (solo vertical), las cargas lineales,
el efecto sobre el factor de seguridad, la serialización de los cuatro
campos nuevos y la interfaz.

El grupo *Excess Pore Pressure* del diálogo de materiales, **aplazado a
propósito en v0.1.72** porque su motor no existía, entra aquí con él —
que era exactamente la condición que puse entonces para no repetir el
fallo de los coeficientes parciales.

**Probado**: la suite completa y los casos de validación.

**Falta por probar**: el exceso combinado con un análisis transitorio o
con una rejilla de presiones. Las tres opciones avanzadas de agua son
excluyentes entre sí, así que la combinación no es alcanzable desde la
interfaz, pero el motor no lo impide y no lo he ejercitado.

## Pendientes que esta versión deja anotados

1. **`ogr_cli` sigue sin aplicar el descenso rápido** — anotado en
   v0.1.72 y en v0.1.74, sigue ahí.
2. **El backlog frente a la referencia** de
   `docs/audits/project_settings_v174.md`, con *Data Output* a la cabeza.
3. **Las cargas lineales no aparecen en la salida de resultados** con el
   detalle que sí tienen las distribuidas; ahora que cargan, conviene
   revisarlo.
