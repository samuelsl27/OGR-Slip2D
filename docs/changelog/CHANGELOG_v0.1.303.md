# OGR Slip2D v0.1.303

**Materiales, propiedades y agua subterránea son pasos de deshacer (D292), y
calcular el agua marca el proyecto como modificado.** Segunda versión de la
tanda P8e. La primera fue 0.1.301; 0.1.302 fue D310, el aborto de la suite.

## 0. Lo que se encontró

- **El caso de la ficha.** En la primera prueba de la interfaz se quitó un
  material en *Define Materials* y se cambió un Ks en el diálogo hidráulico.
  Ni lo uno ni lo otro dejaba paso, así que Ctrl+Z deshizo un paso anterior
  del agente.
- **Calcular el agua no marcaba el proyecto como modificado.** Ni la ventana
  ni el agente. El campo y el transitorio se guardan en el `.ogr`
  (`Project.to_dict`), y la pregunta al cerrar de D283 lee `is_dirty`. Con un
  proyecto recién guardado, calcular el agua y cerrar no preguntaba nada y
  perdía el campo.
  - Por la ventana: `_compute_groundwater` no tocaba `is_dirty` ni
    notificaba.
  - Por el agente: `_finish_groundwater` escribe con `Workspace.mutate`, que
    llama a `WindowHost.after_edit`, y ese no lo marcaba.
- **Coste del paso pesado** (los atributos del modelo más la malla, el campo
  y el transitorio, como en el API). Medido con el talud de ejemplo y una
  malla de 7939 elementos y 4101 nodos, a través de los métodos reales de
  la ventana:
  - captura del estado antes y después: 0,19 s;
  - comparación `changed`: 0,03 s;
  - memoria retenida por el paso: 7,8 MB (`tracemalloc`).

  Lejos de los ~50 MB que se fijaron como umbral para plantearlo antes de
  seguir. El trabajo añadido es la captura más la comparación. La
  diferencia del reloj entre calcular con paso y sin él no vale como
  medida: la segunda corrida reutiliza el solver ya montado.

## 1. Qué cambia

Los 13 métodos de la familia pasan por `_model_step` con `@undo_step`, con el
nombre del API cuando la operación es la misma:

| Acción | Paso |
|---|---|
| *Define Materials* | Define materials |
| *Import Properties* | Import properties |
| *Assign Water Surface* (también al terminar de dibujar un nivel freático) | Assign water surface |
| Clic derecho → *Assign Material* | Assign material |
| *Define Tension Crack* | Set tension crack |
| *Define Hydraulic Properties* | Hydraulic properties |
| *Water Pressure Grid* | Water pressure grid |
| *Set Boundary Conditions* | Set boundary conditions |
| *Transient Groundwater* | Transient groundwater |
| *Generate FE Mesh* / *Reset FE Mesh* | Generate FE mesh / Reset FE mesh, con la malla y los campos |
| *Compute Groundwater* (permanente y transitorio) | Compute groundwater, con la malla y los campos |

- La malla y el cálculo del agua son pasos con los atributos pesados
  (decisión de la propietaria, 2026-10-12). Deshacer un cálculo devuelve el
  campo que había antes.
- Un paso registrado marca el proyecto como modificado (0.1.301). Por la
  puerta del agente, `WindowHost.after_edit` hace lo mismo, porque solo se
  llama cuando el paso cambió algo.
- Al dibujar un nivel freático, la ventana ofrece asignarlo. Son dos pasos:
  «Add Water Table» y «Assign water surface».
- **AGENTS.md:** el párrafo del corte con código 127 ya no dice «causa en
  estudio». Dice que lo resolvió 0.1.302 y cómo ver la pila nativa si
  vuelve a pasar.
- **El inventario** de `test_window_undo_v1301`: las 13 excepciones salen, y
  `BUDGET` baja de 54 a 41.

## 2. Tests

`tests/test_undo_materials_water_v1303.py`. Por cada sitio, el método de la
ventana con su diálogo sustituido (`_swap`, como en `test_f2_rules_v1196`):
- aceptar deja un paso con su nombre;
- deshacer devuelve el JSON exacto, y rehacer el aceptado;
- cancelar no deja paso y el proyecto sigue sin cambios por guardar.

Además:
- calcular el agua es un paso, marca el proyecto, y deshacerlo quita el campo;
- el campo escrito por la puerta del agente marca el proyecto de la ventana;
- la malla, un paso del agente y el cálculo se deshacen y rehacen en orden.

Con el código de 0.1.302 fallan los 13 casos: ningún sitio dejaba paso
(`([], [])`), y por la puerta del agente el proyecto no quedaba marcado.
Se corrió sobre un `git archive` de HEAD sin el buscador editable.

## 3. Verificación

- **Suite entera:** 5993/5993, código de salida 0, a la primera, y sin
  aborto en el test de 0.1.302.
- **Los tests vecinos** (deshacer, guardián, puente, operaciones del agua,
  versión, i18n, menús, motivos de desactivado): 169/169 antes de lanzarla.

## 4. Pendiente

- 0.1.304: cargas y soportes. 0.1.305: el resto, D306 y el cierre en el
  banco.
