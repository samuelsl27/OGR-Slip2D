# OGR Slip2D v0.1.139

**Defecto D42, que ya estaba cerrado.** Esta versión **no toca producción**:
cero líneas de motor. Lo que trae es la evidencia que faltaba debajo del cierre
de 0.1.137 — un caso publicado ejercitando la mitad del arreglo que **ningún
test tocaba** — y el encargo de D42 puesto al día en el banco.

---

## 1. El encargo llegaba declarando abierto un defecto cerrado

`P-D42` manda averiguar *«de dónde salen los 10,70 kN/m que declara el
enunciado y por qué la referencia se comporta como si fueran 9,28»*, con el
componente ya señalado: `ogr_core/support/support.py::PileMicropile.force_at`.
Su banner decía **ABIERTO, re-medido el 2026-08-29 con OGR 0.1.127**.

Estaba cerrado desde el día anterior, en 0.1.137, y **el propio archivo lo
sabía**: su índice de tier 5, 1780 líneas más arriba, ya registra el cierre.
Un archivo contradiciéndose a sí mismo, que es la forma en que
`AGENTS.md` avisa de que una regla en dos sitios envejece mal en uno de ellos.

Medido sobre 0.1.138 antes de tocar nada, para no dar por bueno un cierre sin
comprobarlo:

| | publicado | 0.1.127 | 0.1.138 |
|---|---|---|---|
| **con** pilote, círculo 54.3 | 1,193 | 1,2118 (+1,57 %) | **1,1953 (+0,19 %)** |
| **sin** pilote, círculo 54.2 | 1,102 | 1,1011 (−0,08 %) | 1,1011 (**no se mueve**) |

Y convergente, que es lo que separa un cierre de una coincidencia:
**+0,40 / +0,19 / +0,18 / +0,18 / +0,18 %** a 25 / 50 / 100 / 200 / 400
dovelas. Con la orientación que la guía documenta —`modelo.ogr` declara
`TANGENT_TO_SLIP`, no una elegida a posteriori—, que es la mitad del criterio
de cierre que suele perderse.

## 2. La pregunta del encargo no tenía respuesta porque no era una pregunta

Los **9,28 kN/m** que había que explicar no son un dato del manual. Son el
resultado de despejar `(1,193 − 1,108263) · ΣW·senα` **bajo una aritmética
rota**: la cifra que habría hecho falta si el soporte entrara en Bishop como
una suma limpia al momento resistente, que es justo lo que dejó de hacer en
0.1.137. Por eso no correspondía a ninguna de las seis orientaciones y hacía
falta «una fuerza a 12,2°»: se estaba resolviendo para el término equivocado.

El micropilote nunca estuvo mal. `force_at` devuelve
`pile_shear_strength / spacing` y entrega sus **10,70 kN/m intactos**. Con la
aritmética correcta el aporte efectivo mide **9,53 kN/m** (9,58 al refinar), y
el resto no se ha perdido: llega a la base **dividido por `m_α`**, como
cualquier otra carga sobre esa dovela.

**La lección no es el número, es la forma del razonamiento.** El encargo decía,
correctamente: *el término del suelo está validado a −0,08 %, luego el error
está en el término del pilote*. Las dos premisas eran ciertas y la conclusión
señalaba mal, porque el tercer candidato —**la aritmética que une los dos**— no
estaba en la lista. «El suelo o el refuerzo» es una disyunción incompleta
siempre que haya un método en medio.

## 3. Lo que sí faltaba: media función sin un solo test

`support_vertical_load` escribe la carga que el soporte pone sobre su dovela
como dos términos:

    down = T_N·cos α  −  slide_sign·sin α·(T_S,activo + T_S,pasivo/F)
           [ NORMAL ]     [            TANGENCIAL                    ]

`test_support_normal_v1137` cubre el primero. Su fixture es
**deliberadamente** un soporte puramente normal —`_purely_normal_angle()` hace
`T_S = 0` por construcción, y el archivo lo dice— así que **borrar el segundo
término lo dejaba entero en verde**.

En el 54 pasa exactamente lo contrario, y por eso es el caso complementario:
la fuerza del pilote es TANGENTE a la superficie, luego `T_N ≡ 0`
(max |n_press| = 2,7e−15 en las 50 dovelas) y **todo** lo que se mueve viene de
la rama tangencial. Medido anulándola:

| | FoS | Δ vs 1,193 |
|---|---|---|
| 0.1.138 tal cual | 1,195274 | +0,19 % |
| sin la rama **tangencial** | 1,211782 | **+1,57 %** |
| sin `support_vertical_load` entero | 1,211782 | +1,57 % |

Restaura el número de 0.1.136 **dígito a dígito**. Todo el cierre de D42 vivía
en un término que nadie comprobaba.

### El mecanismo, que es fácil de leer al revés

El pilote resiste ladera **arriba** a lo largo de la base; su reacción por tanto
**LEVANTA** la dovela de esa base, `W_eff` baja, y la fricción
`(W_eff − u·b)·tan φ'` baja con ella. Un soporte que ayuda en el equilibrio
tangencial devuelve algo en el normal. De v0.1.64 a v0.1.136 Bishop cobraba la
ayuda y no el coste — y por eso el error era **inseguro**.

## 4. El test, y por qué el par publicado es lo que lo convierte en medida

`tests/test_support_tangential_v1139.py`, geometría construida en código como
el resto de los benchmarks (la suite tiene que correr sin el banco en disco).

Yamagami (2000) publica **el par**: el mismo talud con pilote y sin él, sobre
**dos círculos distintos**, uno por figura. El gemelo sin refuerzo **no puede
moverse** —no hay soporte que lo cruce— así que sujeta el término del suelo
mientras el otro mide el del refuerzo. Un solo caso reforzado no separa los
dos, que es por lo que este error se leyó durante setenta y dos versiones como
un desacuerdo del 1,6 % sobre la geometría.

Nueve aserciones en tres clases:

- **el control**: el talud desnudo reproduce **su propio** círculo publicado, y
  los dos círculos no son la misma superficie —compararlo contra el reforzado
  es el error que tapó el término del suelo hasta 0.1.113—;
- **el par publicado**: 1,193 ± 1 %, que es el criterio de cierre de D42
  literal, con la orientación **asertada, no elegida** (`orientation=None` en el
  modelo, para que resuelva contra la declaración del propio tipo y el test
  falle si alguien cambia el defecto de fábrica);
- **el discriminante**: la ecuación de Bishop reconstruida término a término al
  factor al que converge, en las dos formas candidatas. La que incluye la carga
  tangencial cierra con residuo **+5,7e−05**; la otra falla por **+1,6e−02**,
  273 veces más.

**Nada capturado**: 1,193 · 1,102 · 10,7 kN · 1 m son todos publicados, y las
tolerancias son las del criterio de cierre, no las del error que se mide hoy.

### La comprobación de que el test discrimina

Anulada la rama tangencial:

- `test_support_normal_v1137` → **10/10 en verde**. No la ve. Ése era el hueco.
- `test_support_tangential_v1139` → **4 de 9 fallan**, y el caso reforzado
  devuelve `1.2117817539`.
- Los 5 que siguen verdes son los que deben: el gemelo desnudo, los dos
  círculos distintos, la orientación declarada, el cortante de la dovela
  cruzada y `n_press ≡ 0`. Un control que se pone rojo con todo no distingue
  nada.

## 5. Y una honestidad sobre las anclas de esta familia

Los problemas **60 y 85 no miden nada de esto**: son arcilla con **φ = 0**,
donde `tan φ' ≡ 0` anula el término entero. Salen idénticos y decir «no se han
roto» sería cierto y engañoso. El 54 tiene φ = 10°, y es la razón de que sea el
ancla y no ellos — cosa que el changelog de 0.1.137 ya decía en prosa sin que
nada en la suite la sostuviera.

## 6. Banco

- `02_Slide2_Problema054/referencia.json`: `medido_en` 0.1.113 → 0.1.138, las
  cifras de las dos orientaciones, la tabla de convergencia, y **A54-1 pasa a
  CERRADA** con el componente RE-ATRIBUIDO (`bishop.py` y
  `support_vertical_load`, **no** `PileMicropile.force_at`). Los números viejos
  se conservan en un sub-bloque, porque son los que este caso devuelve si
  alguien retira la rama.
- `PROMPTS_RESOLUCION.md`: el banner de `P-D42` pasa a CERRADO. El cuerpo del
  encargo **se conserva íntegro**, con sus números de 0.1.127: es la prueba de
  que un enunciado puede nombrar el componente equivocado con toda la confianza
  del mundo.
- `02_Slide2_Problema054/construir_modelo.py`: el último párrafo de su cabecera
  declaraba el defecto abierto.

Los derivados ya estaban bien y **no se re-corren**: `resultados.json` está
regenerado en 0.1.138 con 1,195274 / 1,101094 y la fila 54 de la COMPARATIVA ya
está en **OK**. Una versión que sólo añade un test no puede mover un número, y
volver a correr el caso son 31 minutos por coste sin información.

## 7. Lo que queda anotado, medido y sin tocar

**Otros siete prompts declaran ABIERTO un defecto que ya está cerrado**, con la
misma forma que tenía P-D42: `P-D32` (cerrado en 0.1.128), `P-D33` (0.1.129),
`P-D36` (0.1.131), `P-D13` (0.1.131), `P-D44` (0.1.137, el **mismo commit**
que D42) y `P-D40` (0.1.138). `P-D39` es el caso a medias y por eso el más
engañoso de los siete: su mitad de Bishop se cerró en 0.1.137 y la de Janbu
sigue abierta, así que su banner no es falso — es incompleto, que se lee
peor. El estado de récord vive en
`ERRORES_Y_DISCREPANCIAS.md`, y los banners no se han vuelto a mirar desde que
se escribieron. Se deja registrado en vez de barrerlo de paso: cada uno cuesta
leer su cierre, y hacerlo a ojo es como se llega a un banner que miente.

Y sigue **abierta la mitad de Janbu de D39**, con sus cuatro combinaciones
medidas y su desacuerdo congelado en un test desde 0.1.137. Esta versión no la
toca.

---

**Suite**: entera, sin filtrar.
