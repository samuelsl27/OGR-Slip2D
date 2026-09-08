# OGR Slip2D v0.1.153

**El encargo de P-D38 empezaba mandando bajar el fondo del contorno del problema
45, y la figura que el propio manual publica dice que el fondo estaba bien.** Lo
que faltaba era una opción apagada. Esta versión **no toca motor**: cero líneas
de producción. Trae el ancla que el test de σ′max no tenía, y la medida que
descarta la sexta causa de D38.

El **+8,5 % del 44 y el +11,5/12,5 % del 61 siguen sin causa nombrada.** Lo que
ha cambiado es cuánto se sabe de ellos, y que ya no queda la salida fácil.

---

## 1. La premisa del paso 0 era falsa, y la refutó la figura 45.1

D38c decía que a los modelos del problema 45 les faltaba fondo: sus dos círculos
publicados bajan a y = −0,452 y −0,778, el contorno acaba en y = 0 y la guarda de
`slicer.py:1640` los rechazaba enteros. El encargo pedía bajar el fondo «por
ejemplo a y = −5».

La **Figura 45.1** publica el contorno con los cuatro vértices rotulados —
`(0,0) — (48,12) — (100,12) — (100,0)` — o sea que **el suelo del modelo está en
y = 0 y es exactamente el que el banco construye**. Bajarlo habría separado el
modelo de la geometría publicada para hacer entrar una superficie.

Lo que el manual publica es un círculo **recortado contra el contorno**. Medido
sobre su propio dibujo a 900 dpi (1 px = 0,021–0,023 m), calibrando en el dibujo
con la línea de suelo y la coronación:

| fig | x [m] | y **dibujado** | y del **círculo** |
|---|---|---|---|
| 45.2 | 10,0 → 21,9 | **0,000** en todo el tramo | −0,205 … −0,452 … −0,007 |
| 45.3 | 13,0 → 25,0 | **0,148** constante | −0,390 … −0,778 … −0,349 |

El tramo plano empieza y acaba **justo donde el círculo cruza y = 0**, calculado
por separado desde el centro y el radio del panel. Una bajada de 0,45–0,78 m
serían 19–37 px y no están.

Eso es *Composite Surfaces*, cuya regla cita literalmente el docstring de
`CompositeSurface` en [surface.py:590](../../ogr_slip2d/surface.py). La opción
existe en OGR desde hace tiempo y está bien; lo que pasaba es que
`construir_modelo.py` del 45 no la encendía y se quedaba en el `False` por
defecto.

**Con la opción puesta y el contorno intacto**, las tres superficies publicadas
evalúan:

| figura | FoS | pub | Δ | σ′max | pub | Δ |
|---|---|---|---|---|---|---|
| 45.2 | 2,559645 | 2,559 | +0,025 % | 99,5025 | 99,50 | **+0,003 %** |
| 45.3 | 2,661652 | 2,662 | −0,013 % | 118,6246 | 118,63 | **−0,005 %** |
| 45.4 | 2,695564 | 2,696 | −0,016 % | 82,2604 | 82,25 | +0,013 % |

**45.4 no mueve un dígito** con la opción encendida o apagada — su arco no baja
del contorno, no hay nada que recortar — que era el invariante que el encargo
puso como condición de parada. El mínimo de la búsqueda también se acerca sin
tocar la rejilla: Janbu de +0,59 % a +0,04 %, de +1,35 % a +0,04 % y de +0,06 %
a −0,00 %. Las seis filas del 45 quedan `OK`.

**D38c cierra**, con la premisa refutada. Trabajo de banco: el repositorio no
cambia por esto.

## 2. Lo que eso fija, y que era una pregunta abierta de la ficha

D38 dejaba escrito que la guía de la referencia **no define en ninguna página**
una «maximum effective normal stress» como salida del programa: sólo *Base
Normal Stress* como serie por dovela, registrada «at the midpoint of the base of
each slice». Quedaba anotado como pregunta, no como supuesto.

Ya no hace falta. La reducción `max` por dovelas de `N/base_length − u`
reproduce **tres valores publicados** sobre tres superficies, dos métodos y tres
envolventes, a **3–13 partes en 100 000**. Una definición equivocada no acierta
tres veces a la cuarta cifra.

Consecuencia para D38: la segunda salida de su criterio de cierre — «documentar
que la magnitud publicada no es la que OGR calcula» — **se estrecha mucho**. Sí
es la que OGR calcula. Quien la use ahora tiene que decir qué tienen el 44 y el
61 que no tenga el 45.

## 3. Sexta causa descartada: el pico no es un artefacto de los extremos

Era la hipótesis del paso 2 del encargo, y la única vía que separaba «geometría
empinada» de «convenio de reporte»: un máximo en la primera o la última dovela
sería un artefacto de la discretización.

`_tools/medir_d38_sigma.py --perfil`, ocho filas, 30 / 50 / 100 dovelas:

- la **posición normalizada del pico** se queda entre **0,47 y 0,58** del arco
  en las ocho;
- no se mueve al refinar de 30 a 100;
- quitar una dovela de cada extremo, o dos, cambia σ′max **+0,00 %** en las
  ocho.

Y pasa **igual** en las filas que cuadran y en las que no, así que el convenio de
los extremos no puede separar unas de otras. Descartada.

De paso se verificó lo barato que quedaba por verificar: la **transcripción de
los círculos**. Para las ocho superficies, la distancia del centro a los dos
afloramientos publicados concuerda con el radio publicado a **menos de un
milímetro** (peor caso +0,00054). Están bien leídos.

## 4. El ancla de σ′max del test estaba cruzando dos superficies

Y esto es lo único que toca el repositorio.

`tests/test_janbu_base_forces_v1107.py` fijaba su ancla 3 sobre los círculos
`(-0.977, 9.501, 9.551)` y `(-1.665, 9.968, 10.106)`, corriendo **Janbu** sobre
ellos y comparando contra 36,33 y 30,05. Son los dos círculos publicados del
problema 61 del banco, y **sus dos paneles dicen `Method: spencer`**, mientras
que 36,33 y 30,05 son las filas de **Janbu** de la tabla, medidas sobre el
círculo crítico de Janbu, que ese problema **no publica**. El test pasaba a
−1,9 % y +1,2 % dentro de una banda de ±3 %, y su docstring lo llamaba «on the
published critical circle».

No es una diferencia de redondeo. Medido: el círculo crítico que Janbu encuentra
en ese modelo queda a **3,010 m** del centro del panel con el radio **2,820 m**
menor (curva de potencia), y a 2,579 m / 2,518 m menor (Mohr-Coulomb). Es otro
mecanismo.

El ancla se muda al **ejemplo 2 de Baker**, que es el problema 45 y que sí
imprime centro, radio, afloramientos y `Method: janbu simplified` en el mismo
panel que la fila de la tabla que se compara. Banda **±0,5 %**, seis veces más
estrecha que la que sustituye, con +0,003 % y −0,005 % medidos. Y dos anclas
nuevas que la vieja no tenía:

- **el factor también** tiene que caer dentro del ±0,5 % sobre la misma
  superficie. Una σ′ que acertara con el factor fuera sería justo el accidente
  interesante — y es lo que el ancla vieja era: la tensión dentro del ±3 % con
  el factor a −3,6 %;
- **el arco se recorta de verdad**: se afirma que la superficie es
  `CompositeSurface` y que ninguna base queda por debajo del contorno, para que
  un cambio que dejara de recortar falle aquí y no con un mensaje confuso.

### La lección que salió de rehacer el test

`test_it_is_a_stress_and_not_the_force` afirmaba `max(fuerza) < 0,5·σ′
publicada`, y sobre el ejemplo 2 **falla**: da 153,72 contra 99,50. No es un
fallo del motor, es que la afirmación estaba escrita en la dirección
equivocada. El cociente entre la fuerza y la tensión **es la longitud de la
base**: en el ejemplo 3 —talud de 6 m, 50 dovelas, bases de ~0,2 m— la lectura
equivocada sale pequeña, y en el ejemplo 2 —12 m, 30 dovelas, bases de ~1,5 m—
sale **+54 % demasiado grande**. Leer «demasiado pequeño» como la firma del
error era generalizar de un caso. Ahora se afirma lo único que es cierto: que
los dos números son distintos.

## 5. Dos defectos nuevos, reportados y NO tocados

### D81 — Bishop no rellena las columnas por dovela sobre superficie compuesta

`BishopSimplified._general_moment_fos` —la rama para cualquier superficie que no
sea un círculo— devuelve su `LEMResult` en
[bishop.py:324](../../ogr_slip2d/methods/bishop.py) **sin**
`base_normal_force`, `base_shear_force` ni `base_shear_strength`, mientras la
rama circular sí las rellena en `bishop.py:614`. Medido sobre el círculo
publicado de la 45.2, 30 dovelas: Bishop devuelve `len(base_normal_force) = 0` y
los otros tres métodos devuelven 30.

Es **anterior a este trabajo** — el problema 57 ya lo traía con 0.1.147 — y es
la misma laguna que `test_janbu_base_forces_v1107.py` documenta para las dos
ramas de Janbu hasta v0.1.107, cuando **no era cosmética**:
`rapid_drawdown._stage1_state` lee la normal en la base, y con la lista vacía el
desembalse en dos etapas aplicaba resistencia no drenada a cero dovelas. Hoy esa
función **comprueba la longitud y lanza `RapidDrawdownError`**
(`rapid_drawdown.py:348`), así que la consecuencia no es un número malo sino que
la combinación Bishop + compuesta + desembalse **no funciona**, con un mensaje
que culpa al método sin decir que sólo falla fuera del círculo.

No se corrige aquí porque la corrección tiene una pregunta dentro: sobre los
tramos rectos el equilibrio que la rama general resuelve lleva el término
`Σ N·f` de Fredlund y Krahn (1977), y hay que comprobar que la N reconstruida
satisface el equilibrio vertical por dovela **ahí** antes de publicarla.

### D82 — el escenario Mohr-Coulomb del problema 61 no tiene fila

Es de banco. `referencia.json` del 61 publica cuatro filas y su bloque `fos`
—el que consume la comparativa— sólo lleva dos, así que las dos de Mohr-Coulomb
(Janbu 1,291 / 30,05 y Spencer 1,366 / 26,44) no se comparan nunca aunque el
modelo se construya y se corra. Misma forma que D03e, corregida para el 44 el
2026-08-29 y no para el 61. Medidas a mano caen a −2,44 % y −3,48 %: son dos
filas de discrepancia sin contar, en el problema de D38.

## 6. Lo que esta versión NO resuelve, dicho claro

El **+8,5 % del 44 y el +11,5/12,5 % del 61**. Siguen sin causa, y ahora sin
siete explicaciones en vez de sin cinco: ni la aritmética de la normal (I5), ni
la hipótesis interdovela, ni el cociente entre métodos, ni «Spencer sobrestima
σ′» —refutado ya por partida triple—, ni el cortante, el mallado, el factor, el
reporte o la geometría, **ni el convenio de los extremos, ni la definición de la
magnitud, ni la transcripción del círculo**.

Quedan dos pistas nuevas, y las dos apuntan a la **masa deslizante** y no a σ′:

1. **El valor publicado está por debajo de la estática.** En las cuatro filas
   que se desvían, `γ·h·cos²α` en la dovela del pico —el peso de la columna de
   tierras resuelto sobre la base, sin método de por medio— queda por encima de
   lo publicado: 17,01 contra 15,40 (44.2), 10,53 contra 9,62 (44.4) y 34,74
   contra 31,21 (61.2). En las tres del 45 que cuadran, coincide a menos del 1 %.
2. **En el 61 falla también el factor**, en los cuatro cruces de método y
   envolvente y hacia abajo: −1,39 %, −2,44 %, −3,61 % y −3,48 % sobre los
   círculos publicados. Sus filas están en `REVISAR`, no en `OK`. El enunciado
   del encargo decía «dentro del 1 %» y no lo está. En el 61 lo que no cuadra
   es el problema entero.

## Verificado

- `tests/test_janbu_base_forces_v1107.py` — 22 de 22, con el ancla nueva.
- **I5** (`test_spencer_base_normal_v1141.py`), **I1–I4**
  (`test_gle_interslice_v1106.py`) y los tres `test_slide_validation_*`: 77 de
  77, sin mover una tolerancia ni un dígito.
- Suite entera sin filtrar.
- Producción sin tocar: los únicos archivos con cambio de comportamiento son el
  test y los siete números de versión.
- Banco: 45.4 en 2,695564 / 82,2604; las tres superficies del 45 evalúan;
  `auditoria_invariantes.py` con **ERROR = 0** y cero hallazgos en el 45; la
  comparativa sólo cambia en las filas del 45.
