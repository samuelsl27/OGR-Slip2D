# OGR Suite v0.1.33 — Changelog

**Lanzamiento:** 2 de agosto de 2026
**Desarrollador:** Samuel Sáez López — Estudiante de Doctorado, UPCT
**Licencia:** GPL-3.0

> **Fase P0 del análisis probabilístico: núcleo estadístico.** Las siete
> distribuciones de la referencia, los dos métodos de muestreo, el
> truncado por mínimo/máximo relativos, la correlación c–φ y los
> estadísticos de salida. Primer bloque del plan de seis fases descrito
> en `docs/PLAN_PROBABILISTICO.md`.

---

## 📋 Plan por fases

Nuevo documento **`docs/PLAN_PROBABILISTICO.md`**, obtenido por
ingeniería inversa de las ~15 páginas de documentación probabilística de
la referencia. Seis fases: **P0 núcleo estadístico** (esta versión) →
P1 variables aleatorias → P2 motor Global Minimum → P4 sensibilidad →
P3 Overall Slope → P5 interfaz. La sensibilidad se adelanta a Overall
Slope porque es más simple, comparte la definición de variables y da
resultados útiles antes.

## 🆕 Distribuciones (`ogr_core/statistics/distributions.py`)

Las **siete** de la referencia: Normal, Uniform, Triangular, Beta,
Exponential, Lognormal y Gamma, cada una con densidad, acumulada e
inversa.

**Mínimo y máximo RELATIVOS.** Un matiz importante de la referencia que
condiciona todo el diseño: los límites que introduce el usuario no son
valores absolutos sino **distancias respecto a la media**, de modo que la
variable queda truncada a `[media − rel_min, media + rel_max]`. Es como
un ingeniero expresa la incertidumbre de forma natural («la cohesión es
5 kPa, más o menos 2») y además garantiza que no se generen valores
imposibles, como un ángulo de rozamiento negativo.

**El truncado se aplica por remapeo de la variable uniforme**, no por
rechazo:

    u' = F(lo) + u·[F(hi) − F(lo)]      x = F⁻¹(u')

El rechazo rompería la estratificación del Latin Hypercube (algún
estrato se quedaría sin muestra), mientras que remapear la conserva
exactamente. Un test comprueba que no se pierde ninguna muestra aun con
un truncado agresivo.

Parametrización pensada para el usuario: la **lognormal** y la **gamma**
se definen por la media y desviación de *la variable*, no de su
logaritmo, convirtiéndose internamente; la **beta** se ajusta por el
método de los momentos sobre el rango truncado.

## 🆕 Muestreo

- **Monte Carlo** — variables independientes.
- **Latin Hypercube** — el intervalo unidad se divide en N estratos, se
  extrae una variable dentro de cada uno y se baraja, de forma
  independiente para cada variable.

**Verificación de la afirmación de la referencia** (1000 muestras LHS ≈
5000 Monte Carlo). Error medio de la media, normal(10, 2), 30 semillas:

| N | Monte Carlo | Latin Hypercube | Mejora |
|---|---|---|---|
| 50 | 0.2305 | 0.0153 | **15×** |
| 100 | 0.2039 | 0.0083 | **25×** |
| 500 | 0.0790 | 0.0011 | **75×** |
| 1000 | 0.0605 | 0.0005 | **132×** |

## 🆕 Correlación c–φ

`correlate_pair()` impone un coeficiente de correlación entre dos series
muestreadas por reordenación de rangos (idea de Iman-Conover), lo que
**preserva exactamente la distribución marginal** de cada variable: solo
cambia el emparejamiento.

Un primer intento con escalado lineal de rangos **se pasaba un 10 %**
(pedido −0.70 → obtenido −0.738). Se calibró usando **puntuaciones
normales de van der Waerden**, con lo que el error cae por debajo de
0.013 en todo el rango:

| Pedido | Obtenido | Error |
|---|---|---|
| −0.90 | −0.903 | −0.003 |
| −0.70 | −0.705 | −0.005 |
| −0.30 | −0.298 | +0.002 |
| +0.80 | +0.808 | +0.008 |

## 🆕 Estadísticos de salida

`SampleStatistics`: media, desviación, mínimo, máximo, **probabilidad de
fallo** (fracción de muestras con FS < 1), **índice de fiabilidad**
normal `β = (μ − 1)/σ` y su versión **lognormal** (a menudo mejor ajuste,
porque un factor de seguridad no puede ser negativo), histograma y datos
del **gráfico de convergencia** que la referencia usa para decidir cuántas
muestras hacen falta.

## ⚡ Muestreo vectorizado (100× más rápido)

Los tests iniciales tardaban **67 s** porque cada muestra hacía una
llamada escalar a SciPy. Con el mapeo por lotes mediante NumPy el mismo
conjunto tarda **0.7 s**. No es cosmética: un análisis probabilístico
real necesita miles de muestras por variable, así que este camino es el
que se usará en las fases siguientes.

Sin dependencias nuevas: SciPy y NumPy ya eran dependencias núcleo, y
Uniform, Triangular y Exponential están implementadas analíticamente, por
lo que funcionan incluso sin ellas.

## 📊 Tests

**622 tests, 622 verdes** (+31 desde v0.1.32; suite 100 % desde v0.1.21).

Validación contra objetivos **analíticos**, no contra capturas: momentos
teóricos de las siete distribuciones; formas cerradas de la uniforme
(σ = rango/√12) y la triangular (σ = rango/√24); positividad estricta de
la lognormal; respeto de los límites relativos, incluso asimétricos, con
el sesgo esperado; estratificación exacta del LHS (una muestra por
estrato) y su ausencia en Monte Carlo; superioridad del LHS;
reproducibilidad por semilla; independencia entre variables; correlación
alcanzada con marginal intacta; y probabilidad de fallo e índice de
fiabilidad contra casos calculables a mano.

## ⏳ Siguiente

**Fase P1 — variables aleatorias**: modelo de datos que identifique qué
parámetro de qué objeto es aleatorio (material, soporte, carga, sísmico,
freática), aplicación de una muestra a una copia del proyecto,
correlación c–φ por material y serialización en el `.ogr`.

---

© 2026 Samuel Sáez López — UPCT — GPL-3.0
