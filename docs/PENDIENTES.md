# Pendientes abiertos

Lo que quedó sin cerrar y **por qué**, para que no se pierda entre
changelogs. Cada entrada dice qué falta exactamente y qué haría falta para
cerrarla. Se borra la entrada cuando se cierra, no se marca.

Origen: trabajo sobre los ejemplos Ej_1 y Ej_2 de `referencias/Ejemplos/`
(v0.1.84 en adelante).

---

## 1 · La regla de radios del Grid Search — CERRADO en v0.1.88

La medición que faltaba se ejecutó
(`referencias/Ejemplos/00_2026_08_17_Test_Regla_radios`) y la regla quedó
despejada por lectura directa de los `.s01`, sin ajustar nada. Derivación,
comprobación sobre 949 centros y tablas en
`docs/audits/grid_radius_rule_v188.md`.

Queda **una** pieza sin medir, y sólo ésa: en los seis modelos los Slope
Limits están en su posición automática, así que los datos no distinguen si
`d_max` se mide a los *puntos límite* o a los *extremos del perfil*, ni si
`d_min` se mide sobre el perfil recortado o el completo. Se implementó la
lectura documentada.

### CERRADO en v0.1.92

Los modelos con los Slope Limits metidos a x = 20/100 (Ej_1) y −20/85 (Ej_2)
—abscisas que no son vértices del perfil— distinguen por fin las lecturas:
`d_max` se mide **a los puntos límite** (5·10⁻¹⁴), no a los extremos del perfil
(error de 10,0 m y 23,5 m). Lo implementado desde v0.1.88 era lo correcto.

Sigue sin distinguirse, y se dice: si `d_min` se mide sobre el perfil recortado
o el completo. En esas rejillas el punto más cercano cae dentro de los límites
en todos los centros, así que las dos lecturas dan idéntico.

`AutoRefineSearch` **queda arreglado** con esa misma medición: recortaba los
límites filtrando vértices y ahora interpola, como `GridSearch`.

### Decisión tomada en v0.1.88 que conviene revisar: `min_radius = 0`

El predeterminado pasó de 2,0 a **0,0** en `GridSearch` y de 3,0 a 0,0 en
`analysis_runner.build_search`, para que la configuración de fábrica —la que
usan la interfaz y la CLI— muestree **exactamente** la población de la
referencia. La referencia no tiene control de radio mínimo; ofrece *Minimum
Elevation* y *Minimum Depth*.

Está medido que no cambia ningún resultado: con 3,0 y con 0,0 el factor de
seguridad de los cinco casos publicados es idéntico, y sólo se mueven los
recuentos de válidas en unas unidades.

**Lo que queda por decidir es de producto, no de cálculo**: si un usuario de la
interfaz se beneficia de un suelo de 3 m que le ahorre círculos diminutos, o si
vale más que la interfaz reproduzca la referencia sin excepciones. Se eligió lo
segundo. Cambiarlo es una línea en cada sitio; si se cambia, hay que decir en
la documentación que la interfaz **no** reproduce el muestreo de la referencia.

---

## 0a · GLE bajo Simulated Annealing — CERRADO en v0.1.90

No era el rebanador de v0.1.89 y no era el recocido: era el **rango de λ**,
cortado en ±1,5 mientras la raíz de esas superficies está en λ ≈ 3. Medido,
arreglado y validado por tres caminos en v0.1.90. Ver
`docs/audits/spencer_gle_interslice_v179.md`.

---

## 0 · Simulated Annealing converge peor que un círculo

**Estado**: reportado con medidas, sin corregir. Regla 6.

Sobre un talud cuyo mínimo **circular** es 1,1239, SA devuelve **1,6564**. Una
búsqueda no circular no puede hacerlo peor que un círculo: los círculos están,
salvo discretización, en su espacio de búsqueda. Block Search, sobre el mismo
modelo, da 1,13-1,16 — dentro de la discretización. SA se va un 47 %.

### Corrección de lo que decía esta entrada en v0.1.89

Decía que `generation_steps` «deja de hacer nada». **Estaba mal medido**, y el
mecanismo real apunta a otro sitio. Instrumentado (`search.py:2686-2687` y
`:2767`):

```python
K     = max(4,  int(self.generation_steps / 50))   # pasadas externas
Ngen0 = max(20, self.generation_steps // K)        # bucle interno
Ngen  = max(10, Ngen0 // (2 ** (k - 1)))           # se HALVA cada pasada
if no_improve_passes >= 3: break                   # parada
```

| `generation_steps` | K | Ngen0 | Σ Ngen nominal | **evaluadas de verdad** | FoS |
|---|---|---|---|---|---|
| 50 | 4 | 20 | 50 | 151 | 1,7491 |
| 300 | 6 | **50** | 117 | 459 | 2,1854 |
| 1 000 | 20 | **50** | 257 | **462** | 1,6564 |
| 3 000 | 60 | **50** | 657 | **462** | 1,6564 |

Tres cosas, y ninguna es «el ajuste se ignora»:

1. `K = generation_steps/50` hace que `Ngen0 = generation_steps // K` sea
   **50 siempre** para `generation_steps ≥ 200`. El ajuste no controla el
   tamaño del bucle interno; sólo añade pasadas externas.
2. `Ngen` se halva cada pasada hasta un suelo de 10, así que las pasadas de
   temperatura baja —donde el recocido debería explotar el óptimo— exploran
   con diez propuestas.
3. La parada a las 3 pasadas sin mejorar congela el total en 462 evaluaciones,
   así que de 1000 en adelante el ajuste es inerte **por la parada**, no por
   la fórmula.

### Los parámetros de la referencia, que ahora sí se conocen

De sus propios modelos (`simulatedannealing search` en el `.sli`):

| | referencia | OGR |
|---|---|---|
| `ngen` (estados generados por temperatura) | **1000** | 50 (fijo) |
| `nepsilon` (pasadas sin mejora antes de parar) | **5** | 3 |
| `ftol` | **0,0001** | `tolerance` 1e-3 |
| `c` (enfriamiento) | 8 | 8 ✔ |
| `nvertices` | 8 | 9 por defecto |

Eso convierte esta entrada de «investigar» en «cambiar exactamente esto». No
se hizo en v0.1.90 porque cambia coste y resultados en toda la suite y **no
hay referencia externa para el resultado de una búsqueda no circular** — lo
dice `validacion/casos/004-arai-tagyo-1985-ej1/caso.md`. Merece su propia
versión con su propio triaje.

Qué haría falta además: el mínimo **no circular** publicado de Yamagami y Ueta
(1988) o del reanálisis de Greco (1996), cuyo talud ya está en
`validacion/casos/002-yamagami-ueta-1988/` con coordenadas rotuladas. Con ese
número, las búsquedas no circulares tendrían por primera vez una referencia
externa en vez de una identidad interna.

Relacionado: `test_annealing_bootstrap_v139.py` documenta que el arranque de
SA dependía de la suerte (200 rechazos consecutivos con semillas
desafortunadas).

---

## 2 · La geometría degenerada — CERRADO en v0.1.89

Eran **nueve** contornos en siete archivos, no cinco: la lista de aquí estaba
hecha a mano y se había quedado corta. El inventario se toma ahora con
`ogr_core.geometry.zero_thickness_spans()` ejecutando la suite con
`Project.add_boundary` instrumentado, que no se puede quedar obsoleto.

Lo que tapaba está en el changelog de v0.1.89 y en los pendientes 0 y 0a de
este documento.

Queda una limitación dicha: el detector **no impide** que un archivo nuevo
reintroduzca el contorno. Haría falta que todos los modelos de test pasaran por
una fábrica única.

---

## 3 · El panel de dovelas — CERRADO en v0.1.91

Los tres botones (Copy, Zoom Slice, Hide/Show Geometry) y las fuerzas entre
dovelas, dibujadas **sólo** cuando el método publica `boundary_ratios` y
declaradas en palabras cuando no. Detalle en el changelog de v0.1.91.

Se abre uno nuevo de paso: **OGR no tiene «analizar exactamente esta
superficie»**, lo que la referencia llama *Add Surface*. Las superficies no
circulares de referencia sólo se pueden evaluar por programa, no desde la
interfaz. Ver `referencias/Ejemplos/README.md`.

---

## 4 · Diagnóstico fuera del runner — CERRADO en v0.1.89

Explicado, comprobado con un señuelo y con guarda: `pip install -e .` registra
un buscador que resuelve todo `ogr_*` a una ruta absoluta fija, y
`sys.path[0]` es el directorio **del script**, no el de trabajo. El runner
imprime ahora la procedencia y se niega a correr sobre otro árbol. Detalle en
el changelog de v0.1.89.

---

## 5 · Arrastrar un contorno entero rompe — ABIERTO (v0.1.93)

`ogr_gui/canvas/canvas_view.py:1966-1968` asigna sobre un `Vertex`, que es un
`@dataclass(frozen=True, slots=True)`:

```python
for vi, v in enumerate(b.polyline.vertices):
    v.x = ox0 + dx
    v.y = oy0 + dy
```

Reproducido: `FrozenInstanceError: cannot assign to field 'x'`. Es decir, el
arrastre de un contorno completo lanza al primer movimiento del ratón.

Apareció escribiendo el test de invalidación in situ de v0.1.93 —que intentó
editar así porque el comentario del lienzo dice que así se edita— y se dejó
sin tocar según la regla 6. **Falta por averiguar**: desde qué versión, qué
modos de herramienta llegan a ese bloque (`_dragging_boundary` se arma en
algún sitio que hay que localizar), y por qué ningún test de la interfaz lo
cubre. El arreglo previsible es reemplazar la lista
(`b.polyline.vertices[vi] = Vertex(...)`), que es como edita el resto del
código, pero **no se toca sin saber antes por qué nadie lo notó**: si el
bloque fuera inalcanzable, el arreglo sería un parche sobre código muerto.

## 9 · La rama de fuerzas de Spencer y GLE llevaba cos α donde va sec α — CERRADO en v0.1.106

Era correcto, y era **una de tres**. Entró en v0.1.106 junto con las otras dos,
porque arreglar ésta sola no habría movido el factor de seguridad: `F_m` seguía
sin depender de λ, así que la raíz `F_f = F_m` habría vuelto a aterrizar sobre
Bishop. Ver `docs/audits/spencer_gle_interslice_v179.md`, apartado v0.1.106.

**Y corrige un diagnóstico que este mismo apartado dejó a medias.** Decía que la
otra mitad de D10 —`F_m(0)/Bishop` corto un 2-4 %— «sigue en pie y es
independiente». Lo primero era cierto; lo segundo no tenía la causa que D10 le
atribuía. No era `m_α` sin λ: en λ = 0 no hay cortante interdovela y `m_α` sin λ
**es** la expresión correcta ahí. Era que las dos ramas compartían un solo
iterado `F = (F_f + F_m)/2`, de modo que ninguna era su propio punto fijo.
Separadas, `F_m(0)` sale exactamente Bishop a ocho cifras.

## 8 · La carga de vuelta del paralelismo — ABIERTO (v0.1.97)

**Estado: medido, con el camino identificado.** La búsqueda en paralelo da
1,5-2× cuando el techo con transferencia cero sería 3,0×.

Instrumentado sobre Lowe-Karafiath, rejilla completa, 7 procesos, 56 lotes:

| | wall | paralelismo efectivo |
|---|---|---|
| **sin** devolver las evaluaciones | **11,79 s** | 6,30× |
| devolviendo todo | 18,05 s | 6,39× |

El reparto funciona: 6,3× de paralelismo efectivo, sin desequilibrio de carga
que arreglar (se probó afinar los lotes de 7 a 56 y dio 1,85× → 1,84 %, nada).
Lo que cuesta el 35 % del reloj es **deserializar ~30 MB de `LEMResult` en el
proceso padre**, cada uno con sus 25 dovelas y sus referencias a materiales, y
ese trabajo es **serie**.

**Qué haría falta**: que los workers devuelvan un resumen compacto por círculo
—centro, radio, FoS, convergencia, admisibilidad, motivo— y que el padre
reconstruya por su cuenta sólo las superficies que se van a enseñar.

**Por qué no se hizo ya**: cambia *qué recibe la ventana de interpretación* de
una búsqueda. Antes de tocarlo hay que saber **quién recorre `evaluations`
esperando encontrar dovelas**: el panel de dovelas, las consultas fijadas, los
mapas de calor de la rejilla y la exportación. Si alguno las necesita para toda
la población y no sólo para la superficie consultada, el resumen no vale y hay
que rebanar bajo demanda.

Relacionado: sólo Grid Search se paraleliza. Las aleatorias (SA, Path, Block)
necesitan semilla derivada por lote para no romper la reproducibilidad de
v0.1.74, y Auto Refine encadena iteraciones.

---

## 7 · Lowe-Karafiath con agua: ¿empuje entre dovelas, sí o no? — ABIERTO (v0.1.94)

**Estado: diagnosticado y medido, sin corregir. Regla 6.** Falta UN dato
externo, y está identificado exactamente.

Sobre `Ej_2_Piezometric_Line`, círculo crítico de la referencia, Lowe-Karafiath
da **−10,89 %**. La causa está localizada: `interslice_water_thrust`
(`ogr_slip2d/external_forces.py`), que usa **sólo** este método. Integra u sobre
las caras verticales entre dovelas y la aplica como fuerza externa, con lo que
la `Z` de la recursión pasa a ser la fuerza interdovela **efectiva** en vez de
la **total**.

```
con el empuje (hoy)     0,626915    −10,89 %
sin el empuje           0,704139     +0,09 %
referencia              0,703504
```

**Y quitarlo rompe un caso publicado.** Verificación #70 de Duncan y Wright
(talud sumergido, árbitro 1,60):

| | ponded 75 | ponded 105 | boyante | invarianza |
|---|---|---|---|---|
| Bishop / Spencer / GLE | 1,6006 | 1,6006 | 1,6003 | 0,00 % |
| **Lowe CON empuje** | 1,6092 | 1,6099 | 1,6081 | 0,05 % ✔ |
| **Lowe SIN empuje** | **5,0000** | **0,2203** | 1,6081 | **95,6 %** ✘ |

Se pierde la magnitud **y** la invarianza con la profundidad del agua, que es
el invariante fuerte del caso. `test_ponded_water_v161.py` la exige dentro del
1 % y del 2 %, así que borrar el término deja la suite en rojo — como debe.

Las dos formulaciones son consistentes consigo mismas. Difieren en si la
inclinación prescrita θ = ½(β+α) se aplica a la fuerza interdovela **total** o
a la **efectiva**. Ninguna acierta en los dos casos.

### El dato externo apareció en v0.1.98, y no basta

Buscando la fuente de los métodos Corps of Engineers salió que la EM
1110-2-1902 se pronuncia sobre exactamente esta pregunta, y en los dos sentidos:

- §C-4a, sobre la hipótesis del Corps: *«Total interslice forces are used in much
  of the computer software …, but **effective forces are recommended** when the
  side forces are assumed to be parallel to the average embankment slope.»*
- §C-4a, sobre Lowe-Karafiath: *«This assumption appears to be better than any of
  the assumptions described earlier, **especially when the side forces represent
  total, rather than effective, forces**.»*
- y su propio ejemplo resuelto del apéndice G, §G-5a, usa **totales**: *«The
  interslice forces are total forces and thus include the water pressures on the
  sides of the slices … also consistent with most computer software.»*

O sea: para el Corps, efectivas; para Lowe-Karafiath, **totales** — que es lo
contrario de lo que OGR hace. Eso apoya el −10,89 % de `Ej_2` y **no explica el
problema 70**, donde quitar el empuje daba 5,0 y 0,2203 y destruía la
invarianza con la profundidad del agua. Un dato que apoya una mitad y contradice
la otra no cierra nada, así que el pendiente sigue abierto.

Lo que sí cambió en v0.1.98: el reparto es ahora un **ajuste del proyecto**
(`MethodsSettings.interslice_forces`), predeterminado en `effective`, de modo que
ningún número validado se mueve y la bifurcación se puede medir sin parchear
código. Los métodos Corps nuevos leen el mismo ajuste.

**Qué sigue haciendo falta para cerrarlo**: el factor de seguridad que da la
referencia con **Lowe-Karafiath** sobre un modelo con **agua embalsada** — la
propia verificación #70 sirve, o cualquier talud con la lámina de agua por
encima del contorno externo. Dos lecturas posibles y las dos son concluyentes:

- si da ≈ 1,6 → la referencia desdobla efectiva/total, y nuestro −10,9 % viene
  de otro sitio dentro del mismo término;
- si da ≈ 5 → la referencia simplemente no lo hace, y entonces **OGR es más
  correcto que la referencia aquí**. Lo que procede es documentar la
  divergencia, no «arreglarla» persiguiendo su número.

Lo que NO hay que hacer mientras tanto: borrar el término para que Ej_2 salga
bien. Sería cambiar un resultado validado por otro validado, a ciegas.

### Y en v0.1.106 la misma pregunta aparece en Spencer y GLE

No es el mismo término, pero es la misma bifurcación, y ahora tiene una medida
propia. Duncan y Wright #70 dice que sobre un talud **ya sumergido** subir el
agua no puede cambiar nada. Bishop lo cumple a 9·10⁻¹³ y Janbu simplificado
también. Spencer y GLE se quedan en **3·10⁻⁴**, y el residuo **no baja al
apretar la tolerancia**: es real.

Aislado por ramas, la causa no admite discusión:

| | F_f | F_m |
|---|---|---|
| λ = 0,0 | 9·10⁻¹³ | 9·10⁻¹³ |
| λ = 0,1 | **16 %** | 0,6 % |
| λ = 0,2 | **45 %** | 1,3 % |

En λ = 0 las dos ramas **son** Janbu y Bishop, y heredan su exactitud. En
λ ≠ 0, `X = λ·E` se aplica a la fuerza interdovela **total**, y la presión del
agua sobre la cara vertical es parte de `E`: sube la lámina, sube `E`, sube el
cortante interdovela a igualdad de λ. Lo que rescata el resultado final es que
la **raíz se mueve con ellas** y el cruce acaba casi donde estaba.

**Qué haría falta**: extender `MethodsSettings.interslice_forces` —la
bifurcación efectiva/total que la familia Corps ya tiene desde v0.1.98— a
Spencer y GLE. No se hizo en v0.1.106 por dos motivos, y el segundo es el que
manda:

1. falta el mismo dato externo que este pendiente lleva pidiendo desde v0.1.94;
2. la evidencia disponible apunta a **totales**, que es lo que hay: Fredlund y
   Krahn (1977) escriben `E` como fuerza total, y la referencia separa su
   Spencer de su Bishop un +1,888 % sobre el modelo con piezométrica, donde OGR
   con totales da +2,14 %. Con efectivas ese número se movería, y se movería
   alejándose.

Medido y sujeto en `tests/test_ponded_water_v161.py`, con un tripwire de dos
caras: falla si el residuo crece, y falla si desaparece — porque desaparecer
significaría que alguien cambió la hipótesis sin actualizar esta entrada.

---

## 6 · Arranque en caliente de λ en Spencer y GLE — ABIERTO (v0.1.106)

Cada *inner solve* sigue arrancando en `initial_fos = 1.0` en vez de en la `F`
ya convergida del λ anterior. Sigue siendo previsiblemente el mayor ahorro que
resta, y sigue sin hacerse por lo mismo: **mueve los números dentro de la
tolerancia**, y cerrarlo exige revalidar Ej_1, Ej_2 y los cinco casos de
`validacion/casos/` publicando el desplazamiento de cada uno.

Lo que sí cambió en v0.1.106, y va en la dirección contraria al coste: la
linealización de la resistencia y el denominador de momentos se resuelven ahora
**una vez por superficie** (`GLESystem`) en vez de una vez por iteración y por
λ. A cambio, cada pasada hace la recursión interdovela, que antes no existía.

### La segunda medición de este apartado — CERRADA en v0.1.106

La tabla de separación respecto de Bishop con piezométrica, que en v0.1.94
medía **−0,000 %** donde la referencia separa **+1,888 %**, era el síntoma de
los tres defectos de la auditoría. Sobre el mismo círculo:

| separación respecto de su propio Bishop | referencia | OGR 0.1.105 | **OGR 0.1.106** |
|---|---|---|---|
| spencer | +1,888 % | −0,000 % | **+2,142 %** |
| gle | +0,809 % | −0,056 % | **+1,743 %** |

El mecanismo que este apartado describía —«el término resistente es el
numerador de Bishop, con `m_α` **sin λ**»— era la mitad correcta del
diagnóstico. La otra mitad, que atribuía a lo mismo el hueco de `F_m(0)`, no lo
era; ver el §9 de este archivo.

---

## 11 · GLE se queda sistemáticamente por encima de Spencer — ABIERTO (v0.1.106)

**Estado: medido, con la causa acotada por descarte, sin corregir. Regla 6.**

Con la corrección interdovela de v0.1.106, Spencer cae dentro del 0,1 % de la
referencia y GLE se queda un escalón por encima, **siempre del mismo lado**:

| caso | Spencer | GLE |
|---|---|---|
| problema 1 (ACADS 1a) | +0,01 % | +0,01 % |
| problema 3 (ACADS 1c) | −0,02 % | +0,00 % |
| problema 6 (Talbingo) | +0,03 % | +0,04 % |
| problema 8 (no circular) | +0,89 % | +0,83 % |
| Ej_2 con piezométrica | **+0,10 %** | **+0,77 %** |
| Ej_1 no circular | +0,03 % | +0,83 % |
| Ej_2 no circular | −0,29 % | −0,09 % |

**Lo que NO es, y está comprobado**: la función de forma. El informe de la
referencia dice literalmente `interslice force function : Half Sine`, que es el
predeterminado de OGR, así que nominalmente las dos son la misma `f(x)`.

**Lo que queda por comprobar**: cómo se normaliza su **argumento**. OGR mapea x
linealmente sobre la luz **horizontal** entre el primer y el último borde de
dovela (`gle.py`, `x0` y `x1`). Una referencia que midiera x **a lo largo de la
superficie**, o sobre una luz que una grieta de tracción trunca, obtendría una
`f` distinta en cada borde — poco, y siempre en el mismo sentido. Un error
aleatorio no sería sistemático; un argumento desplazado sí.

La diferencia es la única cosa que distingue GLE de Spencer desde v0.1.106,
porque los dos comparten `ogr_slip2d/interslice.py` entero. Eso acota el sitio
donde buscar a una función de cuatro líneas.

**Cómo se cerraría**: la referencia publica el valor de `f(x)` por borde de
dovela en su panel de datos de dovela cuando el método es GLE. Con esa columna
al lado de la de OGR sobre el mismo círculo, la normalización queda decidida en
una lectura, sin conjeturas.

Anotado con su medida en `TestKnownDivergences` de
`tests/test_slide_validation_ej2_piezo_v194.py`.

---

## 10 · Lo que el inventario de ajustes dejó abierto (D07c) — ABIERTO (v0.1.103)

v0.1.103 colapsó los seis pares de ajustes que existían dos veces (el nombre
que la interfaz enseñaba y el que el motor leía). El inventario que hizo falta
para encontrarlos —los 64 campos de `SearchSettings` cruzados contra todo
lector fuera de `ogr_gui/`— dejó tres cosas señaladas y sin arreglar, cada una
porque **mueve un número** y necesita su propia referencia. El test
`tests/test_settings_coverage_v1103.py` las sujeta en un inventario congelado,
así que no pueden pudrirse en silencio.

### a) `sa_num_fos_compared_before_stopping`: declarado 5, el código para en 3

Es el n_ε del criterio de parada de Su (2009), sección 2.1.7: se comparan los
últimos n_ε mejores factores y se para si ninguno mejora más que la tolerancia.
El diálogo lo enseña con el valor de la referencia, **5**, y `search.py` para
en un `no_improve_passes >= 3` escrito a mano.

Para cerrarlo: cablearlo y medir qué le hace a los modelos de recocido del
banco. Alarga la búsqueda, así que el factor sólo puede bajar o quedarse — pero
hay que enseñarlo, no suponerlo.

### b) `block_multiple_groups` no lo lee nadie, y lo que sí se lee se deriva mal

El motor lee `block_num_groups`; el diálogo lo calcula como
`num_surfaces // 1000` cuando la casilla *Multiple Groups* está marcada, y 3
cuando no. Eso no es lo que la referencia llama Multiple Groups. Antes de tocar
nada hay que leer su documentación de Block Search: el número de grupos y el
número de superficies no son la misma magnitud dividida por mil.

### c) El rótulo del Auto Refine publica una cifra que no es la suya

`grid_dialogs.py` estima «Number of Surfaces Computed» como
`divisiones × círculos × iteraciones`, que con los valores por defecto da
**1000**. La referencia anuncia **4500** para esos mismos valores, porque cuenta
**pares** de divisiones: C(10,2) = 45 × 10 círculos × 10 iteraciones, y su
«Surfaces Interpreted: 45» es exactamente C(10,2). El algoritmo de OGR sí
recorre pares, así que el que cuenta mal es el rótulo.

No cambia ningún cálculo — es una cifra de pantalla — pero es una cifra
publicada que miente, y la medida real está a un `math.comb` de distancia.

### d) Un ángulo guardado en el marco viejo no se convierte al migrar

`path_min_angle_deg` y `path_max_angle_deg` guardaban el ángulo en el marco
pie→cresta de la búsqueda; los campos que los sustituyen son absolutos. La
conversión necesita la dirección de rotura, que no está en el bloque de ajustes
que `SearchSettings.from_dict` recibe, así que un valor fuera de su defecto se
**reporta** en vez de adivinarse. Ninguno de los 142 modelos del banco lo tiene
fuera del defecto, de modo que hoy no hay nada que convertir; si algún día lo
hay, la conversión tiene que hacerse donde se conoce el proyecto entero.
