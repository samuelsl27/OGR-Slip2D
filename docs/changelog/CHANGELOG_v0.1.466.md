# OGR Slip2D v0.1.466

**La raíz de Sarma junto a un polo (D451).** Con los ajustes por defecto del método (25 cuñas, la bisectriz), el
problema 4 saturado del manual 03 daba F = 0,9004 en vez de 0,4347 (Slide 0,434), como factor admisible y sin ninguna
nota. Lo arreglan dos cambios:
- **Un tramo recto sigue recto.** Las cuñas se cortan sobre los extremos que resolvió el rebanado vertical, en una
  poligonal y en un recorte de capa débil de una poligonal.
- **Una raíz junto a un polo se dice.** Cuando el menor |q| de las caras queda por debajo de 0,2, una nota lo explica
  con sus números, y el factor se mantiene.

Ningún método de dovelas verticales cambia, y el solver no mueve ninguna raíz.

Decisiones de la propietaria (2026-11-16):
- **D451 va en su propia versión,** delante de lo que queda de D357: Interpretar con cuñas pasa a 0.1.467, la
  herramienta de ángulos y el menú contextual del vértice a 0.1.468, y los ángulos optimizados a 0.1.469. La spec 009
  se renumera en este commit.
- **Se arregla la geometría, no solo el aviso.**
- **Tras la revisión, la guarda es una nota y no un rechazo.** Qué raíz debe dar una superficie junto a un polo queda
  para una ficha nueva, D452.
- **El recorte de capa débil de una poligonal se arregla en esta versión.**

## 0. Lo que se encontró

### Al preparar el banco de 0.1.465

Con los ajustes por defecto, el 4 saturado daba 0,434662 con 2 a 10 cuñas y 0,900404 con 25 y 50. Con caras
verticales, o en seco, no pasaba. Con 25 cuñas, `max_force_ratio` valía 6,5e5 y había fuerzas de cara y de base de
4,5e10 kN/m. Evidencia: `_auditoria/P9_D357/medir_polo_4_saturado.py` del banco, con su log.

0.1.461 dejó escrito que una raíz junto a un polo se devuelve, porque es raíz de la ecuación, con `max_force_ratio`
«para que el método avise en 0.1.463». Ni 0.1.463 ni 0.1.464 lo leían: estaba en `details` y en el API, y nada lo
miraba.

### El diagnóstico, al planificar

- **No es una cara casi paralela,** que era la hipótesis de la ficha. La bisectriz de un tramo recto es la normal a la
  base. Con una cara perpendicular a su base, en un mismo material, q = cos φ′·(1 − tan φ̄′ tan φ′) se anula justo en
  F = tan φ = tan 42° = 0,90040, y la raíz espuria valía 0,9004043. Es un polo que el solver cancela de forma exacta
  cuando las dos bases son colineales (`solver._pairs`, qₖ ≡ Ẽₖ₊₁).
- **Por qué no se cancelaba:**
  - el extremo publicado, (128; 67,6737), está 3,3e-5 por encima del terreno, porque la coordenada viene redondeada;
  - el rebanador baja la base de la dovela extrema al terreno cuando el extremo queda por encima dentro de
    `ABOVE_GROUND_REL` (`y_base = y_top`), lo que es correcto para dovelas verticales, y la deja en (128; 67,67367);
  - la última cuña acababa ahí, pero la división uniforme de x = 123 se cortaba sobre la recta original;
  - las dos bases de la escarpa diferían 6,3e-7 rad, por encima de la tolerancia de `_pairs` (1e-9), y quedaba un
    polo verdadero con una raíz al lado, a 2,5e-7 de él.

  El doblez movía también el seco: 1,198338815 con 25 cuñas, frente a 1,198339096 con 2.
- **El censo de las búsquedas.** 41 212 superficies de 8 búsquedas con Sarma sobre el banco del 03, con los ajustes
  por defecto:
  - rejillas circulares del 2, 3, 7, 8 y 9;
  - Block Search del 1, 2 y 3.

  `max_force_ratio` llega como mucho a 1,0, y el menor |q| de las críticas está entre 0,29 y 0,85. La revisión
  mostró que el cociente no basta para afirmar que no haya raíces junto a un polo (abajo).

### Al escribir

- **El campo `{fos}` del mensaje casaba con la sigla retirada «FoS»** (`test_voice_and_terms`), como ya pasó en
  0.1.427. Se llama `{factor}`.
- **La primera guarda rechazaba** la superficie (sin factor, `lem.sarma_near_pole`) por encima de `max_force_ratio`
  = 10. La revisión la tumbó, y ese código ya no existe.

### La revisión adversaria (un agente)

Exportó 3a44f0a con `git archive` para comparar. Encontró:
- **ALTO — el cociente de fuerzas no ve la clase.** El 4 saturado con un vértice dibujado en x = 123, fuera de la
  cuerda:
  - a 0,3–1,5 m (0,44–2,35°), la guarda cortaba;
  - a 2 m (3,2°), daba F = 0,9232, admisible y sin nota, con un cociente de 7,5, justo por encima de un polo en
    0,876;
  - a 8 m (18,8°), daba 1,0534, con un cociente de 1,35;
  - en todos los casos la raíz que continúa la publicada sigue ahí, 0,4295 y 0,4165, y Spencer da 0,21.

  Un círculo con caras verticales, φ = 30° y Ru = 0,7 dio 0,8045, un 0,2 % por encima de un polo, con un cociente de
  0,26 y un menor q de 0,0023, y F se movía con el número de cuñas. **Qué raíz es la del método cuando un polo la
  separa de la siguiente es una pregunta de método, y se abre como D452.**
- **MEDIO — falsos positivos.** El denominador es solo la carga vertical, y X lleva c̄′d:
  - una base recta con c de cara de 6000 kPa daba 2,16835, el Janbu de la misma superficie (lejos de todo polo,
    menor |q| 0,88), y salía sin factor;
  - una carga horizontal de 10 000 kN/m hacía lo mismo.

  Las dos cosas quedan del lado inseguro, y por eso la guarda pasa a ser una nota sobre el menor |q|.
- **MEDIO — el recorte de capa débil de una poligonal no recibía el arreglo.** El 4 saturado con una junta débil
  seguía dando 0,9004, y el docstring afirmaba, en falso, que un recorte acaba en su arco. Arreglado: la base del
  recorte recibe los extremos resueltos.
- **BAJOS, todos arreglados:**
  - un cociente None o NaN pasaba la guarda: la nota lo trata como el caso más cercano;
  - el mensaje hablaba del peso de la masa, y es la carga vertical total;
  - cuatro referencias a versiones que la renumeración dejó atrás (`interpret_window.py`, `main_window.py`,
    `postprocess.py`, la spec);
  - el docstring de `SarmaSettings` atribuía la identidad al agua;
  - «el mismo objeto» no está garantizado por el último dígito de `base_y_at`, y el docstring lo dice ahora.
- **Comprobado sano:**
  - **A/B frente a 0.1.465 en 128 casos.** Janbu y Spencer salen idénticos bit a bit. Sarma solo cambia donde el
    rebanador baja un extremo al terreno, y no se mueven ni los círculos, ni el 5, ni los extremos por debajo del
    terreno.
  - **La copia:** la grieta en cabeza y en pie, también reflejada, `id`, `block_group` y los datos por vértice.
  - **Las puertas:** Ky, la estadística, Interpretar y el API.

## 1. El cambio

- **`ogr_slip2d/sarma/wedges.py`:** `_with_resolved_ends(surface, vertical)`.
  - **Una poligonal** (`SlipSurface`) cuyo extremo resuelto difiere de su vértice, dentro de la tolerancia del propio
    rebanador, recibe una copia con ese vértice en el punto resuelto y su propia lista de grietas.
  - **Un recorte de capa débil cuya base es una poligonal** recibe una copia con esa base.
  - `build_wedges` corta las cuñas sobre la copia. La superficie del usuario no se toca, y los datos por vértice se
    leen de ella.
  - Un extremo que la capa débil levanta más allá de esa tolerancia no se mueve.
  - Círculos, compuestas y recortes de un círculo no cambian.
- **`ogr_slip2d/sarma/solver.py`:** `SarmaSolution.min_abs_q`, el menor |qᵢ| de las q que dividen, solo como
  diagnóstico. Ninguna raíz se mueve.
- **`ogr_slip2d/methods/sarma.py`:** `NEAR_POLE_MIN_Q = 0,2`, una constante. Es el límite de m-alpha (Whitman y Bailey
  1967), tomado por analogía y declarado así. `details["sarma_min_abs_q"]`.
- **`ogr_slip2d/analysis_runner.sarma_notes`:** la nota `method.sarma_near_pole`, con el factor, el menor |q|, el
  límite y el cociente de fuerzas, cuando el menor |q| queda por debajo del límite o no se pudo calcular. Tiene su
  español y su muestra.
- **`ogr_api/results.py`:** `sarma_min_abs_q` en el resumen.
- **Textos:**
  - el docstring del solver;
  - el de `SarmaSettings.num_slices`;
  - la spec 009, renumerada;
  - las cuatro referencias de versión.

## 2. El test

`tests/test_sarma_pole_v1466.py`, 8 casos. Comprueba:
- **el 4 con los ajustes por defecto y con 50 cuñas:** seco y saturado a 1e-6 de la herramienta del banco y a ±1 % de
  lo publicado, iguales a 2 cuñas a 1e-9; también reflejado, donde el extremo bajado es el izquierdo;
- **la escarpa es una recta:** sus bases tienen la misma α a 1e-12 y el solver las empareja;
- **la nota:**
  - un vértice doblado 2,6e-6 rad se dice, con el factor junto a tan 42°;
  - los dos casos de la revisión: el de 2 m fuera de la cuerda se dice, y el de 6000 kPa de cohesión de cara (igual a
    Janbu) no;
  - exactamente colineal, 0,434662 sin nota;
  - el límite mueve la nota (regla 7);
  - el API la da;
- **un recorte de capa débil de una poligonal:** con 25 y 50 cuñas da lo de 2, sin nota;
- **lo que no se toca:** un círculo, una compuesta, un recorte de un círculo, una poligonal con los extremos en el
  terreno y un extremo levantado fuera de la tolerancia salen como estaban, y la superficie del usuario conserva su
  extremo.

En los publicados, la nota solo sale en el 5 con γw = 9,81 (menor |q| 0,023), que es la raíz no física de D123, con
bases en tracción. No sale en el 4 seco (0,35 y 0,53), en el 4 saturado (0,435) ni en el 5 con γw = 1 (0,256).

Mutantes: `_auditoria/P9_D451/mutants_v1466.py` del banco, con su log. Son 11 y vive uno, equivalente: copiar «lo que
tenga `polyline`» en vez de «una `SlipSurface`» da lo mismo, porque ninguna otra clase de superficie tiene `polyline`.

## 3. La suite

- `test_core_messages_v1333`: ni gana ni pierde muestras, porque el código `lem.sarma_near_pole` nació y se retiró en
  esta versión.
- `test_method_notes_v1348`: la muestra de `method.sarma_near_pole`.

## 4. Verificación

- **La suite entera, `--jobs 4`, una vez tras la revisión:** 7936 casos; pasan 7935 y uno queda saltado, sin fugas ni
  tramos muertos. La última serie en verde es de hace 44 commits.
- **El test nuevo:** 8 de 8. **Los de Sarma y los de mensajes juntos:** 205 de 205. **Mutantes:** 11; vive uno,
  equivalente.
- **Los README:** 7927 → 7935 tests.

## 5. Lo que queda

- **D452 (ficha nueva, por decisión de la propietaria): qué raíz da el método cuando un polo la separa de la
  siguiente.** Los casos medidos por la revisión (el 4 con un vértice de 2 a 8 m fuera de la cuerda, y el círculo con
  caras verticales) van a la ficha. Las mediciones que pide: el menor |q|, la continuidad de la rama y la tracción.
- **El banco, tras el commit:**
  - `d451()` (CUBIERTO POR TEST, discriminado con 0.1.465);
  - retirar D451 y abrir D452;
  - `medir_polo` con 0.1.466;
  - las notas del 4;
  - la re-corrida del 4 y del 5.
- 0.1.467: Interpretar con cuñas.
