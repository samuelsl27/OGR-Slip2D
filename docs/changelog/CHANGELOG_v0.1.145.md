# OGR Slip2D v0.1.145

**El defecto decía que el muestreo estrechaba las distribuciones y que por
eso el índice de fiabilidad salía alto. El muestreo es exacto, la
propagación de la varianza es exacta, y la hipótesis se refutaba con
aritmética de bachillerato: un truncamiento a 2,7σ estrecha una normal un
2,1 %, no un 10 %. Lo que estaba mal era QUÉ SUPERFICIE se evaluaba — y el
observable que lo destapó, la dispersión, es justamente el que nadie había
mirado porque es el único que no se deja calibrar con el parámetro libre
del modelo.**

Cierra **D49** del banco de verificación. **No cambia una sola línea de
producción**: el motor estadístico ya hacía lo correcto. Lo que añade son
los dos tests que faltaban y que habrían acortado esto a una tarde.

---

## Qué decía el defecto, y por qué era plausible

Los diez casos del problema 28 del manual de verificación —Congress St.
Cut, Chowdhury & Xu 1995— daban β sistemáticamente alto y PF baja en nueve
de diez. Signo inseguro: el talud parecía más fiable de lo que la
referencia calcula.

El encargo traía una hipótesis con evidencia: tres de las dieciocho
variables aleatorias declaran `rel_min = mean`, es decir truncan la
cohesión en cero, que para c1 del ejemplo 1 cae en **−2,70σ**. Un
truncamiento estrecha una distribución. La medida enseñaba σ un 10 % más
estrecha. Encajaba.

## Lo que la medida dice en realidad

Generadas las dieciocho variables con la semilla y el método reales, la σ
de las muestras reproduce la **forma cerrada de la normal truncada**
(Johnson, Kotz & Balakrishnan 1994, vol. 1, cap. 13) dentro del ruido de
Monte Carlo. El truncamiento se aplica, y se aplica bien. Lo que no cuadra
es cuánto vale:

| truncamiento | σ_truncada / σ_nominal |
|---|---|
| ±3,00σ (quince de las dieciocho) | 0,9866 → **−1,34 %** |
| −2,70σ / +3,00σ (las tres recortadas en cero) | 0,9788 → **−2,12 %** |

Hacía falta un −10 %. Y había un caso que refutaba la hipótesis él solo sin
tocar código: el **ejemplo 2 trunca simétricamente a ±3σ en sus tres
variables** —efecto esperado, −1,3 %— y mostraba −10,8 % y −13,3 %.

## La identidad que cerró la pregunta

En ese problema la arena es c = 0, φ = 0 y las tres arcillas son φ = 0. Con
φ = 0 el m-α de Bishop pierde su dependencia de F y el factor de seguridad
se vuelve **una forma lineal exacta** en las cohesiones — comprobado a
4·10⁻¹⁶ contrastando F(c+2δ) − F(c) contra 2·[F(c+δ) − F(c)].

Eso permite una identidad analítica sin aproximación de primer orden:

    Var[F] = aᵀ Σ a,    a_i = ∂F/∂c_i

Con los a_i por diferencias finitas y Σ la covarianza **realizada** de las
muestras que el motor generó, cierra a **1e-14**. No se pierde dispersión
en ningún punto del módulo estadístico: ni en el muestreador, ni en el
clonado, ni al aplicar la muestra, ni al recorrer las dovelas.

El defecto estaba fuera del programa: en el banco se evaluaba el trío
(centro, radio) que **rotula** la figura en vez del radio de tangencia que
define el enunciado, 0,14–0,19 m menor. Con el radio del enunciado la media
cae dentro del 1,2 % en nueve de diez y σ dentro del 1,8 % en ocho de diez,
sin tocar nada más. Detalle completo en
`_auditoria/D49_DISPERSION_0.1.145.md` del banco.

## Los dos huecos de la suite, que sí eran reales

Que una hipótesis falsa por un factor cinco sobreviviera dos semanas tiene
una causa medible: **nada la contradecía en los tests**.

- `test_statistics_v133` comprueba los **límites** del truncamiento
  —mínimo, máximo, ningún sample perdido, sesgo de la media hacia el tope
  más apretado— pero **nunca su varianza**. El número del que dependía todo
  el diagnóstico no estaba sujeto por nada.
- Y nada comprobaba que la varianza del factor de seguridad fuese la que
  las entradas implican. Esa es la prueba que habría cazado una pérdida
  real de dispersión — que es lo que el defecto afirmaba que ocurría.

`tests/test_statistics_v145.py`, nueve tests:

**Varianza del truncamiento.** Contra la forma cerrada, evaluando el mapeo
sobre una **cuadratura del punto medio** de la función cuantil, u = (i+½)/N,
en vez de sobre una muestra aleatoria. El mapeo bajo prueba es un remapeo
determinista de la CDF inversa, así que la cuadratura converge como O(1/N²)
—1e-7 con N = 20000— mientras que Monte Carlo daría 0,5 % y **no podría
resolver el efecto del 1,3 % que tiene que medir**. Se fijan también las dos
magnitudes de las que dependía el defecto (0,9866 y 0,9788), y hay un
control con los límites a ±12σ, cuya tolerancia es 1e-4 y no 1e-5 por una
razón que conviene tener escrita: pasados unos seis sigma el remapeo es la
cuantil sin truncar, cuya derivada se dispara en u → 0 y u → 1, y la regla
del punto medio pierde su O(1/N²) en las colas.

**Propagación de la varianza.** Sobre el modelo del ejemplo 1 con todos los
ángulos de rozamiento a cero: primero la linealidad exacta —que es la
licencia de la identidad— y después σ² = aᵀΣ̂a a 1e-9, en Monte Carlo, en
hipercubo latino y con una correlación declarada. El círculo se eligió
porque corta los tres materiales con influencias comparables (0,0028 /
0,0046 / 0,0047): uno que rozara una sola capa pasaría la identidad sin
ejercitar jamás los términos cruzados de la covarianza, y hay un test que
guarda esa propiedad de la superficie para que no se pierda en silencio.

## Lo que enseña, más allá del número

**Un parámetro libre absorbe casi cualquier error de la media.** El peso
específico de la arena no lo publica nadie —el manual admite haberlo
elegido para ajustar— y en el banco se recalibró para absorber el error que
introdujo la superficie equivocada. Funcionó, y por eso el error sobrevivió
una versión entera.

La dispersión no se deja: con F = R·Σc·L / ΣW·x, γ entra sólo en el momento
motor y escala μ y σ **por igual**, así que el coeficiente de variación es
exactamente invariante a él. Cuando un modelo tiene un parámetro libre, el
observable que arbitra es el que ese parámetro no puede mover.

Y una segunda, sobre el criterio: el defecto pedía β dentro del ±5 %.
β = (μ−1)/σ divide por un número pequeño — con μ − 1 = 0,063, un 0,5 % de
error en la media es un 8 % en β. **El criterio en β no era un criterio de
dispersión**, que era lo que se estaba investigando.

---

## Verificado

- `tests/test_statistics_v145.py` — 9 de 9.
- Suite completa sin argumentos.
- Banco: los diez casos del problema 28 rehechos (5000 muestras, semilla
  20260819, cero `failed_samples`, 585 s), el determinista rehecho y la
  comparativa regenerada. Ocho de diez pasan a OK; los dos del ejemplo 4
  quedan en REVISAR.
