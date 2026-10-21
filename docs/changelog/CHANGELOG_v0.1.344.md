# OGR Slip2D v0.1.344

**La columna de suelo y la presión vertical de las cargas bajan del rebanador al núcleo
(`ogr_core.loads.overburden`), y su interruptor `SIGNED_SURFACE_PRESSURE` se muda con ellas, sin dejar copia
(D337, quinta parte).** Quinta versión de la tanda P8k.

## 0. Lo que se encontró

- **Seis importaciones del rebanador desde el núcleo.**
  - La tensión efectiva a lo largo de un soporte (`bond.py`) y el exceso de presión intersticial por carga
    (`excess_pore_pressure.py`) leen la misma descomposición de la columna de suelo que el peso de la dovela.
  - Para llegar a ella importaban el rebanador. Un comentario de `bond.py` ya lo decía: «deserves lifting into
    ogr_core».
- **El interruptor tenía dos lectores en dos capas.**
  - `SIGNED_SURFACE_PRESSURE` (v0.1.241, D232: una carga hacia arriba quita peso) vivía en el rebanador, y el
    núcleo lo leía como `slicer.SIGNED_SURFACE_PRESSURE`.
  - Una reexportación no comparte la mutación. Si el rebanador conservara una copia, apagarla no cambiaría
    nada, que es peor que no tener interruptor (regla 7). Por eso se muda entero.
- **La tabla de interruptores del banco lo habría perdido en silencio.**
  - `elegibilidad_critica_d155.INTERRUPTORES`, que reconstruye «el motor que escribió un archivo», hace
    `getattr(módulo, nombre, None)` y se salta lo que no encuentra.
  - Con la ruta vieja, en un árbol nuevo, el interruptor se habría saltado sin avisar. Ahora lleva las dos
    rutas, la nueva primero.

## 1. Qué cambia

- **`ogr_core/loads/overburden.py`** (nuevo): `_polyline_crossings_at_x`, `_column_weight`, `_material_key`,
  `_line_load_components`, `_surface_pressure_at`, `_surface_pressures_at`, `_summed` y el interruptor,
  palabra por palabra.
- **El rebanador** importa esos nombres de vuelta, los mismos objetos, y no conserva el interruptor.
- **`bond.py` y `excess_pore_pressure.py`** los importan del núcleo.

**Cambios deliberados en tests:**
- `test_upward_load_v1241` apaga el interruptor en su sitio nuevo;
- `test_core_layering_v1340` pierde seis entradas.

## 2. Tests

- **`tests/test_overburden_in_core_v1344.py`** (nuevo, 6 casos):
  - los nombres del rebanador son los objetos del núcleo;
  - **el interruptor tiene un solo sitio**, y el rebanador no lo tiene;
  - **el interruptor mueve los tres lectores** (regla 7): apagado, una carga hacia arriba vuelve a empujar en
    el peso de las dovelas, en la tensión de las cargas con B-bar y en la tensión efectiva junto a un soporte;
    encendido, en los tres quita;
  - **ningún interruptor del núcleo ni del motor se define en dos módulos**, para que una medida que apaga
    uno no apague una copia que nadie lee;
  - en un intérprete nuevo, la tensión junto a un soporte y la de las cargas se calculan sin importar el
    motor;
  - el censo pierde las seis entradas.

**Con el código de 0.1.343 fallan los 6.** El del intérprete nuevo enseña allí `ogr_slip2d` cargado, y el
de los interruptores, que el interruptor estaba en el rebanador.

## 3. Verificación

- **El test de esta versión**, 6/6.
- **Los vecinos:** 650/650: la columna, las cargas, los soportes y sus anclajes, el exceso de presión, la
  lámina de agua, los coeficientes de diseño, el rebanador y la carga hacia arriba.
- **Comparación A/B, árbol contra árbol.**
  - En los 44 modelos del banco con cargas o soportes se compararon, con 0.1.343 y con 0.1.344, las funciones
    movidas:
    - el peso de la columna y el techo de su banda en 41 abscisas y tres profundidades;
    - la presión de las cargas;
    - la tensión de las cargas con B-bar;
    - la tensión efectiva en 11 puntos de cada soporte.
  - Salen idénticos 12 254 valores, bit a bit (por `repr`). 168 de las presiones muestreadas son distintas
    de cero.
- **El coste.** No se añade trabajo: el rebanador llama a los mismos objetos función, ahora definidos en otro
  módulo, y el interruptor se lee igual, como global de su módulo. Por eso no se midieron tiempos: manda el
  razonamiento.
- **Suite entera:** 6382/6382, `EXIT=0`, 72 min.
- **Banco:**
  - raíz: `verificar_cierres.py` entero, 86 comprobaciones, 0 bajadas;
  - **manual 02**, las comprobaciones que tocan el código movido: D232 (el interruptor, apagado en su sitio
    nuevo: la que tira vuelve a empujar), D251, D166, D84, D172, D219 y D206. Todas se sostienen;
  - una corrida de esas sueltas escribió en el resultado del manual 02 una entrada «SIN CRITERIO» para
    D226d, que es ficha de la raíz. Se quitó a mano;
  - `INTERRUPTORES` lleva las dos rutas del interruptor;
  - D337, con su quinta parte apuntada;
  - instantánea `Evaluaciones/0.1.344`, prompts y auditorías con 0 ERROR.
- **Ningún número del motor cambia.**

## 4. Pendiente

- **0.1.345:** la linealización de la envolvente (`local_c_phi`) baja al núcleo (D337).
