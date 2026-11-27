# OGR Slip2D v0.1.503

**D442: el conmutador «Superficie probabilística crítica» de Interpretar dibuja la superficie, y
la barra dice si la definió el usuario.** Desde 0.1.37 solo escribía el PF y el índice de
fiabilidad en la barra de estado. Ningún número cambia.

## 0. Lo que se encontró

- **El defecto, medido antes de tocar nada** con la sonda de la ficha (el talud de ejemplo, Path
  Search de 5 sin optimizar, Janbu, una polilínea del usuario y la cohesión Normal al 30 % con
  rango ±60 %, 20 muestras LHS, Overall Slope). Con 0.1.502 la superficie probabilística crítica
  es la polilínea del usuario, con PF 10 %. Al marcar el conmutador, la imagen del lienzo no cambia
  ni un bit, y la barra no dice que la superficie sea del usuario. Es el mismo defecto que v0.1.126
  arregló en su vecino *Show GM Surfaces*.
- **De dónde sale «es del usuario».** La superficie llega a Interpretar como un diccionario.
  Desde ahí no se puede saber de quién es: una polilínea del usuario y una de la búsqueda con los
  mismos vértices dan el mismo diccionario. Lo sabe la corrida (`is_user_surface_of`, por
  identidad), así que la marca se pone donde se acumula cada superficie (`_accumulate_surfaces`).
  Se pone antes del `seen`: una superficie que es a la vez del usuario y de la búsqueda se cuenta
  una vez, y aun así es del usuario.
- **Un hueco que el arreglo tenía que cerrar.** La puerta de D413 desmarca el conmutador cuando
  se queda gris. Con el resultado probabilístico ya borrado, la función salía antes de tocar el
  lienzo. Si el conmutador hubiera dibujado algo, el dibujo se habría quedado en pantalla. Ahora se
  redibuja también en ese camino, y la superficie se pide al resultado en cada redibujado, así que
  si el resultado desaparece se lleva el dibujo con él.

## 1. Qué cambia

- `ogr_slip2d/probabilistic.py`: `SurfaceProbability.user_defined` (por defecto `False`), que pone
  `_accumulate_surfaces`. Ni el PF, ni el índice, ni la superficie elegida cambian: el campo no
  entra en ninguna comparación.
- `ogr_gui/interpret_window.py`:
  - `_toggle_critical_prob` dibuja y borra con `_refresh_canvas_with_highlights`, el único sitio
    que dibuja el resultado. Desmarcarlo limpia la barra;
  - la barra añade «, defined by the user.» (las palabras de D401) cuando `user_defined`;
  - `_critical_probabilistic_dict` da la superficie mientras el conmutador está marcado.
- `ogr_gui/canvas/canvas_view.py`: `display_search_result` acepta `probabilistic_surface_dict`, que
  se guarda con lo demás para `refresh_scene`. Se dibuja con el trazo de los mínimos
  (`is_query`, 2 px, la decisión de la propietaria) en naranja `#f77f00`
  (`PROBABILISTIC_SURFACE_COLOUR`), con su *tooltip*.
- `ogr_gui/i18n/__init__.py`: el castellano de los dos textos nuevos.

**Sin hacer, a propósito:** `user_defined` no sale en el `to_dict` del resultado probabilístico, que
es lo que lee el agente. La ficha pedía la barra. Si el agente también lo necesita, es una entrada
nueva de `results_get`.

## 2. Lista de comprobación de la guía de interfaz

- Identidad: la crítica sigue en rojo, la seleccionada en morado y los mínimos y consultas en
  negro. El naranja no coincide con ninguno. **Para que lo mire la propietaria:** en los modos
  *Minimum* y *All Surfaces*, cada superficie toma el color de su factor en la leyenda, y el
  naranja de la leyenda (FS 0,75–1,0) se le parece. El grosor (2 px frente a 1,2) las distingue,
  pero no del todo. La captura está en el resumen de la sesión. **La propietaria dio por bueno
  el naranja el 2026-11-27.**
- Acción: no hay ninguna nueva. El conmutador sigue en *Statistics*, con su puerta de D413.
- Mensaje: la barra dice el PF, el índice y, si es el caso, que la superficie es del usuario.
  Ningún diálogo modal en el camino que corre el test.
- Lienzo: lo que se marca se dibuja, y lo que se desmarca vuelve a la imagen de antes, bit a bit
  (regla 7).
- Gemela en OGR-GUI (`ogr_ui`): sin comprobar. Hay que avisar a esa sesión.

## 3. Tests

- `tests/test_interpret_crit_prob_draw_v1503.py` (nuevo, 4 tests; las dos corridas estadísticas
  se calculan una vez por archivo):
  - la premisa: la polilínea es la superficie crítica, con PF 10 % y `user_defined`;
  - marcar el conmutador cambia la imagen, desmarcarlo la devuelve bit a bit, y la barra dice
    «defined by the user.» con el PF 10,00 %;
  - el control: sin la polilínea, la superficie es de la búsqueda, se dibuja y la barra no dice
    «user»;
  - la puerta gris desmarca el conmutador y se lleva el dibujo.

  Contra 0.1.502 fallan 3 de 4: dos por `user_defined` y uno porque «the toggle drew nothing». El
  de la puerta pasa, porque entonces no había nada que llevarse.
- Áreas `interpret`, `overall_slope`, `probabilistic`, `surface_key`, `i18n`, `translation` y
  `core_messages`: 373 en verde. `texts`, `terms`, `voice`, `budget`, `wrap` y `license`: 131 en
  verde.

## 4. Suite

La suite entera se corre al final de la tanda (revisión primero, una suite al final).
