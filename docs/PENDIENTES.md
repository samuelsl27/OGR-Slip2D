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
## 0 · Simulated Annealing converge peor que un círculo — CERRADO en v0.1.119

La causa que esta entrada daba por diagnosticada —«eso convierte esta entrada
de *investigar* en *cambiar exactamente esto*»: `ngen` 1000, `nepsilon` 5—
**era falsa**, y se midió una a una antes de tocar nada. La real: SA se
guiaba por superficies que el programa después se niega a publicar
(`_evaluate_polyline` preguntaba `is_valid` y nunca `admissible`), y las dos
puntas de la superficie estaban clavadas donde el paper dice que son
variables de control. Peor de siete semillas 1,7365 → **1,1232** contra un
mínimo circular de 1,1135, y el caso 002 pasa de +13 % sobre lo publicado a
dentro de la banda de Greco (1996). Detalle en el changelog de v0.1.119.

La referencia externa que esta entrada decía que faltaba **existe y está
publicada** sobre un talud que ya estaba en el repositorio: Yamagami y Ueta
(1988) 1,338–1,348 y Greco (1996) 1,327–1,333 sobre
`validacion/casos/002-yamagami-ueta-1988`. Ahora hay un test.

---

## 0b · `generation_steps` sigue sin ser monótono

**Estado**: medido, sin corregir. Regla 6. Abierto en v0.1.119.

Esto es lo que sobrevive del pendiente anterior, y sobrevive **por otra
razón** de la que se creía. La puerta de admisibilidad de v0.1.119 explicaba
el nivel del error; no explica que pedir más esfuerzo dé peor respuesta.

Peor de siete semillas, con la causa raíz ya corregida y Optimize Surfaces
activo:

| `generation_steps` | talud del defecto | caso 002 (Spencer) |
|---|---|---|
| 300 | **1,1232** | 1,3550 |
| 600 | 1,1611 | 1,3500 |
| 1 000 | **1,1772** | 1,3500 |

En el talud del defecto **empeora**; en el caso 002 mejora un poco y tampoco
es monótono. La medición de v0.1.90 que hay más abajo sigue en pie:

```python
K     = max(4,  int(self.generation_steps / 50))   # pasadas externas
Ngen0 = max(20, self.generation_steps // K)        # = 50 SIEMPRE si gs >= 200
Ngen  = max(10, Ngen0 // (2 ** (k - 1)))           # se halva cada pasada
if no_improve_passes >= 3: break                   # parada
```

Lo que hay que medir antes de tocar nada, y por orden:

1. **`generation_steps` mueve DOS cosas a la vez** y eso solo ya impide leer
   el efecto de una: las pasadas externas de VFSA, y el tope de evaluaciones
   del LMC (`max_total_evals = 2 * generation_steps`). Separarlos es la
   primera medición, no la última.
2. Más pasadas externas con `Ngen0` fijo en 50 es **más enfriamiento con la
   misma exploración**: `T_gen` cae antes de que el muestreo haya cubierto
   nada, así que la fase local arranca de otro sitio. Es la hipótesis, no un
   hecho.
3. El presupuesto del LMC **ya no ata**: subirlo de ×2 a ×8 y a ×20 no mueve
   el resultado, converge antes.

Y lo que ya está descartado con medida, para que nadie lo vuelva a intentar:
`Ngen0 = generation_steps` (el «ngen 1000» del paper) **empeora**, y
`nepsilon` = 5 no mueve dos de tres semillas.

**Actualizado en v0.1.132**, al cablear `nepsilon` (D07c(a)): ese «no mueve
dos de tres semillas» tiene causa, y es de este mismo pendiente. `K` es el
tope de pasadas, así que **el criterio de parada sólo muerde mientras
nepsilon < K**; con los 300 pasos de la medición K = 6 y con el defecto del
motor (200) K = 4, de modo que el N_eps = 5 que adopta el paper **no puede
dispararse**. Ahora `nepsilon` es un ajuste con valor 5 por defecto, así que
`generation_steps` no sólo mueve dos cosas: gobierna si una tercera existe.
Contado con `progress_cb` sobre el talud de este pendiente (300 pasos, sin
optimización): con nepsilon = 2 las semillas paran en la pasada 2, 2, 2 y 5;
con 3 para una sola; con 5 y con 20 no para ninguna.

---

## 0c · Cuatro desviaciones del paper del recocido, con su efecto medido

**Estado**: medido, sin corregir. Regla 6. Abierto en v0.1.119.

Todas contra Su, X. (2009), *Global Optimization of General Failure Surfaces
in Slope Analysis by Hybrid Simulated Annealing*, University of Waterloo,
que es el paper de la formulación y está en
`referencias/Documentacion_Guia/Search_Option_Surface/`.

**(a) El enfriamiento es acumulado, no absoluto.** `search.py` multiplica
`T_k = T_{k-1}·e^{-c·k^{1/n}}` donde las Ecs. (10)-(11) escriben
`T_k = T_in·e^{-c·k^{1/n}}` desde la temperatura inicial. Conformar el
código al paper **empeora** el resultado: peor de siete semillas 1,1237 →
1,1394 (los dos del mismo A/B, antes del cambio de semilla propia: se
comparan entre sí, no con el 1,1232 de producción). No se cambió, y ésa es la parte que hay que resolver algún día: o el
código está bien por una razón que no se ha escrito, o la ventaja del código
es una casualidad de este talud. Hace falta un segundo modelo para
distinguirlo.

**(b) `dE` se mide contra el mejor histórico, no contra el estado actual.**
La Ec. (9) dice `dE = F(v_{j+1}) − F(v_j)`. Corregido, el resultado es
**idéntico bit a bit** en las tres semillas probadas: una desviación real con
efecto nulo medido. Se deja dicha para que el siguiente no la vuelva a
encontrar y crea que ha dado con algo.

**(c) Las divisiones en x no son las de la Ec. (3).** El código usa `N−1`
divisiones donde el paper usa `N−2`, y además mete los `N−2` vértices
interiores en las `N−2` divisiones **de la izquierda**: ningún vértice
interior puede acercarse al extremo derecho más de `(xN−x1)/(N−1)`, que con
`N` = 9 es el 12,5 % derecho del vano, vedado. Hay un `# Wait —` escrito en
v0.1.17 encima de esa misma línea señalándolo. Desde v0.1.119 los extremos se
mueven, así que el vano ya no es fijo y el sesgo pesa menos, pero sigue ahí.

**(d) `y_floor` sólo ata a la fase 1.** `_vfsa` limita la profundidad a
0,15·H bajo el pie; `_lmc` no la conoce. Uno de los dos está de más, y hasta
saber cuál no se toca ninguno.

**(e) Una sola tolerancia hace dos trabajos.** Encontrada en v0.1.132 al leer
la §3.1 para el valor por defecto de `nepsilon`, y **sin medir**: el paper usa
dos tolerancias distintas —`f_tol` = 1e-4 para la parada y 1e-6 para el factor
de seguridad—, y `_vfsa` usa `self.tolerance` para las dos cosas: para decidir
qué cuenta como mejora del óptimo (`f < best_fos - self.tolerance`) y para
decidir la parada. Con el defecto del proyecto, 1e-4, una mejora menor que
1e-4 **no se guarda** como mejor superficie, cuando el paper la guardaría y
sólo no la contaría para parar.

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

## 7 · Lowe-Karafiath con agua: ¿empuje entre dovelas, sí o no? — ABIERTO (v0.1.117)

**Estado: cerrada la pregunta, abierta la decisión.** Desde v0.1.94 esta
entrada decía «falta UN dato externo». **Ya no falta**: la evidencia está
completa y apunta a un sitio, y lo que queda es elegir el predeterminado
sabiendo lo que se pierde con cada opción. Remedido entero en v0.1.117.

Los tres métodos que **prescriben** la inclinación interdovela —Lowe y
Karafiath (1960) y los dos Corps of Engineers, USACE (2003) EM 1110-2-1902
§C-4a— obligan a la resultante de cada cara vertical a ir a un ángulo θ fijado
por la geometría. Con agua, esa resultante es la suma de una parte efectiva y
del empuje del agua sobre la cara, que es **horizontal**. Que θ se imponga a la
**total** o sólo a la **efectiva** es una elección de modelo: desde v0.1.98 es
`MethodsSettings.interslice_forces`, predeterminado en `effective`, y desde
v0.1.61 lo que la separa es `interslice_water_thrust`
(`ogr_slip2d/external_forces.py`), que sólo usa esta familia.

### La medida, en 0.1.116, mismo círculo, cambiando sólo el ajuste

Fuente: `_tools/medir_d20_interdovela.py` en el banco, que no toca ningún
`.ogr`; el reparto se cambia en memoria.

| caso | publicado | `effective` | error | `total` | error |
|---|---|---|---|---|---|
| #55 lowe-k (Pockoski y Duncan 2000) | 1,318 · UTEXAS4 1,32 | 1,25346 | **−4,90 %** | 1,31520 | **−0,21 %** |
| #56 lowe-k | 1,304 · UTEXAS4 1,31 | 1,24936 | −4,19 % | 1,30097 | −0,23 % |
| Ej_2 piezométrica lowe-k | 0,703504 | 0,62685 | **−10,90 %** | 0,70411 | **+0,09 %** |

Sobre esos mismos círculos Bishop cae a +0,03 % y −0,05 % de su valor
publicado, así que la comparación es del **método**, no de la geometría ni de
la búsqueda. Los cinco métodos que no leen el ajuste dan el mismo número dígito
a dígito en las dos columnas, y **sin freática las dos columnas coinciden**: la
anomalía es del término de agua, no de θ.

El **#51** (Zhu 2003) mejora en la misma dirección sin llegar (relación con
Bishop 0,9333 → 0,9738, publicada 1,008), y no puede llegar: su capa 4 no está
publicada y gobierna más de media superficie. Su Corps of Engineers #2 pasa de
0,9939 a **1,0673** contra 1,0775 de Zhu.

### Cinco líneas de evidencia, todas hacia TOTALES

1. **La referencia lo declara por escrito**, en su base de conocimiento de agua
   subterránea: *«In the case of total stress, you formulate in terms of total
   force and seepage forces are conveniently hidden within the interslice
   normal forces … This is why [este programa] and most LEM programs formulate
   in terms of total forces»*, citando a Duncan, Wright y Brandon, *Soil
   Strength and Slope Stability*, §6.8.1, p. 105. **Ése es el dato que esta
   entrada llevaba pidiendo desde v0.1.94**, en forma documental en vez de
   numérica, y cae del lado «≈ 5»: la referencia no desdobla. La misma página
   añade *«both give identical solutions»*, que es cierto para Bishop, Janbu,
   Spencer y GLE y **falso** para un método de inclinación prescrita — aquí la
   diferencia es del 5 al 12 %.
2. **EM 1110-2-1902 §C-4a**, sobre esta hipótesis: *«This assumption appears to
   be better than any of the assumptions described earlier, especially when the
   side forces represent **total**, rather than effective, forces.»*
3. **§G-5a de la misma norma**, sobre su ejemplo resuelto: *«The interslice
   forces are total forces and thus include the water pressures on the sides of
   the slices.»* Y OGR **ya reproduce ese ejemplo dovela a dovela** desde
   v0.1.98 (`tests/test_modified_swedish_v198.py`) alimentando la recursión con
   las columnas publicadas y **sin restar ningún empuje de cara**: la única
   validación dovela a dovela de este motor es una validación en convenio
   total.
4. **Tres implementaciones independientes**: la referencia, **UTEXAS4** (el
   programa de S. G. Wright, coautor del libro del punto 1) y **Zhu (2003)**.
   Las tres ponen Lowe-Karafiath por encima de Bishop con freática.
5. **La tabla de arriba**: con totales, tres valores publicados se reproducen
   dentro del 0,25 %.

*(No encontrado, y se dice: el artículo original de Lowe y Karafiath (1960) es
un acta del 1er Congreso Panamericano y no está en línea.)*

### Y una identidad analítica en contra, que tampoco admite discusión

Sobre un talud **ya sumergido**, subir la lámina Δh añade una presión uniforme
γ_w·Δh sobre todas las caras del sólido libre. El incremento exacto es
ΔN = γ_w·Δh·ℓ, ΔE_i = γ_w·Δh·h_i **horizontal** y ΔX_i = 0, con lo que σ' y F
no cambian. Una hipótesis que obliga a X_i = E_i·tan θ exige
ΔX_i = ΔE_i·tan θ ≠ 0. Por tanto **con fuerzas totales esta familia no puede
ser invariante con la profundidad del agua.** Sobre el problema 70 (Duncan y
Wright 2005, fig. 6.27, árbitro 1,60):

| | embalsada 75 | embalsada 105 | boyante | invarianza |
|---|---|---|---|---|
| bishop / spencer | 1,60031 / 1,59536 | 1,60031 / 1,59491 | 1,60017 / 1,59685 | 0,00 % / 0,03 % |
| **lowe-k `effective`** | **1,60758** | **1,60758** | 1,60777 | **0,000 %** |
| **lowe-k `total`** | **5,00000** | **0,22043** | 1,60777 | destruida |

Con efectivas la invarianza no es aproximada: las **dieciséis muestras del
residuo Z_n(F)** son idénticas dígito a dígito entre las dos profundidades, no
sólo su raíz; y la equivalencia de Duncan y Wright con el peso boyante se
cumple al 0,012 %.

**Corrección a lo que decía esta entrada: el 5,0 no es un factor de seguridad.**
Muestreado el residuo de cierre sobre la rejilla de arranque de
`_force_balance`, en las dos orientaciones de marcha:

- **embalsada 75, totales**: el residuo **no cambia de signo en ninguna**. No
  hay raíz. Lo devuelto es `best_fallback`, el menor |Z_n| muestreado, que cae
  en F = 5,0 — el **techo** de la rejilla — y sale con `converged = False`;
- **embalsada 105, totales**: aparece un cambio de signo **espurio** en la
  orientación reflejada, entre F = 0,2 (+89 642) y F = 0,3 (−45 380), y el
  buscador converge a **0,22043**. Éste es el peor: número convergido, de
  aspecto plausible y sin aviso.

### Lo que esto cierra, y lo que abre

**Cierra la pregunta.** Las dos formulaciones son consistentes consigo mismas y
cada una acierta donde la otra falla, y ya se sabe por qué: el mundo formula en
totales, y en totales la hipótesis de inclinación prescrita es incompatible con
un talud sumergido. No es un defecto a la espera de un parche.

**Y anula el criterio de cierre que este pendiente y la ficha D20 llevaban
escrito**, que pedía a la vez relación > 1,0 en 51/55/56 (exige totales) e
invarianza dentro del 1 % en el 70 (exige efectivas). **Ningún ajuste único
cumple las dos.**

**Abre una decisión de producto**, que es lo único que queda:

- seguir en `effective` — físicamente coherente, y solo: se aleja del 0,2 % al
  10,9 % de todo valor publicado de esta familia con agua;
- pasar a `total` — reproduce lo publicado dentro del 0,25 %, alinea la familia
  con el Spencer/GLE de este mismo programa (que aplican λ·E a la fuerza total
  desde siempre, con su falta de invarianza documentada como *tripwire* desde
  v0.1.106) y con la única validación dovela a dovela que tiene el motor, **a
  cambio de** quedarse sin respuesta sobre un talud sumergido, donde hoy hace
  falta además un aviso, porque el 0,22043 del caso de 105 ft converge.

Sea cual sea, la alternativa tiene que seguir siendo alcanzable: la norma que
define los métodos considera legítimas las dos.

**La salida práctica, con fuente, mientras tanto**: sobre un talud sumergido,
el procedimiento equivalente de Duncan y Wright —peso boyante γ' = γ − γ_w y
nada de agua— hace desaparecer la bifurcación entera, porque sin superficie de
agua no hay empuje de cara que separar. Los dos ajustes dan entonces el mismo
número, a 0,012 % del que da el tratamiento con agua embalsada y efectivas.

Medido y sujeto en `tests/test_interslice_split_v1117.py`, 12 casos con las dos
anclas enfrentadas y *tripwires* de dos caras: fallan si la divergencia crece y
fallan si desaparece, porque desaparecer significaría que alguien cambió el
predeterminado sin actualizar esta entrada.

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
bifurcación efectiva/total que la familia de inclinación prescrita tiene desde
v0.1.98— a Spencer y GLE. No se hizo en v0.1.106 porque faltaba el dato externo
que este pendiente pedía; ese motivo ha caído en v0.1.117, y el que queda es
que la evidencia apunta a **totales**, que es lo que ya hacen: Fredlund y Krahn
(1977) escriben `E` como fuerza total, y la referencia separa su Spencer de su
Bishop un +1,888 % sobre el modelo con piezométrica, donde OGR con totales da
+2,14 %. Con efectivas ese número se movería, y se movería alejándose. La tarea
sigue en pie como **tarea propia**: si el predeterminado de la familia
prescrita cambia, esto tiene que decidirse con él.

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

## 10 · Lo que el inventario de ajustes dejó abierto (D07c) — (a) CERRADA en v0.1.132, (c) CERRADA en v0.1.133, (d) CERRADA en v0.1.134; (b) ABIERTA (v0.1.103)

v0.1.103 colapsó los seis pares de ajustes que existían dos veces (el nombre
que la interfaz enseñaba y el que el motor leía). El inventario que hizo falta
para encontrarlos —los 64 campos de `SearchSettings` cruzados contra todo
lector fuera de `ogr_gui/`— dejó tres cosas señaladas y sin arreglar, cada una
porque **mueve un número** y necesita su propia referencia. El test
`tests/test_settings_coverage_v1103.py` las sujeta en un inventario congelado,
así que no pueden pudrirse en silencio.

### a) `sa_num_fos_compared_before_stopping` — CERRADO en v0.1.132

Era el n_ε del criterio de parada de Su (2009), sección 2.1.7 —«if there has
not been any visible improvement for the global optimum in the previous n_ε
consecutive runs, the algorithm is to be stopped»—, el diálogo lo enseñaba con
el valor de la referencia, **5**, y `search.py` paraba en un
`no_improve_passes >= 3` escrito a mano. Ya lo lee el motor, con 5 por defecto
en los dos sitios, que es el `N_ε = 5` que la §3.1 del paper adopta para sus
casos de verificación.

**Lo que se aprendió al medirlo**, y no era lo que esta entrada decía:

- **el signo era falso.** «Alarga la búsqueda, así que el factor sólo puede
  bajar o quedarse» no se sostiene: de diez pares semilla/modelo se mueven
  cuatro, tres hacia abajo (caso 002) y **una hacia arriba** (talud D22,
  semilla 7: 1,0808 → 1,0927, +1,1 % con una evaluación más). El recocido es
  estocástico y la fase local arranca donde la global la deja;
- **el mejor de cinco semillas no cambia** en ninguno de los dos modelos;
- y el criterio de parada **sólo existe mientras n_ε < K**, con
  `K = max(4, generation_steps/50)`. Está desarrollado en §0b, que es donde
  vive esa cuerda.

El test es `tests/test_annealing_stopping_v1132.py`, y contrasta 2 contra 20
—no 3 contra 5, que no discrimina— más una comprobación determinista del
número de pasadas.

### b) `block_multiple_groups` no lo lee nadie, y lo que sí se lee se deriva mal

El motor lee `block_num_groups`; el diálogo lo calcula como
`num_surfaces // 1000` cuando la casilla *Multiple Groups* está marcada, y 3
cuando no. Eso no es lo que la referencia llama Multiple Groups. Antes de tocar
nada hay que leer su documentación de Block Search: el número de grupos y el
número de superficies no son la misma magnitud dividida por mil.

### c) El rótulo del Auto Refine — CERRADO en v0.1.133

`grid_dialogs.py` estimaba «Number of Surfaces Computed» como
`divisiones × círculos × iteraciones`, **1000** con los valores por defecto,
mientras el generador recorre los **pares** de divisiones: C(10,2) = 45 × 10
círculos × 10 iteraciones = **4500**, que es lo que la referencia publica con
fórmula (`z·(y·x(x−1)/2)`) y en prosa.

Ya no hay fórmula paralela: el rótulo llama a
`AutoRefineSearch.surfaces_generated` / `.surfaces_per_iteration`, que viven
junto al bucle que genera la población, y `_run` lleva la cuenta de sus propios
intentos en `SearchResult.attempts`, de modo que la cifra publicada se
contrasta contra una corrida real en vez de contra otra fórmula.

**Tres cosas que salieron y no estaban en el enunciado:**

1. **El rótulo estaba congelado.** No había ningún `valueChanged` conectado:
   se escribía una vez, al construir el panel. Cambiar las divisiones de 10 a
   20 no movía la cifra, y la referencia dice que se muestra «as you enter the
   parameters».
2. **La segunda línea existe en la referencia y no está definida.** Las
   capturas del diálogo (paneles circular y no circular) publican
   «Number of Surfaces Interpreted: 45», pero no hay una sola página de la
   ayuda —antigua, actual o el artículo de métodos de búsqueda— que diga qué
   es. Con el único punto de dato coincide con C(x,2), y **un punto no fija una
   fórmula**; además no describe nada que OGR haga, porque OGR conserva todas
   las superficies evaluadas. Se sustituye por **superficies por iteración**
   (450), que la referencia sí publica con fórmula y OGR sí calcula.
3. **Generadas no es analizadas.** El problema 14 genera 4500 y analiza 3300
   (900 → 701 y 90 → 53 en el talud del test): una construcción sin centro
   válido, o un círculo que el foco rechaza, se salta sin contarse. La cifra
   correcta es una **cota superior**, y el tooltip lo dice — si no, la queja
   vuelve al comparar el rótulo con el informe.

Y por eso no se llama `total_count`: ese nombre ya es la población
**analizada** (`SearchResult.total_count`), la que el banco registra como
`generadas`.

### d) Un ángulo guardado en el marco viejo no se convierte al migrar — CERRADO en v0.1.134

`path_min_angle_deg` y `path_max_angle_deg` guardaban el ángulo en el marco
pie→cresta de la búsqueda; los campos que los sustituyen son absolutos. La
conversión necesita la dirección de rotura, que no está en el bloque de ajustes
que `SearchSettings.from_dict` recibe, así que **no se convierte**: se avisa.
Esa decisión es de v0.1.103 y no ha cambiado.

**Lo que sí ha cambiado en v0.1.134, y no era lo que esta entrada decía:**

- **el aviso vigilaba el campo equivocado.** La interfaz de v0.1.102 escribía
  los DOS nombres desde el mismo widget —el superviviente recibía el valor
  tecleado `v` y el gemelo `-abs(v)`—, así que el gemelo no aporta nada y el
  número que entra al cálculo es el del superviviente, escrito en el marco
  viejo y leído en el nuevo;
- **y por eso callaba en el caso más frecuente.** El defecto del gemelo (−45)
  es el espejo del defecto de la caja (45), de modo que quien marcó la casilla
  y la dejó como venía guardó el gemelo exactamente en su defecto y **no
  recibía ningún aviso**. Medido: tecleado 30 → avisaba; tecleado 45 → no;
  sin marcar → no, y eso sí era correcto;
- **el aviso era de un solo uso**: `asdict` no reexporta el nombre retirado,
  así que al primer guardado el gemelo desaparecía y ya nada volvía a avisar.

Ahora el marcador de «archivo anterior a v0.1.103» es la **presencia** de
cualquier gemelo retirado, nunca su valor, y el aviso sale cuando el ángulo del
superviviente viene activado.

**Cuánto costaba** (P079 y P081, Path Search, Bishop simplificado, 2 000
superficies): el valor sin convertir deja la búsqueda con **0 superficies
válidas** en los dos modelos, y el convertido reproduce el resultado dígito a
dígito (FS 1,252166 y 1,095438). Barriendo el ángulo tecleado sobre P079, +v
nunca produce resultado: el fallo es **ruidoso, no silencioso**, lo que rebaja
la gravedad y refuerza avisar en vez de convertir — no hay número mentiroso que
rescatar.

**Dos cosas aparte:** el ángulo *superior* estaba muerto antes de v0.1.103 (la
interfaz nunca escribía `path_upper_angle_enabled`), así que para él no hay
nada que preservar; y la referencia, en su única página sobre abrir un formato
anterior, **convierte en silencio** y no documenta aviso alguno por ajuste cuyo
significado haya cambiado.

Los 142 modelos del banco llevan el gemelo y los supervivientes en sus
defectos, con los dos ángulos desactivados: ni avisan ni pueden mover un
número. Test: `tests/test_settings_migration_v1134.py`.

**Deuda anotada aquí, no resuelta**: ninguna cadena de `settings_warnings`
tiene entrada en español, y son `f-string`s con valores interpolados, así que
el `tr(note)` del punto de uso (`main_window.py`) no podría casar ninguna clave
aunque existiera. Arreglarlo pide separar la parte fija de la interpolada en
todas ellas.

---

## Interpolación de la rejilla de presiones: el spline clásico y el spline con tensión (v0.1.109)

**Encontrado al cerrar D13.** Con la grieta de tracción ya truncando el arco,
el problema 12 del banco de verificación pasa de **+20,8 %** a **−4,8 %** sobre
el valor publicado (Bishop 1,0173 frente a 1,069), y lo que queda **no es la
grieta**:

- el criterio geométrico se cumple exacto: el arco termina en x = 19,5706
  frente al 19,570 publicado;
- el problema 27, que no lleva rejilla, cae en **+0,82 %** con el truncado —
  el mismo sesgo (+0,80 %) que su modelo *sin* grieta ya tenía;
- el problema 2 reproduce los cuatro métodos a **−0,03 %**, en la búsqueda y
  sobre los círculos publicados.

El problema 12 se resuelve con una **rejilla de 22 puntos de presión
intersticial** y su factor es extremadamente sensible a *u*: 1,0173 con `u`,
2,5765 con `u/2` y 4,1364 con `u = 0`. Un **1,7 %** de error en *u* explica
entero el 4,8 %.

**Lo comprobado sobre la implementación de OGR**, que está bien en lo que dice
ser: reproduce los 22 puntos de dato con error 1e-12 y un campo plano con
error 7e-15.

**Lo que falla es de qué spline se trata.** El docstring de
`ogr_core/hydraulic/water_pressure_grid.py` atribuía φ(r) = r²·ln r a *Franke
(1985)* — corregido en v0.1.109 a Harder y Desmarais (1972) / Duchon (1976),
que es de quien es—. Franke (1985) se titula **«Thin plate splines with
tension»** y describe otra superficie: base ln(φr/2) + K₀(φr) + γₑ, con un
parámetro de tensión φ, que degenera en el spline clásico sólo cuando φ → 0.
La ayuda del programa de referencia habla literalmente de *una placa elástica
infinita **bajo tensión*** y cita ese artículo, así que es esa la que usa.

Las dos bases coinciden dentro de la nube de datos y divergen **extrapolando**,
que es justo donde caen **6 de las 30 dovelas** del problema 12: sus bases
quedan fuera de la envolvente convexa de los 22 puntos.

### Por qué NO se ha implementado

El parámetro de tensión φ **no está publicado**. Elegirlo para que el problema
12 dé 1,069 sería ajustar al resultado, que es exactamente lo que prohíbe la
regla 1. Si se aborda, tiene que ser como tarea propia y validado contra tres
identidades **independientes del problema 12**:

1. exactitud en los puntos de dato;
2. límite φ → 0, que debe reproducir el spline clásico de hoy;
3. límite φ → ∞, que tiende a la interpolación armónica (membrana).

Y con la regla 7 encima, porque φ sería un ajuste nuevo: hay que enseñar que
mueve el número. `scipy.special.k0` está disponible sin añadir dependencias.

Mientras tanto, el problema 12 queda con **causa nombrada y medida**, no con
un número inexplicado.
