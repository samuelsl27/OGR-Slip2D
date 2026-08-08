# OGR Slip2D v0.1.63 — el peso de la dovela sale de integrar su columna

Segunda fase de la deuda de v0.1.61. Un solo cambio, en un solo sitio, con
consecuencias en dos sitios distintos.

---

## Qué hacía antes

`slice_surface` clasificaba **cada dovela entera por su punto medio de
base**: un único peso específico para toda su altura, y el material de la
base para toda la columna.

```python
mat = _material_at(project, Vertex(xc, base_y_mid + 0.01))
below_water = ...   # ¿hay algún NF por encima de base_y_mid?
gamma = mat.gamma_at(below_water)
weight = gamma * h_mid * dx
```

De ahí salían dos errores independientes:

- **Multicapa**: una dovela que atravesaba tres capas pesaba como si fuera
  toda del material que hay bajo su base.
- **Húmedo/seco**: una dovela a caballo del nivel freático recibía γ o γsat
  para toda su altura, según de qué lado cayera su punto medio de base.

El segundo estaba anotado en un comentario del código como simplificación
conocida. El primero **no**: el docstring del módulo afirmaba exactamente
lo contrario —

> *"The slicer handles multi-layer materials by intersecting each slice
> with every material boundary and composing the weights accordingly."*

— y eso no estaba implementado. Un comentario que miente es peor que uno
que falta, porque el siguiente que lea el módulo no irá a comprobarlo.

## Qué hace ahora

`_column_weight(project, x, y_base, y_top, dx)` integra la columna
vertical: la corta en cada contorno de material y en cada nivel freático
que la cruce, y suma `Σ γ_banda · Δh · dx`. Cada banda resuelve su material
en su propio punto medio y su saturación contra el NF.

El paso `dx` **sigue siendo uniforme**. Repartir los límites de dovela en
las intersecciones es la fase 5, y es un cambio de otra naturaleza: éste
corrige el número dentro de una dovela dada, aquél cambia qué dovelas hay.

Tres decisiones que conviene tener escritas:

- **Solo `MATERIAL` y `WATER_TABLE` cortan.** Las piezométricas y la línea
  de desembalse no deciden el peso específico — es la primera de las tres
  diferencias documentadas entre NF y piezométrica.
- **El material de la base sigue resolviéndose una sola vez**, en
  `base_y_mid + 0.01`. La resistencia al corte y la presión intersticial
  se evalúan en la base y pertenecen al material que la base corta; eso
  era correcto y no se ha tocado.
- **Un segmento vertical no aporta corte.** Yace a lo largo de la columna
  en vez de cruzarla; contar sus extremos inventaría bandas.

### Contornos que se doblan

`_polyline_crossings_at_x` devuelve **todos** los cruces de una polilínea
con la vertical, no el primero. `interp_y_on_polyline` se para en el primero
porque una superficie de agua es unívoca en x, pero un contorno de material
puede plegarse: una lente o una cuña cruzan la misma columna dos veces, y
quedarse con el primer cruce perdería una banda.

## Compatibilidad

Con **un material y sin nivel freático** el resultado es
`γ · (y_top − y_base) · dx`, que es literalmente lo que calculaba la versión
anterior — la altura media trapezoidal
`0.5·((tl−bl)+(tr−br))` es idénticamente `y_top_mid − y_base_mid`. Los siete
casos de validación LEM son de una capa, así que **no se mueven**, y se ha
comprobado: siguen dentro del 0.7 %.

Cambian los números en dos situaciones, ambas por ser ahora correctas: un
modelo multicapa, y uno cuyo NF corta las dovelas a media altura. Un modelo
totalmente sumergido —que es como está montado el test de γsat de v0.1.60—
tampoco cambia.

---

## Lo que se encontró por el camino

**El test que no depende de ninguna γ.** El caso más útil del fichero nuevo
no es el de dos capas: es
`test_a_boundary_that_changes_nothing_changes_nothing`, que mete un contorno
de material con **el mismo material a ambos lados** y exige que el peso no
cambie **ni un bit**. Separa "el corte ocurrió" de "el corte importó". Si el
bucle de bandas contase una dos veces, o perdiera una por una tolerancia,
ahí salta — sin ninguna diferencia de γ detrás donde esconderse. Las
identidades con dos pesos específicos distintos pueden pasar por
compensación; ésta no.

**La aditividad como comprobación independiente.** Cortar la misma columna
por un sitio arbitrario y sumar las partes tiene que dar el total. Es cierto
de cualquier integral, y sigue siéndolo a través del corte de capa, así que
comprueba el bucle sin conocer ninguna geometría concreta.

**Estabilidad bajo refinamiento.** El peso total de la masa no puede
depender de en cuántas dovelas se cortó, más allá de la discretización del
terreno. Un fallo de peso por dovela aparece aquí como un total que depende
del número de dovelas; con 25 y con 100 la diferencia se queda por debajo
del 2 %.

**El caso de validación ej1 NO protege este cambio, y conviene saberlo.**
Al comprobar que no se movía, se midió también por qué: ej1 tiene tres
materiales y dos contornos de material, así que parecía el guardián ideal.
Pero **sus tres materiales tienen el mismo peso específico**, γ = 20, y uno
de los dos contornos ni siquiera abarca la abscisa del círculo crítico. El
peso total sale idéntico hasta el último bit —3325.414430 con las dos
implementaciones— y los tres factores de seguridad no se mueven ni en la
sexta cifra.

Es decir: que ej1 siga pasando **no es evidencia de nada** sobre esta
fase. Es una buena noticia (no hay regresión) y una mala (el caso de
referencia multicapa que teníamos no discrimina entre pesar bien y pesar
mal). Por eso los anclajes del fichero nuevo son identidades construidas a
propósito con γ distintos, y no un caso publicado: aquí no había ninguno
que sirviera.

**El coste estaba escondido en la validación de una caché.**
`resolve_regions()` cuesta **20.6 µs incluso cuando acierta en caché**,
porque `_regions_cache_key()` reconstruye una tupla con todos los vértices
redondeados de todos los contornos externos y de material **en cada
llamada**, solo para comprobar si la caché sigue valiendo. Son el 82 % de
los 25 µs de `material_at`.

Era invisible mientras cada llamante pedía un punto: el slicer hacía una
consulta por dovela. Al pedir una por banda, la firma se pagaba tantas
veces como bandas y el rebanado se fue a 2.72 ms por superficie, frente a
1.54 ms antes.

Dos medidas, en este orden:

1. `Project.materials_at(points)` resuelve varios puntos contra **una
   sola** consulta de regiones. Rebanado: 2.72 → 1.91 ms.
2. Con **un solo material** no se consulta la subdivisión en absoluto:
   todas las regiones resuelven a él, y el respaldo sin región también, así
   que la geometría no puede cambiar la respuesta.

El resultado depende de cuántos materiales tenga el modelo:

| Modelo | Antes | Ahora |
|---|---|---|
| Un material | 0.59 ms | **0.51 ms** (−14 %) |
| Multicapa (ej1) | 1.54 ms | 1.91 ms (+24 %) |

Un modelo de una capa sale **más rápido que antes**, porque el atajo se
salta una consulta de regiones que la versión anterior sí hacía. El +24 %
del multicapa es el coste real de la integración —dos barridos
punto-en-polígono por columna en vez de uno— y es el precio de pesar bien.

La ineficiencia de `_regions_cache_key` es anterior a esta fase y sigue
ahí para los llamantes de un solo punto. No se ha tocado: la firma es la
red que protege de que alguien mueva un vértice sin notificar, y
sustituirla por un contador de generación reintroduciría exactamente ese
fallo.

---

## Qué se probó

Fichero nuevo `tests/test_slice_column_v163.py`, 15 tests, todos con
anclaje analítico:

- **Una capa**: `γ·h·dx` exacto, y el corte que no cambia nada.
- **Dos capas**: suma ponderada por espesor exacta; columna entera dentro
  de una capa; aditividad del corte.
- **Nivel freático**: media columna sumergida da `γsat·h/2 + γ·h/2`
  exacto; totalmente sumergida sigue dando γsat en toda la altura; un NF por
  debajo no moja; una piezométrica no satura.
- **Composición**: dos capas cortadas por un NF entre medias, cuatro bandas.
- **Contornos plegados**: los dos cruces de una V, con sus dos y exactas por
  interpolación lineal; y el segmento vertical que no aporta corte.
- **Extremo a extremo**: una capa superior más ligera baja el peso total; el
  total es estable al refinar; y con un material la dovela sigue cumpliendo
  `W = γ·h·dx`, que es el guardián de los casos de validación.

Suite completa en verde. Casos de validación LEM, γsat de v0.1.60 y
verificación #70 del agua embalsada, todos intactos.

## Lo que queda

Fases 3 a 6: soportes en los siete métodos, embalse derivado de las
condiciones de contorno de altura total, reparto de dovelas en las
intersecciones, y el descenso rápido multietapa.
