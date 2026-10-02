# OGR Slip2D v0.1.242

**D226a: el γG de la norma de diseño multiplica el peso de cada dovela.**
Hasta 0.1.241, `factor_permanent` se leía y no se aplicaba. Con el preset
DA1-C1, el tutorial de Eurocódigo 7 de la referencia daba el característico,
1,36, donde publica 1,207.

Ahora el rebanador multiplica el peso del suelo de cada dovela en la copia de
análisis. Por defecto, con la fuente única, todas las dovelas toman γG. Con la
casilla desmarcada, γG va a las dovelas cuya base empuja el deslizamiento y
γG,fav a las que van contra él. Con la casilla desmarcada, el tutorial da
1,2042 (−0,23 %).

DA3 pasa a las acciones de A2, y una regla impide factores que inviertan el
sentido de deslizamiento.

Segunda versión de la tanda D226–D232, y la primera de las cuatro de D226. La
ficha sigue abierta hasta D226d.

## 0. Lo que se encontró, y dónde

### La premisa, medida con 0.1.241

El Tutorial 21 de la referencia es el ejemplo 5.12 de Smith (2006). Es una
presa de tierra con γ = 19,2, c′ = 12 y φ′ = 20°, con filtración permanente
por elementos finitos y Bishop. Se montó por la capa de operaciones:

| | Publicado | OGR 0.1.241 |
|---|---|---|
| F | 1,37 | 1,36028 (−0,71 %) |
| DA1-C1 | 1,207 | **1,36028**: el preset no hacía nada |
| DA1-C2 | 1,096 | 1,08802 (−0,73 %) |

Sobre el círculo crítico, con los pesos multiplicados a mano:

- **todas las dovelas × 1,35** daban 1,2318 (+2,06 %);
- **× 1,35 solo las que empujan** daban **1,2042 (−0,23 %)**. Las cinco dovelas
  del pie, cuya base va contra el deslizamiento, quedaban × 1,0.

El tutorial es anterior a la casilla de fuente única de la referencia y cuadra
con la regla por dovela. La captura del diálogo actual de la referencia
muestra la casilla marcada.

**Decisión de la propietaria (2026-10-02):** casilla marcada por defecto, como
el diálogo actual y como Frank et al. (2004), y el tutorial se ancla con la
casilla desmarcada.

### Lo que dice la referencia, y lo que no se copia

La ayuda de la referencia parte la masa por la vertical del punto más bajo de
la superficie. A un lado el peso empuja y al otro resiste. La casilla de
fuente única aplica el factor desfavorable a todo el peso, porque el suelo es
una sola acción de una sola fuente (Bond et al. 2013). La ayuda dice además
que un mismo peso por dovela alimenta todos los términos.

En el código no se cita el texto de la casilla: los comentarios lo parafrasean
(regla de `docs/reference/`).

### DA3 llevaba las acciones de A1

En un talud, DA3 factoriza las acciones geotécnicas con A2: 1,0 y 1,3. Frank
et al. (2004, §11.5) dan γG = 1,00 en DA-1C2 y en DA-3, así que en un talud
DA3 es DA1-C2. El preset llevaba 1,35 y 1,5, los de A1.

### Por qué las búsquedas no daban F/1,25 en DA1-C2

Con 0.1.242, DA1-C1 por dovela da 1,203509 y DA1-C2 1,088017 en la búsqueda
Auto Refine, sobre el mismo círculo que el característico. Evaluado ese círculo
con Bishop a 1e-12, salen 1,20419 y 1,08822, y DA1-C2 es F/1,25 a 7e-11.

La diferencia es la tolerancia de 0,005 del proyecto. Bishop se para antes, en
un valor que depende de dónde empezó la iteración: con la tolerancia del
proyecto, el círculo crítico característico da 1,360145 evaluado solo y
1,360280 en la búsqueda. No es un defecto.

### La copia de análisis lleva la filtración con 9 cifras

Con la norma activada, factores de material iguales a 1 y el interruptor nuevo
apagado, las presiones intersticiales de la copia difieren de las del modelo:

- hasta 5e-9 relativo en 23 de 25 dovelas del tutorial;
- F difiere en 6,6e-11.

La copia se hace por el formato de archivo (`Project.from_dict(project.to_dict())`),
y `SeepageResult.to_dict` guarda las alturas con 9 cifras significativas a
propósito. Es el mismo ida y vuelta que el changelog de 0.1.194 ya reportó como
ampliación del alcance de D182. Se dice y no se cambia; los tests del tutorial
comparan las presiones a 1e-6 kPa y lo explican.

## 1. El motor

- **`ogr_core/loads/actions.py`** (nuevo): `ActionFactors`, una clase congelada
  con γG, γG,fav y la fuente única, más `is_identity()` y `factor_for(drives)`.
  - Son números neutros: el motor lee factores, nunca el nombre de una norma.
- **`apply_design_factors`** sella la copia con `factored.action_factors`.
  - `Project.action_factors` es None en un modelo.
  - El sello no se guarda en el archivo.
  - Sobrevive a `deepcopy` y a pickle, que es como lo recibe cada muestra
    estadística y cada proceso de la búsqueda en paralelo.
- **`ogr_slip2d/design_actions.py`** (nuevo):
  - `sliding_sense(slices)` es el signo de Σ W·sen α sobre las dovelas sin
    factorizar (`bishop.slide_sense(slices, 0)`).
  - `apply_action_factors` multiplica el peso del suelo
    (`weight += (ξ−1)·soil_weight`, `soil_weight *= ξ`).
  - Guarda `Slice.weight_factor` y `Slices.design_sense`.
- **Rebanador.** Al final de `slice_surface`, con todas las dovelas hechas y
  antes del agua de la grieta, que no se factoriza.
  - Tampoco se factorizan las cargas ni el agua embalsada.
  - El sismo (kh·W y W·(1+kv)) y la σ′v de Vertical Stress Ratio y SHANSEP
    siguen al peso factorizado sin tocar nada más.
- **Interruptor `ogr_slip2d.slicer.DESIGN_WEIGHT_FACTORS`.** Apagado, el
  comportamiento de 0.1.241. Entra como el 34.º en `INTERRUPTORES` del banco.
- **Ajustes.** `DesignStandardSettings` gana `factor_permanent_favourable`
  (γG,fav) y `single_source_weight` (True).
  - Los presets pasan a nueve columnas.
  - DA3 lleva 1,0 y 1,3 (`OLD_PRESET_ACTIONS` guarda lo que llevaba).
  - Un archivo sin `single_source_weight` es anterior. Un DA3 con 1,35/1,5
    recibe las acciones corregidas; uno personalizado conserva sus números.
- **Notas del informe de coeficientes.** «Soil weight: the permanent-action
  factor X multiplies the weight of every slice (single source assumption)»,
  o la versión por dovela. La nota de que el factor permanente «no se aplica»
  desaparece.

## 2. La regla

`rules.design_action_factors_refusal` exige valores finitos y
γG ≥ 1 ≥ γG,fav > 0:

- **La razón matemática.** Con el sentido s decidido sobre las dovelas sin
  factorizar, s·Σ ξ·W·sen α = Σ_empujan γG·W·|sen α| − Σ_resisten γG,fav·W·|sen α|
  ≥ s·Σ W·sen α > 0. Ninguna dovela cambia de lado al factorizar.
- **Lo que significan las palabras.** Un factor desfavorable menor que 1 o uno
  favorable mayor que 1 hacen el cálculo menos seguro que el característico.
  EN 1990 (Tabla A1.2) y EN 1997-1 (Tablas A.1, A.3, A.15 y A.17) nunca lo
  hacen.

La preguntan tres sitios:

- **el análisis** (`check_analysis_settings`), solo con la norma activada;
- **la API**, solo si el lote toca la norma: un valor guardado es asunto del
  análisis, no razón para rechazar otra edición;
- **los límites del diálogo** (`PERMANENT_ACTION_FACTOR_BOUND`).

## 3. La interfaz, la API y el informe

- **Diálogo de la norma.**
  - «Acciones permanentes, desfavorables» y «favorables».
  - La casilla de fuente única, abierta también con una norma con nombre: dice
    cómo se reparten los factores, no cuáles son.
  - Con la casilla marcada, γG,fav aparece en gris, porque nada lo lee
    (regla 7).
  - Cadenas por `tr()`, con su entrada en español.
- **Datos de dovela.** La fila «Factor de peso» en el panel de interpretación,
  en `slice_rows`, en la tabla de la API y en `Slice.to_dict`.
- **Informe PDF.**
  - `generate_report(..., factor_report=)` recibe el informe de coeficientes
    de la corrida, no los ajustes, que pueden haber cambiado después.
  - Con coeficientes aplicados, una sección «Design Standard» con sus notas, y
    el número se llama «Over-design Factor».
  - La tabla de dovelas gana la columna del factor cuando lo hay.
  - La ventana y la operación `report_generate` pasan el informe de su
    corrida.

## 4. Tests

**`tests/test_design_weight_factors_v1242.py`** (28 casos) recoge las
identidades analíticas:

- **Frank et al. (2004, §11.5)** en los nueve métodos, sobre un talud sin
  drenaje y seco: DA1-C1 da F/1,35, DA2 F/1,485, y DA1-C2 y DA3 F/1,4.
- **Homogeneidad.**
  - Con c′ = 0 y seco, Γ = F; con Vertical Stress Ratio, Γ = F.
  - Con φ = 0 y kh, Γ = F/1,35: el sismo sigue al peso.
- **Por dovela.**
  - Los pesos a cada lado del punto más bajo son exactamente γG o γG,fav
    veces los característicos.
  - Bishop converge a la forma cerrada c·L·R / (γG·M_empuja − γG,fav·M_resiste),
    con las integrales partidas en x = x_c. El error baja de 40 a 160 y a 640
    dovelas, y queda por debajo de 1e-5.
  - Un control comprueba que esa forma no es la de la fuente única.
- **El sentido** sobrevive a γG = 10 y γG,fav = 0,1, en los dos sentidos de
  rotura, y el espejo da el mismo factor.
- **Regla 7:**
  - la casilla mueve el número;
  - γG,fav lo mueve solo con la casilla desmarcada (−1,1 %);
  - el diálogo deja γG,fav en gris con la casilla marcada, y la casilla está
    abierta también con una norma con nombre.
- **Presets y archivos:**
  - DA3 es DA1-C2;
  - las acciones de la Tabla A.3;
  - un DA3 viejo se migra y uno personalizado no;
  - el ida y vuelta conserva los valores.
- **La regla:**
  - sus cuatro códigos y todos los presets aceptados;
  - el análisis y la API la preguntan, la API solo si el lote toca la norma;
  - los límites del diálogo son el de la regla.
- **Lo que lee el resultado:** las tablas de dovelas, el panel, las notas y la
  columna del PDF.
- **Apagado y modelo intacto:**
  - con el interruptor apagado, el número de 0.1.241;
  - el proyecto del usuario no se toca: sin sello, mismo `to_dict`, sus
    dovelas con factor 1.

**`tests/test_tutorial21_eurocode_v1242.py`** (5 casos) es el ancla externa.
El Tutorial 21 se monta por la capa de operaciones y se evalúa sobre el círculo
crítico característico, con Bishop a 1e-12:

- F = 1,36028 frente a 1,37, a menos del 1 %;
- DA1-C1 por dovela 1,20419 frente a 1,207, con las cinco dovelas del pie a
  1,0;
- DA1-C1 con fuente única: los pesos son exactamente 1,35 veces y el factor
  queda entre los otros dos;
- DA1-C2 1,08822 frente a 1,096, y F/1,25 a 1e-9;
- con el interruptor apagado, DA1-C1 vuelve al característico.

Unos 10 s.

**Discriminación** contra `git archive` 307f85d (0.1.241), con el runner de ese
árbol: **27 de 33 fallan**, 15 por comportamiento y 12 por símbolo. Pasan los
seis controles:

- el archivo personalizado;
- el espejo;
- c′ = 0;
- Vertical Stress Ratio;
- DA1-C2;
- el característico.

**Cambian a propósito:**

- **`test_m6_v157::test_da1c1_leaves_an_unloaded_model_alone`** pasa a
  `test_da1c1_factors_the_weight_of_an_unloaded_model`. Su premisa, «sin cargas
  no hay nada que factorizar», era el defecto. Comprueba lo que quería
  comprobar con el interruptor apagado (bit a bit) y que, encendido, el factor
  baja: 0,8960 → 0,8145 en Ej_1.
- **`test_design_factors_categories_v1226`.**
  - `test_da2_applies_its_resistance_factor` mide γR;e con γG = 1; la identidad
    entera de DA2 está en el test nuevo.
  - `test_the_permanent_factor_is_said_not_applied` pasa a
    `test_the_permanent_factor_is_said`.

## 5. El banco

- **Censo** (`_auditoria/P4_0242/censo_norma.py`, leído del JSON sin pasar
  por el cargador): 230 modelos, **0 con la norma activada**. Los guiones del
  banco tampoco la activan. El cambio no puede mover un número del banco, así
  que no hay A/B que hacer.
- **El cierre `d224()` miraba en vivo «DA2 da F/1,1»**, y con D226a DA2 lleva
  además γG = 1,35. Se cambia como el test v1226: DA2 con γG = 1.
- **El Tutorial 21:** medidas, guiones y discriminación en
  `_auditoria/P4_0242/`.
- **D226 no se cierra:** su cierre `d226()` llega con D226d. La ficha registra
  lo hecho.
- **Ciclo del banco:**
  - `verificar_cierres.py` entero: 214 cierres y 0 bajadas; `d224()`, `d93()`
    y `d232()` siguen CUBIERTO POR TEST;
  - instantánea `Evaluaciones/0.1.242`;
  - prompts regenerados (44);
  - auditorías de invariantes con 0 ERROR en el 02 y en la raíz;
  - instantánea rehecha con `--forzar`.

## 6. Lo que se reporta y NO se corrige

- **Ru no sigue al peso factorizado.** u = ru·σv se calcula al rebanar, con el
  peso sin factorizar. La referencia dice que un mismo peso alimenta todos los
  términos, la presión intersticial incluida. Ya está planificado: es D226c,
  con el B̄ de carga y el empuje entre dovelas de Lowe-Karafiath.
- **La copia de análisis por el formato de archivo** (ver §0). Ya reportado en
  0.1.194.

## 7. Verificación

- **Suite entera:** 5395 de 5395, en 47,5 min, con la verificación de los
  cierres en paralelo.
- **Selección** de normas de diseño, API de ajustes, CLI, operaciones,
  enlaces Generalized, filtración, m6, ajustes del proyecto, estadística con
  norma, superficies del usuario, i18n, versiones y menús: 385 casos, 383 en
  verde antes de cambiar los dos tests a propósito.
- **Tests nuevos:** 28 de 28 y 5 de 5. Discriminación: 27 de 33 contra
  0.1.241.
- **Banco:** censo (0 de 230), `d224()` corregido y el ciclo completo (214
  cierres, 0 bajadas).

**Qué falta por probar:**
- **El diálogo en la aplicación real:** marcar y desmarcar la casilla con
  DA1-C1 y ver el factor del tutorial moverse de 1,23 a 1,20. Lo cubren los
  tests de la página, no la ventana.
- **El PDF entero con norma:** se comprueba la tabla de dovelas, no el
  documento generado.
- **Un caso publicado por dovela con fuente única:** nada publica 1,2318.
