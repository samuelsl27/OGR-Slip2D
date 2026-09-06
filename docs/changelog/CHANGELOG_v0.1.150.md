# OGR Slip2D v0.1.150

**El encargo de D65 traía una hipótesis —la pareja de divisiones que genera
el círculo publicado del 14 no sobrevive al 50 % retenido— y la
instrumentación la refutó en la primera medida: esa pareja se genera y gana
en las diez iteraciones. Lo que pasaba es que Auto Refine no refinaba: la
retención se quedaba con los dos extremos del talud, el casco contiguo de
eso es el talud entero, y las diez iteraciones generaban los mismos 450
círculos diez veces.** Cuatro lecturas del texto documentado corregidas,
cada una con su medida; el 14 pasa de 1,437293 a **1,405952** (publicado
1,409; el círculo publicado da 1,408452 con el mismo método) y los otros
tres Auto Refine del banco quedan a +0,16 %, −0,12 % y +0,09 % de lo
publicado donde estaban a +0,45 %, +1,74 % y +1,25 %.

---

## Lo que había

Problema 14 (Arai y Tagyo 1985, ej. 1), Auto Refine circular 10-10-10 al
50 %. La búsqueda devolvía **1,437293** (Bishop); el círculo publicado
resuelve a **1,408452** con el mismo método, y entre los dos el factor baja
de forma continua (a t = 0,95 del camino, 1,406914). Un mínimo con un
descenso continuo al lado no es un mínimo local (P014-BUS2, D65).

Instrumentado `AutoRefineSearch._run` sobre el `construir_modelo.py` del 14
(qué pares se generan, qué divisiones se retienen, qué polilínea queda):

| Iteración | Puntos medios (x) | Retenidas | Mejor |
|---|---|---|---|
| 0 | 3,6 · 10,8 · 17,7 · 24,0 · 30,0 · 36,0 · 42,0 · 48,3 · 55,2 · 62,4 | {0,1,2,8,9} | 1,437293 |
| 1–9 | 3,6 · 10,7 · 17,7 · 24,1 · 30,0 · 36,0 · 41,9 · 48,3 · 55,3 · 62,4 | {0,1,2,8,9} | 1,437916 |

La pareja (2, 8) —puntos medios (17,71 · 16,00) y (55,19 · 35,00), la más
cercana a los afloramientos publicados (17,81 · 56,99)— es la del mejor
círculo de **todas** las iteraciones. Nadie la descartaba. Lo que no se
movía eran los puntos medios: las cinco divisiones de menor media eran los
dos llanos de los extremos, y `_run` formaba la polilínea nueva como el
casco desde la primera retenida hasta la última (`search.py`, retención
de v0.1.17), que con {0,1,2,8,9} es todo el talud. 4 050 de las 4 500
evaluaciones eran repeticiones. El 16 hacía exactamente lo mismo; el 17 se
congelaba desde la iteración 2; el 15 estrechaba, y hacia una franja de 8 m
donde el mejor **subía** de 0,4219 a 1,5299 (el 0,42 sobrevivía porque la
población conserva todo). *Number of Iterations* = 10 no cambiaba nada en
dos de cuatro modelos: regla 7.

## Lo que apareció de paso (regla 6: se dice antes de tocarlo)

Tres diferencias más entre lo documentado y lo implementado, todas
medibles en la primera iteración del 14:

- **El punto medio de una división estaba en el aire.** Se tomaba el punto
  medio de la cuerda entre los extremos de la división; en la división que
  cruza el pie (18 · 15) eso da (17,71 · 16,00), un metro por encima del
  suelo. El punto a mitad de longitud **sobre** la polilínea cae en
  (18,01 · 15,01), el pie.
- **El barrido angular era fijo.** θ relativo a la cuerda en [92°, 178°]
  fuese cual fuese la pendiente de la cuerda, y después se rechazaban los
  círculos con el centro por debajo de los puntos. Para la pareja ganadora
  del 14 (cuerda a 27°) morían siempre los tres ángulos más empinados:
  siete útiles con paso 9,6° donde el barrido documentado —de la
  pendiente de la cuerda a la vertical en el punto alto— pone los diez a
  6,3°. Esto es exactamente el «4 500 generadas, 3 300 analizadas» de
  D07c. El máximo documentado (tangente vertical en el punto alto, θ =
  90° − |pendiente de la cuerda|) es **la misma condición** que el «centro
  por encima de los dos puntos» que ya se imponía a posteriori: el centro
  queda a la altura del punto alto. No es que el centro quede encima de
  él, como escribí primero en un test y me corrigió el propio test.
- **La media por división es una medida de centralidad, no de mínimo.**
  Con las dos correcciones anteriores y la retención en trozos (las
  divisiones retenidas, sin casco), la iteración 1 del 14 daba 1,407564
  pero la refinación **derivaba hacia los llanos lejanos** (x = 0,9 y
  65,1) hasta que desde la iteración 3 no salía ni un círculo válido. La
  causa se ve en un campo sintético cuadrático `1 + ((x_izq − X1)/s)² +
  ((x_der − X2)/s)²` con el mínimo en los dos extremos del talud: la media
  de una división promedia su distancia a **todas** las demás, así que es
  más baja en las divisiones centrales (18,7 en x = 28 frente a 23,2 en
  x = 3, donde está el mínimo), y seis iteraciones no refinaban nada
  (1,50 en 1, 3 y 6 iteraciones). En el 14 se suma otra cosa: los
  círculos pequeños sobre el llano no deslizan («zero driving moment»),
  se excluyen de la media, y los llanos quedan con medias de círculos
  profundos solamente. Con ninguna atribución de la media (a los dos
  extremos del par; a todas las divisiones que el círculo cubre) se
  retiene la zona del mínimo.

Medida de la primera iteración sola (450 círculos) con las tres familias:

| Familia | Válidos | Mejor | Retenidas |
|---|---|---|---|
| Como estaba (cuerda, barrido fijo) | 267 | 1,437293 | {0,1,2,8,9} |
| Barrido documentado, punto medio de cuerda | 379 | 1,434707 | {0,1,2,8,9} |
| Barrido documentado, punto medio sobre polilínea | 375 | **1,407564** | {0,1,2,8,9} |

Y una anomalía que no es de esta versión pero se decide aquí porque el
banco lo dejó apuntado «al pasar por P-D65»: en `GridSearch._run` el
rechazo por foco se **salta** mientras el comentario de al lado defiende
que la población es (nx+1)(ny+1)(rinc+1) «whatever the geometry does».
D33 ya decidió que un foco salta y no cuenta, en todas las búsquedas; lo
que estaba mal era el comentario, y es lo que cambia: la población es ésa
menos los rechazos por foco. Ningún número se mueve.

## Qué cambia

Todo en `ogr_slip2d/search.py::AutoRefineSearch`; la variante no circular
hereda las cuatro cosas por la costura `_evaluate_trial`.

1. **Puntos medios sobre el talud.** Cada división es un tramo de la
   polilínea por longitud de arco y su punto medio es el punto a mitad de
   ese arco (`_point_along`), no la media de sus extremos. Sólo se mueven
   las divisiones que cruzan un vértice.
2. **Barrido documentado.** El semiángulo central θ (ángulo tangente-
   cuerda, Euclides III.32) se barre en (ε, 90° − |pendiente| − ε) en
   pasos iguales, r = cuerda / (2 sen θ), centro del lado superior
   (`_circle_through_two_points_half_angle`). ε = 1° es elección de esta
   implementación y está dicho así en el código; el texto sólo dice «small
   offset». Una cuerda vertical (dos puntos medios en un muro) no tiene
   rango y se salta, contada en `attempts`. `_circle_through_two_points_
   tangent` se conserva (lo usa un test de v0.1.17). `surfaces_generated`
   sigue siendo C(d,2)·c·z: 4 500 en el 14, y ahora las 4 500 se analizan.
3. **Retención sin casco.** Las divisiones retenidas **son** la zona de
   búsqueda siguiente, agrupadas en tramos contiguos; la iteración
   siguiente reparte `divisions` divisiones entre los tramos en proporción
   a su longitud (resto mayor, mínimo una por tramo: `_allocate_
   divisions`), y los sub-tramos conservan los vértices del terreno. Las
   parejas se generan entre todas las divisiones, también entre tramos, así
   que los círculos profundos pie → coronación siguen existiendo. Una
   iteración sin ningún círculo válido no reordena nada (no hay con qué) y
   deja la zona como estaba.
4. **Retención por el mínimo de cada división**, no por su media. Es la
   única de las cuatro que se aparta de la palabra del texto, y se aparta
   porque la palabra no puede hacer lo que el mismo texto dice que hace el
   método («narrow the search to the part of the slope that produces the
   lowest safety factors»). Está dicho en el docstring y en el comentario
   de `_run`, con la medida.

Con las cuatro, en el 14 (10-10-10, 50 %, 30 dovelas, Bishop):

| Iteración | Puntos medios (x) | Mejor |
|---|---|---|
| 0 | 3,6 · 10,8 · 18,0 · 24,0 · 30,0 · 36,0 · 42,0 · 48,0 · 55,2 · 62,4 | 1,4076 |
| 1 | 1,8 · 5,4 · 9,0 · 12,6 · 16,2 · 19,5 · 53,4 · 57,0 · 60,6 · 64,2 | 1,4198 |
| 2 | 11,7 · 13,5 · 15,3 · 17,1 · 52,5 · 54,3 · 56,1 · 57,9 · 59,7 · 61,5 | 1,4129 |
| 3 | 16,7 · 17,6 · 53,8 … 60,1 | 1,4096 |
| 5 | 17,7 · 17,9 · 55,3 … 56,9 | 1,4067 |
| 9 | 18,0 · 55,9 · 56,0 | **1,4060** |

Los puntos medios convergen al pie (18,0) y a 8 m detrás del borde de la
coronación (56,0). El publicado aflora en 17,81 y 56,99; la construcción
exacta de la referencia no se puede reconstruir desde el manual (el
afloramiento 56,993 es punto medio exacto de una división de 3,603 m,
pero eso lo dan las dos lecturas de la retención y el otro afloramiento no
lo da ninguna), y esta versión no pretende reproducirla.

## Qué se probó

`tests/test_auto_refine_refinement_v1150.py`, 17 tests en cinco clases:

- **Campo sintético** (criterio 2 de D65): el método es un objeto con
  `METHOD_ID` y `compute_fos` que devuelve el campo cuadrático sobre los
  afloramientos, con X1 y X2 entre dos puntos medios consecutivos de la
  iteración 1 y en los dos extremos del talud. Iteración 1: 1,5 por
  construcción; seis iteraciones: < 1,02 y afloramientos a menos de un
  décimo del paso (medido 1,0005, a 0,1 m); tres iteraciones mejoran a
  una estrictamente. Con el código de 0.1.149 el resultado era 1,5 en las
  tres cuentas.
- **Puntos medios sobre el suelo**: `envelope_y_at(x) == y` a tolerancia
  relativa para los diez de la iteración 1, con divisiones que cruzan el
  pie y la coronación; y el ayudante en el propio vértice.
- **Barrido**: centro por encima de los dos puntos en todo (0°, 63°) de una
  cuerda a 27°, tangente vertical en el punto alto en θ_max; en una corrida
  real, cada par barre exactamente los `c` valores documentados y ninguna
  construcción falla; generadas == analizadas sin focos ni muros; el
  reparto de divisiones entre tramos ([21,6; 14,4] → [6, 4], suma exacta,
  mínimo uno).
- **Problema de referencia** (criterio 1): el modelo de
  `validacion/casos/004-arai-tagyo-1985-ej1`, Bishop por `build_method`
  (a pelo, `BishopSimplified()` da 1,408853 en el mismo círculo: 0,03 %
  que la tolerancia de convergencia explica y que el test dice); el
  círculo publicado no se mueve de 1,408452; Auto Refine 10-10-3 queda
  ≤ 1,408452 × 1,005 y > 1,39. Tres iteraciones y no diez para que cueste
  ~15 s: la primera ya cumple, y la refinación se prueba en el campo
  sintético.
- **Escenarios que el banco no cubre** (los cuatro Auto Refine del banco
  miran a la derecha, sin muro ni límites): talud espejo (mismo factor a
  0,2 % y centro reflejado); el campo sintético en el espejo; mínimo en
  **medio** del talud (c' = 0,5, φ' = 35°: círculo de cara, donde el casco
  viejo funcionaba por casualidad y la regla nueva no puede perderlo);
  Slope Limits (20, 55) que confinan todos los puntos medios de todas las
  iteraciones; un muro de 6 m con puntos medios sobre él (intentos
  contados, ninguna construcción falla, mecanismo devuelto); y objetivo
  **ky** (la retención ordena por `score`, y el crítico es el mínimo de la
  población en ese objetivo).

Tests existentes que se movieron, y por qué:

- `test_auto_refine_noncircular_v1128::test_a_complete_equilibrium_method_
  reproduces_the_arc`: el círculo crítico del talud de ese test es otro
  (la búsqueda cambió) y la secuencia polilínea/arco con Spencer es ahora
  +0,387 %, +0,059 %, +0,0098 %, +0,025 %: el último paso **sube** 1,5e-4,
  un orden de magnitud por debajo de la tolerancia del solver. La
  monotonía estricta se relaja con un suelo de 2,5e-4; la convergencia
  (errores[0] > 4·errores[−1], errores[−1] < 5e-4) no se toca.
- `test_search_effort_v1103::test_doubling_the_iterations_doubles_the_
  surfaces` falló con la retención por media (28 válidas en 2 iteraciones,
  32 en 4: las últimas no producían nada) y pasa con la retención por
  mínimo sin tocarlo.

Suite completa: **3 167 de 3 167** (2026-09-06, en paralelo con la corrida
del banco, así que el reloj no vale como medida). La suite corrió con el
acumulador de medias todavía en el código; después se quitó por no leerlo
nadie y se repitieron los 35 tests de los tres archivos de Auto Refine.

## Banco

Los cuatro Auto Refine del banco (14–17; 18–20 son Path, Path y Grid),
reejecutados con `_tools/correr_todo.py 14 15 16 17 --forzar`:

| Problema · método | Publicado | Antes | 0.1.150 | Δ nuevo |
|---|---|---|---|---|
| 14 · Bishop | 1,409 (círculo publicado: 1,408452) | 1,437293 (+2,01 %) | **1,405952** | −0,22 % (−0,18 % frente a su círculo) |
| 14 · Spencer | 1,319 | 1,434268 (+8,74 %) | 1,403273 | +6,39 % (la referencia separada de sí misma; sin círculo publicado) |
| 14 · GLE | 1,414 | 1,434023 (+1,42 %) | 1,402547 | −0,81 % |
| 14 · Janbu corregido | 1,407 | 1,449483 (+3,02 %) | 1,412638 | +0,40 % |
| 15 · Bishop | 0,420 (círculo publicado: 0,420290) | 0,4219 (+0,45 %) | **0,420665** | +0,16 % |
| 16 · Bishop | 1,118 | 1,1374 (+1,74 %) | **1,116679** | −0,12 % |
| 16 · Spencer | 1,118 | 1,1236 (+0,50 %) | 1,117170 | −0,07 % |
| 17 · Bishop | 1,344 (círculo publicado: 1,344699) | 1,3608 (+1,25 %) | **1,345178** | +0,09 % |
| 17 · Fellenius | 1,278 | 1,2836 (+0,44 %) | 1,279860 | +0,15 % |

Con la tabla regenerada (`generar_comparativa.py`), las tres filas
circulares del 14 que estaban en REVISAR pasan a OK; Spencer sigue en
DISCREPANCIA por la referencia. El reparto de D37 regenerado
(`clasificar_d37.py`, que sólo mide) pasa de 63 filas a 51: las del 14, el
15 y el 17 con círculo publicado dejan de contar porque la búsqueda ya no
queda por encima de él, y el resto es lo que se ha cerrado desde 0.1.129,
cuando se generó por última vez.

El 14 queda **por debajo** del círculo publicado: el campo de OGR tiene su
mínimo cerca de (25,54 · 46,73) R 32,61 y no en el círculo de la
referencia, lo que el propio P014-BUS2 ya anticipaba (t = 0,95 daba
1,406914). Los cuatro criterios de cierre de D65 se cumplen; la fila
circular del 14 sale de D37 (era la única de la causa C5 con evidencia
limpia de búsqueda).

## Qué falta

- La retención por mínimo se aparta de la palabra «average» del texto. Es
  una decisión medida, no una lectura: si alguna vez aparece una
  descripción más precisa de cómo promedia la referencia, hay que volver a
  medir, no a discutir.
- La construcción exacta de la referencia no se reproduce: sus
  afloramientos publicados (17,81 · 56,99) no son puntos medios de ninguna
  iteración bajo ninguna lectura que se haya probado. El 14 cierra por
  criterio, no por coincidencia.
- El «small offset» del barrido es 1° por elección propia.
- Las variables aleatorias de soporte y *Ungroup Pattern* (D66) siguen
  reportadas y sin tocar.
