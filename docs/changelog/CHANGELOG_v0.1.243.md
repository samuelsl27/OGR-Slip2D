# OGR Slip2D v0.1.243

**D226b: cada carga lleva su acción, y la norma la factoriza entera según si
empuja o resiste.** Hasta 0.1.242, la copia de análisis multiplicaba todas las
cargas por γQ, fueran lo que fueran y actuaran donde actuaran. Con EN 1997-1
DA1-C1, una carga variable sobre la parte del talud que se opone al
deslizamiento tomaba 1,5 donde la Tabla A.3 da γQ,fav = 0. Además, una carga
permanente no se podía declarar.

Ahora cada carga es permanente o variable. El motor la clasifica entera por lo
que hace al deslizamiento de cada superficie y la multiplica por γG o γG,fav,
o por γQ o γQ,fav.

Tercera versión de la tanda D226–D232, y la segunda de las cuatro de D226. La
ficha sigue abierta hasta D226d.

## 0. Lo que se encontró, y dónde

### La premisa, medida con 0.1.242

Talud φ = 0 de `test_tension_crack_truncation_v1109` (c 40, γ 19, seco), con su
círculo (55; 58) R 34, Bishop a 1e-12 y 160 dovelas. Lleva dos cargas
verticales de 20 kPa: una en la meseta (x 62–78), que empuja, y otra en el
paramento (x 42–52), a la izquierda del punto bajo del círculo, que va contra
el deslizamiento.

«Esperado» es el modelo hecho a mano con la Tabla A.3:

| | Característico | DA1-C1 con 0.1.242 | DA1-C1 esperado | DA1-C1 con 0.1.243 |
|---|---|---|---|---|
| sin cargas | 1,110927 | 0,822909 | — | 0,822909 |
| meseta | 1,029541 | 0,756465 | 0,756465 (× 1,5) | 0,756465 |
| paramento | 1,140972 | **0,847712** | 0,822909 (× 0) | **0,822909** |
| las dos | 1,055294 | **0,777374** | 0,756465 | **0,756465** |

La carga que resiste salía del lado inseguro: un +3,0 % sola y un +2,8 % con la
otra.

### Una carga es una acción

El plan fijaba la clasificación por carga ENTERA, y la ayuda de la referencia
no da otro criterio que si la fuerza es «favorable o desfavorable para evitar
que la superficie se movilice».

Una carga es una sola acción de una sola fuente, y lleva un factor:

- el de «empuja» si la componente de todo lo que pone sobre la masa, en la
  dirección del deslizamiento, es positiva:
  Σ_i s·(f_v,i·sen α_i − f_h,i·cos α_i) > 0;
- el de «resiste» si no lo es.

Es la misma lectura de «empuja» que tiene el peso del suelo dovela a dovela. La
casilla de fuente única es del peso del suelo y no llega a las cargas.

Medido en el mismo talud con una carga que cruza el punto bajo (x 48–60, sobre
el paramento):

- entera resiste y sale fuera: 0,822909;
- dibujada como dos cargas, la mitad de la derecha empuja (× 1,5) y da
  0,818939, un −0,48 %.

Es la diferencia entre las dos lecturas y se queda declarada.

### Los otros dos lectores de las cargas, y lo que les pasa

Las cargas salen de la copia: ya no se multiplican allí. Hay dos lectores más
de sus magnitudes:

- **El exceso de presión intersticial** (`load_delta_sigma_v`, el B̄ de carga).
  Hasta 0.1.242 leía todas las cargas × γQ; desde esta versión las lee sin
  factorizar. Lo factorizará D226c, en la pasada final que recalcula u donde
  el material lee el peso: cada carga necesita su clase, que depende de la
  superficie. **Hasta entonces es un hueco declarado**, y en el banco no
  muerde: ningún modelo tiene norma.
- **La σ′v con que un anclaje calcula su adherencia** (`bond.sigma_v_effective_at`).
  También pasa a leer las cargas sin factorizar. Es lo que la referencia hace
  por defecto con las permanentes («no se consideran, porque aumentan la
  tensión efectiva»), y lo que el plan quería para las variables. La casilla
  que añade γG a los anclajes llega con D226d.

### El banco no tiene ninguna norma, pero sí cargas

El desglose por carga del rebanador pasa por todo modelo con cargas, con norma
o sin ella. Para comprobar que no mueve un bit no hay interruptor que sirva, y
se hizo un A/B **árbol contra árbol**: el mismo guion con `git archive`
502634e (0.1.242) y con este árbol.

Fueron los 13 modelos del 02 con cargas, 9 con repartidas y 4 con puntuales,
con los círculos publicados y las críticas archivadas: 82 números en 238 hojas,
**0 distintos**.

## 1. El motor

- **`ogr_core/loads`:**
  - `LoadAction` (PERMANENT / VARIABLE) y el campo `action` en
    `DistributedLoad` y `LineLoad`, al final para no romper una construcción
    por posición;
  - variable por defecto, como los diálogos de la referencia;
  - una carga sin la clave en el archivo es variable.
- **Ajustes.**
  - `factor_variable_favourable` (γQ,fav): 0 en los cuatro presets del
    Eurocódigo y 1 en «none». Los presets pasan a diez columnas.
  - Un archivo sin la clave es anterior: un estándar con nombre toma el valor
    de su preset, y uno personalizado su propio `factor_variable`, que es lo
    que llevaba cada carga, así que sus números no se mueven.
- **`ActionFactors`** gana γQ y γQ,fav y `factors_loads`.
  - `is_identity()` se parte en `weight_is_identity()` y `loads_are_identity()`.
  - `load_factor_for(action, drives)`.
- **`design_factors.LOADS_BY_ACTION`** (el interruptor, el 35.º de
  `INTERRUPTORES`).
  - Encendido, la copia no toca las cargas y su nota dice cómo se factorizan.
  - Apagado, el comportamiento de 0.1.242: todas × γQ en la copia.
- **Rebanador.**
  - `_surface_pressures_at` da la presión de cada carga.
  - `_surface_pressure_at` es su suma con `_summed`, en el mismo orden y desde
    0.0: bit a bit la de siempre.
  - `distributed_loads_on` devuelve también la carga.
  - Cada dovela guarda `load_parts`, el registro de lo que puso cada carga
    `(id, acción, f_v, f_h, y)`, sin aplicarlo otra vez.
  - Las componentes de una carga puntual se calculan una vez, no dos.
- **`design_actions.load_factors`** clasifica cada carga entera.
  - `apply_action_factors` multiplica lo que puso: la parte vertical, en el
    peso y no en el del suelo, así que el sismo sigue sin alcanzarla; la
    horizontal, en el canal externo, momento incluido.
  - `Slices.load_factors` dice, por carga, `(acción, empuja, factor, nombre)`.

## 2. La regla

`rules.design_action_factors_refusal` pide también γQ ≥ 1 ≥ γQ,fav ≥ 0. Aquí el
0 vale: es el valor de la norma. Hay tres códigos nuevos, y el argumento es el
mismo: lo que empuja crece y lo que resiste mengua, así que el balance que
decidió el sentido de deslizamiento solo puede crecer.

El límite de la API para γQ,fav va de 0 a 10. El diálogo limita γQ a [1, 10]
y γQ,fav a [0, 1].

Un archivo personalizado con γQ < 1, que hasta ahora corría, se rechaza con
la razón.

## 3. La interfaz, la API y el informe

- **Diálogos de carga.**
  - «Acción de la carga» con dos opciones: «Variable (sobrecarga de uso)» y
    «Permanente (carga muerta)».
  - Visible solo con la norma activada, como en la referencia. Oculto, se
    conserva lo que la carga tenía (regla 7).
  - La ventana la aplica al crear y al modificar.
- **Diálogo de la norma.** Acciones variables, desfavorables y favorables.
- **API.**
  - `load_set(action=...)`, con una nota si no hay norma.
  - El MCP expone el parámetro, y la guía de herramientas lo dice.
- **Lo que lee el resultado.** Si una carga empuja depende de la superficie,
  así que se dice por superficie, no por corrida:
  - el resumen de la API (`load_factors`, con nombre, acción, si empuja y
    factor);
  - el PDF (una fila por carga en el mínimo global de cada método);
  - el panel de resultados de la ventana (líneas bajo la cabecera).

## 4. Tests

**`tests/test_load_actions_v1243.py`** (23 casos):

- **Tabla A.3 como identidades en los nueve métodos:**
  - una variable favorable da el modelo sin ella;
  - una desfavorable, el de magnitud × 1,5;
  - una permanente, × 1,35 y × 1,0;
  - las dos juntas.
- **Las horizontales:** hacia fuera del talud empuja y hacia dentro resiste.
- **Una carga es una acción:**
  - la que cruza el punto bajo lleva un solo factor, el de su balance,
    calculado aparte;
  - sus dos mitades como dos cargas dan otro número.
- **Nada más se mueve:**
  - sin norma, las partes suman el peso de las cargas y
    `_surface_pressure_at` es la suma de las partes;
  - el sentido de deslizamiento no cambia.
- **Regla 7:**
  - la acción mueve el número, y γQ,fav también;
  - el diálogo enseña la acción solo con norma y la conserva oculta.
- **Los archivos:**
  - una carga sin acción es variable;
  - unos ajustes sin γQ,fav toman 0 con un Eurocódigo, su γQ si son
    personalizados y 1 con «none»;
  - un archivo personalizado de 0.1.242 da su número;
  - los presets.
- **La regla:** sus códigos, y el 0 por la API y el diálogo.
- **Lo que lee el resultado:**
  - el resumen de la API, y la nota de `load_set` sin norma;
  - las filas del PDF y las líneas del panel.
- **Apagado e intacto:**
  - con el interruptor apagado, otra vez 0,847712;
  - las cargas del usuario no se tocan.

Las cargas variables de los ayudantes se construyen sin `LoadAction`, para que
la discriminación falle por comportamiento.

**Discriminación** contra `git archive` 502634e (0.1.242), con el runner de ese
árbol: **21 de 23 fallan**, 6 por comportamiento y 15 por símbolo. Los 6 son:

- la favorable que no salía fuera (0,847712 frente a 0,822909);
- las dos juntas;
- las horizontales;
- las dos mitades;
- γQ,fav;
- los códigos de la regla.

Pasan los dos controles: el sentido y el archivo personalizado de 0.1.242.

## 5. El banco

- **Censo:** 0 de 230 modelos con la norma activada (el de 0.1.242 sigue
  valiendo).
- **A/B árbol contra árbol** (`_auditoria/P4_0243/ab_d226b.py`, con su
  `--comparar`): 13 modelos con cargas, **0 de 82 números distintos**.
- **`INTERRUPTORES`** gana `ogr_core.project.design_factors.LOADS_BY_ACTION`,
  el primero que vive fuera de `ogr_slip2d`. `_Contexto._sitio` acepta ahora
  una ruta entera que empiece por `ogr_`. Comprobado: encuentra los 35, los
  apaga y los restaura.
- **D226 no se cierra:** su cierre llega con D226d. La ficha registra la
  medida y lo hecho.

## 6. Lo que se reporta y NO se corrige

- **El exceso de presión intersticial lee las cargas sin factorizar** hasta
  D226c (ver §0).
- **Una carga que cruza el punto bajo se clasifica entera** (−0,48 % frente a
  partirla, en el ejemplo). Es la regla del plan y se queda.

## 7. Verificación

- **Suite entera:** 5418 de 5418, en 39,5 min, con la verificación de los
  cierres en paralelo.
- **Selección** de cargas, la carga hacia arriba, exceso de presión
  intersticial, normas de diseño, Tutorial 21, m6, adherencia, API y operaciones,
  e i18n: 277 casos en verde antes de cambiar las etiquetas idénticas al
  castellano. MCP: 20 de 20.
- **Test nuevo:** 23 de 23. Discriminación: 21 de 23 contra 0.1.242.
- **Banco:**
  - censo, A/B árbol contra árbol (0 de 82) e `INTERRUPTORES`;
  - `verificar_cierres.py` entero: 214 cierres y 0 bajadas;
  - instantánea `Evaluaciones/0.1.243`;
  - prompts regenerados (44);
  - auditorías de invariantes con 0 ERROR en el 02 y en la raíz;
  - instantánea rehecha con `--forzar`.

**Qué falta por probar:**
- **El combo en la aplicación real:** activar la norma, dibujar una carga
  permanente y ver la línea del panel. Lo cubren los tests del diálogo y del
  panel, no la ventana.
- **Un caso publicado con cargas y norma:** el Tutorial 21 no tiene cargas, y
  ningún ejemplo del banco usa norma.
