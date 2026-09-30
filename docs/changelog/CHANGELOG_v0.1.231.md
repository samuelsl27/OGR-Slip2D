# OGR Slip2D v0.1.231

**La CI roja de 0.1.230, D227 y D228: los soportes declaran el suelo que no
pueden leer y leen el buzamiento local de una superficie anisótropa.**

Es la primera versión de la tanda D226–D232 (plan aprobado el 2026-09-30).
Lo que cambia en el banco de verificación (`_tools/`, `_auditoria/`, fichas)
está fuera de git.

---

## 0. La CI de 0.1.230: un *segfault* determinista en el trabajo de 3.12

**Qué se vio.**

- Python 3.11 y 3.13 pasaron la suite entera; el trabajo de 3.12 murió con
  «Segmentation fault» (código 139).
- Se relanzó y cayó **en el mismo sitio**: tras el test 2311 de 5149, en
  `test_lens_regions_v1197.py`, con un aviso de PySide sobre
  `MainWindow._on_line_load_point_picked` un segundo antes y el fallo once
  segundos después. No es azar: es determinista con ese intérprete.
- No se puede reproducir aquí: en local solo hay 3.14.

**Dónde estaba de verdad.** La salida estándar del runner va a una tubería,
en bloques de 8 KB. El registro de la CI llega hasta el final de un bloque y
lo que siguió se perdió con el proceso, así que «el test 2312» es solo el
último que cupo en el bloque. El aviso sale por la salida de errores, sin
búfer, y es el que fecha lo ocurrido:

- lo emite `test_line_load_boundary_v1199` (fichero 130), que llama al
  método directamente;
- el siguiente fichero es `test_live_bridge_v1203`, el único que ejecuta un
  hilo de Python (el cliente del puente) mientras el hilo de Qt procesa
  eventos.

**El mecanismo.**

- El recolector cíclico de Python corre en el hilo que asigna memoria cuando
  se cruza un umbral, y lo que recoge se destruye en ESE hilo. Qt no admite
  destruir un widget fuera de su hilo.
- Los tests de diálogo de 0.1.218, 0.1.225, 0.1.227, 0.1.228 y 0.1.229
  sustituían `accept` por una lambda que **capturaba el diálogo**. Eso deja
  cada diálogo en un ciclo que sobrevive al test y que destruye quien pase
  el recolector, en cualquier momento posterior y dentro de otro test.
- Cuatro ficheros nuevos de la tanda anterior corren antes del puente (los
  de 0.1.225, 0.1.226, 0.1.228 y 0.1.230), y dos de ellos con ese patrón.
  Cambiaron cuánto se asigna antes del puente y, con ello, en qué hilo cae
  la recolección que se lleva los diálogos. Eso explicaría que falle un solo
  intérprete, de forma determinista, y justo al añadir tests que no tocan el
  puente. El patrón ya estaba en `test_anisotropic_function_ranges_v1218`
  desde 0.1.218, y la CI pasó con él hasta 0.1.224.

**Medido aquí** (un guion de prueba fuera del repositorio, PySide 6.11.1 en
Windows):

| Patrón | Qué pasa |
|---|---|
| La lambda captura el diálogo | Sobrevive al test. `gc.collect()` en el hilo principal lo destruye allí; en un hilo secundario, el envoltorio de Python desaparece y el diálogo no emite nunca `destroyed` |
| La lambda captura la lista | El diálogo muere al salir del test, por recuento de referencias, en el hilo principal |

Una sonda en el recolector (`gc.callbacks` con `DEBUG_COLLECTABLE` solo fuera
del hilo principal) sobre el árbol de 0.1.230, hasta el puente, en 3.14:

- 707 recolecciones fuera del hilo principal;
- todas de objetos del motor (dovelas, estados de rama, sistemas de GLE);
- ninguna de Qt: en este intérprete, la recolección que se lleva los
  diálogos cae en el hilo principal.

El mecanismo queda confirmado, pero el fallo no: en Windows no revienta.
**No está probado que esa sea la causa del fallo de la CI.** La próxima
corrida lo dirá, y si vuelve a caer dirá dónde.

El plan proponía un ayudante común que cerrara y liberara cada diálogo
(`close()`, `deleteLater()`, `processEvents()`). Se hizo otra cosa, más
pequeña: romper el ciclo. El experimento de arriba muestra que así el
diálogo muere al salir del test, en el hilo principal, sin depender de un
bucle de eventos que procese el `deleteLater`.

**Lo que cambia:**

- Los cinco ayudantes `_dialog` capturan la lista y no el diálogo:
  `test_anisotropic_function_ranges_v1218`,
  `test_generalized_anisotropic_honest_v1225`,
  `test_generalized_links_v1228`, `test_material_tables_units_v1227` y
  `test_snowden_reference_v1229`.
- `_drive` (`test_live_bridge_v1203`) hace `gc.collect()` en el hilo de Qt
  antes de arrancar el cliente y apaga el recolector automático mientras el
  hilo vive. Así el puente no depende de la basura que deje ningún test
  anterior.
- `PYTHONFAULTHANDLER=1` en el paso de tests de la CI: un fallo futuro
  imprimirá la pila de Python de cada hilo.

**Hallazgo reportado y NO corregido (regla 6).** La aplicación ejecuta los
análisis en un `QThread` (`_ComputeWorker`), así que el recolector corre
sobre todo en ese hilo. Cualquier objeto Qt que esté en un ciclo en ese
momento se destruiría allí. Es el problema por el que pyqtgraph apaga el
recolector automático y recoge desde un `QTimer` en el hilo de la interfaz
(`pyqtgraph.util.garbage_collector`). No se ha visto fallar en la aplicación.
Abierta como **D234** en el banco, a petición de la propietaria.

## 1. Una fuga de idioma entre tests

Salió al correr una selección de soportes: `test_support_silence_v1155`
fallaba con «no notes» solo si antes corría `test_i18n_coverage_v141`.

- `TestLanguageSwitching` devolvía el inglés en un `teardown_method`, que
  este runner no llama.
- Dos tests de `TestTranslationCompleteness` acababan en español, uno a
  propósito y otro por omisión.
- `test_max_iterations_scope_v1173` dejaba también el español.

En la suite entera no se veía porque, en ese orden, nada de lo que venía
después leía un texto traducido: es la regla 5. En HEAD también fallaba.
Ahora un gestor de contexto `_Language` devuelve el idioma que encontró, y
el test de v1173 usa `try/finally`.

## 2. D227: el suelo que no se puede leer se declara

**El defecto.** `soil_shear_strength_at` y `equivalent_c_phi_at`
(`ogr_core/support/bond.py`) envolvían la lectura del modelo del suelo en
`except Exception: return 0.0`. Un modelo que lanzara dejaba el soporte con
adherencia cero en ese tramo, y con ella la resistencia al arranque, sin
decirlo: la clase de D56 y D94.

**Lo que hace ahora** (la decisión de D184, «rechazar y declarar»):

- la excepción se convierte en `SupportEvaluationError`, con un motivo que
  nombra el material, su modelo, la excepción y el punto;
- ese motivo sigue el canal que abrió D95: el soporte queda fuera como
  `not_priceable` en cada superficie que cruza, con el motivo en
  `details["support_failure"]` y en la nota;
- el tooltip del lienzo y el diagrama de fuerzas lo dicen: «Este soporte no
  se puede calcular (…): el análisis lo deja fuera.». El motivo va escapado
  en el HTML del tooltip.

**Dos silencios de la misma familia**, vistos al preparar el plan:

- **El sentido de rotura** se leía bajo un `except`, y cualquier cosa ilegible
  pasaba a «de derecha a izquierda». Eso invierte el sentido de una fuerza
  tangente, horizontal o perpendicular. Ahora se lee tal cual: el enum no
  tiene tercer valor, así que si no se puede leer, el proyecto está roto y
  lo dice.
- **Las dos comprobaciones de Ito-Matsui** (presión de poro en el fuste,
  presión negativa cerca de la superficie) contestaban False a una
  excepción, y la nota desaparecía. Ahora dicen «It could not be checked …»
  con la excepción.

**El cero por resistencia no finita (hallazgo c).** Es una decisión escrita,
no una excepción tragada: la resistencia infinita es cómo un modelo dibuja
la roca rígida, y un soporte anclado en ella se queda allí con adherencia,
portante de placa o empuje de pilote CERO, no infinitos. El plan pedía
medirla antes de decidir. Censo nuevo, `_tools/censo_infinita_d227.py`,
sobre los `.ogr` vivos de los seis manuales:

| Qué | Cuántos |
|---|---|
| Modelos | 230 |
| Soportes | 294, de los que 245 leen el suelo |
| Soportes que cruzan un material de resistencia infinita | 2 (los dos *soil nails* del 060, que no leen el suelo) |
| De ellos, que leen el suelo | 0 |

Se queda como está, y ahora se declara:

- **Qué tipos leen el suelo.** Cada tipo lo dice con `READS_SOIL_STRENGTH`,
  sin listas de `TYPE_ID`:

  | Tipo | `READS_SOIL_STRENGTH` |
  |---|---|
  | Geosintético | Una propiedad, verdadera solo en modo coeficiente |
  | Anclaje helicoidal | Sí |
  | Pilote | Una propiedad, verdadera solo en Ito-Matsui |
  | Los demás | No |

- **La nota.** `support_notes.infinite_strength_notes`, en
  `settings_warnings`, nombra el soporte, el material y qué parte de su
  longitud (y cuántas placas) cae en él.
- **La lectura que la dispara es la misma que pone el cero.**
  `bond._soil_reading` se separó de `soil_shear_strength_at` sin cambiar
  nada, y `bond.infinite_soil_at` lee con el estado de tensiones y la
  orientación del perfil de adherencia. Si esa lectura falla, la nota salta
  el soporte: ese fallo ya lo declara el análisis por el canal de arriba.

## 3. D228: los soportes leen el buzamiento local

**El defecto.** Desde 0.1.126 el rebanador da a cada base el ángulo de la
superficie anisótropa del material en el punto más próximo, y Anisotropic
Linear y Snowden lo toman antes que su ángulo global. Los dos lectores del
suelo a lo largo de un soporte construían su `SliceContext` sin él. Así, un
geosintético en modo coeficiente, un anclaje helicoidal (fuste y placas) y
un pilote Ito-Matsui leían el ángulo GLOBAL: el mismo material era dos
materiales distintos, uno para las dovelas y otro para los soportes.

**Lo que hace ahora:**

- `ogr_slip2d.slicer._anisotropic_surfaces` pasa bit a bit a
  `ogr_core.geometry.anisotropic_surface.material_surfaces`, y el rebanador
  lo importa de vuelta.
- `bedding_angle_at(project, material, x, y)` da el ángulo con la regla del
  rebanador, o None si no hay enlace o la superficie ya no existe.
- `soil_shear_strength_at` lo pasa a su contexto.
- `_PointAsSlice` lo lleva como ÚLTIMO argumento, con None por defecto,
  porque `test_helical_anchor_v1124` la construye con siete.

**La decisión, escrita.** La regla de la referencia para un geosintético (la
anisotropía se mide contra el eje del soporte) ya se cumplía
(`axis_angle_rad`). Leer el buzamiento local a lo largo del soporte es una
decisión de coherencia con el rebanador.

## 4. Tests

**`tests/test_support_soil_failure_v1231.py`**, 18 casos. Usa el talud de
`test_supports_all_methods_v164` con una lente DETRÁS del círculo cuyo
modelo lanza: la cola del soporte la cruza y ninguna base entra en ella.

- El geosintético en modo coeficiente y el anclaje quedan fuera: el factor
  coincide con el del talud sin soporte (rel 1e-15), con el código
  `not_priceable` y el motivo en `support_failure`. El control: en suelo
  legible el soporte mueve F.
- Los dos lectores lanzan `SupportEvaluationError` con el material, la
  excepción y el punto, y un suelo legible se lee como antes (c + σ tan φ).
- Las subcadenas reservadas del banco no aparecen en ningún texto nuevo.
- Otros silencios:
  - el sentido de rotura no se lee bajo un `except` (la forma del código);
  - la nota de Ito-Matsui «could not be checked».
- **El cero infinito:**
  - la nota da el soporte, el material y «about 28 %», 14 de 50 puntos
    medios; el anclaje cuenta sus placas;
  - la nota llega a `settings_warnings`;
  - no hay nota en suelo finito, con un *soil nail* ni con un geosintético
    con ley propia;
  - `READS_SOIL_STRENGTH` de cada tipo;
  - **la identidad que fija la decisión**: a lo largo de la lámina, la
    resistencia infinita es un suelo de resistencia cero, bit a bit. Se usa
    una lámina en la que gobierna el arranque por detrás; con la de los
    demás tests gobierna la tracción y la lente no mueve nada, y el control
    lo detectó.
- El tooltip, el diagrama y la traducción.

**`tests/test_support_bedding_v1231.py`**, 12 casos:

- una superficie recta a 30° es EXACTAMENTE el material de ángulo global
  igual al que da la superficie, bit a bit:
  - en los dos lectores, con Anisotropic Linear y con Snowden;
  - por el motor, con los tres soportes que leen el suelo;
- enlazada la superficie, el ángulo global no mueve nada;
- enlazarla mueve el número (regla 7). Los parámetros se eligieron para que
  lo mueva también en el eje vertical del pilote: con B = 40, 60° y 90° de la
  estratificación darían los dos la resistencia del macizo;
- Anisotropic Linear, a mano (la transición de Mercer);
- sin enlace o con la superficie borrada, el ángulo global;
- el eje no tiene sentido: 165° lee lo mismo que −15°. El par linealizado se
  compara a 1e-9, porque sale de una pendiente numérica que convierte el
  último bit del ángulo plegado en ~10⁻¹¹ de c.

**Contra 0.1.230 fallan 24 de 30:**

| Por qué | Cuántos |
|---|---|
| Comportamiento | 15 |
| Forma del código | 1 |
| Símbolo | 8 |

Pasan los 6 controles.

**Tests que cambian a propósito:**

- los cinco ayudantes de diálogo (§0);
- `_drive` del puente (§0);
- `test_i18n_coverage_v141` y `test_max_iterations_scope_v1173` (§1).

## 5. Otro hallazgo reportado y NO corregido

`BishopSimplified._local_c_phi` convierte en «resistencia infinita»
(c = 10¹², tan φ = 0) CUALQUIER τ no finito, también un NaN. Medido aquí con
una lente cuyo modelo devuelve NaN, cruzada por el círculo del talud de
soportes:

| Lente | Bishop | Spencer |
|---|---|---|
| Modelo que devuelve NaN | 2,787·10¹⁰, superficie válida | Inválida |
| Resistencia infinita | 2,787·10¹⁰, superficie válida | Inválida |

Un modelo con un defecto se lee como roca sin decirlo, y la superficie
desaparece del mínimo: la clase de D56. Abierta como **D235** en el banco,
a petición de la propietaria.

## 6. El banco

- **D227 y D228 cerradas** con `d227()` y `d228()`, las dos CUBIERTO POR
  TEST.
  - `d227()` comprueba en vivo:
    - que el soporte con suelo ilegible queda fuera, con F la del talud sin
      soporte y el motivo en `support_failure`;
    - que los dos lectores lanzan el error tipado;
    - que la resistencia infinita, a lo largo de la lámina, es un suelo
      nulo bit a bit, y que la nota lo dice.

    Revisa además el código del sentido de rotura, el censo y la
    discriminación.
  - `d228()` comprueba en vivo la superficie a 30° en los dos lectores y
    por el motor, el censo de D219 (ningún material anisótropo en el banco)
    y la discriminación.
- **Contra 0.1.230** (`PYTHONPATH` al árbol archivado), **las dos NO SE
  SOSTIENEN, todo por comportamiento** (D227 además por el símbolo de la
  nota).
- **Censo nuevo, `_tools/censo_infinita_d227.py`**, la tabla del §2:
  - 245 soportes leen el suelo según la regla del censo, y los mismos 245
    según `READS_SOIL_STRENGTH`, sin ninguna discrepancia;
  - no hubo errores de carga.
- Sin interruptores nuevos: `INTERRUPTORES` sigue en 31. Las dos fichas no
  mueven ninguna fila del banco.
- PAQUETES podado (D227 de P1 y D228 de P4) y las dos cadenas tachadas.
- Quedan abiertas, reportadas y sin corregir, D226 y D229–D231, y se abren
  D234 y D235 (§0 y §5). D232 y D233 están reservadas por el plan, sin
  ficha escrita todavía.

## 7. Caminos equivocados

- **La primera versión de `d228()` pasaba contra 0.1.230** en su
  comprobación por el motor: con un geosintético de tracción 50 gobierna la
  tracción y la lámina no lee el suelo. Lo mismo le ocurría al caso del
  geosintético en el test. Los dos pasan a tracción 500 y conexión 1000, que
  hace gobernar el arranque por detrás del círculo. Los tests del motor
  enumeran ahora TODOS los soportes que fallan, no el primero: contra
  0.1.230, cada tipo discrimina con los dos modelos en al menos uno de los
  dos tests.
- **`verificar_cierres` no lee `OGR_REPO`.** La primera corrida «contra
  0.1.230» midió el motor vivo y dio CUBIERTO; con `PYTHONPATH` al árbol
  archivado da NO SE SOSTIENE.
- **La tolerancia del eje sin sentido era de 1e-12 para el par
  linealizado**, y falló a 3,5·10⁻¹¹: el par sale de una pendiente numérica.
  Pasa a 1e-9, con la razón escrita en el test.

## 8. Verificación

| Comprobación | Resultado |
|---|---|
| Selecciones dirigidas | 737 casos de soportes, anisotropía, notas, puente, versión e i18n: 736 en verde, y el changelog que aún faltaba. Tras el último cambio, 97 de 97 en los tres ficheros del diagrama de fuerzas |
| Suite entera | 5179 de 5179 (las 5149 de 0.1.230 más los 30 casos nuevos) |
| Discriminación | 24 de 30 fallan en 0.1.230 |
| `d227()` y `d228()` | CUBIERTO POR TEST; NO SE SOSTIENEN contra 0.1.230 |
| `--seco` completo | 171 cierres, 0 bajadas, 0 subidas, 0 nuevas |
| `auditoria_invariantes.py` | 0 ERROR en el 02 y en la raíz |

**Queda por probar:**

- **La CI.** Es lo que decide si el §0 era la causa.
- **A mano:** el tooltip y el diagrama de fuerzas de un soporte cuyo suelo
  no se puede leer, y la nota de resistencia infinita en el panel de notas
  del análisis.
