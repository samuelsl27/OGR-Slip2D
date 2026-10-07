# OGR Slip2D v0.1.271

**El mallador ya no deja triángulos planos, y la filtración del 02-038 converge
por primera vez (D270).** Cada región se triangula con un Delaunay sin
restricciones. Donde varios nodos de su contorno quedan colineales sobre una
arista que es también del casco convexo, Qhull cierra el casco con triángulos
de área nula. Esos triángulos no eran un problema de precisión, sino de
**topología**: escondían nodos de la superficie del talud, que dejaban de
contar como contorno y nunca recibían la condición de cara de rezume. Ahora
el mallador los repara (interruptor `FLAT_TRIANGLE_REPAIR`), y los solvers
avisan si una malla guardada todavía los tiene.

## 0. Lo que se encontró

### El censo (puerta de medida C, `_auditoria/P6_0271/` del banco)

- **4 de 65 mallas tienen degenerados, y todos son planos de verdad.** Su
  forma 2A/L²max es de 1e-16 o menos (una aguja estaría hacia 1e-2):
  - 7 en la cara del talud del 05-007 y del 05-020 (la misma malla);
  - 16 en la cara del talud del 02-038, en sus tres alturas;
  - 7 en la presa 2 del 05-009 a 1500 elementos (fuera del banco).
- **La malla no era topológicamente válida.** V − E + F daba 0, −3 y −4, cuando
  tiene que dar 1.
  - La arista larga de un abanico plano es la que la malla toma como
    contorno, y tapa los nodos que hay debajo: 9, 72 y 43 nodos quedaban
    dentro de una arista de contorno.
  - Esos nodos eran 6 nodos de la superficie del 05-007 y 11 de la del
    02-038, que nunca recibían la condición UNKNOWN (cara de rezume).
- **En el 02-038, además, el plano entraba en la matriz.** Su determinante
  (~1e-13 m²) supera el 1e-15 absoluto de `shape_gradients`, así que entraba
  unas 1e15 veces más rígido que sus vecinos. En el 05-007, con
  coordenadas de centímetros, el determinante es ~1e-17 y el ensamblaje ya
  lo saltaba.
- **La hipótesis del prompt se quedaba corta.** Hablaba de un sistema mal
  condicionado. El efecto principal es de condiciones de contorno.

### El camino equivocado

El primer prototipo de reparación quitaba los planos de uno en uno y partía
el vecino a través de la arista larga. **No terminaba**: el vecino es a menudo
otro plano del abanico, y partirlo crea planos nuevos. Se colgó dos horas y
media en el 02-038. Lo que funciona es quitarlos todos a la vez y partir en
abanico, desde su vértice opuesto, el triángulo que quede con nodos de la
corrida dentro de una arista. En el banco no hizo falta ninguna partición.

### Lo que cambia (con la malla reparada)

**02-038, filtración** (tres alturas por cuatro curvas):

| | Antes | Ahora |
|---|---|---|
| Gardner, Gardner seco, van Genuchten (9 casos) | **no converge**: ~580 pasadas y rescate fallido | **converge**: 31–171 pasadas, sin rescate, 0 nodos sin asentar |
| Constante (3 casos) | converge, 31–33 pasadas | converge, 29 pasadas |

**02-038, Bishop.** La malla vieja reproduce al dígito los factores
archivados en 0.1.173.

| Altura | Slide | Antes | Ahora | Cambio |
|---|---|---|---|---|
| H61 | 1,621 | 2,2971 | 2,3398 | +1,86 % |
| H62 | 1,538 | 2,2704 | 2,3160 | +2,01 % |
| H63 | 1,407 | 2,2491 | 2,2926 | +1,93 % |

La discrepancia del 38 frente a Slide (+42 a +60 %) **no venía de aquí**. La
fila sigue NO CONCLUYENTE por su propia causa, y ahora sobre un campo
convergido.

**El 05-007 y el 05-020:**
- El 05-007 baja sus cargas entre un 0,04 y un 0,24 %.
- Su caudal pasa de −6,45 a −6,65 % frente al publicado.
- En el 05-020 solo se mueve la etapa de 208 s (−0,14 a −0,20 %).

**Su primera etapa (4,6 s) sigue sin converger.** El prompt la atribuía a los
planos, y no lo es: ficha nueva **D278**.

**Las otras 59 mallas del banco salen idénticas al bit.**

## 1. Qué cambia

### Mallador (`ogr_fem2d/mesh/generator.py`)

- **`_repair_flat_triangles`** se aplica al final de `generate_mesh`:
  - quita los triángulos con `shape_ratio` < 1e-10;
  - parte en abanico el que quede con nodos de la corrida dentro de una
    arista (en orden a lo largo de ella, y con la orientación antihoraria);
  - termina por construcción, y aun así lleva un tope.
- **`mesh.notes["flat_triangles_repaired"]`** se escribe solo cuando hubo
  alguno.
- **Interruptor `FLAT_TRIANGLE_REPAIR`** (alta en `INTERRUPTORES` del banco,
  (0, 1, 271)). Apagado, reconstruye las mallas de 0.1.270.

### Malla (`ogr_fem2d/mesh/mesh.py`)

- **`triangle_shape_ratio`**, que mide 2A/L²max, y
  **`DEGENERATE_SHAPE_RATIO`** = 1e-10. Es una medida RELATIVA: no depende del
  tamaño del modelo, al contrario que el 1e-15 absoluto sobre el determinante.
- **`Element.shape_ratio`** y **`Mesh.degenerate_elements()`**.

### Solver (`ogr_fem2d/solvers/seepage.py`)

- **Solo avisa; no salta los elementos planos.** Un `fem_mesh` guardado por
  una versión anterior viaja en el `.ogr`, y saltar un plano puede dejar un
  nodo sin elemento en su región. Si la malla los tiene, el resultado lleva
  `notes["degenerate_elements"]` y `notes["mesh_warning"]`, que pide
  regenerar la malla. También cuando el solve falla por ellos: la nota se
  pone antes de cualquier salida temprana.
- **Una malla sin planos no lleva nota.** El ensamblaje no cambia.
- **Dónde se ve el aviso:** en el resumen de campo de la API y en la ventana
  de interpretación de agua.

## 2. Tests

`tests/test_mesh_flat_triangles_v1271.py` (11 casos). Con 0.1.270 el módulo
no importa, porque `_repair_flat_triangles` no existía. Sus tres tests de la
malla del defecto fallarían allí por lo que midió el censo: V − E + F = −4, 43
nodos dentro de aristas de contorno y ángulo mínimo de 0°.

- **La presa 2 del 9 a 1500** (con `_dam2_project` del test de D124) cumple
  las identidades:
  - cada arista tiene uno o dos elementos;
  - todo nodo tiene elemento;
  - ningún nodo cae dentro de una arista de contorno;
  - V − E + F = 1;
  - las áreas suman el área de las regiones;
  - el ángulo mínimo pasa de 1°.

  **No se fija cuántos planos hace Qhull**, porque depende de su versión (la
  CI ya se puso roja una vez por diferencias de SciPy).
- **La reparación, sobre mallas hechas a mano** con las dos formas que toma un
  abanico plano:
  - planos fuera de los triángulos reales: se quitan;
  - un triángulo real con la arista larga y los nodos colgando de planos: se
    parte en abanico.

  Se comprueba la orientación antihoraria, y que una malla sin planos se
  devuelve tal cual.
- **Una malla sana sale idéntica** con el interruptor apagado y encendido.
- **El solver avisa** de los planos, también cuando el solve falla por ellos.

Suite entera: **5770 de 5770**.

## 3. Banco

- **`ejecutar_filtracion.py --banco 05 7 20 --forzar`.** En la comparativa de
  la raíz solo cambian filas del 7 y del 20, y ninguna de estado.
  - Las cargas del 05-007 con la malla gruesa reparada **se acercan a las de
    la malla fina**: en x = 0,4 pasan de 0,3867 a 0,3865 (la fina da 0,3857);
    en y = 0,7, de 0,8367 a 0,8347 (la fina, 0,8338). Es lo que se espera si
    la cara del talud queda mejor resuelta.
  - El caudal sigue en DISCREPANCIA: −6,65 % frente a −6,45 %.
- **El 02-038**, con `ejecutar_caso.py --filtracion` en sus tres modelos. Los
  `resultados*.json` dicen `filtracion.convergio: true` por primera vez desde
  que existen.
  - Bishop sube de 2,2971 a 2,3398 en H61, de 2,2704 a 2,3160 en H62 y de
    2,2491 a 2,2926 en H63.
  - **El factor sobre el círculo publicado pasa de 3,7654 a 4,7262 (+25,5 %).**
    Es el número que más se mueve. Ese círculo es somero, pegado a la cara
    del talud, donde los 11 nodos recuperan la condición de cara de rezume.
  - La fila sigue NO CONCLUYENTE.
- **El VC del 02** (`--seco`): 230 comprobaciones, 0 bajadas.
- **`d270()`** del `verificar_cierres.py` de la raíz (la carpeta del 02 va
  por ruta, porque el 02 no tiene `banco.json`):
  - el censo da 0 elementos con ángulo < 1°;
  - los tres `resultados*.json` del 02-038 dicen que la filtración convergió;
  - el test existe.

  Veredicto: **CUBIERTO POR TEST**. D270 retirada.
- **Fichas nuevas en P6:**
  - **D276**: el Picard del transitorio juzga el cambio relajado y publica la
    solución sin relajar;
  - **D277**: el permanente inicial del transitorio usa otros ajustes que el
    permanente del proyecto;
  - **D278**: la primera etapa del 05-020 no converge, y no la causan los
    planos.
