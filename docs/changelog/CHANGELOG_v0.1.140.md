# OGR Slip2D v0.1.140

**Defecto D44, que ya estaba cerrado — y el encargo pedía el arreglo al
revés.** Esta versión **no toca producción**: cero líneas de motor. Trae la
medida que sostenía el cierre y que sólo vivía en un changelog, y la mitad del
arreglo de 0.1.137 que **ningún test podía ver** — con la explicación de por
qué ninguno de los cuatro archivos que cubren soportes podía verla.

---

## 1. El encargo llegaba declarando abierto un defecto cerrado, y es el tercero

`P-D44` manda decidir si se quita `T_N·tanφ'` del numerador de Bishop, con el
banner **ABIERTO, medido y con causa nombrada, NO corregido**. Está cerrado
desde el 2026-08-31, en 0.1.137, **el mismo commit que D39 y D42**.

Lo que hace este caso peor que el de 0.1.139 es que **el archivo de récord se
contradice a sí mismo en tres sitios a la vez**: la cabecera de la ficha D44 y
el índice de tier 5 dicen CERRADO, y **el cuerpo de esa misma ficha, ocho
líneas más abajo, sigue diciendo «Estado: ABIERTO»**. Y el changelog de 0.1.139
ya había listado `P-D44` por su nombre entre los siete prompts con el banner
caducado. Nadie tenía que descubrirlo: había que leerlo.

### Y el arreglo real fue el CONTRARIO al que el encargo propone

El encargo propone **quitar** el término. 0.1.137 lo **metió dentro de `m_α`**,
que es lo que sale de resolver el equilibrio vertical de la dovela. Sobre esta
familia las dos cosas dan el mismo número, y por una razón que conviene decir:
**las láminas de geotextil son horizontales**, y para una fuerza horizontal

    down = T_N·cos α − slide_sign·sin α·T_S = F·sin α·cos α − F·sin α·cos α

es idénticamente cero en el caso activo. Meter la carga en `W_eff` equivale
entonces a no sumar nada, o sea a quitar el término. **Las dos recetas se
separan en cuanto la fuerza tiene componente vertical**, y ahí sólo una es
correcta. El encargo acertaba el síntoma y el método por el que llegaba a él
—retroanálisis sobre ocho problemas de la misma geometría— no podía distinguir
las dos.

## 2. La medida que sostenía el cierre no estaba en el banco

Vivía en la tabla de un changelog. Ahora es
`_tools/medir_d44_separacion.py` → `_auditoria/D44_SEPARACION_0.1.139.md`, y se
remidió **antes de tocar nada**, sobre 0.1.139:

| # | círculo de | Bishop | Spencer | sep. OGR | sep. manual |
|---|---|---|---|---|---|
| 87 | Bishop | 1,0330 | 1,0376 | 0,44 % | 5,20 % |
| 88 | Spencer | 1,0991 | 1,0977 | **0,13 %** | 0,19 % |
| 89 | Spencer | 1,0106 | 1,0080 | **0,25 %** | 0,51 % |
| 90 | Spencer | 0,9141 | 0,9242 | **1,10 %** | 0,20 % |
| 91 | Spencer | 0,9806 | 0,9515 | 3,06 % | 2,18 % |
| 92 | Bishop | 0,8579 | 0,8785 | 2,34 % | 6,66 % |
| 93 | Spencer | 1,0143 | 1,0156 | **0,13 %** | 0,10 % |
| 94 | Bishop | 1,0340 | 1,0384 | 0,43 % | 7,88 % |

Reproduce el cierre **dígito a dígito** dos versiones después. Lo que el
medidor añade y la tabla vieja no tenía:

- **de quién es cada círculo**. Los ocho publican **una** superficie crítica y
  no todas del mismo método: el 87, el 92 y el 94 la de Bishop; los otros cinco
  la de Spencer. La separación que afirma D44 es la del MÉTODO, y sólo se mide
  poniendo los dos sobre la misma superficie — la columna de búsqueda de la
  comparativa mezcla eso con la búsqueda, y ahí el 92 «separa» un 14 %;
- **el gemelo sin refuerzo**, vaciando `supports` en memoria sobre el mismo
  modelo, que es el ancla del propio enunciado: 0,10 % a 0,45 %, salvo el 91;
- **tres testigos** —Fellenius, GLE y Janbu— porque un desvío compartido no es
  del término.

## 3. El criterio de cierre NO se cumple entero, y el sondeo dice que no es esto

El criterio pedía **≤ 0,5 %** en el 88, 89, 90 y 93. Tres cumplen; **el 90 sale
a 1,10 %**, y no se encoge al refinar: **1,11 / 1,10 / 1,11 / 1,11 %** a 25, 50,
100 y 200 dovelas. Por la propia regla que este proyecto usa, un residuo que no
se encoge es de formulación.

Antes de escribirlo como defecto, se sondeó. **Forzando la fuerza a tangente a
la superficie `n_press` es idénticamente cero y la rama normal desaparece
entera**; si el residuo fuese ese término, se iría con ella:

| # | separación hoy | con la fuerza TANGENTE | aporte B/S hoy | tangente |
|---|---|---|---|---|
| 90 | 1,10 % | **1,13 %** | 0,9761 | 0,9738 |
| 92 | 2,34 % | **1,94 %** | 0,9527 | 0,9579 |

**No se va.** El residuo del 90 y del 92 sobrevive a la desaparición del término
que D44 nombra, así que **la causa que D44 nombraba está cerrada y lo que queda
ahí es otra cosa**. Queda anotado como tal en la ficha, no arreglado: el 92 es
además el único de la familia con agua y su separación **crece** con el dovelado
(1,83 → 2,34 → 2,37 → 2,83 %), que es la firma de un modelo, no la de un método.

Decir «D44 cerrado» sin esta línea habría sido cierto en la causa y falso en el
criterio.

## 4. Lo que sí faltaba: la mitad NO CIRCULAR, y por qué nadie podía verla

0.1.137 cambió **las dos** rutas de Bishop. La circular tiene dos archivos
encima; la de `_general_moment_fos` no tenía **ninguno**, y los cuatro que
cubren soportes fallan cada uno por su motivo:

| archivo | por qué no lo ve |
|---|---|
| `test_support_normal_v1137` | sólo `SlipCircle` |
| `test_support_tangential_v1139` | sólo `SlipCircle` |
| `test_support_active_passive_v1115` | **sí** usa polilínea, pero su forma cerrada es **φ' = 0**, donde el término es idénticamente cero |
| `test_efp_wall_v1122` | tiene la identidad carga≡soporte, pero con fuerza **horizontal y ACTIVA**, donde `down ≡ 0` |

Y el descubrimiento que ordena todo lo anterior: **con fuerza horizontal y
activa la carga sobre la dovela es exactamente cero**, porque una fuerza
horizontal no tiene componente vertical. La primera sonda de esta versión
anuló `support_vertical_load` sobre la fixture del 1122 y **el factor de
seguridad no se movió ni un bit** — no porque el arreglo no importase, sino
porque esa fixture no puede verlo. La familia entera que abrió D44 es
horizontal.

## 5. El test, con dos anclas y ninguna capturada

`tests/test_support_noncircular_v1140.py`, geometría en código como el resto.
Un anclaje **inclinado 20°** —ni horizontal ni tangente— sobre la misma
superficie escrita como círculo y como polilínea de seis vértices.

**La forma cerrada.** Para un soporte activo, con F a θ sobre la horizontal:

    down = F·sin(α−θ)·cos α − sin α·F·cos(α−θ) = −F·sin θ

o sea **la componente vertical de la fuerza, y nada más**. No depende de α, ni
de la superficie, ni del dovelado. Medido: −13,680806 en el círculo y en la
polilínea, con α = 30,99° y 32,30°.

**La identidad.** La misma fuerza, en el mismo punto, al mismo ángulo, entrando
como **carga lineal** en vez de como soporte —que es literalmente lo que dice la
página de la referencia en la que se apoyó 0.1.137— tiene que dar el mismo
factor. Llegan por código sin relación: una por `resolve_support_terms` y `sup`,
la otra por el rebanador. Sobre la polilínea:

| | 50 dovelas | 100 | 400 |
|---|---|---|---|
| Bishop | −0,087 % | −0,019 % | −0,0020 % |
| Fellenius | −0,133 % | −0,029 % | −0,0031 % |
| Spencer | −0,048 % | −0,011 % | −0,0011 % |
| GLE | −0,048 % | −0,010 % | −0,0011 % |

Los cuatro encogen ×40 y Bishop es el **segundo mejor** de los cuatro: lo que
queda es malla.

### La comprobación de que discrimina

Anulada la rama (la aritmética pre-0.1.137 en lo que toca al equilibrio
vertical), **4 de las 14 aserciones caen** y la identidad se va a
**−3,56 / −3,57 / −3,58 %** sin encoger. Las 10 que siguen verdes son las que
deben: las cuatro premisas de la fixture, la de fuerza horizontal (0 = 0, y por
eso está escrito que no discrimina), la de independencia de α (ídem), y la
última clase, que **espera** la rotura. Fuera de este archivo, los cuatro de
soportes pierden **11 de 75**.

El parche se deshace en `finally` y hay un test que lo comprueba: un
monkeypatch filtrado sobre un módulo de producción es el peor de todos, porque
sólo aparece en la suite completa (regla 5).

### Un test que se cazó a sí mismo

La primera versión de `test_it_does_not_depend_on_the_base_angle` refinaba la
malla para obtener dos α distintas. **En una polilínea eso no funciona**: todas
las dovelas de un tramo comparten la pendiente del segmento, así que α salía
idéntica al último bit y el test comparaba un número consigo mismo. Lo cazó su
propia guarda —estaba escrita para eso— y ahora las dos α vienen de las dos
superficies, 30,99° contra 32,30°.

## 6. Medido y NO asertado

Comparar el aporte del soporte `ΔF = F(con) − F(sin)` entre el camino circular
y el mismo círculo como polilínea densa. **No discrimina**: la razón de Bishop
es 1,011 hoy y 1,026 con la rama anulada, sobre una base que **no es 1** de
partida, porque los dos caminos toman el arco y la cuerda respectivamente y
`bishop.py` lo documenta como decisión deliberada desde v0.1.92. Una
casi-identidad con la referencia moviéndose no demuestra nada, así que queda
escrita en el archivo en vez de asertada.

## 7. Qué se tocó

| archivo | cambio |
|---|---|
| `ogr_slip2d/**` | **nada**; producción sin tocar |
| `tests/test_support_noncircular_v1140.py` | nuevo: 14 aserciones sobre la rama no circular |
| banco · `_tools/medir_d44_separacion.py` | nuevo: la medida del criterio de cierre, que no escribe en ninguna ficha |
| banco · `_auditoria/D44_SEPARACION_0.1.139.md` y `.json` | la evidencia |
| banco · `ERRORES_Y_DISCREPANCIAS.md` | el cuerpo de D44, que decía ABIERTO; y la cabecera de D39, que no decía que su mitad de Bishop está cerrada |
| banco · `PROMPTS_RESOLUCION.md` | el banner de `P-D44` |

Los derivados del banco **no se re-corren**: ninguna cifra de producción se ha
movido, y `resultados.json` está regenerado en 0.1.138.

## 8. Qué queda

- **El 1,10 % del 90 y el 2,34 % del 92**, medidos, con el sondeo que descarta
  el término de D44 y sin causa nombrada todavía.
- **La mitad de Janbu de D39/D46**, con sus cuatro combinaciones medidas y
  ninguna evidencia externa que elija. Esta versión no la toca.
- **Cinco prompts más** siguen declarando abierto un defecto cerrado —`P-D32`,
  `P-D33`, `P-D36`, `P-D13`, `P-D40`— y `P-D39` sigue siendo el de banner a
  medias. No se barren a ojo: cada uno cuesta leer su cierre.

---

**Suite**: entera, sin filtrar.
