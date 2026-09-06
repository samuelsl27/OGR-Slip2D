# La regla de radios con dos ventanas, despejada por medición

**Estado: resuelto en v0.1.148.** Continúa `grid_radius_rule_v188.md`, que
midió la regla con UN juego de límites y dejó escrito que faltaba una
geometría con caras verticales. Aquí está esa geometría, y lo que salió de
ella no era lo que se buscaba.

---

## 1 · De dónde viene

Defecto D77 del banco de verificación: en los ocho muros de bancadas (87–94),
que declaran una ventana de salida en la bancada inferior y otra de entrada
en la coronación, ningún centro a la izquierda del pie podía generar un
círculo de pie, porque la regla de v0.1.88 tapa en el primer límite
alcanzado y ése era la esquina (0 · 6) del modelo. El encargo proponía
sustituirla por «el mayor radio cuyo círculo todavía aflora».

## 2 · Lo que la calibración de v0.1.88 ya decía, y no se había leído

| lectura | centro que la refuta | error |
|---|---|---|
| límite lejano | Ej_1 (40 · 120): la referencia tapa en (0 · 50), 80,62 m | 40 m |
| límite del lado de la salida | el mismo | 40 m |
| último radio con dos cortes (círculo por el pie) | Ej_2 (−29,52 · 135): la referencia para en el punto límite con masas válidas más allá; 26 centros de Ej_1, 16 de Ej_2, 8 con límites movidos | 6,7 m |

La regla de v0.1.88 reproduce los 949 + 34 centros a 7e-13 y es la única de
las cuatro que lo hace.

## 3 · El experimento

`referencias/Ejemplos/00_2026_09_06_Test_Muro_D77/`: el muro del 87 del
banco (`_tools/muro_bancadas.py`), cinco modelos corridos en la referencia
el 2026-09-06, `.ogr` gemelos, lector `_tools/leer_slim_d77.py`.

| modelo | búsqueda | qué mide |
|---|---|---|
| A | rejilla 21 × 19 desde (−5,713 · 20,432), rinc 1, dos juegos | la horquilla desnuda |
| B | ídem, rinc 10 | que los extremos no dependen de rinc |
| C | rejilla del banco 18 × 17, rinc 60, dos juegos | la regla en 342 centros distintos |
| D | Auto Refine 10/10/10/50 % | el mínimo de la referencia con otra búsqueda |
| E | como A con un solo juego (0 · 6)–(24 · 15) | si el problema es el juego o el muro |

## 4 · Un juego: nada que cambiar

E contra `_radius_bracket` de v0.1.88: **440 centros, peor error 9,4e-14**,
con `d_min` a (8,4 · 15) y `d_max` a (0 · 6). Las caras verticales no
cambian la regla. Y con un juego la referencia tampoco genera el círculo
publicado: desde (−5,713 · 20,432) emite [15,142, 15,502].

## 5 · Dos juegos: la regla

Superficie de cada ventana: los segmentos del perfil que solapan su intervalo
abierto de x (un límite en mitad de un segmento lo incluye entero) más las
caras verticales estrictamente interiores. En el muro: salida = suelo
(0 · 6)–(6 · 6), cara (6 · 6)–(6 · 9), banqueta (6 · 9)–(7,2 · 9); entrada =
coronación (8,4 · 15)–(24 · 15). Ni la cara x = 7,2, ni la banqueta y = 12,
ni la cara x = 8,4.

Un radio es válido si el círculo corta esas superficies en dos puntos
consecutivos, entrando en el suelo por la ventana 1 y saliendo por la 2.
`[R_lo, R_hi]` es el rango válido, leído de las distancias a vértices, puntos
límite y pies de perpendicular (la validez sólo cambia ahí). Margen del
**0,1 % relativo** en un extremo fijado por esquina del perfil, ninguno en
uno fijado por punto límite. Si se cruzan, se repite `r_min`. Sin rango, un
radio degenerado que no resuelve.

| comprobación | resultado |
|---|---|
| A, 440 centros | 440, peor 8,9e-14 |
| B, 440 centros, rinc 10 | mismos extremos que A; espaciado uniforme 9,2e-14 |
| C, 342 centros | 301 (peor 5,0e-10); los 41 restantes no tienen ningún círculo válido en la referencia (0 de 2 501) |
| E, 440 centros, un juego | 440, 9,4e-14 (camino de v0.1.88) |

### Las lecturas que se cayeron, con el centro que las tumbó

| lectura | centro | qué pasó |
|---|---|---|
| inset del 5 % sobre el rango válido | A, todos | los extremos son `R_lo · 1,001` y `R_hi · 0,999` exactos |
| «último radio con dos cortes» sobre el perfil entero | C (−24 · 22,29) | la referencia arranca en |C − (7,2 · 9)| aunque el arco cruce la banqueta y = 12; el hueco no cuenta |
| segmento que toca la ventana por un extremo | C, 16 centros | mete la banqueta y = 12 en la ventana de entrada |
| cara x = 8,4 dentro de la ventana de entrada | C (−8,889 · 15) | colapsa la horquilla donde la referencia emite 61 radios distintos |
| margen también en los puntos límite | C (0,556 · 40,53), (−8,889 · 15) | `r_max` es |C − (24 · 15)| exacto y `r_min` es |C − (8,4 · 15)| exacto |

## 6 · Los ocho círculos publicados, en su centro, con la regla

| # | centro | R publicado | la referencia emitiría | |
|---|---|---|---|---|
| 87 | (−5,713 · 20,432) | 18,547 | [17,264, 18,568] | dentro |
| 88 | (−11,368 · 42,221) | 40,023 | [38,096, 40,130] | dentro |
| 89 | (−17,531 · 39,139) | 40,572 | [39,026, 40,603] | dentro |
| 90 | (−9,069 · 23,079) | 22,754 | [21,537, 22,754] | es el último |
| 91 | (4,658 · 15,000) | 10,934 | [6,523, 11,184] | dentro |
| 92 | (−4,903 · 20,532) | 18,112 | [16,734, 18,149] | dentro |
| 93 | (−8,825 · 23,102) | 22,603 | [21,368, 22,611] | dentro |
| 94 | (−5,537 · 20,452) | 18,450 | [17,550, 18,474] | dentro |

## 7 · Lo que salió además y no es de aquí

Sobre el modelo del banco, la referencia da Bishop 1,078 (C y D) y 1,102
sobre el círculo publicado; el manual, 1,040: el modelo reconstruido no es el
del manual. Y este motor evalúa un 5–7 % por debajo de la referencia sobre el
mismo círculo del mismo modelo (1,029 frente a 1,102; 1,026 frente a 1,078).
Registrado en `_auditoria/D77_LECTURA_FASE_B.md` del banco, para D38 / D44 /
D37.

## 8 · Lo que NO está medido

- Un límite exterior en mitad de un segmento con dos juegos (los del muro caen
  en vértices). Se toma el perfil recortado tal cual.
- Más de un intervalo válido por centro (ninguno en los 782 medidos). Se
  toman el menor y el mayor radio válidos.
- El valor del radio de relleno en los centros sin rango válido: el de la
  referencia no reproduce nada (0 válidos), y aquí se emite el radio
  tangente a la envolvente, que tampoco.
