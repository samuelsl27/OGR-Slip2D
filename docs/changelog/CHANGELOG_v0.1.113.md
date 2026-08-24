# OGR Slip2D v0.1.113

**El refuerzo va PARALELO al soporte, lo dice la guía en la página del
propio tipo, y lo que impedía que la paralela aterrizara era otro defecto:
el eje sobre el que se proyectaba la fuerza**

---

## Empieza corrigiendo v0.1.112

En v0.1.112 se arregló el **sentido** de la fuerza del refuerzo. Al cerrar
la anomalía, el modelo del problema 47 se dejó declarando
`TANGENT_TO_SLIP` **porque era la única orientación dentro del ±3 %**:

| orientación | Δ vs 0,890 |
|---|---|
| `TANGENT_TO_SLIP` | **+2,30 %** |
| `PARALLEL_TO_SUPPORT` | +4,60 % |
| `BISECTOR` | +4,86 % |
| `HORIZONTAL` | +5,11 % |

Eso es ajustar el modelo al resultado, que es exactamente lo que prohíbe
la regla 1 de este proyecto. El propio changelog de v0.1.112 dejó escrito
lo incómodo —«la guía v6 afirma que para bulones la fuerza se asume
PARALELA, y esa es justo la que se queda a +4,60 %»— y aun así se eligió
la que ajustaba.

La guía no deja margen. **Página por página, en la del propio tipo de
soporte**:

| Tipo | Force Orientation | Force Application | OGR hasta 0.1.112 |
|---|---|---|---|
| End Anchored | *always PARALLEL* | Active | ✔ ✔ |
| Grouted Tieback | *always PARALLEL* | Active | ✔ ✔ |
| **Soil Nail** | ***always PARALLEL*** | ***Passive*** | **BISECTOR ✘ / ACTIVE ✘** |
| **Micro Pile** | ***default TANGENTIAL*** | Passive | **PERPENDICULAR ✘** / ✔ |
| **GeoTextile** | elige el usuario | ***Passive*** | PARALLEL / **ACTIVE ✘** |

Cuatro valores por defecto contradecían la fuente, y desde v0.1.112 pesan
más que antes, porque `SupportInstance` ya los **hereda**. Los cuatro
corregidos.

## El segundo defecto, que es el grande

Declarar la paralela, con el código de 0.1.112, **empeoraba** el problema
47. Investigar por qué destapó lo siguiente.

Las ecuaciones de la referencia, una sola pareja para los cuatro métodos
de cociente:

    Activo   F = (R + T_N·tanφ') / (D − T_S)
    Pasivo   F = (R + T_N·tanφ' + T_S) / D

`T_S` es la componente **sobre la BASE** de la dovela. Janbu obedecía el
primer término y no el segundo: `T_N·tanφ'` venía de la referencia —y
estaba comentado como tal— mientras `T_S` estaba sustituido por la
componente **horizontal** de la fuerza. La misma ecuación, un término
tomado de la fuente y el otro cambiado.

**El changelog de v0.1.64 se contradice a sí mismo en la misma página**:
lista a Janbu entre los «métodos de cociente» con la fórmula de arriba y,
un párrafo antes, lo desvía a la horizontal con el argumento de que
«Janbu equilibra Σ W·tan α + Σ kh·W, una suma de fuerzas horizontales».

Ese argumento no sobrevive a la aritmética. Con φ' = 0 un término de
dovela de Janbu es `c'·b/cos²α = c'·l/cos α` y el motor es
`W·tan α = W·sen α/cos α`: **los dos lados son magnitudes de cortante con
un `1/cos α` común**. Una fuerza horizontal H encaja en ese peso por
accidente —su cortante motor `H·cos α` dividido por `cos α` devuelve H,
que es justo por qué el sismo y el empuje del agua se suman crudos— pero
un soporte en un ángulo cualquiera, no.

## Cómo se decidió: seis puntos publicados del mismo muro

El problema 48 del manual (muro Clouterre, Sheahan 2003) publica el factor
de seguridad para **seis** ángulos de plano de rotura. Eso es lo que
permite decidir una formulación: **un error de formulación deja tendencia
a lo largo de la curva y uno de geometría no**.

| ángulo | Slide | Sheahan | horizontal | **T_S** | T_S/cos α |
|---|---|---|---|---|---|
| 45° | 1,123 | 1,176 | 1,2057 (+7,4 %) | **1,1269 (+0,35 %)** | 1,1728 (+4,4 %) |
| 50° | 1,043 | 1,070 | 1,1474 (+10,0 %) | **1,0393 (−0,35 %)** | 1,1033 (+5,8 %) |
| 55° | 0,989 | 0,989 | 1,1178 (+13,0 %) | **0,9845 (−0,45 %)** | 1,0588 (+7,1 %) |
| 60° | 0,945 | 0,929 | 1,0983 (+16,2 %) | **0,9281 (−1,79 %)** | 1,0191 (+7,8 %) |
| 65° | 0,922 | 0,893 | 1,1026 (+19,6 %) | **0,8931 (−3,13 %)** | 0,9993 (+8,4 %) |
| 70° | 0,923 | 0,887 | 1,1406 (+23,6 %) | **0,8815 (−4,49 %)** | 0,9959 (+7,9 %) |
| | | **error medio** | **14,96 %** | **1,76 %** | 6,90 % |

Y con eso, **cada problema aterriza con la orientación que la guía
documenta para SU tipo de soporte**, que es la comprobación que de verdad
cierra el asunto:

| problema | orientación documentada | OGR | publicado | Δ |
|---|---|---|---|---|
| 47, plano publicado | PARALLEL (bulón) | 0,8876 | 0,890 | **−0,27 %** |
| 47, contra la fuente original | | 0,8876 | 0,887 (Sheahan) | **+0,07 %** |
| 85 circular, activo | (elige el usuario) | 1,5562 | 1,531 | +1,64 % |
| 85 circular, pasivo | (elige el usuario) | 1,3270 | 1,324 | **+0,23 %** |
| 54, círculo sin pilote | — | 1,1011 | 1,102 | **−0,08 %** |

**La tabla del problema 47 se da la vuelta entera**, y esa permutación es
la firma del defecto: `HORIZONTAL` con T_S da 0,9104, que es exactamente
lo que daba `TANGENT` con el eje horizontal. Las dos implementaciones
estaban **transpuestas**.

Y el argumento del ángulo crítico con el que se justificó la tangente en
v0.1.112 —44,0° medidos frente a 44,17° del panel— era **débil**: el
mínimo de la curva es plano, y con la paralela cae en 45,5° con sólo un
0,1 % de diferencia en el factor. No discriminaba nada.

## Dos hipótesis medidas y descartadas

**`T_S / cos α`**, el peso estricto que sugiere el álgebra de Janbu:
cuatro veces peor que `T_S` sobre los seis planos.

**El pasivo dividido por F** merece más espacio, porque es la que volverá.
Es el **Método B de Duncan y Wright (2005)**, que factoriza la fuerza del
refuerzo por F igual que la resistencia del suelo, y es **lo que el propio
docstring de `support_integration` afirmaba que OGR hacía** desde v0.1.14.
Mejora el problema 48 —0,71 % de error medio, y **quita la tendencia
residual**— y arregla el 54 (+0,16 %). Pero **rompe el 85**, que es el
caso que la referencia publica precisamente para comparar activo con
pasivo y que viene del propio Duncan y Wright: su pasivo publicado pasa de
**+0,23 % a −5,91 %**.

Descartada por eso, y con un test que la deja fuera —
`TestPassiveIsNotDividedByF`— porque dos de tres problemas la respaldan y
sin ese test volvería.

## El micropilote, investigado a fondo

El manual publica **dos** círculos para el problema 54, uno por figura, y
`referencia.json` sólo tenía uno: el caso sin pilote se comparaba contra
el círculo *con* pilote, que es otra superficie.

Con el círculo que le corresponde, el término del suelo resulta ser
**exacto**: Bishop da **1,101094** frente a 1,102 (**−0,08 %**) y sale del
terreno en x = 9,866 frente a 9,867 publicado. Luego lo que quede está en
el término del pilote, y no en el troceado ni en la geometría:

| | FoS | Δ vs 1,193 | aporte efectivo |
|---|---|---|---|
| `TANGENT_TO_SLIP` (la documentada) | 1,2118 | +1,57 % | 11,34 kN/m |
| `PERPENDICULAR_TO_PILE` | 1,1862 | −0,57 % | 8,54 kN/m |
| **lo que necesita la referencia** | 1,193 | — | **9,28 kN/m** |
| *declarado en el enunciado* | | | *10,70 kN/m* |

Se declara la **tangencial** porque es la que documenta la guía, con su
razón mecánica —*el pilote rompe a cortante a través de su sección sobre
el plano de deslizamiento*—, **no porque ajuste**: ajusta un punto peor.
Elegir la perpendicular para ganar un 1 % sería repetir el error que esta
versión viene a corregir.

Ninguna de las dos da los 9,28 kN/m. Con la tangencial el aporte **no
depende del ángulo de la base**, así que la posición del pilote —medida en
la figura— no puede explicarlo. Queda anotado como defecto abierto en vez
de inventarle una explicación.

## Lo que arrastra: A48-1 estaba mal atribuida

La ficha del problema 48 culpaba al guardia `circle_R is not None` de
`spencer.py` y `bishop.py` —la familia de A42-1 (agua) y A62-1 (sismo)—
apoyándose en que **Spencer no contaba el refuerzo**. Esa mitad era cierta
y era el defecto **D09**, cerrado en v0.1.105 al llevar el eje de momentos
a los cuatro métodos de momentos. Spencer hoy sí lo cuenta: 0,8701 →
1,0868 a 45°.

**Y el problema 48 no se movió entonces.** Eso ya era la señal de que la
causa del +7…+24 % era otra, y nadie la leyó así durante ocho versiones.

## Cambios

### Corregido

- `ogr_slip2d/methods/janbu.py` — el refuerzo entra por `T_S`, la
  proyección sobre la base, como en Bishop y Ordinary y como escribe la
  referencia. `h_active` / `h_passive` **se borran** de `SupportTerms`,
  no se dejan sin usar: un campo muerto invita a volver a enrutar un
  método por él.
- `ogr_core/support/support.py` — cuatro valores por defecto alineados
  con la guía: `SoilNail` a PARALLEL + PASSIVE, `PileMicropile` a
  TANGENT_TO_SLIP, `Geosynthetic` a PASSIVE.
- El docstring de `support_integration` decía que el pasivo iba dividido
  por F. No lo hacía, y no debe: ahora lo explica con la medida que lo
  descarta.

### Añadido

- `tests/test_support_projection_v1113.py` — 11 casos. Anclas externas:
  los seis planos publicados del Clouterre, el muro de Amherst con la
  orientación documentada (±1 %), y el caso de Duncan y Wright con su
  activo, su pasivo y el orden entre los dos.

### Actualizado

- `tests/test_support_orientation_v1112.py` — la tabla de valores por
  defecto por tipo es ahora la de la guía; el valor publicado del Amherst
  se muda al archivo nuevo y aquí queda la identidad que este archivo
  protege, que ninguna orientación empeore el muro.

### Banco de verificación (fuera del repositorio)

- **47**: de `TANGENT_TO_SLIP` a `PARALLEL_TO_SUPPORT`; **−0,27 %**.
- **48**: de DISCREPANCIA (+19,6 %) a error medio **1,76 %** en seis
  puntos. A48-1 cerrada con la causa reatribuida.
- **54**: de `PERPENDICULAR_TO_PILE` a `TANGENT_TO_SLIP`; se añade el
  círculo sin pilote que faltaba y nace **A54-1**.
- **85** y **86** comparan Bishop, Spencer y GLE: no se mueven.
