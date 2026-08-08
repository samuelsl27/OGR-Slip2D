# OGR Slip2D v0.1.65 — con elementos finitos, el embalse se prescribe

Cuarta fase de la deuda de v0.1.61. La más pequeña de las cuatro, y la que
menos código nuevo tiene: son unas cuarenta líneas en `ponded_water` y un
cambio de forma en el lienzo.

---

## El problema

El nivel del embalse salía **solo** de polilíneas dibujadas: nivel freático
o línea de desembalse. Con un análisis de filtración por elementos finitos
eso es la fuente equivocada. El embalse con el que se resolvió la
filtración vive en las **condiciones de contorno**, como una altura total
aplicada al borde del modelo. Hay agua embalsada allí donde esa altura
supera la cota del contorno al que se aplica.

Pedirle al usuario que además dibuje un nivel freático encima sería una
**segunda afirmación independiente del mismo hecho**, libre de contradecir
al análisis que de verdad se resolvió. Y el nivel del embalse no es un
adorno: pesa sobre el talud y empuja horizontalmente.

## Lo que hace ahora

`_fea_ponding_polyline` recorre las condiciones Dirichlet y se queda con
los nodos cuya carga supera su propia cota:

| Tipo de condición | Altura total H |
|---|---|
| `total_head` | el valor |
| `pressure_head` | `y_nodo + valor` |
| `zero_pressure` | `y_nodo` |
| Neumann y caras de rezume | ninguna: no prescriben nivel |

Los puntos `(x, H)` resultantes se ordenan e interpolan linealmente. El
nivel así obtenido se combina con las superficies dibujadas por la **misma
regla de "gana la más alta"** que esas ya seguían entre sí, de modo que un
proyecto que tenía embalse lo conserva.

Tres decisiones que conviene tener escritas:

- **La condición guarda un id de nodo**, así que hace falta la malla para
  saber dónde está. Ambas se serializan con el proyecto, así que el
  embalse sobrevive a guardar y reabrir.
- **`bc_type` se compara por su cadena**, no importando `BCType`:
  `ogr_core` no debe depender de `ogr_fem2d`, y el acoplamiento que ya
  existía —el campo de presiones del FEM— es duck-typed por lo mismo.
- **Entre dos embalses a distinta cota** —agua arriba y agua abajo de una
  presa— la interpolación traza una rampa que no es una superficie de agua
  real. Da igual: el terreno entre ambos está por encima de los dos y
  `ponded_depth_at` recorta a cero ahí.

## El lienzo, que era el fallo escondido

El dibujo del embalse recorría **las polilíneas de contorno**. Un embalse
que existe solo en las condiciones de contorno habría cargado el talud
**sin verse**, que es exactamente la forma de fallo que persigue la regla
7: el usuario cree que el análisis no tiene agua encima, y la tiene.

El muestreo se generaliza a una lista de funciones "nivel en x": una por
polilínea dibujada, más la derivada de las condiciones cuando el método es
de elementos finitos.

## Una desviación deliberada respecto a la referencia

La referencia **deshabilita la herramienta de dibujar nivel freático**
cuando el análisis es por elementos finitos, porque allí el FEA gobierna
todo lo hidráulico. Aquí **no se ha deshabilitado**, y es a propósito: en
este programa un nivel freático dibujado sigue teniendo dos efectos que el
campo del FEM no cubre —separa el peso específico saturado del seco, y
gobierna la presión intersticial de los materiales que **no** están puestos
en `FEM_SEEPAGE`, que son la mayoría en un modelo mixto—. Quitar la
herramienta eliminaría capacidades que aquí siguen significando algo.

---

## Qué se probó

Fichero nuevo `tests/test_fea_ponding_v165.py`, 15 tests.

El anclaje principal es una **identidad entre dos caminos que tienen que
coincidir**: una condición de altura total H sobre un terreno a cota y
tiene que producir exactamente la misma carga vertical y el mismo empuje
horizontal que un nivel freático dibujado a la cota H sobre ese mismo
terreno. Si discrepan, uno de los dos está mal — y el camino dibujado es el
que ya está validado (verificación #70, v0.1.61).

Para que la identidad no pueda ser "dos errores iguales", va acompañada de
su forma cerrada: `Σ W_agua = γw · profundidad · anchura total`, exacta.

Lo demás:

- Los **tres tipos Dirichlet** describen el mismo embalse: `pressure_head`
  de 5 a cota 10 carga igual que `total_head` de 15; `zero_pressure` no
  embalsa nada, porque la superficie está *en* el contorno.
- Lo que **no** debe embalsar: una carga por debajo del contorno (eso es un
  nivel freático, no un embalse), las condiciones de Neumann y las caras de
  rezume, unas condiciones que sobreviven a un cambio de método a uno que
  no es de filtración, y el caso sin malla.
- La combinación con una superficie dibujada, en los dos sentidos.
- Una carga que **varía linealmente** da una superficie inclinada, con el
  valor exacto a media distancia, y se mantiene constante fuera del tramo
  con nodos mojados.
- Y el lienzo: con embalse prescrito aparecen elementos gráficos; sin él,
  ninguno.

Suite completa en verde.

---

## Coste, y por qué la medición de v0.1.64 tampoco valía

`ponded_water_level_at` corre una vez por dovela, así que el bucle nuevo
sobre el método de agua está en la ruta caliente. Al ir a medirlo apareció
algo que obliga a corregir la lección de v0.1.64.

Allí se concluyó que el cronómetro de la suite no sirve para diferencias
por debajo del 10 %, pero que **las medidas en bucle caliente sí eran
fiables**. Sólo la mitad es cierta. `_column_weight`, que no se ha tocado
desde v0.1.63, mide ahora **40 µs donde entonces midió 32.5**: la máquina
está simplemente más lenta que aquel día. Los números absolutos **entre
sesiones tampoco son comparables**; sólo lo son los A/B tomados espalda con
espalda en el mismo proceso.

Hecho así, el cambio de esta fase da +8.7 %... con las dos corridas de
control difiriendo entre sí un 5 %, o sea que la medida no resuelve el
efecto. Por construcción el trabajo añadido es una consulta de atributo y
una pertenencia a tupla, ~0.2 µs por dovela sobre 2.5 ms por superficie:
del orden del 0.2 %. **Cuando la medición no puede distinguir el efecto del
ruido, manda el razonamiento sobre lo que se ha añadido.**

De paso apareció una ineficiencia anterior y real: la función llamaba
`boundaries_of` **una vez por tipo de contorno embalsante**, construyendo
dos listas nuevas en cada invocación sólo para recorrerlas una vez. Una
sola pasada sobre `project.boundaries` con un filtro de tipo:

| | Antes | Ahora |
|---|---:|---:|
| `ponded_water_level_at` | 0.819 µs | **0.390 µs** (2.1×) |

Medido A/B en el mismo proceso. Compensa con creces los 0.2 µs añadidos,
así que esta ruta queda más rápida que antes de la fase.

## Lo que queda

Fases 5 y 6: el reparto de dovelas en las intersecciones —la primera que
puede mover los casos de validación—, y el descenso rápido multietapa, que
sigue bloqueado hasta obtener las ecuaciones de conversión entre la
envolvente R y la Kc = 1 de su fuente original.
