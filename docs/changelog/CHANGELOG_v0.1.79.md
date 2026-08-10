# OGR Slip2D v0.1.79 — tres casos publicados más, y lo que aparecieron al llegar

v0.1.78 dejó los casos ACADS 1(c), Arai & Tagyo y Yamagami & Ueta fuera
porque **su geometría solo existía en figuras**. Esta versión las saca de los
PDF, y con ellas llegan tres casos de validación nuevos y una anomalía que
llevaba escondida desde v0.1.19.

---

## Las figuras salieron del propio PDF

No hizo falta ninguna captura de pantalla. Las figuras son **imágenes
rasterizadas incrustadas** (`/Subtype /Image`, FlateDecode, paleta indexada)
dentro de `Slide_SlopeStabilityVerification_Part1.pdf`, así que se decodifican
directamente: objeto XObject → zlib → resolver la paleta → PNG.

Dos detalles del camino que valen para la próxima vez:

- **La numeración impresa no sirve para localizarlas.** Va desfasada respecto
  a la del PDF, y el desfase no es constante. Lo que sí funciona es buscar
  cada página por **su propio texto** (`N.3 Geometry and Properties`), que
  además confirma que se ha abierto la figura correcta.
- **Sin resolver la paleta no se ve nada.** Con índice de color, interpretar
  los bytes como gris convierte un dibujo de líneas en ruido. El primer
  intento salió así.
- **Y hay dos profundidades de bit mezcladas en el mismo PDF.** Casi todas
  las figuras son de 8 bits por píxel, pero algunas son de 4 (dos píxeles por
  byte). Leer una de 4 como si fuera de 8 no falla: produce una imagen
  plausible, oscura y repetida, en la que se distinguen líneas. Estuvo a
  punto de darse por buena — y con ella se habría dado por perdido el caso
  `005`, que en realidad está completamente rotulado.

---

## Cuatro casos nuevos

### `002-yamagami-ueta-1988` — el más exigente de la carpeta

> Yamagami, T. & Ueta, Y. (1988), *Search for noncircular slip surfaces by the
> Morgenstern-Price method*, Proc. 6th Int. Conf. Num. Meth. Geomech.

Talud homogéneo, geometría **rotulada con coordenadas sobre la propia
figura** — nada que medir.

| Método | Publicado | OGR | Error |
|---|---|---|---|
| Bishop simplificado | 1.348 | 1.3539 | **0.44 %** |
| Fellenius / Ordinario | 1.282 | 1.2860 | **0.31 %** |

Tolerancia 1.5 %, la más estrecha de la carpeta, y se la puede permitir
porque la fuente es un valor calculado y publicado en una revista, no una
media entre programas que discrepan. Que acierten **los dos** fija además la
distancia entre ellos (4.9 %), no solo su nivel.

### `003-acads-1c` — regiones y materiales

El hermano estratificado del `001`: tres capas. Aquí las coordenadas **sí**
estaban en el texto; lo que solo existía en el dibujo era **cómo se conectan**.

Y ahí está lo bueno del caso: se pudo comprobar la lectura **sin usar el
factor de seguridad**. La figura de resultados publica el círculo crítico
completo, y sus dos puntos de corte con el terreno están ambos a 18.781 del
centro — lo que de paso resuelve el radio, que en la imagen se lee ambiguo
entre 16.781 y 18.781. Colocando ese círculo exacto sobre la geometría leída:

```
    OGR:        x = 29.703 .. 50.991
    publicado:  x = 29.702 .. 50.991
```

**Un milímetro sobre 21 m de cuerda.** Si las líneas de material estuvieran
mal conectadas, el círculo no podría daylightear donde dice la referencia. La
geometría no es una interpretación razonable: está verificada contra un dato
independiente.

Con ella, Bishop da **1.4065** frente a la media Bishop de 16 programas
(1.406): **0.04 %**.

### `004-arai-tagyo-1985-ej1` — y por qué su tolerancia es del 3.5 %

> Arai, K. & Tagyo, K. (1985), *Determination of noncircular slip surface…*,
> Soils and Foundations 25(1).

| | Bishop |
|---|---|
| Arai & Tagyo (1985), publicado | 1.451 |
| Programa comercial de referencia | 1.409 |
| OGR Slip2D | 1.4136 |

Los dos reanálisis modernos coinciden entre sí en un 0.3 % y los dos quedan
un 2.6–2.9 % **por debajo** del valor de 1985. Eso no es error de nadie: es
lo que separa una búsqueda de 1985 de una de ahora, que encuentra un mínimo
menor porque puede mirar en más sitios — y un mínimo menor es un mínimo
mejor.

El caso espera **1.451, el valor publicado**, con tolerancia 3.5 %. Las dos
alternativas eran peores: esperar 1.409 sería consagrar la salida de un
programa comercial —lo que `validacion/README.md` prohíbe—, e inventar un
promedio sería fabricar una referencia que nadie ha publicado. La tolerancia
la fija la fuente, que es exactamente para lo que existe esa regla.

### `005-arai-tagyo-1985-ej3` — el agua, por fin

Los cuatro casos anteriores son análisis **en seco**. Ninguno de ellos podía
detectar un error en el cálculo de la presión intersticial.

Éste es **exactamente el talud del `004`** con un nivel freático añadido —
también rotulado sobre la figura: (0,15) → (18,15) → (30,23) → (48,29) →
(66,32). Compartir geometría y material con el caso seco es lo que le da su
valor: la diferencia entre los dos aísla el efecto del agua y nada más.

```
    seco (004):      Bishop 1.451 publicado
    con agua (005):  Bishop 1.138 publicado      OGR 1.1199
```

Un 22 % de caída atribuible solo a u. Si el cálculo estuviera mal escalado,
fallaría éste y no el `004` — y `caso.md` lo dice, para que quien vea el
fallo sepa dónde mirar primero.

Solo declara Bishop. Janbu simplificado y corregido salen un 8.6 % por debajo
de la referencia, **pero sobre otro círculo** (más somero); separar "otro
mínimo" de "otro resultado" exigiría el círculo publicado, y este problema
—a diferencia de ACADS 1(c)— no lo publica.

---

## La anomalía: Spencer y GLE devuelven el valor de Bishop

**Reportada, NO corregida** (regla 6). Evidencia completa en
`docs/audits/spencer_gle_interslice_v179.md`.

Sobre un círculo dado, Spencer y GLE coinciden con Bishop hasta la tercera o
cuarta cifra. Las referencias los sitúan **por debajo**:

| | Bishop | Spencer publicado | Spencer OGR |
|---|---|---|---|
| Ej_1, círculo de referencia | 0.883 | −0.68 % | **−0.065 %** |
| ACADS 1(c), círculo publicado | 1.407 | −2.1 % | **−0.02 %** |

Mismo patrón, misma dirección, y su tamaño escala con lo que la referencia
separa los métodos. La contribución de la cortante entre dovelas está
llegando al resultado con un peso muy inferior al que debería, o no llega.
Spencer y GLE comparten la maquinaria de λ, lo que apunta a una causa común.

En ACADS 1(c) no cabe escaparse por la geometría ni por la búsqueda: es el
**mismo círculo**, sobre una geometría verificada al milímetro, y Bishop
acierta con un 0.13 % mientras Spencer se va un 2.29 %.

### Una hipótesis que parecía buena y era falsa

La primera sospecha fue que λ estaba clavado: salía 1.046662 en ACADS 1(c) y
1.046603 en Ej_1, dos modelos sin nada en común coincidiendo en cinco cifras.
Es casualidad. Barriendo cinco círculos del mismo modelo, λ recorre 1.0278,
1.0466, 1.0707 y 1.0957. **λ sí depende del círculo.** Queda escrito porque
la hipótesis era razonable y descartarla costó lo mismo que confirmarla.

### Por qué ningún test lo veía

`test_slide_validation_ej1.py` valida los siete métodos con tolerancia 0.5 %…
salvo Spencer y GLE, que tienen **1.0 %**. Los errores reales son 0.64 % y
0.53 %: por debajo de lo que se les concede y por encima de lo que se le
exige a todo lo demás. El test pasa desde v0.1.19.

La tolerancia doble no se documentó nunca como decisión. Vista ahora, **la
asimetría era el hallazgo**: los dos únicos métodos que necesitaban el doble
de margen son exactamente los dos que comparten la maquinaria de λ. Una
tolerancia que se afloja para que un test pase deja de medir el código.

No se ha tocado. Estrecharla ahora pondría un test en rojo sin arreglar nada;
cuando se corrija el fondo, bajar esas dos tolerancias a 0.5 % será la prueba
de que la corrección funcionó.

### Consecuencia inmediata

**Ningún caso de `validacion/casos/` declara Spencer ni GLE**, aunque las
cuatro fuentes publican valores para ellos. También se han **retirado del
`001`**, donde pasaban con un 0.4 % de error: en ese problema la referencia
apenas los separa de Bishop (0.987 contra 0.986), así que acertarlos no
demostraba nada, y sobre los problemas donde sí se separan no los acertamos.

Escribir los números que salen hoy sería justo lo que prohíbe la regla 1 —
un test de instantánea consagra el bug. Hay un test que comprueba esa
ausencia, para que volver a añadirlos sea una decisión y no una limpieza.

---

## Qué se probó

- `tests/test_published_cases_v179.py` (12): que el círculo publicado
  daylightea donde dice la referencia y que sus extremos fijan el radio (la
  verificación de la geometría, independiente del factor de seguridad); las
  tres regiones de ACADS 1(c); Bishop sobre el círculo publicado; Slope
  Search sobre los dos taludes de revista y su superioridad frente a la
  rejilla declarada; **que el agua mueve el número** —los casos `004` y
  `005` comparten geometría y material, así que el par es la comprobación de
  la regla 7 sobre la propia presión intersticial, y la caída tiene que ser
  la publicada, no solo negativa—; y la ausencia de Spencer/GLE en todos los
  casos.
- `tests/test_validation_cases.py`: **cinco** casos ejecutables donde había
  uno.

Suite completa: **1706 tests, 1706 pasan.**

## Qué falta por probar

- **Arai & Tagyo ejemplo 2** (problema #15), el talud estratificado con capa
  débil: su figura está extraída, pero **las dos líneas de capa no llevan
  coordenadas rotuladas**, a diferencia de los ejemplos 1 y 3. Habría que
  medirlas sobre la escala del dibujo, que es lo que este proyecto no hace
  sin una comprobación independiente como la del `003` — y este problema no
  publica su círculo crítico. Es el que más valdría: Greco (1996) y Kim et
  al. (2002) lo usan para comparar búsquedas **no circulares**, que siguen
  sin ninguna referencia externa.
- **Talbingo (#5) y ACADS 5 (#10)**: el primero tiene 26 puntos tabulados
  pero la conectividad en la figura; el segundo necesita además la red de
  flujo.
- El fondo de la anomalía de Spencer/GLE.

## Pendientes que siguen abiertos

Los mismos de v0.1.78, sin cambios: las Slope Limits que `SlopeSearch` no
lee; el *Lower Angle* anulado por `min(ang_lo, radians(-70))`; las dos
casillas del panel de Slope Search que `apply()` no lee; el CLI sin
probabilístico, barrido, retroanálisis ni informes; y el `except Exception`
de `_ComputeWorker.run`. Más, ahora, `spencer_gle_interslice_v179.md`.
