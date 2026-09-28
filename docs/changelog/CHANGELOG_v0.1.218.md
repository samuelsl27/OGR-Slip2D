# OGR Slip2D v0.1.218

Primera de las cuatro versiones que cierran lo que queda del paquete P4 del
banco de verificación (reparto de la propietaria, 2026-09-28: 0.1.218 los
modelos de resistencia; 0.1.219 D206; 0.1.220 D211 y D210, con parada tras
medir; 0.1.221 D212). Tres modelos de resistencia pasan a ser los que
documenta la referencia:

- **D208 — Snowden lee el buzamiento local.** Una superficie anisótropa
  enlazada a un material Snowden no hacía nada: el diálogo la ofrecía y el
  cálculo usaba siempre el ángulo global.
- **D209 — la función anisótropa es una tabla de TRAMOS «ángulo hasta, c,
  φ»**, con c y φ constantes en cada tramo, como la documenta la referencia.
  OGR interpolaba entre puntos, así que la misma tabla eran dos materiales
  distintos en los dos programas. Las filas van en una clave nueva, `rows`;
  un `.ogr` que aún guarda `points` se abre pero no se calcula.
- **D207 — SHANSEP suma A y Vertical Stress Ratio lee σ′v.** SHANSEP pasa a
  `τ = max(A + σ′v·S·OCR^m, su_min)`, y con σ′v ≤ 0 evalúa la fórmula en cero
  en vez de pasarse en silencio a una resistencia friccional. Vertical Stress
  Ratio lee la tensión vertical de la dovela y no σ′ₙ, y Janbu lo trata como
  «sólo c».

Y en el banco, **D214**, abierta y cerrada en esta versión:
- el cierre de D197 leía el banco vivo, que 0.1.217 movió a propósito;
- el recorrido en seco de todos los cierres encontró otro de la misma clase,
  el de D66, cuyo 050 movió 0.1.214 (D80).

Se abren cinco fichas que no se corrigen (sección 3).

Cero filas del banco: ningún `.ogr` de los 7995 del árbol RS2 usa SHANSEP,
Vertical Stress Ratio, Snowden ni la función anisótropa.

Lo que cambia en el banco de verificación (`_tools/`, `_auditoria/`, fichas)
está fuera de git.

---

## 0. Las fuentes, y lo que decían los encargos

### D207: la documentación de la referencia, leída

- **SHANSEP** (página del modelo, fórmula en imagen):
  `τ = A + σ′v·S·(OCR)^m`, con A «minimum undrained shear strength» SUMADA y
  σ′v «in situ effective vertical stress» (Ladd & Foott 1974). OGR tomaba
  `max(σ′v·S·OCR^m, su_min)`. No dice qué pasa con σ′v ≤ 0.
- **Vertical Stress Ratio**: `τ = K·σ′v`, con σ′v «computed from the total
  weight of each slice, and the pore pressure acting at the center of the
  base of each slice». No tiene resistencia mínima.

Decisiones:

- **A es un parámetro nuevo, sumado, y `su_min` se queda como el suelo que
  era** (propietaria). Renombrar `su_min` rompía la carga de cualquier `.ogr`
  viejo (el constructor rechaza parámetros desconocidos) y dejaba sin efecto,
  en silencio, una variable aleatoria sobre «su_min». Con A = 0, bit a bit lo
  de antes: el producto se forma igual y A se suma delante.
- **σ′v ≤ 0 (una columna artesiana)**: la fórmula en cero, τ = max(A, su_min).
  Hasta aquí SHANSEP pasaba a `su(σ′ₙ)`, un suelo friccional con
  tan φ = S·OCR^m que no es el modelo publicado en ninguna tensión.
- **El exceso B̄ se queda en la u de σ′v, a propósito.** SHANSEP lee la tensión
  de consolidación, y una carga no drenada no consolida: con B̄ = 1 sube σv y
  u por igual y deja σ′v donde estaba. El ejemplo trabajado de la referencia
  da 1872 lb/ft² antes y después del desembalse por la misma razón. El test lo
  fija como identidad, exacta porque `load_delta_sigma_v` es unidimensional.
- **Vertical Stress Ratio declara contexto** y lee `ctx.sigma_v_eff`, la misma
  σ′v que SHANSEP (con el agua embalsada de D166 y sin kv). `min_strength` se
  conserva como extensión de OGR. `janbu.base_soil_type` lo nombra con
  SHANSEP: sobre una dovela su resistencia es una constante.

### D209: tramos, y por qué una clave nueva

La documentación: «discrete angular ranges of slice base inclination, each with
its own cohesion and friction angle»; filas «Angle To, c and phi»; el primer
tramo empieza en −90 y el último tiene que terminar en +90. No dice a qué tramo
pertenece un ángulo justo en un límite: aquí, al inferior, el convenio de
`GeneralizedAnisotropic._model_for_angle`, escrito como decisión.

**El encargo decía «sin migración» y la premisa era incompleta.** La propietaria
eligió los tramos con el argumento de que el modelo reventaba de 0.1.126 a
0.1.214, así que ningún `.ogr` de esas versiones pudo analizarse con él. La
revisión del diseño encontró que interpolaba bien de 0.1.15 a 0.1.125 y de
0.1.215 a 0.1.217, y que un `.ogr` no guarda la versión que lo escribió. Se
preguntó otra vez. La decisión:

- las filas van en una clave NUEVA, `rows`;
- un `.ogr` con la vieja, `points`, se abre y las conserva al guardar, pero
  no se calcula con ellas;
- el diálogo las precarga para revisarlas como tramos, con un aviso.

Leerlas como tramos habría cambiado el número en silencio.

**Del mismo tipo, y dentro de la ficha (propietaria):** un soporte lee la función
en el ángulo de su eje, un `atan2` de cabeza a cola en (−180°, 180°]. La función
no lo plegaba, y un soporte que apunta hacia −x leía siempre la última fila.
Ahora se pliega a (−90°, 90°]: un plano a 165° es el de −15°.

### D208: la causa es la de D195

El commit d4cdcd5 (v0.1.126) cambió la firma de `_c_phi` de Snowden para que
admitiera el buzamiento local y no cambió su llamada, y puso el argumento en la
de la función anisótropa, que no lo admitía (D195, cerrada en 0.1.215).

## 1. Los arreglos (motor)

- **Snowden** (`builtin_models.py`): `shear_strength_ctx` pasa
  `_local_bedding_deg(self, ctx)` a `_c_phi`. Sin superficie el contexto lleva
  None y el respaldo es el ángulo global: bit a bit lo de antes.
- **Función anisótropa**:
  - `rows` con `DEFAULT_ROWS` = el ejemplo de la documentación, (−30, 10, 35),
    (0, 1, 20), (90, 5, 10);
  - no se ordenan: una tabla desordenada se rechaza, no se reordena;
  - `legacy_points` y `LegacyAnisotropicTable` para las tablas de puntos;
  - `fold_plane_angle_deg`.
  - El límite pertenece al tramo inferior con un margen de 1e-9°, porque el
    ángulo llega en radianes: `degrees(radians(−30))` es −29,999999999999996, y
    sin margen el límite documentado cambiaba de tramo en el viaje de ida y
    vuelta. Salió en el primer test.
- **Regla compartida** (`ogr_core/project/rules.py`):
  - `anisotropic_function_rows_refusal`: filas estrictamente crecientes, la
    primera por encima de −90, la última en +90, c ≥ 0 y 0 ≤ φ < 90;
  - `strength_model_refusal`, que también mira dentro de las reglas de un
    Generalized Anisotropic.
  - La preguntan `check_analysis_settings` (todos los caminos de cálculo:
    interfaz, API, CLI y `python_exec`), `ogr_api.catalog.strength_from_spec` y
    el diálogo.
- **SHANSEP** y **Vertical Stress Ratio**: arriba. `SliceContext` documenta
  quién lee `sigma_v_eff`.
- **La nota de resistencia nula** (`BishopSimplified._zero_strength`) sondea
  también la σ′v. Con A = su_min = 0, una dovela SHANSEP artesiana queda sin
  resistencia; sondeando sólo σ′ₙ el modelo parecía «sin resistencia por
  definición» y la nota callaba. `_local_c_phi` admite `sigma_v_probe`, que
  sólo usa esa sonda. Lo vio la revisión del diseño.
- **Diálogo de materiales**:
  - la tabla edita `rows`, con columnas `tr("Angle to (°)")`, c y φ;
  - precarga una tabla de puntos con aviso;
  - al aceptar rechaza una tabla que no es de tramos, con la razón en una
    etiqueta y no en un modal, y también una fila que no son tres números
    (antes se descartaba en silencio y dos tramos se fundían en uno);
  - las fórmulas mostradas de SHANSEP y de la función anisótropa, al día.

## 2. Tests

- `test_snowden_bedding_v1218.py`, 7 casos:
  - la identidad «superficie recta a α = buzamiento global α» (a 1e-12 con
    Bishop y a 1e-9 en los nueve métodos), la de `test_anisotropic_surface_v1126`;
  - la regla 7;
  - el id colgante;
  - Snowden anidado en un Generalized Anisotropic.
- `test_shansep_vsr_v1218.py`, 21 casos:
  - la fórmula publicada;
  - la regla 7 de A y de su_min;
  - la columna artesiana, que es el suelo no drenado de cu = A en los nueve
    métodos a 1e-12;
  - la nota de resistencia nula;
  - la identidad B̄ = 1;
  - Vertical Stress Ratio bajo lámina (γ′·h, como D166) y como cohesión K·σ′v;
  - su tipo de Janbu (F_corr = f0(0,69)·F_simp a 1e-12);
  - su lectura en los soportes.
- `test_anisotropic_function_ranges_v1218.py`, 26 casos:
  - el ejemplo documentado escrito a mano;
  - el convenio del límite;
  - el plegado, también desde un soporte;
  - la identidad que separa tramos de interpolación: un tramo que no toca
    ninguna base NO mueve el factor en los nueve métodos, y el que sí toca, sí;
  - la regla;
  - la tabla de puntos, que se conserva y no se calcula;
  - la API;
  - el diálogo.
- **Cambiado a propósito**: `test_anisotropic_function_v1215.py`, cuyas anclas
  eran la interpolación de la tabla vieja (la razón, en su cabecera), y la lista
  de identidades permitidas de `test_i18n_coverage_v141.py` («c (kPa)», «φ (°)»,
  notación como «A (kPa):»).

**Contra 0.1.217 fallan 41 de los 54 casos nuevos** (git archive de b6800a6):

| | casos | por comportamiento | por símbolo | pasan |
|---|---|---|---|---|
| D208 | 7 | 4 | 0 | 3 controles |
| D207 | 21 | 9 | 7 (el parámetro `A`) | 5 |
| D209 | 26 | 10 | 11 | 5 |

- **Los de tramos prueban los números con la lectura vieja** (`points=`) cuando
  el árbol no conoce `rows`, así que caen por la INTERPOLACIÓN y no por la
  palabra: en 0.1.217, cambiar el primer tramo mueve el factor de Bishop de
  1,0622 a 1,1146.
- Pasan allí la identidad B̄ (lo que se decidió conservar) y los controles.

## 3. Lo que se reporta y NO se corrige (regla 6)

- **D215 — Snowden no es la formulación de la referencia.** La referencia tiene
  cuatro parámetros asimétricos (A1, A2, B1, B2), una transición LINEAL y
  funciones de resistencia (corte-normal o cohesión-fricción) para la
  estratificación y el macizo. OGR usa un coseno simétrico con un solo B y c, φ
  constantes. D208 corrige qué buzamiento lee, no qué modelo es.
- **D216 — Anisotropic Linear interpola φ donde la referencia interpola tan φ.**
  Comprobado en la imagen de la ecuación de la documentación:
  `tan φ = tan φ1·(1 − t) + tan φ2·t`.
- **D217 — las tablas de puntos del diálogo de materiales** (función corte-normal
  y discreta) no convierten unidades, con «kPa» fijo en la cabecera aunque el
  proyecto esté en unidades imperiales. Sus cabeceras no pasan por `tr()`, y una
  fila que no son números se descarta en silencio al guardar. La de la función
  anisótropa ya no tiene los dos últimos.
- **D218 — Generalized Anisotropic se traga la excepción** al construir el modelo
  de una regla y devuelve τ = 0, y también τ = 0 cuando ninguna regla cubre el
  ángulo, sin decirlo.
- **D219 — la función anisótropa sin contexto** toma la fila de menor c y no la de
  menor resistencia, y Janbu clasifica su tipo de suelo por material y no por
  base. Una tabla que mezcla un tramo «sólo φ» y otro «sólo c» toma el b1 de uno
  de ellos donde la regla de D80 daría 0,50.
- Observaciones, sin número:
  - SHANSEP no tiene la historia tensional por profundidad o cota ni el
    «Vertical Stress Factor» de la referencia; son funciones que faltan, no
    defectos;
  - los coeficientes parciales no tocan ningún parámetro de SHANSEP (ni S, ni
    su_min, ni A);
  - la σ′v de las leyes de adherencia de los soportes no lleva el exceso B̄: lo
    de «conserva el exceso» es del camino de la dovela.

## 4. Verificación

- Selección dirigida (resistencia, materiales, i18n, Janbu, σ′v, no drenado,
  anclajes, anisotropía, exceso B̄, resistencia nula, envolvente, catálogo, API,
  propiedades): **639 de 639**.
- Suite entera: **4890 de 4890** (31 min 30 s).
- Banco:
  - `d207()`, `d208()`, `d209()` y `d214()` cierran, y dan NO SE SOSTIENE
    contra 0.1.217;
  - `d195()` se actualizó: sus anclas eran la interpolación, y su afirmación
    sigue en pie;
  - el `d197()` viejo, ejecutado sobre el banco de hoy, ya no se sostenía
    (097: 0,788538 frente a 0,805392), que es D214.
- **Todos los cierres en seco**, comparados clave a clave con el JSON
  archivado, con la regla de `veredictos_cierre.fusionar`. La primera pasada
  dio **dos bajadas**, y ninguna era de esta versión:
  - **D66** leía el `resultados.json` vivo del 050, que 0.1.214 reescribió con
    D80 (el b1 de Janbu corregido por tipo de suelo). La fila `por_0_-5` quedó
    en −3,37 %, fuera del 3 % del cierre. Nadie había vuelto a ejecutar `d66`
    desde entonces, porque el JSON acumula. Es la clase de D214 y entró en
    ella sin número (convención de 0.1.208): `d66` lee
    `Evaluaciones/0.1.160`, que guarda al dígito lo que archivó el cierre.
  - **D186** caía por D66, que es miembro suyo, y por un error de esta tanda:
    `d214()` comparaba contra un conjunto de veredictos escrito a mano, que
    D186 prohíbe por AST. Ahora pregunta a `veredictos_cierre.cierra`.
  - Una trampa ya anotada volvió a pasar: el script propio que importa
    `verificar_cierres` no tenía `if __name__ == "__main__"`, y cada hijo del
    ProcessPool de una búsqueda lo re-ejecutó entero. Se paró y se relanzó.
