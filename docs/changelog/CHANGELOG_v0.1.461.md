# OGR Slip2D v0.1.461

**El solver de Sarma con dovelas no verticales, puro y sin registrar (D357, primera de las siete versiones del
método).** `ogr_slip2d/sarma/solver.py` da el factor de seguridad de un conjunto de cuñas entre caras inclinadas:
- es la raíz MAYOR de Kc(F) = kh, la aceleración crítica de Sarma (1973);
- la recurrencia de Kc es la derivación propia del equilibrio de fuerzas de una cuña, escrita en el `plan.md` de la
  spec 009 (Sarma 1979 no se ha consultado);
- F reduce c y tan φ en las bases **y** en las caras, el convenio que fijan los publicados del manual 03.

`ogr_slip2d/sarma/vertical.py` lee las dovelas verticales del rebanador como cuñas de caras verticales. Es la entrada
δ = 0 que usará `compute_fos` en 0.1.463, y aquí la usa la identidad con Janbu.

**Nada está registrado.** El registro sigue con nueve métodos, y ninguna corrida, búsqueda ni ventana llega al solver
hasta 0.1.463. **Ningún número cambia.** Las únicas cadenas nuevas son tres códigos de rechazo del motor, con su
español; no hay ajuste ni acción nuevos.

Por decisión de la propietaria (2026-11-15), Sarma va ya, aunque la fila de P10 no esté tachada: D429–D446 se quedan
en P10, sin versión, para después de Sarma (0.1.461–0.1.467).

## 0. Lo que se encontró

- **El REPRODÚCELO de P-D357,** con 0.1.460 (f3121ce), da lo de 0.1.435:
  - el `control` de `cunas_sarma.py`, 0,9249309231188405;
  - el 4: 1,198339, y saturado [0,146694; 0,434662]; el 5: 1,089053;
  - las filas del 4 en NO COMPARABLE y la del 5 en «DISCREPANCIA — de método»;
  - nueve métodos.
- **La derivación de `plan.md`, rehecha a mano:**
  - la proyección sobre v anula N′;
  - una cuña da (cL + (W cos α − U) tan φ)/(W sen α);
  - con δ = 0 y caras sin resistencia, la ecuación es exactamente la de Janbu simplificado, con U = u·l.
- **La recurrencia contra la herramienta del banco,** que resuelve las 2n ecuaciones de las cuñas de otra forma,
  alimentada con las mismas cuñas:

  | caso | solver | `cunas_sarma.py` |
  |---|---|---|
  | 4 seco | 1,1983391299829476 | 1,1983391299829478 |
  | 4 saturado | 0,43466200850498166 | 0,4346620085049817 |
  | 5 cinemático (γw = 1) | 1,0890526340859255 | 1,0890526340859257 |
  | 5 cinemático (γw = 9,81) | 0,8239735634030568 | 0,8239735634030567 |

  - El 5 fijo da 1,0882705, el 1,088271 de la planificación.
  - Montado a mano desde su geometría publicada, el 4 saturado da 0,43466207701. La herramienta integra U con Simpson a
    través del quiebro del terreno en x = 111,4, a 3,8e-7 de la integral exacta, y eso mueve F 7e-8.
- **(alta, del diseño de la spec) un cero falso por encima de la raíz.** La spec busca la raíz en
  H(F) = (N − kh·D)·∏qᵢ porque «no tiene polos». Pero ∏qᵢ no es siempre el mínimo común denominador de Kc:
  - cuando una cara parte una base recta de una misma resistencia, qₘ y Ẽₘ₊₁ son la MISMA función de F;
  - el polo se cancela en Kc, y H conserva qₘ como factor, así que cruza cero donde Kc = kh no tiene raíz;
  - medido en el 5, cuyo vértice 3 parte un tramo recto: una raíz 0,672966 idéntica con γw = 1 y con 9,81 y en los dos
    sentidos. Ahí está por debajo del factor y no cambia nada;
  - pero con resistencia en esa cara el cero falso puede quedar **por encima**: en un pie de dos cuñas colineales, el
    solver habría devuelto 2,064 para un factor verdadero de 1,741 (Kc = −0,24 en 2,064). El constructor de 0.1.462
    pone caras en divisiones uniformes de los tramos rectos, así que habría dado factores falsos.
  - Se quita el factor común de forma exacta. Con eso, la lista de raíces del 5 cinemático coincide una a una con la de
    la herramienta: 0,435312, 0,564298, 0,657502, 0,787954 y 1,089053.
  - Con caras verticales sin resistencia (Janbu) el cero falso queda siempre por debajo de la raíz: Kc → +∞ en el pie
    al acercarse a qₘ = 0.
  - **La revisión adversaria encontró que mi primer arreglo no bastaba** (los dos hallazgos altos de abajo), y el
    arreglo pasó a ser general.
- **El sentido cinemático tiene forma cerrada.** La velocidad relativa de la cuña de arriba en la cara i vale
  vᵢ₋₁·sen(αᵢ₋₁ − αᵢ)/cos(αᵢ + δᵢ):
  - el sentido fijo (σ = +1) es el de un vértice cóncavo, con la base de arriba más empinada;
  - σ = −1, el de un vértice convexo. En el 5, solo el vértice 8 (de 39,8° a 34,7°), que es la diferencia entre 1,0883
    y 1,0891;
  - en un tramo recto partido por una cara la velocidad relativa es cero. La herramienta decide ahí por el signo del
    redondeo, y en el vértice 3 del 5 salió +1. El motor toma +1 a propósito, declarado.
- **La tabla 5.2 de la capa de texto del PDF del 5 (`texto.txt`) va desplazada una fila:** el vértice 6 sale en
  blanco, y queda un 128,66 suelto debajo del 9. La imagen (pág. 11) dice v6 = 114,775, v7 = 123,111 y
  v8 = v9 = 128,66, que es lo que usa la herramienta. La lectura no estaba declarada; el test de 0.1.462 la cita por la
  imagen.
- **La herramienta no tiene regla de raíz mayor.** Guarda todas las raíces, y elige quien la llama (`F_fisica`, la
  cercana a 0,434 en `d122`, `F_casi_fisica`). El contraste se hace con la raíz publicada de su lista.
- **«Solo bases», el convenio de 1973, medido:** +14,8 % (4 seco), −58,0 % (4 saturado), +2,8 % (5 fijo) y +2,9 % (5
  cinemático) de los publicados. Lo que dice la spec.
- **La identidad con Janbu** sale a 1,4e-13 en el peor de los 28 casos medidos (seco, freática, agua libre, kh = 0,1 y
  kv = ±0,05, 25 y 60 dovelas, el modelo y su reflejo), y a 1,8e-14 con la grieta llena.
  - Dar además el agua de la grieta como empuje de cabeza la contaría dos veces: ya va en el `water_force_h` de la
    dovela de la pared. Mueve F un 8,6 %.
- **El coste.** El barrido evaluado con NumPy en todos los F a la vez cuesta 1,15–1,33 ms por `solve` con las 9 cuñas
  del 5, ya con el polinomio general. Con un bucle escalar costaba 3,5–4,4 ms: son 97 evaluaciones hasta F = 1,09, a
  unos 3–5 µs por cuña.
  - Las mismas fórmulas sirven a las dos aritméticas (`_Ops`). Brent y todo lo que se devuelve van con `math`.
- **(baja) la cara paralela a su base.** La spec pedía el código solo en modo cinemático. Pero una cara paralela a la
  base de debajo pone un polo de la recurrencia en F = ∞, donde empieza el barrido, así que se rechaza en los dos
  modos (`SARMA_FACE_PARALLEL`).
- **La revisión adversaria (un agente).** Escribió aparte un Kc que resuelve directamente las 2n ecuaciones de las
  cuñas. Coincide con `kc()` a ~1e-15 fuera de los polos. Hallazgos, todos de esta versión, y lo que se hizo:
  - **(alta) el factor común no es solo entre cuñas vecinas.** Si las bases K y J (J ≥ K+2) tienen la misma α y tan φ,
    y las caras K+1 y J la misma δ y σ·tan φ̄, qₖ ≡ Ẽⱼ.
    - En unos escalones que se repiten, el cero falso (1,4609) caía en el mismo paso del barrido que la raíz mayor
      (1,5055), y salía **1,0841** (−28 %), con normales en tracción, sin aviso. Medido también por mí.
    - En un barrido al azar de cuñas escalonadas, 9 casos de ~1500, con errores de −15 % a −37 %.
  - **(alta) el arreglo exacto no resistía el redondeo.** Una diferencia de 1,3e-12 en tan φ, la que deja la secante
    numérica de Mohr-Coulomb entre dos dovelas del mismo material, impedía la cancelación y devolvía 2,0642 con
    N′ = 1,8e11·W. Lo midió en el caso «water table» del test: los pares 20, 21 y 23 de 24, colineales, sin unir.
  - **Lo que hay detrás, medido por mí:** cerca de una coincidencia (una base doblada Δα) la ecuación tiene una raíz
    VERDADERA pegada a un polo, por encima de la de la base recta, y sus fuerzas crecen como 1/Δα:

    | Δα | F | fuerza máx. / W |
    |---|---|---|
    | 0 (recta) | 1,7408 | 1,21 |
    | 1e-6 | 2,0642 | 8,7e4 |
    | 1e-3 | 2,0663 | 88 |
    | 1e-2 (0,57°) | 2,0830 | 10 |
    | 0,1 (5,7°) | 2,1651 | 1,9 |

    No hay un umbral limpio: es una familia continua. Con Δα = −0,03 las dos raíces de arriba se funden y la mayor que
    queda es 0,095. Es la propia ecuación de Sarma con las caras reducidas por F, no el solver.
  - **Decisión de la propietaria:**
    - cancelación general y exacta de todo factor común estructural (pares K < J), con tolerancia de redondeo 1e-9;
    - se mantiene la regla de la raíz mayor;
    - la solución lleva `max_force_ratio` para que el método avise en 0.1.463, sin cambiar F;
    - las bases casi rectas quedan declaradas y medidas;
    - entran todos los demás hallazgos.
  - **(media)** el equilibrio no se comprobaba con kh, fuerzas horizontales ni cargas. Tres mutantes de `_forces`
    vivían. Ahora se comprueba en la cuña única (con kh, kv y empuje), en todos los casos de Janbu y en los reflejos.
  - **(media)** el reflejo de la fuerza horizontal no se probaba. Ahora entran la presa con agua libre reflejada y las
    tres cuñas con fuerzas horizontales.
  - **(media)** nada protegía `_SWEEP_RATIO`. Ahora hay un caso de dos raíces verdaderas a ×1,12 (0,8627 y 0,7711):
    los barridos ×1,15, ×1,25 y ×1,5 dan 0,1235. Con la resistencia ×20, las mismas raíces quedan a 17,25 y 15,42, y
    `_F_MAX = 5` da 2,47.
  - **(media)** los pares sin mirar tan φ sobrevivían; también los pares sin mirar la cara, que vi yo al ampliar los
    mutantes. Ahora hay casos para cada condición.
  - **(baja)** una cara extrema de longitud cero se rechazaba como paralela sin actuar.
    - La del pie no actúa nunca (E₁ = 0).
    - La de cabeza sin grieta solo orienta la Eₙ₊₁ ficticia, así que se lee como vertical.
  - **(baja)** resistencia en una cara extrema creaba cortante en una cara libre: ahora es un ValueError.
  - **(baja)** kh o el empuje NaN daban `SARMA_NO_ROOT` («kh = nan»), y un empuje negativo se aceptaba: ahora son
    ValueError.
  - **(baja)** `min_q` mezclaba la q de la cara de cabeza ficticia. Ahora solo cuentan las q que dividen un empuje
    real.
  - **(baja)** tres frases no reproducibles:
    - «11 raíces en [0,05; 20] en el 5»: son 8 con el sentido fijo y 5 con el cinemático;
    - «polo hacia 0,4285»: es 0,4288;
    - «por encima de la raíz Kc < kh»: solo vale si no hay polos por encima; en el 4 saturado vale, medido.
  - **(baja)** huecos del test: la admisibilidad cinemática, la inversión de velocidades y E′ al reflejar, los índices
    de los códigos en una masa reflejada, `kc()` con empuje, sentido y reflejo, los extremos del barrido, la rama de
    F > 10⁶ y el respaldo escalar. Ahora tienen caso.
- **Dos caminos equivocados míos al cerrar los mutantes:**
  - **El juez de la raíz preguntaba a `kc()`,** que usa el mismo polinomio y los mismos pares: un par falso corrompía
    a la vez al solver y al juez. Ahora el juez es `_kc_direct` del test, el equilibrio de las cuñas como un sistema
    lineal, independiente del solver.
  - **El arnés de mutantes compilaba cada función mutada con una copia de los globales del módulo,** así que un test
    que parchea `_ARRAY` no llegaba a ella. Ahora compila en el espacio de nombres del propio módulo. Además, negar
    sin y cos no rompía nada: H cambia de signo entero y sus cambios de signo quedan donde estaban. El test usa ahora
    una aritmética que da NaN, y un caso con H(∞) > 0 para la rama que llega a F = ∞, que tampoco se comprobaba y se
    arregla.
- **(trampa de la casa, otra vez) los guiones de edición con Python en modo texto** dejaron en CRLF los archivos que
  tocaban. Además, el `grep -c $'\r'` de Git Bash cuenta todas las líneas, así que no lo ve. Se cuentan los bytes con
  Python y se vuelve a LF con `read_bytes`/`write_bytes`.

## 1. Lo que se añade

- `ogr_slip2d/sarma/__init__.py`: el paquete, sin importar `methods` ni registrar nada.
- `ogr_slip2d/sarma/solver.py`:
  - `Base` y `Face`, en coordenadas del modelo;
  - `solve(bases, faces, *, kh, slide_sign, shear_sense, head_thrust, tolerance, max_iterations)`;
  - `kc(...)` y `kinematic_senses`;
  - `SarmaSolution`, con F, Kc(1), N′, E, E′ y X, los sentidos, las velocidades, la admisibilidad cinemática, min qᵢ
    (solo de las q que dividen un empuje real) y `max_force_ratio`.
  - **La raíz:** si Kc(∞) ≥ kh, `SARMA_NO_DRIVING`. Si no, un barrido descendente: de 10⁶ a 100 por ×10, y de 100 a
    0,01 por ×1,05, que deja 6,6 pasos frente al ×1,38 del 5. Después Brent (Brent 1973, de SciPy, que ya era
    dependencia).
    - El barrido va con NumPy, y su intervalo se confirma con `math`. Si no se confirma, se repite con `math`.
  - **El polinomio** divide de forma exacta cada factor común estructural (`_pairs`, `_polynomial`), con tolerancia de
    redondeo 1e-9 en ángulos y tangentes. Los términos de la suma de Horner van en segmentos partidos tras cada K
    pendiente, porque en el paso J los de hasta K toman Ẽⱼ/qₖ = 1 y los demás Ẽⱼ.
  - **El reflejo:** una masa hacia +x se resuelve reflejada.
  - **Las caras extremas:** la del pie no actúa; la de cabeza sin grieta se lee vertical; ninguna lleva resistencia
    (ValueError).
  - **Las normales negativas** se devuelven sin rechazar; la nota llega con el método.
- `ogr_slip2d/sarma/vertical.py`: `from_vertical_slices(slices, kh, kv)`. Lee lo que lee Janbu y por las mismas
  funciones: `slice_forces`, `seismic_soil_part`, `_local_c_phi` a la σ′ de Fellenius de Janbu y `janbu.slide_sense`.
- Tres códigos del motor, con su español y su muestra en `test_core_messages_v1333`, que cambia por eso (regla I20):
  - `lem.sarma_no_driving`;
  - `lem.sarma_no_root`;
  - `lem.sarma_face_parallel`.
- Las fuentes en `.claude/skills/geotecnia/SKILL.md`, y las casillas de la spec y de las tareas.

## 2. El test

`tests/test_sarma_solver_v1461.py` (39 casos, 2,6 s), contra referencias de fuera del código:
1. una cuña en forma cerrada (Coulomb pseudoestático, Kramer 1996), con agua, sismo y grieta, hasta F = 661 y por
   encima del techo, y su Kc(1);
2. Janbu simplificado sobre las mismas dovelas (Janbu 1954, 1973), a 1e-10, en 12 modelos más uno con envolvente
   curva (`ENVELOPE_AT_OWN_STRESS` apagado y restaurado, para que Janbu la lea donde la lee el adaptador);
3. el 4 publicado (1,198 y 0,434, ±1 %), montado a mano desde su geometría, en los dos sentidos, y «solo bases»
   apartándose +14,8 % y −58 %;
4. la herramienta del banco, a 1e-6, con sus raíces escritas y su procedencia, sin importarla;
5. la raíz junto al polo;
6. los ceros falsos (el pie, los escalones, el redondeo, las bases colineales de distinta φ, los escalones con caras
   distintas) y la base doblada con su raíz junto al polo. El juez es un Kc independiente, el equilibrio de las cuñas
   como un sistema lineal;
7. dos raíces a ×1,12 en la cabeza, también con la resistencia ×20;
8. el reflejo, con fuerzas horizontales, velocidades, E′ y los índices de los códigos;
9. el sentido cinemático contra su forma cerrada, y una cuña que tendría que subir por su base;
10. el equilibrio de cada cuña, comprobado desde fuera del solver;
11. la tolerancia y las iteraciones mueven el número, cada código dispara, el respaldo escalar del barrido, y las
    llamadas mal formadas.

**Mutantes** (`_auditoria/P9_D357/mutants_v1461.py` del banco): 49, y mueren los 49.
- El del adaptador que lee la resistencia a σ = 100 kPa, equivalente con Mohr-Coulomb, muere con la envolvente curva.
- «El reflejo sin invertir las caras» vivía con el 4, cuyas caras son simétricas: muere con las tres cuñas.
- Para matar «kv también sobre las cargas» entró un caso de Janbu con sobrecarga.
- Uno no se escribió, y se declara: el adaptador con el sentido de Bishop (Σ W sen α) en lugar del de Janbu
  (Σ W tan α). Solo difieren cuando las dos sumas tienen distinto signo, y el test exige en cada caso el sentido que
  Janbu publica en `details`.

## 3. Lo que no cambia

- Los nueve métodos y sus números. El registro, la ventana, el API, la CLI y el `.ogr` no se tocan, así que las
  huellas tampoco.
- `test_slide_validation_*`.
- `cunas_sarma.py` no se importa desde el motor ni se copia en él.

## 4. Verificación

- **Suite entera,** `QT_QPA_PLATFORM=offscreen python tests/_runner.py --jobs 4`: 7823 casos, 7822 en verde,
  1 omitido, 0 fallos, sin fugas ni tramos muertos, `EXIT=0`. Una sola corrida, tras la revisión y sus arreglos. La
  última serie en verde fue hace 39 commits, así que no toca.
- `python tests/_runner.py sarma core_messages i18n test_license_v143.py test_version_consistency_v176.py`: 93 de 93.
- **Mutantes:** 49 de 49 muertos (§2).
- **El REPRODÚCELO de P-D357,** antes y después: lo de 0.1.435. La herramienta del banco no cambia.
- **El registro sigue con nueve métodos:** `method_registry()` no ve Sarma.
- La discriminación sobre el árbol de 0.1.460 es trivial (el módulo no existe); la vale la de los mutantes.
- Los VC del banco no se re-corren: ninguno de los nueve métodos ni el rebanador cambian.

## 5. Banco

- **Decisión de la propietaria (2026-11-15):** Sarma va antes de D429–D446.
  - En el ERRORES, el preámbulo y la fila de P10 lo dicen.
  - En `PAQUETES` de `generar_prompts.py`, P9 pasa delante de P10, con el comentario de la decisión.
  - Después, `generar_prompts.py` y la auditoría de la raíz, en 0 ERROR.
- **La ficha D357** apunta 0.1.461. No se cierra: el cierre es `d357()`, tras 0.1.466.
- **`_auditoria/P9_D357/mutants_v1461.py`,** nuevo: los 49 mutantes.
- **B0** (el `--sentido` de `cunas_sarma.py`) va con 0.1.462, como dice el plan.
