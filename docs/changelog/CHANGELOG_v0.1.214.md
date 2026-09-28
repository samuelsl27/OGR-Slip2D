# OGR Slip2D v0.1.214

Tanda del paquete P4 del banco de verificación: seis fichas, todas de motor. Cinco
venían del encargo (D80, D150, D151, D166 y D170). La sexta, D173, la añadió la
propietaria porque D170 tocaba su misma línea. Un encargo traía la premisa mal
medida (D151), otro proponía una regla que resultó peor que la de la referencia
(D80), y otro pedía elegir un signo que había que investigar (D170).

- **D170 — sismo pseudoestático: kv positivo hacia abajo, el suelo carga
  W·(1 + kv), y la fuerza horizontal es kh·W sobre el peso estático.** Investigado,
  no elegido.
  - El código aplicaba W·(1 − kv), el sentido contrario al que documentan la
    referencia, la interfaz, los docstrings de OGR y su propio exceso de presión
    sísmico.
  - Además acoplaba la horizontal a la vertical, kh·W·(1 − kv), que está mal con
    cualquier signo.
  - Contrastado con la cuña plana pseudoestática en forma cerrada (Kramer 1996).
    Con kh = 0,15 y kv = +0,1 el motor daba 0,711390 y la cuña da 0,691024; ahora
    Janbu, Corps 1, Corps 2 y Lowe-Karafiath la reproducen.
  - Dentro de la ficha:
    - el retroanálisis de Bishop sumaba el momento sísmico con el brazo al revés
      (−7599 kN/m de fuerza en su propio factor con kh = 0,1);
    - la interfaz admitía |kv| = 1, que la API rechaza.
  - **Cero filas del banco**: kv = 0 en los 194 modelos, y con kv = 0 el cálculo es
    bit a bit el de antes.
- **D173 — la marcha de fuerzas entre dovelas aplica las cargas que aplicó el
  método**: el agua embalsada, el sismo del resultado y su sentido de deslizamiento.
  La N de la marcha es ahora la `base_normal_force` del método, a 10⁻⁹. Sin efecto
  en el banco.
- **D166 — la σ′v que lee SHANSEP y la de la adherencia de los soportes llevan el
  agua embalsada.** Bajo una lámina, σ′v = γ′·h (Terzaghi) y reproduce el ejemplo
  trabajado de la documentación de la referencia (1872). Cero filas.
- **D80 — el b1 de Janbu corregido sigue el tipo de suelo de todas las bases**: 0,69
  solo c, 0,31 solo φ, 0,50 c-φ o mezcla. Los modelos sin c y φ se clasifican por la
  forma de su envolvente.
  - Mueve 13 de 59 superficies archivadas.
  - En la comparativa, medido con un A/B en disco, cuatro filas mejoran de estado
    (029, 050 `por_0_0`, 068 y 069), dos mejoran sin cambiar de estado (005 y 011)
    y una empeora sin cambiarlo (050 `por_0_-5`, −0,64 → −3,37 %). Ningún mínimo de
    búsqueda cambia de superficie.
- **D151 — un soporte tangente es, en el círculo, un cortante de base: momento
  |F|·R.** La ficha leía el residuo como un error de dirección, y es el brazo: el
  cruce está sobre la cuerda. Mueve 8 de 116 superficies con soporte, como mucho un
  0,002 %.
- **D150 — la parte normal del refuerzo toma su momento soporte a soporte en el
  camino no circular.** Ninguna superficie crítica archivada tiene dos soportes en
  una dovela: cero filas.

Nacen **D206** (el sismo también actúa sobre la sobrecarga) y **D207** (SHANSEP y
Vertical Stress Ratio frente a la referencia). Las dos se reportan y no se corrigen.

Lo que cambia en el banco de verificación (`_tools/`, `_auditoria/`, fichas) está
fuera de git.

---

## 0. Lo que estaba mal en los encargos

### D151: la identidad que pedía no se alcanza girando la fuerza

La ficha medía que el momento de un soporte `TANGENT_TO_SLIP` sobre un círculo
queda un poco por debajo de |F|·R. Lo atribuía a la DIRECCIÓN: la fuerza sigue la
cuerda de la dovela y no la tangente al arco en el cruce. Pedía girarla y exigir
|F|·R a 10⁻⁹ con cualquier número de dovelas.

Medido, el residuo es del BRAZO, no de la dirección. El cruce del soporte se
calcula sobre la poligonal de cuerdas (`_slip_polyline`), así que el punto está a
menos de R del centro. A 40 dovelas:

| Término | Residuo relativo de M frente a F·R |
|---|---|
| El brazo (cruce sobre la cuerda) | −3,45·10⁻⁵ |
| La dirección (cuerda frente a tangente) | −6,4·10⁻⁷ |

Girar la fuerza deja el 98 % del residuo en su sitio. La identidad que pedía la
ficha tenía otro camino, y lo eligió la propietaria (2026-09-27). En el círculo, la
parte axial de un soporte tangente es un cortante de base. En la ecuación de
momentos de Bishop (1955) el cortante de la base toma el brazo R, porque la base es
el arco. Su dirección sigue siendo la de la cuerda, que es la del cortante que usa
el equilibrio de fuerzas.

### D170: el encargo pedía elegir un signo; había dos defectos

La ficha pedía decidir el sentido de kv «con fuente» y, si no había caso publicado,
dejar la decisión marcada como tal. No hay ningún caso publicado con kv ≠ 0 en
`referencias/`. El sentido se decidió por la mecánica, y la mecánica destapó un
segundo defecto que la ficha no había visto: el acoplamiento kh·W·(1 − kv).

### D80: la regla que la ficha proponía era peor

La ficha proponía elegir b1 por el «material dominante» de la base, por longitud o
por área, y reconocía que ni la referencia ni Janbu (1973) definen «dominante». El
censo de las filas de Janbu corregido midió las tres reglas contra el valor
publicado (por longitud y por área dan lo mismo en todo el banco).

- **El material dominante empeora cinco problemas**, siete superficies: 006
  (+0,04 → −2,24 %), 008 (+0,99 → −1,91 %), 009 (−5,25 → −6,84 %), 065
  (−0,66 → −2,93 %) y las tres del 074 (+1,32 → +4,42 %, y −0,42 → +2,66 % en la
  no circular).
- **Mejora uno**: el 007, de +2,73 % a −0,21 %.
- La regla de la referencia (un solo tipo en toda la superficie da su b1, y varios
  tipos dan 0,50) deja los seis como estaban, porque sus superficies mezclan tipos.

La propietaria eligió la regla de la referencia. Lo que esa regla mueve está en la
sección 4.

### D150 y D151: los prompts no tenían las seis secciones

Los dos salían como «FALTA EL PROMPT LARGO», con 8 y 9 secciones en vez de 6. Se
reescribieron con las seis antes de empezar. El de D151 lleva ya la refutación
medida.

## 1. D170 — el convenio sísmico (motor)

### Lo que se investigó

La fuerza pseudoestática es una fuerza de inercia: masa por aceleración en cada
dirección. Las dos componentes se toman sobre el **peso estático**:

    F_h = k_h·W,   F_v = k_v·W

(Terzaghi 1950; Kramer 1996, §10.6.1; EN 1998-5, §4.1.3.3: F_H = 0,5·α·S·W y
F_V = ±0,5·F_H, o ±0,33·F_H según a_vg/a_g, las dos sobre el mismo W).

- **El sentido de kv.** OGR lo documenta positivo hacia abajo en cuatro sitios, y la
  documentación de la referencia dice lo mismo. Con ese convenio la carga vertical
  es W + k_v·W = W·(1 + k_v). El código hacía W·(1 − k_v), que es el convenio
  contrario. Y `seismic_delta_sigma_v` suma k_v·σ_v, así que el mismo kv empujaba
  hacia arriba en el peso y hacia abajo en el exceso de presión.
- **La horizontal no puede depender de kv.** Son las dos componentes ortogonales de
  la segunda ley sobre la misma masa. Mononobe-Okabe, y EN 1998-5 en su anejo E,
  escriben tan θ = k_h/(1 ± k_v), que solo sale con F_h = k_h·W. El
  k_h·W·(1 − k_v) de OGR no tiene base mecánica con ningún signo.

### El contraste: una forma cerrada y dos identidades

- **La cuña plana pseudoestática** (Kramer 1996, §10.6.1), escrita con kv positivo
  hacia abajo:

      F = [c·L + (W(1 + k_v)·cos β − k_h·W·sin β)·tan φ] / [W(1 + k_v)·sin β + k_h·W·cos β]

  Se usó el plano a 40° del talud de `test_janbu_wedge_v1142`, con c = 5 kPa y
  φ = 30°:

  | | Motor antes | Cuña, kv abajo | Cuña, kv arriba |
  |---|---|---|---|
  | k_h = 0, k_v = +0,1 | 0,925163 | **0,882053** | — |
  | k_h = 0,15, k_v = +0,1 | 0,711390 | **0,691024** | 0,691573 |

  Antes, el motor coincidía al dígito con «W(1 − k_v) y H = k_h·W(1 − k_v)». Ahora
  Janbu, Corps 1, Corps 2 y Lowe-Karafiath reproducen la cuña con k_v hacia abajo:
  Janbu a 10⁻¹¹ y la familia de inclinación prescrita a 10⁻⁸. Con k_v = 0 ya la
  reproducían antes (0,901452, y 0,691275 con k_h = 0,15).
- **Dos identidades en el círculo con φ = 0**, donde F = Σc·ℓ / ΣW·sin α:
  - F(0, k_v)·(1 + k_v) = F(0, 0), a 10⁻¹² en Bishop y el Ordinario;
  - 1/F(k_h, k_v) − 1/F(k_h, 0) = k_v/F(0, 0). Esta es la que discrimina el
    acoplamiento: con k_h·W·(1 − k_v) no se cumple.

  El número que la ficha citaba se lee ahora al revés. En su talud, F(0, 0) =
  0,6869 y k_v = +0,2 daba 0,8586 (el sismo hacia abajo estabilizaba). Ahora da
  0,5724 = 0,6869/1,2.

### El arreglo

- **Un solo sitio del convenio**: `external_forces.slice_forces`, con
  `w_soil = W·(1 + k_v)` y `h_seismic = k_h·W`. Hay además un ayudante público,
  `seismic_soil_weight(weight, kv)`, para quien no tiene una `Slice`.
- **Las copias a mano pasan por él**:
  - el signo de deslizamiento de Bishop, Spencer, GLE, el Ordinario y la familia de
    inclinación prescrita;
  - la recursión de esa familia, donde vivía la última copia del acoplamiento
    (`kh*s.weight*(1-kv)`);
  - el retroanálisis;
  - la marcha de fuerzas entre dovelas (D173).
- **Los docstrings que atribuían «W → W·(1 − kv)» a la referencia** se corrigen:
  Bishop, Janbu, el Ordinario, los chequeos y el posproceso. El argumento de
  `checks._denominator_sign` pasa a ser «(1 + k_v) ≥ 0 para k_v ≥ −1». El caso
  degenerado (suelo sin peso) es ahora k_v = −1 y no +1.
- El comentario del Ordinario que llamaba al acoplamiento «lo que dice la
  formulación pseudoestática» era falso y se reescribe. La «aproximación
  Σ k_h·W·tan α» del docstring de Janbu tampoco la hacía el código, que suma
  `h_seismic`: lo exacto en la cuña.
- La API (`seismic_set`), el servidor MCP y `docs/mcp/herramientas.md` dicen ya el
  sentido: «kv positive DOWNWARD: the soil carries W·(1 + kv)».

### Dentro de la ficha: el retroanálisis (A1) y el rango de la interfaz (A7)

- **A1 — el brazo del momento sísmico del retroanálisis de Bishop estaba al revés.**
  `back_analysis._sums_at_fixed_fos` usaba (y_g − y_c)/R, y el solver usa
  (y_c − y_g)/R. La identidad de v0.1.202 dice que, en el factor propio del método,
  la fuerza requerida es cero. Leída sin el recorte a 0 de `required_force`, con
  k_h = 0,1:
  - el sismo **bajaba** la suma motora de 4532 a 3093;
  - la fuerza en el factor propio salía −7599 kN/m.

  Ahora la suma motora sube, y la fuerza queda por debajo de 5·10⁻³ de ella en
  Bishop y de 10⁻⁶ en Janbu. Se corrigió dentro de D170 por decisión de la
  propietaria. Lo demás que el retroanálisis reconstruye a mano va a D204.
- **A7 — la interfaz admitía |k| = 1 exacto**, y la API lo rechazaba. Con kv hacia
  abajo, k_v = −1 es el suelo sin peso. La regla se mueve a
  `ogr_core/project/rules.py` (`seismic_coefficient_refusal`), la API la pregunta, y
  el diálogo para sus casillas un paso por dentro (±0,999). Se quita del diálogo una
  comprobación cuyo `return` no se alcanzaba nunca y que no decía nada.

### Lo que mueve

- **El banco: nada, por identidad.** Ninguno de los 194 modelos tiene k_v ≠ 0 (8
  tienen el sismo activo, todos con k_v = 0). Con k_v = 0, (1 + 0) y (1 − 0) son el
  mismo 1,0 exacto, y k_h·W·1,0 es k_h·W. El test lo fija bit a bit.
- **Un archivo con k_v ≠ 0 anterior a esta versión cambia de factor.** No hay
  migración, a propósito: el archivo guarda el número que el usuario escribió en
  una casilla que prometía «positivo hacia abajo», y ahora se aplica ese sentido.

### Tests

- **`test_seismic_convention_v1214.py`** (14 casos):
  - la cuña cerrada en los cuatro métodos de fuerzas;
  - las identidades del círculo;
  - el mismo sentido en el peso y en el exceso de presión;
  - k_v = 0 bit a bit;
  - el retroanálisis en su factor propio con sismo.
- **`test_seismic_range_v1214.py`** (5 casos): la regla, el mensaje compartido y las
  casillas del diálogo.
- **`test_slide_sign_by_method_v1189.py`** codificaba (1 − k_v). Pasa a (1 + k_v), y
  su caso degenerado de k_v = +1 a k_v = −1
  (`test_only_kv_exactly_minus_one_degenerates`), con la razón escrita.

## 2. D173 — la marcha de fuerzas entre dovelas (motor e interfaz)

### Lo que estaba mal

`postprocess._march` rehacía la carga a mano: `s.weight*(1-kv)`, sin el agua
embalsada (ni su peso ni su empuje horizontal) y con el sismo que le pasara el
llamante. Las tres llamadas de la ventana de interpretación no se ponían de
acuerdo:
- dos pasaban el k_h y k_v del proyecto, que pueden no ser los del cálculo;
- el panel de dovelas (`_SliceDataDock._inter_state`) no pasaba ningún sismo.

### El arreglo

- **La marcha toma la carga de `slice_forces`**:
  - la vertical es `w_total`;
  - la horizontal es el sismo en su sentido más el empuje del agua.

  En la línea de empuje, el suelo sigue en su centroide. El peso del agua va en la
  vertical del centro de la dovela, y su empuje horizontal a la cota
  `m_water_ref0/h_water`.
- **Los coeficientes vienen del resultado.** Los nueve métodos publican ya
  `details["kh"]`, junto al `"kv"` que publicaban. `compute_interslice_state(result)`
  los lee de ahí, y las tres llamadas de la interfaz ya no pasan nada. El desembalse
  multietapa añade `"kh"` a las claves que pasan de la etapa al resultado.
- **A4 — el sentido de deslizamiento es el del método.** La marcha lo sacaba de
  Σ W·sin α, y Janbu puede deslizar al revés que esa suma (el testigo de D112). Ahora
  lee `details["slide_sign"]`. Con X = 0, la marcha resuelve el equilibrio vertical
  de cada dovela con la F del método, así que su N **es** la `base_normal_force` que
  publican Bishop y Janbu. Es la identidad que lo comprueba, a 10⁻⁹.

  Se barrieron miles de círculos sobre las geometrías del banco y ninguno da
  sentidos distintos entre Janbu y Bishop. Solo el testigo sintético de tres
  dovelas lo hace.

### Test

**`test_interslice_ponded_v1214.py`** (10 casos), sobre la presa con embalse de
`test_m_alpha_ponded_v1188`:
- el equilibrio vertical y el horizontal de cada dovela con la carga total;
- quitar el agua mueve la N;
- la N de la marcha es la del método;
- los coeficientes salen del resultado, también en el panel de dovelas;
- el testigo de D112.

Contra 0.1.213, en la dovela 0 del embalse la marcha daba N = 84,4 donde Bishop
publica 1224,9.

## 3. D166 — la σ′v de consolidación con el agua embalsada (motor)

### Lo que estaba mal

`BishopSimplified._local_c_phi` construye el contexto de los modelos que lo piden
(SHANSEP). Calculaba σ′v = W/b − u con el peso del **suelo**. Bajo un embalse, u
sube con la columna de agua y el peso que la compensa (`water_weight`) no entraba,
así que σ′v se saturaba a cero con cientos de kPa de agua encima. La ficha lo
anticipaba: el mismo linaje que D113, pero dentro de la linealización y no en un
chequeo.

`ogr_core/support/bond.py::sigma_v_effective_at`, el perfil de adherencia de los
soportes con ley dependiente de la tensión, tenía el mismo defecto. Entró en la
ficha por ser de la misma clase.

### La referencia externa

- **La identidad de Terzaghi**: bajo una lámina, σ′v = γ′·z, y no depende del
  calado.
- **El ejemplo trabajado de exceso de presión de la documentación de la
  referencia**, que suma la columna de agua a la tensión total: 30 ft de suelo de
  124,8 pcf bajo 40 ft de agua dan

      σ′v = (30·124,8 + 40·62,4) − 70·62,4 = 1872 psf

### El arreglo

- `_local_c_phi`: σ′v = (W + W_agua)/b − u, **sin k_v**, porque es una tensión de
  consolidación y no una carga del cálculo. Lee con `getattr`, porque `_PointAsSlice`
  de `bond.py` no tiene el campo.
- `sigma_v_effective_at`: suma γ_w·`ponded_depth_at(project, x, ground_y)`, la misma
  función con la que el slicer carga la lámina.
- El docstring de `SliceContext.sigma_v_eff` dice ya lo que contiene: el peso de las
  tierras más el agua embalsada, menos u, sin k_v.

### Lo que mueve

**Nada en el banco**, medido con `_tools/censo_d166_sigma_v.py`:
- ningún material SHANSEP en los 194 modelos;
- el único con soportes de adherencia y lámina es el 092 (dos modelos, 7
  superficies): ninguna de sus láminas queda bajo el agua, y 0 superficies se
  mueven.

El control sintético (una lámina bajo el agua) sí ve el caso.

### Test

**`test_sigma_v_ponded_v1214.py`** (7 casos):
- SHANSEP lee γ′·h dovela a dovela bajo dos embalses distintos, y lee lo mismo en
  los dos;
- en seco, bit a bit igual;
- el perfil de adherencia bajo una lámina da γ′·h (20,38 kPa a 2 m, donde 0.1.213
  daba 0);
- el ejemplo publicado da 1872.

## 4. D80 — el b1 de Janbu corregido por tipo de suelo (motor)

### Lo que estaba mal

`_janbu_correction_factor` documentaba el factor de Janbu (1973),

    f0 = 1 + b1·[(d/L) − 1,4·(d/L)²]

con b1 = 0,69 en suelo solo cohesivo, 0,31 en suelo sin cohesión y 0,50 en c-φ.
Pero usaba 0,50 **siempre**. Es la regla 7: una elección documentada que no se
hace.

### El arreglo

- **`janbu.janbu_correction(slices) → (f0, b1)`** aplica la regla de la referencia
  sobre el material de **todas** las bases:
  - si todas son del mismo tipo, el b1 de ese tipo;
  - si hay más de un tipo, 0,50.

  Documentado con Janbu (1973), en Hirschfeld y Poulos (eds.), *Embankment-Dam
  Engineering*, Wiley, 47–86, y Abramson et al. (2002), §5.5. Funciona sin proyecto,
  así que el retroanálisis usa la misma regla.
- **`base_soil_type(material)`** clasifica cada base:
  - Mohr-Coulomb por su c y su φ;
  - Undrained, SHANSEP y las no drenadas con la profundidad, «solo c»;
  - sin resistencia y resistencia infinita no tienen tipo y no participan.
- **Los demás modelos, por la forma de su envolvente** (decisión de la
  propietaria). Se prueba τ a σ′ = 0, 10 y 200 kPa:
  - todo cero: sin tipo;
  - plana entre 10 y 200: «solo c»;
  - cero en el origen: «solo φ»;
  - lo demás: c-φ.

  Con los valores por defecto de cada modelo registrado quedan así:

  | Tipo | Modelos |
  |---|---|
  | solo φ | Barton-Bandis, Hoek-Brown (las dos), hiperbólico, Vertical Stress Ratio |
  | c-φ | drenado-no drenado, curva de potencia, los anisótropos |
  | solo c | no drenados, SHANSEP |
  | sin tipo | el anisótropo generalizado, resistencia infinita, sin resistencia |

  Una curva de potencia que pasa por el origen es «solo φ». Con d = 5 es c-φ.
- **El resultado publica `janbu_b1` y `janbu_f0`** en `details`.
- **Interruptor `B1_BY_SOIL_TYPE`.**
- El comentario «pick from the dominant base material» se retira: esa regla no es
  la elegida.

### Lo que mueve (medido con `_tools/censo_b1_janbu_d80.py`)

Es un A/B con el interruptor en el mismo proceso, sobre las superficies archivadas
y las publicadas (`_auditoria/B1_JANBU_0.1.214.md`).

- **13 de 59 superficies se mueven.** En las 59, el b1 del motor es el de la regla.
- **Filas con valor publicado:**

  | Fila | Antes | Ahora | |
  |---|---|---|---|
  | 029 (Duncan 2000, 1,168) | −1,49 % | **−0,53 %** | mejora |
  | 068 sobre el círculo publicado (1,385) | −2,60 % | **+0,29 %** | mejora |
  | 050 `por_0_0` (1,577) | +1,99 % | **+0,56 %** | mejora |
  | 069 (1,830) | +5,52 % | **+2,85 %** | mejora |
  | 005 aguas arriba (1,949) | +0,27 % | **+0,15 %** | mejora |
  | 050 `por_0_-5` (1,417) | −0,64 % | **−3,37 %** | empeora |

  El 050 es un talud con geotextil y c′ = 0. La ficha ya lo había medido: **ningún
  b1 cierra sus dos superficies a la vez**.
- **Dos mecanismos de Prandtl con solución cerrada** (FS exacto 1,0). No son filas
  de la comparativa, porque el manual solo publica Spencer:
  - el 026 pasa de −2,83 % a **+0,20 %**;
  - el 025 pasa de +7,26 % a **+9,19 %**.

  El f0 de Janbu es una calibración empírica sobre superficies de forma corriente,
  así que ninguno de los dos valida b1.
- **Sin valor publicado**: el polígono de Perry del 040, cuya curva de potencia pasa
  por el origen, −2,76 %; 047 sin bulones, +1,72 %; y las búsquedas del 011
  (−0,84 %) y del 068 (+2,01 %).

### Lo que mueve en la comparativa (A/B en disco)

El censo mide superficies fijas. Que un mínimo de búsqueda salte a otra superficie
solo lo ve una búsqueda, así que se re-corrieron los problemas de la lista
`a_re_correr` del censo: los que tienen alguna superficie movida o algún material de
un solo tipo. Se añadieron los de soporte tangente de D151, 19 problemas y 26
archivos en total.

- **Lado A**: el árbol de 0.1.214 con los tres interruptores de la tanda apagados
  **en los archivos del motor**.
- **Lado B**: el mismo árbol, encendidos.

En disco y no con un parche en memoria, porque la búsqueda reparte los círculos entre
procesos hijos que no heredan un parche del padre. Antes de cada lado, una sonda (un
intérprete nuevo, lanzado desde el banco) comprobaba que veía los interruptores como
tocaba. Tras el lado A el motor se restauró y se comprobó por sha256. Tardó 3935 s
y 3831 s, sin ningún fallo.

Hacía falta porque `Evaluaciones/0.1.213` tiene esos 26 archivos byte a byte iguales
al vivo, pero escritos por 0.1.173–0.1.213. Compararlos con 0.1.214 le atribuía a
esta tanda veinte versiones de deriva. Por ejemplo, el optimizado de Spencer del 074
no circular pasa de 1,151381 (0.1.185) a 1,18705 **en los dos lados**: no es de esta
tanda, aunque el balance contra 0.1.213 lo cuenta como una mejora más (REVISAR → OK).

**Resultado: 44 valores distintos en 26 archivos**, todos en las superficies que
predijo el censo (las 13 de D80 y las 8 de D151). **Ningún mínimo de búsqueda cambia
de superficie.** 003, 004, 007, 009, 013 y las dos mitades del 074 salen idénticos,
aunque tengan materiales de un solo tipo. En la comparativa:

| Fila | Antes | Ahora | |
|---|---|---|---|
| 029 Janbu corr. | REVISAR, −1,49 % | **OK, −0,53 %** | mejora de estado |
| 050 `por_0_0` | REVISAR, +1,99 % | **OK, +0,56 %** | mejora de estado |
| 068 Janbu corr., búsqueda | REVISAR, −15,66 % | **OK, −13,97 %** | mejora de estado |
| 069 Janbu corr. | DISCREPANCIA, +5,52 % | **REVISAR, +2,85 %** | mejora de estado |
| 005 Janbu corr. | +0,27 % | +0,15 % | mejora |
| 011 Janbu corr. | +39,05 % | +37,89 % | mejora (sigue NO CONCLUYENTE) |
| 050 `por_0_-5` | −0,64 % | −3,37 % | empeora (sigue NO CONCLUYENTE) |

**Una cosa que no esperaba, medida antes de darla por buena (regla 6).** En dos
búsquedas de Janbu corregido cambia el recuento de superficies válidas: 068 pasa de
1149 a 1145 y 047 sin bulones de 1055 a 1053. Un b1 solo multiplica F.
- La búsqueda de rejilla cuenta como inválido todo F fuera de [0,2; 100].
- Repetidas en serie en el mismo proceso (apagado, encendido, apagado), las
  superficies que salen de la población son las que tenían F entre 97,9 y 99,9 con
  b1 = 0,50, y que b1 = 0,69 lleva por encima de 100.
- No mueve ningún mínimo, y no es un defecto: es esa regla leyendo un F más alto.

Todo archivado en `_auditoria/AB_en_disco_0.1.214/`.

### Test

**`test_janbu_b1_v1214.py`** (10 casos):
- seis suelos sobre un talud 2:1, con la identidad F_corr/F_simp = f0(b1) a 10⁻¹²;
- el b1 y el f0 publicados;
- la regla 7 con el interruptor;
- el retroanálisis;
- el tipo de cada modelo, por clase y por forma de la envolvente, y una base sin
  tipo que no participa.

## 5. D151 — la parte tangente de un soporte es un cortante de base (motor)

### El arreglo

- `SupportEffect` lleva, en dos campos nuevos al final con valor por defecto 0, las
  componentes de la parte dirigida por la tangente: la axial de un
  `TANGENT_TO_SLIP`, antes de sumar el cortante V del soporte.
- En `resolve_support_terms`, camino circular, esa parte toma momento
  `slide_sign·(t_h·cos a + t_v·sin a)`: su proyección sobre la cuerda, ±|F|, con
  brazo R. El resto, que es el cortante V de SoilNail, GroutedTieback y
  HelicalAnchor, toma el producto vectorial en el cruce, como desde D144.
- Con la parte tangente a cero, la expresión es la de D144 bit a bit. PARALLEL,
  HORIZONTAL y USER_DEFINED no cambian.
- **Interruptor `TANGENT_AS_BASE_SHEAR`.**
- **Los dos detalles menores de la ficha:**
  - la pendiente se lee de la dovela ya encontrada (`_chord_slope`);
  - `_slip_tangent_at_x` usa la misma holgura por la izquierda que por la derecha y
    ya no cae a `or 0.0`.
- `docs/PENDIENTES.md`, sección 12: CERRADO.

### Lo que mueve (`_tools/censo_d150_d151.py`, A/B con el interruptor)

- **8 de 116 superficies con soporte**, todas de modelos con `tangent_to_slip`, y
  como mucho un **0,0020 %**:
  - la publicada del 054 con Bishop;
  - cuatro del 060;
  - D1D3, D1D4 y D1D6 del 106.
- 0 superficies se mueven en modelos sin soporte tangente.
- El 049 tiene soportes tangentes, pero sus cuatro filas son de Janbu, que no toma
  momentos.
- El 111 (ancla helicoidal tangente) mide su factor sobre una poligonal, que no es
  el camino circular.
- El control ve el caso: 19,99929706 → 20,0 a 40 dovelas.

En la comparativa (el mismo A/B en disco de la sección 4):
- el 054 con Bishop sobre su círculo publicado pasa de +0,19 % a +0,20 %;
- los mínimos de búsqueda del 060 y del 106 se mueven en la quinta o sexta cifra
  (1,583093 → 1,583108 en el 060), por debajo de lo que imprime la tabla;
- la búsqueda de Spencer del 054 gana una superficie válida, con el mismo mínimo;
- el 054 sin pilote, que no tiene soporte, sale bit a bit igual.

### Tests

- **`test_support_tangent_v1214.py`** (6 casos):
  - M = |F|·R a 10⁻⁹ con 20, 50 y 200 dovelas, activo y pasivo;
  - n_press = 0;
  - el cortante V por producto vectorial;
  - las otras orientaciones bit a bit;
  - el interruptor.
- **`test_support_active_passive_v1115.py`**: `_moment_over_r` vuelve a esperar
  `CAPACITY` exacto, con la banda de 10⁻⁹ intacta. El docstring ya no dice que el
  residuo es de la dirección.

## 6. D150 — la parte normal del refuerzo, soporte a soporte (motor)

### Lo que estaba mal

En el camino no circular, cuando una dovela recibe dos o más soportes, la parte
normal de todos ellos tomaba momento en el punto de aplicación **medio** (x_app,
y_app, ponderado por |F|). Por Varignon, el momento de una suma de fuerzas es la
suma de los momentos si cada una se toma en **su** punto, no en uno medio. El
docstring de `moment_terms` lo tenía escrito como «Reported, not fixed».

### El arreglo

- `SupportTerms.normal_couple` (campo nuevo al final, por dovela) lleva el par de la
  parte normal de cada efecto respecto de (x_app, y_app). Solo es distinto de cero en
  dovelas con dos o más efectos.
- `moment_terms` lo suma.
- Con un soporte por dovela, bit a bit igual.
- **Interruptor `NORMAL_PART_PER_EFFECT`.**

### Lo que mueve

**Nada** en lo medido: ninguna crítica archivada del banco tiene dos soportes en una
dovela (0 de 116 superficies, mismo censo que D151). El control sintético sí ve el
caso.

Solo entra en el camino no circular: las ramas generales de Spencer/GLE y de Bishop
son las que llaman a `moment_terms` con el soporte, y en el círculo el radio se
simplifica. El A/B en disco no lo ve, porque sus búsquedas con soporte son
circulares. **Queda sin medir** si una búsqueda no circular con soporte salta a una
superficie con dos soportes en una dovela: las del 085 (activo y pasivo), la del 086
y el barrido de planos del 047 no se han vuelto a correr.

### Test

**`test_support_normal_arm_v1214.py`** (5 casos): dos anclajes de orientación
distinta en una dovela de la poligonal de `test_support_noncircular_v1140`.
- El momento es la suma por efecto a 10⁻¹² (−4,8327).
- El punto medio da −20,4626.
- Cada caso comprueba primero que el fixture pone de verdad los dos en una dovela, y
  que hay al menos cinco mallados donde lo hace. Los anclajes del fixture de v1178
  no compartían nunca dovela, y un caso sobre una lista vacía habría pasado en
  vacío.

## 7. Lo que se reporta y NO se corrige (regla 6)

- **D206 — k_h y k_v multiplican también la sobrecarga que el slicer pliega en
  `s.weight`.** La documentación de la referencia define la fuerza sísmica sobre el
  peso del suelo de la dovela. El docstring de
  `excess_pore_pressure.seismic_delta_sigma_v` afirma que la sobrecarga no es masa
  acelerada «con el mismo convenio que `slice_forces`», que hace lo contrario.
  - Ninguno de los 8 modelos del banco con sismo lleva cargas.
  - Decidirlo pide saber qué representa la carga: un relleno tiene masa, el tráfico
    no.
- **D207 — SHANSEP y Vertical Stress Ratio no son las formulaciones de la
  referencia.**
  - SHANSEP: la documentación suma la resistencia mínima (A + σ′v·S·OCR^m), y OGR
    toma `max`.
  - Con σ′v ≤ 0, SHANSEP cae en silencio a su(σ′n). Y su σ′v resta la u con el
    exceso B̄.
  - Vertical Stress Ratio no pide contexto y usa σ′n como si fuera σ′v. Por eso D80
    lo clasifica «solo φ».
  - Ningún modelo del banco lleva ninguno de los dos.
- **Notas añadidas a fichas abiertas**, por ser de la misma clase:
  - **D195**: el `_c_phi` de Snowden ignora el buzamiento local;
  - **D143**: Spencer y GLE sobre un plano con k_h ≠ 0 caen a la reserva de λ y se
    separan un +1,8 % de la cuña cerrada, que Janbu y la familia reproducen al
    dígito;
  - **D204**: el retroanálisis tampoco lleva el agua embalsada ni sus empujes;
  - **D171**: con la `shear_strength` actual, Hoek-Brown tiene τ(0) = 0 y D80 lo
    clasifica «solo φ»; con la envolvente de Mohr exacta del criterio sería c-φ.
- **Sin medir (A6)**: los perfiles de adherencia se guardan en el proyecto y se
  reusan mientras dura el análisis (v0.1.116). `level_project`, que construye cada
  etapa del desembalse, es una copia superficial que hereda esa caché. Si el
  proyecto original ya la tenía llena, las dos etapas leerían el perfil del mismo
  nivel de agua. Desde D166 la lámina entra en ese perfil. No hay en el banco ningún
  modelo con desembalse y soportes de adherencia, y no se ha medido.

## 8. Verificación

- **Suite entera: 4778 de 4778**, en 33 min 35 s, sin filtro. La corrida anterior,
  sin este changelog, dio 4777 de 4778: el único fallo era su ausencia.
- **Tests nuevos: siete archivos, 57 casos.** Contra 0.1.213 fallan 37: 30 por
  comportamiento y 7 porque las funciones nuevas no existían. Se midieron
  copiándolos a un árbol de e02b605 (0.1.213) extraído con `git archive`; por
  carpeta:

  | Carpeta | Fallan en 0.1.213 | Por comportamiento | Por símbolo nuevo |
  |---|---|---|---|
  | D80 | 6 de 10 | 3 | 3 (`janbu_correction`, `base_soil_type`) |
  | D150/D151 | 6 de 35 | 6 | — |
  | D166 | 4 de 7 | 4 | — |
  | D170/D173 | 23 de 29 | 19 | 4 (`seismic_coefficient_refusal`) |

  Los 35 de D150/D151 incluyen `test_support_active_passive_v1115` (2 de 15 fallan)
  y `test_support_tangential_v1139` (0 de 9) como contexto. Los casos nuevos que
  pasan en 0.1.213 son controles (bit a bit, interruptor apagado, que el fixture ve
  el caso) o invariantes que ya se cumplían.
- **Tests existentes que cambian:**
  - `test_slide_sign_by_method_v1189`, `test_drawdown_passthrough_v1210` y
    `test_support_active_passive_v1115`, con la razón escrita;
  - `test_sigma_seismic_v1191`, `test_support_tangential_v1139` y
    `test_support_arm_v1178`, solo en comentarios;
  - ningún `test_slide_validation_*`.
- **Banco:**
  - los censos de D80 (13 de 59 superficies), D150/D151 (0 y 8 de 116, como mucho
    un 0,002 %) y D166 (ningún SHANSEP; 0 de 7 superficies del 092);
  - kv = 0 en los 194 modelos;
  - el A/B en disco de 26 archivos: 44 valores distintos, las 7 filas de la
    sección 4 y ningún mínimo movido de superficie;
  - `generar_comparativa.py`, y los balances contra el lado A y contra
    `Evaluaciones/0.1.213` (`_auditoria/BALANCE_0.1.214.md`).
- **Cierres del banco** `d80()`, `d150()`, `d151()`, `d166()`, `d170()` y `d173()`:
  - dan CUBIERTO POR TEST con este árbol;
  - dan NO SE SOSTIENE contra 0.1.213 por comportamiento, los seis. Leyendo además
    el código del árbol viejo, cinco caen también por él. En D151 esa comprobación
    lee el test de v1115, y en ese árbol el test ya era el nuevo;
  - la corrida entera en seco de los 172 cierres no cambia ningún veredicto
    archivado.
- **Ciclo de cierre**: seis fichas retiradas con su historia en
  `Evaluaciones/0.1.214`, `PAQUETES` podado, prompts regenerados (45: las 7 FALTA
  son anteriores a esta tanda) y `auditoria_invariantes.py` a 0 ERROR en el 02 y en
  la raíz.

**Lo que queda sin probar:**
- ningún caso publicado con kv ≠ 0: D170 se contrasta con una forma cerrada y dos
  identidades;
- las búsquedas no circulares con soporte, para D150 (sección 6);
- la caché de adherencia entre etapas del desembalse (A6);
- el diálogo sísmico, probado sin pantalla y no a mano.
