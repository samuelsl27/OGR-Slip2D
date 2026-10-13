# OGR Slip2D v0.1.307

**El estado inicial de un transitorio (t = 0) se guarda aparte, y *Interpret
Groundwater* lo ofrece primero (D295).** Segunda versión de la tanda P8f.

## 0. Lo que se encontró

- **El dato existía y se tiraba.** La prueba de la interfaz de 0.1.284 (H12)
  hizo un desembalse de una etapa, y el selector «Etapa:» solo tenía «1: t =
  86400 [BC]»: no se podía ver de dónde partía el campo.
  - Todo transitorio resuelve el permanente de sus condiciones iniciales. D268
    publica si convergió, y D277 lo hizo igual al bit al de la puerta del
    permanente.
  - Pero `TransientSeepageSolver.solve_transient` lo guardaba en una variable
    local, y solo sobrevivían su `converged` y su aviso, copiados en cada
    etapa.
- **Por qué no meterlo entre las etapas.** Ponerlo como etapa 0 en
  `transient_results` correría el número de todas las etapas, que se leen por
  número:
  - `groundwater_results(stage=…)`, `model_render` y `stage_rows`, en el API
    y en el MCP;
  - el emparejamiento etapa-factor de `run_transient_stability`.
- **Qué hace la referencia** (tutoriales 18 y 19 de su ayuda): su
  *Interpret* enseña primero el estado inicial («You will first see the
  initial state») y después «Stage 1 (10 hours)». El estado inicial no es una
  de sus etapas.
- **Las huellas.** `model_hash`, `document_hash` y la huella del banco
  (`fechas_estables.huella`, con `limpiar`) resumen el `.ogr` entero, y
  `limpiar` no quita las claves nulas. Una clave escrita siempre
  (`"transient_initial_result": null`) habría cambiado la huella de todo
  modelo regenerado sin que nada cambiara. En el banco, ninguno de sus 19 166
  `.ogr` guarda resultados transitorios.

## 1. Qué cambia

**Decisión de la propietaria (2026-10-13): aparte, en el `.ogr`, como
«0:», y el agente lo lee con `stage="initial"`.**

- **El solver** guarda el permanente inicial en `initial_result`. La firma y
  lo que devuelve no cambian, así que los guiones del banco que lo llaman
  directamente no notan nada.
- **`project.transient_initial_result`:**
  - lo rellena `solve_project_groundwater` en cada transitorio, con
    `notes["time"] = 0.0` y `notes["initial_state"] = True`;
  - un permanente lo borra, y una malla nueva también (`rules.set_fem_mesh`
    lo nombra entre lo que se pierde: «estado inicial del transitorio»);
  - el `.ogr` lo guarda **solo cuando existe**; un archivo anterior abre sin
    él;
  - va en `HEAVY_ATTRS`, así que deshacer *Compute groundwater* o una malla lo
    devuelve, en la ventana y en el API.
- ***Interpret Groundwater*:**
  - la primera entrada del selector es «0: t = 0 (estado inicial)», y las
    etapas siguen siendo «1:», «2:»…;
  - al abrir sigue elegida la última etapa;
  - cada entrada lleva lo que enseña, así que `_on_stage(i)` sigue siendo la
    etapa i;
  - la línea de estado dice «t = 0 | estado inicial»;
  - un transitorio calculado antes de esta versión no lo tiene, y no ofrece
    la entrada.
- **El API y el MCP:**
  - `groundwater_results` y `model_render` aceptan `stage="initial"`. Los
    números de etapa no cambian: `stage=0` sigue siendo la primera;
  - `view="stages"` y el resumen del trabajo añaden `initial_state` al lado de
    la lista de etapas, no dentro;
  - con `result_id` se lee del resultado guardado;
  - el tipo de `stage` en el MCP pasa a «entero o "initial"», y la guía y
    `docs/mcp/herramientas.md` lo cuentan.

## 2. Tests

`tests/test_transient_initial_result_v1307.py`:

- **identidad con una puerta validada (regla 1):** en la presa rectangular de
  Gardner (`test_initial_steady_v1281`), llena al principio y desembalsada en
  una hora, el estado inicial es AL BIT el permanente de la presa llena; la
  etapa 1 no lo es (control);
- **forma cerrada, por el API:** en el acuífero de `test_groundwater_ops_v1200`
  (validado contra la erfc) los dos lados empiezan en H0, así que el estado
  inicial es H = H0 en todo nodo, y la etapa 0 ya no;
- **las etapas no se mueven:** `stage=0` es la primera, las filas siguen
  siendo `[0, 1]`, y `initial_state` va aparte;
- **por resultado guardado (`result_id`) y en imagen (`model_render`);**
- **la ventana real** (el desembalse de `test_transient_v130`, calculado con
  *Compute Groundwater*):
  - la entrada «0: t = 0 (initial state)», también en castellano;
  - elegirla enseña el campo inicial, y al abrir sigue la última etapa;
  - sin estado inicial no hay entrada;
  - deshacer un cálculo lo devuelve;
- **el archivo:**
  - se guarda y se reabre;
  - un proyecto sin transitorio no escribe la clave;
  - un archivo anterior abre sin él;
- **lo borran** un permanente y una malla nueva, y la malla lo dice.

**Tests antiguos que cambian:**
- `test_transient_v130::test_stage_selector_lists_every_stage`: etapas + 1;
- `test_window_undo_v1301`: `MODEL_ATTRS` (copia a mano de LIGHT + HEAVY)
  gana el atributo.

**Con el código de 0.1.306 fallan 12 de los 14 casos,** cada uno por la causa
exacta:
- `stage` solo admitía enteros;
- no había `transient_initial_result`, ni `initial_state`, ni la entrada «0:».

Los dos que pasan son guardas que tienen que pasar en los dos árboles: la
clave no se escribe sin estado inicial, y sin él no hay entrada. Se corrió
sobre una copia del árbol de 0.1.306 sin el buscador editable.

## 3. Verificación

- **Suite entera:** 6048/6048, código de salida 0, a la primera.
- **Banco:** `d295()` en el `verificar_cierres.py` de la raíz, registrada en
  `COMPROBACIONES`: **CUBIERTO POR TEST**. Ciclo de cierre:
  - `verificar_cierres.py` entero: 49 comprobaciones, 0 bajadas;
  - instantánea `Evaluaciones/0.1.307` antes y después (`--forzar`);
  - `retirar_cerrados.py --escribir D295`;
  - poda de la lista P8 y D295 tachada en la fila P8;
  - `generar_prompts.py`: 43 prompts y 19 FALTA, todas de paquetes
    anteriores;
  - `auditoria_invariantes.py` en la raíz y en el 02, con 0 ERROR.
- **Los tests vecinos**, antes de lanzarla: 533/533. Son transitorio,
  operaciones de agua, estado inicial, deshacer, i18n, todo el API, MCP, agua
  en la GUI, firma de malla, *Interpret*, serialización y versión.
- **Ningún número se mueve. A/B en disco, 0.1.306 contra 0.1.307, cada uno con
  su árbol sin el buscador editable:**
  - el desembalse de `test_transient_v130` con *Calculate SF*, Bishop y
    Spencer: los factores de cada etapa, la huella del campo de cada etapa y
    las filas de `stage_rows`, iguales byte a byte;
  - el 02-102 del banco, el transitorio del banco que pasa por la puerta del
    proyecto (`serie_transitoria`, 500 elementos, 2 pasos): sus doce factores,
    iguales con todas sus cifras.
- **Banco:** de los 19 166 `.ogr`, ninguno guarda resultados transitorios, así
  que ninguna huella cambia.

## 4. Pendiente

- **A mano:** el desembalse de H12 en la ventana, con «0: t = 0 (estado
  inicial)» en el selector.
- **Los pasos intermedios de cada etapa** (H12 también los pedía): no se
  guardan, y no hay ficha.
