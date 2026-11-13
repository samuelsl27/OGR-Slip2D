# OGR Slip2D v0.1.444

**Los círculos que dibuja el usuario tienen ya lo que 0.1.427 dio a las polilíneas (D402):** un círculo que una
comprobación rechaza deja una nota, las entradas del menú en gris dicen por qué, y la ventana no guarda un círculo con
el tipo de superficie no circular. Medido con 0.1.443:

| caso | 0.1.443 | ahora |
|---|---|---|
| talud de ejemplo con una rejilla de 3×3×3, Bishop, círculo del usuario de centro (32, 16) y radio 5: F = 3,0019, que m-alfa rechaza | la corrida no decía nada | una nota, con su factor y el motivo |
| proyecto nuevo, tipo no circular (Path): entradas en gris sin motivo en la barra de estado | cinco: Rejilla automática, Añadir rejilla y las tres de círculos | ninguna |
| proyecto nuevo, tipo circular con Slope | dos: Rejilla automática y Añadir rejilla | ninguna |
| un modelo con nivel freático o con grieta de tracción | Añadir nivel freático o Añadir grieta de tracción, en gris sin motivo | con su motivo |
| el tipo cambia a no circular con un modo de círculo puesto, y se entrega el círculo (clic, tecleado, tres puntos) | tres círculos guardados y tres pasos de deshacer; el camino tecleado abría «Radius:» | ninguno; sale del modo y lo dice, sin preguntar nada |

Es la decimoséptima versión de la tanda P10, y la última del plan aprobado el 2026-11-12. **Ningún factor cambia.**

## 0. Lo que se encontró

- **Paso 0, sobre 0.1.443 (34c90f0):** el fragmento del prompt da lo que dice la ficha: `3.001898542106169 False
  1.135451296006176 []`; las cinco entradas en gris sin motivo con Path, dos con Slope, ninguna con rejilla; y `1 1`,
  `2 2`, `3 3` con «Circle added: …» y `getDouble: ['Radius:']`.
- **N1, la misma clase de defecto** (visto al planificar): Rejilla automática y Añadir rejilla se ponían en gris, con
  una búsqueda que no usa rejilla, con `setEnabled` y un tooltip, que ningún menú enseña. Entran con las tres de
  círculos. Las de polilíneas ya usaban `gate` desde 0.1.427.
- **Otras dos de la misma clase, que encontró la revisión:** Añadir nivel freático y Añadir grieta de tracción, en un
  modelo que ya tiene el suyo. Un proyecto nuevo no las pone en gris, y por eso ni el paso 0 ni el test de D289b las
  veían; con el talud de ejemplo cargado, Añadir nivel freático estaba en gris sin motivo en todos los estados.
  Entran también, con la frase de su tooltip, por decisión de la propietaria en el resumen de la versión
  (2026-11-13). El revisor midió que son todas las que quedaban.
- **El motivo, en una línea.** Los tooltips de la rejilla y de la grieta tienen varias líneas y la barra de estado
  enseña una: el motivo es la misma frase, ya traducida, con los saltos por espacios. Ninguna cadena nueva.
- **La nota podía contradecir a la corrida** (revisión). Si ninguna superficie válida es admisible, la crítica cae
  en la más baja de las rechazadas. Con la búsqueda vacía y el círculo del usuario rechazado, la corrida decía a la
  vez «no puede ser la superficie crítica» y «la superficie informada es la que definió el usuario». Ahora la nota
  no se dice del círculo que la corrida informa; de los demás rechazados, sí (confirmado por la propietaria).
  - **La polilínea tiene esa misma contradicción desde 0.1.427**, medida: la que m-alfa rechaza (F = 0,223), sola
    bajo un foco que vacía la búsqueda, deja las dos notas. **Se reporta y no se toca:** es anterior a esta versión
    y su test no se puede mover sin decisión de la propietaria.
- **Camino equivocado.** Escribí un test en el que el tipo cambiaba mientras el cuadro «Radius:» estaba abierto, y un
  comentario que decía que eso podía pasar. El test fallaba por otra cosa: mi simulación cambiaba el ajuste dentro
  del paso de deshacer del propio manejador, y el paso lo registraba. No tengo medido que el tipo pueda cambiar con
  ese cuadro abierto, así que quité el test y el comentario. La comprobación de `_add_user_circle` se queda: es la
  del camino del clic, y el tecleado pasa por ella otra vez sin coste.
- **Reportado y sin tocar** (lo midió el revisor):
  - **dos círculos del usuario iguales dejan una sola nota**, porque las notas se guardan una vez por frase y los
    círculos no se numeran (las polilíneas sí). Las demás notas de círculos ya eran así;
  - **el modo sigue puesto cuando el tipo cambia:** el usuario aún hace sus clics antes de que se le diga que no.
    Igual que con las polilíneas;
  - **la barra de estado puede cortar el motivo de la rejilla:** con las fuentes de la prueba sin pantalla caben
    481 px y la frase pide 1046 en inglés y 1251 en castellano, así que se pierde la mitad que dice qué hacer. Los
    motivos de Block Search son igual de largos. A mirar en la prueba a mano, con fuentes de verdad.
- **La nota es nueva en el JSON del agente** de una corrida que tenga un círculo así: una entrada más en `notes` y en
  los avisos. Ninguna otra cosa cambia.

## 1. Qué cambia

- **Motor** (`ogr_slip2d/search.py`, `ogr_slip2d/search_note_messages.py`): código nuevo `search.user_inadmissible`.
  `_evaluate_user_surfaces` lo emite, cuando ya tiene todos los círculos, para cada círculo válido que las
  comprobaciones posteriores rechazan y que no es la superficie que la corrida informa. El texto es el de la
  polilínea desde «has a factor of safety», con el círculo nombrado por su centro y su radio:
  - «The user-defined surface at centre (32, 16) with radius 5 has a factor of safety of 3.002, but the
    post-analysis checks reject it, so it cannot be the critical surface: m_alpha < 0.2 on 1 slice(s)»;
  - «La superficie definida por el usuario con centro en (32, 16) y radio 5 tiene un factor de seguridad de 3.002,
    pero las comprobaciones posteriores al cálculo la rechazan, así que no puede ser la superficie crítica: …».
- **Siete entradas, con `gate`** (`ogr_gui/main_window.py`, `refresh_action_availability`): en gris llevan su motivo
  como status tip, que la barra de estado enseña; habilitadas, ninguno. Los tooltips no cambian.
  - las tres de círculos: «Only available with Surface Options -> Surface Type = Circular.»;
  - Rejilla automática y Añadir rejilla: «The current Search Method does not use a slip-circle centre grid. Switch
    to Surface Options → Grid Search to use this action.»;
  - Añadir nivel freático: «Only one Water Table is allowed.»;
  - Añadir grieta de tracción: «Only one Tension Crack boundary is allowed. Delete the existing one to add a new
    one.».
- **Los caminos por los que entra un círculo** (`_add_user_circle`, `_type_surface_centre_radius` antes de sus
  cuadros, `_on_surface_3pt_picked`) preguntan a una sola comprobación, `_circles_refused()`. Con el tipo no circular
  sale del modo y dice las dos frases que ya existían: «Only available with Surface Options -> Surface Type =
  Circular. The surface was not added.». No deja paso de deshacer ni marca el proyecto como modificado. El API no
  cambia: `user_surface_add` sigue con su `Conflict`.

## 2. Qué se probó

- **`tests/test_user_circles_parity_v1444.py`** (17 casos; cinco corridas pequeñas y una sola `MainWindow`):
  - **la nota contra la propia corrida:** su factor es el `fos` de la evaluación, al último bit; su motivo, el de esa
    evaluación; una nota por método, cada una con el factor de su método (Bishop, Janbu y Spencer rechazan el mismo
    círculo con factores distintos); llega a los avisos; y en castellano;
  - **no se dice del círculo que la corrida informa:** con la búsqueda vacía y dos círculos rechazados, la corrida
    informa el más bajo como del usuario y dice del otro que está rechazado;
  - **ningún número se mueve:** la crítica, los contadores y los factores de la búsqueda son los de la corrida sin
    el círculo, en el mismo proceso. (Es un control dentro del árbol; contra 0.1.443 lo midió el revisor: críticas y
    factores idénticos, también con 114 círculos y dos métodos.);
  - la frase es la de la polilínea; un círculo admisible no deja la nota, y uno sin factor deja la de siempre y solo
    esa;
  - toda entrada en gris alcanzable desde la barra de menús tiene motivo, en cuatro estados de la búsqueda (Path,
    Block, Slope y rejilla) y con un nivel freático y una grieta de tracción en el modelo; las siete dicen su frase;
    la de la rejilla y la de la grieta van en una línea y sus tooltips conservan las suyas; habilitadas, sin motivo
    y con el tooltip de siempre;
  - las cuatro entregas (el clic, el tecleado con el centro y sin él, y los tres puntos), con el tipo cambiado
    mientras el modo estaba puesto, no tocan `user_surfaces`, ni la pila de deshacer, ni la marca de modificado; salen
    del modo, lo dicen (también en castellano) y no abren ningún cuadro; con el tipo circular añaden el círculo como
    siempre, con su paso de deshacer.
- **Discriminación:** en el árbol de 0.1.443, sin el buscador editable, fallan 12 de 17, todos por lo que miden (la
  nota que no está, los status tips vacíos y los círculos guardados); pasan los cinco de control.
- **Mutantes** (`mutants_d402.py`, en el banco): 30, todos muertos; 9 son de la revisión.
- **Cambia a propósito** `tests/test_search_notes_v1349.py`: la muestra del código nuevo en `_LATER`, que el test
  exige para todo código.
- **Vecinos**, con los patrones `user_surfaces add_surface disabled_reasons search_notes user_polylines
  spanish_texts terms_spanish f3b_ops window_undo results_query windows_user user_circles i18n budget translat voice
  labels menu notes boundary water tension` del runner: 838 casos en verde en 53 archivos, el nuevo entre ellos.
- **La revisión adversaria** (un agente, que miró código, test y changelog; el cambio es más pequeño que los
  anteriores): ningún defecto grave. Además de lo de arriba encontró que el ayudante del test que sustituye un
  método dejaba el atributo puesto en una clase que lo hereda, que la cabecera del test contaba mal sus corridas, y
  cuatro mutantes que sobrevivían (el camino tecleado sin centro, la marca de modificado, la nota solo para los
  métodos «simplified», y la caída de la crítica). Todo arreglado.
- **Banco, en seco:** `d402()` da SIGUE ABIERTO con el árbol de 0.1.443 y CUBIERTO POR TEST con el nuevo; D289b, D142
  y D346 de la raíz, y D58 y D101 del 02, siguen cerrando.
- **La suite entera** con `--jobs 4`, sobre el árbol final: **7538 casos, 7537 en verde, 0 fallos y 1 omitido**, sin
  fugas ni tramos muertos. La serie no toca (22 commits desde la última).

## 3. Qué queda

- **Sin ficha, a decidir por la propietaria:** la nota de la polilínea rechazada, que contradice a la corrida cuando
  esa polilínea es la que se informa; y los dos círculos iguales con una sola nota.
- **A mano, por la propietaria:** con el tipo no circular, pasar el ratón por las tres entradas de círculos y por
  las dos de rejilla y leer el motivo en la barra de estado, mirando si la frase de la rejilla cabe; y con un nivel
  freático en el modelo, Añadir nivel freático.
- **Fichas que siguen en P10:** D420 (0.1.445) y las demás del orden del 2026-11-11. El plan aprobado el 2026-11-12
  (0.1.440–0.1.444) termina aquí.
