# OGR Slip2D v0.1.107

**Los dos Janbu dejan de publicar una columna vacía, y por el camino: la
identidad que el encargo daba por buena estaba mal, el desembalse tiraba las
tres columnas de todos los métodos, y un campo significaba dos cosas
distintas según quién lo escribiera.**

El defecto de partida (A44-1 / D11 del banco de verificación) decía que
`LEMResult.base_normal` sólo lo rellenaban `bishop.py` y `ordinary.py`, y que
cinco de los siete métodos dejaban la lista vacía. Se midió en 0.1.97.

Lo primero que se hizo fue volver a medirlo, y el defecto ya no era el que
decía la ficha:

| 0.1.106 — rellenan las tres columnas | la dejan vacía |
|---|---|
| bishop, ordinary, lowe-karafiath, corps #1, corps #2, spencer, gle | **janbu simplificado, janbu corregido** |

La familia de inclinación prescrita entró en 0.1.98 y Spencer y GLE en
0.1.106, al cerrar D10. Quedaban **dos** métodos, no cinco.

---

## 1 · Por qué importaba: el desembalse rápido, medido

No es una columna de adorno. `rapid_drawdown._stage1_state` recupera de ahí el
estado de consolidación de la etapa 1; con la lista vacía el bucle se rompe en
la primera vuelta, el estado sale vacío y el procedimiento de dos etapas
aplica resistencia sin drenar a **cero** dovelas — es decir, vuelve a resolver
la etapa 1 con el embalse bajo y lo llama desembalse.

Medido en el círculo crítico del problema 95 del banco (167,75 · 198,0,
R = 196,24; 50 dovelas; Corps de dos etapas; valor publicado **1,347**):

| | F | dovelas sin drenar |
|---|---|---|
| bishop | 1,3682 | 50 |
| janbu simplificado, **antes** | **1,7625** | **0** |
| janbu simplificado, **ahora** | **1,2177** | **50** |

Un **+31 % del lado inseguro**, en silencio.

## 2 · El arreglo, y de dónde sale la ecuación

Janbu (1954) desprecia el cortante entre dovelas exactamente igual que Bishop
(1955), así que el equilibrio **vertical** de la dovela les da a los dos la
misma expresión para la normal en la base:

    N = [ W − (c'·l·sinα − u·l·tanφ'·sinα)/F ] / m_α ,
    m_α = cos α + s·sin α·tan φ'/F

Lo que cambia es el F al que se evalúa, porque cada método lo obtiene de una
ecuación de equilibrio distinta. El bloque de post-proceso que Bishop tenía
dentro pasa a ser una función de módulo, `base_forces_no_interslice_shear`, y
Janbu la llama. Comprobado bit a bit: Bishop devuelve exactamente los mismos
números antes y después de la extracción.

`slide_sign` es **parámetro** y no se recalcula dentro. Bishop lo saca de
`sign(Σ W(1−kv) sin α)` y Janbu de `sign(Σ W_total tan α)`, y cada uno tiene
que entregar el suyo: `m_α` no es simétrica en α, y leerla en el sentido
equivocado es exactamente la anomalía de v0.1.82.

### Janbu Corregido: con el F corregido, y por qué

`f₀` (Janbu 1973) multiplica el factor de seguridad. Las fuerzas por dovela se
forman **después**, con el factor corregido, para que la normal vaya con el
número que se muestra — es lo que la ventana de interpretación y
`_stage1_state` necesitan, porque los dos combinan `base_normal_force` con
`result.fos`.

El precio está medido y queda escrito: el conjunto de Janbu Corregido **no**
cierra el equilibrio horizontal global que Janbu (1954) resuelve, porque `f₀`
es empírico y no sale de re-resolver nada. Cada dovela sigue cumpliendo su
equilibrio vertical. Hay un test que afirma las dos cosas.

## 3 · Tres premisas del encargo que la medición corrigió

Esto es lo que el changelog existe para registrar.

### (a) La identidad de coherencia propuesta era falsa

El encargo pedía comprobar que `Σ N·cos α` iguala el peso total de la masa,
«en los siete métodos». **Falla por −4,3 a −5,0 %** en los seis que sí
satisfacen el equilibrio vertical de la dovela. La identidad correcta lleva la
componente vertical del cortante movilizado:

    Σ (N·cos α + s·S·sin α) = W_total ,   S = τ_f·l/F

Las componentes verticales de las fuerzas entre dovelas se telescopan a cero
entre los dos extremos libres, así que vale para cualquier hipótesis sobre la
inclinación entre dovelas. Comprobada a 1e-7 con Mohr-Coulomb.

### (b) No vale para todos los métodos, y el que falla no está roto

Fellenius resuelve las fuerzas exteriores **normal a la base** y toma
`N = W·cos α`: nunca escribe el equilibrio vertical de la dovela. Falla por
−3,8 a −4,7 %, y es la razón clásica de que el método sea conservador. El test
lo afirma como **fallo**, para que un cambio que lo hiciera cumplir sin
querer se vea como un test roto y no como una mejora.

Con envolvente **no lineal** el residuo sube a ~0,18 % en todos los métodos, y
tampoco es un defecto: `N` se deriva con la envolvente linealizada en la
tensión de la primera pasada y `τ_f` se reporta con la linealización en el σ′
final. Se comprueba aparte, con esa tolerancia.

### (c) El objetivo «36,3 ± 1 % con Janbu y con Spencer» no era alcanzable, y para Spencer el valor publicado no era ése

El manual publica, para la curva de potencia, σ′max = **36,33 con Janbu
simplificado** y **31,21 con Spencer**; con Mohr-Coulomb, 30,05 y 26,44. Son
dos números distintos porque el cortante entre dovelas mueve el pico.

Medido sobre los dos círculos publicados, 50 dovelas:

| envolvente | Janbu (ahora) | publicado | Spencer (desde 0.1.106) | publicado |
|---|---|---|---|---|
| curva de potencia | 35,66 | 36,33 (**−1,8 %**) | 34,81 | 31,21 (**+11,5 %**) |
| Mohr-Coulomb | 30,42 | 30,05 (**+1,2 %**) | 29,75 | 26,44 (**+12,5 %**) |

El −1,8 % de Janbu es del tamaño del −1,4 % que su **factor de seguridad** ya
tiene en ese mismo círculo: la tensión no puede acertar mejor que el factor
del que sale. El test se cierra en ±3 % y dice por qué; apretarlo a ±1 %
sería fijar una discrepancia que este cambio no causó.

El **+11 a +12 % de Spencer** es un hallazgo nuevo, mayor que su desviación en
factor de seguridad (−3,6 %) y no atribuible al mallado: σ′max varía menos del
0,1 % entre 15 y 150 dovelas. Visto como cociente contra Janbu sobre el mismo
círculo es más claro todavía: el manual da σ′max(Janbu)/σ′max(Spencer) = 1,164
y 1,137 en las dos envolventes, y OGR da 1,024 y 1,023. El cortante entre
dovelas baja el pico un 14 % allí y un 2 % aquí. Queda registrado como
anomalía en el banco. **No se ha tocado Spencer.**

Y una segunda medida, que **no lo confirma** y por eso se escribe: otro problema
del mismo autor publica σ′max para los dos métodos y tres escenarios, pero **sin
sus círculos críticos**. Comparando cada método sobre el suyo, las seis tensiones
salen de −4 a −19 % por debajo de lo publicado — Spencer incluido — con los
seis factores de seguridad dentro del ±1,4 %. En superficies distintas, así que
las dos medidas no se contradicen; lo que dicen juntas es que σ′max depende
mucho de qué círculo se toma (aquí mismo, Janbu da 35,66 sobre el círculo
publicado y 37,38 sobre el que encuentra la búsqueda: 4,8 % sólo por eso) y que
comparar esta magnitud sobre una superficie encontrada por uno mismo es
evidencia débil. El propio Baker publica 21,4 donde el manual publica 31,21 para
el mismo caso: un 46 % entre dos fuentes.

## 4 · `base_normal` → `base_normal_force`

El campo guarda una **fuerza** en kN/m, no una tensión. Leer
`max(base_normal)` como si fueran kPa da un número unas cuatro veces menor y
lo bastante plausible como para pasar desapercibido: estuvo mal en dos fichas
del banco hasta que una tercera, que sí publica la tensión, lo delató (fuerza
7,69; tensión 36,46; publicado 36,33).

- `base_normal_force` es el nombre nuevo, y también la clave de `to_dict()`.
- `base_normal` sobrevive como **propiedad de sólo lectura**, porque hay
  herramientas fuera de este repositorio que preguntan por ese nombre.
- El *docstring* del dataclass dice ahora que **las tres listas son fuerzas**,
  `base_shear_strength` incluida: se llama *strength* y vale `τ_f·l`.

## 5 · `base_shear_force` significaba dos cosas

Encontrado al decidir qué tenía que escribir Janbu en ese campo, y no había
una respuesta: dependía del método.

| | qué guardaba, dovela 10 de la misma superficie |
|---|---|
| bishop, ordinary, (janbu) | fuerza motora `W·sin α` = **2,58** |
| corps #1, corps #2, lowe-karafiath, spencer, gle | cortante **movilizado** = **41,0** |

Y la ventana de interpretación rotula esa fila «Driving shear W·sinα (kN)»
para los nueve. O sea que en cinco métodos imprimía el movilizado bajo un
rótulo de motor, con un factor 16 de diferencia.

Unificado a la **fuerza motora** en los nueve, que es lo que dice el rótulo y
lo que ya fijaba el test validado contra la tabla de datos por dovela de la
referencia. El movilizado no se pierde: es exactamente
`base_shear_strength / fos`, que es lo que el panel divide para su propia fila
«Mobilised shear τ_m». Ordinary conserva su brazo geométrico (v0.1.100), que
difiere de `sin α` en menos de un 0,1 % en círculo y es el brazo del que sale
su propio factor de seguridad; el test le da esa holgura y ninguna más.

## 6 · El desembalse multietapa tiraba las tres columnas — con todos los métodos

`MultiStageDrawdownMethod.compute_fos` construía un `LEMResult` nuevo **sin**
las tres listas y con las dovelas de la **etapa 1**. Consecuencias, ninguna
exclusiva de Janbu:

- la ventana de interpretación salía vacía en cualquier desembalse, Bishop
  incluido (por eso el problema 95 escribía `sigma_n_max: null` hasta con
  Bishop, que sí rellena la normal);
- `checks.base_effective_stresses` recalculaba la normal con las dovelas de la
  etapa 1 y el factor de seguridad de la etapa 2 — dos estados distintos en la
  misma expresión.

Ahora `DrawdownResult` lleva el `LEMResult` de la etapa que **produjo el
factor devuelto**, y el envoltorio copia de ahí las tres columnas y el
rebanado. Dos cuidados que valen más que el arreglo:

- `res.fos = min(fos_stage2, fos_stage3)`, así que las columnas salen de la
  etapa que ganó. Publicar la normal de una etapa junto al factor de otra
  sería peor que no publicar ninguna.
- Cuando la iteración del tope drenado **no converge**, el factor que se
  reporta es el CENTRO de su ciclo (v0.1.71), que ningún paso calculó. En ese
  caso no se adjuntan columnas, a propósito.

Efecto secundario **buscado**: el resultado de un desembalse lleva ahora el
rebanado de la etapa 2, que tiene un corte que la etapa 1 no tiene (el del
nivel bajado). Los veredictos de la comprobación de tracción en un desembalse
se mueven; es una corrección, no un daño colateral.

---

## 7 · Qué se probó

`tests/test_janbu_base_forces_v1107.py`, 20 tests. Los anclajes, ninguno una
captura de lo que imprime el código hoy:

1. **Equilibrio vertical de cada dovela** — identidad analítica, exacta a 1e-6
   con Mohr-Coulomb, para los dos Janbu y para Bishop.
2. **Equilibrio horizontal global** — la ecuación que Janbu simplificado *es*.
   Residuo 0,015 sobre fuerzas de orden 1300 en Janbu; **−97,4 en Bishop**,
   que satisface momentos y no fuerzas. Ese contraste es lo que impide que el
   anclaje 1 sea una tautología: una normal copiada de un método de momentos
   lo suspendería.
3. **σ′max publicado** de Baker (2003) ej. 3, las dos envolventes, ±3 %.
4. **Equilibrio vertical global** en los ocho métodos que lo escriben, con
   Fellenius excluido y afirmado como excepción.
5. `base_shear_force` es la fuerza motora en los nueve, y en la dovela más
   tumbada el movilizado la supera 16 veces — la distinción no es de redondeo.
6. El alias `base_normal` sigue respondiendo.
7. **Regla 7**: con desembalse de dos etapas, Janbu ya alcanza la etapa 2 y el
   resultado lleva sus columnas y su rebanado.

Suite completa, sin argumentos, en verde.

### Qué queda sin probar

- El **+11 % de Spencer** en σ′max no tiene test: está registrado como
  anomalía abierta, no como comportamiento aceptado.
- El desembalse con **Janbu Corregido** no se ha contrastado con ningún valor
  publicado; ninguna referencia de las que hay aquí lo publica.
- Las fuerzas de sostenimiento siguen sin entrar en la normal reportada, en
  Janbu igual que en Bishop. Limitación heredada, ahora escrita en el
  *docstring* de la función compartida.
