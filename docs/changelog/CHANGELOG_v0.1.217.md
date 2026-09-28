# OGR Slip2D v0.1.217

Tercera y última de las versiones que cierran el paquete P4 del banco de
verificación. El Ordinario bajo un embalse:

- **D199 — la componente horizontal de la presión del estanque sale de la
  normal con la que el Ordinario lee su resistencia.** Un talud sumergido
  tiene ahora el factor de los pesos sumergidos a cualquier profundidad.
  Hasta aquí el factor crecía con el agua: 1,826 a 30 ft y 2,100 a 60 ft en el
  talud de Duncan & Wright (2005, Fig. 6.27), frente a 1,513.
- **D213 — en el camino no circular, el momento de las normales de base se
  toma de la normal total propia del método, `N′ + u·l`**, y no de la N sin
  corregir. Sin esto, D199 no se cumplía en poligonales. Abierta y cerrada
  en esta versión (sección 0).

Lo que cambia en el banco de verificación (`_tools/`, `_auditoria/`, fichas)
está fuera de git.

---

## 0. La fuente, y lo que decía el encargo

El encargo pedía leer Duncan, Wright & Brandon (2014), cap. 6, antes de decir
que la Ec. C-14 del EM 1110-2-1902 está mal, porque «decir que una fórmula
publicada está mal exige la fuente». La propietaria dejó el libro en
`referencias/Documentacion_Guia/` (2.ª ed.) y se leyó:

- **No trae el Ordinario con agua exterior.** «Because of its relative
  inaccuracy … the appropriate equations for additional known loads with the
  Ordinary Method of Slices are not presented here» (p. 93). En todo el libro
  no aparece `P·cos(α − β)`.
- **En Bishop, el agua sobre el techo entra en el equilibrio vertical solo por
  `P cos β`** (Ecs. 6.74–6.77). La componente horizontal va únicamente al
  momento.
- **§14.6 (p. 245), comprobaciones de un programa.** Un talud sumergido tiene
  que dar el mismo factor si el agua se modela como presión exterior o como
  «suelo» c = φ = 0. También deben coincidir pesos totales con presiones y
  pesos sumergidos sin agua: «Both approaches should give the same factor of
  safety». Solo avisan de los métodos de fuerzas.
- **Del Ordinario, la forma preferida es la del peso efectivo**, Ec. 6.59
  (Turnbull & Hvorslev 1967), que es la C-12 del EM.

Con eso la decisión no es «C-14 está mal», sino la coherencia de la C-12.

- C-12 toma el peso efectivo `W − u·b`, es decir, la componente **vertical**
  de la fuerza de poro de la base, y lo resuelve sobre la base.
- C-14 resuelve la presión del techo **entera**. Conserva así una componente
  horizontal cuya contrapartida en la base la C-12 ya había tirado.
- Tratada igual que la base, el agua entra por sus componentes verticales:
  `W + P_v − u·b`. Bajo un embalse en reposo eso es exactamente el peso
  sumergido.
- Una subida uniforme del embalse no cambia ninguna tensión efectiva y no debe
  cambiar el factor. Con C-14 lo cambiaba.

**Una fuente secundaria que no se usa como apoyo.** Pyke (2017, *The Ordinary
Method of Columns*) atribuye a Duncan, Wright & Brandon y a Whitman & Bailey
(1967) la recomendación de pesos sumergidos en el Ordinario. El libro no la
hace; Whitman & Bailey solo aparece citado por m_alpha (p. 240).

**D213: por qué es ficha propia y entra aquí.** En el talud sumergido como
poligonal, D199 solo no bastaba (1,749 a 30 ft, 1,981 a 60 ft). En el camino
general las normales de base tienen momento respecto del eje, y ese momento se
tomaba de la N sin corregir, cuya parte de poro es la de C-13: la misma
incoherencia que D197 quitó de la columna publicada. Con la normal total propia,
`N′ + u·l`, la poligonal da el factor sumergido a las dos profundidades
(1,514656 frente a 1,514655).

Mueve también las poligonales mojadas sin estanque, que el encargo de D199
prohibía tocar, así que se preguntó. La propietaria: «haz lo necesario para
cerrarlo, pero con lógica». El soporte sigue fuera de esa normal, como siempre
en este camino: su efecto entra por sus propios términos, y meterlo lo contaba
dos veces (v0.1.115). La rama general de Bishop ya tomaba su propia normal.

## 1. Los arreglos (motor)

- **`slicer._apply_ponded_water`** guarda además la componente horizontal del
  estanque en un campo nuevo de la dovela, `pond_force_h`, que llega a los
  métodos como `SliceForces.h_pond`. Hacía falta separarla: el agua de una
  grieta de tracción y la componente horizontal de las cargas lineales y
  repartidas van por el mismo acumulador, `water_force_h`, y esas **sí** siguen
  en la normal.
- **`methods.ordinary.POND_THRUST_OUT_OF_NORMAL`** (D199), en las dos ramas.
  Solo cambia la normal con la que se lee la resistencia. El lado motor
  conserva el momento de todo el agua: el de las presiones del techo es, con
  sumersión total, el del empuje de Arquímedes.
- **`methods.ordinary.MOMENT_NORMAL_OWN`** (D213), en el camino general.
- La tabla `INTERRUPTORES` del banco pasa a 22.

## 2. Medido

Talud del problema 70 (Duncan & Wright 2005, Fig. 6.27; c′ = 100 psf,
φ′ = 20°, γ = 128 pcf), con el agua a 30 y a 60 ft sobre la coronación, en su
círculo publicado:

| | 30 ft | 60 ft | pesos sumergidos |
|---|---|---|---|
| Ordinario, círculo, 0.1.216 | 1,8264 | 2,1002 | 1,5126 |
| Ordinario, círculo, 0.1.217 | 1,51269 | 1,51269 | 1,51260 |
| Ordinario, poligonal, 0.1.216 | 2,1183 | 2,7664 | 1,5147 |
| Ordinario, poligonal, solo D199 | 1,7492 | 1,9815 | 1,5147 |
| Ordinario, poligonal, 0.1.217 | 1,514656 | 1,514656 | 1,514655 |
| Bishop, círculo (control) | 1,60028 | 1,60028 | 1,60014 |

- El hueco del círculo es discretización: 5,8·10⁻⁵ con 50 dovelas y 3·10⁻⁶ con
  200.
- Las dos modelizaciones del EM (el agua como carga o como «suelo» sin
  resistencia), con 200 dovelas:
  - el Ordinario coincide a 2·10⁻⁵; en 0.1.216 difería un 21 % y un 39 %;
  - Bishop, el control, ya coincidía.

**Banco** (`_tools/censo_p4_0217.py`, búsquedas en serie, sin reescribir nada;
ninguna de estas filas tiene publicado del Ordinario):

| | 0.1.216 | 0.1.217 |
|---|---|---|
| 097 (desembalse Corps 2 etapas) | 0,805392 | 0,788538 (−2,09 %, otra superficie) |
| 098 | 0,821665 | 0,824890 (+0,39 %) |
| 100 (B-bar) | 1,241180 | igual |
| 101 (B-bar) | 1,413917 | 1,415956 (+0,14 %) |
| 052, poligonal «superficie4_humeda», D213 | 1,4255 | 1,3557 (−4,9 %) |

La fila del 052 está marcada MECANISMO NO REPRODUCIDO (publicado 0,799, OGR
+47,6 %), así que su movimiento, hacia el publicado, no prueba nada en ningún
sentido.

## 3. Tests

`test_ordinary_ponded_v1217.py`, 17 casos:

- **Invariancia con la profundidad**, en círculo y en poligonal, a 1e-9.
- **Peso sumergido**, en círculo (< 2e-4 con 50 dovelas, y con 200 menos de un
  cuarto de ese hueco) y en poligonal (< 1e-5).
- **Sumergido = seco con c = 0**, frente al talud seco con su peso total.
- **Las dos modelizaciones del EM**, con el Ordinario y con Bishop como
  control.
- **La suma de `pond_force_h`** es el empuje hidrostático sobre la proyección
  vertical del paramento. Se cumple a 1e-5 y no a redondeo: el círculo sale
  0,01 ft a la izquierda del pie y el corte del pie se funde con esa dovela,
  cuyo techo quebrado toma el empuje con la pendiente de la cuerda. Medido
  8·10⁻⁶.
- **Controles**:
  - sin estanque nada se mueve con D199: seco, freático dentro del talud,
    grieta llena de agua y carga lineal horizontal;
  - D213 no toca un círculo ni una poligonal seca;
  - D213 mueve una poligonal mojada (regla 7).

**Contra 0.1.216 fallan 9 de 17**: 7 por comportamiento y 2 por el campo nuevo
`pond_force_h`. Medido copiando el test a un árbol de 6635cdd extraído con
`git archive`. En 0.1.216 el talud sin cohesión sumergido daba 1,3438 donde el
seco da 1,0303.

Nada que ya existiera cambia: una selección de 464 casos (Ordinario, desembalse,
estanques, validaciones) pasa entera antes de la suite.

## 4. Verificación

- Suite entera: **4836 de 4836** (30 min 48 s).
- Banco, después del commit:
  - re-correr 097, 098, 101 y la mitad no circular del 052;
  - el censo con la versión publicada;
  - los cierres `d199()` y `d213()`.
