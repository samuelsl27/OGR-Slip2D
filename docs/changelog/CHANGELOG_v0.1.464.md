# OGR Slip2D v0.1.464

**El método de Sarma, registrado (D357, tercera de las siete versiones).** `ogr_slip2d/methods/sarma.py` es el décimo
método del registro. Tiene sus propios ajustes (`settings.sarma`), lo construye `build_method`, y las búsquedas lo
analizan sobre sus cuñas (`search._wedge_trial`), que se construyen sobre las mismas dovelas que han pasado todos los
filtros. Ningún factor de los nueve métodos cambia, y un proyecto sin Sarma no mueve su huella.

Por las decisiones de la propietaria (2026-11-16):
- **la bisectriz es la política por defecto.** Una cara de política que se cruzaría con su vecina, o que no llegaría al
  terreno, se trata así, con una nota:
  - si es de una división uniforme, se quita con su frontera;
  - si es de un vértice, un contacto o un corte del freático, pasa a vertical, una por par.

  Esta segunda forma es la decisión tras la revisión; la primera ponía verticales todas y encadenaba;
- **`sarma.num_slices` es un ajuste propio**, el mínimo de cuñas, con su ayuda;
- **el corte en el nivel freático se queda;**
- **una cara por un material sin drenaje lleva c̄ = cu y φ̄ = 0.** Los demás materiales que no son Mohr–Coulomb se
  siguen rechazando en una cara, como dice la spec, y la suite salta a Sarma solo cuando rechaza por ese código;
- **una sola versión.**

## 0. Lo que se encontró

### El censo, antes de escribir

Tres exploraciones (solo lectura), sobre 0.1.463:
- **41 archivos de tests recorren el registro:**
  - 23 pasan si Sarma lee unas dovelas verticales dadas como cuñas de caras verticales;
  - 7 piden detalles concretos;
  - 4 llevan soportes;
  - 7 son censos o particiones.

  Hay 14 `assert len(...) == 9`.
- **Lo que el motor no esperaba:**
  - `num_slices` no llega a ningún método, solo a la búsqueda;
  - los envoltorios de desembalse esconden los atributos de la clase y vuelven a rebanar en vertical;
  - `SliceStore` perdía los campos de `Wedges` al volcar;
  - el botón Aplicar del diálogo quita un método que no tiene casilla;
  - `MethodsSettings(**datos)` revienta con una clave desconocida;
  - `model_hash` es el SHA-256 de todo `to_dict()`;
  - ningún método rechaza soportes, y no había mecanismo que reutilizar.

### Al registrar

- **Los materiales que no son Mohr–Coulomb en la suite.** Unos 20 casos de los tests del registro usan materiales sin
  drenaje, anisótropos, SHANSEP, VSR o funciones. Sarma rechazaba esas superficies porque sus caras no tienen
  resistencia definida, como manda la spec. La propietaria decidió que el material sin drenaje sí vale en una cara
  (τ = cu a cualquier tensión) y que el resto se salte en la suite solo por ese código
  (`tests/_sarma_registry.py`).
- **Un defecto propio:** las caras verticales de la entrada vertical leían Ru sin el factor de diseño de sus dovelas.
  `test_design_pore_pressure_v1244` lo vio: F se movía un 1,6 % con γG, donde la homogeneidad pide que no se mueva.
  Ahora la cara lee la media de las dos dovelas, como `_face_factor` en una cara vertical.
- **El 4 por la puerta.** Con la bisectriz y 25 cuñas el 4 seco da 1,6017, no el 1,198 publicado. Lo publicado pide el
  ángulo dado en el vértice del quiebro, que llega a la puerta con los datos por vértice (0.1.465). El test de la
  puerta comprueba que es el constructor con los mismos ajustes, al bit.

### Al adaptar la suite (un agente)

Adaptó 24 archivos; dejó tres sin tocar, con su evidencia:
- **`evaluate_surfaces` perdía el rechazo de las cuñas.** Daba `None`, y la nota culpaba a un filtro («no reason was
  recorded; filters active…»). Ahora una superficie cuyas cuñas se rechazan es un resultado sin factor con el código
  del constructor, como un rechazo del solver (`search._wedge_refusal`).
- **`test_moment_axis_v1126`:** Sarma daba 1,4055 sobre la polilínea inscrita frente a 1,3430 sobre el arco.
  - La causa no era el número de cuñas: un contacto corta la superficie a 0,24 m de un vértice, y con la bisectriz
    sus caras se cruzaban.
  - Con caras verticales coinciden: 1,61013 frente a 1,61014. El test corre Sarma con caras verticales y lo dice.
- **Un `.ogr` con `settings.sarma` de otra forma** se abría con un `AttributeError` sin código. La sección entra en
  la tabla del lector (`file_shape.SETTINGS_SECTIONS`), y un nulo vale los valores por defecto.

### La revisión adversaria (un agente)

Comprobó que los nueve métodos dan los mismos bits que HEAD en 3538 evaluaciones (la demo), en tres rejillas de 433
y con Sarma en la corrida, en serie y en paralelo. Comprobó también que el archivo sin Sarma tiene las mismas claves.
Lo que encontró:

- **Alto: dos archivos de tests truncados por mi guion de edición.** `test_anisotropic_surface_v1126` y
  `test_snowden_bedding_v1218` habían perdido todas sus clases después de `_fos` (13 y 7 casos), y el runner los daba
  en verde con cero casos. Se restauraron de HEAD y se volvió a aplicar el cambio. Una comparación del número de tests
  de cada archivo tocado contra HEAD no encuentra más pérdidas.
- **Alto: la regla de las caras verticales encadenaba.** Una cara vertical en un quiebro cóncavo se cruza con la
  normal siguiente, y así una tras otra. En el talud del test, F = 2,5431 con 1 a 20 cuñas, 2,6740 con las 25 por
  defecto (12 caras verticales) y 2,6971 con 100: el número de cuñas movía F donde la ayuda dice que no.
  - **Decisión de la propietaria:** la cara de una división uniforme que cruza (o que no llega al terreno) se quita
    con su frontera, porque F no se mueve por la identidad de los tramos rectos. Solo una cara de vértice, contacto o
    corte del freático por par pasa a vertical, la más inclinada.
  - Ahora F = 2,5430856155 con 1, 6, 14, 25 y 40 cuñas, y es un test.
- **Medios, arreglados:**
  - el contador de superficies sin cuñas no cruzaba el pool de la rejilla en paralelo (`_RUN_COUNTERS`), y la nota
    decía «quedaron fuera» de superficies que se guardan con su código;
  - un valor malo dentro de `settings.sarma` abría el archivo y luego abortaba la corrida entera, Bishop incluido. Ahora
    Sarma salta con una nota que nombra el campo (`sarma_setting_problem`);
  - el barrido de desembalse daba a Sarma tres fallos sin motivo. Ahora lo salta con la nota del desembalse.
- **Bajos, arreglados:**
  - el informe de factores listaba «Sarma» en una corrida sin Sarma;
  - la puerta de una superficie no decía las caras verticales ni las tracciones;
  - la nota de ajustes propios salía junto a «no calculado»;
  - un resultado volcado a disco perdía `faces` para el dibujo;
  - tres comentarios falsos, un docstring del ayudante de la suite que prometía tests que no existen, dos aserciones
    débiles y tres archivos en CRLF.
- **Declarado, sin arreglar:**
  - Optimize con desembalse o B-bar no tiene salto propio: le llega la red, superficie a superficie;
  - un resultado de Sarma volcado guarda en memoria sus `wedge_fields` (las dovelas verticales y las caras, 12 kB
    frente a 5 kB del registro en disco).

## 1. El cambio

- **`ogr_slip2d/methods/sarma.py`** (nuevo): `SarmaNonVertical`.
  - Atributos: `NON_VERTICAL` y `ACCEPTS_SUPPORTS = False`; `SATISFIES_FORCE` sí y `SATISFIES_MOMENT` no.
  - Dos entradas de `compute_fos`:
    - unas `Wedges`, el método completo;
    - unas `Slices` verticales, con caras verticales y su resistencia y agua (`wedges.vertical_faces`).
  - Rechaza con código: los soportes (`lem.sarma_supports`) y lo que rechacen las cuñas o el solver.
  - `details`: `kh`, `kv`, `slide_sign`, `solved_base_normal`, `sarma_kc`, `sarma_min_q`, `sarma_max_force_ratio`,
    `sarma_verticalized` y las fuerzas de cara.
- **Las cuñas** (`wedges.py`):
  - las caras de política que se cruzan o no llegan al terreno: la división uniforme se quita y la de un vértice, un
    contacto o un corte pasa a vertical, una por par (`VERTICALIZED`, `Wedges.verticalized`);
  - una cara por un material sin drenaje lleva c = cu;
  - `vertical_faces` da las caras de unas dovelas verticales;
  - `wedge_fields` es lo que `SliceStore` guarda de unas `Wedges`.
- **El motor:**
  - `build_method` le pasa `settings.sarma`;
  - `search._wedge_trial` construye las cuñas;
  - el reparto de la rejilla cuenta solo los métodos verticales y no se da a la búsqueda de Sarma;
  - `non_vertical_skip`: con desembalse o B-bar, Sarma no se calcula y lo dice una nota, en `run_analysis` y en
    `evaluate_surfaces`;
  - `NonVerticalDrawdownRefusal` es la red de `wrap_for_drawdown`;
  - `checks.OWN_DENOMINATOR` es el cuarto cubo de m-alpha;
  - `sarma_notes` añade cinco notas de corrida, y `settings_warnings` una sexta;
  - `compute_interslice_state` no marcha sobre Sarma;
  - `SliceStore` devuelve unas `Wedges`;
  - el HDF5 lleva las caras y `sarma_kc`;
  - `prepare_analysis_project` factoriza la c/φ de cara dada.
- **Los ajustes:** `SarmaSettings` y `LEMMethod.SARMA`. La sección se escribe solo si se usa, y `from_dict` tira las
  claves desconocidas.
- **API:**
  - el esquema, con elecciones y cotas;
  - `lem_summary`, con `sarma_kc`, `sarma_min_q`, `sarma_max_force_ratio`, `sarma_verticalized` y las caras.
- **CLI:** el alias `sarma` y `--sarma-slices`.
- **La ventana:**
  - la casilla, el nombre y el grupo «Sarma» en Métodos, en gris cuando no aplica;
  - una frase en las ayudas de iteraciones y Steffensen;
  - las caras inclinadas en el PNG y en Interpretar, y el polígono de la cuña seleccionada;
  - el diagrama de cuerpo libre lo dice en la barra de estado y no dibuja nada, hasta 0.1.466;
  - el área del informe, por los polígonos.
- **Mensajes:** `lem.sarma_supports` y `lem.sarma_drawdown`, seis notas de método y `REASON_SARMA_REFUSED`, cada uno
  con su español y su muestra.
- **Documentación:** AGENTS.md, la guía MCP y los README dicen 10 métodos.

## 2. El test

`tests/test_sarma_method_v1464.py`, 24 casos. Contra:
- **las puertas:** el constructor de 0.1.463 al bit, que reproduce los publicados del 4 y el 5 con la cara dada;
- **Janbu simplificado** (Janbu 1954, 1973) con caras verticales sin resistencia, por la puerta y con dovelas dadas,
  a 10⁻¹⁰;
- **los coeficientes parciales sobre la c/φ de cara dada** (Frank et al. 2004), F/(γ·γR;e) a 5·10⁻⁹;
- **Ky** (Sarma 1973): max(0, sup Kc(F≥1)) por un barrido fino, y 0 en el 4 saturado;
- **la regla 7:** cada ajuste mueve el número, y el número de cuñas da la identidad en una polilínea Mohr–Coulomb hasta
  40;
- **lo que hace la corrida:**
  - los verticales al bit, con el reparto vaciado;
  - B-bar con una nota, el desembalse por la red, los soportes y un ajuste inválido rechazados;
  - las caras que se cruzan;
  - la nota de m-alpha;
- **el archivo, la CLI y el volcado.**

Mutantes: `_auditoria/P9_D357/mutants_v1464.py` del banco, con su log. Mueren 21 de 22. Vive uno, declarado
equivalente: dar el reparto también a la búsqueda de Sarma libera antes los registros, y Janbu vuelve a rebanar con
el mismo resultado.

## 3. La suite

- **Los 14 `assert len(...) == 9`** pasan a 10, cada uno con su comentario.
- **`tests/_sarma_registry.py`:** salta a Sarma solo cuando rechaza por un código de su spec (caras de materiales no
  Mohr–Coulomb ni sin drenaje, B-bar, soportes). Lo usan unos 20 archivos que recorren el registro.
- **Soportes:** los tests leen `ACCEPTS_SUPPORTS` y no una lista a mano.
- **Particiones:** `OWN_DENOMINATOR` en m-alpha, y un grupo de iteraciones propias.
- **Otros:** `test_moment_axis_v1126` corre Sarma con caras verticales, y `test_ogr_open_refusals_v1438` gana la
  sección «sarma».

## 4. Verificación

- **La suite entera, `--jobs 4`, una vez tras la revisión:** 7909 casos; pasan 7908 y uno queda saltado, sin fugas ni
  tramos muertos.
  - Después cambiaron dos textos que describían la regla vieja de las caras: la ayuda del ángulo, con su español, y el
    docstring de `SarmaSettings`.
  - Con ese cambio se pasaron i18n, el diálogo, las etiquetas y la versión: 116 de 116.
- **El test nuevo**, 24 casos, y los de Sarma juntos (v1461, v1463 y v1464): 94 de 94.
- **Mutantes:** 22; vive uno, equivalente.
- **Los README:** 7883 → 7908 tests.
- **Pruebas a mano para la propietaria:**
  - la casilla y el grupo de Sarma en Métodos, con Aplicar;
  - un cálculo con Bishop y Sarma;
  - las caras en el lienzo y en Interpretar, y el mensaje del diagrama de cuerpo libre.

## 5. Lo que queda

- Los ángulos y la c/φ por vértice hasta la puerta: 0.1.465.
- Interpretar con cuñas (fuerzas de cara y cuerpo libre): 0.1.466.
- Sin test, y se declara: el dibujo de las caras en el PNG, el área del informe y la tabla de caras del HDF5.
- La estadística y los barridos no tienen salto propio con desembalse: les llega la red, superficie a superficie.
