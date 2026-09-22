# OGR Slip2D v0.1.188 — los dos chequeos de admisibilidad linearizan la envolvente en UNA tensión, y el testigo dice que la estimación vieja no se equivocaba poco: se saturaba a cero

D113 estaba bien diagnosticada, que no es lo habitual en esta serie de fichas.
Lo que no estaba medido es **cuánto** se equivocaba la estimación que le faltaba
el agua, y la respuesta cambia cómo hay que contar el defecto.

---

## 1. El defecto, y por qué la dirección de la corrección no es opinión

`ogr_slip2d/checks.py` corre los dos chequeos que la referencia hace *después* de
converger el factor: el de tracción en la base y el de m-alpha, éste **encendido
por defecto** desde v0.1.84. Los dos linearizan la envolvente de resistencia
llamando a `BishopSimplified._local_c_phi(s, material, sigma_est)`, que devuelve
`(c, tan φ)` **evaluados en esa tensión**. Y la estimaban distinto:

| función | estimación |
|---|---|
| `base_effective_stresses` | `W = s.weight + water_weight` (v0.1.67) |
| `base_m_alphas`, el mismo bucle quince líneas abajo | `s.weight` a secas |

La corrección de v0.1.67 entró en una y no en la otra. Reportada en 0.1.158 §4 y
sin tocar desde entonces.

**Cuál de las dos era la correcta no hace falta discutirlo**, y conviene decirlo
porque una ficha de este tipo invita a elegir por gusto: el motor estima σ con
`w_total`, que es suelo **más** agua embalsada — `bishop.py:229-231` sobre
`external_forces.py:81`, cuyo propio docstring la declara como «the total vertical
load carried by the base… what the base normal and the gravity driving term must
use». `base_effective_stresses` reproducía al motor; `base_m_alphas` no.

Por eso el arreglo no repite `s.weight + getattr(s, "water_weight", 0.0)`: toma la
carga de `slice_forces(s).w_total`, que es **la misma función que usa la
iteración**. Con `kh = kv = 0` da el mismo número al último bit, pero deja la
estimación atada al concepto en vez de meramente igual a él hoy. Y las dos
cantidades salen de **una sola función**, `_base_load_and_sigma`, que devuelve
`(W, sigma)`: mientras fueran dos expresiones, por parecidas que fuesen, podían
volver a separarse — que es exactamente lo que pasó entre v0.1.67 y hoy.

## 2. Lo que el testigo destapó: no era «un poco menos», era CERO

La ficha dice que el defecto «muerde donde la resistencia depende de σ y hay agua
encima». Es cierto y se queda corto. Medido dovela a dovela sobre el testigo —el
paramento aguas arriba de una presa con el embalse encima, la geometría que
v0.1.67 ya usó porque ahí el agua domina al suelo:

```
  i     weight      water        u*l    sig_dry    sig_wet
  4      166.1     1061.9     1170.6      0.000      9.761
  8      259.2      931.9     1105.7      0.000     11.712
 12      297.3      802.0     1016.0      0.000      3.098
```

Con el embalse lleno, `u·l` ronda 1200 kN/m mientras el peso del suelo solo ronda
300, de modo que `max(0, W_suelo·cos α − u·l)` **se recorta a cero en las
veinticinco dovelas**. La estimación vieja no daba una tensión baja: daba el
extremo del dominio. Y ahí `_local_c_phi` lineariza la envolvente en σ = 0, que
para una curva de potencia con `b < 1` es donde la **tangente es más empinada** —
así que el chequeo no sólo desplazaba `m_alpha`, informaba de la superficie más
floja como si fuera la más resistente.

Es palabra por palabra el síntoma que v0.1.67 documentó en Pilarcitos («todas las
resistencias no drenadas salían cero, porque σ′_fc = (N − u·l)/l daba cero al ser N
un tercio de lo debido frente a una u de embalse lleno»), dejado intacto en la
función de al lado durante ciento veintiuna versiones.

## 3. El guardián existía, decía la verdad en prosa y la mentía en código

`tests/test_checks_v132.py::test_sign_convention_matches_the_solver` se titula «the
identity that makes the check meaningful at all» y su docstring declara que
`base_m_alphas` **debe reproducir el m_alpha que el método usó dentro de su propia
iteración**, añadiendo que recalcularlo a mano desde la expresión publicada de
Bishop «is the only way to keep the two from drifting apart again».

Acto seguido lo recalculaba con `s.weight * cos(a)`: la estimación sin agua. Pasó
verde cincuenta y seis versiones porque su modelo —el Ej_1 de referencia— **no
tiene ninguna lámina de agua**, así que la identidad se cumplía tanto con la
expresión buena como con la mala. Era el test que tenía que haber cazado esto y no
podía.

Queda corregido, con la razón escrita dentro. El término se escribe a mano y **no**
se importa de `checks`: una reimplementación independiente es el punto entero, y
llamar a la función bajo prueba habría dejado la aserción vacía. **Ese cambio no
discrimina** —pasa igual contra los dos árboles, porque el modelo sigue sin agua—
y se dice aquí en vez de dejar que parezca una comprobación nueva.

## 4. El censo, antes de tocar el motor (regla 6)

`_tools/censo_sigma_agua_d113.py`, nuevo en el banco, **SOLO MIDE**. Dos mitades,
porque la pregunta se puede contestar a dos costes muy distintos:

- **Mitad A**, sobre los 194 `.ogr` vivos y sin evaluar nada. Es la que sostiene el
  argumento, porque cubre también las superficies que la mitad B no alcanza.
- **Mitad B**, sobre las superficies publicadas y con el motor: 226 filas
  evaluadas, dovela a dovela.

| | |
|---|---|
| problemas con envolvente dependiente de σ | **5** — 040, 041, 044, 045, 061 |
| problemas con lámina embalsada | **7** — 010, 042, 065, 066, 069, 076, 092 |
| **intersección** | **vacía** |
| filas movidas / veredictos cambiados (mitad B) | **0 / 0** |

**Eso convierte «cero filas movidas» en una identidad y no en un muestreo**: para
`mohr_coulomb`, `undrained`, `undrained_depth_datum` e `infinite_strength` —los 395
materiales restantes— el par `(c, tan φ)` que devuelve `_local_c_phi` no depende de
la estimación, así que ninguna de las dos puede mover nada aunque hubiera agua.

Dos decisiones del medidor que no son adorno:

- **La dependencia de σ se MIDE, no se lista.** Escribir `{"power_curve",
  "hoek_brown", …}` habría sido más corto y se habría quedado corto el día que
  naciera un modelo nuevo — la lista negra de D164, cerrada poniendo una lista
  blanca justo por esto. Aquí el predicado se interroga llamando a `_local_c_phi`
  con dos tensiones.
- **El censo no llama a `base_m_alphas`**, a propósito: hoy devolvería la
  estimación vieja y mañana la nueva, así que apoyarse en ella daría un censo que
  mide cosas distintas antes y después. Calcula las dos él mismo. **Comprobado**:
  corrido contra el árbol de 0.1.187 y contra el de 0.1.188, los dos resúmenes
  difieren en **una sola clave, `version`**. Los dos informes se conservan
  —`docs/audits/sigma_ponded_v1187.md` y `..._v1188.md`— porque esa pareja **es**
  la evidencia de la invariancia; no son dos medidas de dos épocas, son la misma
  medida a los dos lados del cambio.

**Las omisiones se declaran y además se acota lo que pueden tapar.** Veintiuna
filas quedan sin medir (ocho del 022 y cinco del 057 que no rebanan, tres problemas
sin ningún `.ogr`, y cuatro sin factor utilizable), y el resumen publica las dos
cifras que hacen falta para que eso no sea un hueco: **2** saltadas caen en
problemas con envolvente dependiente de σ —las dos del 045, que no tiene agua— y
**0** en problemas con lámina. Un cruce necesita las dos condiciones, luego ninguna
fila saltada puede esconder uno.

## 5. Los tests

`tests/test_m_alpha_ponded_v1188.py`, 12 casos en cinco clases. **Ninguno fija un
factor de seguridad ni ningún otro número contra lo que el código imprime hoy.**
Los anclajes son:

- la **forma cerrada** de la tangente de la curva de potencia, `dτ/dσ =
  a·b·(σ+d)^(b−1) + tan W`, que es derivar la envolvente publicada y no una
  medición: el test la calcula desde a, b y d y la compara a 1e-12;
- la definición `m_alpha = cos α + s·sin α·tan φ/F` (Bishop 1955), recalculada
  desde la geometría de la dovela;
- y la **identidad** entre las dos funciones, que es el defecto escrito como
  ecuación y es verdadera o falsa al margen de lo que cualquiera de las dos
  devuelva.

**La tabla de atribución, ejecutada**, que es lo que dice que la causa es la causa:

| envolvente | lámina | max \|Δm_alpha\| |
|---|---|---|
| potencia | sí | **1,79e-01** |
| potencia | no | 0 exacto |
| Mohr-Coulomb | sí | 7e-14 |
| Mohr-Coulomb | no | 0 exacto |

El brazo «Mohr-Coulomb con agua» es el control que separa «el agua importa» de «la
estimación importa»: ahí el agua está y las tensiones sí difieren, pero `m_alpha`
no, porque una recta tiene la misma tangente en todas partes.

**Discriminación medida, con el reparto nombrado**: contra el árbol de 0.1.187
**fallan 5 y pasan 7**. Los cinco que fallan son los que leen `base_m_alphas`; los
siete que pasan lo hacen **por diseño**, porque dicen lo que el defecto ES leyendo
el motor en vez del arreglo — las tres guardas del testigo, la forma cerrada y la
tabla 2×2 con sus dos controles, que comparan las dos reimplementaciones del propio
fichero y valen en cualquier árbol. Está escrito en la cabecera del fichero.

## 6. Cuatro errores propios detectados antes de publicar

1. **El primer medidor declaró NO LINEAL a una recta.** El umbral era `1e-12` sobre
   `|Δtan φ|` y el censo daba intersección `['042']`, que es `mohr_coulomb`. La
   causa no es el modelo: `MohrCoulomb` **no implementa `tangent_slope`**, así que
   `_local_c_phi` cae a la secante centrada `(τ(σ+δ) − τ(σ−δ))/2δ` con `δ = 1e-4·σ`,
   y a 500 kPa eso extrae una diferencia de orden 0,06 restando dos números de orden
   300 — cancelación catastrófica. Medido sobre los 400 materiales del banco, las
   dos poblaciones **no se tocan**: `power_curve` 8,4e-01 relativo, `mohr_coulomb`
   5,2e-10, el resto 0,0 exacto. El umbral es ahora relativo y vale 1e-6, con 3,7
   órdenes de margen sobre el ruido y 5,9 por debajo de la señal, y el número está
   escrito en el código junto a la medida que lo justifica. **Estuve a punto de
   publicar un cruce inexistente.**
2. **El fallback heredado se comía nueve filas.** `s.get("modelo") or "modelo.ogr"`
   —copiado de `auditoria_traccion.py`, que tiene el mismo hueco— pierde los
   problemas que no tienen ningún `modelo.ogr`: el 52, 62, 70, 79, 81 y 85 llaman a
   los suyos `modelo_seco.ogr`, `modelo_1.ogr`, `modelo_pasivo.ogr`. El nombre bueno
   está en el `resultados*.json` que `referencia.json` nombra, así que ahora se va a
   buscar ahí; y cuando hay varios candidatos y la superficie no declara cuál, **no
   se elige uno**, se declara la ambigüedad — elegir sería inventar el modelo que la
   fila midió, que es el defecto que D133 cerró por no poder nombrarlo. De 30
   saltadas a 21, y de 217 filas medidas a 226.
3. **Una aserción mía era más fuerte que el hecho.** El testigo exigía que en
   **toda** dovela con agua las dos estimaciones difirieran, y falló: en las dovelas
   más sumergidas las dos se recortan a cero y coinciden. Al mirarlo apareció el
   hallazgo de §2, que es más informativo que la aserción que lo escondía; ahora el
   test afirma la saturación y no la desigualdad.
4. **La comprobación de cierre no puede leer por `grep`.** `d113()` verifica que las
   dos funciones **llaman** a `_base_load_and_sigma` recorriendo el AST, no buscando
   la cadena: un `grep` no distingue una llamada de una mención en un docstring, y
   esa diferencia ya dejó pasar una comprobación en `d146()`.

## 7. Reportado y NO corregido (regla 6)

Los dos salieron de leer `checks.py` entero, ninguno es D113, y ninguno se toca en
esta tanda. Fichas nuevas en el banco, con su prompt largo y su paquete:

- **D165 — la resistencia a tracción admisible sale 0.0 siempre, también en roca
  Hoek-Brown.** `_material_tensile_strength` existe para conceder la excepción que
  el docstring del módulo promete a tres modelos, y no puede concederla a ninguno,
  por tres causas independientes y cada una suficiente: lee `sigma_ci`, `mb` y `s`
  como **atributos** cuando `StrengthModel` los guarda en `self.params` y no define
  `__getattr__`; los nombres tampoco existirían (`sigci`, no `sigma_ci`; `m`, no
  `mb`, en el clásico); y `_TENSILE_CAPABLE` nombra `"generalized_hoek_brown"`, que
  **no es el `MODEL_ID` de nada**, mientras omite `"hoek_brown_classic"`, que sí
  existe. Es la regla 7 al revés: no es un ajuste que no mueve el número, es una
  excepción documentada que el código no puede aplicar. Efecto hoy: **ninguno**, y
  hay que decirlo — el chequeo está apagado por defecto y el banco no tiene un solo
  material de la familia Hoek-Brown.
- **D166 — la tensión vertical efectiva del contexto tampoco ve el agua embalsada.**
  `_local_c_phi` construye `SliceContext.sigma_v_eff` desde `slice_.weight / b − u`
  (`bishop.py:96-100`), que es el peso del **suelo**. Mismo linaje que D113 un piso
  más abajo, y con una diferencia que importa: esto no es un chequeo, es la
  linearización que **todos los métodos LEM** usan dentro de su iteración, así que
  moverlo mueve factores de seguridad y no sólo qué superficies se aceptan. Alcanza
  sólo a los modelos con `needs_context` (SHANSEP, los anisótropos, la familia
  `undrained_depth_*`). Efecto en el banco: **ninguno**, medido — los 13
  `undrained_depth_datum` no están en ninguno de los siete problemas con lámina.
  No se corrige porque pide una decisión con referencia externa que hoy no está
  escrita: si una columna de agua libre cuenta como sobrecarga vertical depende del
  modelo constitutivo, y para SHANSEP la respuesta plausible es que sí.

## 8. La re-corrida dirigida, y el quinto error propio: la comparación que no podía atribuir nada

Se pagó la re-corrida de doce problemas por decisión del propietario, aunque el
censo ya dijera que el cambio es un no-op por identidad: los cinco con envolvente
dependiente de σ (040, 041, 044, 045, 061) y los siete con lámina embalsada (010,
042, 065, 066, 069, 076, 092) como **control nulo**. Son 21 archivos, y costaron
**8703 s (2,4 h)** de reloj.

Sobre el coste, porque este proyecto ya se ha engañado dos veces midiéndolo: la
estimación previa fueron 2,9 h, aplicando a los segundos archivados el factor
**×1,224** que midió el sondeo circular de D162. El factor real sobre estos
21 archivos es **×1,016** (8410 s → 8540 s). O sea que el factor de D162 **no se
extrapola a otro subconjunto**: allí se eligió la muestra por coste y se dijo que
el factor crecía con él; aquí, con otros problemas, casi no hay factor.

**Y entonces la comparación denunció dos valores movidos**, y estuve a punto de
publicarlos como efecto de este cambio:

```
040/resultados.json  círculo spencer:  1.104663 -> 1.104662
092/resultados.json  spencer:          1.006442 -> 0.998046   (-0,83 %)
```

**La comparación no podía atribuir nada, y ése es el error.** El lado A era
`Evaluaciones/0.1.187`, pero lo que esa instantánea **congela** para estos
problemas son archivos escritos por versiones anteriores: de los 21, **17 los
escribió 0.1.173 y 4 los escribió 0.1.179, ninguno 0.1.187**. Entre 0.1.179 y hoy
hay nueve versiones de motor con D145, D148, D149, D152, D153, D156 y D159 dentro,
todas sobre el solver de λ — que es justo donde se movió el 092, y con Spencer.
Es el cero falso de D101, D103, D118, D127 y D129 leído del revés: no un cero que
no significa nada, sino una diferencia que no significa lo que parece.

**Lo que sí atribuye es un A/B sobre el mismo árbol**: 0.1.188 entero, cambiando
**únicamente** `ogr_slip2d/checks.py` entre la estimación vieja y la única, y
re-corriendo el 040 y el 092. El parche va en **disco** y no con monkeypatch
porque la búsqueda reparte círculos con `ProcessPoolExecutor` y un parche del
proceso padre no llega a los hijos — la lección del censo con `sitecustomize`.

**33 magnitudes comparadas** —`fos`, `generadas`, `validas`, `invalidas` de cada
método y los siete círculos publicados—, **cero difieren**. `092 spencer` da
0.998046 en los dos lados. Luego las dos filas las movieron las versiones
anteriores, y D113 no mueve ni un dígito del banco. Queda archivado en
`_auditoria/D113_sigma_agua/ab_0.1.188.json`.

**El A/B llevaba además un control interno falsable**: el 040 no tiene agua, así
que las dos estimaciones son el mismo número **por construcción** y sus siete
círculos tenían que salir idénticos bit a bit. Salen. Si no hubieran salido, lo
que estaba mal era mi modelo del cambio y no el banco.

Por eso `d113()` **no** se apoya en la comparación contra la instantánea —que es
lo que la ficha pedía— sino en el A/B, y dice por escrito por qué.

**Balance contra 0.1.187**: 559 → 559 filas, **558 IGUAL**, 0 sin pareja, 0
cambios de estado y **una sola fila que mueve su número**: la de `FoS Slide =
1,111`, el 092·spencer, cuyo error de búsqueda pasa de −9,41 % a −10,17 %. Otras
43 filas cambian **sólo la columna `Version`**, que es exactamente para lo que
v0.1.187 la puso. El banco queda **mezclado** a propósito: 21 archivos a 0.1.188 y
el resto a 0.1.173 y posteriores; el balance lo publica por fila y avisa de que en
los 408 pares con los dos lados en la misma versión «IGUAL» no mide nada.

## 9. Alcance y verificación

El `git diff` del motor es **un solo archivo**, `ogr_slip2d/checks.py`, y dentro
de él una función nueva y dos líneas que la llaman. `ogr_slip2d/methods/` no
cambia; `search.py`, `analysis_runner.py` y `rapid_drawdown.py` —los tres
consumidores aguas abajo— tampoco. No hay ajuste nuevo, así que la regla 3 no pide
ninguna acción de menú, y no hay texto nuevo, así que la regla 2 no pide ninguna
traducción.

- **Suite entera, sin argumentos y sola en la máquina: 4053/4053.** 0.1.187 traía
  4041; los **+12** son exactamente los casos del fichero nuevo.
- **El fichero nuevo discrimina**: 5 de sus 12 casos fallan contra el árbol de
  0.1.187, con el reparto nombrado en su cabecera.
- **Censo de la regla 6** corrido contra los dos árboles: idéntico salvo `version`.
- **A/B** de 33 magnitudes sobre el mismo árbol: cero movidas.
- **`verificar_cierres.py D113`**: CUBIERTO POR TEST.
- **`auditoria_invariantes.py`**: 0 ERROR (748 hallazgos: 491 AVISO, 257
  INFO, el mismo perfil que en 0.1.186 y 0.1.187).
- Instantánea `Evaluaciones/0.1.188`: 1679 archivos comprobados **byte a
  byte**, de los que 21 son de 0.1.188. Sigue sin ser homogénea, y eso ya no
  es un defecto que haya que cazar a mano: la comparativa publica la versión
  por fila desde 0.1.187.

**Una advertencia que va aquí porque es fácil de leer al revés**: que el banco no
se mueva **no** quiere decir que el defecto fuera inocuo. Quiere decir que el
banco no tiene ningún problema con envolvente dependiente de σ y agua embalsada a
la vez. En un modelo que sí los tenga —el testigo de este changelog— la estimación
vieja no daba una tensión algo baja: daba **cero en las veinticinco dovelas**, y
linearizaba la envolvente en el punto donde es más empinada. El banco mide lo que
contiene, y no contenía este caso.
