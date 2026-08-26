# Plan de implementación

## Enfoque

Tres frentes en este orden, porque el primero cambia los números del segundo.
**A**: el eje de momentos de una poligonal pasa de una construcción sobre la
cuerda al centro del círculo que mejor ajusta sus vértices, con la identidad
del refinamiento como juez y el banco entero medido antes y después.
**B**: una búsqueda por enjambre nueva, cuyas partículas son **círculos** en la
parametrización ya validada de Slope Search, con modo unimodal y multimodal, y
extracción de mínimos distintos por radio de especie.
**C**: un tipo de contorno nuevo que orienta el buzamiento de los tres modelos
anisótropos punto a punto, en vez del ángulo global de hoy.

Y de paso, porque son exactamente la maquinaria que B estrena, se resucitan las
dos acciones de «varios mínimos» que ya existen y no hacen nada.

## Archivos que se tocan

| Archivo | Qué cambia |
|---|---|
| `ogr_slip2d/surface.py` | `moment_axis`: centro del círculo de mejor ajuste; la construcción vieja queda citada y refutada, con su medición |
| `ogr_slip2d/particle_swarm.py` | **nuevo** — enjambre uni/multimodal, especies por radio |
| `ogr_slip2d/search.py` | `SearchResult.minima`; optimización **por mínimo**; círculos discretizados antes de pasear |
| `ogr_slip2d/analysis_runner.py` | rama `particle_swarm` en `build_search`; avisos |
| `ogr_slip2d/slicer.py` | el ángulo de buzamiento local viaja en `SliceContext` |
| `ogr_core/geometry/anisotropic_surface.py` | **nuevo** — punto más cercano y regla del vértice |
| `ogr_core/geometry/boundary_type.py`, `boundary.py`, `transforms.py` | `ANISOTROPIC_SURFACE` y sus enganches |
| `ogr_core/materials/strength_model.py`, `builtin_models.py` | campo nuevo en `SliceContext`; los tres modelos anisótropos lo leen |
| `ogr_core/project/settings.py` | `SearchMethod.PARTICLE_SWARM`, ajustes del enjambre, enjambre mejorado |
| `ogr_core/dxf/importer.py` | mapa DXF del contorno nuevo |
| `ogr_gui/dialogs/grid_dialogs.py` | panel del enjambre en *Surface Options*, y las dos listas de métodos duplicadas a mano |
| `ogr_gui/dialogs/project_settings_dialog.py` | casilla del enjambre mejorado, en *Advanced* |
| `ogr_gui/dialogs/material_properties_dialog.py` | asignar superficie anisótropa a un material |
| `ogr_gui/interpret_window.py` | modo de varios mínimos; `Show`/`Pick GM Surfaces` vivas y sin modal |
| `ogr_gui/canvas/tool_mode.py`, `canvas_view.py`, `graphics_items.py` | modo de dibujo, color, z-order, dibujo de los varios mínimos |
| `ogr_gui/main_window.py` | acción *Add Anisotropic Surface* en el menú Boundaries |
| `ogr_gui/i18n/__init__.py`, `tests/test_i18n_coverage_v141.py` | traducciones y un cognado a la lista blanca |
| `tests/test_moment_axis_v1126.py` | **nuevo** — la identidad del refinamiento |
| `tests/test_multimodal_v1126.py` | **nuevo** — el enjambre y el problema 103 |
| `tests/test_anisotropic_surface_v1126.py` | **nuevo** |
| `docs/changelog/CHANGELOG_v0.1.126.md` | **nuevo** |
| Los **siete** sitios de versión | 0.1.125 → 0.1.126 |

## Decisiones de diseño

### Por qué el eje va primero, y por qué el criterio es una identidad

La construcción actual —`midpoint(cuerda) + rot90(cuerda)`— se dedujo en
v0.1.92 del `xc, yc` que **imprime** el programa de referencia para una
superficie no circular, y ajusta a 1,2e-6 en dos casos. Pero el propio
comentario reconoce que el `r` que acompaña a ese par es un valor de
presentación: «la distancia media del eje a los vértices… no el radio de ningún
círculo que pase por ellos». Que un trío impreso para mostrar sea el eje que el
motor **usa** nunca se comprobó.

Medido sobre el círculo crítico del problema 103 (centro 125,400 · 56,700,
R = 56,40, 200 dovelas):

| | Ordinary | Bishop | Spencer |
|---|---|---|---|
| arco | 1,3043 | 1,3043 | 1,3043 |
| 192 cuerdas, eje construido | **1,2427** | **1,2500** | 1,3032 |
| 192 cuerdas, eje = centro real | **1,3043** | **1,3043** | **1,3043** |

y el eje construido cae en **(137,672 · 120,486)**, a 65 m del centro. Spencer
se salva porque satisface fuerzas **y** momentos, así que no depende del punto.
La identidad del refinamiento gana a un campo impreso: es geometría, no
observación.

**Alternativas consideradas.** (a) Caso especial «si la poligonal es un arco,
usa su centro»: introduce un salto —una superficie casi circular cambiaría de
eje de golpe— y no dice nada del caso general. (b) Dejarlo y avisar: un aviso
no arregla que el número siga en pantalla. (c) El centro del círculo de mejor
ajuste por mínimos cuadrados (forma cerrada de Kåsa): continuo, se reduce
exactamente al centro para un arco, y no necesita umbral. Se elige (c).

**El override del usuario sigue ganando**, y `SlipCircle` y `CompositeSurface`
siguen contestando antes con su centro real, como desde v0.1.111.

### Por qué la partícula es un círculo, y en esa parametrización

La ayuda de la referencia dice que su enjambre «can use either spherical or
ellipsoidal surfaces»: las partículas **no** son poligonales; la forma no
circular la produce después la optimización. Eso además esquiva la dependencia
que el encargo señalaba —D22 sigue abierto: sobre este mismo modelo Simulated
Annealing devuelve 1,3741 donde la rejilla circular da 1,3057—, porque el
enjambre busca en el mismo espacio donde la rejilla ya es competitiva.

Se elige la parametrización de Slope Search, `(x_entrada, x_salida, ángulo en
el pie)`, y no `(xc, yc, R)`, por tres razones: sus límites son los *Slope
Limits* y la ventana de ángulo, así que **«el 10 % de la extensión del espacio
de búsqueda» queda definido sin inventar un dominio**; el círculo siempre
aflora en el terreno; y reutiliza `_circle_from_point_tangent_point`, ya
probado desde v0.1.17.

### Qué hace significativo a un mínimo

El encargo pedía elegir entre distancia entre superficies, diferencia de factor
o las dos. **La fuente lo decide**: el filtro documentado es un radio en el
espacio de búsqueda, con 10 % por defecto, y el número de candidatos es el
número de partículas. La diferencia de factor no interviene. El algoritmo que
lo implementa es la identificación de semillas de especie de Li (2004): se
ordenan las partículas por factor, la mejor siembra una especie, todo lo que
caiga dentro del radio se le asigna, y se repite con la siguiente no asignada.

### Dónde se aparta la implementación de la fuente, y se dice

- La ecuación documentada `V_i = r1·(SG − S_i) + r2·(SB − S_i)` **no lleva
  término de inercia** ni factor de constricción, a diferencia de la forma
  canónica de Kennedy y Eberhart. Se implementa la forma documentada y se
  escribe en el código que es la de la referencia, no la del artículo.
- El *enjambre mejorado* reubica al azar «una porción» de las partículas de
  mayor factor al final de cada iteración. **Qué porción no está publicada**:
  se elige un valor, se declara en el código y se mide que mueve el número.

### La superficie anisótropa

La regla está documentada literalmente y **no** es la de una superficie de
agua: para un punto del modelo se toma el **punto más cercano** de la polilínea
—no la vertical— y la orientación del segmento en ese punto es el ángulo. Si el
punto más cercano es un vértice se usa el segmento **dibujado primero**, y la
fuente dice explícitamente que no promedia, a propósito. Así que el orden de
los vértices es significativo y hay que conservarlo en el `.ogr`.

Es una entidad independiente: no se interseca con nada, no define regiones y no
entra en el mallador — el mismo estatuto que `WEAK_LAYER`, que ya abrió ese
camino en v0.1.121 y dejó inventariados los enganches de un `BoundaryType`
nuevo.

## Riesgos

- **El eje toca toda superficie no circular**: Block, Path, Simulated
  Annealing, capas débiles y superficies optimizadas, en Ordinary, Bishop y los
  Janbu. Es el riesgo grande de esta versión, no la búsqueda nueva. Se detecta
  corriendo el banco entero antes y después; Spencer y GLE son inmunes por
  construcción, así que la mitad no puede moverse. **Si el banco desmiente el
  cambio, se reporta y no se publica.**
- **La feature es grande**: tres frentes en una versión. Si A resulta más hondo
  de lo que la medición sugiere, se publica **sólo A** en 0.1.126 y el enjambre
  pasa a 0.1.127. El eje es prerrequisito del enjambre, no al revés.
- **El 103 puede no cerrar en valores absolutos.** Hoy tres rutas de OGR dan
  1,30 (rejilla), 1,37 (recocido) y 1,04 (optimizada) para el mismo problema
  cuyo valor publicado es 1,215. Por eso el criterio va en dos piezas:
  estructura y cocientes, además de los absolutos.
- **`BoundaryType` es rígido**: dos `mapping[self]` sin `.get()`, así que un
  miembro nuevo sin entrada no falla donde se escribe — falla en un `KeyError`
  a media búsqueda.
- **Coste**: una corrida del enjambre son unas 2500 evaluaciones, del orden de
  la rejilla fina. En la suite, modelo pequeño y semilla fija; la Tabla 2
  entera (treinta celdas) va al banco, no a la suite.
