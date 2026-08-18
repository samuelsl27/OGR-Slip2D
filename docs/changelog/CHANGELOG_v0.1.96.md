# OGR Slip2D v0.1.96 — tres anomalías que sólo el agua podía enseñar

Las tres estaban medidas y reportadas en v0.1.94 sin corregir, como manda la
regla 6. Ésta las corrige, cada una con su ancla externa.

| | antes | ahora |
|---|---|---|
| **A1** τ reportada, dovela 25 (σ' = −11,27) | 15,000 (**+66 %**) | 9,143 (**+1,5 %**) |
| **A2** peor error en el peso de dovela | **0,637 %** | **0,0012 %** |
| **A2** σ_n de Bishop, dovela 23 | −0,837 % | **−0,160 %** |
| **A4** piezométrica que no cubre la dovela | talud seco, en silencio | **superficie rechazada** |

---

## 1 · A1 · La resistencia que se publicaba estaba truncada en σ' = 0

`bishop.py` calculaba `sigma_eff = max(0.0, N/l − u)` y de ahí
`τ = shear_strength(σ')`, que **vuelve a truncar** dentro de
`MohrCoulomb.shear_strength`. Una base en tracción se publicaba con la cohesión
entera:

```
dovela 25   σ' = −11,27 kPa
  referencia   τ = 15 + (−11,27)·tan 28° =  9,005 kPa
  truncado     τ = 15 + max(0, −11,27)·… = 15,000 kPa    +66 %
dovela  1   σ' = −0,79 kPa   referencia 25,544   truncado 26,000   +1,8 %
```

**El factor de seguridad no se mueve**, y eso está comprobado, no supuesto: el
bloque corre después de converger y sólo reporta, mientras que el numerador de
Bishop usa `(W − u·b)·tanφ`, que nunca pasó por aquí. Medido antes y después:
0,673712 en los dos casos.

Lo que sí cambiaba era **lo que ve el usuario** en el panel de dovelas y en
cualquier gráfica de σ' o τ, justo donde hay agua — porque hace falta agua para
que σ' entre en tracción, y por eso dos modelos secos no podían enseñarlo.

Detalle que merece la pena: `checks.base_effective_stresses` —la que lee el
*Tensile Stress Check*— **siempre** devolvió σ' con signo. Eran dos caminos
calculando la misma magnitud y sólo uno truncaba. Ahora coinciden.

La envolvente se evalúa por la **linealización** en vez de por
`shear_strength`, para que siga siendo correcto con los modelos no lineales:
para Mohr-Coulomb es exacto, y para Hoek-Brown es la tangente extendida a
tracción, que es la lectura natural y mejor que truncar. Con suelo en τ = 0,
porque una resistencia al corte negativa no es una magnitud física — para eso
está la comprobación de tracción.

Tras el arreglo queda un residuo de **+1,5 %** en la dovela 25, que ya no es
esto: viene de que la `N` reportada difiere un 2,3 % de la de la referencia en
las bases muy inclinadas. Es otro asunto, más pequeño, y se deja dicho.

## 2 · A2 · El peso de una dovela con un quiebro del terreno dentro

La dovela 23 va de x = 39,08 a x = 40,10, y **el vértice de coronación en
x = 40 cae dentro**. El peso se integraba entre la base y
`top_y_mid = ½(y_izq + y_der)`, la cuerda entre las dos esquinas de la dovela,
que corta la esquina del terreno.

La referencia **no** parte una dovela en un quiebro del terreno — sus anchos son
19 × 1,04705 más 6 × 1,01518, sin ningún corte extra en x = 40 —, así que tiene
que estar integrando el área real. Ahora también:
`_mean_polyline_y` parte en cada vértice del perfil dentro de la dovela y suma
trapecios. El perfil es lineal a trozos, así que **la integral es exacta**, no
muestreada.

```
                        antes        ahora     referencia
W dovela 23           137,192      138,072      138,072
peor error, las 25      0,637 %      0,0012 %
sigma_n Bishop d.23    −0,837 %     −0,160 %
```

### Y de paso: la tabla de la referencia se contradice a sí misma en esa fila

Al ajustar el test apareció esto, y conviene dejarlo escrito porque cambia cómo
hay que leer el ancla. Invirtiendo `σ' = W cosα/l − u cos²α` sobre el σ' que la
referencia publica para la dovela 23 sale un peso de **137,4177**. En la misma
tabla, la referencia imprime **138,0720**.

```
peso implicado por su sigma-prima   137,4177
peso que ella misma imprime         138,0720     -> 0,48 % de diferencia
```

Metiendo el peso IMPRESO por la referencia en su propia fórmula sale
σ' = 22,7903, que es exactamente lo que da este programa, y **+0,567 %** frente
al σ' que ella publica. Como desde ahora OGR coincide con el peso impreso a
2·10⁻⁴ %, hereda entera esa discrepancia.

Por eso el límite de esa dovela en el test es 0,8 % y no 0,5 %, con la
aritmética escrita en el propio test. **No es una tolerancia relajada hasta que
pasó**: exigir 0,5 % sería exigir coincidencia con un número con el que la
propia fuente no coincide.

### Y un test viejo cazó la incoherencia a medio camino

El primer intento cambiaba **sólo el peso** y dejaba `Slice.height` con el
punto medio de la cuerda. La suite lo rechazó:

```
test_slice_column_v163.py :: test_one_material_no_water_matches_the_closed_form
    assert abs(s.weight - GAMMA_BOT * s.height * s.width) < 1e-9
```

Y tenía razón. Con un solo material, `peso = γ · altura · ancho` es una
identidad, no una aproximación, y romperla habría dejado el peso, la altura y
el área describiendo tres columnas distintas. Ese test es de v0.1.63 y su
docstring se llama a sí mismo «the regression guard for the validation cases»;
cazó exactamente lo que decía que iba a cazar.

Así que `Slice.height` lee ahora la misma media exacta (`top_y_mean`), y la
identidad vuelve a ser cierta. `top_y_left`, `top_y_right` y `top_y_mid` se
quedan como estaban: son la geometría real de la cara superior, que es lo que
necesitan el agua embalsada y el dibujo.

### Lo que esto mueve

Un segundo acierto que no se buscaba — **el área que se reporta**, contra los
160,25 m² que publica la referencia:

```
antes de A2      160,205   −0,03 %
ahora            160,2489  −0,0007 %
```

El ancla del área en el test pasa por eso de 0,5 % a **1e-4**: con la anterior
ya no estaría midiendo nada.

Sobre el círculo con agua, Bishop pasa de 0,673712 a 0,673608 — de −0,181 % a
−0,196 % frente a la referencia. Es decir: el peso y el área se vuelven
**exactos** y el factor de seguridad se aleja 0,015 %. No es contradictorio,
una dovela más pesada sube el numerador y el denominador a la vez; y 0,015 % no
es una magnitud sobre la que decidir nada.

## 3 · A4 · Una piezométrica que no cubre la dovela ya no se lee como talud seco

`interp_y_on_polyline` responde `None` fuera del rango en x de la polilínea, y
`pore_pressure_at` lo convertía en `u = 0`. Un talud seco, en silencio, del
lado inseguro.

La referencia hace lo contrario y lo dice dos veces en su documentación, bajo
*Add Water Table* y bajo *Add Piezometric Surface*:

> "the analysis will not be able to calculate the pore pressure for slip
> surfaces where the [surface] is not defined, and a safety factor will NOT BE
> CALCULATED"

Hacían falta **dos preguntas distintas**, porque `pore_pressure_at` no puede
decirle a quien la llama cuál de las dos cosas está devolviendo: «u = 0 porque
el agua está por debajo de este punto» es un resultado, y «no hay superficie de
agua sobre esta abscisa» es una negativa. `water_surface_defined_at` es la
segunda; el rebanador la hace por dovela y descarta la superficie entera.

Comprobado sobre el modelo de referencia, acortando la piezométrica para que
deje de cubrir la parte izquierda de la rotura (x = 16,14 … 42,13):

```
piezometrica completa      FoS 0,673608
piezometrica acortada      superficie RECHAZADA   (antes: se calculaba seca)
```

Devuelve «analizable» cuando el material no usa ninguna superficie de agua
—Ru, constante, campo de elementos finitos o ninguna—, porque ahí la pregunta
no se plantea. Y también cuando el modelo del material **es** una superficie de
agua pero no resuelve a ninguna frontera: eso es un proyecto con el modelo
puesto y nada dibujado, que ya da u = 0 en todas partes y es un problema
distinto de una superficie que existe pero se queda corta.

## 4 · Lo que sigue abierto

Sin cambios:

- **Lowe-Karafiath, −10,9 %** (`PENDIENTES.md` §7). Sigue esperando **un dato**:
  el Lowe-Karafiath de la referencia sobre un modelo con agua embalsada.
- **Spencer −2,0 % y GLE −0,8 %**: la auditoría `spencer_gle_interslice_v179.md`.
- **El clamp de `sigma_n_eff` en la ruta de cálculo de Fellenius**
  (`ordinary.py`, `max(0.0, N_eff)`). A1 arregla el reporte de Bishop, que es lo
  que estaba medido. El de Fellenius **sí** entra en el factor de seguridad, y
  no hay ningún caso de referencia con σ' negativo en Fellenius para validar el
  cambio — con la corrección de v0.1.94 ninguna de las 25 dovelas sale negativa.
  Se deja como está antes que cambiarlo a ciegas.

---

## Archivos

| archivo | qué |
|---|---|
| `ogr_slip2d/methods/bishop.py` | A1 — σ' y τ se reportan con signo, por la linealización |
| `ogr_slip2d/slicer.py` | A2 — `_mean_polyline_y`, `Slice.top_y_mean`, `height`; A4 — la negativa por dovela |
| `ogr_core/hydraulic/water_surfaces.py` | A4 — `water_surface_defined_at` |
| `tests/test_slide_validation_ej2_piezo_v194.py` | ancla de pesos; el límite medido de la dovela 23 |

© 2026 Samuel Sáez López — UPCT — AGPL-3.0-or-later
