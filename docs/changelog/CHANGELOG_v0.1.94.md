# OGR Slip2D v0.1.94 — Fellenius restaba el agua sobre la base entera, y la referencia la resta sobre su proyección vertical

| Ej_2 + línea piezométrica, círculo crítico de la referencia | antes | ahora |
|---|---|---|
| ordinary/fellenius | 0,600111 (**−24,72 %**) | **0,796740 (−0,06 %)** |
| dovelas de 25 con σ' negativa | **5** | **0** |
| peor error en σ' contra la tabla de la referencia | **118 %** | **0,03 %** |

**Ningún modelo seco se mueve, y no por suerte**: las dos formas son la misma
ecuación cuando u = 0. La suite entera pasa, 1961 → 1972 tests.

---

## 1 · El caso que lo destapó existía desde ayer

`referencias/Ejemplos/Ej_2/Ej_2_Piezometric_Line/` es la geometría de Ej_2 con
una línea piezométrica asignada a los materiales 2 y 3. Es **el primer modelo
de referencia del proyecto con presión intersticial**: Ej_1 y Ej_2 son secos,
así que durante ochenta versiones toda la formulación de agua del motor LEM no
tuvo ningún valor externo contra el que medirse.

Lo primero que se midió fue tranquilizador, y por poco hace que no se mirara
más. Sobre el círculo crítico de la referencia, Bishop:

| magnitud | resultado |
|---|---|
| **u en las 25 dovelas** | error < **0,001 %** |
| ancho de dovela, las 25 | idéntico (19 × 1,04705 + 6 × 1,01518) |
| material de la base, las 25 | idéntico, con el corte en el contacto 3→2 |
| extremos de la superficie | 16,1410 / 42,1260 vs 16,141 / 42,126 |
| FoS Bishop | 0,673712 vs 0,674931 → **−0,18 %** |

O sea: **el agua llega bien a la dovela**. `pore_pressure_at`, la resolución de
qué superficie aplica a cada material, Hu = 1 y γw = 9,81 están bien.

La conclusión «la integración piezométrica es correcta» se escribió con eso, y
**era falsa**. Estaba sacada de un método.

## 2 · Los siete métodos, sobre el círculo de la propia referencia

Sin efecto de búsqueda de por medio: misma geometría, mismas dovelas, misma u.

| método | OGR | referencia | error |
|---|---|---|---|
| bishop simplified | 0,673712 | 0,674931 | −0,18 % ✔ |
| janbu simplified | 0,571566 | 0,568860 | +0,48 % ✔ |
| janbu corrected | 0,615670 | 0,612772 | +0,47 % ✔ |
| gle/morgenstern-price | 0,674871 | 0,680394 | −0,81 % |
| spencer | 0,673860 | 0,687672 | −2,01 % |
| lowe-karafiath | 0,626915 | 0,703504 | −10,89 % |
| **ordinary/fellenius** | **0,600111** | **0,797225** | **−24,72 %** |

Y la tabla que lo aísla — el mismo código, el mismo círculo, el agua quitada
del modelo en la columna izquierda:

| método | SECO | CON AGUA |
|---|---|---|
| ordinary/fellenius | −0,03 % | **−24,72 %** |
| bishop simplified | −0,07 % | −0,23 % |
| janbu simplified | −0,03 % | +0,23 % |
| janbu corrected | −0,00 % | +0,23 % |
| spencer | −0,18 % | −2,08 % |
| lowe-karafiath | −0,12 % | −10,89 % |
| gle/morgenstern-price | −0,26 % | −1,09 % |

Los siete dentro del 0,26 % en seco. **Lo que falla es lo que cada método hace
con la u**, no el método.

## 3 · Fellenius: la corrección de Turnbull y Hvorslev

`ordinary.py` calculaba `N' = W cos α − u·l`. La referencia usa

```
N' = W cos α − u·l·cos²α
```

es decir, resuelve la fuerza de agua sobre la **proyección vertical** de la
base y no sobre la base entera (Turnbull y Hvorslev, 1967; Lambe y Whitman la
llaman *Ordinary method with corrected pore pressure*). Las dos coinciden en
α = 0 y divergen como cos²α.

Contrastadas contra la columna *Effective Normal Stress* de la tabla de dovelas
de la referencia, las 25 dovelas:

```
                                            peor |error|
A   sigma' = W cos a / l - u                  118,1 %     <- lo que hacía OGR
B   sigma' = W cos a / l - u cos^2 a            0,03 %    <- las 22 con u > 0
```

**No es un ajuste, es una identidad**: B reproduce las 20 primeras dovelas a
0,000-0,01 %. Cuatro números fitados nunca habrían decidido esto (regla 1); una
columna publicada sí.

### El comentario que estaba justificando el bug

Esto es la parte que merece recordarse. `ordinary.py` contaba las dovelas con
`N' < 0` y las explicaba así:

> This is THE failure mode of the method, not of this implementation […]
> Whitman and Bailey (1967) measured errors of up to 60 % this way […]
> Reported rather than patched: "fixing" it would no longer be Fellenius'
> method.

En este círculo eran **5 dovelas de 25**, con σ' hasta −7,3 kPa. Con el término
corregido **ninguna de las 25 sale negativa**. Las tracciones las fabricaba el
término de agua sin corregir — y una cita bibliográfica correcta, sobre una
limitación real del método, llevaba versiones tapándolo. Una explicación
plausible es más difícil de quitar que un fallo evidente.

## 4 · Qué NO se ha tocado, y por qué

### Lowe-Karafiath, −10,9 %: diagnosticado, no corregido (regla 6)

La causa está localizada: `interslice_water_thrust` (`external_forces.py`), que
usa **sólo** Lowe-Karafiath. Integra u sobre las caras verticales entre dovelas
y la mete como fuerza externa, con lo que la `Z` de la recursión pasa a ser la
fuerza interdovela **efectiva** en vez de la **total**. Desactivándola:

```
con el empuje (hoy)     0,626915    −10,89 %
sin el empuje           0,704139     +0,09 %
referencia              0,703504
```

**Pero quitarlo rompe un caso publicado.** Verificación #70 de Duncan y Wright
(talud sumergido, árbitro 1,60), remedida ahora:

| | ponded 75 | ponded 105 | boyante | invarianza |
|---|---|---|---|---|
| Bishop / Spencer / GLE | 1,6006 | 1,6006 | 1,6003 | 0,00 % |
| **Lowe CON empuje** | 1,6092 | 1,6099 | 1,6081 | 0,05 % ✔ |
| **Lowe SIN empuje** | **5,0000** | **0,2203** | 1,6081 | **95,6 %** ✘ |

Sin el término no sólo se pierde la magnitud: se pierde la **invarianza con la
profundidad del agua**, que es el invariante fuerte del caso — añadir agua
sobre un talud ya sumergido no puede cambiar nada.

Las dos formulaciones son consistentes consigo mismas; difieren en si la
inclinación prescrita θ = ½(β+α) se aplica a la fuerza interdovela **total** o
a la **efectiva**. Ninguna acierta en los dos casos.

**Lo que falta es un dato, no un razonamiento**: el factor de seguridad que da
la referencia con Lowe-Karafiath sobre un modelo con **agua embalsada**. Si da
≈1,6, hace el desdoblamiento y nuestro −10,9 % es otra cosa; si da ≈5, no lo
hace, y entonces OGR es **más correcto que la referencia** en este punto y lo
que procede es documentar la divergencia. Anotado en `docs/PENDIENTES.md`.

### Spencer −2,0 % y GLE −0,8 %: no es el agua

La separación de cada método respecto de **su propio** Bishop:

| | seco ref | seco OGR | agua ref | agua OGR |
|---|---|---|---|---|
| spencer / bishop | +0,087 % | −0,026 % | **+1,888 %** | **−0,000 %** |
| gle / bishop | +0,191 % | −0,001 % | **+0,809 %** | −0,056 % |

La referencia separa Spencer de Bishop casi un 2 % al meter agua; OGR se queda
en cero. `spencer.py` construye su término resistente como el numerador de
Bishop con un `m_α` **sin λ**, así que la fuerza vertical interdovela nunca
llega a la normal en la base. Es exactamente el síntoma que
`docs/audits/spencer_gle_interslice_v179.md` lleva abierto desde v0.1.79 y que
v0.1.90 dejó **sin explicar** tras descartar el rango de λ.

En seco la separación verdadera es del 0,09-0,19 %, por debajo del ruido: por
eso el defecto era invisible. **Este modelo es el primero que lo hace
medible.** La medición se añade a esa auditoría; el arreglo va en su versión.

## 5 · El test, y por qué tiene dientes

`tests/test_slide_validation_ej2_piezo_v194.py`, 11 casos, tres anclas en orden
creciente de fuerza:

1. **u en las 25 dovelas** contra la tabla de la referencia — ancla el modelo de
   agua con independencia de cualquier método. Más una identidad cerrada:
   u = γw·(y_piezo − y), exacta a 1e-12.
2. **σ' de Fellenius en las 25 dovelas** — el ancla que encontró el bug.
3. Los **cuatro** métodos que coinciden, dentro del 0,5 %.

Y dos que existen para que el propio test no se crea a sí mismo:

- `test_the_uncorrected_form_would_fail_this_same_check` recalcula σ' con la
  fórmula vieja y **exige que falle** (> 100 %). Sin él, el ancla podría estar
  pasando por una tolerancia lo bastante laxa como para admitir las dos
  fórmulas.
- `test_a_dry_model_cannot_tell_the_two_forms_apart` afirma la razón por la que
  Ej_1 y Ej_2 no pueden moverse, en vez de afirmar que no se han movido.

Comprobado a mano restaurando la fórmula vieja: el archivo pasa de 11/11 a
fallar en `test_no_slice_is_driven_into_false_tension` (5 dovelas) y en
`test_within_half_a_percent` (24,7 %).

Las tres divergencias abiertas van en `TestKnownDivergences` con su **tamaño
medido**, no con una tolerancia que las deje pasar: consagrar el defecto es lo
que la regla 1 prohíbe, y esta forma obliga a quien lo arregle a venir aquí y
decirlo.

## 6 · Anomalías encontradas de paso, NO corregidas

- **La resistencia que se REPORTA está truncada en σ' = 0.** `bishop.py:563`
  calcula `max(0, N/l − u)` y `MohrCoulomb.shear_strength` vuelve a truncar.
  Dovela 25: la referencia publica τ = 9,005 (σ' = −11,27); OGR muestra 15,000,
  un **+66 %**. **No afecta al factor de seguridad** —el numerador de Bishop usa
  `(W − u·b)·tanφ`, que sí deja pasar el término negativo— pero sí a lo que ve
  el usuario en el panel de dovelas. `checks.base_effective_stresses` devuelve
  σ' con signo, así que el *Tensile Stress Check* no está afectado: son dos
  caminos que calculan lo mismo y sólo uno trunca.
- **El peso de una dovela con un quiebro del terreno dentro sale bajo.**
  Dovela 23: el vértice del perfil en x = 40 cae dentro de la dovela y
  `_column_weight` integra la cuerda, no el terreno. W 137,192 vs 138,072
  (−0,64 %); área total −0,03 %, toda de esa dovela. Las otras 24 a 1e-5.
- **Asignar una superficie de agua a un material no hace nada por sí solo.**
  `act_assign_water_surface` escribe `Material.water_surface_id` y nada más;
  `pore_pressure_at` sale por `ppt == NONE` antes de mirarlo. Medido: 0,000 →
  196,200 kPa según se toque o no también `pore_pressure`. Regla 7, y es el
  campo que el panel *Assign Piezo Line* tendrá que escribir.
- **Una piezométrica que no cubre la dovela se lee como talud seco, en
  silencio.** La referencia se niega a calcular la superficie y escribe un
  error (`Add_Piezometric_Surface.htm`, `Water_Parameters.htm`). Aquí u = 0, del
  lado inseguro.

## 7 · Discrepancias en los archivos del ejemplo

- `Ej_2_Geometria_Piezometric_Line.txt` da la piezométrica con el cuarto
  vértice en **(60, 50)**. El `.sli` de la referencia
  (`piezos: 1 vertices: [12,11,15,16,3]`, vértice 16 = `x: 55 y: 50`) y el
  `.ogr` dicen **(55, 50)**. El `.txt` es el que está mal.
- El `.ogr` lleva `check_m_alpha = False` donde el `.sli` lleva `malpha: 1`.
  Por eso los recuentos de válidas no coinciden (3403 frente a 3194 + 233 de
  código −112). Misma clase de infidelidad que la ya anotada sobre la rejilla
  de `Ej_1/PGR_Slip2D_Ej_1_General.ogr`.

---

## Archivos

| archivo | qué |
|---|---|
| `ogr_slip2d/methods/ordinary.py` | `u·l·cos²α`; el comentario que justificaba el bug, reescrito |
| `tests/test_slide_validation_ej2_piezo_v194.py` | el caso con agua entra en la suite, 11 tests |
| `docs/PENDIENTES.md` | Lowe-Karafiath y Spencer/GLE, con sus medidas |
| `referencias/Ejemplos/README.md` | el ejemplo nuevo (fuera del repositorio) |

© 2026 Samuel Sáez López — UPCT — AGPL-3.0-or-later
