# OGR Slip2D v0.1.301

**La infraestructura de deshacer de la ventana (D292): un paso por edición, la
ventana ocupada mientras un paso está abierto, y *Deshacer* y *Rehacer* que
dicen qué deshacen.** Primera versión de la tanda P8e. Las tres siguientes
pasan por ella, familia a familia, los 54 sitios que hoy cambian el modelo
sin dejar paso.

## 0. Lo que se encontró

- **El síntoma** (primera prueba de la interfaz, 0.1.284, H8).
  1. El modelo se definió por el agente, con sus condiciones de contorno.
  2. En la ventana se quitó un material.
  3. *Edición → Deshacer* no devolvió el material: deshizo la última
     condición de contorno del agente, sin decirlo.
- **El tamaño.** La ficha contaba 26 sitios. El inventario de hoy cuenta **54
  métodos** de `MainWindow` que cambian el modelo sin paso de deshacer, por
  familias:

  | Familia | Métodos |
  |---|---|
  | Materiales, propiedades y agua | 13 |
  | Cargas y soportes | 16 |
  | Ajustes, búsqueda, estadística, superficies, foco, anotaciones, DXF | 23 |
  | El borrador del arrastre de vértices | 2 |

  Los 26 que sí dejan paso son todos del lienzo y de la geometría.
- **«Cancelar no cancela» (D306).** Cuatro diálogos escriben en el modelo
  mientras están abiertos:
  - *Ajustes de proyecto* con Aplicar o Restaurar;
  - *Optimize Settings* dentro de *Surface Options*;
  - la rejilla elegida en el lienzo antes de Aceptar;
  - *Anotaciones*, que escribe en vivo y solo tiene Aceptar.

  Se arreglan al envolverlos, porque el paso empieza antes del `exec()`. Eso
  es 0.1.304.
- **Una carrera que ya existía.** El puente del agente es un `QTcpServer` en
  el hilo de la interfaz, y un diálogo modal mantiene vivo el bucle de
  eventos. Por eso una edición del agente puede ejecutarse **mientras** un
  diálogo de la ventana está abierto. Con *Define Materials* abierto, el
  material que añadiera el agente desaparecía al pulsar Aceptar, porque el
  diálogo trabaja sobre copias tomadas al abrir.
- ***Deshacer* y *Rehacer* nunca decían qué deshacían** ni se desactivaban:
  `next_undo_description` y `on_changed` estaban escritos y nadie los usaba.
- **Un paso vacío:** pulsar un vértice sin moverlo dejaba un paso que no
  cambiaba nada.
- **Tres defectos nuevos, fuera de esta tanda.** Salieron en el inventario y
  se abrieron en el banco, cada uno con su reproducción
  (`_auditoria/P8_interfaz/repro_d307.py`–`repro_d309.py`). Se resuelven
  después de P8e:

  | Ficha | Defecto |
  |---|---|
  | D307 | *Move Boundary* arrastrando asigna `v.x` sobre un `Vertex` congelado: `FrozenInstanceError` en el primer movimiento, y el contorno no se mueve |
  | D308 | El manejador de *Add Support* se vuelve a conectar y Esc no lo desconecta: tras usarlo, dos clics de una carga distribuida ponen la carga **y un soporte** |
  | D309 | *Restaurar valores* de *Ajustes de proyecto* borra 9 campos de `search` que ninguna página enseña (rejilla, límites del talud, eje de momentos) y el objetivo del análisis inverso |

- **Observado, sin ficha:** `canvas.set_project()` añade un oyente más al
  proyecto cada vez que se llama (*Import DXF*, *Convert Tool to Boundary*).
  Solo duplica refrescos del lienzo.

## 1. Qué cambia

- **`MainWindow._model_step(description, fn, attrs)`** es el patrón de
  `Workspace.mutate`:
  - `fn` corre dentro de un `SnapshotCommand`, con el `exec()` del diálogo
    incluido, y el paso solo se registra si el modelo cambió;
  - un paso registrado marca el proyecto modificado y refresca el lienzo, los
    menús y la comprobación de resultado desfasado, como `after_edit` para el
    agente;
  - si `fn` devuelve **`STEP_CANCELLED`**, lo escrito se devuelve con
    `SnapshotCommand.rollback` (nuevo). Este solo restaura los atributos que
    cambiaron, y el proyecto recupera el `is_dirty` que tenía;
  - es **reentrante**: un paso dentro de otro forma parte del de fuera. Uno
    interior cancelado devuelve solo lo suyo;
  - si `fn` lanza, `SnapshotCommand` restaura y relanza.
- **`@undo_step("…")`** convierte un método entero en un paso. Qt pasa
  `checked` a los slots de `triggered`; el decorador corta los argumentos a
  los que acepta el método, así que no hace falta reindentar nada.
- **La ventana ocupada.** Con un paso abierto, `WindowHost.busy()` devuelve el
  motivo, y una edición del agente responde `Busy`, como cuando la ventana
  calcula. **`project_history` pregunta lo mismo antes de deshacer o
  rehacer.** Hasta ahora deshacía incluso durante un cálculo de la ventana.
- ***Deshacer* y *Rehacer*:**
  - nombran el paso: «Undo Set material», «Rehacer «Definir material»»;
  - sin pila, quedan en gris y dicen por qué en la barra de estado («No hay
    nada que deshacer.»), como pide D289b;
  - al deshacer, la barra de estado dice qué se deshizo. Si
    `SnapshotCommand._restore_where` conservó algo que otra mano cambió
    después (`kept`), también lo dice;
  - no actúan mientras un paso está abierto, por ejemplo desde la terminal.
- **Los nombres de paso** se guardan en inglés, porque el agente los lee en
  `project_history`, y se traducen al enseñarlos. Llevan su castellano en el
  catálogo todos los literales: los de los comandos tipados, los de la
  ventana y los de las 37 operaciones de edición del API. «Change Slope
  Angle» pasa a «Change slope angle», el nombre del API.
- **El arrastre de vértices** no deja paso si el vértice no se movió.
- **`test_window_english_left_v1293`** exime el nombre de `_model_step` y de
  `undo_step`, como ya eximía el de las clases `*Command`.
- **AGENTS.md:** la suite tarda 50–72 min desde 0.1.278, no «unos 25»; y un
  corte sin traza a los ~40 min se repite antes de culpar al código.

## 2. Tests

`tests/test_window_undo_v1301.py`, 19 casos:
- **El inventario por AST**
  (`test_every_project_write_goes_through_the_stack`). Recorre los métodos de
  `MainWindow` y encuentra los que escriben el modelo:
  - asignaciones bajo `self.project.<atributo del modelo>`, también por
    alias, por `getattr`, por `setattr` y por iteración;
  - mutadores (`append`, `pop`, `add`, `set_*`…), salvo sobre una copia;
  - las funciones que escriben (`set_fem_mesh`, `import_properties`…);
  - los diálogos que escriben por su cuenta.

  Falla si alguno no es un paso ni está en `EXCEPTIONS` con su razón. Un
  método solo llamado desde dentro de un paso cuenta como cubierto; uno
  conectado a una señal, no.
  - `EXCEPTIONS` tiene hoy los 54. `BUDGET = 54` está congelado y solo puede
    bajar.
  - Otro caso falla con una excepción fantasma, y otro con una lista de
    escritores que nombre algo inexistente.
  - Un caso prueba el propio análisis sobre una ventana inventada.
- **La mecánica**, con la ventana real:
  - un cambio deja un paso con su nombre, y deshacer y rehacer devuelven el
    JSON exacto;
  - sin cambio no queda paso;
  - `STEP_CANCELLED` lo devuelve todo, `is_dirty` incluido, y deja el objeto
    de `settings` intacto;
  - un error no deja rastro;
  - un paso dentro de otro forma un solo paso;
  - el decorador aguanta el `checked` de `triggered`;
  - el vértice pulsado sin mover no deja paso.
- ***Deshacer* y *Rehacer*:** en gris con su motivo; nombran el paso en inglés
  y en castellano; esperan al paso abierto.
- **Con el agente**, por el `Workspace` de `AgentBridge` sin servidor:
  - con un paso abierto, `settings_set` y `project_history` responden `Busy`;
  - al cerrarlo, se le vuelve a servir;
  - **la mezcla** (`test_window_and_agent_steps_undo_in_order`): ventana,
    agente y ventana; deshacer tres veces devuelve cada estado en JSON,
    rehacer los tres, y el `project_history` del agente recorre la misma
    pila.
- **Los nombres:** todo nombre literal de paso, y el «Add {tipo}» de cada
  contorno, tienen su castellano.

Con el código de 0.1.300 fallan 14 de los 19, corridos en un `git archive`
de HEAD sin el buscador editable. Pasan los 5 del inventario, como debe ser:
sus 54 excepciones son justo lo que 0.1.300 tenía sin paso.

## 3. Verificación

- **Suite entera:** 5974/5974, código de salida 0, en unos 50 minutos. Fue el
  tercer intento: los dos primeros abortaron, como se cuenta abajo.
- **Los tests vecinos** (21 archivos de deshacer, puente, API, ángulo del
  talud, i18n, menús…): 348/348 antes de lanzar la suite.

### El corte sin traza de 0.1.300 no es del reloj: la suite aborta

Los dos primeros intentos murieron sin totales, con código 127, en el mismo
sitio que las dos corridas cortadas de 0.1.300: el test 3679, al entrar en
`TestGlobalMinimumEngine` de `test_probabilistic_v135.py`. El changelog de
0.1.300 lo leyó como «algo externo que terminó el proceso a los ~40 min».
Lo medido hoy lo refuta:

- **No es el reloj.** El primer intento murió a los 28 minutos, no a los 40,
  y en el mismo test.
- **Es un `abort()`.** En Git Bash, un proceso que termina con 0xC0000409
  (`__fastfail`, que es lo que hace `abort()` del CRT) da 127; con 0xC0000005
  da 139. Con `PYTHONFAULTHANDLER=1`, el segundo intento dejó la traza:
  `Fatal Python error: Aborted`, con el hilo principal esperando en
  `as_completed` de `_parallel_grid_run` (`ogr_slip2d/search.py`). Ningún
  mensaje de Qt antes, aunque se pidió con `QT_FORCE_STDERR_LOGGING=1`.
- **El test es `test_a_shared_seed_is_denounced`** (el runner ordena los
  métodos por nombre). Su rejilla `grid=(6, 6, 8)` son 7 × 7 × 9 = 441
  círculos, por encima del umbral de 400, así que abre un pool de 4 procesos.
  El changelog de 0.1.300 decía 175 círculos: miró la rejilla por defecto del
  archivo, no la de ese test.
- **Al morir deja 4 trabajadores `spawn_main` huérfanos,** creados el mismo
  segundo, y el proceso abortado puede quedarse a medio desmontar
  reteniendo memoria: uno se quedó con 4,1 GB y no lo cierra ni `taskkill`.
- **La memoria crece hasta el final.** Muestreada cada 15 s en el tercer
  intento, el proceso de la suite tiene:

  | Momento | Memoria privada |
  |---|---|
  | Al empezar | 1,2 GB |
  | Al llegar a ese test | 4,3 GB |
  | Al terminar | 7,7 GB |

  La máquina tiene 15,9 GB.
- **Pero la memoria sola no lo explica.** El tercer intento abrió el mismo
  pool con *menos* memoria libre que el segundo (el proceso atascado seguía
  reteniendo 4 GB) y pasó. En ningún momento se agotó la memoria
  comprometible: lo mínimo libre fue 1,7 GB.

**No lo causa este cambio:** el árbol de 0.1.300 ya abortaba ahí. Por
decisión de la propietaria (2026-10-12), P8e espera hasta diagnosticarlo.

## 4. Pendiente

- 0.1.302: materiales, propiedades y agua (13 métodos, con la malla y el
  cálculo del agua como pasos pesados). Calcular el agua no marca el proyecto
  como modificado, ni por la ventana ni por el agente, aunque el campo se
  guarda en el `.ogr`.
- 0.1.303: cargas y soportes (16).
- 0.1.304: el resto (23), D306 y el cierre de D292 y D306 en el banco.
- La CI de 0.1.300 salió en rojo por el segfault al cerrar el intérprete en
  Linux (5954/5955, ningún fallo). Sigue sin diagnosticar.
