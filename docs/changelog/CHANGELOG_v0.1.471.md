# OGR Slip2D v0.1.471

**Los ángulos optimizados de Sarma (D357).** `settings.sarma.slice_angles` admite dos valores nuevos, además de las
tres políticas:
- **`optimized_global`:** todas las superficies se calculan con la bisectriz, y la crítica se calcula otra vez con las
  caras que hacen mínimo su factor. El resultado nuevo ocupa el sitio del viejo.
- **`optimized_all`:** cada superficie se optimiza. Es mucho más lento: con 25 cuñas, segundos por superficie.

Los dos modos los describe la documentación de la referencia, que no dice cómo se hace. Lo de aquí es del proyecto, y
cada regla se midió antes de escribirse. Los factores de las tres políticas no cambian, de ningún método.

Decisiones de la propietaria (2026-11-17):
- **En el mínimo global, el resultado optimizado sustituye al de la crítica en su sitio.** El F de la política de
  partida queda en `details`, y no cambian ni los contadores ni el censo.
- **La guarda de D457 vive en el optimizador.** El `solve` de las superficies normales no cambia, y D457 sigue
  abierta.
- **Las caras paralelas a los planos débiles quedan fuera,** en una ficha nueva (D460).
- **Fase B, con las medidas delante:**
  - el empuje y la continuidad;
  - los pasos de 10° a 0,3125°, sin barrido grueso;
  - el test del problema 1, a 1 % con las horquillas;
  - las caras congeladas en el probabilístico de mínimo global.
- **El ángulo del quiebro:** el test afirma que las caras de la referencia son óptimas aquí al 0,1 %, y el ángulo a
  menos de 2°.
- **Tras la revisión adversaria:**
  - el pliegue se afina hasta su borde y se dice con una nota;
  - con un objetivo que no es F, una crítica que las caras empeorarían conserva las suyas, con su nota;
  - si ninguna política pasa la guarda, no se optimiza, con su nota;
  - dos fichas para dos anomalías anteriores (D461 y D462).

## 0. Lo que se encontró

### La fase A: la medida, solo en el banco

`_auditoria/P9_D357/digitalizar_p1_v1471.py` y `medir_angulos_v1471.py`, con su log.

- **Las figuras del problema 1, a su resolución nativa.** Son imágenes indexadas dentro del PDF: la 1.2 de 456 × 417
  px y la 1.3 de 619 × 558.
  - **Calibración:** por mínimos cuadrados, x e y por separado, con residuos por debajo de 0,07 m.
  - **Cada línea dibujada:** una recta ajustada a sus píxeles oscuros, y los vértices son sus intersecciones.
- **La capa débil del problema 1 está en y = 0–0,75, no en 0,75–1,25** (ficha D459 del banco, por decisión de la
  propietaria). Los colores lo dicen:
  - dorado (242, 206, 0): el suelo superior, también en la banda 0,75–1,25 de la izquierda;
  - verde (60, 179, 113): la capa débil;
  - amarillo puro: la masa resaltada.

  La figura 1.1 rotula vértices en y = 0,75 y ninguno en (40; 1,25). Con la geometría del banco, Sarma sobre estas
  superficies da 2,40, y Spencer 2,42. Con la de las figuras, Spencer da 1,299 y 1,277, a menos del 1 % de los 1,29 y
  1,27 de Donald y Giam.
- **La figura 1.3, «seven slices», dibuja ocho cuñas:**
  - una en el tramo del pie;
  - cinco iguales en el tramo llano;
  - dos en la escarpa (una cara nace a media escarpa).

  No mueve F: las caras en un tramo recto de un solo material no lo mueven.
- **En la figura 1.2, la base de la cuña del pie cruza el contacto y = 0,75,** y la cuña toma el material de su punto
  medio:
  - con la lectura, el punto medio queda 0,015 m por debajo: capa débil, 1,3367;
  - medio píxel más arriba: suelo superior, 1,3830, a 0,07 % del 1,382 de la referencia.
- **En la figura 1.3, nuestro F con las caras dibujadas es 1,3147, frente a 1,324.** La dispersión de ±1 px es 0,0045.
  Lo que falta es la resistencia de las caras: 1,324 queda entre la media de los materiales por longitud (1,3147) y el
  suelo superior solo (1,3388).
- **El prototipo del optimizador:**
  - en la figura 1.2 iguala al barrido bruto 2-D: 1,3303 frente a 1,3303;
  - en la figura 1.3 dejó la cara del quiebro a 116,88°, y la referencia la dibuja a 116,83°.

### Lo que el prototipo destapó: dos reglas que el plan no tenía

- **El bloqueo.** Mover una cara sola la hace cruzar a sus vecinas mucho antes de llegar a un ángulo que importe. En
  el problema 4 saturado, la cara del quiebro no alcanzaba la interfaz publicada (0,4347) por las caras de la escarpa,
  y la búsqueda se paraba en 0,585.

  **El empuje:** una vecina libre que la cara movida cruza se hace paralela a ella, en cascada. Dos caras paralelas no
  se cruzan.
- **Los saltos.** F(θ) salta donde un polo de la recurrencia o de Kc cruza la raíz, o donde la raíz mayor se junta con
  otra y las dos desaparecen. El minimizador iba derecho a esos saltos:
  - problema 4: 0,16, con todas las caras en tracción;
  - problema 5: 0,36, junto a un polo (menor |q| 0,006).

  **La continuidad:** una mejora de más del 1 % se parte por la mitad hasta que cada mitad cambie menos; un salto que
  sigue ahí por debajo de 0,001° es un cambio de rama, y se rechaza.
- **Con las dos reglas:**
  - problema 4 saturado: 0,21, cerca del 0,209 de Spencer sobre la misma superficie (la revisión mostró que es un
    pliegue: ver abajo);
  - problema 5: 0,91 (Spencer 0,986);
  - problema 1 y los círculos, sin cambios.
- **El barrido grueso** (cada cara en 5°, 15°, …, 175° antes de los pasos) daba factores un 2 % más bajos en los
  problemas 4 y 5. Cuesta el doble de pruebas y deja el 5 junto a un polo (menor |q| 0,039). No se tomó.

### Durante la implementación

- **Con el empuje, la cara del quiebro de la figura 1.3 llega a 118,47°,** porque aparta a la vecina que bloqueaba al
  prototipo. El mínimo es plano: con los 116,83° dibujados, F sube un 0,046 %, y con todas las caras dibujadas un
  0,072 %, por debajo de la precisión publicada. El criterio de «< 1°» pasó a «caras dibujadas óptimas al 0,1 % y
  ángulo a < 2°», por decisión de la propietaria.
- **El problema 4 saturado con una sola interfaz:**
  - la rama continua de F(θ) termina en un hueco sin raíz (θ ≈ 85–97°);
  - el optimizador se quedaba cerca de su borde (0,2080 con el último paso de 0,3125°; tras la revisión, en el borde,
    0,2037);
  - el mínimo bruto (0,155) está al otro lado del hueco, que la continuidad no deja cruzar.

  Sin ficha: queda dicho aquí. El seco es una curva lisa, y su mínimo (1,1974) está a 1,5° de la interfaz de Hoek.
- **El juez independiente de 0.1.470 confunde un polo casi cancelado con una raíz.** Su regla es «un polo tiene
  |Kc − kh| > 1». En el círculo de D452 con Ru 0,7, D se anula en 0,5269 con N casi nulo, y Kc − kh cambia de signo con
  valores pequeños. H, el polinomio sin polos, no cambia de signo ahí. El test nuevo bisecta cada cambio de signo: una
  raíz es donde |Kc − kh| va a cero, y un polo donde crece.
- **Optimize con datos por vértice** (pendiente desde 0.1.465) se queda como está. Una cara de vértice que el paseo
  pierde queda libre, y con un modo optimizado la toma el optimizador.

### La revisión adversaria (un agente)

- **ALTO — la guarda de D457 no cubría el arranque.** El optimizador arrancaba de la menor de las tres políticas sin
  la guarda, y elegir la menor favorece justo el factor que el barrido de 1,05 deja demasiado bajo.
  - **El caso:** problema 5 con γw = 9,81, sin las caras de la tabla y 10 cuñas. La bisectriz da 0,5957, con una raíz
    mayor en 0,6096.
  - **El resultado:** 0,5957, con la nota «el factor que queda es uno comprobado», que era falsa.
  - **El arreglo:** el arranque pasa por la guarda y ahora es la normal media, 0,6091. El resultado, 0,5958, es la raíz
    mayor de sus cuñas.
  - **Si ninguna política pasa,** no se optimiza: queda el factor ordinario del método, con la nota
    `method.sarma_angles_no_start` (decisión de la propietaria).
- **ALTO — el «óptimo» de varios casos era un pliegue,** el borde donde la raíz mayor se junta con la siguiente y
  desaparecen las dos.
  - **Dependía del paso:** con un último paso de 0,039°, −1,3 % en el 4 saturado con 2 cuñas, −2,9 % con 10, −1,0 % en
    un talud con contacto.
  - **Las caras en tracción:** todas tienen E′ < 0 en ese borde. La interfaz de Hoek tiene E′ = +12 660.
  - **El 0,21 «igual que Spencer»** del primer borrador era una coincidencia.

  **El arreglo, por decisión de la propietaria:** un último movimiento que no encuentra factor o salta se parte por la
  mitad hacia ese borde, hasta 0,001°, y una nota lo dice (`method.sarma_angles_fold`, con las caras en tracción). El
  factor se queda.
  - **El 4 saturado:** 0,20370 con 2 cuñas y con 10, con los dos pasos.
  - **La fig. 1.3:** 1,31371 y 1,31370.
  - **Resto, declarado:** en el círculo de Ru 0,7, con 5–6 caras en el pliegue a la vez, queda un 0,27 % (0,50032 y
    0,49898). El refinado es cara a cara y no recorre un pliegue conjunto. Ese caso lleva además la nota de polo
    cercano.
- **MEDIO — la sensibilidad no congelaba las caras:** en la media daba el factor de la bisectriz (1,335866 frente a
  1,330356). Ahora congela como el mínimo global, con un solo helper, `methods.sarma.freeze_faces`.
- **MEDIO — con el objetivo Ky, la crítica sustituida empeoraba el resultado.** Su F bajaba (1,31725 → 1,31371) y su Ky
  subía (0,099787 → 0,100636), y la crítica pasaba a otra superficie sin optimizar.

  Ahora, con un objetivo que no es F, una crítica que las caras harían quedar detrás conserva las suyas, con la nota
  `method.sarma_angles_kept` (decisión de la propietaria). Con F se sustituye siempre: el nuevo solo queda detrás
  cuando el factor viejo fallaba la guarda o era un inadmisible de respaldo. Aplicar la regla también con F devolvía,
  en el problema 5 de arriba, el 0,5957 sin comprobar. Se midió al aplicar la regla, y por eso se dejó solo para los
  objetivos que no son F.
- **MEDIO — el coste y Cancelar:**
  - un talud con contacto y 25 cuñas tarda unos 35 s por superficie;
  - Cancelar no actuaba durante la optimización;
  - los saltos rechazados se repetían.

  Ahora cada prueba es un punto de cancelación (`checkpoint`), el paso posterior va bajo la fase «Optimizando la
  superficie crítica…» con su avance por pasos, y una configuración ya resuelta no se resuelve otra vez. La ayuda del
  diálogo dice «de segundos a un minuto» y que un paso cuenta cuando baja F más que la tolerancia.
- **BAJOS, arreglados:**
  - una superficie sin ninguna cara que mover ya no sale marcada como optimizada;
  - el docstring decía «3 pasadas como mucho» (se midieron 14);
  - el log de mutantes era anterior al test final, y se regeneró.
- **BAJOS, declarados:**
  - `block_groups[*]["min_fos"]` conserva el factor de la bisectriz (no lo lee nadie);
  - unas caras congeladas que no casan con otra masa caen a la política sin decirlo (no se pudo provocar: con grieta,
    capa débil y kh con espejo, el mínimo global reproduce el determinista).
- **Anteriores a esta versión, a fichas** (por decisión de la propietaria):
  - **D461:** con la norma de diseño y `single_source_weight=False`, F salta −1,55 % en θ = 90° (DA1-C1);
  - **D462:** el diálogo de 0.1.470 muestra como Bisectriz un valor de `slice_angles` que no conoce, y lo guarda así al
    Aceptar, sin avisar;
  - **D457 en el `solve` normal, sigue abierta:** la bisectriz del 5 con γw = 9,81.
- **Sin hallazgo:**
  - el espejo, bit a bit;
  - la reconstrucción por abscisa en 15 superficies;
  - serie y paralelo con «todas», bit a bit;
  - el volcado a disco;
  - la sustitución en Path, SA, PSO con mínimos múltiples, Auto Refine, Slope y Grid con Optimize;
  - el mínimo global con círculo, grieta, capa débil, kh y datos de vértice;
  - la norma de diseño;
  - la compatibilidad: HEAD abre un `.ogr` con `optimized_global` y omite Sarma con su nota, y `model_hash` es igual
    en las dos versiones.

## 1. El cambio

- **`ogr_slip2d/sarma/optimize_angles.py` (nuevo):** `optimize(project, build=, evaluate=, larger_root=, gain=,
  progress=)`. Su docstring cuenta lo medido y lo que la revisión corrigió.
- **`ogr_slip2d/sarma/wedges.py`:**
  - `build_wedges(boundaries=, face_angles=)`: las caras dadas por abscisa, con la fuente `optimized`, que nunca se
    quitan ni se ponen verticales;
  - `boundaries_fit` y `ground_position`.
- **`ogr_slip2d/sarma/solver.py`:** `larger_root_above` y `FINE_SWEEP_RATIO` (1,002); `_sweep` toma la razón.
- **`ogr_slip2d/sarma/angles.py`:** `OPTIMIZED_GLOBAL`, `OPTIMIZED_ALL` y `ANGLE_SETTINGS`.
- **`ogr_slip2d/methods/sarma.py`:**
  - el modo;
  - `frozen_faces` y `frozen_faces_of`;
  - `wedges_for(policy=, boundaries=, face_angles=)`;
  - `larger_root_above`.
- **`ogr_slip2d/search.py`:**
  - `_optimize_critical_angles` en `BaseSearch.run`, después de las superficies del usuario;
  - `optimized_angles_of`;
  - con «todas», en `_best_of_masses`.
- **`ogr_slip2d/analysis_runner.py`:**
  - el ajuste;
  - la puerta de una superficie, que se optimiza porque es su propio mínimo;
  - `run_configured_optimization`, la acción de menú Optimize;
  - la nota `method.sarma_sweep_miss`.
- **`ogr_slip2d/probabilistic.py` y `sensitivity.py`:** las muestras de mínimo global y los puntos de la sensibilidad
  congelan las caras de la crítica en el método (`freeze_faces`).
- **Las notas** `method.sarma_angles_no_start`, `method.sarma_angles_kept` y `method.sarma_angles_fold`, con su
  español.
- **El API** (los modos en el esquema; `sarma_angle_mode`, `sarma_start_policy`, `sarma_start_fos`,
  `sarma_angle_trials`, `sarma_sweep_misses` y `sarma_angle_jumps`), **el informe** (las dos filas de Global Minimums
  y los nombres de los modos) y **el diálogo**, con su español.

## 2. El test

`tests/test_sarma_optimize_angles_v1471.py`, 32 casos y unos 18 s. Comprueba:
- **el problema 1** frente a 1,382 y 1,324;
- **el problema 4:**
  - seco: frente a un barrido bruto, y por debajo de la interfaz de Hoek;
  - saturado: el óptimo alcanza la interfaz de Hoek;
- **nunca por encima de una política;**
- **las reglas:** exactas sobre un factor sintético, y sobre cuñas reales con un empuje independiente y el Kc
  independiente de `_kc_direct`;
- **lo de la revisión:**
  - la guarda del arranque (problema 5 con γw = 9,81);
  - el pliegue con el mismo borde con 2 y 10 cuñas y con un paso más fino;
  - con el objetivo Ky, la crítica que se queda;
  - la sensibilidad congelada;
  - las tres notas;
- **la regla 7:** «todas» frente a «mínimo global», con dos superficies del usuario;
- **la sustitución en su sitio;**
- **la muestra del probabilístico;**
- **el contrato del constructor por abscisa;**
- **el ajuste, el API, el informe y la nota en español.**

Mutantes: `_auditoria/P9_D357/mutants_v1471.py` del banco, con su log: 37, y ninguno vive. Tiene un modo
`--anclas` que compila cada mutante sin correr nada: dos corridas se perdieron por anclas que el código había dejado
viejas.
- **Antes de la revisión vivían cinco:**
  - arrancar solo en la bisectriz;
  - sin empuje, y el empuje solo hacia el pie;
  - los dos del constructor.

  Los matan:
  - la mejor política del 4 seco;
  - el 4 saturado frente a la interfaz de Hoek: sin empuje se queda en 0,585;
  - el test directo del constructor.

  La fig. 1.3 no distinguía el empuje: sin él, el optimizador aparta las caras del tramo recto por mejoras en la sexta
  cifra y llega al mismo óptimo.
- **Después de la revisión, uno:** la nota de «sin arranque» en la búsqueda, que ningún caso real llevaba hasta ahí. Lo
  mata un test de la tubería con una guarda inyectada que rechaza todo, restaurada al acabar.

## 3. La suite

- `test_method_notes_v1348`: muestras de las cuatro notas nuevas.
- **La primera suite entera dio un fallo:** `test_texts_details_v1418` exige el punto decimal en los textos del
  diálogo de ajustes, y la ayuda en español decía «0,3125°». Ahora dice «0.3125°».

## 4. Verificación

- **La suite entera, `--jobs 4`, tras el arreglo:** 8046 casos; pasan 8045 y uno queda saltado, sin fugas ni tramos
  muertos. La última serie en verde es de hace 49 commits.
- **El test nuevo:** 32 de 32. **Mutantes:** 37, ninguno vivo.
- **Los README:** 8013 → 8045 tests.
- **Medidas con el código final** (los guiones del banco y de la revisión):

  | Caso | Paso 0,3125° | Paso 0,039° |
  |---|---|---|
  | 4 saturado, 2 cuñas | 0,20370 | 0,20370 |
  | 4 saturado, 10 cuñas | 0,20370 | 0,20370 |
  | Fig. 1.3 | 1,31371 | 1,31370 |

  - **El problema 5 con γw = 9,81:** arranca en la normal media y da 0,595833, comprobado.
  - **La sensibilidad en la media:** el factor determinista optimizado.
  - **Con el objetivo Ky:** la crítica conserva su Ky.
  - **El coste, con 25 cuñas:** de 7 s (talud, círculo con Ru 0,3) a 36 s (talud con contacto, 1604 pruebas) por
    superficie.

## 5. Lo que queda

- **D459 (banco):** la capa débil del problema 1, y re-correr su comparativa.
- **D460:** las caras paralelas a los planos débiles.
- **D457 sigue abierta:** la guarda solo vive en el optimizador.
- **El banco:**
  - el problema 1 con Sarma optimizado (tarea 36 de la spec);
  - la rejilla con «todas», en serie y en paralelo;
  - el progreso de D357.
