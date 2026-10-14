# OGR Slip2D v0.1.309

**El factor de seguridad del estado inicial (t = 0) de un transitorio se
calcula cuando alguna etapa pide factores (D312).** Cuarta y última versión
de la tanda P8f.

## 0. Lo que se encontró

- **La referencia lo enseña.** Se encontró al investigar D294. El tutorial de
  la referencia sobre agua transitoria con estabilidad enseña el estado inicial
  con su factor de seguridad («the slope is quite stable at this time»), y
  para ella el estado inicial no es una etapa.
- **El banco lo publica.** El 02-102 da «permanente inicial» 1,745 con φb = 0
  y 1,815 con φb = 37, dos de sus cuatro criterios de cierre. Su guion lo
  reproduce metiendo a mano una etapa en t = 0.
- **Nadie podía pedirlo.**
  - `set_transient` exige tiempos de etapa positivos, como la referencia.
  - El estado inicial no era una etapa, y hasta D295 ni siquiera se guardaba.
- **El motor ya sabía hacerlo.** Una etapa de duración cero con *Calculate SF*
  lo calcula con el agua de las condiciones iniciales (`in_force`,
  `test_the_initial_instant_can_have_a_factor_too`).

## 1. Qué cambia

**Decisión de la propietaria (2026-10-13): automático, sin ajuste nuevo.**
Una casilla propia habría sido un campo nuevo en `GroundwaterSettings`, que
cambia la huella de todo `.ogr` regenerado y necesita su test de regla 7, y la
referencia no la tiene.

- **`run_transient_stability`:**
  - si alguna etapa lleva *Calculate SF* y algún material toma la presión del
    campo, calcula también el factor de `project.transient_initial_result`,
    con el agua de las condiciones iniciales (`with_stage_water`);
  - lo deja en `outcome.initial` (un `StageStability` con índice −1) y en las
    notas del estado inicial (`fos`, `fos_min`), que se guardan con él (D295);
  - ningún índice de etapa cambia;
  - cuesta una búsqueda más: N + 1 en lugar de N.
- **El cálculo de los factores de un campo con su agua** sale del bucle a una
  función local, `factors_of`, que usan las etapas y el estado inicial. Es el
  mismo código.
- **Dónde se ve:**
  - la entrada «0:» de *Interpret Groundwater*, con su «FoS …»;
  - las dos curvas del factor contra el tiempo, que empiezan en t = 0
    (`fos_history`, D311);
  - el `initial_state` del agente (`fos` en sus notas), y la guía del MCP lo
    cuenta.

## 2. Tests

`tests/test_initial_factor_v1309.py`, en el desembalse de `test_transient_v130`:
- **identidades (regla 1, consistencia con caminos validados):**
  - el factor del estado inicial es AL BIT el de una etapa de duración cero en
    t = 0 de la misma corrida, el camino que ya usa el 02-102;
  - y el de la estabilidad sobre el permanente de las condiciones iniciales por
    la puerta del permanente: el campo es el mismo al bit (D277), y la búsqueda
    y el agua también;
  - **una hipótesis mía, refutada al medir.** El test afirmaba también que «el
    desembalse lo baja», que la primera etapa tendría menos factor que el
    estado inicial. Falló:
    - el factor SUBE: 0,862 en t = 0, 0,889 en la etapa 1 y 0,904 en la 2;
    - y es lo correcto en este modelo: la coronación está a la izquierda
      (y = 50), y el «desembalse» del test baja la carga de 45 a 28 m en ese
      borde, o sea, el agua DETRÁS de la coronación, no un embalse apoyado en
      la cara;
    - la aserción se quitó y queda escrito por qué;
- **control:** sin etapas con factor, o sin material acoplado, no se calcula;
- **llega a la historia** (empieza en t = 0), **a la ventana** («0:» con su
  FoS) **y al agente** (`initial_state`).

**Un test anterior que cambia, por lo pedido:** en
`test_fos_chart_v1308::test_the_series_handed_to_the_chart` la serie gana el
punto t = 0 delante de las dos etapas (`[0.0, 1e4, 1e6]`). Afirmaba dos
puntos.

**Con el código de 0.1.308 fallan los 5:** no existe `outcome.initial`, y los
controles también lo leen. Se corrió sobre una copia del árbol de 0.1.308 sin
el buscador editable.

## 3. Verificación

- **Suite entera:** 6058/6058, código de salida 0, a la primera.
- **Banco:** `d312()` en el `verificar_cierres.py` de la raíz, registrada en
  `COMPROBACIONES`: **CUBIERTO POR TEST**. Ciclo de cierre:
  - `verificar_cierres.py` entero: 51 comprobaciones, 0 bajadas;
  - instantánea `Evaluaciones/0.1.309` antes y después (`--forzar`);
  - `retirar_cerrados.py --escribir D312`;
  - poda de la lista P8 y D312 tachada en la fila P8;
  - `generar_prompts.py`: 41 prompts y las mismas 19 FALTA de paquetes
    anteriores;
  - `auditoria_invariantes.py` en la raíz y en el 02, con 0 ERROR.

  La tanda P8f queda terminada: D294, D295, D311 y D312 cerradas.
- **Los tests vecinos**, antes de lanzarla: 360/360, tras el ajuste de arriba.
  Son transitorio, *Interpret*, el gráfico de D311, operaciones de agua,
  trabajos y deshacer del API, agua en la GUI y acoplamiento transitorio.
- **Los factores de las etapas no se mueven.** A/B en disco, 0.1.308 contra
  0.1.309, con el desembalse con *Calculate SF* y Bishop y Spencer: los
  factores de cada etapa, la huella de su campo, las filas de `stage_rows` y
  los avisos, iguales byte a byte. La búsqueda de más no toca las etapas.
- **Lo único nuevo es un número que antes no existía:** el factor en t = 0
  (0,862 en el desembalse del test).

## 4. Pendiente

- **A mano:** el desembalse con «0:» y su factor, y la curva del factor contra
  el tiempo desde t = 0.
- **El banco:** el 02-102 podría medir su «permanente inicial» por este camino
  en lugar de por la etapa en t = 0 metida a mano. Es la misma cifra por las
  identidades de arriba, y no se toca su guion en esta versión.
