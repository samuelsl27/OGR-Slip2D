# OGR Slip2D v0.1.118

**El 13 % ya era +1 % antes de empezar, el síntoma que lo acompañaba lo había
cerrado otro defecto dos versiones antes, y de los dos filtros que parecían la
causa resultó que uno no movía el mínimo ni un dígito**

---

## De dónde salió

El encargo era la anomalía **A19-1** (defecto **D21** del banco): sobre el
problema 19 —Greco (1996) ejemplo 4, cuatro capas, dos sin cohesión— una
rejilla circular corriente encontraba **1,454** mientras el Path Search con
5000 superficies y optimización se quedaba en **1,649**, un **13 %** por
encima. Una búsqueda no circular no puede encontrar más que una circular: el
espacio circular está contenido en el no circular, salvo discretización.

Venía con dos síntomas de acompañamiento y una advertencia: **las medidas eran
de 0.1.97**.

---

## 1 · Lo primero, remedir. Y el enunciado ya no describía el programa

Entre 0.1.97 y 0.1.117 han entrado D07b, D08, D09 y D10, todos en el camino de
esta medida. Remedido en **0.1.117**, Spencer, 30 dovelas, semilla 10116, con
la casilla de optimización como la declara el `.ogr` (desmarcada):

| | 0.1.97 (ficha) | **0.1.117** |
|---|---|---|
| Rejilla circular 15×15, 10 radios | 1,454290 | **1,433239** (2816 generadas, 2125 válidas) |
| Path Search 5000 | 1,697798 · **505 válidas / 867 intentos** | **1,448145** · **5000 válidas / 6115 intentos** |
| Block 2 grupos / 3000 | 1,467190 (1936 válidas) | **1,596973** (1852) |
| Block 3 grupos / 3000 | 1,541860 | **1,606084** (1364) |
| Block 4 grupos / 3000 | 1,563650 (522) | **1,668830** (635) |
| Block 5 grupos / 3000 | — | **1,822153** (222) |

Cuatro correcciones al enunciado, antes de tocar nada:

**a) El primer síntoma estaba cerrado, y no por este trabajo.** «Declara 5000
superficies y sólo hace 867 intentos con 505 válidas» era el objetivo de
**500** del campo en la sombra `path_num_paths` —defecto **D07b**, cerrado en
0.1.103— más las cinco superficies que añadía el optimizador privado que
retiró **D08** en 0.1.104. Hoy declara 5000, obtiene 5000 válidas en 6115
intentos y publica el `attempts` de verdad.

**b) El 13 % era +1,04 %.** 1,448145 contra 1,433239. La desigualdad se seguía
violando; el tamaño estaba exagerado por un factor doce.

**c) El lado izquierdo de la comparación SÍ era reproducible.** La auditoría
del banco lo daba por perdido (P019-COH2: «no se sabe sobre qué modelo se
obtuvo»). Con `grid_nx = grid_ny = 15`, `radius_increment = 10` y límites
automáticos salen **2816 superficies**, exactamente la población que cita la
anomalía. Lo que no coincide es el factor, y es por las versiones de por medio.

**d) El «contraste que no puede romperse» ya estaba roto.** El +0,06 % del
problema 18 es frente a **Baker 1,02**, y salía de una corrida **doblemente
optimizada** (P018 en la auditoría). Con una sola optimización, 0.1.117 daba
**0,997969**: −2,2 % frente a Baker, por debajo de un mínimo publicado por
programación dinámica. El arreglo de esta versión lo devuelve a **1,021928**,
+0,19 % — lo **restaura**, no lo amenaza.

---

## 2 · La causa que quedaba en Path Search: 0,3·H con la H del MODELO

La recomendación documentada para la longitud de segmento es *«approximately
0.3H, where H is the maximum height of the **slope**»*. `search.py` calculaba
`H = y_max - y_min` sobre el **contorno externo entero**, que es el relieve del
**modelo** y cuenta como talud cada metro de **cimentación bajo el pie**.

En el problema 19 el modelo va de y = 0 a y = 100 y el talud del pie (y = 40)
a la coronación (y = 100): **H = 100 donde el talud mide 60**. Segmentos de
30 m y ocho vértices para una masa de 150 m.

**El hueco era discretización, y se puede medir aparte.** El mismo círculo
crítico de la rejilla, redibujado en cuerdas:

| | FoS |
|---|---|
| arco | 1,433237 |
| 16 cuerdas | 1,438735 (+0,38 %) |
| **8 cuerdas** | **1,446998 (+0,96 %)** |

Ocho cuerdas es lo que producía el Path Search, y 1,4470 es prácticamente el
1,4481 que devolvía. **No estaba encontrando una superficie peor: encontraba
la misma con menos vértices.**

Barrido de la longitud de segmento sobre el problema 19 (0.1.117):

| `segment_length` | FoS | vs rejilla 1,433239 |
|---|---|---|
| auto = 0,3·100 = **30** | 1,448145 | **+1,04 %** |
| **18 = 0,3·60** | 1,426871 | **−0,44 %** |
| 12 | 1,426996 | −0,44 % |
| 7,14 | 1,414443 | −1,31 % |

Corregido: **H es el relieve del perfil del terreno entre los Slope Limits**.
No `cresta.y − pie.y` de la cara más inclinada, porque en un talud de varias
bermas la cara más inclinada es una berma y no el talud.

---

## 3 · La ventana de arranque era invención propia, y excluía la respuesta

La referencia define el arranque del Path Search por los **Slope Limits**:
*«if a single set of Slope Limits is defined, SLIDE will automatically divide
the range in half, and use the range closest to the toe»*. Y los Slope Limits
por defecto son *«the left and right limits of the upper surface of the
External Boundary»*: en el problema 19, [0, 260], mitad del lado del pie
**[0, 130]**.

OGR usaba una ventana derivada de la cara del talud,
`[pie − 0,15·ancho, pie + 0,55·ancho]` = **[42, 126]**.

**El testigo es del propio manual**, y estaba anotado en la auditoría
(P019-PUB3) sin que nadie lo hubiera cobrado: el panel de la figura 19.2
publica *Left Slip Surface Endpoint: **39.177**, Right: 191.374*.

- **39,177 queda fuera de [42, 126]**, por 2,8 m.
- El círculo crítico de la propia rejilla aflora en **x = 29,37** (medido) —
  fuera por 12,6 m.

Es decir: el espacio de búsqueda **no contenía ni la superficie publicada ni
el círculo con el que se la comparaba**, y no por discretización sino porque
el punto de arranque no se sorteaba nunca ahí. El mínimo que devolvía arrancaba
en x = 44,3, pegado al borde de la ventana, que es la firma de un óptimo
recortado.

Por el otro extremo, igual: el filtro de salida usaba
`[cresta − 0,55·ancho, cresta + 0,6·ancho]` en vez de los límites, cuando la
referencia dice que *«The Slope Limits DO NOT influence the location of the
endpoint, but are used as a filter»*.

### Y los Slope Limits sólo llegaban a UNA de las seis búsquedas

*«The Slope Limits **ALWAYS** serve as a filter for valid surfaces, regardless
of the Surface Type or the Search Method being used.»*

Sólo `GridSearch` los recibía. `BlockSearch` **implementaba el filtro** y
`build_search` no le pasaba nunca un valor con el que filtrar. `PathSearch` ni
siquiera los tenía como argumento. `SlopeSearch` al menos avisaba; Path y Block
no avisaban de nada. Es la forma exacta de **A37-1 / D07** (Minimum Elevation y
Minimum Depth, declarados, editables, guardados, y sin una rama que los
pasara), y se ha arreglado con el mismo patrón:

- `slope_limits` pasa a `_base_kwargs` y a `BaseSearch`, de modo que las seis
  ramas lo reciben por `common` y ninguna puede olvidarlo;
- el **filtro** vive una sola vez, en `_best_of_masses`, junto a los otros dos
  filtros de superficie. Se pregunta **después de rebanar**, porque ése es el
  primer momento en que se conoce la extensión de una masa circular: los
  extremos de un arco son donde corte el terreno, y un arco que lo corta más de
  dos veces tiene un par por masa;
- la **generación** la leen las búsquedas que construyen sus candidatas desde
  la superficie del terreno. La referencia exime exactamente a una, el Block
  Search, cuyos vértices salen de los objetos que dibuja el usuario.

Ningún modelo del banco declara límites (todos a `None`), así que esto no mueve
ningún número existente; el test de regla 7 usa un modelo que sí los estrecha.

---

## 4 · Path Search, resultado

Problema 19 (publicado: Slide 1,398; Greco 1,40–1,42):

| | FoS | Δ vs Slide | Δ vs Greco 1,42 | vs rejilla 1,433239 |
|---|---|---|---|---|
| 0.1.97 | 1,697798 | +21,4 % | +19,6 % | +16,7 % |
| 0.1.117 | 1,448145 | +3,6 % | +2,0 % | +1,04 % |
| **0.1.118** | **1,415424** | **+1,25 %** | **−0,32 %** | **−1,24 %** ✔ |

Once vértices en vez de ocho, y la superficie va de x = 46,00 a **x = 190,56**
contra los **191,374** que publica el manual: el extremo de salida coincide al
0,4 %.

Problema 18 (Baker 1980; publicado Slide 1,010, Baker 1,02), sin optimizar:
**1,074928 → 1,062510**.

---

## 5 · Block Search: dos filtros que la referencia no tiene, y una sorpresa

La referencia describe la generación en cuatro pasos: un punto por objeto de
búsqueda → **ordenar por X** (*«to ensure that the slip surface … does not
reverse direction»*, y eso es toda la admisibilidad cinemática que pide) →
proyectar a la superficie con los ángulos izquierdo y derecho → filtrar por
Slope Limits. *Convex Surfaces Only* es **una casilla del usuario**.

OGR aplicaba además dos filtros **siempre activos**, aun con la casilla de
convexidad desmarcada: vértices interiores por debajo de la cuerda, y
**unimodalidad** (bajar hasta un único mínimo y luego subir). Son de v0.1.17,
**anteriores** al cribado post-análisis que la referencia sí documenta y que el
proyecto ya tiene desde v0.1.32 y v0.1.89: la comprobación de m-alpha y el
Tensile Stress Check. El motivo con el que se escribieron —«superficies en
sierra que dan factores espurios bajos»— es exactamente lo que ese cribado
atrapa hoy, y lo atrapa donde la referencia lo pone: **después** de converger.

Cada punto de bloque sortea su `y` de forma **independiente y uniforme**, así
que la probabilidad de que N salgan unimodales es `2^(N−1)/N!`. Normalizado a
N = 2: 1 · 0,667 · 0,333 · 0,133. Medido en 0.1.117 sobre el problema 19,
3000 candidatas: 1852, 1364, 635, 222 → 1 · 0,74 · 0,34 · 0,12. **El filtro
ERA la tasa de aceptación**, y ésa es la respuesta a la segunda pregunta del
encargo: añadir grupos no compraba libertad, compraba rechazo.

### La sorpresa: quitarlos no mueve el mínimo ni un dígito

| grupos | 0.1.117 · FoS | 0.1.118 · FoS | válidas 0.1.117 | **válidas 0.1.118** |
|---|---|---|---|---|
| 2 | 1,596973 | 1,596973 | 1852 | **1852** |
| 3 | 1,606084 | 1,606084 | 1364 | **1623** |
| 4 | 1,668830 | 1,668830 | 635 | **1214** |
| 5 | 1,822153 | 1,822153 | 222 | **841** |

Idénticos a seis decimales. Los dos filtros **sólo rechazaban superficies que
nunca iban a ser el mínimo**. Así que el síntoma (b) del encargo tenía dos
mitades y **dos causas distintas**, y la que se ve —el factor que sube— no es
la que se arregla aquí.

### La otra mitad: subir con los grupos no es un defecto del generador

El encargo lo lee como uno: *«más grupos deberían dar más libertad y por tanto
un mínimo menor o igual»*. Con los filtros fuera el mínimo **sigue subiendo**,
y la razón es que una búsqueda aleatoria **no guiada** con el mismo
presupuesto de candidatas y un vértice libre más muestrea un espacio mayor más
finamente repartido: el mejor de 3000 sorteos empeora al subir la dimensión.
No hay nada que arreglar ahí sin inventar; la referencia lo esquiva
**exigiendo que el usuario dibuje los objetos de búsqueda**
(*«A Block Search requires at least one Block Search object to be defined by
the user»*), y OGR, cuando no hay ninguno, sustituye esa decisión por bandas
propias. Eso ya no es la Block Search de la referencia y ahora el código lo
dice.

Se midió también la alternativa de no repartir en bandas —sortear los
`num_groups` puntos en toda la región y ordenarlos por x, que es lo que darían
N ventanas superpuestas—: los mínimos se mueven menos que el ruido y en las dos
direcciones, y la variante cuesta **un tercio de las válidas** por abscisas
casi coincidentes. Las bandas se quedan, y ahora con el A/B escrito al lado.

### `block_num_groups` deja de derivarse de otra magnitud

Cerrado **D07c(b)**. El diálogo lo calculaba como `Number of Surfaces // 1000`
si *Multiple Groups* estaba marcado: 5000 superficies significaban **cinco**
grupos, y pedir más superficies cambiaba en silencio la forma de la búsqueda.
Ahora es su propio contador, entre 1 y 20, habilitado por esa casilla.
`block_multiple_groups` sigue en el inventario congelado de
`test_settings_coverage_v1103.py`, y con razón: **enciende un control y nada
más**, así que el motor no tiene nada que leer. El inventario admite desde hoy
esa respuesta —`UI only`— porque decirlo en voz alta es su trabajo.

### Con la configuración que la referencia describe, Block SÍ llega

Los ángulos por defecto de OGR (135–135 y 45–45) **coinciden con los de la
referencia**, que documenta que con Start = End se usa ese ángulo exacto para
todas las superficies. Entonces las dos cuerdas extremas quedan clavadas a 45°.
Medido sobre el círculo crítico ganador de la rejilla, ese círculo aflora a
**27,7°** por la izquierda y **68,4°** por la derecha. **Exigir «Block ≤
rejilla circular» con los ángulos por defecto es exigir algo que el método
documentado no puede dar.**

Abiertos a la ventana que la propia referencia declara admisible —izquierda
95–175, derecha 5–85— los 152,3° y 68,4° que hacen falta sí caben:

| grupos | sin optimizar (3000) | **con Optimize Surfaces** (600) |
|---|---|---|
| 2 | 1,484145 (648 válidas) | **1,407263** (147) |
| 3 | 1,647488 (547) | 1,469779 (102) |
| 4 | 1,659322 (384) | 1,440964 (78) |

**1,407263 contra los 1,433239 de la rejilla: −1,81 %.** Frente a lo publicado,
**+0,66 %** sobre el 1,398 de Slide y **−0,90 %** sobre el 1,42 de Greco.
Abrir los ángulos solos ya vale un 7 % (1,597 → 1,484 con dos grupos); el resto
lo pone la optimización — que es exactamente lo que el manual declara haber
usado para este problema: *«Random search with Monte-Carlo optimization»*.

Así que **el criterio de cierre de D21 se cumple para las dos búsquedas**,
cuando cada una se configura como la referencia la describe.

---

## 6 · El test: una desigualdad con la tolerancia CALCULADA

`tests/test_search_inequality_v1118.py`, diez casos. Lo que lo hace externo
(regla 1) no es un número guardado, es cómo se construye la referencia:

```
min(búsqueda)  ≤  FoS( círculo crítico de la rejilla discretizado
                       al MISMO número de tramos que produjo la búsqueda )
```

El encargo pedía *«una tolerancia por discretización que hay que justificar, no
elegir»*. La justificación se mide: el mismo arco vale 1,433237, y en ocho
cuerdas 1,446998. Así que el test **discretiza el círculo ganador dentro de la
propia prueba** en vez de escribir una constante, y si mañana cambia el método
la referencia se mueve con él.

El umbral del test de rendimiento tampoco se elige: es **el doble de lo que
dejaría el filtro retirado**, `2·2^(N−1)/N!`. Antes del arreglo esa comparación
daba 0,074 contra un límite de 0,164 (falla); después, 0,195 contra 0,107.

Y hay una aserción que **no** está, porque se midió y es falsa: que Block con
más grupos encuentre un mínimo menor. Escribirla habría sido consagrar la
lectura equivocada del síntoma.

---

## 7 · Lo que se encontró y NO se ha tocado (regla 6)

- **D21b** — el mínimo de Block sube con los grupos, y ya no es por rechazo:
  con optimización, 1,407 / 1,470 / 1,441 para 2 / 3 / 4. Es dimensionalidad en
  una búsqueda aleatoria no guiada sobre una región que **OGR inventa** porque
  la referencia no define ninguna (exige que el usuario dibuje los objetos).
  Las tres fracciones que la definen —`0,3·ancho_cara`, `0,05·dy`, `0,75·dy`—
  se apoyan en el relieve del **modelo**, el mismo desliz conceptual que la
  longitud de segmento. **Pero no hay ningún valor documentado al que
  corregirlas**: cambiarlas sería ajustar hacia la respuesta conocida, que es
  lo único que aquí no puede pasar. Anotado en el código, sin tocar.
- **Block Search empeoró entre 0.1.97 y 0.1.117** sobre este modelo (1,467 →
  1,597 con 2 grupos) mientras la rejilla bajaba. Sin diagnóstico.
- **Una poligonal de 31 vértices con `num_slices = 30` devuelve `None` sin
  aviso.** Medido al discretizar el círculo: n = 8 y n = 16 se evalúan, n = 30
  y n = 60 no. Puede ser legítimo —un vértice por frontera de dovela— pero es
  silencioso.
- **`max_segments = 30` es una constante de la clase.** La referencia ata ese
  tope al *Number of Slices* del proyecto. Hoy coinciden por casualidad.
- **Problema 41** — el Path Search ya daba un mínimo **por debajo de todas** las
  referencias publicadas (1,45 contra los 1,56 de la programación dinámica de
  Baker 2003). Segmentos más cortos dan más libertad, así que puede bajar más.
  Es un defecto de **signo contrario** al de este encargo y apunta a la
  evaluación de superficies no circulares, no a la generación.
- **Quitar los dos filtros de generación cuesta tiempo.** Ahora casi todas las
  candidatas llegan al solver en vez de morir antes; sobre el problema 19 con
  3000 superficies el Block Search pasa de ~85 s a varios minutos. Es lo
  correcto —la referencia criba después de converger— pero es un coste real.

---

---

## 8 · Verificación sobre el banco

Los **seis** problemas que usan búsqueda no circular, corridos con 0.1.118 por
`analysis_runner.build_search`, que es la puerta que usa todo el mundo:

| | método | 0.1.118 | vs publicado | archivado (0.1.97) |
|---|---|---|---|---|
| **P7** ACADS 3(a), Block con objetos | bishop | 1,234434 | −1,87 % vs 1,258 | 1,234434 |
| | spencer | 1,292270 | +2,72 % vs 1,258 | 1,292270 |
| | GLE | 1,282683 | +2,94 % vs 1,246 | 1,282683 |
| | janbu corr. | 1,309770 | +2,73 % vs 1,275 | 1,309770 |
| **P8** ACADS 3(b) | spencer | 1,292270 | +1,20 % vs 1,277 | 1,292270 |
| | GLE | 1,282683 | +1,64 % vs 1,262 | 1,282683 |
| | janbu corr. | 1,309770 | +1,22 % vs 1,294 | 1,309770 |
| **P9** ACADS 4 | spencer | 0,705377 | −7,19 % vs 0,760 | 0,705377 |
| | GLE | 0,680775 | −5,45 % vs 0,720 | 0,680775 |
| | janbu corr. | 0,696209 | −5,15 % vs 0,734 | 0,696209 |
| **P18** Baker (1980) | spencer | **1,062510** | +5,20 % vs 1,010 | 1,074928 |
| **P19** Greco (1996) | spencer | **1,415424** | **+1,25 %** vs 1,398 | 1,448145 |
| **P41** Jiang et al. (2003) | bishop | 1,480596 | −10,59 % vs 1,656 | 1,452584 |
| | janbu simpl. | 1,318973 | −15,61 % vs 1,563 | 1,285119 |

**Los diez valores de los tres problemas de Block coinciden dígito a dígito con
los archivados.** Son los únicos del banco que ejercitan el camino documentado
—objetos de búsqueda dibujados por el usuario y rangos de ángulo 135–155 /
45–65— y son el ancla externa de este cambio: retirar los dos filtros **no les
mueve nada**, que es lo mismo que dice la tabla del problema 19 y la razón por
la que el síntoma (b) estaba mal leído.

**P18 mejora** (+6,43 % → +5,20 % sin optimizar; con optimización, de 0,997969
a 1,021928, o sea de −2,2 % a **+0,19 %** frente al 1,02 de Baker).

**P41 no empeora**, que era el riesgo declarado: un segmento más corto da más
libertad, y este problema ya devolvía un mínimo por debajo de todas las
referencias. Se mueve **hacia arriba** (1,452584 → 1,480596 en Bishop), o sea
hacia lo publicado, y sigue siendo el defecto de signo contrario que se anota
arriba.

## 9 · Corregido en el banco

`ERRORES_Y_DISCREPANCIAS.md` recoge el cierre de **D21** con las cuatro
correcciones al enunciado y las cinco causas, cada una con su cita, y abre
**D21b**. La ficha `02_Slide2_Problema019.md` pasa de **REVISAR** a **OK** y
conserva la tabla de 0.1.97 marcada como lo que es: lo que sostenía la
anomalía, no una descripción del programa. Cierra de paso **D07c(b)**.

Nada de esto entra en un commit: el banco vive fuera del repositorio.

---

## Nota aparte, no tocada

`ogr_slip2d/search.py` nombra el producto de referencia **22 veces**, y el
resto del motor otras cien. AGENTS.md es explícito en que el código no puede
contener esas marcas. Es anterior a esta versión y no hay test que lo sujete,
así que merece su propia pasada —con el test— y no un arreglo a medias desde
aquí. Lo añadido en 0.1.118 dice «la referencia».
