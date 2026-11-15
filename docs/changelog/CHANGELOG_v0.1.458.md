# OGR Slip2D v0.1.458

**Sin cortes obligados, el rebanador fija el último corte en x_r (D407).** `_slice_boundaries` devolvía la división
uniforme `x_l + step * i` y no fijaba el último corte en `x_r`. La rama con cortes lo hace desde 0.1.66. En coma
flotante `x_l + (w / n) * n` no es `x_r`, y un pelo más allá de x_r el rebanador leía otra cosa.

- **Una polilínea** (lo que decía la ficha). `SlipSurface.base_y_at` da None fuera de sus vértices.
  - Sobre el plano (2, 2)–(30, 10) de `test_yield_acceleration_v1127`, el último corte se pasaba de 30 por 3,6e-15
    con 25, 41, 43, 50 y 51 dovelas.
  - El rebanador abandonaba entonces la superficie entera sin anotar motivo, y la corrida decía el genérico «the
    slicer refused it (more mandatory cuts than slices, a degenerate width or a tension crack it could not place)»,
    que no era ninguna de las tres cosas.
  - 25 es el número de dovelas por defecto del proyecto.
- **Un círculo que sale por una cara vertical en x_r, con el terreno más bajo delante** (un pie cortado en vertical
  con rotura de izquierda a derecha). Esto no lo decía la ficha: lo encontró la revisión adversaria.
  - Un ulp después de la cara, la envolvente leída por un lado es la berma de delante y no la coronación de la cara.
  - La sujeción del extremo (`ends_are_ground_crossings`) bajaba la base de la última esquina hasta la berma.
  - El factor subía varios puntos, del lado inseguro: un 4,7 % entre el modelo y su reflejo.

Por decisión de la propietaria (opción A del prompt), el último corte es `x_r` también sin cortes obligados: la misma
regla en las dos ramas.

Medido con 0.1.457 (3f7b506), con `_auditoria/P10_herramientas/paso0_d407.py` del banco y su log de 0.1.457, y la
cara con el especular de la revisión:

| | 0.1.457 | ahora |
|---|---|---|
| el plano de dos vértices, de 5 a 80 dovelas | rechazado con 25, 41, 43, 50 y 51, `reasons` vacía | rebanado con los 76 |
| la junta de `test_weak_layer_v1121`, de 5 a 80 | rechazada con los mismos cinco, con el genérico | con factor con los 76 |
| la última dovela del plano con 55 y 71 | acaba en 29,999999999999996 | acaba en 30 |
| un círculo que sale por una cara vertical en x_r, frente a su reflejo, de 5 a 80, Bishop | hasta 4,7 % (39 dovelas: 2,4808 frente a 2,3685) | 3,4e-14 |
| 201 pares círculo × dovelas de un talud sin cara ni cortes obligados, Bishop | — | 14 cambian de `float.hex`, el peor en 2,2e-15 relativo |
| los mismos con un contorno de material a y = 5 | — | ninguno cambia |
| los 23 casos del banco de cómputo (huella bit a bit) | — | 14 idénticos; en 9 cambian evaluaciones sueltas; ninguna crítica cambia |
| los dos modelos del banco con una cara que baja hacia la derecha (02-048 con y sin bulones, y 05-005), su búsqueda entera | — | en el 048, de 2 a 8 factores de ~1540 por método, el peor en 1,1e-15; en el 05-005, ninguno; ninguna crítica cambia |

Es la trigésima primera versión de la tanda P10 y la primera del plan aprobado el 2026-11-15 (D407, D427 y D428).

## 0. Lo que se encontró

- **El REPRODÚCELO da con 0.1.457 lo de 0.1.435.** Da `2 vértices, rechaza: {25: [], 41: [], 43: [], 50: [], 51: []}`
  y `3 vértices, rechaza: {}`. El último corte con 25 es `30.000000000000004` y las anchuras son 1,12 todas. Y da
  `se pasa: [25, 41, 43, 50, 51] se queda corto: [55, 71]`.
- **La ficha tenía un segundo caso que el prompt no decía,** y su criterio de cierre lo exige: la junta de
  `tests/test_weak_layer_v1121.py`. Lo añadió el paso 0 de D403 (0.1.446).
  - Es la polilínea (2, 2)–(16, 1)–(30, 10), recortada por la capa débil de (2, 2) a (30, 10).
  - **Es la misma causa.** La capa gana todo el tramo, así que el vértice de la base en x = 16 no es un vértice de la
    superficie recortada (`WeakLayerSurface.kinks`). Sin cortes, la división es uniforme entre los mismos dos
    extremos.
  - Medido en un proceso: hoy rechaza [25, 41, 43, 50, 51]; con A, ninguno.
- **La sospecha con que se abrió la ficha queda refutada en los dos casos.** Decía que un corte uniforme caía sobre
  uno obligado y dejaba una dovela casi nula. No hay ningún corte obligado, y las 25 dovelas del plano miden 28/25,
  la última incluida.
- **Lo que A mueve en un talud sin cara, medido en un mismo proceso** con `_slice_boundaries` sustituida (la de
  0.1.457, la nueva y otra vez la de 0.1.457 como control, que repite la primera bit a bit):
  - 128 círculos del mismo talud con c = 5 kPa, con 25, 41 y 50 dovelas: se rebanan 201 pares con las dos reglas;
  - sin cortes obligados, 14 cambian de `float.hex`, el peor en 2,2e-15 relativo, con el mismo número de dovelas. Allí
    un círculo contesta también un pelo más allá de x_r, porque su arco sigue y, en su tangente vertical, la holgura
    relativa de `SlipCircle._ARC_EPS` (0.1.100) sujeta el extremo;
  - con un contorno de material a y = 5, ninguno cambia: esa rama ya fijaba el último corte.
- **La huella del banco de cómputo** (`_auditoria/COMPUTO/bench`), con el lote `version` sobre 0.1.457 y sobre
  0.1.458, uno detrás de otro y solos en la máquina (`datos/v0.1.457` y `datos/v0.1.458`), comparada caso a caso con
  `comparar.py`:
  - 14 de los 23 casos son idénticos bit a bit: K08, K09, K10 y K12 a K22;
  - en los otros 9 (K01, K01b, K02 a K07 y K11, todos de círculos) difieren solo evaluaciones sueltas de la
    población: de 2 de 2118 (K11) a 7 de 23 (K04). Ninguna aparece ni desaparece, y ninguna crítica ni su factor
    cambia;
  - la huella guarda un resumen por evaluación, no su valor. La magnitud se midió aparte, con un A/B en memoria y en
    serie de K01 y K04. En K01, de 7 a 9 factores de 336 por método, el peor en 4,8e-15. En K04 (el 078, caso 3b, con
    un foco tangente), 6 o 7 de 23, el peor en 3,4e-8 con Janbu;
  - **los 3,4e-8 no son la convergencia.** Con tolerancia 1e-12 salen los mismos. Es un círculo que sale por su
    tangente vertical: (x_r − cx)/R = 1 y dy/dx = 6,7e7 en x_r. Allí un ulp de x vale √(2·R·ulp) de cota de la
    base. El corte nuevo evalúa la base en el cruce mismo, el que el rebanador ya da por bueno en un círculo
    (`ends_are_ground_crossings`). Los otros círculos que cambian en K04 se mueven de 1,9e-16 a 4,8e-15;
  - ninguno de los 23 casos tiene una cara vertical en el extremo derecho de sus círculos.
- **La revisión adversaria (un agente) encontró la cara vertical en x_r,** que ni la ficha ni el paso 0 habían visto,
  y que cambia lo que contaba el primer borrador de esta versión («un círculo se mueve en los últimos bits»).
  - El mecanismo: `candidate_chords` da como cruce exactamente x = 40, la cara (dx = 0). Con la regla de 0.1.457, si
    `x_l + step * n` se pasaba por un ulp, `envelope_y_at(ground, x, side=-1)` leía la rama de delante, la berma
    (y = 10). La sujeción de la última esquina (`i == last_i and ends_are_ground_crossings`) bajaba entonces la base
    hasta ella, sin decir nada. En x_r exacto la lectura por la izquierda da la coronación de la cara, como ya
    pasaba en el extremo izquierdo.
  - Medido otra vez aquí, en un mismo proceso: talud (0, 0)…(40, 10), (40, 15)… con la cara en x = 40 de y = 10 a 15,
    c = 5 kPa, φ = 30°, el círculo (36; 38,33; 26,507) de su rejilla por defecto, 41 dovelas. Con 0.1.457 la última
    dovela acaba en 40,00000000000001 con la base en y = 10 y la cara de altura nula; con 0.1.458 acaba en 40, con la
    base en el arco (y = 12,13) bajo la coronación (y = 15).
  - **El especular:** el mismo modelo reflejado, con la rotura al revés y la cara en el extremo izquierdo, que siempre
    fue exacto. De 5 a 80 dovelas, con Bishop: con 0.1.457 difieren hasta un 4,7 % (39 dovelas: 2,4808 frente a
    2,3685), y con 0.1.458, 3,4e-14. El valor viejo era el más alto.
  - La revisión midió también la rejilla por defecto de ese modelo, con 41 dovelas: círculos que pasan de 2,4794 a
    2,3684 y de 2,2915 a 2,2192, y la crítica igual en las cuatro configuraciones que probó.
- **Las otras dos opciones del prompt.**
  - Con B (fijarlo solo cuando se pasa), el plano y la cara se rebanan igual, pero con 55 y 71 la última dovela del
    plano acaba un ulp antes de 30. Un mutante con B muere en los dos casos de la partición.
  - C (solo para lo que no es un círculo) no cambiaba ningún bit de los círculos, y por eso dejaba vivo el defecto de
    la cara. El primer borrador lo contaba como una ventaja. Además pasaba los seis casos del primer test: lo vio la
    revisión, y por eso entró el caso del especular, que lo mata.
- **El rechazo sin motivo.** La propietaria decidió medirlo antes de darle un motivo propio (`slicer.py`, la rama en
  que `base_y_at` da None).
  - Un censo en memoria (`sitecustomize` en cada proceso, también en los hijos del pool) vigiló `_slice_boundaries`
    en los 64 archivos de tests de rebanado, búsquedas, superficies, capas débiles, grieta, Newmark y foco (1019
    casos en verde). Contó las veces que algún corte cae donde `base_y_at` da None: 0 de 122 357.
  - La misma sonda sobre el árbol de 0.1.457 cazó el plano de 25 dovelas (1 de 3), así que el cero no es un medidor
    ciego.
  - **La revisión encontró cómo llegar:** un círculo con extremos guardados fuera de su propio arco.
    `SlipCircle(20, 25, 10, x_left=10 − 5e-5, x_right=26)` en el talud de la cara: `base_y_at(9,99995)` da None y
    sale el genérico falso. Medido aquí también.
  - Ningún camino del programa lo produce: `to_dict` y `from_dict` guardan los extremos exactos, y el agente no
    pasa extremos. Solo lo hace un script o un archivo editado a mano.
  - Por decisión de la propietaria se queda como guarda, sin cadena nueva, con un comentario que dice exactamente
    cuándo se alcanza. El del primer borrador decía que todo corte cae donde la superficie contesta, y no es así.
- **Un camino equivocado del test.** El caso de la puerta del usuario comparaba Janbu con la forma cerrada de la cuña
  (tan φ / tan β) a 1e-6 y fallaba por 2,6e-6. No era el rebanador sino la tolerancia de convergencia por defecto del
  proyecto (0,005): con `methods.tolerance = 1e-10` coincide.
- **Ky se calcula en el test,** no con `_plane_ky` de v1127. Ese lee la memoria `_CACHE` de su archivo, y la guarda
  `test_shared_test_caches_v1378` lo cuenta como alcanzar la memoria de otro archivo.
- **La revisión vio de paso, sin que esta versión lo mueva, la carga lineal justo en x_r que se pierde** (el
  docstring de `line_loads_on` dice lo contrario; desde 0.1.75). Es D427, la versión siguiente del plan, también
  para el gunitado del 048 en (12, 8).

## 1. El arreglo

`ogr_slip2d/slicer.py`, `_slice_boundaries`: sin cortes obligados, los cortes son `x_l + step * i` para
i = 0 … n − 1, y el último es `x_r`. Los interiores no cambian ni un bit; el test lo fija. El comentario dice por qué,
con los tres casos: la polilínea, la cara vertical y el último bit de un círculo.

La rama de `slice_surface` que abandona la superficie cuando `base_y_at` da None se queda como guarda, con lo medido y
el único modo de alcanzarla escritos al lado.

`tests/test_newmark_user_surfaces_v1429.py` se queda en 60 dovelas, por decisión de la propietaria, para que no se
mueva ningún número suyo. Cambia su comentario («with 25 this two-vertex plane is one the slicer refuses»), que deja
de ser cierto.

## 2. El test

`tests/test_slice_last_cut_v1458.py`, 8 casos, alrededor de 1 s sin contar los imports, sin Qt. Invariante: el
rebanador reparte exactamente [x_l, x_r], con el número de dovelas pedido.

- **La partición.** El plano se rebana con todos los números de 5 a 80, con n dovelas exactas, de x = 2 a x = 30
  exactos. Los cortes interiores son la división uniforme bit a bit: solo se movió el último. La premisa, que la
  división uniforme se pasa con los cinco números, también se comprueba.
- **La junta contra Fellenius.** El Ordinario sobre la junta es la forma cerrada plana de v1121
  (`_ordinary_closed_form`) a 1e-9, con todos los números de 5 a 80.
- **Ky contra Newmark** (Newmark 1965). Janbu simplificado da Ky = tan(φ − β) a 1e-6 con 25, 41, 43, 50 y 51, como
  v1127 lo afirma con 60.
- **La puerta del usuario.** El plano evaluado con las 25 dovelas del proyecto tiene factor y ningún aviso. Su factor
  es el de la cuña sin cohesión, tan φ / tan β (Duncan y Wright 2005, §6), a 1e-6.
- **La cara en x_r frente a su reflejo** (de la revisión). De 5 a 80 dovelas:
  - la última dovela del círculo acaba en la cara, con la base en su arco y bajo la coronación;
  - Bishop (1955) da al modelo y a su reflejo el mismo factor, a 1e-10.

Discriminación: sobre el `git archive` de 0.1.457, sin el buscador editable y con los `__file__` comprobados, fallan
7 de los 8. Pasa la premisa, que no depende del código. Los mutantes (`mutants_d407.py` del banco) mueren los seis:

- la regla de 0.1.457: 7 casos;
- B, solo cuando se pasa: los 2 de la partición;
- el arreglo solo para las polilíneas simples: el de la junta y los 2 de la cara;
- los cortes recalculados como `x_l + w·i/n`: el de los cortes interiores;
- C, todo menos los círculos, y C2, solo lo que tiene vértices: los 2 de la cara, y solo esos.

## 3. Lo que no cambia

- Ninguna superficie con cortes obligados: esa rama no se tocó, y el A/B lo mide (0 de 201).
- Ninguna superficie crítica de los 23 casos del banco de cómputo, bit a bit.
- El número de dovelas pedido: el arreglo no quita ni añade ninguna.
- Los `test_slide_validation_*` y `test_noncircular_validation_v192`, en verde.
- Ninguna cadena de la interfaz, ajuste ni acción.

**Sí cambian:**
- en varios puntos, y hacia abajo, los factores de los círculos que salen por una cara vertical en x_r con el
  terreno más bajo delante, como arriba;
- en sus últimos bits, factores de círculos que no son críticos;
- hasta 3,4e-8, un círculo que sale por su tangente vertical.

## 4. Verificación

- El test solo: 8 de 8. Su discriminación y sus mutantes, arriba.
- Los vecinos, con cada patrón comprobado con `--list` (D431): `yield_acceleration newmark_user_surfaces
  user_surfaces_v1157 slicer_budget slice_cuts weak_layer noncircular_validation line_load_boundary janbu_wedge
  disjoint_masses slide_validation slice_last_cut`, la guarda de memorias compartidas y la de cabeceras: 302 casos en
  19 archivos, en verde. La revisión corrió además `test_ground_envelope_v1114`, `test_tangent_surface_v1100` y
  `test_efp_wall_v1122`: 65 de 65.
- El censo de la rama sin motivo, arriba: 1019 casos en 64 archivos, en verde, con el censo puesto.
- **La suite entera con `--jobs 4`,** tras los arreglos de la revisión:
  - 7754 casos: 7753 en verde y 1 saltado, `Failed: 0`;
  - sin `Leaks` ni `Chunks died`, y sin el aviso `SLOW, NOT IN tests/_slow.txt`;
  - la última serie en verde fue hace 36 commits (bea135c), así que no toca serie.
  - Los contadores de los dos README pasan de 7745 a 7753: los 8 casos nuevos.

## 5. Banco

- `d407()` en el `verificar_cierres.py` de la raíz, registrada en `COMPROBACIONES`. Mide en vivo, de 5 a 80 dovelas:
  - el plano por `slice_surface`;
  - la junta por `evaluate_surfaces`;
  - la cara y su reflejo por Bishop, a 1e-10.

  Exige además las cinco clases del test.
  - Con el árbol nuevo: CUBIERTO POR TEST (la cara, 3,5e-14).
  - Con el de 0.1.457: SIGUE ABIERTO por lo que hace (los cinco rechazos en cada caso, y la cara, 4,7e-2).
- **Los dos modelos del banco con una cara que baja hacia la derecha** (`paso0_d407_s1.py` y su log).
  - Según la revisión, que leyó el JSON de los 230 `.ogr`, son solo dos:
    - 02-048, con la cara x = 12 de y = 1 a 8;
    - 05-005.
  - Por decisión de la propietaria, su búsqueda entera se midió con la regla de 0.1.457, la nueva y otra vez la de
    0.1.457 como control: en serie, en un mismo proceso y factor a factor por `float.hex`.
  - **El 048, con y sin bulones,** con Janbu, Janbu corregido, Spencer y Bishop:
    - cambian de 2 a 8 factores de unas 1540 evaluaciones por método, el peor en 1,1e-15;
    - ninguna superficie gana ni pierde su factor, y ninguna crítica cambia;
    - sus seis planos dan `x_l + step * 50 == 12` exacto (lo comprobó la revisión), así que sus cifras publicadas no
      se mueven.
  - **El 05-005,** con Bishop y Janbu: no cambia ningún factor.
  - Las tres corridas de control repiten la primera bit a bit.
  - Los modelos que se construyen con `construir_modelo.py` no se han escaneado.
  - **Así que la clase de la cara no muerde en el banco,** y ningún número que publica se mueve.
- **El VC de la raíz entero, en seco:** 168 comprobaciones en 12,3 min. No se corría entero desde 0.1.426
  (2026-11-04): de 0.1.427 a 0.1.457 cada versión corrió la suya y las que tocaba.
  - 166 dicen lo que el JSON archivado y `D407` entra CUBIERTO POR TEST.
  - **`D340` bajaba en falso desde 0.1.435, y no por D407.**
    - `d340` buscaba por texto, en `ogr_gui/main_window.py`, la línea `self.result, _report, self.warnings =`.
    - 0.1.435 (D413, c080aa0) la cambió por `self.result, self.factor_report, self.warnings = (` al dejar de tirar
      el informe de factores. El trabajador del barrido seguía guardando los avisos, y `test_task_notes_v1363` lo
      sigue fijando.
    - Por decisión de la propietaria, la comprobación lee ahora el AST (`_d340_barrido_guarda`): alguna asignación
      guarda `self.warnings` directamente de `run_configured_drawdown_sweep(...)`.
    - Discrimina: False en 60f92fa^ (antes del cierre de D340) y True en 60f92fa, en c080aa0^, en c080aa0 y en
      0.1.458.
    - Con ella, `D340` vuelve a CUBIERTO POR TEST.
  - **Un camino equivocado, de la herramienta.** La primera corrida entera se colgó en la comprobación 99, `d362`, la
    primera que abre un pool de procesos.
    - `_auditoria/P10_herramientas/discriminar_vc.py` no tenía la guarda de `__main__`, y cada trabajador `spawn` lo
      reimportaba y volvía a ejecutar las comprobaciones desde la primera, en vez de servir al pool. Se vio con
      `sys.remote_exec`, sin parar el proceso.
    - Llevaba 84 min. La herramienta solo se había usado con unas pocas comprobaciones, y ninguna abría un pool.
    - Ahora todo va dentro de `main()`, y cada línea sale con `flush` y su tiempo.
    - Las más lentas: `d367` (183 s), `d377` (123 s), `d122` (61 s) y `d250` (60 s).
- **El VC del 02 entero, con `--seco`:**
  - los 242 veredictos dicen lo que su JSON archivado;
  - difieren seis detalles, todos recuentos que crecen con el repositorio: líneas de código (D96), acciones (D102),
    una línea citada (D101), archivos (D174), citas (D188) y un contador de búsqueda más (D255);
  - ningún factor cambia.
