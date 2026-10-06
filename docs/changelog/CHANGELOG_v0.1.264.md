# OGR Slip2D v0.1.264

**La Auto Refine no circular no llegaba al 1,268 del Tutorial 20 de la
referencia (D250), y ya se sabe por qué: falla la optimización, no la
siembra.** El paseo Monte Carlo se queda atrapado con la rampa a ~36°, en
parte por un límite de ángulo cóncavo de 5° que no tiene fuente. Surface
Altering, que existe desde 0.1.260, llega a 1,2691 (+0,09 %). No cambia el
comportamiento del motor: es un cierre documental con un test contra el valor
publicado. Ningún número del banco se mueve (no hay ningún modelo con esta
búsqueda).

## 0. Lo que se encontró

### D250: el 4,9 % del Tutorial 20 es de la optimización

El Tutorial 20 (Generalized Anisotropic «Angle Range», Bishop, 25 dovelas)
publica 1,478 en circular y 1,268 en no circular. El no circular sale de la
Auto Refine no circular (10/10/10/50 %, 12 vértices) con *Optimize Surfaces*.
OGR daba 1,3303 (+4,91 %) y el Simulated Annealing, en el mismo modelo,
1,2680. La figura publicada es un tramo a ~10° por la estratificación débil
y una rampa de ~45° hasta la coronación.

Todo se midió **sin tocar el motor y en un mismo proceso**. La medida está
archivada en el banco: `02_…/_auditoria/P5_0264/medida_d250.py` y su JSON.

- **La siembra no es.** La búsqueda sin optimizar da 1,4379, y ninguna de sus
  2875 poligonales baja de 1,40.
  - Todas son polígonos inscritos en un círculo, que no pueden tener el
    quiebro «tramo + rampa».
  - Es el algoritmo documentado de la referencia, no un fallo de OGR: la
    familia solo puede salir de la optimización, allí como aquí.
- **El Monte Carlo es lo que no llega.** Desde la crítica, con la semilla del
  proyecto y las semillas 1–5, da **1,3069–1,3524**.
  - Alarga el tramo a 10°, pero deja la rampa a ~36°, repartida en seis o
    siete segmentos casi colineales.
  - Para empinarla moviendo un vértice cada vez hay que pasar por un quiebro
    cóncavo, y el límite de 5° (activado por defecto) lo prohíbe. Con el
    límite a 45°, el mismo paseo da 1,3059 / 1,2687 / 1,2740 con tres
    semillas, con escalones cóncavos en dos de ellas.
- **Surface Altering sí llega.** Mueve la superficie entera de una vez: desde
  la misma crítica da **1,2691 (+0,09 %)**, y desde otras cuatro partidas
  1,2609–1,2784.
  - Por la puerta normal (`run_analysis`, ajustes del tutorial) da
    **1,26915**.
  - Con 20 vértices da 1,28693, donde el Monte Carlo daba 1,3640.
- **El tutorial es de Slide 6.0**, de antes de Surface Altering. Su 1,268 salió
  de un paseo aleatorio cuyas reglas la referencia no publica, y Greco (1996)
  no está en `Documentacion_Guia`.

### Los caminos que no eran

- **Los extremos fijos (D264).** Con los extremos libres el paseo da
  1,3104–1,3385: la misma cuenca. D264 es real, pero aquí no es el mecanismo.
- **Insertar vértices.** La ayuda dice que la optimización inserta vértices,
  aunque no da la regla. Reiniciar el paseo con 23 vértices da 1,3258. Con 45,
  el rebanador rechaza la superficie: 44 segmentos y 25 dovelas.
- **Más semillas, *Explore All Vertices*, reiniciar.** 1,3265 y 1,3273: la
  misma cuenca.
- **Partir de otras semillas de la búsqueda.** Desde las diez mejores celdas
  (entrada, salida) el paseo da 1,3303–1,3779.
- **La superficie publicada, digitalizada.** Leída de la figura a ~8,9 px/m da
  1,3400 en OGR, pero eso no prueba nada: su primer tramo sale a −12,8°, fuera
  de la banda débil [−10°, 10°]. Con lectura a ±0,5 m, un segmento cambia de
  material.
- **La Path por debajo del publicado (−2,1 %).** Su crítica (1,24125) es válida
  y admisible: entra por la cara, sigue cinco segmentos a 10,0° exactos y sube
  por una rampa de 43° hasta (84,08; 50), detrás de la coronación. Es un
  mecanismo más largo que la referencia no publica: el 1,268 no es el mínimo
  global de Bishop en este modelo, sino lo que encontró la búsqueda del
  tutorial. Se reporta y no lleva ficha.

### El límite cóncavo, a D264

El 5° activado no tiene fuente: la ayuda actual describe la casilla sin dar el
valor, y la de 6.0 dice solo que la opción se estrenó ahí. La propietaria lo
sumó a D264 (misma clase: un valor por defecto del Monte Carlo sin fuente),
que se decidirá con un A/B de todas las filas Monte Carlo del banco.

### Qué no se cambió, y por qué

El Monte Carlo sigue siendo la técnica por defecto, también en la Auto Refine
no circular. Lo decidió la propietaria el 2026-10-05: ningún modelo se mueve
salvo que se elija Surface Altering. Cambiarlo solo aquí habría acercado el
número cambiando la técnica con la que el tutorial se hizo.

## 1. Lo que cambia

- **El docstring de `AutoRefineNonCircularSearch`** (`ogr_slip2d/search.py`)
  explica qué tiene que hacer aquí la optimización, con la medida.
- **`ogr_core/project/settings.py`:** un comentario junto a
  `optimize_max_concave_angle_*` dice que el 5° no tiene fuente y no es
  inerte (D264).
- **Ningún interruptor nuevo.** El comportamiento no cambia.

## 2. Tests

**`tests/test_auto_refine_noncircular_family_v1264.py`, 2 casos.** Usa el
modelo del Tutorial 20, el panel de búsqueda de su p. 20-11 y Surface
Altering elegido explícitamente, con un solo `run_analysis` compartido (~100 s).
- **El factor publicado:** |F/1,268 − 1| ≤ 1 %.
  - No hay «tres semillas» porque Surface Altering no lee la semilla y la
    Auto Refine es determinista.
  - La dispersión que existe es la de la partida, −0,56 a +0,82 % en cinco, y
    de ahí sale el 1 %.
- **La forma publicada,** «a section of sub-horizontal slip connected to the
  surface by a steep incline»: al menos el 30 % del ancho en segmentos de la
  banda débil (|α| ≤ 10°) y al menos un segmento de 35° o más.
- **No se fija el 1,33 del Monte Carlo.** Sería consagrar la trampa (regla 1).

**Discriminación** contra un `git archive` de 0.1.255 (2eb5ace), que no tiene
Surface Altering, así que el mismo modelo corre el Monte Carlo:
- **el caso del factor falla** (1,33028, +4,9 %);
- **el de la forma pasa también allí**, y es un hallazgo, no un hueco. El paseo
  ya encuentra el tramo por la estratificación y una rampa de más de 35°; lo
  que no encuentra es lo empinada que es (~36° frente a los ~45° de la
  figura). Ese umbral habría que leerlo de una figura digitalizada a medio
  metro, así que no se fija.

## 3. Banco

- **Censo** (`censo_auto_refine_nc_d250.py`): 230 modelos y **0** con Auto
  Refine no circular. Por pares: 170 rejillas, 4 Auto Refine circulares,
  35 Path, 12 Block y 9 Particle Swarm, como el censo del 2026-10-04.
  Ningún `construir_modelo.py` la declara.
  - La primera versión del censo contó tres scripts (007, 009, 019) que
    nombran `auto_refine` en un comentario y declaran Block y Path. Ahora se
    exige la asignación de las dos claves.
- **`d250()`** en el `verificar_cierres.py` de la raíz. Da CIERRE DOCUMENTAL
  si se cumple todo esto:
  - la medida archivada da el mecanismo «optimizacion»;
  - `D250_mecanismo.md` cita sus cifras;
  - el censo y el test existen;
  - en vivo, el tutorial con Surface Altering queda a ±1 % de 1,268.

  El Monte Carlo en vivo se informa y no decide: si D264 lo arregla, esta
  ficha no se reabre.
  - **Con 0.1.264:** CIERRE DOCUMENTAL. En vivo, Surface Altering da 1,2691 y el
    Monte Carlo 1,3303.
  - **Con el motor de 0.1.255** (mismo banco, mismo test): SIGUE ABIERTO,
    porque la rama de Surface Altering corre el Monte Carlo y da 1,3303.
  - Ojo al reproducirlo: `_tools/banco.py` mete el repositorio vivo en
    `sys.path[0]` al importarse, así que el árbol viejo hay que ponerlo delante
    DESPUÉS de cargar `verificar_cierres`. La primera corrida de esta
    discriminación habría medido el motor vivo.
- **D264** recibe la nota del límite cóncavo.
