# OGR Slip2D v0.1.395

**Los materiales de la etapa 2 del desembalse se copian de un prototipo, y el tope drenado lee el c′/φ′ de cada
dovela una sola vez** (V16 de la fase 3 de la auditoría del cómputo, `docs/audits/AUDITORIA_COMPUTO_v0.1.377.md`).

**Lo medido** en K07 (banco 097, desembalse rápido en varias etapas, Corps of Engineers, con Bishop y el
Ordinario), en serie, porque los parches no llegan a los trabajadores de un pool (D375), y con una corrida por
proceso nuevo:
- en orden ABBA, de 160,9 y 163,7 s a 158,7 y 148,8 s;
- en orden BAAB, de 165,7 y 162,5 s a **149,7 y 148,8 s (−9 %)**.

Las dos corridas de control del primer par difieren entre sí (10 s) tanto como el efecto, y por eso se repitió. En
el segundo difieren 0,9 s (las nuevas) y 3,2 s (las viejas). De media, en las ocho corridas, de 163,2 a 151,5 s
(**−7 %**). Como comprobación, el trabajo contado, medido en un mismo proceso y espalda con espalda:
- **el material:** el constructor cuesta 8,5 µs y la copia con su `Undrained` y su id, 6,0 µs. Son 2,5 µs menos por
  material, unos 6 s en los 2,36 millones de copias de K07;
- **el tope drenado:** cada lectura de c′/φ′ cuesta 2,0 µs, y dejan de hacerse unos 2 millones, unos 4 s.

En total, unos 10 s de ~160 (−6 %), que concuerda con el A/B. El hash de las 8399 evaluaciones
(factor y validez, por método) es el mismo en todas las corridas.

Clase B: los mismos valores en los mismos campos y en el mismo orden. Lo demuestra la huella de los 23 casos, 23 de
23 idénticos a 0.1.377.

## 0. Lo que se encontró

- **La puerta de medida,** K07 en serie (173 s con los cronómetros puestos):
  - `_undrained_slices` se llamaba 48 177 veces y construía **2 408 850 materiales de la etapa 2**. En cada llamada,
    todas las dovelas no drenadas compartían **un solo** material base;
  - `Material.__init__` se llevaba 23,5 s, unos 9,7 µs por material: el constructor asigna sus 26 campos a través de
    un `__setattr__` escrito en Python, y `uuid4` son 2,8 µs;
  - `_drawdown_material` y `_effective_c_phi` se llamaban 2,85 millones de veces cada una (5,4 + 1,6 s). Casi todas
    venían de las pasadas del tope drenado, que repetían por cada dovela la misma llamada sobre la misma dovela del
    mismo proyecto que ya había hecho la etapa 2.
- **Las decisiones de la propietaria:**
  - (a) y (b) van juntas, en esta versión;
  - cada material de dovela conserva su propio `uuid4`, como hasta ahora. `detach_materials` (D381) copia los
    materiales por su id, y un id compartido mezclaría materiales de resistencias distintas;
  - el `Undrained` de cada dovela se sigue construyendo con su constructor.
- **(a) El par c′/φ′:** la etapa 2 lo guarda por dovela al calcular la resistencia no drenada, y cada pasada del tope
  lo lee de ahí. Toda dovela del tope pasó por ese cálculo, porque está en `tau_by_index`, así que el par existe y
  es el de la misma llamada.
- **(b) Los materiales:**
  - el primer material de la etapa 2 de cada base, en cada llamada, sale del constructor;
  - los siguientes son copias superficiales de ese primero, con su `Undrained` construido y un id nuevo, sacado
    con la misma función que usa el constructor (`default_factory` del campo `id`).
  - **Por qué la copia es el material del constructor:** todos los demás campos los pone el constructor desde la
    misma base, o son valores por defecto, y ninguno es mutable. `Material` no tiene más `default_factory` que la del
    `id`, ni `__post_init__`, ni `__slots__`, ni ganchos de copia. Un test lo vigila.
  - El orden de las claves también es el mismo: la copia conserva el del primero, y reasignar una clave no la
    mueve.
- **Menos de lo que daba la puerta,** que eran 23,5 s en el constructor. La copia también cuesta (2,3 µs), y el
  `uuid4` por dovela se queda (1,8 µs). El plan esperaba −6 a −9 % en K07.
- **Un mutante no alcanzable, anotado:** quitar la comprobación de identidad de la base (`first[0] is not base`) no lo
  caza ningún test. Solo actuaría si se reutilizara un `id()`, y durante la llamada cada dovela mantiene viva su
  base, así que ningún `id` puede repetirse. Se queda como guarda, igual que en V14.

## 1. Qué cambia

- `ogr_slip2d/rapid_drawdown.py`:
  - **`_undrained_slices`:** el primer material de cada base se construye, y los siguientes se copian;
  - **`_NEW_MATERIAL_ID`:** la `default_factory` del campo `id` de `Material`;
  - **`rapid_drawdown_fos`:** `c_phi_by_index`, guardado en la etapa 2 y leído por el tope drenado.
- `tests/test_drawdown_stage2_materials_v1395.py`, nuevo: 6 tests.
- El número, en los nueve sitios, y el contador de los dos README.

## 2. Qué se probó

- **`tests/test_drawdown_stage2_materials_v1395.py`.** Como referencia lleva `rapid_drawdown_fos` y
  `_undrained_slices` de 0.1.394 copiados (sin docstrings ni comentarios) y ejecutados en una copia del espacio de
  nombres del módulo:
  - **un desembalse es el de 0.1.394, bit a bit:** el factor de cada etapa, las pasadas del tope, los dos cuernos de
    un ciclo y todos los números del resultado final;
    - con los tres procedimientos, sobre el círculo que converge y el que oscila de la presa de Pilarcitos
      (`test_rapid_drawdown_v168`);
    - y sobre una variante con un segundo material no drenado aguas arriba, con otro c′/φ′ y otra envolvente: las
      dovelas de un mismo círculo leen dos pares, así que el tope no puede tomar el de una dovela por el de otra;
  - **cada material de la etapa 2 es el del constructor:**
    - campo a campo y en el mismo orden de claves;
    - con su propio id, un `uuid4`;
    - con su propio objeto de resistencia;
    - y con las dovelas de alrededor sin cambios;
    - con bases intercaladas, repetidas y ausentes;
  - **la guarda sobre `Material`:** solo `id` con `default_factory`; sin `__post_init__`, `__slots__` ni ganchos de
    copia; y valores inmutables en los campos que el constructor de la etapa 2 deja por defecto;
  - **el trabajo, contado:**
    - el constructor, una vez por base y llamada;
    - `_effective_c_phi`, tantas veces con el tope drenado (Duncan-Wright-Wong, más de dos pasadas) como sin él
      (Lowe-Karafiath).

  El archivo entero tarda 1,2 s, con el arranque del intérprete.
- **Ocho mutantes,** siete cazados:
  - las copias con el id del primero;
  - con su resistencia;
  - un primero para todas las bases;
  - el primero compartido y no copiado;
  - ids no sacados como los saca el constructor;
  - el tope leyendo el par de otra dovela;
  - el par guardado al revés.

  El octavo, la comprobación de identidad de la base, no es alcanzable (ver §0).
- **Los tests de desembalse y de materiales,** juntos: 351 de 351.
- **El banco:** la huella de los 23 casos frente a 0.1.377, 23 de 23 idénticos (`all identical`, código 0), ninguna
  corrida contaminada. K07 en la corrida de identidad, con su pool, de 77,0 a 71,2 s frente a 0.1.394 (−8 %).
- **La suite entera con `--jobs 4`:** **6906 de 6906, `Failed: 0`**, sin `Leaks` ni `Chunks died`, en 20 min.

## 3. Lo que queda

- **V17 y V18,** cada una con su OK. La siguiente es V17: un pool por conductor, que toca lo paralelo y pide la serie
  entera de la suite.

## Archivos

- `ogr_slip2d/rapid_drawdown.py`
- `tests/test_drawdown_stage2_materials_v1395.py` (nuevo)
- `docs/changelog/CHANGELOG_v0.1.395.md` (nuevo)
- `README.md`, `README.es.md`
- `pyproject.toml`, `ogr_gui/main_window.py` y los `__init__.py` de `ogr_core`, `ogr_slip2d`, `ogr_fem2d`,
  `ogr_gui`, `ogr_cli`, `ogr_api` y `ogr_mcp` (el número)
