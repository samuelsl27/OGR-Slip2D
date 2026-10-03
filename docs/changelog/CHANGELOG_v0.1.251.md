# OGR Slip2D v0.1.251

**D85: una superficie crítica que corre por una capa débil tiene
estadística, y cada muestra contesta por la capa débil de su propio
proyecto.** Hasta 0.1.250 un cálculo estadístico (Global Minimum y
sensibilidad) rechazaba por nombre un determinista de tipo `weak_layer`
(0.1.154): un modelo cuya crítica va por una junta, una geomembrana o un
plano de estratificación no tenía probabilidad de rotura. Ahora la superficie
se siembra desde su BASE, y cada muestra la recorta otra vez contra las
capas débiles de su proyecto, igual que una compuesta se recorta otra vez
contra el suelo desde su círculo.

Segunda versión de la tanda Help + D85, D251/D252, D253, D97, D128 y D131.

## 0. Lo que se encontró

### La premisa, y una forma cerrada que la mide

Con 0.1.250 el talud plano de `test_weak_layer_v1121` se rechazaba entero:
«The deterministic critical surface is of type 'weak_layer', which a
statistical run cannot re-evaluate». Sobre ese talud el método ordinario es
exacto:

    F = (c L + W cos α tan φ) / (W sin α)

con W = γ · 80 por el área integrada a mano en v1121. Muestreando la c y la φ
de la junta, cada muestra es un número de forma cerrada, y la probabilidad
de rotura el recuento cerrado.

La siembra se midió primero en memoria, parcheando las dos funciones. Cada
una de las 40 muestras volvió de capa débil y coincidió con la forma cerrada
a 7,7e-16; la PF salió 0,025, igual al recuento cerrado, y el punto medio de
la sensibilidad reproducía el determinista exacto.

### Dos huecos que la siembra abría, medidos y cerrados aquí

La propietaria pidió cerrarlos dentro de D85 (2026-10-03).

- **(a) La sonda de D88 no veía el caso de capa débil.** Compara tipo y
  extremos, y una superficie de capa débil conserva los extremos de la masa
  de la que se recortó.
  - Con las dos juntas de la regla 7 de v1121 (una fuerte arriba y una débil
    debajo), el determinista calculado con «highest» (F 5,957) publicaba unas
    muestras calculadas con «auto_cases» de media 1,855, sin nota.
  - A este hueco solo llega una llamada directa (un script, `python_exec`): la
    puerta de la interfaz recalcula el determinista con los mismos ajustes.
- **(b) Un cambio de caso no se decía.** Con «auto_cases», una masa se
  convierte en una superficie por cada subconjunto de capas, la masa desnuda
  incluida, y gana la de menor factor, lo que es correcto. Con la φ de la
  junta débil muestreada ancha, 1 de 40 muestras contestó por la masa
  desnuda y nada lo dijo. Es el argumento de D89 para las masas, palabra por
  palabra.

### El 109 no era el caso de la ficha

La ficha decía que el 109 daba 6,58, 6,73 y 6,09 con tres métodos. Desde
0.1.233 da 4,69 con cuatro, y su archivo guarda la crítica como `polyline`,
sin decir si es de capa débil. Se midió:
- las críticas (Bishop 4,692466, Spencer 4,768045) y las 242 superficies
  válidas de Bishop son `SlipSurface`: ningún caso recortado sobrevive;
- la crítica corta las juntas en vez de seguirlas.

Así que la prueba del paso 4 es un A/B sin cambio, y lo demás es evidencia
para D243 (ver §4).

### El riesgo de la semilla compartida, medido: inocente, y lo que destapó

La revisión de diseño avisó de que la semilla poligonal es un solo objeto
compartido y de que el rebanador la trunca en su sitio con una grieta de
tracción. Medido con la poligonal, una grieta en y = 8,5 (llena y seca) y
los dos manejos: la semilla compartida, una fresca y el determinista dan el
mismo factor bit a bit en los seis casos. No hace falta copiarla por muestra.

Pero salió otra cosa, que es **D253**. Con «auto_cases», el caso 0 (la masa
sin junta) se rebana primero y escribe su pared de grieta en la base
compartida (x = 27,67). Los casos con junta la heredan en lugar de la suya
(x = 24,75, donde la junta corta la línea de grieta). El mismo mecanismo da
1,5401 con «auto_cases» y 1,5166 con «highest». Se abre la ficha y se
corrige en 0.1.253, después de investigar qué regla es la correcta, como
pidió la propietaria.

## 1. El motor

`ogr_core/statistics/probabilistic.py`; la sensibilidad usa los mismos
ayudantes.

- **`_seed_source`** es el único sitio que decide qué se puede sembrar.
  - El círculo, la compuesta y la poligonal se siembran a sí mismos.
  - La capa débil siembra su base, a un nivel de profundidad.
  - `_rebuild_surface` construye desde él y `_cannot_reevaluate` rechaza por
    él. Hasta ahora cada uno tenía su lista, y un tipo que una aceptara y la
    otra no habría acabado en el `continue` mudo de los dos bucles.
- **`_cannot_reevaluate`** juzga la capa débil por su base.
  - La rechaza solo si falta la base o no se puede sembrar, y la frase
    (`_type_refusal`) nombra los dos tipos.
  - Una base compuesta con Composite Surfaces apagada recibe su propia
    variante de la frase de la compuesta.
- **El `continue` mudo** que seguía a `_rebuild_surface` en los dos bucles
  pasa a nota más método perdido, con la frase de tipo. Solo se llega a él
  si alguien sustituye una de las dos funciones; hasta ahora el método
  desaparecía sin una palabra, la tercera vía de D129.
- **La sonda de D88 compara también las capas activas**
  (`_active_layers`: `(boundary_id, x0, x1)` de cada tramo que gana una capa,
  sin tolerancia, porque la misma aritmética da los mismos dígitos, D87).
  - Cuando vuelve la masa y no el caso, la frase es `_NOT_ITSELF_CASE`. Lleva
    la misma cabeza que `_NOT_ITSELF`, que es por la que la reconocen el
    cierre de D88 y v1239, y un final que nombra lo que decide un caso (el
    manejo de las capas débiles, una capa suprimida).
  - Nombra los casos por tramos de x, no por uuid.
  - `_NOT_ITSELF` no cambia.
- **`_CaseSwitches`, hermana de `_MassSwitches`:** cuenta la muestra que
  vuelve con los extremos de casa y otras capas activas.
  - Es disjunta del cambio de masa por construcción.
  - Vigila también una base poligonal, donde `_MassSwitches` no tiene masa
    que vigilar, y lee el objeto sin `to_dict()` por muestra.
  - Su recuento es `MethodProbabilisticResult.case_switches` (también en
    `summary()`, así que la API y el MCP lo ven) y su frase
    `notes["case_switch"]`, que llega al panel por
    `_publish_method_warnings`.
  - En la sensibilidad, `VariableSensitivity.case_switch_values` y su línea.
  - No se mueve ningún número.
- **Overall Slope queda fuera, a propósito y por escrito.** No vuelve a
  sembrar el determinista: cada muestra busca de nuevo, y en una búsqueda no
  circular dos poligonales pueden compartir extremos. Allí otro caso es otra
  superficie, y `distinct_minima` la cuenta.

## 2. La interfaz

Nada nuevo. La frase de cambio de caso llega al panel de notas por el mismo
canal que la de masa (D89, D129).

Lo que sí se vio: la ventana de estadísticas pone estas frases bajo «Lo que
esta corrida no pudo hacer:», y no son fallos. Se corrige en 0.1.255, con
D128, que toca esa ventana.

## 3. Tests

**`tests/test_weak_layer_statistics_v1251.py`**, 18 casos. El sufijo es el
de la versión en la que aterriza, no el v1160 del prompt.
- **La premisa:** la crítica del talud plano es de capa débil, igual a la
  forma cerrada, y se siembra desde su base poligonal.
- **La forma cerrada muestra a muestra:** cada uno de los 40 factores es la
  forma cerrada de su propia junta a 1e-12, y la PF es el recuento cerrado.
  Cada muestra corre por las mismas capas del determinista, sin cambios de
  masa ni de caso. La sensibilidad da el determinista en el punto medio y la
  forma cerrada en los extremos.
- **La base circular** (el talud de `TestRuleSeven`): cada muestra es, bit a
  bit, el círculo base evaluado directamente sobre el proyecto de esa
  muestra, y conserva su masa.
- **La sonda:**
  - «highest» frente a «auto_cases», en los dos sentidos, y la capa suprimida
    solo en las muestras se rechazan con la frase del caso;
  - el mismo proyecto no se rechaza;
  - la frase nueva conserva la cabeza y no lleva «: ».
- **El cambio de caso:**
  - el recuento es el de una reproducción independiente, y la frase llega al
    panel;
  - contar no mueve ningún número (los valores son los de las muestras
    registradas);
  - una distribución estrecha no dice nada;
  - la sensibilidad también lo dice.
- **Lo que sigue rechazado dice por qué:** la capa débil sin base, la base
  compuesta sin Composite Surfaces y una semilla que no se puede construir,
  nombrada en vez de soltada.

**Cambian a propósito dos tests de `test_statistical_rebuild_v1154.py`:**
- `test_each_one_either_seeds_or_is_refused_by_name`: la capa débil pasa de
  rechazada a SEMBRADA, un círculo sin extremos. La rama de rechazo sigue
  viva con una capa débil sin base, que se rechaza con su nombre.
- `test_a_weak_layer_critical_no_longer_takes_the_run_down` sigue pasando,
  pero por otra razón. El sustituto es una capa débil sobre un modelo SIN
  capas débiles (la capa débil del problema 22 es una franja de material),
  así que su círculo base vuelve como compuesta, con otros extremos, y lo
  rechaza la sonda. Se afirma la cabeza de la sonda.

**Discriminación** contra una copia del árbol de 0.1.250 (fc17885), con su
runner y sin el buscador editable: **17 de 18 fallan**. Quince fallan por
comportamiento:
- el rechazo por nombre;
- la frase de la base;
- el `continue` mudo.

Dos fallan por símbolo. Pasa, a propósito, la premisa: el motor que rebana
la junta no cambia.

## 4. El banco

- **Base comprobada antes de correr:** los once
  `resultados_probabilistico*.json` vivos eran, byte a byte, los de
  `Evaluaciones/0.1.249` (todos de 0.1.239).
- **Re-corrida del lote** con `correr_probabilistico.py`: 11 de 11 en 3452 s,
  en paralelo con la suite. **198 números iguales a los de 0.1.249**, 0 sin
  pareja una vez fuera `case_switches`, que vale 0 en las once, y ningún
  método rechazado. Ningún modelo del banco tiene una crítica de capa débil:
  es el A/B de «sembrar la capa débil no toca nada más».
- **El 109**, sin escribir en el banco (`_auditoria/P5_0251/estadistica_109.py`,
  con 0.1.250 y con 0.1.251): las críticas son `SlipSurface`, se publican las
  dos y hay **0 diferencias**.
- **Trampa evitada en los cierres.** `d88()` y `d89()` comparan esas corridas
  por el conjunto de rutas numéricas, y solo excluían `version_ogr`,
  `segundos` y `mass_switches` (`_FUERA_D89`). El `case_switches` nuevo los
  habría bajado como una «ruta sin pareja». Se añade a la exclusión con la
  razón escrita, como hizo D89 con `mass_switches`, y `d85()` comprueba
  aparte que vale 0 en las once.
- **Cierre: `d85()`, CUBIERTO POR TEST.** Comprueba:
  - en vivo: el talud plano con la forma cerrada, la semilla de la base y la
    sonda ante el cambio de manejo;
  - las once corridas;
  - el 109;
  - la discriminación.
- **Fichas nuevas:**
  - **D251:** los consumidores que despachan una superficie por su tipo
    pierden la capa débil (lienzo, DXF, interpretación, API, optimización).
    P1; se corrige en 0.1.252.
  - **D252:** «Add Query» revienta lejos de la rejilla desde 0.1.201. P1, con
    D251.
  - **D253:** la grieta y la capa débil. P5; se corrige en 0.1.253.
- **Añadidos** a D97 (el pilote Ito-Matsui al revés, sumado por decisión de
  la propietaria) y a D243 (la evidencia del 109).
- **Ciclo de cierre:**
  - `verificar_cierres.py` entero: 220 cierres y 0 bajadas; comparado clave
    a clave con la copia previa, el único cambio es D85 nuevo;
  - `d85()` da NO SE SOSTIENE con el motor de 0.1.250 por delante en
    `PYTHONPATH` (la semilla `None` y el rechazo por nombre);
  - instantánea `Evaluaciones/0.1.251` (3082 archivos, comprobados byte a
    byte);
  - D85 retirada al índice, podada de `PAQUETES` y tachada en la cadena P5;
  - prompts regenerados (44; D251, D252 y D253 salen como FALTA, sin prompt
    largo, porque se corrigen en esta tanda);
  - auditorías de invariantes con 0 ERROR en el 02 y en la raíz;
  - instantánea rehecha con `--forzar`;
  - `--seco` completo después de retirar.

## 5. Lo que se reporta y NO se corrige aquí

- **D253** (arriba): abierta, con su medida, y se corrige en 0.1.253.
- **D248** sigue abierta: la llamada directa evalúa con 25 dovelas por
  defecto. El talud plano no se puede rebanar con 25, así que el test pasa
  40 explícitamente.

## 6. Verificación

- **Suite entera:** 5542 de 5542 (las 5524 de 0.1.250 más los 18 casos
  nuevos), en paralelo con el lote del banco.
- **Selección** de estadística, sensibilidad, cambios de masa, sonda,
  pérdidas, claves, grieta, Overall Slope, la puerta y capas débiles: 475 de
  475 en 25 archivos.
- **Discriminación:** 17 de 18 contra 0.1.250.

**Qué falta por probar:**
- **La estadística de un modelo con capa débil desde el menú**, y la frase
  de cambio de caso en pantalla.
