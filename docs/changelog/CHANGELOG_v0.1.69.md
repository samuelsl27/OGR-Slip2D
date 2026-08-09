# OGR Slip2D v0.1.69 — un solo convenio de desembalse, y dos referencias que lo prueban

Las dos cosas que v0.1.68 dejó anotadas sin resolver. La primera resultó
ser mucho más grande que su enunciado; la segunda encontró un error que
nada de lo que había podía detectar.

> **AVISO PARA PROYECTOS GUARDADOS.** Un `.ogr` que use el modelo B̄ con
> el convenio anterior —línea de desembalse por encima del nivel
> freático— se **migra al abrirlo, sin preguntar**: se intercambian los
> dos tipos de contorno. No se mueve ni un vértice, pero **el factor de
> seguridad cambia**, y baja. El anterior era el del embalse lleno.

---

## 1. El modelo B̄ devolvía el FS de antes del desembalse

Lo anotado en v0.1.68 era «el convenio de la línea de desembalse está
invertido entre las dos implementaciones». Lo que había eran **cuatro
defectos apilados** que, en B̄ = 1, se cancelaban entre sí.

Medido sobre la geometría de Pilarcitos con el convenio que el código
exigía (NF = 37 abajo, línea de desembalse = 72 arriba), Bishop
simplificado, rejilla de 729 círculos:

| Modo | FS crítico |
|---|---|
| Solo NF = 72 (embalse lleno, sin desembalse) | **2.5044** |
| Solo NF = 37 (drenado al nivel bajo) | 2.3679 |
| B̄ = 1.0, desembalse rápido activo | **2.5044** ← el mismo número |
| B̄ = 0.5 | 4.9324 |
| Material drenante (B̄ = 0) | 6.3407 |

Con B̄ < 1 el «desembalse» salía **más seguro** que el embalse lleno, que
es la dirección física contraria. Los cuatro defectos:

1. **Convenio invertido.** El código exigía `y_desembalse > y_freático`.
   El Tutorial 13 de la documentación de referencia —el del propio método
   B̄, no el de los multietapa— dice lo contrario y sin ambigüedad: *«An
   initial water table is defined […] For a partial drawdown scenario, a
   drawdown water table is also defined»*. El NF es el nivel **inicial**
   también en B̄.

2. **Δσ_v mal medido.** La referencia es `Δu = B̄·Δσ_v` con Δσ_v = peso
   del agua embalsada retirada, **acotado por la superficie del terreno**.
   El código usaba la diferencia de cotas de las dos líneas, sin mirar el
   terreno. Para un punto bajo el talud aguas arriba —donde corre la
   superficie crítica— con B̄ = 1 devolvía `γw·(y_alto − y_punto)`: la
   presión intersticial anterior al desembalse, exacta.

3. **La carga de agua embalsada era la del embalse lleno.**
   `PONDING_BOUNDARY_TYPES` incluía `DRAWDOWN` y «gana la más alta», que
   bajo aquel convenio era la línea de desembalse. El talud conservaba
   íntegro el peso estabilizador del embalse que acababa de vaciarse.

4. **B̄ no movía el número por encima del NF.** El `return 0.0` de
   succión (agua bajo el punto → cero) se ejecutaba *antes* del bloque
   B̄. En el primer círculo probado, B̄ = 1.0 y B̄ = 0.5 daban FS idéntico
   hasta el último dígito. Regla 7.

Además B̄ estaba **fuera de todas las guardas**: `wrap_for_drawdown` y
`check_drawdown_settings` devolvían sin hacer nada cuando el método era
`b_bar`. Y no tenía **ninguna validación externa**: los únicos tests eran
de su propia aritmética, que es exactamente la instantánea que la regla 1
prohíbe.

### El camino equivocado

Lo primero que se intentó fue arreglarlo donde estaba, dentro de
`pore_pressure_at`. No puede funcionar: esa función no conoce la
superficie del terreno (defecto 2) ni la carga de agua embalsada (defecto
3), y el cortocircuito de succión se ejecuta antes que ella (defecto 4).
Los tres son consecuencia del sitio, no del código.

B̄ pasa ahora por el mismo mecanismo que los tres multietapa —
`BBarDrawdownMethod`, junto a `MultiStageDrawdownMethod` — que rebana en
el nivel final y sobrescribe la presión intersticial de las dovelas no
drenadas:

```
Δσ_v = −γw·(h_embalsada,inicial − h_embalsada,final)   acotadas por el terreno
u    = max(0, u_inicial + B̄·Δσ_v)
```

Los defectos 3 y 4 desaparecen por construcción: la copia del nivel final
no contiene la línea alta, y el exceso ya no vive detrás del
cortocircuito.

### Dos decisiones que no son accidentes

- **La compuerta es `undrained_behaviour` sola, no `b_bar > 0`.** Con el
  coeficiente de segunda compuerta el modelo sería discontinuo en cero:
  B̄ = 0.001 conserva casi toda la presión inicial y B̄ = 0 saltaría al
  nivel final. La casilla dice si el suelo puede drenar; B̄, cuánto sigue
  su agua a la descarga.
- **El resultado se acota en cero.** Una presión negativa aquí sería
  succión creada por el desembalse, y apoyarse en ella es justo lo que la
  envolvente compuesta del Corps existe para evitar.

### Por qué el defecto sobrevivió sesenta versiones

Una masa deslizante **enteramente sumergida bajo los dos niveles** tiene
el mismo factor de seguridad con el embalse lleno, con el embalse bajado y
después del desembalse: con un campo hidrostático, la carga de agua y la
subpresión se cancelan y solo queda el peso sumergido. Comprobado a seis
cifras.

Y el círculo crítico de Pilarcitos con el embalse lleno —(20, 180) r =
160— cae **justo en ese régimen**: su terreno no pasa de la cota 35.23,
por debajo de los dos niveles. Ahí la respuesta rota y la correcta
coinciden **exactamente**, que es lo que hacía que el modelo pareciera
razonable a quien lo mirase por encima.

Hace falta una masa que **emerja** para distinguirlas. Sobre esa misma
presa, buscando el crítico de verdad:

| | FS crítico | círculo |
|---|---|---|
| Embalse lleno | 2.5044 | (20, 180) r = 160 |
| Tras el desembalse, B̄ = 1 | **1.1730** | (80, 160) r = 120 |

Una caída del **53 %**, y el círculo crítico se muda: deja de ser el del
pie sumergido. Eso es lo que el modelo anterior no reportaba.

### El sentido de B̄, que es contraintuitivo

`Δσ_v < 0`, así que **más B̄ significa menos presión intersticial y más
factor de seguridad**. B̄ = 1 —un suelo saturado cuya presión sigue por
completo la descarga— es el menos conservador de los dos, al revés de lo
que sugiere la intuición traída de los problemas de carga. Hay un test
que lo fija con esa explicación, porque el signo se equivocó una vez al
escribirlo.

---

## 2. La validación externa que faltaba: Morgenstern (1963)

Problemas #100 y #101 de la documentación de verificación, cuyas figuras
llevan **las coordenadas rotuladas vértice a vértice** — no hay
digitalización a ojo en ningún sitio.

Talud homogéneo 3:1 de 100 ft, γ = 124.8 pcf, c' = 312 psf, φ' = 30°,
B̄ = 1, embalse inicialmente a ras de coronación:

| Caso | Publicado | OGR Slip2D | Error |
|---|---|---|---|
| Desembalse completo, 100 → 0 ft | 1.20 | 1.2027 | +0.2 % |
| Desembalse parcial, 100 → 50 ft | 1.41 | 1.4251 | +1.1 % |

Rejilla única de 2310 círculos para los dos casos, unos 2 s cada uno. Una
rejilla de 40 ft se probó primero y quedó un 5.3 % alta en el caso
completo: era la resolución hablando, no el modelo.

### La identidad que ancla el modelo sin depender de nadie

Con B̄ = 1 y desembalse **completo** el modelo tiene forma cerrada. En un
punto P cuya superficie del terreno está en y_g:

```
u_inicial = γw·(100 − y_P)
Δσ_v      = −γw·(100 − y_g)        la columna embalsada retirada
u_final   = γw·(y_g − y_P)
```

que es γw por la profundidad vertical bajo el terreno: **exactamente
`ru = γw/γ = 62.4/124.8 = 0.5`**. La rama `ru` de `pore_pressure_at` no
comparte una línea de código con la de desembalse, así que el acuerdo no
puede venir de un error común. Coincide **círculo a círculo hasta 1e-6**,
sin búsqueda, sin rejilla y sin número publicado. Fue además la primera
comprobación que se hizo, antes de escribir nada: dio 1.2027 contra el
1.20 de Morgenstern y confirmó de golpe la derivación y la geometría
leída de la figura.

---

## 3. El benchmark del apéndice G encontró un error en `min(R, efectiva)`

La otra deuda anotada. Problemas #95 y #96, que **comparten figura** — así
se sabe que comparten geometría — y por tanto dan dos valores publicados
sobre **el mismo círculo fijo**: centro (169.5, 210), R = 210 ft. Sin
búsqueda, sin margen donde compensar.

Al montarlo, DWW reprodujo su 1.44 a la primera y **el Corps dio 1.220
contra 1.35, un −9.6 %**.

### Dónde mordía

Diagnóstico dovela a dovela, con la envolvente compuesta evaluada —como
hasta ahora— con las dos ramas en σ'_fc, la tensión efectiva **anterior**
al desembalse:

| x | u | σ_total | σ'_fc | R | S | manda |
|---|---|---|---|---|---|---|
| 74.8 | 5019 | 5218 | **199** | 1257 | **115** | S |
| 165.7 | 6424 | 10470 | 4046 | 2360 | 2336 | S |
| 233.8 | 5796 | 10403 | 4606 | **2521** | 2660 | R |

Con c' = 0 la rama drenada se desploma justo donde el embalse de 100 ft
deja casi sin tensión efectiva: en x = 74.8 la resistencia cae de 1257 a
**115 psf**, un factor de 11. Mandaba en 31 de 50 dovelas.

**Pilarcitos no podía haberlo detectado**: allí las dos rectas se cruzan
en σ ≈ 104 psf, así que la compuesta nunca llegaba a morder y el caso
reproducía con cualquier lectura. Por eso hacía falta este benchmark, y
por eso quedó anotado en v0.1.68.

### Cinco lecturas, contrastadas contra los dos casos a la vez

| Regla | Apéndice G (1.35) | Pilarcitos (0.824) |
|---|---|---|
| `min(R(σ'_fc), S(σ'_fc))` — la anterior | 1.220 (−9.6 %) | 0.838 (+1.7 %) |
| `R(σ'_fc)` sin compuesta | 1.433 (+6.2 %) | 0.839 (+1.8 %) |
| `min(R(σ_total), S(σ'_fc))` | 1.243 (−8.0 %) | 1.357 (+64.6 %) |
| `min(Kc1(σ'_fc), S(σ'_fc))` | 1.243 (−8.0 %) | 0.895 (+8.6 %) |
| **`min(R(σ'_fc), S(σ'_post))`** | **1.334 (−1.2 %)** | **0.838 (+1.7 %)** |

La única que reproduce los dos es tomar el **tope drenado con la tensión
efectiva posterior al desembalse**. Y no es solo que ajuste:

- El propósito declarado de la compuesta es *no apoyarse en resistencias
  elevadas que solo existen por presiones intersticiales negativas*, y
  esas presiones existirían **después** del desembalse. La lectura
  anterior comparaba la tensión de consolidación con una rotura que
  ocurre en otro estado.
- Deja al Corps y a DWW diferenciándose en **una sola cosa**, la
  envolvente no drenada (R directa frente a Kc = 1 interpolada por K_c),
  que es exactamente lo que la referencia dice que los distingue. El tope
  drenado pasa a ser común y a calcularse en una sola pasada.
- Coincide con el modelo *Drained-Undrained* que la propia referencia
  documenta: resistencia drenada acotada por un techo no drenado.

Los tres procedimientos quedan así:

| Procedimiento | Envolvente no drenada | Tope drenado |
|---|---|---|
| Lowe y Karafiath (1960) | Kc = 1 interpolada por K_c | no |
| Duncan, Wright y Wong (1990) | ídem | sí |
| Cuerpo de Ingenieros (1970) | R directa | sí |

Pilarcitos **no se mueve**: 0.838 antes y después, porque allí la
compuesta no llegaba a actuar.

### Resultado del benchmark

| Procedimiento | Árbitro | OGR Slip2D | Error |
|---|---|---|---|
| Cuerpo de Ingenieros, 2 etapas | 1.35 | 1.3335 | −1.2 % |
| Duncan, Wright y Wong, 3 etapas | 1.44 | 1.4333 | −0.5 % |

Sobre el mismo círculo, con la misma geometría, sin búsqueda.

### Dos comprobaciones de que la figura se leyó bien

El círculo dado es **tangente a la cimentación** en x = 169.5 (centro_y =
radio) y **aflora en el talud aguas arriba exactamente en (72, 24)**, el
punto donde el nivel final corta la ladera. Un vértice mal leído rompería
esa coincidencia.

### Una contradicción en la fuente, medida en vez de zanjada

El texto de ambos problemas dice que el nivel inicial está en **110 ft**;
la figura rotula los dos extremos del nivel inicial en **(0, 103)** y
**(380, 103)**. 110 es la cota de coronación, así que el texto parece
haber copiado el número de al lado.

La primera versión del test daba por hecho que 110 alejaría las respuestas
de los valores del árbitro y así probaría que la figura tiene razón. **No
lo hace**: los dos procedimientos se mueven un 0.5 %, un orden de magnitud
menos que el acuerdo que se está reclamando.

| | 103 ft | 110 ft |
|---|---|---|
| Corps 2 etapas | 1.3335 | 1.3261 |
| DWW 3 etapas | 1.4333 | 1.4258 |

Los 7 ft de más quedan por encima del punto donde la superficie de rotura
aflora, y añaden carga embalsada y presión intersticial casi en
equilibrio. La geometría se toma de la figura, pero **nada de lo que se
afirma aquí depende de esa elección**, y el test lo dice midiéndolo.

---

## Migración de proyectos guardados

Al cargar, si el desembalse rápido está activo con método B̄ **y** la
línea de desembalse queda por encima del nivel freático, se intercambian
los dos tipos de contorno. El archivo antiguo pasa a decir lo mismo con
las etiquetas nuevas. No hace falta versión de formato: la geometría se
autodescribe.

- **Si las dos líneas se cruzan, no se migra.** Ese modelo no es un
  modelo de desembalse, y responder «invertido» mandaría a intercambiar
  dos líneas que no significan ninguno de los dos niveles.
- **Un proyecto multietapa con la línea invertida tampoco se migra**: eso
  nunca fue válido, y recibe el rechazo explícito de
  `check_drawdown_settings` en lugar de una reparación silenciosa.
- **Un material asignado al antiguo nivel bajo se repunta** al contorno
  que ahora es el nivel inicial. Sin eso la asignación se resolvería por
  el respaldo «el primero de su tipo» — que da la respuesta correcta por
  casualidad, y una asignación que acierta por casualidad es decorativa.

---

## Guardas, ahora también para B̄

`check_drawdown_settings` deja de eximir al método B̄. Los cuatro
procedimientos exigen método de agua por superficies y al menos un
material no drenado, y **una línea de desembalse por encima del NF es
ahora un error de modelado con mensaje**. Lo que antes era el requisito
pasa a ser el rechazo.

---

## Archivos

| Archivo | Qué cambia |
|---|---|
| `ogr_core/hydraulic/drawdown_levels.py` | **Nuevo.** Único sitio donde se decide qué línea es qué nivel |
| `ogr_core/hydraulic/pore_pressure.py` | Se retira el bloque B̄, con el comentario de por qué el sitio era el problema |
| `ogr_core/hydraulic/ponded_water.py` | La línea de desembalse deja de embalsar por sí misma |
| `ogr_core/materials/drawdown_envelopes.py` | `composite_strength` toma la resistencia no drenada y la tensión **posterior** |
| `ogr_slip2d/rapid_drawdown.py` | `BBarDrawdownMethod`; el tope drenado se comparte; `_level_project` se importa de `ogr_core` |
| `ogr_core/project/project.py` | Migración del convenio |
| `ogr_gui/dialogs/project_settings_dialog.py` | El tooltip del combo cubre los cuatro procedimientos |
| `tests/test_drawdown_bbar_v169.py` | **Nuevo.** Morgenstern 1963 y la identidad r_u |
| `tests/test_drawdown_usace_v169.py` | **Nuevo.** Apéndice G sobre círculo fijo |
| `tests/test_drawdown.py` | Reescrito con el convenio correcto, y midiendo por dovela |
| `tests/test_water_surfaces_v162.py` | Migración del convenio, junto a la de v0.1.62 |
| `tests/test_drawdown_envelopes_v167.py` | La compuesta, con su nueva firma |
| `tests/test_rapid_drawdown_v168.py` | B̄ pasa por el envoltorio; Pilarcitos intacto |

---

## Coste

Los dos archivos nuevos son baratos y se sabe por qué: el del apéndice G
no busca nada —el círculo viene dado— y el de Morgenstern paga una sola
rejilla por caso.

| Archivo | Coste | Qué lo domina |
|---|---|---|
| `test_drawdown_bbar_v169.py` | 4.0 s | 2 × 2310 círculos de Bishop |
| `test_drawdown_usace_v169.py` | 0.6 s | 9 evaluaciones sobre el círculo dado |
| `test_drawdown.py` (reescrito) | 0.5 s | 7 rebanados de 20 dovelas |

Ninguno malla ni resuelve filtración, que es lo caro en esta suite.

---

## Lo que queda anotado

- **El desembalse parcial puede ser peor que el completo.** La referencia
  lo documenta (*«a minimum safety factor therefore exists at some
  intermediate drawdown level»*) y aquí se ve: el círculo crítico del caso
  100 → 50 ft es otro y mucho más somero que el del 100 → 0. No hay nada
  en la interfaz que sugiera barrer niveles intermedios, y el usuario que
  analice solo el desembalse total puede quedarse del lado inseguro.
- **El tope drenado del Corps se aplica en una sola pasada**, igual que la
  tercera etapa de DWW. Iterar hasta converger cambiaría poco —cambia la
  resistencia de las dovelas que ya estaban topadas— pero no se ha medido
  cuánto.
