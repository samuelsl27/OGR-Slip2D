# Plan — filtración transitoria acoplada (D30)

## Lo que se midió antes de tocar nada (regla 6)

Tres hallazgos, los tres con su medición, y **dos de ellos son defectos**.

### 1 · La geometría está publicada, y los rótulos están redondeados

Los seis círculos publicados tienen todos el extremo izquierdo en **y = 28,600**
y el derecho en **y = 7,300**, con x distinta cada uno. Sobre una cara inclinada
una cota fija obliga a una x fija; que varíe la x y no la y sólo cabe si esos
extremos están sobre **tramos horizontales**. Coronamiento 28,6, explanada 7,3,
donde los rótulos dicen 29 y 7. Peor residuo de los dieciséis extremos:
**1,4 mm**, que es el redondeo de los tres decimales publicados.

Y hay un rótulo que la propia tabla desmiente: el pie dice 158, pero un extremo
publicado en x = 157,908 con y = 7,300 ya tiene que estar sobre la explanada, así
que el pie está **en 157,908 o antes**.

### 2 · El embalse prescrito se extrapolaba a todo el modelo

`_fea_level_at` devolvía el valor del extremo fuera del rango de los nodos
mojados. En esta presa los nodos con carga prescrita acaban en x = 87, así que
la función respondía 24,41 **hasta x = 191**: diecisiete metros de agua sobre el
talud de aguas abajo. Spencer sobre el círculo publicado: **5,8262 con la regla
vieja, 1,5759 sin ponding**. El camino de las superficies **dibujadas** ya
respondía bien (`interp_y_on_polyline` devuelve `None` fuera de su rango): las
dos rutas contestaban distinto a la misma pregunta y la del FEM era la mala.

### 3 · El conmutador de la cara de filtración fabricaba convergencia

`max_node_switches = 3` congela un nodo tras tres cambios. Un nodo congelado ya
no puede mover el conjunto activo, y «el conjunto activo dejó de cambiar» era el
criterio de convergencia. Medido: **47 de 77 nodos** congelados, freática 4,5 m
alta, factor **1,5818 (−9,35 %)** y `converged = True`. Con presupuesto 10, 40 o
200 el resultado es **idéntico** (1,7174), así que el tope no compraba nada.

**Y su consecuencia más útil**: con el conmutador asentado, prescribir una cola
de aguas abajo a 7,3 y dejar cara de filtración dan **1,7173 y 1,7174**. Son la
misma condición física, y antes se separaban un 8 %. La cola de aguas abajo, que
parecía la causa, era el síntoma.

### 4 · Dos defectos más, y uno lo creé yo al arreglar el tercero

**Una etapa de duración cero no anotaba `calculate_sf`.** La rama que la atiende
construye sus notas a mano y esa clave no estaba, mientras que el consumidor la
busca ahí. Como la única etapa que **siempre** tiene duración cero es el instante
inicial, se podía marcar *Calculate SF* en t = 0 y no salir factor ninguno.

**Y un modal en un camino que este arreglo hace alcanzable.** Decir la verdad
sobre la convergencia convierte el aviso de «el campo no se asentó» de casi
imposible a fácil, y ese aviso era un `QMessageBox.information` **modal**.
Medido en carne propia: una corrida automática se quedó **1 h 51 min** parada,
con el proceso a 125 s de CPU, esperando un botón que nadie iba a pulsar. Pasa a
la barra de estado, con test que comprueba que la llamada vuelve.

### 5 · Un camino que resultó estar bien

La auditoría de los consumidores de `ponded_water` señalaba que el lienzo no
dibuja el embalse prescrito. **Es falso**: `canvas_view._draw_ponded_water` lo
dibuja desde v0.1.65, y además hereda el arreglo, porque toma el nivel de
`_fea_level_at`. Se anota como camino equivocado.

## Coste, medido como manda el contrato

A/B en el mismo proceso, espalda con espalda, con la versión nueva de control a
los dos lados. Sobre el **permanente** los controles se separaron un 30 % entre
sí —más que el efecto—, así que no resuelve y manda contar el trabajo: **29 → 33
iteraciones de Picard**. Sobre el **transitorio**, donde el conmutador actúa
dentro de cada paso de tiempo y podía multiplicar, sí resuelve: 108 s con el
presupuesto nuevo, 109 s con el viejo, 108 s el control. No hay efecto.

## Diseño

| Pieza | Dónde |
|---|---|
| Perímetro mojado y ciclo del contorno | `ogr_fem2d/solvers/bc_targets.py` **nuevo** |
| El embalse deja de extrapolarse; cuerpos de agua por tramos contiguos | `ogr_core/hydraulic/ponded_water.py` |
| Presupuesto de conmutación y comprobación del estado FINAL | `ogr_fem2d/solvers/seepage.py` |
| Conductor sin Qt; cada etapa con su campo **y** sus contornos | `ogr_slip2d/transient_stability.py` **nuevo** |
| `run_analysis` rechaza un proyecto sin configurar | `ogr_slip2d/analysis_runner.py` |
| Tope de succión, leído una vez por corrida | `ogr_slip2d/slicer.py`, `ogr_core/project/settings.py` |
| Destino «Embalse a la cota», tope en Project Settings | `ogr_gui/dialogs/` |

## Decisiones

- **El perímetro mojado es un número y un lado, no una selección.** Lo que cambia
  entre las etapas de un desembalse es una cota; expresarlo como un conjunto de
  nodos obligaría a rehacer la selección en cada etapa.
- **El paseo nunca entra en la base del modelo.** Sin esa regla, partir de la
  esquina inferior recorre la solera, sube por el extremo opuesto y baja por el
  talud de aguas abajo: 208 de 226 nodos, medido.
- **El tope se aplica ANTES de la envolvente bilineal**, porque lo que acota es
  la presión y no la cohesión que de ella se deriva.
- **`run_analysis` levanta.** La guarda existía desde v0.1.77 y sólo la llamaban
  el CLI y la interfaz, es decir, todos menos el que más la necesitaba.
- **El presupuesto de conmutación se sube y, sobre todo, se comprueba el estado
  final.** Preguntarle a la respuesta en vez de al bucle es lo que impide que un
  tope vuelva a esconderse.
