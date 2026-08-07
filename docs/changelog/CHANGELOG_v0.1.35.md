# OGR Suite v0.1.35 — Changelog

**Lanzamiento:** 2 de agosto de 2026
**Desarrollador:** Samuel Sáez López — Estudiante de Doctorado, UPCT
**Licencia:** GPL-3.0

> **Fase P2: motor probabilístico Global Minimum.** El análisis
> probabilístico ya funciona de principio a fin desde el motor: se
> localiza la superficie crítica determinista, se repite el cálculo N
> veces con las muestras generadas, y se obtienen probabilidad de fallo e
> índice de fiabilidad.

---

## 🆕 `ogr_core/statistics/probabilistic.py`

Implementa el tipo **Global Minimum** tal como lo define la referencia:

1. Se ejecuta primero el análisis **determinista** para localizar la
   superficie de factor de seguridad mínimo global.
2. El análisis probabilístico se realiza **sobre esa superficie**,
   repitiendo el cálculo N veces con las muestras de cada variable
   aleatoria.
3. La **probabilidad de fallo** es el número de muestras con FS < 1
   dividido entre N.

**Un punto que la referencia subraya y que se respeta**: cada método de
análisis puede dar una superficie crítica distinta, así que la corrida
probabilística se hace **independientemente sobre la crítica de cada
método** solicitado.

Cada muestra se evalúa sobre un **clon** del proyecto (Fase P1), de modo
que el modelo del usuario nunca se modifica — verificado en un test que
compara la serialización completa antes y después.

**Muestras no evaluables.** Una combinación extrema de parámetros puede
hacer que la superficie no se resuelva. En vez de descartarlas en
silencio, se **cuentan aparte** (`failed_samples`) y se emite un aviso si
superan el 20 %, porque un recuento alto significa que los rangos
declarados no son realistas.

## 📤 Resultados

Por método: factor de seguridad determinista, superficie analizada, y los
estadísticos completos — media, desviación, mínimo, máximo,
**probabilidad de fallo**, **índice de fiabilidad** normal y lognormal,
histograma y datos de convergencia (los que la referencia usa para
decidir cuántas muestras hacen falta).

Ejemplo real (caso de referencia, 300 muestras LHS, c y φ correlacionadas
a −0.5, en 3.8 s):

| Método | Determinista | Media | Desv. | PF | Índice fiab. |
|---|---|---|---|---|---|
| Bishop | 0.9014 | 0.9047 | 0.0919 | 0.850 | −1.037 |
| Spencer | 0.9013 | 0.9045 | 0.0921 | 0.850 | −1.037 |

La media reproduce el valor determinista (las variables están centradas
en sus medias) y el índice de fiabilidad es comprobable a mano:
(0.9047 − 1)/0.0919 = −1.037.

## 📊 Tests

**665 tests, 665 verdes** (+17 desde v0.1.34; suite 100 % desde v0.1.21).

Validación **contra cálculos independientes**, no contra capturas:

- **Recomputación manual muestra a muestra**: se repite el mismo
  muestreo por fuera del motor, se evalúa cada clon a mano y se exige
  coincidencia exacta con los factores que devolvió el motor.
- La probabilidad de fallo debe igualar la fracción contada por debajo
  de 1, y el índice de fiabilidad la fórmula (media − 1)/σ.
- La media debe quedar próxima al valor determinista cuando las
  variables están centradas.
- El proyecto del usuario debe quedar **idéntico** tras la corrida
  (comparación de la serialización completa).
- Cada método conserva **su propia** superficie crítica.
- Una variable sísmica debe **bajar** la media.
- Errores: sin variables aleatorias, sin resultado determinista, muestras
  fallidas contabilizadas, y callback de progreso que termina al 100 %.
- Convergencia que acaba en N con la media y la PF finales, e histograma
  que suma todas las muestras.

## ⏳ Siguiente

**Fase P4 — análisis de sensibilidad**: barrido de una variable cada vez
entre su mínimo y su máximo, con las demás en su media, produciendo
curvas FoS–parámetro y una ordenación por influencia. Después P3
(Overall Slope) y P5 (interfaz).

---

© 2026 Samuel Sáez López — UPCT — GPL-3.0
