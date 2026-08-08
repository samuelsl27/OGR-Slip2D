# OGR Slip2D v0.1.66 — donde la superficie cambia de capa, hay corte

Quinta fase de la deuda de v0.1.61, y la que más miedo daba: es la primera
que puede mover los casos de validación.

---

## Qué hacía antes

Los límites de dovela eran una división uniforme del ancho de rotura y nada
más:

```python
dx = (x_r - x_l) / num_slices
```

Sin puntos de corte obligatorios. Una dovela cuya base cruzaba un contorno
de material tenía que elegir **un** material para toda su base —el de su
punto medio—, así que a parte de esa base se le asignaba una cohesión y un
ángulo de rozamiento pertenecientes a la otra capa.

v0.1.63 arregló el **peso** de esa dovela integrando su columna. Esto
arregla su **base**, que es donde se evalúan la resistencia al corte y la
presión intersticial.

## Qué hace ahora

`_slice_boundaries` construye la lista de límites como `{x_izq, x_der}` ∪
las abscisas donde la superficie de rotura cruza un contorno de material o
un nivel freático, y reparte las `num_slices` pedidas entre los tramos
resultantes en proporción a su anchura, con al menos una por tramo y
reparto por resto mayor, de modo que el número de dovelas pedido se entrega
exacto.

### Encontrar el cruce sin pagarlo caro

Tanto la superficie de rotura como un segmento de contorno son unívocos en
x, así que el cruce es un cambio de signo de `g(x) = base_y(x) − línea(x)`.
Se recorre **segmento a segmento** con ocho subintervalos y bisección, no
la superficie entera con muchas muestras: un arco puede cortar un mismo
segmento recto dos veces, y los subintervalos separan las dos raíces,
mientras que un contorno tiene pocos segmentos.

Aun así el primer intento costó **+20.3 %** en el rebanado, porque esa
búsqueda corría íntegra para cada superficie de prueba de una búsqueda en
rejilla. La solución fue **rechazar por caja envolvente**: se calcula el
rango de y que abarca la superficie —para un círculo la rama inferior es
convexa, así que sus extremos son el punto más bajo y los dos extremos,
exacto en tres evaluaciones— y se descarta entero cualquier contorno cuya
caja no lo solape. Una capa que corre muy por debajo de la masa deslizante
no puede cortarla, y comprobarlo cuesta dos comparaciones en vez de ocho
evaluaciones por segmento.

| | Rebanado |
|---|---:|
| Uniforme (antes) | 1.916 ms |
| v0.1.66 sin caja envolvente | 2.858 ms (+49 %) |
| **v0.1.66 con caja envolvente** | **1.985 ms (+3.6 %)** |

Medido A/B en el mismo proceso, con los dos controles difiriendo un 3.7 %
entre sí: es decir, **el residuo ya no se distingue del ruido**.

### Los dos rechazos explícitos

- **Más cortes obligatorios que dovelas**: se devuelve `None` en vez de
  descartar cruces en silencio. Es un error de modelo real y la respuesta
  es pedir más dovelas, que es lo que hace la referencia con su código
  −116.
- **Dovela media más estrecha que una diezmilésima del modelo**: peligro
  numérico, no una respuesta más fina (el −106 de la referencia). La
  tolerancia va **relativa** al ancho de rotura, como manda la convención
  del proyecto, para que se comporte igual en milímetros y en metros.
- Dos cortes separados por menos de una milésima del ancho se **funden**:
  dos capas que se acuñan casi en el mismo punto son un corte. También
  relativa.

---

## Lo que se encontró: los casos de validación no protegen esto

Se comprobó, como manda el plan, si los siete casos LEM se movían. **No se
mueven** — y la razón es la que importa.

ej1 tiene tres materiales y dos contornos de material, y **su círculo
crítico no cruza ninguno**. Medido: las anchuras de dovela salen idénticas
a las uniformes, 1.1464 m las veinticinco, y los tres factores de seguridad
no cambian ni en la sexta cifra.

| | dovelas | anchura | Bishop | Janbu | Ordinary |
|---|---:|---:|---:|---:|---:|
| v0.1.66 | 25 | 1.1464 | 0.888420 | 0.843634 | 0.850054 |
| Uniforme | 25 | 1.1464 | 0.888420 | 0.843634 | 0.850054 |
| Cambio | — | — | +0.0000 % | +0.0000 % | +0.0000 % |

Es la **segunda vez** que pasa. En v0.1.63 ej1 tampoco protegía la
integración de la columna, allí porque sus tres materiales comparten
γ = 20. Aquí es por geometría: el arco crítico corre por encima de un
contorno y fuera del rango del otro.

Que un caso de referencia pase **no es evidencia** cuando no ejercita el
camino que se ha tocado. Es la conclusión práctica de las tres últimas
fases, y merece quedar escrita: **antes de apoyarse en un caso de
validación, hay que comprobar que el cambio le llega**.

Por eso el fichero de tests nuevo construye un modelo que cruza a
propósito, y lleva un test cuyo único trabajo es **vigilar al vigilante**:
comprobar que el arco de la fixture sigue teniendo dovelas a ambos lados
del contorno. Sin él, un retoque de la geometría dejaría toda la clase
pasando sin medir nada, que es exactamente lo que le ha ocurrido a ej1 dos
veces.

### El único test que sí se movió, y por qué se ha cambiado

`test_checks_v132::test_flags_the_degenerate_surface` falló. La superficie
degenerada de ese fichero —una cuña profunda que baja hasta 17 m bajo el
pie— **cruza los contornos de material de ej1 tres veces**, así que es el
caso del repositorio al que este cambio más le afecta.

| | FS | dovelas con m_α < 0.2 |
|---|---:|---|
| Uniforme | 0.6826 | 8 — `[7,8,9,10,11,12,13,14]` |
| v0.1.66 | 0.7967 | 2 — `[12,13]` |

Antes de tocar el test se comprobó si esto era la corrección o un artefacto
nuevo. La **secuencia de materiales de base es idéntica** en ambos casos y
las anchuras siguen sanas (2.64 a 2.93 m, ninguna astilla): lo que cambia
es que las dovelas de transición ya no aplican el ángulo de rozamiento de
una capa a una base que está medio en la otra. Es la corrección.

La aserción que falló era `len(bad) >= 5`, un **número capturado del
rebanado del día**, no un invariante. Lo que el test protege de verdad
—que la superficie degenerada se marca y la sana no— sigue cumpliéndose:
`ok` es False, `bad` no está vacío y el m_α mínimo es 0.155 < 0.2. La
aserción pasa a ser `bad` no vacío, con el porqué escrito en el propio
test.

### Y un fixture que mentía

La primera versión de esa fixture pinchaba los materiales en `x = 30`, que
es el **pie del talud**: altura cero, punto fuera del modelo.
`assign_material_at` devolvía `False`, las dos regiones se quedaban con el
material por defecto, y el modelo tenía **una** capa mientras aparentaba
tener dos. Los tests de solapamiento pasaban por vacío y el factor de
seguridad salía 4.31.

Con los puntos dentro del modelo aparece el caso real: FS = 1.93, y el
corte lo mueve un **0.63 %**. La fixture ahora comprueba con `assert` que
la asignación surtió efecto, en vez de confiar en ello.

---

## Qué se probó

Fichero nuevo `tests/test_slice_cuts_v166.py`, 11 tests:

- **Identidad geométrica**, el ancla principal: ninguna dovela puede tener
  una base que empiece en una capa y acabe en otra. Se comprueba
  directamente, sin conocer ningún factor de seguridad. Y su pareja: con el
  reparto uniforme **sí** hay dovelas a caballo, así que el test anterior
  mide algo en vez de pasar por suerte.
- **El corte es una raíz**: la abscisa hallada cumple
  `base_y(x) = contorno_y(x)` con error < 1e-9, y aparece como límite de
  dovela con error < 1e-6.
- **Conservación**: se entregan exactamente las dovelas pedidas (10, 25 y
  40), son contiguas y cubren el ancho exacto.
- **Sin cruce, división uniforme bit a bit**, que es lo que mantiene
  inalterado cualquier modelo que no corte una capa.
- **Regla 7 para el propio cambio**: con cruce, el FS difiere del uniforme.
- **Los dos rechazos**: diez capas finas con cuatro dovelas se rechaza y
  con cuarenta funciona; y dos contornos separados 1e-4 se funden en un
  corte.

Suite completa en verde. Los siete casos de validación LEM, intactos —
aunque, como queda dicho, eso aquí no demuestra gran cosa.

## Lo que queda

Sólo la fase 6: el descenso rápido multietapa —Lowe-Karafiath,
Duncan-Wright-Wong y Corps 2 etapas—, **bloqueada** hasta obtener las
ecuaciones de conversión entre la envolvente R y la Kc = 1 de su fuente
original. No se van a inventar.
