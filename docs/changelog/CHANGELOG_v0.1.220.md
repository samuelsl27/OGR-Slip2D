# OGR Slip2D v0.1.220

Tercera de las cuatro versiones que cierran lo que queda del paquete P4 del
banco de verificación:

- **D210.** El retroanálisis de la fuerza de soporte pide sus sumas al propio
  método, con los soportes del modelo dentro. Hasta ahora las reconstruía a
  mano:
  - sin el agua embalsada ni su empuje;
  - con `sin α` como brazo del peso de Bishop;
  - con el sentido de deslizamiento de Bishop también para Janbu;
  - y sin soportes.
- **D211.** Janbu corregido forma su estado por dovela en F0, el factor en que
  resuelve su equilibrio, y no en el corregido f0·F0.

Hubo una parada tras medir (fase A). La propietaria eligió el lado C de D211 y
confirmó D210. Del τ movilizado pidió «investigar en la documentación y en
internet qué es lo correcto, y analizarlo física y geotécnicamente»; está en
la sección 0.

Cambios en el banco: ningún factor ni ninguna superficie crítica. Solo se
mueven el retroanálisis del 37 (−0,029 %), la σ′max de las filas de Janbu
corregido (ninguna publicada) y los recuentos de −112.

Lo que cambia en el banco de verificación (`_tools/`, `_auditoria/`, fichas)
está fuera de git.

---

## 0. Las fuentes, y lo que se decidió

### D210: las sumas son las del método

Hasta ahora `back_analysis._sums_at_fixed_fos` reconstruía a mano las dos
sumas de Bishop y de Janbu, y es la quinta vez que esa copia se aparta del
solver:
- el brazo del sismo (D170);
- el `n_α` de Janbu (v0.1.202);
- dónde se lee una envolvente curva (D204);
- y ahora el agua, el brazo del peso y el sentido.

Ahora los solvers exponen sus sumas a F fijo y el retroanálisis llama a esas
mismas funciones:
- `bishop.slide_sense`, `bishop.circle_driving_sum` y
  `bishop.x0_resisting_pass`;
- `janbu.slide_sense` y `janbu.horizontal_driving_sum`.

La propietaria decidió el 2026-09-28 que los soportes del modelo entran tal
como los aplica el método, así que la fuerza que se obtiene es la que hay que
AÑADIR al refuerzo que ya existe.

### D211: F0 es el factor de la solución

- **Duncan, Wright & Brandon (2014, Fig. 6.13)** escriben F = f0·F0, con
  «F0 = factor of safety from force equilibrium solution with horizontal
  interslice forces». La corrección es empírica (Janbu 1973, que comparó sus
  procedimientos simplificado y generalizado) y no resuelve nada de nuevo.
- **La documentación de la referencia** obtiene el factor corregido
  «multiplying the Janbu Simplified safety factor for the surface» por f0.
- **Sus dos informes resueltos imprimen el MISMO recuento de cada código**
  para los dos Janbu (Ej_1: 3264 válidas y 91 con −112 en los dos; Ej_2: 146
  con −112 en los dos). Solo un estado formado en F0 da esa igualdad.
  Formado en f0·F0, OGR contaba 90 frente a 92 y 159 frente a 162.

Se midieron dos lados (sección 2):
- **B:** solo el punto fijo de la envolvente y el retroanálisis en F0.
- **C:** todo el estado en F0: columnas, chequeos de m-alpha y de tracción,
  punto fijo, marcha entre dovelas y etapa 1 del desembalse.

B es incoherente por construcción: lee la envolvente en F0 y la comprueba en
f0·F0 (2,4·10⁻² de diferencia). La propietaria eligió C.

### El τ movilizado

- **Duncan, Wright & Brandon (2014, §6.1, Ecs. 6.1–6.2):** τ = s/F es «the
  equilibrium shear stress», la tensión tangencial que mantiene el talud justo
  en equilibrio. Por tanto su F es el de las ecuaciones de equilibrio, que en
  Janbu corregido es F0.
- **El manual de SLOPE/W (2022)** lo dice igual: la cortante de la base de una
  dovela es la movilizada, «the shear strength divided by the factor of
  safety», la que cierra el diagrama de cuerpo libre. Su Janbu es «without any
  empirical correction».
- **Físicamente:** con la N publicada, solo τ_f/F0 cierra el equilibrio
  vertical de cada dovela y el horizontal de Janbu. s/(f0·F0) no es la tensión
  de equilibrio de ninguna solución calculada. Medido en la dovela 0 del test:
  12,16 kN/m frente a 11,96.
- **Lo que no se encontró:** la documentación de la referencia no dice qué
  imprime como «Shear Stress» para Janbu corregido.

**Decisión:** τ_m = τ_f/F0 en la ficha de dovela, en su gráfica y en
`interpretation.slice_rows`. La ficha muestra además el F con que divide, en
una fila nueva, «Factor de seguridad del equilibrio F»: F0 para Janbu
corregido y el factor publicado para el resto.

## 1. Los cambios (motor)

- **`methods/bishop.py`**:
  - `slide_sense`, `circle_driving_sum`, `X0Pass` y `x0_resisting_pass`
    salen de `compute_fos` sin cambiar ninguna operación: bit a bit en 336
    superficies archivadas del banco (factores, columnas y σ′max);
  - la pasada resistente recibe el punto impuesto por una función
    (`LEMMethod._imposed_reader`), que vale `None` si no hay punto que
    imponer.
- **`methods/janbu.py`**:
  - `slide_sense`, `horizontal_driving_sum` y la misma pasada resistente;
  - `f_eq` guarda el F sin corregir;
  - las columnas se forman en él y `details["equilibrium_fos"]` lo publica;
  - interruptor `STATE_AT_EQUILIBRIUM_FOS`.
- **`checks.equilibrium_fos(result)`**: el lector único del factor del estado.
  Lo usan:
  - `base_effective_stresses` y `base_m_alphas`;
  - el punto fijo de D84, a través de la primera;
  - `postprocess.compute_interslice_state`;
  - `rapid_drawdown._stage1_state`;
  - `interpretation.slice_rows` y la ventana de interpretación.
- **`back_analysis.py`**:
  - `_sums_at_fixed_fos(..., project=None)` llama a las funciones del método;
    `_sums_by_hand` conserva las sumas viejas para el A/B del interruptor
    `LOADS_FROM_METHOD`;
  - `required_force(..., project=None)`; `run_back_analysis` pasa su proyecto
    y la interfaz el factorizado;
  - Janbu corregido encuentra su punto en F0;
  - el docstring de `unsupported_fos` dice lo que es: el factor sin la fuerza
    del retroanálisis, con los soportes del modelo (siempre los llevó).
- La tabla `INTERRUPTORES` del banco pasa a 25:
  `back_analysis.LOADS_FROM_METHOD` y `methods.janbu.STATE_AT_EQUILIBRIUM_FOS`.

## 2. Lo medido (censo `_tools/censo_p4_0220.py`, `_auditoria/P4_0220/`)

### D210

- **Fuerza en el factor propio, 335 superficies archivadas** (Bishop sobre
  círculo y los dos Janbu):
  - con las sumas a mano, 208 pasan de 10⁻⁹ del peso: hasta 1,44 veces el peso
    con agua embalsada, 0,61 con soportes, 1,1·10⁻³ en Bishop en seco (el
    brazo) y 1,6·10⁻⁴ con sismo;
  - con las del método, ninguna (la peor, 9,6·10⁻¹¹).
- **El 37** (el único retroanálisis del banco): activa 223,2459 → 223,1814 y
  pasiva 334,8688 → 334,7721 (−0,029 %). Se publican 233,835 y 351. Solo
  cambia el brazo del peso, porque el modelo no tiene agua, soportes ni sismo.
  Se aleja 0,03 puntos del publicado; decide la identidad.

### D211

| | A (hasta 0.1.219) | B | C |
|---|---|---|---|
| −112 en Ej_1 (la referencia da 91 en los dos) | simplificado 92, corregido 90 | como A | 92 y 92 |
| −112 en Ej_2 (la referencia da 146 en los dos) | 162 y 159 | como A | 162 y 162 |
| 34 filas del banco con Janbu corregido, búsquedas en serie | — | como A | 0 factores y 0 superficies críticas cambian; el −112 cambia en 14 filas (1960 → 2059 en total); la σ′max de la crítica, en 32 (hasta −4,8 %, el 012; ninguna publicada) |
| 040 (Perry, la única envolvente curva, superficie dada) | 0,994910 | 0,994886 | 0,994886 |
| Desembalse del Apéndice G con Janbu corregido | 1,33642 / 1,41530 | como A | −0,38 % / −0,87 % |

B coincide con A en todo lo que es Mohr-Coulomb, porque sin envolvente curva el
punto fijo no actúa.

El único veredicto de una superficie archivada que cambia en C es el del
círculo publicado del 012, y no sirve de testigo. En ese círculo OGR no
reproduce los factores publicados (es el caso D60) y el propio Bishop ya lo
rechaza en A. Con los factores de la referencia pasaría en A y en C.

### Coste

A/B en el mismo proceso contra el solver de 0.1.219 cargado aparte: Bishop
−1,0 % (ya no llama a `_imposed_stress` en cada dovela) y Janbu +0,2 %.

## 3. Tests

**`test_back_analysis_loads_v1220.py`, 16 casos.** La fuerza nula en el factor
propio, sin recortar, a 10⁻⁹ del peso y con el solver a 10⁻¹²:
- Bishop en seco sin descuento;
- bajo un embalse, y con sismo;
- con agua en una grieta de tracción;
- con una carga lineal inclinada;
- con un clavo activo y con uno pasivo;
- en el testigo de D112, con Janbu deslizando al revés que Bishop.

Además, la regla 7 del interruptor y los dos llamadores: `run_back_analysis`
con una búsqueda de una sola superficie, y la ventana, por AST.

**`test_janbu_corrected_state_v1220.py`, 16 casos:**
- F = f0·F0 exacto con curva de potencia;
- las columnas, el punto de la envolvente y los chequeos, iguales a los del
  simplificado;
- el equilibrio de cada dovela con τ_f/F0 y el horizontal de Janbu;
- los cuatro círculos de Ej_1 en que los dos Janbu discrepaban;
- la marcha, la etapa 1 del desembalse, `slice_rows` y la fila nueva de la
  ficha;
- la regla 7.

**Contra 0.1.219 fallan 25 de 32:** 20 por comportamiento y 5 por símbolo.
Pasan los dos guardas, los dos controles y los tres casos de la regla 7, que en
el árbol viejo son su comportamiento.

Cambian a propósito, con la razón escrita en el archivo:
- `test_back_analysis_envelope_v1215.py`:
  - se elimina el descuento `_bishop_arm_gap`;
  - el punto de Janbu corregido se busca en F0;
  - el caso que probaba que F/f0 fallaba ahora prueba que falla f0·F0.
- `test_janbu_base_forces_v1107.py`:
  - `_mobilised` divide por el F del equilibrio;
  - el caso de la «elección deliberada» ahora afirma que el conjunto de Janbu
    corregido cierra el equilibrio horizontal de Janbu.
- `test_seismic_convention_v1214.py`: la tolerancia de Bishop pasa a 10⁻⁹ y se
  corrige el comentario, que atribuía el residuo a «la estimación de la
  normal» cuando era el brazo.
- `test_block4_v1202.py`: el mismo comentario.

## 4. Caminos equivocados

- **El testigo −112 salió idéntico en A y en C en la primera corrida (90 y
  90).** No era el motor: la rejilla usa un pool de procesos y el interruptor
  no llega a los hijos. En serie da 92.
- **El censo de búsquedas se colgó 30 minutos en `010/modelo_fem.ogr`.** Ese
  modelo no es una fila del banco: su `resultados` no tiene métodos. El censo
  recorre ahora los `resultados*.json` con Janbu corregido, cada uno con su
  modelo y su tolerancia.
- **El primer A/B de coste** dio Bishop +3,8 % y +2,2 % con controles del 1–2 %.
  No resolvía nada. El micro-A/B por superficie encontró un +1,4 % constante en
  Janbu, que venía de un `import` dentro de la función y de un dataclass por
  pasada. Recortados: −1,0 % y +0,2 %.
- **Seis críticas de búsqueda no circular salían «distintas» en A y en C con el
  factor idéntico bit a bit.** Solo difería el `id` aleatorio anidado en la
  polilínea.

## 5. Lo que se reporta y NO se corrige

- La σ′max archivada de las filas de Janbu corregido queda vieja hasta la
  siguiente corrida del banco (32 de 34 cambian). Ninguna tiene valor
  publicado.
- Los recuentos absolutos de −112 de OGR (Ej_1 92, Ej_2 162) difieren de los de
  la referencia (91 y 146) en los dos Janbu por igual. No es de D211, que solo
  iguala los dos métodos entre sí.

## 6. Verificación

- Selección dirigida de 69 archivos (retroanálisis, Janbu, Bishop, sismo,
  chequeos, marcha, desembalse, interpretación, i18n, soportes): 1172 de 1172.
- Suite entera: **4935 de 4935** (38 min 10 s, con el recorrido en seco del
  banco corriendo a la vez).
- Banco:
  - `d210()` y `d211()` cierran, y dan NO SE SOSTIENE contra 0.1.219;
  - `d204()` pasa a leer el F del punto del propio resultado;
  - el recorrido en seco de los 156 cierres no da ninguna bajada.
