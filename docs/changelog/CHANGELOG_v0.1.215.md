# OGR Slip2D v0.1.215

Primera de las tres versiones que cierran el paquete P4 del banco de
verificación (decisión de la propietaria: 0.1.215 = D195 + D204; 0.1.216 = D196
+ D197 + D198; 0.1.217 = D199). Dos cambios de motor, **ninguno mueve un factor
del banco**.

- **D195 — un talud hecho de `anisotropic_strength_function` se puede
  analizar.** Desde v0.1.126 el modelo reventaba con `TypeError` en la primera
  dovela de cualquiera de los nueve métodos. La tabla se lee ahora en la
  inclinación **absoluta** de la base.
- **D204 — el retroanálisis de la fuerza de soporte lee una envolvente curva
  donde la lee el método.** Con una curva de potencia, la identidad «fuerza cero
  en el factor propio del método» valía +2096 kN/m (Janbu) y −107 kN/m en el 041
  del banco, el lado inseguro. Ahora vale 0 salvo redondeo en Bishop, Janbu y
  Janbu corregido. Mohr-Coulomb, bit a bit igual.

Se abren cuatro fichas (D208–D211), reportadas y no corregidas: sección 3.

Lo que cambia en el banco de verificación (`_tools/`, `_auditoria/`, fichas)
está fuera de git.

---

## 0. Lo que estaba mal en los encargos

### D195 no era «el ángulo entre la base y la estratificación»

El encargo pedía decidir, «con la fuente del modelo y no por analogía», si el
ángulo que recibe la tabla es el relativo al buzamiento local o el absoluto, y
describía el modelo como una función del ángulo entre la base y la
estratificación. **Este modelo no tiene estratificación.**

- La documentación de la referencia lo define como tramos de la **inclinación de
  la base de la dovela**, de −90° a +90° en sentido antihorario; la tabla ES la
  anisotropía.
- La interfaz de OGR dice lo mismo («(c, φ) = f(base angle) (table)»), y el
  diálogo no ofrece enlazarle una superficie anisótropa (`_ANISOTROPIC_MODEL_IDS`
  no lo incluye).
- El `α` del rebanador es `atan2(dy, dx)` con `dx > 0`: el mismo convenio
  antihorario.

**La causa raíz está en la historia.** El commit d4cdcd5 (v0.1.126), que enseñó
a los modelos a leer el buzamiento local de una superficie anisótropa, puso el
segundo argumento en la llamada de ESTA clase en vez de en la de Snowden, cuyo
`_c_phi` sí lo admite. Así, este modelo revienta y Snowden ignora la superficie
en silencio. Lo segundo es D208.

### D204: el paso 2 del encargo pedía el F equivocado para Janbu corregido

El encargo decía que en Janbu corregido «el punto fijo tiene que hacerse en ese
mismo F sin corregir, el que usa el solver». **El método no lo hace así.** Su
solver itera en el F sin corregir y multiplica por f0 al final (`janbu.py:356`).
Pero su punto fijo de la envolvente (`self_consistent_envelope`) lee la σ′
propia de `base_effective_stresses(res)`, que usa `res.fos`, **el corregido**.

Medido sobre la geometría del 41, comparando el punto fijo por dovela con el
`envelope_stress` que publica el método:

| F del punto fijo | desviación máxima relativa |
|---|---|
| F corregido (el publicado) | 5,7·10⁻¹⁰ |
| F/f0 (lo que pedía el encargo) | 2,4·10⁻² |

Así que el retroanálisis busca el punto en el F corregido y forma las sumas en
F/f0 (v0.1.202). Si el método **debería** leer su σ′ en el F sin corregir es otra
pregunta, sobre el método y no sobre el retroanálisis: D211. Corregirlo movería
Janbu corregido en 40, 41, 44, 45 y 61.

### El primer test de D204 no separaba el arreglo del ruido del solver

Con el arreglo puesto, la identidad dejó −0,18 kN/m en el caso de Janbu, fuera de
una tolerancia de 1e-5 del peso total. Apretar la tolerancia del punto fijo
(1e-6 → 1e-10) no movió **ni un dígito**: el método converge en 5 pasadas en los
dos casos. El residuo era la tolerancia de **los propios solvers sobre F**
(1e-3 por defecto). Resueltos a 1e-12, los tres métodos dejan entre 1e-11 y
3e-9 kN/m, con el interruptor encendido y apagado. El test resuelve así y exige
1e-9 del peso: el defecto era 0,12 del peso.

## 1. D195 — la tabla se lee en la inclinación de la base (motor)

`AnisotropicStrengthFunction.shear_strength_ctx` llama a
`self._c_phi(degrees(ctx.base_angle_rad))`. Sin interruptor: el motor viejo
reventaba y no hay nada que reconstruir. El docstring explica por qué no hay
buzamiento.

Test nuevo, `tests/test_anisotropic_function_v1215.py`, 9 casos:

- la función escrita a mano: a +30° `c = 10, φ = 20` y a −45° `c = 12,5,
  φ = 22,5`, a 1e-12;
- un buzamiento en el contexto no cambia nada (fija la decisión);
- los nueve métodos resuelven un talud seco sin excepción, y
  `_local_c_phi` devuelve en cada dovela el (c, tan φ) de su propio ángulo, con
  bases de −18° a +62°;
- **identidad**: una tabla con la misma fila en todas partes ES Mohr-Coulomb, y
  los nueve métodos dan su factor a 1e-9;
- regla 7: la tabla por defecto y una constante dan factores distintos en los
  nueve;
- el Ordinario en el círculo seco es una suma cerrada,
  `Σ(c(α)·l + W·cos α·tan φ(α)) / Σ W·weight_arm_ratio`, reproducida a 1e-10.

## 2. D204 — el punto fijo por dovela en el retroanálisis (motor)

### Por qué el punto fijo es exacto aquí

La fuerza de soporte es horizontal. Entra en el balance de Bishop solo por su
momento y en el de Janbu solo por la suma horizontal. Ninguno de los dos la deja
entrar en el equilibrio **vertical** de la dovela, que es de donde sale su normal
sin cortante entre dovelas (Bishop 1955; Janbu 1954):

    N = [ W − s·(c·l·sin α − u·l·tan φ·sin α)/F ] / m_α

Con F fijo, la normal de cada dovela depende solo de su propio (c, tan φ). Así
que σ′ → (c, tan φ) → N(F) → σ′ se cierra dovela a dovela, sin bucle sobre la
superficie, y cae en el mismo punto que el bucle global del método. Se eligió
iterar en vez de negar las envolventes curvas porque aquí el punto fijo es
exacto y local, no una aproximación.

### El arreglo

- `checks.x0_base_normal` es ahora **la única** expresión de esa N fuera de los
  solvers. La usan el chequeo (la σ′ que los métodos leen en su punto fijo) y el
  retroanálisis, para que no puedan volver a separarse como las dos
  estimaciones de D113. El chequeo queda bit a bit igual: las mismas operaciones,
  en el mismo orden.
- `back_analysis._own_stress` busca el punto de una dovela con la tolerancia y el
  techo de pasadas de los métodos (`ENVELOPE_STRESS_TOL`, `ENVELOPE_MAX_PASSES`).
- `_sums_at_fixed_fos` lo usa solo donde la envolvente depende de la tensión
  (`_envelope_depends_on_stress`) y con `methods.base.ENVELOPE_AT_OWN_STRESS`
  encendido. Es el mismo interruptor que el punto fijo de los métodos, así que
  un A/B que lo apague reconstruye la lectura vieja en los dos lados a la vez.
  El docstring recoge la decisión, el argumento del desacople y el porqué del F
  de Janbu corregido, como pedía el encargo.
- Una dovela cuyo punto no converge **deja la superficie fuera**, con nota.
  `required_force` devuelve fuerzas NaN y `notes["envelope_not_settled"]`;
  `run_back_analysis` las cuenta como cuenta las compuestas. La ventana de
  interpretación lo dice (con `tr()`) en vez de imprimir «nan».

### Medido

| caso | 0.1.214 | 0.1.215 |
|---|---|---|
| 041 del banco, Janbu sobre su crítica archivada (fuerza pasiva sin recortar) | −107,47 kN/m | +0,0016 kN/m (3,7·10⁻⁷ de D) |
| geometría del 41 del test (ru = 0,3), Janbu | +2096,44 kN/m | ~10⁻⁹ kN/m (solver a 1e-12) |
| misma geometría, círculo, Bishop descontado el hueco del brazo (D210) | −73,82 kN/m | ~10⁻¹¹ kN/m |

El +0,0016 del 041 es la tolerancia de F del solver de Janbu (1e-3): con el
interruptor apagado deja +0,0039, del mismo orden.

**El 37 del banco**, el único retroanálisis que tiene, es Mohr-Coulomb (φ = 36°,
c = 0), y queda **bit a bit igual**. Medido con el retroanálisis configurado
del modelo (Bishop, F objetivo 1,5, cota 9 m) en un árbol de 0.1.214 y en
éste: activa 223,24585639155092 y pasiva 334,86878458732633 kN/m sobre el
mismo círculo (2,6667; 25,2083; R 20,1224), entre 3097 superficies, en los
dos. La referencia publica 351 (pasiva) y 233,835 (activa); la diferencia es
de antes y no es de esta ficha.

Test nuevo, `tests/test_back_analysis_envelope_v1215.py`, 11 casos:

- la identidad sin recorte en Janbu y Janbu corregido (poligonal del 41) y en
  Bishop (un círculo sobre la misma geometría), a 1e-9 del peso;
- en Bishop se descuenta explícitamente, calculado desde las dovelas, el hueco
  `sin α` / `weight_arm_ratio` de su suma motora, que es D210 y no este defecto;
- los puntos del retroanálisis coinciden con el `envelope_stress` publicado por
  cada método (< 1e-5), y en Janbu corregido **fallan** en F/f0 (> 1e-3). Eso
  fija la elección del F;
- controles: la identidad con el interruptor apagado; Mohr-Coulomb bit a bit;
  el interruptor mueve las sumas de una curva (regla 7);
- el rechazo: con `ENVELOPE_MAX_PASSES = 1` la superficie no se retroanaliza y
  lo dice.

## 3. Lo que se reporta y NO se corrige (regla 6)

- **D208 — Snowden ignora la superficie anisótropa.**
  `SnowdenModifiedAnisotropicLinear.shear_strength_ctx` llama a
  `self._c_phi(ángulo)` sin el buzamiento local que su `_c_phi` admite, aunque
  el diálogo ofrece enlazarle una superficie. Iba como añadido dentro de la
  ficha D195 y el encargo prohibía mover los demás modelos anisótropos.
- **D209 — la referencia define la función anisótropa por tramos
  escalonados**, cada uno con su c y su φ («discrete angular ranges»); OGR
  interpola linealmente entre puntos. Cambiarlo cambia lo que significa una
  tabla ya guardada, y es decisión de la propietaria.
- **D210 — el retroanálisis reconstruye la carga a mano.** Es el añadido de
  0.1.214 a la ficha D204:
  - sin el agua embalsada ni sus empujes;
  - Bishop con `sin α` en lugar de `weight_arm_ratio`: +3,40 kN/m en su factor
    propio sobre el círculo del test, que el test descuenta;
  - el sentido de Janbu por la regla de Bishop.

  Corregirlo mueve resultados Mohr-Coulomb, y el encargo de D204 exigía el 37 bit
  a bit.
- **D211 — Janbu corregido lee su σ′ propia en el F corregido** mientras su
  solver itera en el F sin corregir (sección 0).

## 4. Verificación

- Suite entera: **4798 de 4798** (32 min 19 s).
- Tests nuevos, 20 casos. Contra 0.1.214 fallan 15, medido copiándolos a un
  árbol de 4645302 extraído con `git archive`:
  - D195: 8 de 9, por el `TypeError` que es el defecto. Pasa la guarda de la
    función escrita a mano, que no toca el motor.
  - D204: 7 de 11, 5 por comportamiento (+2096,44 kN/m, −73,82 kN/m, el
    interruptor que no llega a las sumas, ningún rechazo) y 2 por el símbolo
    nuevo `_own_stress`. Pasan las dos guardas del testigo y los dos controles.
- Selección de 13 archivos vecinos (retroanálisis, bloque 4, modelos de
  resistencia, envolvente propia, chequeos, sismo, i18n): **205 de 205**.
