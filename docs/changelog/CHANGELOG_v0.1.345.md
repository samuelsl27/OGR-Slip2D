# OGR Slip2D v0.1.345

**La linealización de una envolvente de resistencia a una tensión (`_local_c_phi`) baja al núcleo como
`local_c_phi`, y el método liga su nombre a esa función en vez de envolverla, porque la envoltura costaba un
3 % de cada cálculo de Bishop (D337, sexta parte).** Sexta versión de la tanda P8k.

## 0. Lo que se encontró

- **El c y el φ equivalentes de un soporte importaban la clase de Bishop.**
  `bond.equivalent_c_phi_at` llamaba a `BishopSimplified._local_c_phi` para linealizar la envolvente del
  material en un punto del soporte.
- **Envolver tiene un coste, y se midió antes de darlo por bueno.**
  - El plan era dejar en Bishop una `_local_c_phi` que llamara a la del núcleo.
  - La comparación A/B del solver entero no resolvió nada: los dos controles difirieron entre sí un 10 %.
  - Contar el trabajo sí. La llamada de más cuesta 0,25 µs de unos 4 µs por llamada, y Bishop hace 643 en una
    resolución de 160 dovelas (4,7 ms). Es **un 3 % de cada cálculo**, en el bucle más caliente del programa.
  - Por eso el método **liga** su nombre a la función del núcleo (`_local_c_phi = staticmethod(local_c_phi)`)
    y no la envuelve. Medido después, la diferencia por llamada es de −0,1 µs, que es ruido: es la misma
    función.
- **El docstring se va con el cuerpo.**
  - El de `_local_c_phi` dice dónde linealizan los métodos (D84) y las cifras de Perry (1993), que el banco
    lee.
  - Al ligar el nombre, un docstring en Bishop ya no tiene función a la que pertenecer. Pasa entero a
    `local_c_phi`.
  - La comprobación D84 del banco (manual 02) lo lee ahora donde esté, y acepta todavía el sitio viejo para
    un árbol anterior.

## 1. Qué cambia

- **`ogr_core.materials.strength_model.local_c_phi`** (nuevo): el cuerpo y el docstring de
  `BishopSimplified._local_c_phi`, palabra por palabra.
- **`BishopSimplified._local_c_phi`** es esa misma función. Los métodos y los espías de los tests y del banco
  siguen pasando por el nombre del método.
- **`bond.equivalent_c_phi_at`** llama a la del núcleo. Por eso un espía sobre el método ya no ve las
  linealizaciones de los pilotes y los anclajes helicoidales; el test lo dice.
- Los docstrings de `bond.py`, `helical_anchor.py` y `SliceContext.from_slice`, que nombraban la de Bishop,
  nombran la del núcleo.

## 2. Tests

- **`tests/test_local_c_phi_in_core_v1345.py`** (nuevo, 5 casos):
  - **la función del núcleo es el cuerpo viejo, cifra a cifra.**
    - El cuerpo de `_local_c_phi` de 0.1.343 está copiado literalmente en el test, sacado de su commit.
    - Se compara con la nueva en todos los modelos de resistencia que se construyen con sus valores por
      defecto, con siete tensiones (negativa, cero, unilateral junto a cero, ordinarias, grande), con y sin
      dovela de la que leer el contexto, y con y sin la tensión de sondeo.
    - En cada combinación dan el mismo `(c, tan φ)` o lanzan la misma excepción: más de 200 comparaciones.
  - el nombre del método es la función del núcleo, y su docstring lleva Perry, 0,944 y D84;
  - **un espía sobre el método ve todas las llamadas de una resolución de Bishop**, que es de lo que viven
    los espías del banco, y ya no ve la de un soporte;
  - en un intérprete nuevo, el c y el φ equivalentes de un soporte se calculan sin importar el motor;
  - `bond.py` no importa nada de arriba.

**Con el código de 0.1.344 fallan los 5.**

## 3. Verificación

- **El test de esta versión**, 5/5.
- **Los vecinos:** 454/454: Bishop y sus fuerzas de base, los anclajes helicoidales, los pilotes de Ito y
  Matsui, la envolvente en su propia tensión, m-alpha, la anisotropía, Hoek-Brown, las comprobaciones, el
  desembalse, los soportes y la resistencia.
- **Comparación A/B, árbol contra árbol.**
  - En los 44 modelos del banco con cargas o soportes, con 0.1.344 y con 0.1.345, se compararon la tensión
    efectiva y el c y φ equivalentes en 11 puntos de cada soporte.
  - Salen idénticos los 3234 pares (por `repr`), y nada lanza.
- **El coste.**
  - Con la envoltura: 0,25 µs más por llamada.
  - Ligado: −0,1 µs, que es ruido, y el mismo FS bit a bit.
  - La comparación del solver entero no distingue nada: los controles difieren entre sí un 10–12 %.
- **Suite entera:** 6387/6387, `EXIT=0`, 85 min.
- **Banco:**
  - raíz: `verificar_cierres.py` entero, 86 comprobaciones, 0 bajadas;
  - manual 02: D84 (lee el docstring en el núcleo), D172 (los espías sobre el método), D166, D219, D232, D251
    y D206 se sostienen;
  - D337, con su sexta parte apuntada;
  - instantánea `Evaluaciones/0.1.345`, prompts y auditorías con 0 ERROR.
- **Ningún número del motor cambia:** es la misma función.

## 4. Pendiente

- **0.1.346:** la estadística sube al motor, y D337 se cierra.
