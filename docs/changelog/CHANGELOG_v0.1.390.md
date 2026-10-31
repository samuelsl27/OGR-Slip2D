# OGR Slip2D v0.1.390

**Las pasadas de Bishop en una superficie no circular comparten lo que no lee F** (V11 de la fase 3 de la auditoría
del cómputo, `docs/audits/AUDITORIA_COMPUTO_v0.1.377.md`).

**Lo medido en K13** (Tutorial 20, Auto Refine no circular con Surface Altering, Bishop, con un material Generalized
Anisotropic), con una corrida por proceso nuevo y en orden ABBA:
- de 58,9 y 60,9 s a **35,3 y 36,3 s (−40 %)**;
- las 2876 evaluaciones, idénticas en las cuatro corridas (el mismo hash de factores, iteraciones, convergencia y
  admisibilidad).

Clase A: las mismas operaciones en el mismo orden. Lo demuestra la huella de los 23 casos, 23 de 23 idénticos a 0.1.377.

## 0. Lo que se encontró

- **Las pasadas de K13, contadas antes de dar la cifra,** como pedía el plan:
  - 6573 llamadas a `BishopSimplified._general_moment_fos` y 59 510 pasadas, 9,05 por llamada (la mayoría entre 8 y
    10);
  - 1,49 millones de visitas a dovelas;
  - 31,9 s de una corrida de 57,5;
  - ninguna con soporte.
- **Cada pasada lo recalculaba todo** en cada dovela: las cargas, la linealización de la envolvente (aquí, a través del
  modelo Generalized Anisotropic), la trigonometría, la carga del soporte y la suma de momentos entera. Solo m_α, Q y
  la normal de la base leen F.
- **Más ganancia que la del plan,** que estimaba −20 a −30 %: lo caro de cada dovela en K13 es la linealización
  anisótropa, que ahora se hace una vez por llamada en vez de nueve. Eso deja menos que ganar a V12 (el contexto
  anisótropo una vez por linealización), que hay que volver a medir antes de proponerla.
- **Las condiciones del plan, cumplidas:**
  - el memo y la geometría son locales a cada llamada, así que cada pasada de la envolvente y cada etapa de
    desembalse tienen los suyos;
  - las listas publicadas son nuevas en cada pasada;
  - una dovela que cruza un soporte pasivo, cuya carga es `t_passive / F`, se calcula entera en cada pasada, como en
    V6.
- **Lo que encontraron los tests y los mutantes:**
  - **Comparar el factor no basta:** puede tragarse un último bit movido en una dovela. Una normal con otra asociación
    (`q·sen α/F` en vez de `(q/F)·sen α`) pasaba todos los tests de resultado. El test que compara, pasada a pasada y
    dovela a dovela, lo que cada versión entrega a la suma de momentos la caza. Es la misma lección de V6.
  - **Un caso que creía cubierto no lo estaba:** la marca de las dovelas que entran sin resistencia exige una
    envolvente por el origen con tangente nula allí y una tensión estimada negativa. Las pasadas autoconsistentes de
    la envolvente vuelven a linealizar con la tensión de la solución y la borran. El caso se prueba con una llamada
    directa sobre la estimación de Fellenius, que sí marca seis dovelas.
  - **Lo que queda sin cubrir:** la comprobación de m_α colapsado en las pasadas que reutilizan el memo. Para saltar,
    m_α tendría que caer dentro de ±10⁻⁶ en una pasada posterior a la primera; en la práctica cambia de signo sin pasar
    por esa banda. Quitarla no hace fallar ningún test, y se mantiene igual que en la pasada completa.

## 1. Qué cambia

- `ogr_slip2d/methods/bishop.py`, `_general_moment_fos`:
  - **la primera pasada** guarda por dovela las fuerzas, el peso, la carga vertical con el soporte, cos α, sen α,
    `max(cos α, 1e-9)`, `sen α·tan φ`, el numerador de Q, la marca de resistencia nula, y la carga y la fuerza del
    soporte;
  - **las siguientes** forman `m_α = cos α + (sen α·tan φ)/F`, `Q = numerador/m_α` y la normal con las mismas
    operaciones de la forma de una línea;
  - **la geometría de la suma de momentos** (`moment_geometry`, v0.1.389) se construye una vez, al final de la primera
    pasada, donde estaba la suma entera.
- `tests/test_bishop_general_memo_v1390.py`, nuevo: 11 tests.
- El número, en los nueve sitios, y el contador de los dos README.

## 2. Qué se probó

- **`tests/test_bishop_general_memo_v1390.py`:**
  - **una resolución es la de 0.1.389, bit a bit.** El método viejo está copiado en el test, sin comentarios, y los dos
    resuelven las mismas superficies:
    - en seco;
    - con nivel freático y sismo;
    - con un soporte activo y otro pasivo;
    - con dos activos;
    - con una envolvente curva que las pasadas autoconsistentes vuelven a linealizar;
    - con un material Generalized Anisotropic;
    - con dovelas que entran sin resistencia;
    - parada por su tope de pasadas.

    Se comparan el factor, los contadores, el motivo, las tres columnas publicadas y cada detalle;
  - **lo que cada pasada entrega a la suma de momentos**, dovela a dovela y en hexadecimal;
  - **el trabajo contado:** frente a 0.1.389, el memo quita exactamente las linealizaciones de cada pasada después de
    la primera para cada dovela sin soporte pasivo, y la geometría se construye una vez por resolución.
- **Siete mutantes, seis cazados:**
  - las dovelas pasivas guardadas en el memo;
  - la marca de resistencia nula sin repetir;
  - m_α con otra asociación;
  - la normal con otra asociación;
  - la geometría rehecha en cada pasada;
  - la carga del soporte sin republicar.

  El séptimo, sin la comprobación de m_α colapsado en las pasadas repetidas, no lo caza ningún test (arriba).
- **Los tests de Bishop no circular, poligonales, convergencia, soportes y desembalse,** juntos: 687 de 687.
- **El banco:** la huella de los 23 casos frente a 0.1.377, 23 de 23 idénticos (`all identical`, código 0). K13, en
  su corrida de identidad: de 57,2 s (0.1.389) a 33,4 s. K12 y K14 no se mueven.
- **La suite entera con `--jobs 4`:** **6852 de 6852, `Failed: 0`**, sin `Leaks` ni `Chunks died`, en 24 min.

## 3. Lo que queda

- **V12** hay que volver a medirla antes de proponerla: V11 ya divide por nueve las linealizaciones de K13.
- **V13–V18,** cada una con su OK. La siguiente según el orden del plan es V12; si su nueva medida no la justifica, V13
  (los flujos del solucionador de filtración solo para el resultado publicado).

## Archivos

- `ogr_slip2d/methods/bishop.py`
- `tests/test_bishop_general_memo_v1390.py` (nuevo)
- `docs/changelog/CHANGELOG_v0.1.390.md` (nuevo)
- `README.md`, `README.es.md`
- `pyproject.toml`, `ogr_gui/main_window.py` y los `__init__.py` de `ogr_core`, `ogr_slip2d`, `ogr_fem2d`,
  `ogr_gui`, `ogr_cli`, `ogr_api` y `ogr_mcp` (el número)
