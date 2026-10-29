# Auditoría del cómputo — OGR Slip2D 0.1.377

Fecha: 2026-10-29. Árbol: `f179589` (0.1.377), sin cambios durante toda la medida. Python 3.14.7,
numpy 2.5.1, scipy 1.18.0, shapely 2.1.2 (GEOS 3.13.1), Windows 11, i7-8550U (4 núcleos físicos, 8
lógicos, procesador de 15 W), 15,9 GB de RAM, plan «Equilibrado», enchufado. La CI (Linux), leída
de su registro.

Pregunta: ¿dónde gasta el tiempo el cálculo de OGR Slip2D, en las simulaciones y en los tests, y
qué se puede acelerar **sin mover un número**? Este documento es la **fase 2** (diagnóstico). No se
ha cambiado nada del programa ni de los tests; la propuesta (fase 3) va aparte y espera el OK de la
propietaria, optimización a optimización.

Cada cifra lleva su naturaleza: **[M]** medida en esta auditoría, **[H]** hipótesis o
extrapolación, **[L]** leída en el código.

---

## 1. Resumen

1. **Lo que domina depende del cálculo, y está localizado** [M]:
   - en las rejillas con métodos baratos, **rebanar cuesta tanto como resolver** (54 % del cálculo en
     K03 y K06), y se repite **una vez por método**: cada método activo lanza su propia búsqueda;
   - en los métodos rigurosos y en las búsquedas no circulares, `solve_branch` y `moment_terms`
     (75–84 % de Spencer sobre poligonales), que recalculan en cada pasada lo que no cambia;
   - en Mohr-Coulomb, `local_c_phi` es una secante de tres evaluaciones que se repite con los mismos
     bits el 32–75 % de las veces;
   - **la presión del MEF busca su elemento recorriendo la malla**: 86 % de una búsqueda sobre 1441
     elementos (549 elementos probados por consulta);
   - en Global Minimum, **la firma de las regiones** se reconstruye en cada consulta de material: 36 %;
   - en el desembalse, un `Material` nuevo **por dovela y pasada**: ~12 %;
   - en el MEF, el trabajo por elemento en Python en cada solución; SuperLU es el 2 %.
2. **El paralelo da ×1,6–2,2 en las rejillas grandes, y frena las pequeñas** [M]. Un pool de 4
   cuesta 0,4–0,6 s y se abre uno **por método**; 8 trabajadores no mejoran a 4. El techo (~×1,9) lo
   ponen la vuelta de los resultados (8–28 kB y 0,15–0,73 ms por evaluación, deserializados en el
   padre) y una CPU de 15 W que, con los cuatro núcleos cargados, trabaja ~×1,9 más lenta por unidad
   [M+H]. **El algoritmo es paralelo al 99,8 %**: no es eso lo que limita. En esta máquina, **quitar
   trabajo vale más que repartirlo**.
3. **El umbral de 400 círculos está bien puesto** para Bishop (equilibrio a 539) y es prudente para
   Spencer [M]. Lo que falla es que cuenta los círculos nominales: 4 pools para los 172 que deja un
   foco, ×2,9 más lento que en serie.
4. **La huella es idéntica bit a bit en 95 comprobaciones** [M]: determinismo (14 casos), **serie
   igual a paralelo en 12 modelos** (hasta hoy solo lo exigía un test sobre un caso seco de Bishop),
   y el instrumento (gancho, muestreador y `cProfile`) no cambia ningún número en los 23.
5. **Los tests caros son caros sobre todo porque son motor, y porque repiten** [M]: el motor es el
   85–99 % de los archivos de cálculo; **495 s de los 1907 que suman solos los 41 archivos más caros
   son cálculos idénticos repetidos dentro del mismo archivo** (`test_annealing_inequality_v1119`
   155 s; el desembalse de `test_transient_v130`, 7 veces, 113 s). De ellos, **~295 s se pueden
   compartir sin debilitar ningún test**; el resto son repeticiones a propósito (revisado en la
   fase 3, §8.3). Compartirlos bajaría la serie ~5 min y `--jobs 4` ~3 [H derivada de M].
6. **La contención de `--jobs 4` es ×2,76 en los archivos caros**, no ×1,85; los rescates del MEF,
   ×5. Y dos tests de interfaz que solos tardan 2–6 s pasan de 60 en la suite por las ventanas vivas
   [M]. **Windows tarda ×1,98 lo que Linux 3.11** en esos archivos, y D-i queda explicada (×1,59).
7. **Dos medidas mías estaban mal y se corrigieron antes de usarlas**: el muestreador por hilo
   sobrestima Shapely, que suelta el GIL (81 % en Path, frente al < 1 % real), y la clave de cálculo
   repetido no veía repeticiones entre dos construcciones del mismo modelo (fecha de creación y hash
   del modelo). Las dos se detectaron con un control que debía dar positivo.
8. **Ocho anomalías confirmadas** con una sonda (§10), ninguna corregida. La más seria: **una
   variable aleatoria hidráulica no mueve ningún factor y nada lo dice** (regla 7). Además, el
   barrido de desembalse da otro factor al mismo nivel según cuántos niveles barre, las muestras con
   kh < 0 se evalúan sin aviso, un interruptor cambiado en el padre no llega a los trabajadores, y la
   CI de 0.1.377 está roja solo por una fuga de `locale` en Linux. **La revisión de la fase 3 añadió
   dos**:
   - A14: con las comprobaciones de superficie apagadas, los rechazos del paseo de Optimize no
     llegan a las notas (confirmada con una sonda: 3 rechazos sin nota; D379);
   - A15: en la ventana, el recolector podría frenar los cálculos grandes. Era una hipótesis, y
     medida se refuta: en K03, 33 liberaciones y solo una con algo que recoger.

## 2. Qué se midió y cómo

Todo con herramientas fuera del árbol, en el scratchpad de la sesión
`C:\Users\samue\AppData\Local\Temp\claude\c--Samuel-OpenGeoRock-Slip2d-OGR-Slip2D\2771176e-8ec9-4cca-82a7-aa63ef945fbd\scratchpad\computo\`
(copiadas al terminar a `referencias\Ejemplos\RS2_Verification Manuals\_auditoria\COMPUTO\bench\`).
Ningún módulo `ogr_*` se ha tocado: `git status` limpio durante toda la medida.

| Herramienta | Qué hace |
|---|---|
| `casos.py` | Los 22 casos del banco de pruebas (K01–K22), las escaleras (KG, KS) y las sondas de las anomalías (S1–S8). Cada caso carga sus modelos **en memoria**: un archivo se lee y nunca se escribe. |
| `correr.py` | Corre UN caso en un proceso nuevo: tiempos por parte (reloj y CPU del proceso), memoria (`GetProcessMemoryInfo` por `ctypes`), procedencia y huella. Modos: plano, `cProfile` y muestreo. |
| `huella.py`, `comparar.py` | La huella numérica y su comparación ruta a ruta (§3.2). |
| `contar/sitecustomize.py` | El gancho de conteo: entra por `PYTHONPATH` en **todos** los procesos, también en los trabajadores `spawn`, envuelve ~70 funciones del motor al importarse su módulo y escribe un archivo por proceso. Cuenta llamadas y **unidades de trabajo** (dovelas producidas, vueltas por dovela de los métodos, pasadas de `solve_branch`, elementos probados por `Mesh.locate`). |
| `muestreo.py` | Un perfilador estadístico de la biblioteca estándar: un hilo lee la pila del hilo principal cada 7 ms y reparte el tiempo por capa, por función interna y por función inclusiva. No guarda marcos (D310). |
| `perfil.py` | Resume un volcado de `cProfile` por capa, con recuentos exactos. |
| `orquestar.py`, `lotes.py` | Ejecutan los lotes de uno en uno, cada medida en un proceso nuevo, con el control de la máquina (§2.2) y el manifiesto `sha256` de los modelos. |
| `pool.py` | La anatomía del pool (§7). |
| `envoltorio_runner.py` | Corre UN archivo de test con el runner del proyecto y el muestreador, con `TEMP`/`TMP` redirigidos (§8). |
| `ci_linux.py` | Tiempo por archivo en Linux leído del registro de la CI (pasiva). |
| `analizar.py`, `agregar.py`, `tablas.py`, `proyeccion.py` | Identidades, agregados, tablas y la proyección a la suite. |

### 2.1 Reglas que se siguieron

- **Una medida a la vez**, en segundo plano, cada una en un proceso nuevo lanzado desde dentro
  de `OGR-Slip2D`; cada archivo de resultados publica `ogr_slip2d.__file__`, el commit y
  `git status --porcelain` (vacío en todas).
- **Ninguna opción `-X` ni variable de depuración**: Python 3.14 reenvía **todas** las `-X` a los
  trabajadores `spawn` (`subprocess._args_from_interpreter_flags`, `for opt in
  sorted(xoptions)`), no solo faulthandler [L]. El lanzador se niega a arrancar si las ve.
- **Contar en los hijos**: un parche hecho en el padre no llega a un trabajador `spawn`; por eso el
  gancho va en un `sitecustomize`. Los trabajadores sin consola son `pythonw.exe`, sin `stdout`:
  el gancho nunca imprime.
- **Controles del instrumento** [M]: el comparador caza tres diferencias inyectadas (una
  evaluación, un bit de una dovela, una clave que falta); el gancho cuadra el control sintético
  (las `evaluate_circle` sumadas en los 16 trabajadores de K01b = `attempts − focus_rejected` =
  2156); la huella con gancho, con muestreador y con `cProfile` es idéntica a la de la corrida
  limpia (§3.3).
- **Los modelos no cambian**: manifiesto `sha256` de los 24 archivos de modelo antes y después de
  cada lote, sin un cambio.
- **El reloj, como orden de magnitud**; la atribución, con recuentos. Las cifras de reloj son de
  una corrida salvo donde se dice; las de pools varían ±15–25 % entre corridas iguales [M].

### 2.2 Estado de la máquina

Sin intrusos en ninguna medida (el orquestador sondea cada 30 s: suite, banco, trabajos del API,
la ventana de OGR, `spawn_main` ajenos). Plan de energía «Equilibrado». Memoria libre al empezar,
~5,3 GB. De fondo, el Administrador de tareas (~14 % de un núcleo), VS Code (~13 %) y dos
servidores MCP de OGR inactivos.

**Sin ventana de consola** (así se lanzan aquí los procesos), el motor manda sus pools a
`pythonw.exe` (`ogr_slip2d.processes.child_executable`), como en la ventana y en los servidores
MCP. Las medidas de pool de este informe son con `pythonw.exe` salvo donde se compara (§7).

## 3. El banco de pruebas y su huella

### 3.1 Los 22 casos

Modelos versionados (`validacion/casos/`, constructores de los tests) donde los hay, y del banco de
verificación para cubrir lo demás. **Reducir una rejilla o cambiar un ajuste se hace en memoria**:
el manifiesto `sha256` de los modelos no cambió en ningún lote. Ruta del banco:
`referencias/Ejemplos/RS2_Verification Manuals/` (02 = estabilidad, 05 = aguas).

| ID | Modelo y entrada | Tamaño | Ejercita | Referencia externa | Reloj [M] |
|---|---|---|---|---|---:|
| K01 | Caso 001 (ACADS 1a), rejilla 6×6×11 → `run_analysis` | 396 círculos × B, S, G, Jc | serie, bajo el umbral | Giam y Donald (1989): 0,991 ± 2 % | 4,3 s |
| K01b | ídem, 7×7×11 | 539 × 4: 4 pools | el umbral | ídem | 5,3 s |
| K02 | Caso 001 tal cual | 5292 × 4 | pools por método | ídem | 38,5 s |
| K03 | ídem, 51×51×12, B + Jc | 31 212 × 2 | escala y transporte | ídem | 63,4 s |
| K04 | 02/078 `modelo_3b` | 13 671 nominales → 43 por método × 4 | 4 pools para 172 círculos | Duncan y Wright (2005): B 1,125 | 2,7 s |
| K05 | 02/062 `modelo_ru05` | 1440 generados × S + B | Ru, sismo, foco | Loukidis et al. (2003): 1,001 | 6,8 s |
| K06 | 02/106 `modelo_D1D2` | 22 599 × B, 8 trabajadores | pilotes de Ito-Matsui | Ito y Matsui (1975): 1,54 | 28,0 s |
| K07 | 02/097 | 6647 × B, O | desembalse multietapa | Duncan, Wright y Wong (1990): 0,823 | 81,7 s |
| K08 | 02/013 | 4851 × 4 | malla de presiones (TPS) | Pilot et al. (1982): 1,314 | 29,5 s |
| K09 | 02/020 `modelo_bloque` + Optimize | Block 5000, Spencer | Block y paseo | Chen y Shao (1988): 1,01–1,03 | 26,0 + 6,3 s |
| K10 | 02/019 + Optimize | Path hasta 5000 válidas | Path y paseo | Greco (1996): 1,40–1,42 | 82,3 + 12,2 s |
| K11 | 02/104 | enjambre 50×50 | enjambre | ACADS 1(d): 1,359 | 115,5 s |
| K12 | Caso 002, SA semilla 1234 + paseo | 300 pasos | Simulated Annealing | Yamagami y Ueta (1988): 1,327–1,348 | 9,1 s |
| K13 | Tutorial 20 (constructor del test) | Auto Refine no circular + Surface Altering | COBYQA, anisotropía | Tutorial 20: 1,268 | 63,9 s |
| K14 | 9 métodos en superficies fijas: seco, húmedo, 15 geosintéticos, anclaje pasivo y activo | 25–30 dovelas | los métodos | ACADS 2(b): B 2,204; dovela a dovela de la referencia | 1,0 s |
| K15 | 05/004, 2400 y 9600 elementos | Picard | permanente no saturado | Casagrande (1937), Harr (1990) | 1,3 + 7,2 s |
| K16 | 05/015, 600 y 2400 elementos | 40 pasos | transitorio | Terzaghi (1943) | 12,2 + 50,1 s |
| K17 | 02/010 `modelo_fem` (1441 elementos): 4 círculos + rejilla de 396 | B | presión del MEF | ACADS 5: 1,53 | 8,1 s |
| K18 | Tutorial 21 con cuatro normas + el desembalse de `test_transient_v130` | 150 elementos, 2 etapas + t = 0 | norma y transitorio | Smith (2006): 1,37 / 1,207 / 1,096; erfc | 5,5 + 13,1 s |
| K19 | 02/028, círculo dado, Global Minimum | N = 250 y 1000 | coste por muestra | Chowdhury y Xu (1995): 1,128 | 2,7 + 11,8 s |
| K20 | 02/036: Overall Slope N = 6, su gemelo en serie y Global Minimum N = 1000 con sensibilidad | rejilla 4851 | un pool por muestra | Li y Lumb (1987): 1,334 | 50,9 / 63,0 / 13,3 s |
| K21 | Morgenstern (constructor de `test_drawdown_sweep_v170`) | 5 niveles × 1420 | barrido | Morgenstern (1963): 1,20 | 13,5 s |
| K22 | Ej_1, rejilla de referencia, retroanálisis | 4851 | retroanálisis | identidad activa = pasiva; Ej_1 B 0,882889 | 6,6 s |

### 3.2 La huella

Recorrido genérico de dataclasses, objetos con `__slots__` y objetos planos, para que un campo
nuevo entre solo. Floats con `float.hex` (distingue −0,0 de 0,0); un `Material` por su nombre (el
paralelo devuelve copias por lote); los uuid4 de lo construido en código, por orden de aparición;
la lista de evaluaciones, con un resumen de 16 hex **por evaluación** (el comparador dice el
primer índice que difiere); la crítica, entera, con cada campo de cada dovela. **Las iteraciones y
los avisos van en la huella**: una optimización que los cambie no es bit a bit idéntica.

### 3.3 Las identidades [M]

| Comprobación | Casos | Resultado |
|---|---|---|
| Determinismo: `PYTHONHASHSEED` 1 frente a 2, procesos nuevos | los 14 cortos | **idéntico en los 14** |
| Serie igual a paralelo | los 12 de la lista (11 abren pool; K19 no) | **idéntico en los 12** |
| El gancho de conteo no cambia nada | los 23 (K01–K22 y K01b) | **idéntico en los 23** |
| El muestreador no cambia nada | los 23 | **idéntico en los 23** |
| `cProfile` no cambia nada | los 23, en serie | **idéntico en los 23** |

**95 comprobaciones, todas idénticas.**

Hasta hoy, la identidad serie-paralelo solo la exigía `test_parallel_search_v197`, sobre un caso
seco de Bishop; ahora está comprobada en doce modelos, con agua, soportes, desembalse, malla de
presiones, estadística y retroanálisis.

## 4. Dónde se va el tiempo

### 4.1 Tres instrumentos, y por qué no basta uno

- **`cProfile`, en serie** (rejillas con `parallel_search = False`): recuentos exactos; sus tiempos
  inflan el código hecho de muchas llamadas pequeñas (sobrecoste ×2–2,8 sobre la serie) [M].
- **El gancho en modo grueso**: tiempo inclusivo de funciones gruesas (por superficie, por pasada,
  por operación de Shapely), sin envoltorios por dovela [M].
- **El muestreador**: sin coste por llamada, **pero sesgado** [M]. Para leer la pila necesita el
  GIL, y Shapely 2 (y partes de NumPy y SciPy) lo suelta en cada operación: el muestreador cae
  justo ahí. En K10 (Path) atribuyó a Shapely el 81 % del tiempo; `cProfile` da 1 % y el gancho
  grueso, 1,0 s de 107 s (< 1 %: 5164 `buffer` y 52 186 `contains`). En el código Python puro (métodos, rebanado, `Mesh.locate`) los tres
  coinciden (K17: 87 % del muestreador, 86 % de `cProfile`, 7,55 de 8 s del gancho). Las tablas de
  capas de este informe son las de `cProfile`; el muestreador solo se cita donde concuerda.

### 4.2 Por capa (`cProfile`, en serie, tiempo propio) [M]

| Caso | Total (s) | Capas |
|---|---:|---|
| K01 rejilla 396 × 4 | 9,1 | métodos 42 %; C 21 %; rebanado 12 %; resistencia 10 %; geometría 4 % |
| K02 rejilla 5292 × 4 | 140,9 | métodos 43 %; C 21 %; rebanado 12 %; resistencia 10 % |
| K03 rejilla 31 212 × 2 (B, Jc) | 290,0 | C 21 %; métodos 20 %; resistencia 20 %; rebanado 17 %; geometría 7 %; cargas 4 %; proyecto 4 % |
| K06 pilotes | 154,3 | resistencia 21 %; C 20 %; rebanado 18 %; métodos 17 % |
| K07 desembalse | 447,5 | resistencia 21 %; C 20 %; métodos 14 %; rebanado 11 %; desembalse 7 % |
| K08 malla de presiones | 105,5 | métodos 41 %; C 20 %; agua 9 %; rebanado 7 % |
| K09 Block | 66,9 | métodos 65 %; C 16 %; proyecto 4 %; rebanado 4 % |
| K10 Path | 196,3 | métodos 66 %; C 16 %; proyecto 4 %; rebanado 4 % |
| K11 enjambre | 216,6 | métodos 68 %; C 16 %; rebanado 4 % |
| K12 Simulated Annealing | 18,6 | métodos 67 %; C 16 %; rebanado 5 % |
| K13 Auto Refine + Surface Altering | 208,8 | resistencia 49 %; C 23 %; métodos 12 %; SciPy 3 % |
| K15 permanente no saturado | 29,0 | MEF 31 %; C 29 %; búsqueda en la malla 21 % (del posproceso del banco); agua 13 % |
| K16 transitorio | 177,1 | MEF 42 %; C 33 %; agua 16 %; búsqueda en la malla 7 %; matrices dispersas ~0 % |
| K17 MEF + rejilla | 24,2 | **búsqueda en la malla 86 %** |
| K18 Tutorial 21 + desembalse v130 | 36,6 | **búsqueda en la malla 50 %**; C 16 % |
| K19 Global Minimum | 39,8 | **proyecto 28 %**; C 26 %; copias 9 % |
| K20 Overall Slope + GM + sensibilidad | 368,7 | resistencia 21 %; C 20 %; métodos 17 %; rebanado 16 % |

«C» es el tiempo dentro de funciones de C llamadas desde Python (`getattr`, `max`, `abs`,
`math.*`, `list.append`): pertenece a la capa que las llama.

### 4.3 Los puntos calientes [M]

| Caso | Función | Llamadas | Acumulado (s) | % del total |
|---|---|---:|---:|---:|
| K03 | `local_c_phi` (3 `shear_strength` por llamada: secante centrada) | 7 360 077 | 81,4 | 28 % |
| K03 | `slice_surface` | 64 106 | 120,4 | 41 % |
| K03 | `x0_resisting_pass` (Bishop/Janbu) | 174 921 | 90,2 | 31 % |
| K03 | `slice_forces` | 8 055 690 | 41,3 | 14 % |
| K03 | `ground_surface` (se rehace dos veces por círculo) | 126 533 | 8,2 | 3 % |
| K10 | `solve_branch` | 90 999 | 147,0 | 75 % |
| K10 | `moment_terms` (geometría invariante, en cada pasada) | 603 684 | 60,9 | 31 % |
| K11 | `solve_branch` | 119 992 | 168,9 | 78 % |
| K02 | `solve_branch` (Spencer y GLE) | 127 892 | 55,9 | 40 % |
| K13 | `local_c_phi` → `_model_for_angle` → `_rule_index`/`_child_model` (anisotropía) | 2,26 M → 6,7 M | 142,9 | 68 % |
| K16 | `assemble` + `element_fluxes` (en cada solución) | 1600 + 1600 | 53,3 + 37,6 | 51 % |
| K16 | `conductivity_tensor`, `shape_gradients` | 4,92 M cada una | 19,2 + 11,4 | 17 % |
| K16 | SuperLU (`gssv`) | 1600 | 3,6 | 2 % |
| K17 | `Mesh.locate` (549 elementos probados por consulta, de 1441) | 9552 | 7,55 (gancho) | 86 % |
| K19 | `Project._regions_cache_key` (14 M `round`) | 129 162 | 14,5 | 36 % |
| K07 | `Material.__init__`/`__setattr__` (un material nuevo por dovela no drenada y pasada) | ~2,4 M / 55,4 M | ~56 | ~12 % |

## 5. Lo que se recalcula igual [M]

1. **El rebanado, una vez por método.** Cada método repite la búsqueda entera
   (`analysis_runner.py:2166-2183`). En K03 (B + Jc) rebanar cuesta 127,6 s y resolver 116,6 s
   (gancho, sumado en los trabajadores): con dos métodos, la mitad del rebanado es repetida. En
   K02 (4 métodos), las tres cuartas partes.
2. **La linealización de la resistencia**: de 7,36 M llamadas a `local_c_phi` en K03, el 62 % se
   repite con los mismos bits de (dovela, material, σ) [M, muestra de 2,4 M]; en K10, el 32 %; en
   K17, el 72 %; en K13, el 75 %. En Mohr-Coulomb cada llamada son 3 evaluaciones (secante).
3. **Lo invariante entre iteraciones** dentro de los métodos: `x0_resisting_pass` recalcula
   `slice_forces`, `local_c_phi` y la trigonometría de cada dovela en cada iteración de Bishop y
   Janbu [L+M]; `moment_terms` rehace la geometría de la superficie en cada pasada de los métodos
   rigurosos sobre poligonales [L+M].
4. **La firma de las regiones**, fuera de `regions_frozen`: 129 162 reconstrucciones en 1250
   muestras de Global Minimum (36 % del tiempo) [M].
5. **La geometría por elemento del MEF**: `shape_gradients` y `conductivity_tensor` se recalculan
   para cada elemento en cada solución (4,9 M veces en K16), y los flujos de elemento se calculan
   en cada solución aunque solo se publique la última [M].
6. **El material de la etapa 2 del desembalse**, construido de nuevo por dovela y pasada, con su
   `uuid4` [M].
7. **Evaluaciones duplicadas**: 102 de 540 en Simulated Annealing (19 %), 31 de 2118 en el
   enjambre [M, §10].
8. **El trabajo de los tests**: §8.

## 6. El escalado [M]

**Dovelas** — los nueve métodos sobre dos superficies fijas, tres rondas alternas (mediana):

| Dovelas pedidas | Reales | Seco (ms) | Húmedo (ms) |
|---:|---:|---:|---:|
| 12 | 13 | 56,8 | 27,3 |
| 25 | 25 | 67,2 | 47,6 |
| 50 | 50 | 107,9 | 85,2 |
| 51 | 51 | 113,6 | 87,3 |
| 73 | 73 | 149,7 | 122,5 |
| 101 | 101 | 201,2 | 174,5 |
| 199 | 199 | 362,0 | 329,4 |

Lineal: ~1,6–1,8 ms por dovela para los nueve métodos y ~35 ms fijos de la puerta
(`evaluate_surfaces`: comprobaciones, copia preparada y una búsqueda configurada por método). Sin
nada cuadrático en dovelas. Un corte obligatorio añade una dovela a 12.

**Métodos** — el caso 001 tal cual (5292 círculos, pool):

| Métodos | Reloj (s) |
|---|---:|
| B | 3,8 |
| B + Jc | 10,7 |
| B + S + G + Jc | 35,0 |

Cada método repite su búsqueda entera, rebanado incluido. Janbu corregido cuesta casi el doble que
Bishop; Spencer y GLE juntos, 24 s.

**Muestras** — Global Minimum en el 028: 250 muestras 2,7 s y 1000 muestras 11,8 s: ~11,8 ms por
muestra y casi nada fijo.

**Elementos** — permanente no saturado (05/004): de 2307 a 9417 elementos, de 1,3 a 7,2 s (×5,6
por ×4 de elementos); transitorio (05/015): de 600 a 2444, de 12,2 a 50,1 s (×4,1). El mallado
es despreciable (0,05–0,27 s).

**Círculos** — en serie, Bishop, caso 001: 176 círculos 0,28 s; 396, 0,61 s; 4851, 7,8 s (§7): lineal.

## 7. El paralelismo

### 7.1 El punto de equilibrio en Windows [M]

Caso 001, un método, tres rondas en orden alterno, cada corrida en un proceso nuevo; por debajo de
400 se abre el pool bajando el umbral en el padre:

| Círculos | Bishop, serie (s) | Bishop, pool de 4 (s) | Pool / serie | Spencer, serie (s) | Spencer, pool de 4 (s) | Pool / serie |
|---:|---:|---:|---:|---:|---:|---:|
| 396 | 0,61 | 0,76 | 1,24 | 1,33 | 0,98 | 0,74 |
| 539 | 0,83 | 0,82 | 0,98 | 1,89 | 1,17 | 0,62 |
| 891 | 1,39 | 1,01 | 0,73 | 3,20 | 1,72 | 0,54 |
| 1331 | 2,07 | 1,29 | 0,62 | 4,94 | 2,66 | 0,54 |
| 2156 | 3,35 | 2,01 | 0,60 | 8,03 | 4,26 | 0,53 |
| 4851 | 7,82 | 4,44 | 0,57 | 18,86 | 10,02 | 0,53 |

Las tres rondas difieren un 3–5 % entre sí. **Con 8 trabajadores no se gana nada** (1331 Bishop:
1,57 s; 4851: 4,38 s Bishop y 9,39 s Spencer): la máquina tiene 4 núcleos físicos. **El techo es
~×1,9**, no ×4. El umbral de 400 queda en el equilibrio de Bishop y es prudente para Spencer.

En los casos del banco de pruebas, el paralelo por defecto frente a su gemelo en serie: K02 ×0,61,
K03 ×0,53, K05 ×0,59, K06 ×0,46 (8 trabajadores), K07 ×0,49, K08 ×0,61, K22 ×0,61; K21 (5 pools de
1420 círculos) ×0,96, y **K04 ×2,9 más lento** (4 pools para 172 círculos que el foco deja de
13 671 nominales: el umbral cuenta los nominales).

### 7.2 Qué cuesta un pool [M]

Arranque de un pool vacío en un proceso ya caliente, hasta que todos sus trabajadores han
contestado (mediana de 5):

| Trabajadores | `python.exe`, sin importar nada | `python.exe`, importando el motor | `pythonw.exe`, importando el motor |
|---:|---:|---:|---:|
| 2 | 0,15 s | 0,33 s | 0,36 s |
| 4 | 0,21 s | 0,43 s | 0,58 s |
| 8 | 0,31 s | 0,98 s | 0,94 s |

Cierre: 0,04–0,13 s. **El viaje de ida no pesa**: el proyecto ocupa 8–11 kB (242 kB con la malla
de 1441 elementos del 010) y se serializa en 0,2–3 ms por lote. **La vuelta sí**: cada evaluación
vuelve con sus dovelas, 8–28 kB, y el padre tarda 0,15–0,73 ms en deserializarla. Extrapolado a
una búsqueda: 106 → ~227 MB y 5,6 s en el padre; 097 → ~153 MB y 4,0 s; 010 con MEF → ~315 MB y
7,8 s.

**El padre como cuello de botella** [M]: CPU del padre durante la corrida (todos sus hilos), frente
al reloj: K03 24,0 de 63,4 s; K06 13,0 de 28,0 s; K07 11,8 de 81,7 s; K02 8,4 de 38,5 s. Y su
pico de memoria: **K03 4,2 GB**, K07 1,9 GB, K06 1,8 GB, K02 1,5 GB: retiene cada evaluación con
sus dovelas.

### 7.3 El recolector del padre [M]

`gc.callbacks` en el proceso padre (todos sus hilos), con el pool por defecto:

| Caso | Reloj (s) | CPU del padre (s) | Recolector (s) | Pausa máxima (s) | Objetos vivos al final | Pico (MB) |
|---|---:|---:|---:|---:|---:|---:|
| K02 | 35,3 | 8,0 | 1,65 | 0,58 | 1,8 M | 1517 |
| K03 | 63,5 | 22,4 | 3,98 | 0,47 | 5,2 M | 4300 |
| K03 en serie | 118,0 | 117,7 | 6,12 | 1,06 | 5,0 M | 3752 |
| K06 | 27,5 | 12,5 | 1,92 | 0,45 | 2,2 M | 1813 |
| K07 | 86,2 | 11,9 | 2,51 | 0,40 | 3,5 M | 1828 |
| K20 | 128,5 | 82,5 | 3,53 | 0,28 | 0,1 M | 789 |

Entre un 3 y un 7 % del reloj, recorriendo millones de objetos vivos para recoger ~30 por
colección: los resultados retenidos no son basura. Un efecto real y secundario.

### 7.4 La fracción paralelizable [M]

En las corridas en serie con `cProfile`, la parte de cada análisis que cae dentro de
`_run_centres` (lo que se reparte) es el 99,8–100 % en las rejillas (K01b, K02, K03, K05, K06,
K07, K08, K21), el 95 % en K20 (Global Minimum y sensibilidad van fuera) y el 90 % en K22 (el cierre
del retroanálisis corre en el padre). Por Amdahl, 4 trabajadores darían ~×3,99; se miden ×1,6–2,2.
Lo que se pierde es el coste de repartir (arranque, vuelta, padre) y que **cada unidad de trabajo
cuesta ~×1,9 más en los trabajadores** [M: en K02, ~120 s de cálculo en los trabajadores para lo que
la serie hace en 63,5 s], que se explica por la frecuencia de un procesador de 15 W con cuatro
núcleos cargados [H].

## 8. Los tests caros

### 8.1 Qué se midió

Los 41 archivos que salen de unir los de los 40 tests más lentos (19 archivos) con los 40 archivos
más caros del archivo de tiempos, **cada uno solo y en serie**, con el runner del proyecto
(`envoltorio_runner.py`: `runpy` como `__main__`, `sys.path[0]` = `tests/`), el muestreador en el
runner y en sus trabajadores, y el gancho en modo «tests» (entradas gruesas y una clave de las
entradas de cada búsqueda, análisis y solución transitoria). **`TEMP` y `TMP` redirigidos al
scratchpad**: el runner fusiona en `%TEMP%` los tiempos de cada archivo de una corrida filtrada, y
un tiempo solo habría descuadrado el reparto de la próxima `--jobs 4` de la propietaria y su lista
de lentos (comprobado al terminar: sus dos archivos siguen con la hora de su última corrida). Los
41 salieron en verde.

### 8.2 Solo frente a la suite [M]

**Los 41 suman 1907 s solos y 5644 s en la última `--jobs 4`: ×2,96**, no el ×1,85 que se venía
suponiendo (era la media de la suite entera, no la de los caros). Por archivo:

| Archivo | Solo (s) | En `--jobs 4` (s) | × | CI 3.11 (s) | Windows/Linux | Motor | Pools | Ventanas |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `test_annealing_inequality_v1119` | 276,7 | 753,4 | 2,72 | 122,2 | 2,26 | 98 % | 3 | 0 |
| `test_transient_v130` | 171,5 | 394,6 | 2,30 | 67,3 | 2,55 | 90 % | 0 | 14 |
| `test_rescue_fold_v1362` | 128,8 | 664,2 | 5,16 | 94,8 | 1,36 | 99 % | 0 | 0 |
| `test_slope_face_collinear_v1234` | 84,1 | 234,9 | 2,79 | 38,3 | 2,19 | 98 % | 0 | 0 |
| `test_overall_slope_v137` | 78,6 | 236,8 | 3,01 | 37,0 | 2,12 | 93 % | 0 | 0 |
| `test_groundwater_ops_v1200` | 70,2 | 194,1 | 2,76 | 30,0 | 2,34 | 95 % | 0 | 1 |
| `test_auto_refine_noncircular_family_v1264` | 67,5 | 292,2 | 4,33 | 42,4 | 1,59 | 99 % | 0 | 0 |
| `test_validation_cases` | 62,8 | 127,1 | 2,02 | 48,8 | 1,29 | 88 % | 8 | 0 |
| `test_focus_all_searches_v1129` | 57,8 | 161,4 | 2,79 | 25,4 | 2,28 | 95 % | 4 | 0 |
| `test_cancel_v1366` | 52,2 | 108,5 | 2,08 | 22,5 | 2,32 | 67 % | 11 | 10 |
| `test_multimodal_v1126` | 48,0 | 148,2 | 3,09 | 19,4 | 2,48 | 96 % | 1 | 0 |
| `test_drawdown_sweep_v170` | 46,9 | 76,7 | 1,64 | 23,8 | 1,97 | 86 % | 17 | 0 |
| `test_picard_loop_face_v1358` | 44,6 | 150,4 | 3,37 | 21,8 | 2,05 | 98 % | 0 | 0 |
| `test_surface_key_endpoints_v1237` | 44,0 | 123,2 | 2,80 | 19,8 | 2,22 | 89 % | 0 | 0 |
| `test_published_cases_v179` | 41,9 | 92,4 | 2,21 | 25,1 | 1,67 | 88 % | 3 | 0 |
| `test_optimize_wiring_v1104` | 40,1 | 92,3 | 2,30 | 17,9 | 2,24 | 95 % | 0 | 0 |
| `test_rescue_face_v1356` | 35,0 | 171,3 | 4,89 | 25,2 | 1,39 | 99 % | 0 | 0 |
| `test_cli_wiring_v177` | 34,8 | 87,0 | 2,50 | 14,1 | 2,46 | 75 % | 0 | 0 |
| `test_fos_chart_v1308` | 33,3 | 63,9 | 1,92 | 13,0 | 2,57 | 87 % | 0 | 3 |
| `test_transient_coupling_v1125` | 33,2 | 75,6 | 2,28 | 14,2 | 2,34 | 85 % | 1 | 1 |
| `test_reverse_curvature_v182` | 31,1 | 68,1 | 2,19 | 18,5 | 1,69 | 88 % | 5 | 0 |
| `test_names_and_headings_v1369` | 30,8 | 88,3 | 2,87 | 13,3 | 2,32 | 83 % | 4 | 3 |
| `test_transient_initial_result_v1307` | 30,4 | 67,4 | 2,22 | 11,3 | 2,69 | 85 % | 0 | 4 |
| `test_user_surfaces_v1157` | 29,6 | 82,1 | 2,78 | 13,7 | 2,16 | 81 % | 2 | 4 |
| `test_mcp_server_v1195` | 28,0 | 56,6 | 2,02 | 12,2 | 2,30 | 67 % | 3 | 0 |
| `test_surface_altering_v1260` | 26,3 | 69,2 | 2,63 | 10,7 | 2,46 | 98 % | 0 | 0 |
| `test_texts_spanish_v1370` | 25,4 | 51,0 | 2,00 | 9,8 | 2,59 | 74 % | 1 | 4 |
| `test_retention_alpha_v1278` | 24,0 | 73,4 | 3,05 | 8,9 | 2,71 | 92 % | 0 | 0 |
| `test_acads_validation_v178` | 23,8 | 52,9 | 2,22 | 12,9 | 1,85 | 89 % | 1 | 0 |
| `test_discrete_function_v1246` | 22,8 | 59,6 | 2,62 | 6,4 | 3,58 | 92 % | 0 | 0 |
| `test_picard_steep_curve_v1266` | 22,5 | 74,5 | 3,31 | 11,2 | 2,02 | 97 % | 0 | 0 |
| `test_slope_search_v117` | 22,4 | 50,3 | 2,24 | 11,2 | 2,00 | 90 % | 2 | 0 |
| `test_initial_factor_v1309` | 22,1 | 49,1 | 2,22 | 9,4 | 2,34 | 88 % | 0 | 0 |
| `test_sa_autorefine_v117` | 21,9 | 64,1 | 2,92 | 8,4 | 2,60 | 95 % | 0 | 0 |
| `test_noncircular_v115` | 21,6 | 69,4 | 3,22 | 9,8 | 2,20 | 97 % | 0 | 0 |
| `test_transient_face_rule_v1274` | 21,3 | 85,9 | 4,03 | 11,7 | 1,83 | 99 % | 0 | 0 |
| `test_janbu_wedge_v1142` | 20,1 | 53,8 | 2,67 | 7,5 | 2,69 | 96 % | 0 | 0 |
| `test_transient_celia_v1268` | 13,1 | 41,5 | 3,17 | 7,0 | 1,86 | 98 % | 0 | 0 |
| `test_dialogs_fit_more_v1326` | 9,3 | 52,1 | 5,58 | 12,3 | 0,76 | 67 % | 2 | 2 |
| `test_dark_theme_v1316` | 5,8 | 123,5 | 21,40 | 14,7 | 0,39 | 3 % | 0 | 3 |
| `test_language_saved_v1289` | 2,3 | 63,0 | 27,54 | 17,2 | 0,13 | 4 % | 0 | 3 |

Tres familias:

- **Cálculo puro** (la mayoría): 85–99 % del tiempo en el motor; en la suite, ×2,0–3,4 por la
  contención de cuatro tramos sobre cuatro núcleos que además bajan su frecuencia.
- **Los rescates del MEF** (`test_rescue_fold_v1362` ×5,2, `test_rescue_face_v1356` ×4,9,
  `test_transient_face_rule_v1274` ×4,0, `test_auto_refine_noncircular_family_v1264` ×4,3): en la
  suite pierden más que el resto [H: bucles largos de Python puro, los más sensibles a la frecuencia
  y a la caché compartida].
- **Interfaz con estado acumulado**: `test_dark_theme_v1316` 5,8 s solo y 123,5 s en la suite
  (×21); `test_language_saved_v1289` 2,3 s y 63,0 s (×27). Su coste en la suite no es suyo: es el de
  las ventanas que dejan vivas los archivos anteriores (cada cambio de tema recorre todos los
  widgets vivos: auditoría de la suite §4.4). Ninguna optimización del motor los mueve.

### 8.3 El trabajo repetido, contado [M]

En cada búsqueda, análisis, transitorio y solución de filtración, el gancho calcula una clave
canónica de sus entradas: el proyecto (`to_dict`, con los uuid numerados por orden de aparición) y
el estado de la búsqueda o del solucionador, con su generador aleatorio. Dos claves iguales en un
archivo son un cálculo que se repite con las mismas entradas.

**Dos fallos del medidor, cazados con un control antes de publicar** [M]: la primera clave incluía la
fecha de creación del proyecto (`settings.summary.date_created`), distinta en cada construcción, y
no podía ver una repetición entre dos construcciones del mismo modelo; dio 0 en
`test_overall_slope_v137`, donde la lectura del código contaba 261 búsquedas y ~119 distintas. La
segunda incluía `fem_mesh.notes.model_signature`, un hash calculado sobre los ids aleatorios, y escondía
todos los transitorios repetidos. Corregidas las dos, dos llamadas idénticas al ayudante del test
dan las mismas claves (control).

| Archivo | Cálculos repetidos | Tiempo repetido (s) | Del archivo solo |
|---|---:|---:|---:|
| `test_annealing_inequality_v1119` | 13 búsquedas | 155,1 | 55 % |
| `test_transient_v130` | 7 transitorios con sus búsquedas | 112,6 | 62 % |
| `test_slope_face_collinear_v1234` | 11 búsquedas | 41,4 | 49 % |
| `test_overall_slope_v137` | 142 búsquedas | 39,7 | 51 % |
| `test_surface_key_endpoints_v1237` | 69 búsquedas | 20,2 | 45 % |
| `test_drawdown_sweep_v170` | 7 búsquedas | 18,1 | 38 % |
| `test_reverse_curvature_v182` | 3 búsquedas | 17,7 | 57 % |
| `test_multimodal_v1126` | 7 búsquedas | 17,5 | 36 % |
| `test_user_surfaces_v1157` | 26 búsquedas | 16,2 | 57 % |
| `test_fos_chart_v1308` | 1 transitorio | 14,1 | 43 % |
| `test_transient_initial_result_v1307` | 8 soluciones de filtración | ~13 | 42 % |
| `test_published_cases_v179` | 1 búsqueda | 10,0 | 23 % |
| otros 7 archivos | | 18,8 | |

**494,7 s de los 1907 que suman solos** (26 %). La clave no ve los interruptores de módulo: las
parejas encendido/apagado de la regla 7 cuyo interruptor se lee después del tramo común
(`test_picard_loop_face_v1358`, 17,9 s; `test_rescue_face_v1356`, 15,3 s) aparecen como
repetidas y **no** se pueden compartir desde el test; tampoco las dos corridas de reproducibilidad
de `test_cli_wiring_v177`. Quedan fuera de la cifra. Las repeticiones **entre** archivos (el mismo
desembalse de v130 en cuatro archivos; Arai y Tagyo en dos; las tres configuraciones de Overall Slope en
dos) no se pueden compartir sin cachés entre archivos, que con `--jobs` caen en procesos distintos.

**Revisado en la fase 3** [L, archivo a archivo]: no todo lo repetido se puede compartir sin
debilitar un test. La clave tampoco ve los interruptores que se leen dentro del constructor de la
búsqueda ni las repeticiones hechas a propósito.
- **`test_annealing_inequality_v1119`:** los 155,1 s incluyen las corridas de semilla 77, que
  prueban la reproducibilidad, y las corridas «apagado» de la regla 7. Se comparten ~80 s.
- **`test_slope_face_collinear_v1234`:** casi todo son los lados «apagado» de la regla 7. Solo
  ~8 s, y reutilizando una corrida «encendido» dentro de un test de regla 7, que no se propone.
- **`test_surface_key_endpoints_v1237`:** sobre todo repeticiones con la clave vieja, que es el
  contraste del test. ~5 s.
- **`test_drawdown_sweep_v170`:** son niveles que el propio `run_drawdown_sweep` repite; no se
  pueden compartir desde el test.
- **`test_multimodal_v1126` y `test_user_surfaces_v1157`:** sus pruebas de reproducibilidad y de
  historial conservan su corrida (~12,5 y ~13 s).

**Lo compartible es ~295 s, no 495.**

### 8.4 Proyección a las tres corridas [H derivada de M]

Para cada candidato, el ahorro por archivo es su tiempo solo por la parte de las capas sobre
las que actúa (muestreador del runner más sus trabajadores) por la fracción que se estima que
quita (dicha con su porqué en `ahorros.py`); se lleva a `--jobs 4` con la contención medida de
cada archivo y se repite el reparto con la propia `partition` del runner (importada, sin
tocarla). **Calibrada**: con ahorro cero reproduce 68,6 / 34,7 / 12,7 min. Solo cuenta los 41
archivos medidos (~46 % de la serie): para los candidatos del motor es **una cota inferior**, porque los
otros 407 archivos también lo llaman.

| Candidato | Ahorro solo (s) | Serie (min) | `--jobs 4` (min) | `--fast --jobs 4` (min) |
|---|---:|---:|---:|---:|
| Hoy | — | 68,6 | 34,7 | 12,7 |
| Compartir todo lo repetido en los tests (cota superior) | 495 | 60,4 | 29,2 | 12,7 |
| Compartir solo lo que no debilita un test (fase 3) | 295 | 63,7 | 31,6 | 12,7 |
| Rebanar una vez para todos los métodos | 137 | 66,3 | 33,4 | 12,5 |
| Invariantes de los métodos | 128 | 66,5 | 33,6 | 12,6 |
| Localizador del MEF | 120 | 66,6 | 33,8 | 12,7 |
| Cachés del MEF | 48 | 67,8 | 33,9 | 12,7 |
| Un pool por corrida | 17 | 68,3 | 34,5 | 12,7 |
| La regla de anisotropía de cada ángulo, una vez | 12 | 68,4 | 34,3 | 12,7 |
| Congelar las muestras | 1 | 68,6 | 34,7 | 12,7 |

**Corregido antes de entregar** [M]: la primera proyección daba a «congelar las muestras» la capa
«proyecto» entera de los tests (34 s, 68,0 / 34,3 min). En los tests esa capa es sobre todo
`_point_in_polygon_verts` y `_material_in`, que congelar no quita; la firma de las regiones, que es
lo que se ahorra, suma ~1 s en los 41 archivos (tiempo inclusivo medido por función). Es una
ganancia de las simulaciones (K19), no de la suite. Las dos últimas filas salen de ese tiempo por
función; las demás, de la capa por la fracción que se estima.

**`--jobs 4` no suma por partes**: manda el tramo más lento. Compartiendo en cuatro versiones
separadas, cada una sola da:

| Versión | Serie (min) | `--jobs 4` (min) |
|---|---:|---:|
| Annealing | 67,3 | 34,3 |
| Familia del desembalse de v130 | 66,7 | 33,5 |
| Overall Slope | 67,9 | 34,3 |
| Rejillas, enjambre y superficies de usuario | 67,6 | 34,3 |
| Las cuatro juntas | 63,7 | 31,6 |

**`--fast` casi no se mueve**: lo caro vive en los 42 archivos de `tests/_slow.txt`, que `--fast`
deja fuera. Con lo compartible, solo dos de ellos bajarían de los 45 s que fija la lista en una
corrida con `--jobs 4`: `test_reverse_curvature_v182` y `test_fos_chart_v1308`, y
`test_user_surfaces_v1157` quedaría en el límite. La lista se podría reescribir (decisión de la
propietaria). `test_slope_search_v117` no está en la lista: ya corre en `--fast`.

## 9. Windows frente a Linux [M]

CI de 0.1.377 (corrida 40784710428), la primera sin búfer: tiempo por archivo de los tres jobs.

| | 3.11 | 3.12 | 3.13 |
|---|---:|---:|---:|
| Suite (suma de archivos) | 27,3 min | 39,5 min | 50,7 min |
| numpy / scipy | 2.4.6 / 1.17.1 | 2.5.4 / 1.18.1 | 2.5.4 / 1.18.1 |
| shapely / PySide6 | 2.2.0 / 6.12.0 | 2.2.0 / 6.12.0 | 2.2.0 / 6.12.0 |
| Veredicto | 6710/6712, 1 fuga | ídem | ídem |

- **Los tres jobs no son comparables entre sí**: 3.12 y 3.13 tienen las mismas librerías y 3.13
  tarda ×1,28 lo que 3.12 [M]; lo más probable es que cada job caiga en un servidor distinto [H].
  Solo se compara dentro de un job.
- **Windows solo frente a 3.11**, en los 41 archivos caros: **×1,98** en total (1907 frente a 961
  s), ×1,3–2,7 por archivo de cálculo [M]. La cifra de partida «Linux ×1,5» venía de comparar la
  suite entera en serie con estado acumulado; con los archivos solos, la distancia es mayor.
- **D-i, explicada**: `test_auto_refine_noncircular_family_v1264` tarda 67,5 s solo aquí y 42,4 s
  en 3.11 (×1,59), como el resto. El «120 s» de la auditoría de la suite era dentro de la suite.
- **El pool en Linux** sigue siendo [H]: `fork` en 3.11–3.13 no reimporta nada, así que su
  arranque es mucho más barato que los 0,4–0,6 s de `spawn` medidos aquí; en 3.14, `forkserver`
  por defecto (comprobado en la biblioteca estándar) importa una vez en el servidor y luego bifurca.
  El umbral de 400 no se toca para Linux sin medirlo antes en la CI.
- **Identidad entre plataformas**: imposible por construcción (libm de UCRT frente a glibc, SIMD
  AVX2 aquí frente a AVX512 en la CI, `sum()` compensado desde 3.12, versiones distintas). La huella
  solo vale antes y después en el mismo entorno.

## 10. Anomalías (regla 6: reportadas, no corregidas)

Salieron leyendo el código (la exploración de solo lectura del plan) y se confirmaron, o no, con una
sonda de la fase 1 (`casos.py`, S1–S8). Ninguna se ha tocado. Por gravedad:

**A1. Una variable aleatoria HIDRÁULICA no mueve ningún factor, y nada lo dice** [M, confirmada].
Una variable de tipo HYDRAULIC escribe `material.hydraulic` (`random_variables.py:182-189`), que
solo lee el solucionador de filtración (`transient_stability.py:125`; ningún camino del equilibrio
límite lee `.hydraulic`, comprobado con `grep`). Ninguna muestra vuelve a resolver la filtración
(`probabilistic.py:1375-1382`, `:1759-1766`). **Sonda S1**: Ej_1 con Gardner definido antes del
permanente del MEF; Global Minimum con N = 20 sobre el círculo de referencia.
- Con `ks` aleatoria (media 1e-5, desviación 0,5e-5): **un solo valor distinto en las 20
  muestras** (0,836185679621466), sin fallos y sin una nota.
- Con la cohesión aleatoria (control): 20 valores distintos, desviación 0,035.

El usuario ve un análisis probabilístico con dispersión nula y cree que el agua no influye. Es la
regla 7 (un ajuste que no hace nada). La interfaz y el API ofrecen la variable
(`random_variables.py:266-270`).

**A2. El barrido de desembalse configurado arrastra el generador aleatorio de un nivel al
siguiente** [M, confirmada]. `run_configured_drawdown_sweep` construye **una** búsqueda por método
y la reutiliza en todos los niveles (`analysis_runner.py:2468-2475`); Slope y el enjambre crean su
generador en `__init__` y no lo reinician al correr. **Sonda S2** (Morgenstern, Slope sembrada,
300 superficies):

| Nivel | Con 2 niveles | Con 4 niveles | Rejilla (control), 2 y 4 niveles |
|---|---:|---:|---:|
| 100 | 2,58448 | 2,58448 | 2,59767 / 2,59767 |
| 0 | 1,20249 | 1,20614 | 1,21472 / 1,21472 |
| desembalse total | 1,20381 | 1,20561 | 1,21472 / 1,21472 |

El mismo nivel da otro factor según cuántos niveles se barran antes (±0,3 %), y el nivel 0 y el
desembalse total, el mismo estado del agua, salen distintos dentro de una misma corrida. La
rejilla, sin azar, da lo mismo en las dos.

**A3. `_best_of_masses` se queda con la masa de menor factor aunque sea inadmisible**
(`search.py:1274-1278`), mientras `SearchResult.critical` prefiere las admisibles [M, confirmada,
efecto pequeño]. **Sonda S3** (Ej_2, círculos con varias masas, B y S, en serie): 9680 elecciones,
125 círculos con más de una masa válida, 351 veces se queda una inadmisible y **en 2 había una
admisible** (Spencer: 3,04 frente a 3,54; 7,21 frente a 24,2). Aquí no mueve la crítica (1,154),
pero el mecanismo puede esconder una masa admisible.

**A4. Un interruptor de módulo cambiado en el padre no llega a los trabajadores `spawn`**
[M, confirmada]. **Sonda S4**: Lowe-Karafiath en 539 círculos con `THETA_AT_BOUNDARY` cambiado en
el padre: **en serie 0,990756, en paralelo 0,991638**, que es el valor por defecto (102
diferencias de huella); sin cambiarlo, serie y paralelo idénticos. En Linux 3.11–3.13 (`fork`) los
trabajadores sí heredan el cambio: el mismo A/B daría otro resultado en la CI. Afecta a toda
herramienta del banco o test que conmute un interruptor sobre una rejilla de 400 círculos o más
(la memoria del banco ya aconseja `parallel_search = False` para esos A/B, pero nada lo impone).
**La propia sonda S3 cayó en ello**: su primera versión parcheaba en el padre una rejilla que se
fue a los trabajadores, y contó 0 llamadas.

**A5. `_element_kr` indexa kr por posición, donde `assemble` usa `kr[e.id]`**
(`seepage.py:1079-1090` frente a `:167-169`) [M, latente]. **Sonda S5**: en los 219 `.ogr` del
banco y de `validacion/` (2 con malla) y en dos mallas generadas (9417 y 2444 elementos), `id ==
posición` siempre. Hoy no muerde; si una malla llegara con ids no consecutivos, el continuador
leería otra kr.

**A6. La familia de inclinación prescrita llama «sin intervalo» a un intervalo que sí encontró**
(`modified_swedish.py:820-842`, `base.py:99-101`) [L]. Misma forma que D146 en Spencer/GLE.

**A7. Las muestras se saltan las comprobaciones de la corrida** [M, confirmada]. **Sonda S7**: una
variable kh de media nula con la dispersión por defecto (`default_dispersion`: 0,1 y ±0,3) da kh
< 0 en **99 de 200 muestras**; las 200 se evalúan, sin fallos y sin nota, cuando una corrida
determinista con kh < 0 se rechaza (`analysis_runner.py:255-266`).

**A8. Evaluaciones duplicadas** [M, confirmada]. **Sonda S8**: Simulated Annealing (K12),
**102 de 540 evaluaciones son duplicados exactos** (19 %), que gastan presupuesto
(`search.py:6400-6413`: en los extremos, 6 de los 8 movimientos son el mismo candidato); el
enjambre (K11), 31 de 2118, y su identidad de contadores no cuadra (`attempts − total_count` =
2500 − 2535 = −35, con 0 fuera del foco). Quitarlos del presupuesto cambia la búsqueda: sería un
cambio numérico.

**A9. El umbral del pool cuenta los círculos nominales** [M]: K04 abre 4 pools para los 172
círculos que el foco deja de 13 671 nominales y tarda ×2,9 lo que en serie (`search.py:2868-2871`).

**A10. Premisas de tests que no hacen lo que dicen** [L]: `test_acads_validation_v178` corre 5808
círculos y su comentario dice 4851; el caso de validación 001 dice 4851 y corre 5292;
`test_parallel_search_v197` dice 605 círculos y son 539, y es la **única** guarda del paralelo, sobre
un caso seco de Bishop (ahora comprobada en doce modelos, §3.3); ajustes que nadie lee en
`test_slope_face_collinear_v1234` (`max_iterations`), `test_noncircular_v115` (`num_vertices`) y
`test_cli_wiring_v177`.

**A11. Cachés con la clave incompleta, hoy inocuas** [L]: `_weak_bands_cache` sin clave
(`search.py:842-850`); la del estanque del MEF por `id(mesh)` (`ponded_water.py:97-102`); la de
anclaje heredada por las copias superficiales de nivel (`drawdown_levels.py:56`,
`support_integration.py:1247-1249`); la caja envolvente invalidada solo por External/Material (D02,
`project.py:228-250`). Menores: `_node_props` toma el primer elemento y no el promedio de su
docstring (`seepage.py:2195-2204`); kr^t calculado de dos formas (NumPy y `pow` de Python); semilla
fija en `correlate_pair`.

**A12. La CI de 0.1.377 sale en rojo solo por una fuga** [M]: los tres Python dan `Total: 6712
Passed: 6710 Failed: 0 Skipped: 2 Leaks: 1`, por `[LEAK] locale` en
`test_action_inventory_v1195` (`LC_CTYPE=C.UTF-8;LC_NUMERIC=C;…` → `C.UTF-8`): en Linux la
primera `QApplication` cambia el locale del proceso; en Windows no se ve. Con `os._exit`, el
código de salida ya es el veredicto, así que ese es el único motivo del rojo.

**A13. Del banco** [L]: `segundos` mide tramos distintos según el lanzador; etiquetas de versión
anteriores a su commit; `banco.py` (importado por `filtracion_comun.py`) mete el repositorio vivo en
`sys.path` (la clase de D187), lo que falsearía un A/B árbol contra árbol de K15/K16.

**A14. Con las comprobaciones de superficie apagadas, los rechazos del paseo de Optimize no llegan a
las notas** [M, confirmada; D379]. Con «Use checks for depth, elevation, concave surface»
apagado, el paseo evalúa con una copia superficial de la búsqueda (`optimize.py:424-428`).
- **Lo que se pierde:** los contadores de rechazo que suma el paseo (`_unsliceable`,
  `_outside_model`, `_on_model_edge`, los extremos y las bases sobre el terreno) se quedan en la
  copia. Las notas que se escriben tras la optimización (`search.py:1654-1681`) leen los del
  original.
- **Lo que sí llega:** las notas mismas, que van por la lista compartida.
- **Consecuencia:** es el silencio que v0.1.135 quiso evitar («the walk slices too, and a surface it
  could not slice is one it silently did not consider»). No mueve ningún número.

Salió en la revisión de la fase 3. **Sonda S9:** el caso 002 con Simulated Annealing (Spencer,
semilla 1234) y un paseo ancho (`step_fraction` 0,5, `move_endpoints`).
- Con las comprobaciones apagadas, la copia cuenta **3 superficies rechazadas por una base sobre el
  terreno**, el original se queda en 0 y la corrida no lleva ninguna nota.
- El factor es el mismo con las comprobaciones encendidas y apagadas (1,3279556614123529).
- Con el paseo por defecto no hay rechazos de estos tipos.

Es la familia de D255, que en 0.1.261 resolvió lo mismo para los trabajadores de la rejilla con
`_RUN_COUNTERS`.

**A15. En la ventana, el recolector podría frenar los cálculos grandes** [hipótesis de la fase 3,
**refutada** al medirla; ver al final de este punto].
- **El mecanismo:**
  - la ventana calcula en un `QThread` (`ogr_gui/background.py:63-91`);
  - cada recolección hecha fuera del hilo principal guarda su basura entera (`DEBUG_SAVEALL`,
    `ogr_gui/gc_guard.py:41-53`);
  - el temporizador de 2 s lanza entonces un `gc.collect()` completo en el hilo principal
    (`main_window.py:348-351`, `gc_guard.py:79-91`) siempre que haya algo guardado, que es casi
    siempre (~30 objetos por recolección, §7.3).
- **La cuenta:** con los 5,2 M de objetos vivos de K03 y ~320 ns por objeto, serían ~1,6 s de cada
  2 s con el GIL contra el hilo de cálculo.
- **Medido** [M] (`bench/ventana_gc.py`): lo que hace la ventana, sin la ventana. Es decir, la guarda
  instalada, el temporizador de 2 s llamando a `gc_guard.release` en el hilo principal, y K03 en un
  `QThread` mientras el hilo principal espera en un `QEventLoop`; frente al mismo camino sin guarda
  ni temporizador, en orden ABBA y cada corrida en un proceso nuevo.
  - En 67 s, **33 liberaciones y solo una con algo que recoger** (0,01 s); una sola recolección en
    el hilo principal.
  - Con guarda, 67,4 y 61,0 s; sin ella, 62,0 y 60,9 s. La primera corrida es la fría; las otras
    tres coinciden.
  - Factores idénticos en las cuatro.
- **Por qué no ocurre:** en un cálculo, las recolecciones fuera del hilo principal casi nunca
  encuentran basura, así que la guarda no tiene nada que soltar.
- **Lo que no cubre:** la basura con objetos de Qt que una sesión larga de la ventana deja en ciclos
  (lo que D310 vio en la suite) se soltaría una vez, no cada 2 s. Lo confirma la prueba a mano: una
  búsqueda grande en la ventana frente a su tiempo en el banco.

No abre ficha.

**No es anomalía, pero ata la identidad bit a bit**: con norma de diseño, la copia de análisis
pasa por `from_dict(to_dict())` y redondea las cargas del MEF a 9 cifras **a propósito**
(`test_tutorial21_eurocode_v1242.py:143-147`). Medido en K18 [M]: sin norma 1,3602751408313123,
con una norma de coeficientes 1 **1,3602751409214786** (6,6e-11 relativo; 99 diferencias de huella
en presiones y fuerzas de dovela). Una optimización que toque ese camino se compara dentro de él.

## 11. Qué no se midió

- **Linux, salvo el registro de la CI** (decisión de la propietaria): ni el coste de un pool con `fork`
  o `forkserver`, ni la huella antes y después en la CI.
- **La interfaz, en pantalla real.** **Medida después, en la fase 3** [M], offscreen y con la
  ventana de interpretación real (`bench/interfaz.py`). Sobre el resultado de Bishop de K03
  (28 759 evaluaciones):
  - el *hover* cuesta ~32 ms por movimiento dentro de una celda, porque recorre todas las
    evaluaciones antes de su filtro, y ~0,4 s por cambio de celda;
  - Add Query cuesta ~0,3 s por movimiento, porque redibuja siempre;
  - **guardar el HDF5 tarda 47,2 s, en el hilo de la ventana, tras cada Calcular** (198 MB): una
    ventana congelada casi un minuto. Construir los diccionarios de las superficies son solo 0,03 s;
    lo caro es crear el HDF5;
  - el hash del modelo cuesta 0,2 ms sin malla y 4,7 ms con los 1441 elementos de 02/010.

  Pintar offscreen no es pintar en pantalla: son cotas inferiores. Falta la prueba a mano.
- **El padre de una rejilla en paralelo, entero**: de sus 22,4 s de CPU en K03, el recolector se lleva
  4,0 [M] y deserializar ~9 [H: 0,15 ms por evaluación medidos en un lote × 62 424 evaluaciones]; el
  resto (~9 s) queda sin atribuir (avisos sobre las evaluaciones, propiedades que recorren la lista).
- **La frecuencia de la CPU**: la explicación de por qué cada unidad de trabajo cuesta ~×1,9 en los
  trabajadores (procesador de 15 W que baja frecuencia con los 4 núcleos cargados) es [H]; no se
  registró la frecuencia.
- **El +16 % sin atribuir desde 0.1.160** del banco: necesita árboles viejos; decisión de la
  propietaria.
- **El banco entero**: no se volvió a correr; el subconjunto de 13 problemas está en el banco de
  pruebas.

## 12. Lo que deja para la propuesta

Cifras de partida para la fase 3, medidas; las ganancias son [H] derivadas de lo medido, y cada una
se medirá con la huella y el A/B de su propia versión. Clases de identidad: **A**, no toca aritmética;
**B**, idéntica con condiciones; **C**, por medir bit a bit; **D**, cambio numérico.

**Revisada tras la fase 3**, cuando cinco diseños concretos y cuatro revisiones adversariales leyeron
el código de cada candidato:
- ninguna identidad bit a bit quedó refutada;
- las cifras de las filas 1, 4, 6, 10, 11, 12 y 14 ya son las corregidas;
- las condiciones de cada una, el orden de las versiones y las decisiones de la propietaria están en
  el plan de la fase 3.

| # | Candidato | Antes [M] | Esperado [H] | Clase |
|---|---|---|---|---|
| 1 | Localizador de puntos del MEF que respete el primer acierto | K17: 86 % en `Mesh.locate`, 549 elementos probados por consulta; K18: 50 % | K17 ×8 (8,8 → ~1 s); K18 −45 %; tests del MEF acoplado | B |
| 2 | Congelar las cachés en los bucles que hoy no lo hacen (Global Minimum, sensibilidad, Optimize suelto) | K19: firma de regiones 36 % del tiempo | K19 −30–35 % | B |
| 3 | El material de la etapa 2 del desembalse, sin construirlo por dovela y pasada | K07: ~12 % en `Material.__init__`/`__setattr__` y su `uuid4` | K07 −10 % | B |
| 4 | Un pool por corrida y no por método; umbral contando los círculos efectivos | K04: ×2,9 más lento con pool; 0,4–0,6 s por pool; un pool por método | K04 −60 a −65 %; −0,5 s por método extra en cada rejilla con pool. Riesgo: un Spencer con foco justo bajo 400 supervivientes, hasta +35 % | A/B |
| 5 | La vuelta del pool, compacta y sin pérdida (`__reduce__` de `Slice`/`LEMResult`, materiales por id) | 8–28 kB y 0,15–0,73 ms por evaluación en el padre; K03 padre 22 s de CPU, 4,3 GB | −15–30 % en rejillas grandes con pool; menos memoria | B |
| 6 | Rebanar una vez y resolver todos los métodos activos | rebanado 54 % del cálculo en K03 y K06; 32 % en K02 | En serie: −20 a −26 % con 2 métodos (el defecto), ~−24 % con 4. Con pool, una versión aparte de riesgo alto | B |
| 7 | Sacar del bucle lo invariante en F: Bishop/Janbu; `moment_terms`/`solve_branch`; la familia prescrita (tres versiones) | K03: `local_c_phi` 28 %, `x0_resisting_pass` 31 % acumulado; K10/K11: `moment_terms` 29–33 % | −15–30 % en métodos | B |
| 8 | MEF: geometría y conductividad por elemento cacheadas, curvas de kr ordenadas una vez, flujos solo al publicar | K16: `assemble` 13,2 s + `element_fluxes` 11,3 s de 56 s | K16 −30–40 %; rescates | B |
| 9 | MEF: reutilizar la matriz del transitorio saturado cuando (kr, diagonal, Dirichlet) no cambia | K16: 1600 ensamblados para 40 pasos | K16 −50 % [H] | B (C con `splu`) |
| 10 | Anisotropía generalizada: la regla de cada ángulo, una vez | K13: `local_c_phi` 68 % en `cProfile`, que infla las llamadas pequeñas; el muestreador da 22 % a `_model_for_angle`. `_rule_index`/`_child_model`: 6,7 M llamadas | K13 −5 % (la caché) y −6 % (el contexto, tras el Bishop no circular) | A/B |
| 11 | Repartir en procesos los bucles exteriores (Overall Slope primero; Global Minimum; niveles de desembalse) | K20: Overall Slope con un pool por muestra ×1,24 sobre la serie; Global Minimum 11,8 ms por muestra | Overall Slope −18 a −25 % en K20 (6 muestras para 4 trabajadores dejan dos ociosos); GM −40 % tras congelar, ~3 s por 1000 muestras | B |
| 12 | Repartir los candidatos independientes de las búsquedas no circulares; los paseos de Optimize sobre varios mínimos | K11: 91 de 110 s en 4 paseos independientes | K11 −35 a −40 %, si los paseos están equilibrados (sin medir). El umbral propuesto se cumple siempre con 2 paseos y abriría pools dentro de los conductores en serie | B |
| 13 | El recolector del padre: congelar lo acumulado | 3–7 % del reloj en rejillas grandes | −3–6 % | A |
| 14 | Reutilizar evaluaciones duplicadas, reproduciendo sus contadores | SA: 102 de 540 duplicadas | K12 menos del −15 % neto: cada acierto paga una copia profunda. Espera la decisión de D377 | B |
| 15 | Tests: compartir el cálculo repetido dentro de cada archivo | §8.3 | §8.4 | A |
| 16 | La interfaz: el HDF5 fuera del hilo de la ventana; el *hover* con los centros precalculados; Add Query sin redibujar si no cambia | Medido en la fase 3 (K03, offscreen): HDF5 47,2 s en el hilo de la ventana; *hover* ~32 ms por movimiento dentro de una celda; Add Query ~0,3 s por movimiento; el hash del modelo, 0,2–4,7 ms, no es problema | La ventana deja de congelarse ~47 s tras un Calcular grande; *hover* dentro de una celda por debajo de 1 ms | A/B |

**Descartado por la medida:** acelerar Shapely en las búsquedas no circulares (≤ 1 % del tiempo,
§4.1), la ida del pool (el proyecto pesa 8–11 kB por lote, §7.2) y más trabajadores (8 no mejoran a
4 en esta máquina, §7.1).

**Cambios numéricos (clase D), solo si la propietaria los decide:** quitar del presupuesto los
duplicados de Simulated Annealing; un generador nuevo por nivel de desembalse (A2); vectorizar kr con
NumPy; Cholesky u ordenación simétrica; salidas tempranas en la extensión de λ; tangente analítica de
Mohr-Coulomb (hoy, secante de tres evaluaciones); quitar el redondeo de la norma.

---

© 2026 Samuel Sáez López — UPCT — AGPL-3.0-or-later
