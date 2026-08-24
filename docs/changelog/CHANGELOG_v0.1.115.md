# OGR Slip2D v0.1.115

**El ajuste Activo/Pasivo del refuerzo no movía el número, y no eran dos
métodos sino siete: lo que faltaba no era una fuerza, era una división por F**

---

## De dónde salió

El encargo era la anomalía **A85-1**, verificada en 0.1.97: ni
`ogr_slip2d/methods/spencer.py` ni `gle.py` contenían una sola referencia a
`force_application`, así que el ajuste Activo/Pasivo de un soporte no cambiaba
su resultado. Es la **regla 7** del proyecto: un control configurable que no
mueve el número es peor que no tenerlo, porque el usuario cree que el análisis
lo respeta.

Lo primero fue volver a medirlo, porque el encargo traía medidas de diecisiete
versiones atrás. Sobre el círculo de la ficha —(14,778 · 37,889) R 27,141, 50
dovelas, problema 85 del banco: Duncan y Wright (2005) figura 6.34—:

| método | activo | pasivo | ¿distingue? |
|---|---|---|---|
| Ordinary / Fellenius | 1,768655 | 1,411550 | sí |
| Bishop | 1,768655 | 1,411550 | sí |
| Janbu simplificado | 1,626358 | 1,409103 | sí |
| Janbu corregido | 1,728243 | 1,497377 | sí |
| **Spencer** | **1,932337** | **1,932337** | **no** |
| **GLE / M-P** | **1,792091** | **1,792091** | **no** |
| **Lowe-Karafiath** | **1,966888** | **1,966888** | **no** |
| **Corps of Engineers #1** | **1,825348** | **1,825348** | **no** |
| **Corps of Engineers #2** | **2,319745** | **2,319745** | **no** |

El defecto seguía vivo y era **más ancho que el encargo**: cinco métodos, no
dos. Y sobre superficie **no circular** —la misma geometría, el mismo soporte,
una cuña de cuatro vértices— eran **siete de nueve**: sólo los dos Janbu
distinguían. Bishop y Ordinary, que sí lo hacen en círculo, entregaban a
`moment_terms` la suma `t_active + t_passive` como un solo bulto en el lado
motor.

De las tres premisas del encargo, dos ya no valían:

- **Spencer y GLE ya no daban el mismo número entre sí** (1,932337 frente a
  1,792091). Esa mitad de A85-1 la había cerrado D10; la ficha del banco
  estaba desactualizada.
- **El criterio de cierre publicado, «Spencer 1,884 / 1,872 ± 2 %», no era
  medible.** El manual no publica superficie para Spencer, así que 1,884 está
  medido sobre un círculo que no tenemos; y su pareja (−0,6 %) es la rara de
  la tabla frente a Bishop (−13,5 %) y GLE (−12,5 %). Se cerró contra el único
  Δ trazable del problema: **GLE sobre el círculo que sí publica la figura
  85.2**, (15,446 · 37,624) R 27,594.

## Lo que dice la referencia, y lo que el código tenía escrito al revés

La página que define el ajuste está en las dos versiones de la ayuda y **la
explicación cambió entre ellas**. La antigua publica **una** pareja de
ecuaciones, en términos de fuerza. La actual publica **cuatro**, y ahí está
todo: separa momentos de fuerzas, o sea que la distinción **está definida
también para los métodos de equilibrio completo**.

```
Activo  momentos  F = M_resistente / (M_volcador − M_refuerzo)
Activo  fuerzas   F = τ_disponible / (τ_requerido − T_refuerzo)
Pasivo  momentos  F = (M_resistente + M_refuerzo) / M_volcador
Pasivo  fuerzas   F = (τ_disponible + T_refuerzo) / τ_requerido
```

y atribuye la pareja a los **Métodos A y B de Duncan y Wright (2005),
capítulo 8**. Sólo la componente **tangencial** cambia de lado; la normal,
`T_N·tanφ'`, está en el numerador en las dos.

Había además un **test defendiendo el defecto**, con su razón escrita:

> `test_the_rigorous_methods_do_not_distinguish_them` —
> *«Active vs Passive is an artefact of writing the factor of safety as a
> ratio. A method that solves equilibrium sees a force, and a force has no
> such flag.»*

Es falso a la vista de las cuatro ecuaciones, y era la mejor pista de por
dónde iba el arreglo.

## El arreglo, y el camino equivocado que se recorrió antes

**Lo que faltaba no era una fuerza: era una división por F.** Un soporte
ACTIVO es una fuerza que ya está ahí y entra íntegra. Un soporte PASIVO es una
resistencia que sólo se moviliza en la medida en que se moviliza todo lo
demás, así que lo que actúa es `T_S/F` — y eso es exactamente lo que convierte
`F = R/(D − T)` en `F = (R + T)/D`. Una resultante guardada como `f_h`/`f_v`
**no tiene dónde meter esa F**, y por eso los cinco métodos daban un solo
número para los dos ajustes.

Así que el soporte llega ahora **partido** a todos los métodos:

- la parte **NORMAL** es una carga cartesiana sobre la dovela (`nf_h`,
  `nf_v`), entra entera en el equilibrio en los dos casos y de ahí sale
  `T_N·tanφ'` sin sumarlo a mano;
- la parte **TANGENCIAL** es una resistencia sobre la base, movilizada a
  `t_active + t_passive/F`. Ese es el único sitio donde el ajuste tiene
  efecto aritmético.

En Spencer y GLE eso es una línea dentro de `solve_branch`; en los tres
métodos de marcha (Corps of Engineers #1 y #2, Lowe-Karafiath) es una suma a
`k0`, y **es exacto, no una analogía**: el cortante movilizado de esa
recursión es `S/F = k0 + N·a`, así que una fuerza tangencial resistente `T` es
literalmente `k0 + T`.

### El camino equivocado

La primera versión del arreglo sacaba la tangencial **fuera** del equilibrio
de la dovela —la lectura literal de las ecuaciones publicadas, donde `T_S` es
un término global— y dejaba `N` sin ella. Con eso, la forma cerrada de φ' = 0
salía **espectacularmente bien**: Spencer pasaba de +8,2 % a **0,008 %**.

Era mentira. Lo destapó un test que ya existía y que no era mío:
`test_the_force_branch_matches_the_corps_recursion`, que exige que la rama de
fuerzas de GLE y la recursión de Corps of Engineers coincidan a **1e-6** con
refuerzo. Empezó a fallar por 0,13 %. La causa: al quitar la tangencial de
`h_drive` sin ponerla en la recursión de `E`, **la marcha de empujes entre
dovelas era la de un talud sin refuerzo mientras el factor de seguridad era la
de uno con refuerzo**. El sistema estaba sobre-determinado, y la «mejora» del
0,008 % era esa incoherencia haciendo converger la búsqueda de λ por
accidente.

Con la tangencial de vuelta en las dos proyecciones —vertical, `−T_mob·senα`
en `N`; horizontal, `+T_mob·cosα` en la marcha de `E`— la identidad con Corps
vuelve a cumplirse a 1e-6, y la forma cerrada da lo que de verdad da:

|  | activo antes | activo después | pasivo antes | pasivo después |
|---|---|---|---|---|
| Spencer | +8,49 % | +8,41 % | +27,67 % | **+4,29 %** |
| GLE / M-P | +0,80 % | +0,72 % | +18,63 % | **+1,22 %** |
| Lowe-Karafiath | +10,98 % | +10,98 % | +30,61 % | **+5,87 %** |
| Corps #1 | +4,15 % | +4,15 % | +22,57 % | **+2,93 %** |

(error contra `Σc'·l / (Σ W·arm ∓ T_S)`, la forma cerrada que φ' = 0 impone
sobre círculo, medida en el círculo publicado del problema 85 con 100 dovelas;
Bishop y Ordinary la reproducen exactamente.)

**La columna del activo casi no se mueve, y eso es el resultado honesto**: el
tratamiento que estos métodos ya tenían para ACTIVO *era* el de las
ecuaciones 1 y 2. Aplicar `t_active` a valor íntegro sobre la base es
algebraicamente la misma afirmación que aplicar la resultante entera como
carga cartesiana. Lo que cambia es PASIVO.

Lo que queda en la columna del activo es **una discrepancia distinta y
anterior**, que este cambio no toca y que conviene dejar anotada: sobre ese
círculo la búsqueda de λ de Spencer **no converge** —lo dice en su propio
`error_message`, «no λ leaves the inter-slice thrust in net compression»— y
cae al respaldo del F_f ≈ F_m más cercano. Está a **+3,79 % de la misma forma
cerrada sin refuerzo ninguno**. Los tres métodos de equilibrio de fuerzas, por
su parte, no están obligados por una identidad de momentos.

## Un defecto encontrado por el camino: doble contabilidad de T_N

La ruta **no circular** de Ordinary/Fellenius calculaba la normal de la dovela
proyectando las fuerzas exteriores **incluido el soporte entero**, y después
sumaba `T_N·tanφ'` a la resistencia **otra vez**. La ruta circular del mismo
método nunca ha metido el soporte en `N`.

Medido antes de tocarlo (regla 6), con un bulón perpendicular a un pilote
horizontal —T_N = −9,0 kN/m levantando, tanφ' = 0,364—, sobre una poligonal
muestreada del propio círculo:

```
                     círculo     poligonal    Δ
sin soporte          1,527168    1,529302    +0,14 %   <- discretización
soporte activo       1,552546    1,530128    −1,44 %   <- + doble T_N
soporte pasivo       1,534990    1,530128    −0,32 %   <- + doble T_N + A85-1
```

Corregido: el soporte ya no entra en la normal de Fellenius, exactamente como
en su ruta circular.

## Y otro: el brazo del momento del refuerzo en Spencer/GLE

El denominador de la rama de momentos de un círculo llegaba al momento del
refuerzo por el camino largo —la componente vertical montada en el brazo del
**centro de gravedad de la dovela** más un término aparte para la
horizontal—, y ese brazo no es el del soporte. La forma correcta no necesita
brazo ninguno: la parte normal pasa por el centro y su momento es
**exactamente cero**, y la tangencial tiene brazo **exactamente R**, que se
divide fuera de todos los términos. El denominador entero es `−T_S`.

En el círculo publicado del problema 85 eso llevó el denominador de
**8046,109 a 8032,365**, que es el valor exacto de la forma cerrada
(13794,31 − 5761,95).

## Cambios

- `ogr_slip2d/support_integration.py` — `SupportTerms` gana `nf_h`/`nf_v` (la
  resultante **normal** en cartesianas) y `x_app`. `f_h`/`f_v` se quedan como
  la resultante entera, que ya no lee ningún solver: es lo que enseña un
  informe. El punto de aplicación pasa a pesarse por la **magnitud** de la
  fuerza y no por `|F_h|`, que no tenía respuesta para un anclaje vertical.
- `ogr_slip2d/interslice.py` — `SliceRow` lleva `w_soil`, `t_active` y
  `t_passive`; `solve_branch` moviliza el refuerzo (`t_mob`) en las dos
  proyecciones de la dovela y reparte `sec α` entre numerador y denominador;
  el denominador circular usa el peso **sin soporte** y resta `Σ t_active`.
- `ogr_slip2d/moment_balance.py` — `moment_terms` gana `tangential_passive`,
  que suma al numerador mientras `tangential` sigue sumando al motor; `sup`
  pasa a significar la resultante **normal** aplicada en `(x_app, y_app)`.
- `ogr_slip2d/methods/modified_swedish.py` — `_march` y `_z_end` aceptan
  `t_support`; el contexto de la marcha lleva las dos listas y el buscador de
  raíz pasa `t_active + t_passive/F`.
- `ogr_slip2d/methods/bishop.py`, `ordinary.py` — ruta no circular: separadas
  la tangencial activa y la pasiva; y en Ordinary, el soporte fuera de la
  normal de Fellenius.

## Tests

**Nuevo** `tests/test_support_active_passive_v1115.py`, 14 casos y ningún
número capturado:

- **regla 7**: los **nueve** métodos dan números distintos en activo y en
  pasivo, sobre círculo y sobre poligonal;
- un soporte que **no cruza** la superficie no mueve nada, en ningún método
  ni en ningún ajuste;
- `F_pasivo < F_activo` en los nueve, que es la afirmación que publica la
  propia referencia;
- **forma cerrada** φ' = 0 sobre círculo, con soporte tangencial de capacidad
  conocida: `Σc'·l / (Σ W·arm − T)` y `(Σc'·l + T) / Σ W·arm`, exacta a 1e-9
  en Ordinary y Bishop;
- **identidad de tres corridas**: `F_pas = 1 + F_0 − F_0/F_act`, que sale de
  eliminar R y T entre las tres y que puesta en `F_act = 1` da `F_pas = 1` —
  la misma identidad con la que se valida el retroanálisis. Exacta en
  Ordinary; dentro del 3 % en los nueve, cuando los cinco rotos estaban a
  ~40 %;
- Spencer, GLE y Lowe-Karafiath siguen coincidiendo entre sí **también en
  pasivo**, que es lo que detecta que la ruta de `k0` y la de mover el término
  no digan lo mismo;
- el **caso publicado**: geometría del problema 85 embebida, círculo de la
  figura 85.2, GLE activo contra 1,575.

**Modificados**:

- `tests/test_supports_all_methods_v164.py` — invertido el test que defendía
  el defecto, con la razón vieja citada y explicado por qué era falsa. La
  banda de `test_the_gain_is_the_same_for_all_three` pasa de 0,5 % a 1 %:
  Spencer/GLE y Lowe-Karafiath llegan al caso pasivo por rutas distintas —la
  marcha no forma ningún cociente que mover— y el residuo es 0,61 % sobre una
  ganancia, frente al 0,49 % que esos tres ya discrepan **sin refuerzo**.
- `tests/test_modified_swedish_v198.py` — el contexto de la marcha lleva dos
  ranuras más; el ejemplo resuelto del EM 1110-2-1902 no tiene refuerzo, así
  que sus columnas publicadas las mueve la misma recursión de antes.

## Verificación

Los **siete problemas con refuerzo del banco** (47, 48, 54, 59, 60, 85 y 86),
corridos enteros antes y después sobre un árbol limpio en `HEAD`:

| caso | método | publicado | antes | después | Δ antes | Δ después |
|---|---|---|---|---|---|---|
| 047 | los cuatro | | | **sin cambio** | | |
| 048 | Spencer | — | 1,126952 | 1,115510 | | |
| 054 | los cuatro | | | **sin cambio** | | |
| 059 | Spencer | 0,596 | 0,709349 | 0,707345 | +19,02 % | **+18,68 %** |
| 060 | Spencer | — | 2,097259 | 1,649988 | | |
| 060 | Lowe-Karafiath | — | 2,028614 | 1,643933 | | |
| 085 pasivo | Spencer | 1,872 | 2,087916 | 1,774642 | +11,53 % | **−5,20 %** |
| 085 pasivo | GLE / M-P | 1,378 | 2,139921 | 1,628177 | +55,29 % | **+18,16 %** |
| 085 activo | los tres | | | **sin cambio** | | |
| **086** | **Spencer** | **1,620** | **1,626998** | **1,503595** | **+0,43 %** | **−7,19 %** |
| **086** | **GLE / M-P** | **1,622** | **1,628884** | **1,504344** | **+0,42 %** | **−7,25 %** |

Bishop, Ordinary y los dos Janbu no se mueven en ningún problema, y el caso
activo del 85 tampoco. Mejoran el 85 pasivo y el 59. **Empeora el 86**, y esa
es la parte que merece quedar escrita entera.

### Por qué el 86 empeora: dos errores que se estaban cancelando

Sobre el círculo crítico de Bishop del problema 86 —(−5,789 · 48,316)
R 48,296, 50 dovelas—, con el soporte del banco (cinco capas horizontales,
`passive`):

```
                          Bishop     Spencer
sin soporte              1,21077    1,21007    <- coinciden al 0,06 %
soporte ACTIVO           1,85384    1,64287    <- ya discrepaban un 11,4 %
soporte PASIVO (0.1.114) 1,64453    1,64380    <- coinciden al 0,04 %
soporte PASIVO (0.1.115) 1,64453    1,51778
```

La coincidencia de la tercera fila era eso: una **coincidencia**. Spencer
publicaba su número ACTIVO para un modelo PASIVO —el defecto de A85-1— y ese
número activo caía, por casualidad, a 0,04 % del pasivo de Bishop. Corregido
el reparto activo/pasivo, la casualidad se deshace y aparece lo que había
debajo: **Bishop y Spencer discrepan un 8-12 % en cuanto hay refuerzo**,
cuando sin él coinciden al 0,06 %.

### Y de dónde sale ese 8-12 %: el refuerzo descarga la normal de la base

Aislado con el mismo círculo y una orientación **tangente** al deslizamiento,
que pone `T_N` exactamente a cero para que no confunda la medida:

```
                              Bishop     Spencer    Spencer sin descargar N
TANGENTE pasivo  T_S = 4000   1,56782    1,45957 (−6,9 %)   1,57044 (+0,2 %)
TANGENTE activo  T_S = 4000   1,84653    1,61691 (−12,4 %)  1,82618 (−1,1 %)
```

La diferencia entera es que en Spencer, GLE y los tres métodos de marcha el
refuerzo entra en el **equilibrio de la dovela**, así que su componente
tangencial —que tiene componente vertical hacia arriba— **descarga la normal
de la base** y con ella la resistencia por rozamiento `(N − u·l)·tanφ'`. Con
φ' = 37° eso vale un 12 %. Bishop no lo hace: aplica el refuerzo como un
término global, `T_N·tanφ'` al numerador y `T_S` a un lado o al otro, y su
`N` es el de la dovela sin refuerzo.

**Y la referencia tampoco lo hace**: publica 1,629 / 1,620 / 1,622 para
Bishop, Spencer y GLE en este problema, los tres dentro del 0,6 %. Un método
que descargue la normal no puede quedarse a 0,6 % de Bishop sobre un talud
reforzado con φ' = 37°.

Queda **un residuo aparte** de un 3 %, visible en la fila horizontal del
problema 86: `T_N·tanφ'` sumado **fuera** de `m_α` como hace Bishop, o
resuelto **dentro** del equilibrio como hacen los demás. Es la diferencia que
`bishop.py` documenta desde v0.1.64 llamándola de segundo orden; aquí vale un
3 %.

**Ninguna de las dos cosas es nueva en v0.1.115**: las dos existían ya para el
caso ACTIVO —la fila «soporte ACTIVO» de arriba es idéntica antes y después—.
Lo que hace esta versión es dejar de taparlas con un tercer error. Se reportan
medidas y **no se corrigen aquí**: cambiar cómo entra el refuerzo en el
equilibrio de la dovela mueve el caso activo de los siete problemas del banco
y no es lo que pedía A85-1. Es una tarea propia.

### Y el arreglo evidente ya se midió: no vale

Quitar la descarga es lo primero que se le ocurre a cualquiera que lea lo de
arriba, así que se probó entero —copia del árbol, los siete problemas del
banco, la suite— antes de dejarlo escrito como pendiente. **No vale**, y
conviene que quede aquí para que no se vuelva a intentar dentro de tres
versiones.

Son dos cambios y no uno, porque el segundo es obligado: fuera `− T_mob·senα`
de `N`, y **el coeficiente de la rama de fuerzas pasa de `secα` a `cosα`**.
El `secα` sale de sustituir `N·senα` usando un equilibrio vertical que
*contiene* el refuerzo; sin él en la vertical, la misma álgebra da `cosα`.

| caso | método | publicado | v0.1.115 | sin descarga |
|---|---|---|---|---|
| 086 | Spencer | 1,620 | −7,19 % | −2,54 % |
| 086 | GLE / M-P | 1,622 | −7,25 % | −2,45 % |
| 085 pasivo | GLE / M-P | 1,378 | +18,16 % | +5,79 % |
| 085 pasivo | Spencer | 1,872 | −5,20 % | −11,72 % |
| **059** | **Spencer** | **0,596** | **+18,68 %** | **+146,61 %** |
| 059 | Lowe-Karafiath | 0,588 | −8,45 % | −10,55 % |
| 060 | Lowe-Karafiath | — | 1,64393 | 1,52865 |
| 048 | Spencer | — | 1,11551 | 1,60142 |

Arregla la mitad del 86 y **rompe el 59**. Y el 60 pierde lo único que tiene:
sin valores publicados, su evidencia es que Bishop, Ordinary, Spencer y
Lowe-Karafiath caen los cuatro entre 1,6440 y 1,6500, y el experimento saca a
Lowe-Karafiath a 1,5286.

**La razón de fondo, que es lo que merece recordarse.** Un momento es un
momento: sobre un círculo la tangencial del refuerzo tiene brazo `R` y la
rama de MOMENTOS se lleva `T_S·R` entero, con descarga o sin ella. La rama de
FUERZAS se lleva `T_S·secα` con el refuerzo en la vertical y `T_S·cosα` sin
él. Con la descarga las dos ramas describen **el mismo sólido libre**, y por
eso Spencer (momentos) y Lowe-Karafiath (fuerzas puras) coinciden al 0,9 %.
Sin ella se separan un 6,3 % sobre el mismo círculo, y esa coincidencia
cruzada es de las pocas comprobaciones que esta familia tiene sin solución
cerrada.

Dicho de otro modo: **el «bolt-on» de Bishop no es expresable en un método de
marcha.** En la recursión de Corps of Engineers la normal está eliminada
analíticamente de las dos proyecciones a la vez; no hay un «fuera del
equilibrio» donde poner el refuerzo.

Con el experimento aplicado fallan cuatro tests, tres de ellos por esa razón
de fondo y no por una banda mal puesta. Los que **siguen pasando** son los
que dicen que el experimento es autoconsistente dentro de la rama de fuerzas:
la identidad GLE ↔ Corps a 1e-6 con refuerzo, y las formas cerradas de φ' = 0.

Así que la pregunta abierta no es «¿por qué Spencer descarga la normal?» sino
**«¿por qué Bishop, Ordinary y los Janbu no la descargan?»** — y medir ese
otro extremo, el refuerzo entrando en el equilibrio de dovela de los métodos
de cociente, es lo que hay que hacer antes de decidir nada.

### Suite

```bash
QT_QPA_PLATFORM=offscreen python tests/_runner.py
```

---

© 2026 Samuel Sáez López — UPCT — AGPL-3.0-or-later
