# OGR Slip2D v0.1.247

**D230 y D233: el agua y el desembalse de los materiales que enlaza un tramo
de Generalized Anisotropic, y la etapa 1 del desembalse con la resistencia de
su propio modelo.** Hasta 0.1.246, una dovela de un material Generalized
Anisotropic (el padre) tomaba siempre el agua y el desembalse del padre,
aunque su tramo enlazara otro material (el hijo). La referencia tiene una
opción, «usar los parámetros del padre», que decide el agua y deja fuera el
desembalse, que es siempre del hijo. Ahora OGR tiene esa opción, encendida
por defecto, y el desembalse es del hijo.

Al medir esto apareció D233: la etapa 1 del desembalse ponía τ_fc = 0, sin
decirlo, en las bases de un material sin envolvente lineal. No decidía ningún
número hasta esta versión; el desembalse del hijo le abrió un camino, y se
corrige.

Sexta versión de la tanda D226–D232, tras las cuatro de D226 y la de D229.

## 0. Lo que se encontró, y dónde

- **Banco:** 0 de 230 modelos tienen un material Generalized. Seis tienen
  desembalse (095–098 multietapa, 100 y 101 B̄), todos con Mohr-Coulomb. El
  cambio no puede mover un número del banco.
- **La referencia, leída entera** (página de Generalized Anisotropic):
  - la opción del engranaje «use the parent parameters» afecta a los
    parámetros del agua: piezométricas, Hu, la resistencia alternativa,
    las rejillas de presión, el B̄ y la resistencia no saturada;
  - no afecta al desembalse ni al sismo multietapa, que son del hijo;
  - solo existe en la entrada «Angle Range»;
  - en sus archivos recientes viene encendida.

  La nota final de la página («Angle Range uses the water properties of the
  child material») describe la opción apagada. Por eso la ficha leía una
  contradicción que no hay. **Decisión de la propietaria:** la opción,
  encendida por defecto (el agua de siempre, la del padre); el desembalse,
  siempre del hijo.
- **OGR no tiene** la resistencia alternativa sobre la superficie de agua ni
  el sismo multietapa. No hay nada que repartir.
- **Un camino equivocado que se evitó: Ru y el peso.** Ru calcula
  u = ru·σv con el peso específico del material que recibe
  (`material.gamma_at`). Pasarle el hijo como material del agua habría hecho
  que el Ru del hijo multiplicara el peso del HIJO, y el peso es del padre.
  `pore_pressure_at` recibe ahora, aparte, el material del peso.
- **Una decisión donde la referencia es ambigua: el B̄.** Aparece en la lista
  del agua, y el desembalse B̄ es un procedimiento de desembalse. Se toma:
  - el B̄ del exceso de carga va con el agua;
  - el desembalse B̄ entero (la casilla no drenada y su B̄) va con el
    desembalse, del hijo;
  - su presión inicial va con el agua.
- **D233, primera medida** (sin el desembalse del hijo): el cero de la
  etapa 1 no decidía nada.
  - Censo: ningún desembalse multietapa del banco tiene un material no lineal.
  - Caso construido: el Apéndice G con un Power Curve de la misma envolvente
    al lado del espaldón no drenado. En 27 configuraciones, el mismo F a
    2,8e-13 y 0 lecturas de una entrada cero. La diferencia no es del cero:
    sale igual en los Corps, que no leen τ_fc; es el camino que sigue en los
    métodos una envolvente que no es Mohr-Coulomb. La primera redacción de
    la ficha decía «bit a bit», y no lo era.
  - La razón: desde 0.1.66 las fronteras de material son cortes
    obligatorios en las dos etapas. Una base no drenada de la etapa 2 lee
    siempre una de la etapa 1 de su propio material, que tiene que ser
    lineal.
- **D233, segunda medida** (con el desembalse del hijo): el cero sí decide.
  - El Apéndice G hecho de un Generalized de dos tramos, con el límite θ
    barrido cada medio grado: los dos rebanados ponen las bases de una misma
    abscisa a los dos lados del límite, y un tramo sin enlace no tiene
    envolvente lineal.
  - **44 de 726 casos** con F distinto, todos del lado inseguro: hasta
    +0,30 % en Lowe-Karafiath y +0,25 % en Duncan-Wright-Wong. Ninguno en
    los Corps, que leen la envolvente R y no τ_fc.
  - Se corrige como decía el plan; con la corrección, **0 de 726**.

## 1. El motor

- **`GeneralizedAnisotropic`** gana:
  - `use_parent_water`: verdadero por defecto, y un archivo sin la clave lo
    lee verdadero;
  - `rule_index_for_angle(ángulo)` y `linked_material_id(ángulo)`: el tramo
    de una base y el material que enlaza;
  - `replaced(**cambios)`. Lo usan los cuatro sitios que reconstruyen el
    modelo (los coeficientes de diseño, la resolución de enlaces, la
    importación de propiedades y el borrado de la API), que perdían
    cualquier atributo nuevo.
- **El rebanador** (`water_material`, interruptor `slicer.GA_CHILD_WATER`):
  - con la opción apagada, una base cuyo tramo enlaza un material toma el
    agua de ese material: superficie definida en la abscisa, presión,
    política no saturada y exceso de B̄;
  - un tramo sin enlace se queda con el agua del padre;
  - el peso sigue siendo el de la columna, y Ru multiplica el peso del padre;
  - la dovela guarda el material de su agua (`Slice.water_material`;
    `water_material_id` en `to_dict`).
- **Lo que vuelve a preguntar la presión** usa el material del agua de la
  dovela: `design_actions.refresh_pore_pressures` (D226c) y el agua en las
  caras de Lowe-Karafiath y los Corps (`interslice_water_thrust`).
- **El desembalse** (`_drawdown_material`, interruptor
  `rapid_drawdown.GA_CHILD_DRAWDOWN`): en la etapa 1, la etapa 2, el tope
  drenado y el procedimiento B̄, el material de desembalse es el que enlaza el
  tramo, sea cual sea la opción. Dos consecuencias, declaradas:
  - un padre marcado no drenado ya no rechaza todas las superficies;
  - un hijo marcado no drenado deja de drenar.
- **D233** (`rapid_drawdown.STAGE1_OWN_STRENGTH`): donde el material no tiene
  envolvente lineal, τ_fc = s(σ′fc)/F₁, la resistencia con la que la etapa 1
  resolvió esa base (Duncan, Wright y Brandon 2014, ec. 9.3). Se lee como la
  leen los métodos, con el contexto de la base. Para Mohr-Coulomb y sin
  drenaje no cambia nada: la fórmula de siempre.
- **Regla:** `use_parent_water` tiene que ser verdadero o falso
  (`strength_model_refusal`, código `generalized_parent_water`).

## 2. La interfaz y la API

- **Diálogo de materiales.** Casilla «Usar los parámetros de agua del
  material padre» bajo la tabla de tramos. Está en gris mientras ningún tramo
  enlaza un material: un tramo con su propio modelo no tiene agua propia, así
  que la casilla no movería nada (regla 7). Elegir un material para un tramo
  la habilita.
- **API.** `use_parent_water` es un campo más del modelo en `model_define` y
  `material_set`. Si es `false` y ningún tramo enlaza un material, la
  respuesta lo dice en `notes`.
- **Guía del MCP.** Explica la clave nueva. Decía además «22 strength
  models», y desde 0.1.246 (la Step Function) son 23: se corrige.

## 3. Tests

**`tests/test_generalized_child_water_v1247.py`** (22 casos):

- **Identidades en los nueve métodos**, a 1e-12:
  - hijos con el agua del padre dan lo mismo con la opción apagada que
    encendida;
  - un tramo −90..90 que enlaza un hijo con otra piezométrica es, apagada,
    el material simple con la resistencia y el agua del hijo y el peso del
    padre; encendida, el de agua del padre; y las dos difieren (regla 7).
- **A mano:**
  - u por banda de ángulo con dos piezométricas horizontales;
  - un tramo sin enlace conserva el agua del padre;
  - el Ru de un hijo multiplica el peso del padre (ru·γ·z), y con norma
    ru·ξ·γ·z.
- **Desembalse:** el Apéndice G de la EM 1110-2-1902, con su material
  envuelto en un Generalized de un tramo, da su número en los tres
  procedimientos multietapa (con el padre drenante y marcado no drenado) y
  en B̄.
- **D233:**
  - el τ_fc de un Power Curve es (c + a·σ′fc^b)/F₁, a mano;
  - en el límite de banda medido (θ = −20°, Lowe-Karafiath, 50 dovelas), un
    tramo sin enlace da el factor de su gemelo drenante.
- **El contrato de D218:** donde ningún tramo contiene el ángulo, el modelo
  lanza también al buscar el enlace, y el agua de esa base cae en el padre.
- **Interruptores, archivo, `replaced`, regla, API y diálogo.**

**Discriminación** contra `git archive` 2318ae3 (0.1.246), con el runner de
ese árbol: **21 de 22 fallan**.

- Tres por comportamiento:
  - el Apéndice G envuelto da 2,0216 frente a 1,4455;
  - el B̄, 2,0216 frente a 0,8134;
  - el τ_fc del Power Curve, 0 frente a 890,6.
- El resto, por símbolo.
- El que pasa allí («un tramo sin enlace es su gemelo») lo hace por otra
  razón: en 0.1.246 el núcleo hijo ni siquiera drenaba. Lo discrimina su caso
  con el interruptor apagado.

## 4. El banco

- **Censo** (`_auditoria/P4_0247/censo_d230_d233.json`): ningún modelo con
  Generalized; ningún desembalse multietapa con un material no lineal.
- **A/B árbol contra árbol de todo el 02** (`ab_d230.py`, 2318ae3 frente a
  este): 194 modelos, **0 de 1821 números distintos**.
- **Medidas de D233** (`mide_d233.py`, `mide_d233_banda.py`), archivadas con
  el motor que las hizo.
- **`d230()` y `d233()`**, CUBIERTO POR TEST. Las dos se comprueban en vivo y
  contra el motor de 0.1.246.
- **`INTERRUPTORES`** gana los tres interruptores (40 en total).
- **Una bajada que lo era: D218.** La primera verificación entera de cierres
  dio NO SE SOSTIENE en D218 (Generalized no devuelve τ = 0 sin decirlo). Su
  parte en vivo se sostenía; lo que caía era la comprobación del código, que
  busca en la clase un `except` que devuelva `None`. Lo había:
  `rule_index_for_angle` contestaba «ningún tramo» donde la regla de D218 es
  que el modelo LANZA y nunca contesta en lugar de un tramo que no tiene. No
  se tocó la comprobación: se corrigió el código. El modelo lanza también
  ahí, y quien busca el hijo del agua (`slicer._linked_child`) atrapa la
  excepción con la razón escrita (en esa base la resistencia lanza igual y
  la superficie se rechaza). Un caso nuevo del test lo fija, y D218 vuelve a
  CUBIERTO POR TEST.
- **Ciclo de cierre:**
  - `verificar_cierres.py`: 218 cierres y 0 bajadas;
  - instantánea `Evaluaciones/0.1.247`;
  - D230 y D233 retiradas al índice, podadas de `PAQUETES` y tachadas en la
    cadena P4, que queda con D231 → D249;
  - prompts regenerados (42);
  - auditorías con 0 ERROR en el 02 y en la raíz;
  - instantánea rehecha con `--forzar`;
  - `--seco` completo después de retirar.
- **D249 abierta** en P4, al final, con su censo y su medida (§5).

## 5. Lo que se reporta y NO se corrige

- **La adherencia de los soportes lee el agua del padre.** En un punto del
  soporte no hay base de dovela, así que no hay tramo que elija hijo.
- **Un tramo sin enlace no tiene material de desembalse**: el padre lo
  representa. Un padre marcado no drenado sigue rechazando la superficie
  donde una base no drenada cae en un tramo sin enlace, porque un
  Generalized no tiene envolvente lineal.
- **Ru calcula σv como el peso específico del material de la base por la
  profundidad entera**, no integrando la columna capa a capa. Es anterior a
  esta versión y no es de D230; se abre como ficha propia con su medida.

## 6. Verificación

- **Suite entera:** 5482 de 5482, en 61,2 min, con verificaciones del
  banco en paralelo. La primera corrida, antes del caso de D218, dio
  5481 de 5481 en 56,5 min.
- **Selección** de Generalized, desembalse, norma de diseño, presiones,
  anisótropos, diálogos y tablas de materiales, importación, i18n,
  catálogo, `model_define`, operaciones de la API, rebanador, datos de
  dovela, interpretación, exceso, Ru, B̄ y agua: 678 de 678.
- **Test nuevo:** 22 de 22. Discriminación: 21 de 22 contra 0.1.246.
- **Banco:** censo, A/B (0 de 1821), las medidas de D233 (27 de 27 por la
  frontera; 44 de 726 con el cero y 0 con la corrección por el límite de
  banda) y `d230()` y `d233()`, que dicen NO SE SOSTIENE contra el motor de
  0.1.246.

**Qué falta por probar:**
- **Un caso publicado con un Generalized cuyos hijos tengan otra agua:**
  ningún problema de los manuales lo usa.
- **La casilla en la aplicación real**, con un usuario: solo se ha probado el
  diálogo sin pantalla.
