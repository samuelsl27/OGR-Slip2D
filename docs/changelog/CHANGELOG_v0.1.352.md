# OGR Slip2D v0.1.352

**Lo que dicen el solver de filtración, el transitorio, el retroanálisis, el barrido de desembalse y la
calculadora de Hoek-Brown lleva un código estable, y la ventana lo dice en castellano (D335, sexta parte).
Y Calcular agua subterránea ya no lanza una excepción cuando falla el estado inicial de un transitorio
(D341, cerrada).** Decimotercera versión de la tanda P8k.

## 0. Lo que se encontró

- **D341, medido antes de tocarlo** (2026-10-21, en 0.1.349). Si el estado permanente del que parte un
  transitorio no se puede resolver, el solver devuelve un único resultado sin campo, con la razón en
  `notes["error"]`. La ventana calculaba `min()` de ese campo vacío:
  `ValueError('min() iterable argument is empty')` dentro de la ranura de Qt, y la razón no llegaba a
  nadie. Ahora la barra de estado dice la razón del solver, en el idioma de la interfaz.
- **De estas notas, solo tres se traducían:** las tres frases fijas del transitorio (sin etapas, sin
  acoplamiento, estado inicial no convergido), que ya tenían su entrada. El resto no tenía ninguna:
  - las frases con valores («stage 2: some time steps did not converge…», «Picard iteration did not
    converge in 200 steps…»);
  - la que lleva la razón del solver dentro («The groundwater analysis produced no field: …»), que
    `tr()` tampoco podía encontrar;
  - las del barrido, que el cuadro enseñaba tal cual, sin `tr()`;
  - las dos de la calculadora, que se unían tal cual;
  - el aviso de malla con elementos planos y las del retroanálisis.
- **El barrido de desembalse vive en el núcleo** (`ogr_core/statistics/drawdown_sweep.py`), y el núcleo
  no puede importar el motor (D337). Su catálogo va en el núcleo (`ogr_core/statistics/messages.py`), no
  con los del transitorio y el retroanálisis.
- **El retroanálisis tenía una nota que el inventario del plan no contaba:** `composite_skipped`, cuando
  se dejan fuera superficies compuestas. Lleva código como las demás. La ventana sigue sin enseñarla, igual
  que `envelope_not_settled`: eso es **D340**, que sigue abierta.
- **D342 (nueva, abierta):** un campo de filtración guardado pierde los códigos de sus notas al abrir el
  archivo. `SeepageResult.to_dict` escribe la frase inglesa y `from_dict` la lee como `str`, así que
  *Interpretar agua subterránea* las enseña en inglés después de abrir el `.ogr`. Medido con un
  `to_dict`/`from_dict` de ida y vuelta. No es una regresión: antes de esta versión salían en inglés
  siempre. Se reporta y no se corrige aquí.
- **El censo del test encontró tres frases que el inventario no tenía:** las negativas de
  `run_configured_drawdown_sweep` («Enable Rapid Drawdown analysis…») y de `run_configured_back_analysis`
  («The back analysis supports …, not …» y «The target factor of safety must be positive.»). Las tres
  llegaban a los cuadros de negativa de 0.1.350. Las dos primeras tienen ahora su código; la tercera usa el
  de la misma frase del retroanálisis. Su primera versión, además, contaba como frase la docstring de una
  función anidada. Ahora no la cuenta, y lo mismo hacen los censos de 0.1.353 y 0.1.354.
- **`notes["restore_error"]`** (`ogr_core/fem/seepage_data.py`) no lleva código. Nadie lo enseña: es un
  diagnóstico que solo lee quien mira las notas.
- **Un fallo mío de proceso:** lancé el test nuevo en el árbol de trabajo mientras corría la suite entera de
  0.1.350. Era una selección de 17 casos y el resultado no depende de eso, pero la regla es no lanzar tests
  mientras corre la suite. No volví a hacerlo.

## 1. Qué cambia

- **`ogr_fem2d/messages.py`** (nuevo), **15 códigos** `seepage.*`:
  - la malla vacía y los elementos planos;
  - sin condición de altura;
  - los fallos del sistema lineal: directo, en una iteración de Picard y en la resolución final;
  - la cara de rezume sin estabilizar;
  - Picard sin converger, con el rescate desactivado o fallido;
  - el estado permanente inicial que falla o no converge, con la razón anidada o sin ella;
  - el paso de tiempo que falta y la etapa con pasos sin converger.
- **`ogr_slip2d/run_messages.py`** (nuevo), **14 códigos** `run.*`:
  - las cuatro notas del transitorio;
  - las siete del retroanálisis y la negativa del método que no admite;
  - «Could not build the search for: …», con los métodos por su nombre;
  - la negativa del barrido sin desembalse rápido.

  `INITIAL_STATE_NOT_CONVERGED` y `ENVELOPE_NOT_SETTLED_NOTE` siguen existiendo, ahora con su código.
- **`ogr_core/statistics/messages.py`** (2 códigos `sweep.*`) y **`ogr_core/materials/messages.py`**
  (2 códigos `calc.*`), los dos nuevos.
- **La ventana:**
  - la barra de estado de Calcular agua subterránea, permanente y transitorio, pasa la razón del solver por
    `note_text`;
  - también pasan por `note_text`:
    - los avisos del transitorio;
    - el cuadro del barrido;
    - el del retroanálisis;
    - el resumen de *Interpretar agua subterránea* (aviso, estado inicial y malla);
    - las notas de la calculadora.
  - **D341:** un transitorio sin campo dice la razón y no lanza.
  - Las tres reservas sin `tr()` pasan por él: «Back analysis failed.», «sensitivity run failed» y «did not
    converge».
- **El castellano:** 29 entradas nuevas, más las 4 frases fijas que ya la tenían, y 2 para las reservas.

## 2. Tests

- **`tests/test_seepage_run_notes_v1352.py`** (nuevo, 17 casos):
  - **el inglés es el de 0.1.351, byte a byte:** 38 muestras que cubren los 33 códigos. Son las
    expresiones de 0.1.351, leídas de su código fuente y evaluadas con esos valores;
  - cada código tiene su castellano, con los campos de la plantilla; una razón anidada se dice en
    castellano; las reservas pasan por `tr()`;
  - **censo AST** de las 12 funciones;
  - las dos constantes de módulo llevan su código;
  - **en la ventana, en castellano:**
    - Calcular agua subterránea, en un permanente sin ninguna altura impuesta;
    - en un transitorio cuyo estado inicial no tiene ninguna (**D341**: no lanza, y la barra dice la
      razón);
    - el cuadro del barrido;
    - el resumen de *Interpretar agua subterránea*;
    - la calculadora de Hoek-Brown;
  - el API sigue leyendo inglés, y una nota sobrevive al *pickle* de un trabajo.

**Con el código de 0.1.351 fallan los 17.** También los de comportamiento:
- el transitorio lanzaba `ValueError('min() iterable argument is empty')` (D341);
- la barra decía «Análisis de filtración: no Dirichlet (head) boundary condition…»;
- el cuadro del barrido decía «No analysis method selected.»;
- la calculadora decía «D = 2 makes mb undefined…».

## 3. Verificación

- **El test de esta versión**, 17/17. En el primer intento fallaba su censo, por dos cosas del propio test:
  - el nombre `required_force` es también una propiedad del resultado, así que el censo busca primero la
    función del módulo;
  - contaba como frase la docstring de una función anidada.

  Una vez arreglado, el censo encontró las tres frases sin código de las puertas de configuración (§0).
- **Los vecinos:** 547/547, en 35 archivos: el transitorio, la filtración y el agua subterránea, el
  rescate de Picard, el retroanálisis, el barrido de desembalse, la malla con elementos planos, la
  calculadora, el castellano, los mensajes del núcleo, las capas y las licencias.
- **El inglés no cambia:** las 38 muestras del test son la expresión de 0.1.351, evaluada.
- **Suite entera:** 6462/6462, `EXIT=0`, 90 min.
- **Banco:**
  - raíz: `verificar_cierres.py` entero, 88 comprobaciones (una más, `d341`), 0 bajadas. D341 queda
    **CUBIERTO POR TEST**: por la ventana real, sin excepción, un resultado sin campo con el código
    `seepage.initial_failed_why`, y la barra dice la razón del solver;
  - manual 02: `verificar_cierres.py` entero, 238 fichas, 0 bajadas;
  - **D341 retirada** al índice de cerrados, con su sección en `Evaluaciones/0.1.352`;
  - **D342 abierta** en P8;
  - instantánea `Evaluaciones/0.1.352`, prompts (34) y auditorías con 0 ERROR.
- **Ningún número del motor cambia:** solo cambia quién escribe la frase.

## 4. Pendiente

- **D335 sigue abierta.** Siguiente: la estadística y los coeficientes de cálculo (0.1.353).
- **D340** (los avisos que el motor calcula y la ventana no enseña) y **D342** (un campo guardado pierde
  los códigos de sus notas), abiertas.
