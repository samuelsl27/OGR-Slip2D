# OGR Slip2D v0.1.64 — el refuerzo llega a los siete métodos, y con signo

Tercera fase de la deuda de v0.1.61. La deuda decía *"los soportes solo los
integra Bishop"*. Era cierto, y resultó ser la mitad menos grave del
problema: **la única integración que existía estaba mal en tres cosas
distintas**, y las tres se midieron antes de tocar nada.

---

## Lo que se encontró antes de cambiar (regla 6)

Mismo talud, mismo bulón cortando la dovela 13 (α = 25.9°, |F| = 133.3
kN/m), FoS sin soporte = **1.552535**.

### 1. La orientación no podía empeorar el resultado

| Ángulo | proyección tangencial | FoS |
|---:|---:|---:|
| 0° | −119.971 | 2.496110 |
| 180° | +119.971 | **2.496110** |
| 45° | −125.971 | 2.542087 |
| 225° | +125.971 | **2.542087** |
| 90° | −58.179 | 2.017468 |
| 270° | +58.179 | **2.017468** |

`numerator += abs(proj_tangent)` hacía el factor de seguridad **exactamente
simétrico** al girar el soporte 180°. Un tirante empujando la masa
pendiente abajo mejoraba el talud lo mismo que uno sujetándola. No era
ruido de redondeo: eran los mismos dígitos.

### 2. La componente normal no existía

| Orientación | T_tangencial | T_normal | FoS |
|---|---:|---:|---:|
| Tangente | −133.333 | +0.006 | 2.598405 (+67 %) |
| Normal a la base | +0.006 | +133.333 | 1.552583 (**+0.003 %**) |

Un bulón perpendicular a la superficie con 133 kN/m movía el FS un
0.003 %, que es el residuo de una fuga tangencial de 0.006. Su aportación
entera es `T_N·tanφ'`, y ese término no estaba escrito en ningún sitio.

### 3. Activo y Pasivo eran el mismo número

```
Activo  FoS = 2.598405203
Pasivo  FoS = 2.598405203
diferencia  = 0.000e+00
```

Bit a bit. Las ecuaciones publicadas dan
`F_act = (R + T_N·tanφ')/(D − T_S)` y `F_pas = (R + T_N·tanφ' + T_S)/D`, de
donde **Pasivo ≤ Activo siempre**, con igualdad solo si `T_S = 0`.

**Una corrección al propio informe**: al derivar el convenio de signos para
implementarlo se vio que la orientación probada en la anomalía 2 (tangente
+ 90°) **levanta** la dovela en vez de apretarla, así que debería *bajar* el
FS. La anomalía es la misma —la componente normal no aportaba nada en
ningún sentido— pero el signo que se le atribuyó en la primera lectura
estaba al revés. Queda anotado porque el error de signo es exactamente el
tipo de cosa que este proyecto no se puede permitir dar por buena.

---

## Lo que hace ahora

### `resolve_support_terms`, el sitio único donde el soporte se resuelve

Convierte los `SupportEffect` en las cantidades que las ecuaciones
necesitan, **con su signo**:

- **Tangente descendente**: `t_d = −slide_sign·(cos α, sin α)`. Es el
  vector que hace que el peso `(0, −W)` produzca el término motor
  `+slide_sign·W·sin α` que todos los métodos ya usaban, así que no
  introduce un convenio nuevo: hereda el que había. La componente
  resistente de una fuerza **F** es `−F·t_d`.
- **Normal interior**: `n = (−sin α, cos α)`. Una fuerza aprieta la dovela
  contra su base en `−F·n`. Un bulón perpendicular apuntando hacia dentro
  del talud aprieta (positivo); uno apuntando hacia fuera levanta
  (negativo). Ese signo es justo el que `abs()` no podía expresar.
- **Componente horizontal resistente**, `+slide_sign·F_h`, para los métodos
  cuyo equilibrio es de **fuerzas horizontales** y no de momentos.

Ese último punto no es cosmético. Janbu equilibra `Σ W·tan α + Σ kh·W`, una
suma de fuerzas horizontales; proyectar ahí el soporte sobre la tangente de
la base habría sido mezclar dos balances distintos.

### Dos tratamientos, porque hay dos clases de método

**Métodos de cociente** (Ordinary/Fellenius, Bishop, Janbu simplificado y
corregido) — formulación de la referencia:

```
F_act = (R + T_N·tanφ') / (D − T_S)
F_pas = (R + T_N·tanφ' + T_S) / D
```

**Métodos de equilibrio completo** (Spencer, GLE/Morgenstern-Price,
Lowe-Karafiath) — el soporte entra como **fuerza externa sobre la dovela**:
su componente vertical se suma a la carga que la base soporta y la
horizontal al balance horizontal, junto al empuje de agua que v0.1.61 ya
había abierto por esa vía. Es lo que un método que promete equilibrio
completo exige, y se paga solo: **`T_N·tanφ' sale del equilibrio**, no hay
que añadirlo a mano como en Bishop.

Consecuencia deliberada: en los tres rigurosos **Activo y Pasivo dan el
mismo número**, y el test lo exige en vez de dejarlo al azar. La distinción
es un artefacto de escribir el FS como cociente; un método que resuelve
equilibrio ve una fuerza, y una fuerza no lleva esa etiqueta. La propia
referencia admite que la elección es "en parte arbitraria".

### La guarda que sustituye al `abs()`

El comentario de v0.1.15 tenía razón en una cosa: con `D − T_S` en el
denominador, un refuerzo suficientemente grande anula el denominador y el
FS se dispara o se vuelve negativo. Descartar el signo lo evitaba al precio
de hacer el modelo ciego a la orientación.

Ahora, si `D − T_S ≤ 0`, la superficie se marca **inadmisible** con su
nota, reutilizando el mecanismo de v0.1.32: sigue en la lista de
evaluaciones —los algoritmos de búsqueda necesitan la señal— pero queda
fuera de la elección de superficie crítica. Y el resultado lleva
`details["active_support_ratio"]`, la fracción del empuje motor que los
soportes activos se han llevado. **Se informa, no se juzga**: según `T_S`
se acerca a `D` el FS crece sin límite, lo cual es aritméticamente correcto
y físicamente vacío, y no hay ningún umbral entre las dos cosas que se
pueda defender lo bastante como para grabarlo en el código.

### Una elección de modelo que conviene tener escrita

`T_N·tanφ'` se suma **fuera** de la normalización `m_α` (Bishop) y `n_α`
(Janbu), que es como la referencia escribe la ecuación. `m_α` sale de
resolver el equilibrio vertical de la dovela para `N` bajo su propio peso,
mientras que la referencia trata el soporte como una fuerza aplicada
directamente a la base. Plegarlo en el equilibrio vertical dividiría también
este término por `m_α`. La diferencia es de segundo orden para las bases
casi horizontales habituales, pero es una decisión de modelo y no un
detalle, así que está comentada en el código y anotada aquí.

Los tres métodos rigurosos **no** tienen esta ambigüedad, precisamente
porque ahí el soporte sí entra en el equilibrio.

---

## Resultado

Un bulón modesto sobre el mismo talud:

| Método | sin soporte | Pasivo | Activo |
|---|---:|---:|---:|
| Ordinary/Fellenius | 1.52918 | +4.79 % | +7.90 % |
| Bishop simplificado | 1.55254 | +5.25 % | +8.83 % |
| Janbu simplificado | 1.51561 | +4.18 % | +6.75 % |
| Janbu corregido | 1.57314 | +4.18 % | +6.75 % |
| Spencer | 1.55248 | +7.93 % | +7.93 % |
| GLE/Morgenstern-Price | 1.55251 | +7.94 % | +7.94 % |
| Lowe-Karafiath | 1.55867 | +7.84 % | +7.84 % |

Antes, las seis últimas filas habrían dado +0.00 % sin decir nada.

---

## Qué se probó

Fichero nuevo `tests/test_supports_all_methods_v164.py`, 13 tests.

**El problema del anclaje.** No hay en el proyecto ningún caso publicado
con refuerzo, así que no se podía comparar contra un factor de seguridad
conocido. Los anclajes que sí se pueden defender:

- **Forma cerrada.** Ordinary/Fellenius es un cociente llano `ΣR/ΣD`, y un
  soporte puramente normal añade exactamente `T_N·tanφ'` a `ΣR` y nada a
  `ΣD`. El FS nuevo tiene que ser `F₀·(1 + T_N·tanφ'/ΣR)`, con `ΣR` leído
  del resultado sin refuerzo, que ya publica ambas sumas por dovela.
  Comprobado al 1e-6 relativo.
- **Identidad de las ecuaciones publicadas.** `Pasivo < Activo` en los
  tres métodos de cociente.
- **Consistencia entre métodos.** Spencer, GLE y Lowe-Karafiath son tres
  formulaciones independientes del equilibrio completo: tienen que caer en
  el mismo número, con refuerzo y sin él. Coinciden dentro del 1 %, y la
  *ganancia* que produce el bulón coincide entre los tres dentro del 0.5 %.
  Se usan mutuamente de referencia.
- **El test más barato y el que más pega.** Un soporte que **no corta** la
  superficie de rotura tiene que ser inerte en los siete métodos, al bit.
  Un término sumado en el lado equivocado de una ecuación salta ahí sin
  necesidad de conocer ningún valor.
- **Regresiones de las tres anomalías.** Girar el soporte 180° ya no es una
  simetría; apretar sube el FS y levantar lo baja; y el activo supera al
  pasivo.
- **La guarda.** Un soporte activo desmesurado marca la superficie
  inadmisible con nota, en vez de devolver un número absurdo; uno modesto
  sigue siendo admisible con `0 < active_support_ratio < 1`.

Suite completa en verde. Se comprobaron aparte el retroanálisis
(`test_back_analysis_v140`), el test de integración de soportes que ya
existía (`test_supports_v114`, que solo exigía una mejora >5 % con soportes
bien orientados y sigue pasándola) y los casos de validación LEM, que no
llevan refuerzo y no se mueven.

## Coste, y una lección sobre cómo medirlo

`resolve_support_terms` se llama ahora desde **los siete métodos** en
**cada** superficie de prueba, y la primera versión reservaba ocho listas
por dovela antes de comprobar si había algún soporte. La mayoría de los
modelos —y toda la suite de validación— no tienen ninguno, así que ese caso
tenía que salir gratis: la comprobación se hace **antes** de reservar nada
y devuelve una instancia compartida vacía, cuyos `total_*` dan 0.0 sin caso
especial porque suman sobre listas vacías.

La mejora es real y grande en la función: **3.465 µs → 0.211 µs**, un
factor 16. Y es **irrelevante** en el conjunto: se llama una vez por
`compute_fos`, no una vez por dovela, así que son 3 µs sobre los 809 µs que
tarda Bishop — un 0.4 %.

Merece la pena escribirlo porque casi se cuela lo contrario. El reloj de la
suite completa dio 5:55, 6:19 y 6:41 en corridas del **mismo** código en
esta máquina: **±40 s de ruido**, un ±8 %. Con esa señal no se puede
atribuir nada, y la corrida posterior a la optimización salió *más lenta*
que la anterior. Las cifras de v0.1.63 (rebanado: 0.51 ms una capa,
1.91 ms multicapa) se midieron en bucles calientes con miles de
repeticiones y sí son fiables; el tiempo total de la suite, para
diferencias por debajo del 10 %, no lo es. Para la fase 5 —el reparto de
dovelas, que es la que puede encarecer de verdad— hay que medir con bucle
caliente sobre `slice_surface`, no con el cronómetro de la suite.

## Lo que queda

Fases 4 a 6: embalse derivado de las condiciones de contorno de altura
total, reparto de dovelas en las intersecciones, y el descenso rápido
multietapa —que sigue bloqueado hasta obtener las ecuaciones de conversión
entre la envolvente R y la Kc = 1 de su fuente original.
