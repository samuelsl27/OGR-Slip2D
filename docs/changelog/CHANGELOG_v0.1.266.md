# OGR Slip2D v0.1.266

**El permanente no saturado llega a su punto fijo cuando el bucle de Picard
no puede (D124).** Con una curva de permeabilidad muy vertical, el Picard de
una malla fina cae en un ciclo que ninguna relajación rompe. Desde esta
versión, si el bucle termina sin converger, un rescate busca **el mismo**
punto fijo:

- primero, con aceleración de Anderson;
- si no basta, con continuación en la pendiente de las curvas resuelta con
  Newton.

El rescate solo entra después de un fallo, así que todo lo que convergía
hace exactamente la misma aritmética que antes.

## 0. Lo que se encontró

### La medida que decidió el remedio

**La presa 2 del problema 9 del manual de agua** (Bowles 1984). Su dren de
pie tiene una curva que baja seis décadas entre 8 y 12 kPa, unos 0,4 m de
succión.

- **Las mallas.** La del manual (946 T3) converge en 68 pasadas. La ×4
  (3883 T3, no 3866: esa es la de la presa 1) no converge.
- **Lo que hace el bucle en la ×4.** Es un **ciclo límite de periodo 4**:
  - el coseno entre incrementos consecutivos vale −1,000;
  - el cambio sin relajar es de 2,6–3,0 m;
  - el conjunto activo de la cara de rezume está quieto, en 1 nodo;
  - no hay nodos congelados.
- **Dónde está el ciclo.** Lo forman 5–7 elementos del dren junto a su cara
  interior (x 108–113 m, y 4,3–6,7 m), que saltan una década de kr o más en
  cada pasada. El cambio sin relajar no baja con ω, así que relajar no es la
  cura.
- **Los dos experimentos de aislamiento de la ficha, rehechos** (el scratch
  de 0.1.159 se había perdido):
  - la misma caída repartida entre 8 y 60 kPa converge en 67 pasadas (Q
    −1,42 %);
  - el dren con la curva de la presa converge en 54.
- **Las otras mallas.** También fallan las de 1916, 2408 y 2897 T3; solo
  converge la del manual.

**Una columna 1-D con solución cerrada** (Gardner 1958, infiltración
estacionaria):

- **El caso.** La curva de usuario de seis décadas en 0,4 m es exactamente la
  exponencial de Gardner; I/Ks = 10⁻³.
- **El Picard falla con toda ω de 0,2 a 0,6.** Los cambios llegan a decenas
  de metros. Arrancado en la solución exacta se queda en ella, pero desde la
  saturada no la alcanza.

**Los candidatos, medidos en los dos casos:**

| Método | Columna | Presa ×4 |
|---|---|---|
| Anderson (Walker y Ni 2011) | no converge | converge, pero según el arranque y la profundidad: 36–166 evaluaciones |
| Newton directo | no converge | no converge (se estanca en las esquinas de la curva por tramos) |
| ln kr amortiguado por elemento | — | no converge en 300 |
| Continuación + Anderson | se atasca hacia t ≈ 0,5 | — |
| **Continuación kr^t + Newton** | **converge, error 1,7·10⁻¹¹** | converge (194 s vectorizado) |

Todos los que convergen dan **el mismo punto fijo** en la presa: 3,76148·10⁻⁶
m³/(min·m), un 1,69 % por debajo de la malla gruesa y un 1,0 % por debajo de
la red de flujo de Bowles. Por eso el rescate prueba primero Anderson, que es
barato donde funciona, y después la continuación con Newton, que es robusta.
La decisión fue de la propietaria, con esta tabla delante.

### Anomalías encontradas al leer (regla 6)

Se informan aquí; las que no corrige esta versión se abren como fichas del
banco.

- **El comentario de la reacción tenía el signo al revés.** `solve()` decía
  que una reacción negativa es agua entrando. Es al revés: positivo es
  entrada, como ya leía la conmutación. La base de la columna drena con
  −I·ancho. Corregido aquí.
- **`docs/PLAN_AGUA_SUBTERRANEA.md` decía «subrelajación adaptativa» desde
  v0.1.27.** Nunca lo fue: la ω es constante. Corregido aquí.
- **La historia de Δ se calcula y se descarta**, mientras *Iteration History…*
  y *Convergence Plot…* de la ventana de interpretación la buscan en
  `notes["history"]`. Ficha nueva.
- **El aviso de no convergencia pide «a smaller relaxation factor or a finer
  mesh».** La ω está fija en el código (0,4 en `solve_project_groundwater`) y
  refinar es justo lo que provoca el ciclo. El aviso nuevo, el que sale cuando
  también falla el rescate, no da ese consejo. La falta de control de ω es
  ficha nueva.
- **Δ se mide después de relajar:** Δ = ω·max|H_nuevo − H|, así que la
  tolerancia real es tol/ω. El rescate juzga el cambio sin relajar. El bucle
  no se toca: es ficha nueva.
- **`solve_transient` usa el permanente inicial sin mirar si convergió.** En
  el banco (17, 18 y 20) converge siempre, en 22, 35 y 1 pasadas. Ficha nueva.
- **La conmutación del transitorio usa otro umbral** (`q_node > 1e-12`) que la
  del permanente (`q_tol`). Ficha nueva.
- **El mallador deja un triángulo degenerado sobre la línea de contacto del
  dren** en la malla de 1432 T3 de esa presa: área 2,2·10⁻¹⁵ y ángulo mínimo
  0°, con los tres vértices alineados sobre la línea.
  - `shape_gradients` solo descarta det < 10⁻¹⁵, así que entra con |K0| de
    unos 2·10⁷ y el sistema queda casi singular.
  - Ni el Picard ni el rescate convergen en esa malla. El rescate lo dice;
    no es un fallo suyo.
  - Las mallas de 946 y 3883 T3 están sanas (ángulos mínimos de 21° y 20,5°).
  - Ficha nueva.

## 1. Lo que cambia

- **`UnsaturatedSeepageSolver.solve_unsaturated`** llama a `_rescue` cuando el
  bucle termina con `converged = False`.
  - Detrás del interruptor de módulo `PICARD_RESCUE` (apagado, el
    comportamiento de 0.1.265).
  - No entra si el bucle «convergió» y es la comprobación final la que
    encuentra nodos sin asentar: es el presupuesto del usuario, y
    `test_a_starved_budget_is_reported_and_not_called_converged` lo fija.
- **`_rescue`** prueba dos caminos al punto fijo del bucle:
  - **Anderson** del mapa de Picard sin relajar (Anderson 1965; el tipo II de
    Walker y Ni 2011, como lo aplican Lott, Walker, Woodward y Yang 2012 al
    flujo variablemente saturado). Arranca en el centro del último paso del
    bucle, con profundidad 5 y luego 20, y 150 evaluaciones cada una.
  - **Continuación + Newton** (`_continuation_newton`): kr^t con t de 0 a 1 y
    paso adaptativo (empieza en 0,25, se dobla al acertar y se parte al
    fallar, con un mínimo de 10⁻³). Cada paso se resuelve con Newton y
    búsqueda lineal de Armijo, con jacobiano no simétrico y la derivada de kr
    por diferencias centradas (`_NewtonSystem`). Es la continuación natural de
    Allgower y Georg (1990); Paniconi y Putti (1994) comparan Newton y Picard
    en esta ecuación.
  - **Comunes a los dos:**
    - la cara de rezume se conmuta con **la misma regla** del bucle, movida a
      `_switch_seepage_face` sin cambiar una comparación;
    - cada camino estrena su presupuesto de conmutaciones;
    - converge con max|G(H) − H| < tol **sin relajar**.
- **Notas:** `rescue` (qué camino actuó, o «failed»), `rescue_iterations` y
  `rescue_residual`, solo si el rescate se ejecutó. `iterations` es el total.
- **El aviso** cuando también falla el rescate dice qué se intentó y señala
  las curvas, no la ω ni la malla.
- **El comentario de la reacción** y **el plan de agua**, corregidos.

## 2. Tests

**`tests/test_picard_steep_curve_v1266.py`** (el nombre casa con el patrón
de `d124()`).

- **`TestGardnerColumn`.** La columna de 10 m con Δz = 0,25 m:
  - **sin rescate no converge** (con ω de 0,3 y 0,5);
  - con rescate (continuación + Newton) da la carga de presión de Gardner,
    ln(I/Ks)/a = −0,200 m, **exacta** en la zona de gradiente unitario
    (z ≥ 5 m): error por debajo de 10⁻⁶;
  - la base drena −I·ancho.
- **`TestTheRescueKeepsTheFixedPoint`.** La presa rectangular de Gardner de
  `test_unsaturated_v127`:
  - el Picard convergido y el rescate forzado (una sola pasada) dan las
    mismas cargas a 10⁻⁴ y la misma cara de rezume;
  - lo hacen por los dos caminos (Anderson, y continuación + Newton con
    Anderson desactivado);
  - con el interruptor apagado, el informe de antes.
- **`TestBowlesDam2`.** La presa 2 reconstruida dentro del test, con la
  geometría y las curvas de la fig. 9.6 leídas en m/min (D130):
  - la malla del manual converge sin rescate;
  - la ×4 converge con rescate y sin nodos sin asentar;
  - su caudal queda a ±3 % del de la del manual, que es el criterio de la
    ficha;
  - y dentro de la banda publicada [3,8·10⁻⁶ Bowles; 4,23·10⁻⁶ elementos
    finitos] ±5 %.
- **Test existente cambiado:** `test_unsaturated_v127::test_non_convergence_is_reported`
  corre con el interruptor apagado. Con el rescate, dos pasadas ya no dejan
  la corrida sin converger, y su condicional pasaba sin comprobar nada.
- **Discriminación.** Copiado a un worktree de 0.1.265 y corrido desde dentro
  de ese árbol, **fallan 9 de los 10 casos**, y los sustantivos por la razón
  buena:
  - la presa ×4 no converge en 30 pasadas (Δ 0,85 m) y su caudal sale `nan`;
  - la columna termina con Δ = 172 m.

  Pasa el que debe pasar: la malla del manual converge sin rescate.

## 3. Banco

- **`_tools/ejecutar_filtracion.py`** guarda `convergio`, `iteraciones` y
  `notas` también de la malla fina. Antes solo su geometría: una fina que no
  convergía salía como «fino —» sin decir por qué.
- **El problema 9** baja `max_iterations` de 1200 a 300. La malla del manual
  converge en 68 pasadas y no se mueve; en la fina, el rescate empieza antes.
- **`d124()`** exige además `malla_fina.convergio = True` y cero nodos sin
  asentar.
- **`INTERRUPTORES`** suma `ogr_fem2d.solvers.seepage.PICARD_RESCUE`
  (0, 1, 266), el primero de `ogr_fem2d`.

### El A/B: interruptor apagado contra encendido, en el mismo proceso

En `_auditoria/P6_0266/` del banco, con los scripts de la medida.

- **No se comparó contra los `resultados.json` guardados.** Son de 0.1.202 y
  el entorno ha cambiado: Python 3.14 y SciPy 1.18.
- **Manual 05.** 60 filas: todas las variantes, malla del manual y ×4, con la
  salida del solver (cargas, convergencia, iteraciones y notas).
  - **58 son idénticas al bit.**
  - Las 2 distintas son la malla ×4 de `nucleo` y de `nucleo_k_min` del 9: no
    convergían y ahora convergen con Anderson de profundidad 5.
- **Manual 02.**
  - El 10 y el 102: idénticos.
  - El 38: **las cargas son idénticas al bit** en sus 12 combinaciones de
    altura y modelo; cambian las notas y el recuento de iteraciones.
- **El 38 ya no convergía, y el rescate tampoco lo resuelve.** Con Gardner,
  Gardner seco y van Genuchten, el Picard agota las 250 pasadas: 2 nodos de la
  cara sin asentar y 21 congelados. Su malla tiene varios triángulos de área
  cero (D270).
  - Los `resultados.json` del 38 lo registraban
    (`"filtracion": {"convergio": false}`) desde al menos 0.1.173, sin ficha.
  - Queda escrito en D270.

### El banco re-corrido

- **Solo el 9**, porque el A/B prueba que el motor no mueve ningún otro.
  Re-correr los demás habría mezclado en sus JSON la deriva del entorno.
- **La malla del manual da los mismos números en todas las cifras** en las
  tres variantes.
- **Las finas de la presa 2 tienen caudal:** `nucleo_k_min` 3,761·10⁻⁶ frente
  a 3,826·10⁻⁶, −1,69 %, convergida por Anderson. Antes salían «fino —».
- **La comparativa de la raíz** solo cambia en esa columna. Ningún estado
  cambia: la fila sigue en DISCREPANCIA frente a la malla densa de la fuente
  (−9,55 %), que es D130.
- **`d124()`: CUBIERTO POR TEST.** D124 retirada, `PAQUETES` podado y la
  cadena de P6 tachada.
- **Fichas nuevas D265–D271**, en P6 y sin prompt largo. Las abrió la lectura
  del plan y la medida (sección 0); lo de la misma clase entró en ellas sin
  número (el 38 en D270).
- Auditorías de invariantes de la raíz y del 02: 0 ERROR.
- `verificar_cierres.py --seco` del 02 entero: 238 claves, 0 bajadas.

## 4. Verificación

- **Suite entera, sin argumentos: 5714/5714.** Son los 5704 de 0.1.265 más
  los 10 casos nuevos.
- **Lo que queda sin probar:** el rescate con un modelo de usuario en la
  aplicación real (Compute Groundwater). En el permanente lo llama la misma
  `solve_project_groundwater` que mide el A/B del 102, sin camino propio de la
  interfaz.
