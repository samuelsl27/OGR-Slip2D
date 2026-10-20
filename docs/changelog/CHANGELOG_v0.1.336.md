# OGR Slip2D v0.1.336

***Escalar contorno* y *Rotar contorno* se hacen con clics, primero el contorno y después el pivote;
`EXPAND_SHRINK` se retira; y *Expandir / contraer* por polilínea funciona por fin (D142, segunda parte,
D142 cerrada; D334; D339).** Cuarta versión de la tanda P8j.

## 0. Lo que se encontró

- **D142, los tres modos que quedaban.**
  - `SCALE_BOUNDARY` y `ROTATE_BOUNDARY` estaban en la tupla de un clic del lienzo, y la ayuda de Rotar
    prometía un clic de pivote que no existía. Nadie entraba en ellos: la acción elegía el contorno en
    una lista y el pivote se tecleaba, con (0, 0) por defecto.
  - `EXPAND_SHRINK` tampoco tenía quien entrara en él, y el dibujo de la polilínea es de
    `DRAW_EXPAND_SHRINK`.
- **D334, medido el 2026-10-20 en 0.1.335 con la ventana real, antes de tocarlo:**
  - la polilínea (50, 35) → (60, 37) → (70, 35) se dibujaba con sus tres puntos exactos, e Intro no
    hacía nada: el área del exterior seguía en 550 y el modo no se cerraba;
  - la causa: el modo no tiene tipo de contorno, así que `_finish_drawing` cancelaba sin decir nada, y la
    señal desviada a expandir/contraer seguía desviada;
  - **el contorno de material dibujado después no se añadía, y recortaba el exterior de 550 a 450 m²**,
    sin un mensaje: se aplicaba como expandir/contraer. Así desde v0.1.59. El único test llamaba a la
    ranura directamente.
- **D339, encontrado al preparar esta versión y medido antes de arreglarlo:**
  - `QAction.triggered` lleva `checked`, y PySide6 se lo pasa a una ranura que acepta un parámetro;
  - *Escalar contorno…*, *Rotar contorno…* y *Expandir / contraer…* lo tomaban como `preselected_idx`, y
    `False` no es `None`;
  - desde el menú, Escalar y Rotar no preguntaban qué contorno y transformaban `boundaries[False]`, el
    **primero**, el exterior en la pendiente medida; y Expandir / contraer no buscaba el exterior;
  - **censo** de las acciones del menú con un parámetro opcional: cinco. Las otras dos (*Cambiar ángulo
    del talud* y *Asignar superficie de agua*) ignoran el valor o no lo encuentran, sin efecto.
- **La nota del diálogo de escalar era falsa:** «el pivote es (0, 0) por defecto; para usar el
  centroide, déjalo a cero…». (0, 0) nunca fue el centroide.

## 1. Qué cambia

Por decisión de la propietaria (2026-10-19, cablear como la referencia y retirar uno):

- **Escalar y Rotar:**
  - desde el menú, la acción entra en su modo;
  - en el lienzo, el primer clic elige el contorno, que se ve como un fantasma discontinuo, y el segundo
    clic, ajustado, es el pivote (`boundary_base_picked`);
  - **el diálogo abre con ese pivote en sus dos casillas, que siguen editables**: es el camino para
    teclear otro;
  - desde el menú contextual de un contorno, sin clic de pivote, el diálogo propone el centroide del
    contorno, el mismo valor por defecto que el API;
  - Esc suelta el contorno elegido y la herramienta sigue, y un cambio de modo lo olvida (D308);
  - un clic que no cae sobre ningún contorno se rechaza con un mensaje;
  - la nota falsa se sustituye por una que dice de dónde sale el pivote.
- **`EXPAND_SHRINK` retirado:** el miembro, su cursor, su ayuda, su entrada en la tupla del lienzo y su
  rama en la ventana. Se quedan `DRAW_EXPAND_SHRINK` y la entrada del menú contextual.
- **D334:**
  - la polilínea sale por una señal propia, `expand_shrink_drawn`, conectada una sola vez;
  - al terminar el dibujo el lienzo sale del modo;
  - **la desviación de `boundary_drawn` desaparece**, así que el contorno siguiente va al modelo;
  - la ranura acepta la polilínea o un contorno que la lleve, como el de `test_f2_rules_v1196`.
- **D339:** en las tres acciones, un booleano no cuenta como índice.
- **Cinco claves nuevas** (las dos ayudas, dos mensajes del lienzo y la nota) y cuatro retiradas (las tres
  ayudas viejas y la nota falsa).

## 2. Tests

- **`tests/test_scale_rotate_pick_v1336.py`** (nuevo, 14 casos), con clics reales en el lienzo mostrado:
  - **desde el menú, Escalar y Rotar entran en su modo y no abren nada ni cambian el modelo** (D339:
    en 0.1.335, el exterior salía escalado);
  - el diálogo abre con el pivote pulsado;
  - **contra las transformaciones mismas (regla 1):** escalar por 2 lleva cada vértice v a p + 2(v − p),
    y rotar 90° conserva |v − p| y suma exactamente 90° a su dirección;
  - un pivote tecleado manda, y deshacer devuelve el contorno;
  - el fantasma se ve hasta el pivote; Esc y el cambio de modo olvidan el contorno; un clic en el vacío
    no elige nada;
  - **Expandir / contraer desde el menú apunta al exterior, aunque no sea el primero** (D339);
  - `EXPAND_SHRINK` ya no existe y `DRAW_EXPAND_SHRINK` sí.
- **`tests/test_expand_shrink_draw_v1336.py`** (nuevo, 4 casos), con clics reales y el forzado activo
  para que los extremos caigan sobre los vértices del exterior:
  - **el exterior crece exactamente el triángulo de la polilínea**, de base 20 sobre y = 35 y vértice en
    el clic central (la identidad de `test_f2_rules_v1196`);
  - es un paso de deshacer;
  - un contorno de material dibujado después entra en el modelo, también tras un Esc a medio dibujo.
- Los dos sustituyen cada diálogo y cada cuadro de mensaje por un falso que nunca bloquea, para que en el
  árbol viejo fallen en vez de colgar la corrida (como pasó en 0.1.335).
- **Cambio deliberado:** `test_add_surface_three_points_v1168`. El conjunto de modos en los que no entra
  nadie queda vacío, y el total de ayudas baja de 35 a 34.

**Con el código de 0.1.335 fallan 15 de los 18 casos nuevos y los dos cambiados de v1168.** Los tres que
pasan allí lo hacen por casualidad:
- «un pivote tecleado manda»: el menú viejo escalaba directamente el exterior, que es el contorno del caso,
  con el pivote del falso;
- «deshacer devuelve el contorno»: lo devuelve también allí;
- «expandir/contraer es un paso de deshacer»: allí no cambia nada que deshacer.

Se corrió sobre un `git archive` de 0.1.335, sin el buscador editable.

## 3. Verificación

- **Los dos tests de esta versión**, 18/18 a la primera, y los vecinos, 179/179 en 14 archivos (v1168, las
  reglas de v1196, el lienzo, mover contorno, los diálogos, su censo, el diccionario y el castellano).
- **Suite entera:** 6301/6301, `EXIT=0`, 72 min.
- **Banco:**
  - `verificar_cierres.py` entero: 84 comprobaciones, 0 bajadas;
  - **D142 CUBIERTO POR TEST**: el censo AST de los 39 modos no encuentra ninguno sin quien entre, y
    EXPAND_SHRINK no existe;
  - **D334 CUBIERTO POR TEST**: medido con la ventana real, la polilínea lleva el exterior de 550 a 570 m²
    y el contorno siguiente se añade sin tocarlo (en 0.1.335: 550, y luego 450);
  - **D339 CUBIERTO POR TEST**: Escalar desde el menú entra en su modo sin abrir nada, y Expandir /
    contraer apunta al exterior, que en la medida es el segundo contorno;
  - instantánea `Evaluaciones/0.1.336`, las tres retiradas y tachadas, prompts (35) y auditorías con 0
    ERROR.
- **Ningún número del motor cambia:** es interfaz. Las transformaciones son las de siempre (`g_scale`,
  `g_rotate` y `apply_expand_shrink`), y cambia quién les da el contorno y el pivote.

## 4. Pendiente

- **0.1.337:** las anotaciones al DXF como entidades nativas, y D333.
