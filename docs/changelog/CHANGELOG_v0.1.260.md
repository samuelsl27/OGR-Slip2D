# OGR Slip2D v0.1.260

**Surface Altering: una segunda técnica para *Optimize Surfaces*, que mueve
los extremos por el terreno y rehace la superficie entera manteniéndola
convexa (D259). Monte Carlo sigue siendo la técnica por defecto y no cambia
ni un bit.**

## 0. Lo que se encontró

- **El 109 frente al manual (D243).**
  - El mecanismo publicado pasa por la cimentación, bajo el muro de gaviones.
    La rejilla circular del 108 lo reproduce sobre el modelo del 109 entre
    −0,6 % y −2,7 %.
  - La Block Search sobre las juntas no puede generarlo: es lo que dice su
    propia ayuda.
  - El paseo aleatorio de OGR (Greco 1996), desde la crítica de bloque
    (F ≈ 5), se queda en Bishop 2,16 y en Spencer y GLE 4,8, con los extremos
    fijos, que es el flujo del banco.
- **La referencia tiene otra técnica y la recomienda.** La página *Optimize
  Surfaces* ofrece Monte Carlo y Surface Altering, y dice: «Surface Altering
  is recommended — it is faster than Monte Carlo and able to find more
  critical surfaces».
- **El documento que la describe**, «Structure of Surface Altering», lo
  aportó la propietaria el 2026-10-05. Está guardado, con el informe de Powell
  (2009) sobre BOBYQA y un resumen, en
  `referencias/Documentacion_Guia/Optimizacion_de_superficies/`. Define cuatro
  pasos, cada uno resuelto con BOBYQA:
  - **A:** mover los extremos por el contorno, escalando el resto en
    proporción (ec. 1);
  - **B:** comprimir y expandir alrededor de pares de puntos interiores;
  - **C:** cambiar la curvatura con cotas estáticas y dinámicas que mantienen
    la superficie convexa (ec. 2, como Cheng 2003);
  - **D:** llevar puntos a la capa débil.
- **Lo que no dice la ayuda:** cuál de las dos técnicas va por defecto.

### Decisiones de la propietaria (2026-10-05)
- Monte Carlo sigue por defecto.
- Se implementan los cuatro pasos.
- Cada paso se resuelve con `scipy.optimize.minimize(method="COBYQA")`, de
  Ragonneau y Zhang, sucesor de los métodos de Powell, BSD-3, en SciPy desde
  la 1.14. No hay dependencias nuevas. **El suelo de SciPy sube de 1.11 a
  1.14**, porque COBYQA no existía antes.

### Lecturas del documento que se fijaron, cada una escrita en el código
- **Ec. 1, en lectura vectorial.** Los puntos interiores siguen el
  desplazamiento del extremo en sus dos componentes. La lectura literal, por
  un solo eje, crea un quiebro cóncavo en cuanto el extremo se mueve por una
  cara inclinada, y el documento quiere la superficie «convex and ordered».
- **Los extremos se mueven por longitud de arco del terreno**, así que
  pueden subir o bajar por una cara vertical (los tres casos de la figura 2).
- **Ec. 2: el rango dinámico manda sobre el estático,** como en el documento
  («the y-coordinate of point P_i will be changed such that upper dynamic
  bound is evaluated as zero»).
  - La primera versión daba prioridad a la cota estática, y una prueba de
    esquinas encontró que entonces la ec. 2 podía devolver superficies
    cóncavas (54 de 486 esquinas con cotas de 4).
  - Con el rango dinámico primero, el resultado es convexo para cualquier
    desplazamiento.
  - Un punto que la regla dinámica saca de su rango estático da una
    superficie que la evaluación rechaza.
- **La regla simétrica para la cota inferior**, LD < 0, es nuestra.
- **α = 0,5 por paso** (el documento no da valor). Tiene que ser menor que 1
  para que el denominador de la ec. 1 no cambie de signo.
- **Lo demás:**
  - 3 pares interiores por pasada;
  - 10 evaluaciones por variable;
  - radios de confianza de 0,1 y 1e-6 sobre la caja escalada.

  Son constantes del módulo, fijadas a priori.

### Hallazgos que se reportan y no se corrigen aquí (regla 6)
- **Surface Altering con Ordinary llega a superficies no físicas.** En el
  talud de la cuña de v1142, con todos los pasos, encuentra una V que baja
  desde el pie a −77,5° hasta el fondo del modelo y sube casi en vertical.
  Ordinary la da por buena con F = 0,30. Bishop y Spencer no tienen solución
  para ella, y Janbu la rechaza por m-alpha (−112). Ordinary no pasa el
  filtro m-alpha, por la decisión de D111. Con los extremos fijos, Monte Carlo
  se queda en 0,886. Ninguna fila del banco que declara Surface Altering usa
  Ordinary.
- **D260:** una crítica que una capa débil ha recortado no se optimiza, y no
  se dice.
- **D261:** Monte Carlo puede no terminar con tolerancia 0.
- **D258:** el cruce de las críticas entre métodos que la referencia
  documenta.

Las tres fichas quedan abiertas en P5.

## 1. Los cambios

- **`ogr_slip2d/surface_altering.py`, módulo nuevo:**
  - `GroundPath`, el terreno por longitud de arco;
  - los mapas puros: `stretch_from_end` (ec. 1), `stretch_about_pivots` y
    `slide_pair` (paso B), `static_bounds` y `curvature_map` (ec. 2);
  - `_Run`, con la mejor superficie jamás evaluada, la caché, el
    presupuesto y la penalización finita de las candidatas inválidas;
  - `alter`, el bucle de pasadas.

  Para cuando el presupuesto se agota, una pasada no mejora, la geometría no
  se mueve o se cumple la tolerancia de la referencia sobre las cinco últimas
  pasadas. Es determinista: la semilla no se lee.
- **`ogr_slip2d/optimize.py`:**
  - `OptimizeSettings.technique`, `OptimizeReport.technique` y las
    constantes `TECHNIQUE_*`;
  - una técnica desconocida se rechaza con la nota `error`;
  - el epílogo común (*snap shallow* y retorno) pasa a una función interna,
    `_finish`, y `optimize_surface` despacha a Surface Altering después del
    prólogo común. La rama de Monte Carlo no cambia.
- **Ajustes:**
  - `OptimizeTechnique` y `SearchSettings.optimize_technique`, con valor por
    defecto `"monte_carlo"`. Un `.ogr` sin la clave carga como Monte Carlo;
  - `optimize_settings()` la pasa al motor;
  - `rules.optimize_technique_refusal`, que llama `check_analysis_settings`.
- **Notas.** `_optimize_notes` añade una nota cuando se elige Surface
  Altering con *Step Reduction Factor* o *Explore All Vertices* cambiados. La
  nota de «All» conserva su texto exacto con Monte Carlo.
- **API.**
  - `CHOICES["search.optimize_technique"]`;
  - `optimize_summary` devuelve `technique`;
  - la guía del MCP y `docs/mcp/herramientas.md` lo explican.
- **Interfaz.** En el diálogo de ajustes de la optimización, un desplegable
  «Optimization Technique:». Con Surface Altering se desactivan *Step
  Reduction Factor* y *Explore All Vertices*, con un tooltip que dice por
  qué. Las cadenas pasan por `tr()` y tienen su entrada en español.
- **`pyproject.toml`:** `scipy>=1.14`.

## 2. Tests

**Test nuevo `tests/test_surface_altering_v1260.py`, con 25 casos**, cada uno
con su ancla externa:
- **Cuña de Coulomb**, con el pie fijo y solo el paso A:
  - la superficie sigue plana por el pie (5e-15);
  - su F es la forma cerrada en su propia salida (1e-12);
  - llega al minimizador de la forma cerrada, a 7,8e-16 en F y 3e-8 m en x,
    en 36 evaluaciones.
- **Talud infinito**, con Spencer y 25 dovelas: nunca por debajo de
  tan φ/tan β con la tolerancia de v1142 (2e-3), y por debajo de la partida.
- **Identidades de los mapas:**
  - la ec. 1 coloca el extremo exacto y conserva el orden y la convexidad;
  - la ec. 2 da una superficie convexa en todas las esquinas;
  - el deslizamiento del par conserva el orden;
  - `GroundPath` sigue los tres casos de la figura 2.
- **Los extremos**, en un modelo con un muro y dos ventanas, quedan sobre el
  terreno y cada uno en su ventana.
- **La forma:** x creciente y el techo de concavidad en todas las corridas.
- **Determinismo**, también con dos semillas distintas.
- **El presupuesto** con 1, 13 y 60 evaluaciones.
- **La junta plana de v1121**: la forma cerrada, a 2,8e-16. El paso D por sí
  solo lleva puntos a la junta y baja el factor. Con todos los pasos lo hace
  el C: es el C el que baja los puntos a la junta (0 enganches).
- **Monte Carlo explícito igual al de por defecto, bit a bit**, y el valor
  por defecto del proyecto y de un archivo viejo.
- **Regla 7 por la puerta de la búsqueda:** elegir Surface Altering mueve la
  crítica, sin subirla por encima de la de la búsqueda.
- **Regla 7 de lo que lee:**
  - la tolerancia: la floja para en la pasada 5 por tolerancia, y la
    estricta hace 10;
  - *Use checks*, con una profundidad mínima;
  - *Snap Shallow Surfaces*.
- **El contrato de partida**, el foco y las notas.

**Tests ampliados:**
- `test_optimize_wiring_v1104`: el campo llega al motor, el valor por defecto
  es el mismo a los dos lados, y un test nuevo del diálogo;
- `test_surface_options_v112`: el valor por defecto y la ida y vuelta;
- `test_api_settings_v1194`: los dos valores y el rechazo de «bobyqa».

**Discriminación** contra un `git archive` de 0.1.259 (1306fce): **fallan 31
de 96**, los 25 nuevos y los 6 añadidos. Pasan los 65 que ya estaban.

## 3. El banco

**La técnica se declara solo donde el manual la nombra:**
- el 103: «multi-modal Particle Swarm (PS) search and Surface Altering (SA)
  optimization»;
- los ejemplos 1 y 5 del manual 04: «Optimization: Surface Altering».

Cada uno lleva `optimize_technique = "surface_altering"` en su
`construir_modelo.py`, con la medida escrita al lado, y su `.ogr`
regenerado. `ejecutar_no_circular.optimizar` toma del modelo la técnica, y
solo la técnica. Ninguna otra fila del banco cambia.

**Medido antes en el mismo proceso**, con las dos técnicas y los `.ogr`
anteriores (`_auditoria/P5_0260/medida_sao.py`):

| fila | publicado | Monte Carlo | Surface Altering |
|---|---|---|---|
| 103, ratio 1,4, Spencer | 1,215 | 1,2209 (+0,49 %) | 1,2171 (+0,18 %) |
| 103, ratio 1,5, Spencer | 1,290 | 1,2963 (+0,49 %) | 1,2930 (+0,23 %) |
| 103, ratio 1,6, Spencer | 1,315 | 1,3378 (+1,73 %) | 1,3150 (−0,002 %) |
| 04 ej. 1, Bishop | 1,144 | 1,1436 (−0,04 %) | 1,1417 (−0,20 %) |
| 04 ej. 5, Bishop | 1,294 | 1,2995 (+0,43 %) | 1,2936 (−0,03 %) |
| 04 ej. 5, Janbu | 1,224 | 1,2241 (+0,01 %) | 1,2236 (−0,03 %) |

Cada optimización con Surface Altering costó entre 1,6 y 2,9 veces el tiempo
de Monte Carlo.

**El 103 re-corrido** (`correr_no_circular.py --forzar 103`), búsqueda más
optimización, las dos con Surface Altering:

| ratio | resultado | Δ |
|---|---|---|
| 1,4 | 1,2171 | +0,18 % |
| 1,5 | 1,2930 | +0,23 % |
| 1,6 | 1,3142 | −0,06 % |

Con Monte Carlo eran +0,46 / +0,63 / +1,72 %.

**Anomalía del banco, reportada y resuelta al regenerar.** Los `.ogr` de los
ejemplos 1 y 5 del manual 04 tenían tolerancia 0,005, y su
`construir_modelo.py` escribe 1e-4, la del banco desde D134. No se habían
regenerado desde antes: su `resultados.json` era de 0.1.159. Al regenerarlos
cambian la técnica, la tolerancia y siete claves de esquema con su valor por
defecto. Para separar los dos efectos se repitió la medida con 1e-4
(`medida_sao_04_tolerancia_1e-4_0.1.260.json`):

| fila | Monte Carlo, 0,005 | Monte Carlo, 1e-4 | Surface Altering, 1e-4 |
|---|---|---|---|
| ej. 1, Bishop | 1,14359 | 1,14359 | 1,14287 (−0,10 %) |
| ej. 5, Bishop | 1,29951 | 1,30049 | 1,29460 (+0,05 %) |
| ej. 5, Janbu | 1,22407 | 1,22404 | 1,22361 (−0,03 %) |

En el 103 solo cambian, además de la técnica, las mismas claves de esquema,
con su valor por defecto.

**Las filas de Monte Carlo no se mueven: A/B árbol contra árbol**
(`ab_mc_d259.py`, 0.1.259 frente a 0.1.260). Se optimizaron las críticas
archivadas del 15, el 16 y el 62 seco, con todos sus métodos, como hace
`ejecutar_no_circular`.
- **8 filas, 0 distintas bit a bit**: factor, vértices y número de
  evaluaciones.
- Además coinciden con su `fos_optimizado` archivado.
- De paso explica el coste: Monte Carlo para por convergencia entre 372 y
  2465 evaluaciones, y Surface Altering agota casi siempre las 4000.

No se re-corrió el banco entero, aunque el plan lo pedía: su coste es de unas
15 horas. Lo sustituye la identidad. La rama de Monte Carlo no cambia y la
técnica por defecto es Monte Carlo, así que ninguna fila sin la técnica
declarada puede moverse. Lo prueban el test 9, bit a bit, y este A/B.

**El 109 (D243), medido con las dos técnicas** (`exp_109_sao.py`). Desde la
crítica de bloque de cada método, con los ajustes del banco:

| método | publicado | Monte Carlo | Surface Altering |
|---|---|---|---|
| Bishop | 1,799 | 2,325 (+29 %) | **1,538** (−14,5 %) |
| Janbu | 1,610 | 2,421 (+50 %) | **1,445** (−10,2 %) |
| Spencer | 1,803 | 4,814 (+167 %) | **1,726** (−4,3 %) |
| GLE | 1,804 | 4,790 (+166 %) | **1,750** (−3,0 %) |

- **Surface Altering encuentra el mecanismo que dibuja la figura 109.2:**
  entra en la explanada del pie hacia x = 12–13, baja bajo el muro (y mínima
  3,9–4,3) y sale a la coronación hacia x = 21–23.
- **En Bishop queda a +1,5 % del 1,516 que rotula la figura**, por debajo de
  la tabla.
- **La rejilla circular sobre el mismo modelo da la tabla a −0,6 / −2,7 %.**
  La tabla y la figura no pueden salir de la misma corrida.
- **El manual no nombra la técnica para el 109**, así que en el banco sigue
  con Monte Carlo, y su cierre queda para decidir con esta medida.
- **El Monte Carlo de esta tabla parte de otra superficie** que el flujo del
  banco (que da 2,1635 en Bishop). Allí se reintentó desde la superficie sin
  redondear (D163); aquí, los extremos redondeados se llevan al contorno.

**Los probabilísticos de los ejemplos 1 y 5**, re-corridos con Surface
Altering (`correr_probabilistico_04.py`, con 100 muestras de Latin
Hypercube). PF y FS medio:

| fila | publicado | Monte Carlo, 0.1.202 | Surface Altering |
|---|---|---|---|
| ej. 1, Bishop | 9,0 % · 2,139 | 9,0 % · 2,1390 | 9,0 % · 2,1366 |
| ej. 5, Bishop | 25,0 % · 1,308 | 25,0 % · 1,3096 | 26,0 % · 1,3075 |
| ej. 5 correlado, Bishop | 21,0 % · 1,303 | 19,0 % · 1,3064 | 20,0 % · 1,3041 |
| ej. 5, Janbu | 30,0 % · 1,238 | 31,0 % · 1,2389 | 31,0 % · 1,2379 |
| ej. 5 correlado, Janbu | 25,0 % · 1,234 | 26,0 % · 1,2362 | 28,0 % · 1,2352 |

- **El FS medio** queda a menos del 0,2 % del publicado en todas las filas.
- **La PF se mueve de 1 a 3 puntos**, que con 100 muestras son de 1 a 3
  muestras que cruzan F = 1.
- **Costaron 4,3 veces más**: 9163 s frente a 2134 s, y 14 470 s frente a
  3287 s.
  - Dos corridas que pasaban de 2 horas las cortó el límite de las tareas en
    segundo plano y se relanzaron como procesos independientes, un modelo
    cada uno.
  - El lanzador gana `--modelo` para eso.

**El ciclo del banco:**
- `d259()`: CUBIERTO POR TEST;
- las verificaciones de cierres del 02 y de la raíz, con 0 bajadas;
- la instantánea, la retirada de D259, P5 podado y la cadena tachada;
- los prompts;
- las auditorías del 02 y de la raíz, con 0 ERROR;
- `--forzar`, y `--seco` igual al JSON clave a clave.

D243 sigue abierta: su cierre se decide con la medida del 109 de arriba.

## 4. Verificación

- **El test nuevo**, 25 de 25.
- **Selección** de los tests relacionados, 325 de 325: `surface_altering`,
  `optimize`, `surface_options`, `api_settings`, `settings_coverage`,
  `i18n_coverage`, `menu_reachability`, `action_inventory`,
  `focus_all_searches`, `auto_refine_noncircular`, `annealing`, `f3b_ops` y
  `mcp_server`.
- **Suite entera**, 5674 de 5674.

**Qué falta por probar:**
- **La prueba en pantalla del diálogo:** el desplegable de la técnica y los
  dos controles que se desactivan con Surface Altering.
- **El contraste de las cotas dinámicas de la ec. 2 con Cheng (2003)**,
  cuando llegue el artículo.
- **Un criterio de parada más práctico.** Surface Altering casi nunca para
  por la tolerancia de la referencia (1e-9 sobre cinco pasadas) y agota su
  presupuesto. Queda por medir si una tolerancia relativa da el mismo número
  con menos evaluaciones. No se cambia sin medirlo.
