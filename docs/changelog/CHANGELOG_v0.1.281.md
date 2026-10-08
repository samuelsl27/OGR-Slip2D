# OGR Slip2D v0.1.281

**Por la puerta del proyecto, el campo en t = 0 de un transitorio ES el
análisis permanente del mismo modelo y condiciones (D277).**
- `solve_project_groundwater` resuelve el permanente con ω = 0,4, 200 pasadas y
  tolerancia 1e-5.
- El transitorio que construye corre con ω = 0,5 y la tolerancia del
  transitorio, y su permanente inicial heredaba esos ajustes.
- Dónde se para el Picard depende de ω (D267). Los dos campos «iguales» se
  diferenciaban al nivel de la tolerancia.

## 0. Lo que se encontró

- **El banco 05 no pasa por la puerta.**
  - `ejecutar_filtracion.py` construye su `TransientSeepageSolver` directamente,
    con los ajustes de cada script.
  - Un arreglo en la puerta no mueve ninguna fila del 05.
  - Un arreglo dentro de `solve_transient` habría movido el 017 y el 018.
  - Decisión de la propietaria: ajustes desde la puerta.
- **Lo que sí pasa por la puerta:** la interfaz, el API (`groundwater_run`) y el
  transitorio del 02-102, que es una medición y no una validación.
- **La diferencia, medida en la presa rectangular de Gardner** de
  `test_unsaturated_v127` hecha proyecto: max|ΔH| entre t = 0 y el permanente,
  1,2e-6 m con el comportamiento viejo (0,12 tolerancias) y 0 con el nuevo.

## 1. Qué cambia

- **`TransientSeepageSolver`** acepta `steady_relaxation`, `steady_tolerance` y
  `steady_max_iterations`.
  - Los usa su permanente inicial (`_initial_steady`), cuando lo calcula él (sin
    `initial_head`).
  - Con `None`, los suyos de siempre: un script que no los pasa obtiene lo que
    obtenía.
- **La puerta** (`transient_stability`).
  - `STEADY_RELAXATION`, `STEADY_MAX_ITERATIONS` y `STEADY_TOLERANCE` son un
    solo sitio para el permanente y para el arranque del transitorio.
  - Interruptor `INITIAL_STEADY_FROM_DOOR`, con alta en `INTERRUPTORES` como
    (0, 1, 281).

## 2. Tests

`tests/test_initial_steady_v1281.py`, 4 casos:
- por la puerta, el t = 0 es el permanente al bit;
- con el interruptor apagado difiere (regla 7);
- la puerta tiene un solo juego de ajustes;
- un solver sin `steady_*` conserva los suyos.

`test_transient_initial_state_v1270` (el t = 0 frente a `solve_unsaturated` en el
mismo solver) sigue igual.

## 3. Verificación

- **A/B árbol contra árbol** (`_auditoria/P6_0281/ab_arbol.py`, 0.1.280 frente
  a 0.1.281): 75 filas, 2 distintas, las dos explicadas.
  - **02-102 transitorio, 4,2e-7 m.** Es esta versión: pasa por la puerta.
  - **05-020 x1, 2,9e-8 m.** Es el `max_picard=100` del script del banco
    (D278), puesto después del volcado de 0.1.280.
  - Las otras 73 filas quedan iguales al bit.
- **Suite entera:** 5855 / 5855, con código de salida del proceso 0.
- **Lo que separa esta versión** es el interruptor en el mismo proceso
  (`test_the_switch_moves_it`): apagado, el t = 0 difiere del permanente en
  1,2e-6 m; encendido, en 0.
  - El test en el árbol de 0.1.277 también falla entero, pero en parte porque
    ese árbol no tiene `wc_alpha` (0.1.278), así que no aísla D277.

## 4. Lo que no se ha probado

- La serie de factores del 02-102 re-corrida con su script del banco.
