# OGR Slip2D v0.1.123

**Pilote de Ito y Matsui** — la fuerza del pilote deja de ser un dato del
usuario y pasa a deducirse del espaciamiento; y la relación
separación/diámetro resulta ser el único parámetro que sobrevive.

---

## Lo que se añade

Un **modo de rotura** nuevo en el pilote que ya existía. Hasta ahora
`PileMicropile` aplicaba una fuerza **constante** —`pile_shear_strength /
out_of_plane_spacing`—, que es la resistencia estructural de la sección
dividida por la separación. Eso responde a *cuánta carga aguanta el pilote
antes de romperse*. La pregunta que se hace de verdad al proyectar una fila
de pilotes de estabilización es la otra: **cuánta carga le entrega el
terreno**, y esa la fija el suelo que fluye entre ellos, no el acero.

El modo **Ito & Matsui** la calcula. La presión lateral sobre un pilote de
la fila se integra **desde el techo del pilote hasta el corte con la
superficie de rotura**, y se divide por la separación:

```
force_at(d) = (1/D₁) · ∫₀ᵈ p(z) dz
```

Es el hueco **D26** del banco de verificación (problema 106).

Las ecuaciones viven aparte, en `ogr_core/support/ito_matsui.py`, sin
proyecto y sin geometría, para que se puedan contrastar con su fuente
aisladas: **Ito, T. y Matsui, T. (1975)**, «Methods to estimate lateral
force acting on stabilizing piles», *Soils and Foundations* 15(4) 43-59,
Ecs. **(13)** (suelo c–φ), **(14)** (c = 0) y **(23)** (φ = 0).

## Dos impresiones de la misma ecuación, y no es un lujo

La Ec. (13) está publicada **dos veces y por separado**: en Ito y Matsui
p. 47, y como Ec. (10) de **Cai, F. y Ugai, K. (2000)**, «Numerical
analysis of the stability of a slope reinforced with piles», *Soils and
Foundations* 40(1) 73-84, agrupada de otra manera, en torno a
`A = D₁(D₁/D₂)^(√Nφ·tanφ + Nφ − 1)`. Un test escribe la segunda a mano y
exige que las dos coincidan a **8e-15**: es la única comprobación de
transcripción que una implementación no puede pasar por ser coherente
consigo misma.

La Ec. (23) tiene además su **re-derivación** desde las Ecs. (16), (19),
(21) y (22) del propio artículo, que sale idéntica a la impresa. Eso
descarta lo que un contraste con la propia ecuación no descarta: haber
leído mal el escaneo.

## Lo que decidió la división por D₁ fueron las UNIDADES

La ayuda del programa de referencia dice que en este modo el espaciamiento
«no es un cálculo aparte, entra como el valor D₁ de la ecuación». Leída
sola, esa frase admite las dos lecturas. No hizo falta resolverla leyendo:
`p` es fuerza por unidad de profundidad **por pilote** y `force_at` tiene
que devolver kN por **metro de ancho de talud**, así que sólo `Q/D₁` tiene
esas unidades. Y es lo que escribe Cai y Ugai en su Ec. (9),
`M_P = Q·R·cos θ / D₁`.

Comprobado además con los datos publicados antes de escribir una línea:
con D₁/D = 3 la ecuación da **q(z) = 30,28 + 38,04·z**, que para unos 6 m
de pilote movilizado son 866 kN por pilote, **361 kN/m** al dividir, y
sobre ese talud vale ΔF ≈ 0,22 — de 1,13 a **≈ 1,35** contra el **1,37**
publicado. Sin dividir habría dado ≈ 1,65.

## LA RELACIÓN SEPARACIÓN/DIÁMETRO ES EL ÚNICO PARÁMETRO QUE SOBREVIVE

Salió de un test que escribí para demostrar lo contrario. La Ec. (13) es
**homogénea de grado uno** en las dos longitudes: cada uno de sus términos
lleva exactamente una potencia de longitud. Escalar separación y diámetro
juntos multiplica `p` por ese factor, y **dividir por D₁ lo cancela
exactamente** — a 1e-16, no aproximadamente.

O sea: la fuerza por metro de talud **no depende de la separación ni del
diámetro por separado, sólo de D₁/D**. Eso no es una casualidad de esta
implementación, es la razón de que Cai y Ugai —y el manual de verificación
detrás de ellos— tabulen el problema contra *separación / diámetro* y nunca
contra ninguno de los dos a solas.

Y tiene una consecuencia práctica que hay que escribir: un barrido de
separación **a relación constante** no movería el número ni un dígito, y
leer eso como un ajuste inerte sería exactamente al revés.

## Un pilote de diámetro nulo no empuja nada, y es exacto

Con el hueco igual a la separación —diámetro cero— **todos los términos de
la Ec. (13) se cancelan contra otro**: los dos de cohesión entre sí y el
del recubrimiento consigo mismo. Un pilote que no ocupa sitio no puede
hacer que el suelo se estruje. Es la comprobación más afilada de la
transcripción que hay en el archivo, porque basta equivocarse en un
coeficiente para que la cancelación deje de ser exacta.

## La ecuación general es SINGULAR en φ = 0, y su límite es la Ec. (23)

La Ec. (13) divide por `Nφ·tanφ` y por `√Nφ·tanφ + Nφ − 1`, y los dos
tienden a cero con φ. Los dos sumandos de orden `c·D₁/φ` que eso genera
**se cancelan**, así que el límite existe y **es** la Ec. (23) — pero en
coma flotante esa cancelación es catastrófica.

El umbral no se eligió, se **midió**. Barriendo φ por décadas, el
desacuerdo entre las dos ramas cae 6,3e-4 → 6,3e-5 → 6,3e-6 → 6,3e-7 para
φ = 1e-4 … 1e-7 rad y luego **deja de caer**: 6,4e-8 en 1e-8, 9,2e-8 en
1e-9, 7,4e-7 en 1e-10, 1,9e-5 en 1e-11. El valle está en **1e-8**, con las
dos ramas de acuerdo a 6,4e-8 relativo. El test corre ese barrido y falla
si la constante se mueve **en cualquiera de las dos direcciones**.

## El problema 106: la ficha decía que la geometría no existía, y existe

Decía que «la geometría del modelo de Cai y Ugai sólo aparece como captura
de pantalla, sin coordenadas». **Es falso.** Su Fig. 2 está acotada y su
Tabla 1 publica las propiedades enteras: talud de 10 m a 1V:1,5H sobre 10 m
de terreno, 35 × 20 m, γ = 20 kN/m³, c = 10 kPa, φ = 20°, pilote de 0,8 m a
7,5 m del pie, D₁ = 3D. Y la captura del manual **corrobora** esos números
en vez de sustituirlos: midiendo sobre ella el pilote cae en x ≈ 17,4
(Lx ≈ 7,4), la cabeza en y ≈ 15,1 y el pie en y ≈ 1,4.

**Puerta (a), sin pilote**: OGR da **1,1474** contra el **1,13** de Bishop
de Cai y Ugai, **+1,54 %**, y el mínimo está convergido —de rejilla 26×26 a
30×30 se mueve un 0,06 %—. Esa puerta mide OGR y no Ito-Matsui, y por eso
va primero.

**Puerta (b), con pilote.** La tendencia se reproduce entera, y el sesgo de
la puerta (a) explica los extremos pero no el medio:

| D₁/D | Cai y Ugai | Slide2 (manual) | OGR tangencial | OGR horizontal |
|---|---|---|---|---|
| sin pilote | 1,13 | 1,14 | 1,1474 (+1,5 %) | — |
| 2 | 1,54 | 1,54 | 1,5626 (+1,5 %) | 1,5626 (+1,5 %) |
| 3 | 1,37 | 1,43 | 1,4735 (+7,6 %) | 1,4912 (+8,9 %) |
| 4 | 1,31 | 1,33 | 1,3604 (+3,9 %) | 1,3722 (+4,8 %) |
| 6 | 1,25 | 1,25 | 1,2724 (+1,8 %) | 1,2800 (+2,4 %) |

Dos cosas que conviene mirar en esa tabla. La primera: **el programa de
referencia sale alto exactamente donde sale alto OGR** —clavado en 2 y en
6, alto en 3 y en 4—, lo que apunta a que los dos hacen lo mismo y a que la
diferencia está entre la formulación y los valores que Cai y Ugai publican
en su Fig. 4. La segunda: **la explicación que da el propio manual no cubre
el caso de OGR**. Atribuye sus diferencias «a los distintos métodos de
búsqueda», y aquí la búsqueda está agotada: refinar la rejilla de 26×26 a
40×40 mueve el D₁/D = 3 un **0,04 %** (1,4735 → 1,4731). Queda anotado como
lo que es, un residuo medido y sin causa nombrada.

En D₁/D = 2 el mínimo lo gana una superficie **que no corta el pilote**: la
fila es tan eficaz que todas las que lo cortan suben por encima. Es el
cambio de mecanismo que describen Cai y Ugai, y es la razón de que las dos
orientaciones den ahí el mismo número al último dígito.

## Las dos orientaciones se midieron, y no se eligió la que ajusta

Cai y Ugai aplican la fuerza **horizontal** —su Ec. (9) da el momento como
`Q·R·cos θ/D₁`, que es el de una fuerza horizontal aplicada en el corte— y
la referencia declara **tangencial** como orientación por defecto del
pilote. Para un pilote vertical, *perpendicular al pilote* **es**
horizontal, así que OGR tenía ya las dos y no hizo falta código nuevo:
hizo falta medirlas. La tangencial, que ya era el valor por defecto, es
además la más cercana — el orden importa, porque elegir la orientación
*porque ajustaba* costó dos versiones en v0.1.112.

Y hay una tercera diferencia, ahora medida exactamente: OGR **parte** la
fuerza horizontal en su componente sobre la base y su componente normal a
ella —`T_S = F·cos θ` y `T_N = F·sen θ`, a la última cifra—, y cobra
`T_N·tanφ'` que la Ec. (9) de Cai y Ugai no tiene. En este modelo `T_N` es
más de un **20 %** de la fuerza. No es un defecto de ninguno de los dos: es
que no son la misma formulación, y ahora está escrito.

## Un defecto que dejó D28, y que sólo se ve mirando

El mecanismo que deshabilita los campos que el modo elegido no lee
(`PARAMETER_USED_BY`, v0.1.122) estaba **cableado al nombre
`profile_type`**. D28 generalizó el campo de la TABLA y dejó cableado el
campo del MODO, y no se notó porque sólo un tipo lo declaraba. El segundo
tipo que lo declara recibía un combo que **no deshabilitaba nada** y cuatro
campos editables en los dos modos — que es exactamente el defecto que ese
bloque existe para evitar. Lo destapó abrir el diálogo y mirarlo, no
razonar sobre él. Se arregla con dos declaraciones de clase, `MODE_FIELD` y
`TABLE_SHOWN_FOR`, y un test que recorre los dos tipos.

## Y otras cinco cosas menores

- **La nota del punto de aplicación se generaliza.** D28 la escribió dentro
  del módulo del muro; ahora hay dos tipos que ofrecen ese ajuste, y una
  regla escrita en dos sitios se queda obsoleta en uno. Vive en
  `ogr_slip2d/support_notes.py` y los dos módulos la piden.
- **`NEEDS_BOND_PROFILE` y `MEASURED_FROM_TOP` pasan a ser por instancia**
  en el pilote: un pilote en modo cortante no puede pagar 50 muestras de
  suelo por análisis para un número que no lee, y `MEASURED_FROM_TOP`
  además **excluiría del análisis** un pilote dibujado horizontal, que en
  modo cortante es legítimo.
- **c y φ equivalentes** salen de `BishopSimplified._local_c_phi`, la única
  linearización de envolvente del programa y la que usan los nueve métodos.
  Un test de identidad ata las dos, y con eso los veinte modelos
  constitutivos entran gratis en vez de sólo Mohr-Coulomb.
- **σ'_v y no γz.** Ito y Matsui escriben la tensión total porque en su
  artículo no hay agua en ninguna parte; con parámetros efectivos la
  presión activa de Rankine se escribe sobre la efectiva. El análisis lo
  avisa cuando hay presión intersticial sobre el pilote, y la teoría, que
  calla, no queda como si hubiera hablado.
- **`q(z)` puede salir negativa** cerca de la superficie, cuando la
  cohesión pesa más que el recubrimiento. Se integra tal cual y se avisa;
  recortarla muestra a muestra subiría el total en silencio.

## Lo que NO se hace, y por qué

- **El modo EFW**, el tercero del pilote en la referencia. Ningún problema
  del banco lo valida, así que su única ancla sería la fórmula de la propia
  ayuda del programa de referencia, que no es fuente científica externa.
- **Corregir la formulación.** Zhang y otros (2017), *J. Geotech.
  Geoenviron. Eng.* 143(9), sostienen que la solución de Ito y Matsui
  subestima la fuerza —tanto más cuanto mayor es φ— y que a espaciamientos
  cerrados supera el empuje pasivo. No se aplica: los únicos factores
  publicados contra los que esto se puede validar se calcularon con la
  original, y sustituirla dejaría la validación sin nada contra qué
  contrastar. Se cita en el docstring, que es donde un usuario la necesita.
- **Proyectar la integral sobre la vertical** en un pilote inclinado. La
  teoría es para una fila vertical y no dice qué hacer; se integra a lo
  largo del fuste y se avisa a partir de 2° de desplome.

## Anotado y no corregido

- `path_optimize` no hace nada sobre una búsqueda circular —lo que optimiza
  son polilíneas—, así que activarlo en este problema no movió un dígito.
  No es un defecto de esta versión; es un ajuste que el usuario puede
  encender sin efecto según el tipo de superficie.
- El residuo de +3,9 % y +7,6 % en D₁/D = 4 y 3 frente a Cai y Ugai, con la
  búsqueda ya agotada.

## Archivos

**Nuevos**: `ogr_core/support/ito_matsui.py`,
`ogr_slip2d/support_notes.py`, `ogr_slip2d/ito_matsui_notes.py`,
`tests/test_ito_matsui_pile_v1123.py`,
`spec/features/003-pilote-ito-matsui/`.

**Tocados**: `ogr_core/support/support.py`, `ogr_core/support/bond.py`
(primer momento y linearización de punto), `ogr_core/support/__init__.py`,
`ogr_core/support/retaining_wall.py`, `ogr_slip2d/support_integration.py`,
`ogr_slip2d/retaining_wall_notes.py`, `ogr_slip2d/analysis_runner.py`,
`ogr_gui/dialogs/define_support_dialog.py`, `ogr_gui/i18n/__init__.py`,
`tests/test_i18n_coverage_v141.py`, `docs/plugins.md`, y los siete sitios
de versión.

## Probado

- 41 tests nuevos en `tests/test_ito_matsui_pile_v1123.py`.
- Las dos impresiones de la Ec. (13) a 8e-15; la Ec. (23) contra su
  re-derivación; el diámetro nulo a 7e-12 absoluto; el límite φ → 0 con la
  convergencia de primer orden comprobada década a década.
- La escala: `q/D₁` invariante a 1e-16 sobre un factor 50 de tamaño.
- Regla 7 en las dos mitades, incluida la que es fácil no afirmar: el punto
  de aplicación mueve cuatro métodos y **no puede** mover los otros cinco,
  bit a bit.
- El modo cortante no se mueve un bit, y no construye perfil.
- Un `.ogr` de 0.1.122 abre en modo cortante y da el mismo número.
- El banco: puerta (a) a +1,54 % con la rejilla convergida, y puerta (b)
  con las dos orientaciones y cuatro relaciones.
- Suite entera, sin argumentos.
