# OGR Slip2D v0.1.248

**D231a: Generalized Anisotropic gana la otra entrada de la referencia,
«Angle or Surface», con las juntas definidas por ángulo.** Hasta 0.1.247,
OGR solo tenía «Angle Range», tramos de ángulo cada uno con su material. La
otra entrada tiene tres cosas:

- un material base;
- juntas, cada una con su ángulo y su material;
- una función de transición entre la junta y la base según el desfase entre
  la base de la dovela y la junta: A y B, coseno o lineal.

Con varias juntas, responde la peor o la más próxima, y una casilla decide si
una base más débil toma el relevo. Las juntas por superficie llegan en
0.1.249 (D231b).

Séptima versión de la tanda D226–D232.

## 0. Lo que se encontró, y dónde

- **La ficha decía que el Tutorial 20 no da el peso específico. Sí lo da:**
  20 kN/m³ en las capturas de los tres materiales (pp. 20-4 a 20-6). Da
  también todo lo demás que hace falta: el contorno, Soil Mass (c = 5,
  φ = 30), Bedding (c = 0, φ = 20) entre −10° y 10°, sin agua, 25 dovelas,
  tolerancia 0,005 y Auto Refine 10/10/10/50 %. Publica Bishop 1,478 circular
  y 1,268 no circular.
- **El Tutorial 20 con 0.1.247, antes de tocar el código**
  (`_auditoria/P4_0248/tutorial20.py`):
  - circular, 1,4753 frente a 1,478 (−0,18 %): un ancla externa que se
    sostiene;
  - no circular, 1,3303 frente a 1,268 (+4,9 %).

  Para saber si el +4,9 % era del modelo o de la búsqueda, se pasaron las
  otras búsquedas no circulares por el mismo modelo
  (`tutorial20_no_circular.py`). Simulated Annealing da **1,2680**, el
  publicado; la Auto Refine no circular se queda en 1,3303 y con 20 vértices
  empeora (1,3640); la Path Search baja a 1,2412. El modelo está bien y la
  búsqueda no: es **D250**, abierta y NO corregida (§5).
- **La figura de las tres funciones de transición** (en la página de
  Generalized de la referencia) decide el coseno. Su texto («cosine 1 →
  base, 0 → joint») dice lo contrario que la figura y que su propio texto de
  la lineal. La figura dibuja una curva en S, plana en los extremos, que
  cruza la recta en 45°: sen²δ = (1 − cos 2δ)/2.
- **Un empate que decidía el redondeo.** La regla escrita para «Closest»
  dice que, en empate, gana la primera junta de la lista. El ángulo llega por
  radianes, y 30° vuelve como 29,999999999999996, así que con dos juntas a
  30° de la base la comparación exacta dejaba elegir al redondeo. Lo cazó el
  test. Un empate es ahora una diferencia menor que 1e-9°, la misma
  tolerancia que el modelo ya usa en los límites de los tramos.

## 1. El motor

- **`GeneralizedAnisotropic`** gana:
  - `input_type`: `angle_range`, por defecto y lo único de antes, o
    `angle_or_surface`;
  - `base` y `joints`, con un material (`material_id`) o un modelo propio,
    como los tramos;
  - `definition`, `mapping`, `joint_selection` y `use_base_if_weaker`
    (verdadero por defecto), fijados una vez por función como en el diálogo
    de la referencia.

  Las dos listas conviven, y `input_type` dice cuál calcula. Un archivo sin
  las claves nuevas es «Angle Range».
- **La resistencia** con «Angle or Surface», con las decisiones escritas en
  D231:
  - δ es el ángulo agudo entre la base y la junta;
  - t = 0 en la junta y 1 en la base: A y B como en Anisotropic Linear
    (Mercer 2012, 2013), lineal δ/90 y coseno sen²δ;
  - τⱼ = (1 − t)·τ_junta + t·τ_base, a la σ′ₙ de la base;
  - con varias juntas, el mínimo («Worst Case») o la de menor δ, y en empate
    la primera («Closest»);
  - después, si la casilla está marcada, min(τ, τ_base);
  - sin dovela, el mínimo de la base y las juntas.

  En los extremos (t = 0 o 1) solo se lee una resistencia, porque 0·τ no es
  0 cuando τ es infinita.
- **Un solo recorrido de los hijos.** `children_items()` y `with_children()`
  los usan todos los que tocan enlaces: la resolución y su regla, la
  importación de propiedades, la API (enlaces por nombre en `base` y
  `joints`, y el borrado de un material), los coeficientes de diseño (cada
  hijo por su categoría) y los `NEEDS_*`.
- **El agua y el desembalse son los del padre** («Angle or Surface uses the
  water properties of the parent material»). `linked_material_id` devuelve
  None con esta entrada, y `use_parent_water` es solo de «Angle Range».
- **Regla** `generalized_angle_or_surface_refusal`, preguntada por
  `strength_model_refusal`. Exige:
  - base y al menos una junta, con modelos que se puedan construir y que no
    sean otro Generalized;
  - un ángulo numérico en cada junta;
  - 0 ≤ A ≤ B ≤ 90 cuando la función los lee;
  - valores conocidos en las tres opciones.

  Rechaza las juntas por superficie hasta 0.1.249. Una entrada desconocida
  se rechaza también.

## 2. La interfaz y la API

- **Diálogo de materiales.** Un Generalized tiene ahora «Tipo de entrada».
  Con «Ángulo o superficie» aparecen:
  - el material base;
  - la definición, con «Superficie» visible pero deshabilitada;
  - la función de transición y la selección de juntas;
  - la casilla de la base más débil;
  - la tabla Ángulo de la junta | A | B | Material. A y B no se pueden
    editar con el coseno ni con la lineal, que no los leen (regla 7).

  Cambiar de entrada conserva las dos listas.
- **API y MCP.** `input_type`, `base`, `joints` y las tres opciones son campos
  del modelo. La base y las juntas enlazan por nombre (`"material": "Rock"`),
  y la nota de `use_parent_water` dice que con esta entrada no cambia nada.
  La guía del MCP lo explica.

## 3. Tests

**`tests/test_generalized_angle_or_surface_v1248.py`** (22 casos):

- **Identidades:**
  - una junta con A y B e hijos Mohr-Coulomb es Anisotropic Linear, en τ
    (1e-14) y en los nueve métodos (1e-12);
  - con funciones no lineales que se cruzan y sin la casilla, es Snowden con
    A1 = A2 y B1 = B2;
  - la lineal es A y B con A = 0 y B = 90.
- **A mano:** el coseno (extremos y mitad de la S); «Worst Case» y
  «Closest», con un empate exacto y otro a través de radianes; la base más
  débil; sin dovela, el mínimo.
- **Tutorial 20:** «Angle Range» sobre el círculo crítico de OGR queda a
  menos de 0,5 % de 1,478, y la entrada equivalente (junta a 0°,
  A = B = 10) da el mismo factor en los nueve métodos.
- **Regla 7:** la función, la selección y la casilla mueven el número. Los
  coeficientes de DA1-C2 dan F/1,25.
- **Regla, enlaces** (el material decide sobre la copia caducada, el enlace a
  nada, API por nombre y borrado con reasignación, importación), **agua del
  padre, archivo y diálogo.**

**Discriminación** contra `git archive` c3c625c (0.1.247), con el runner de
ese árbol: **21 de 22 fallan**, todos por símbolo, porque la entrada no
existía. El que pasa es el ancla del Tutorial 20 con «Angle Range», que ya
se sostenía.

## 4. El banco

- **Censo:** 0 de 230 modelos con Generalized.
- **El Tutorial 20 con la entrada equivalente** (`tutorial20.py
  --angle-or-surface`): la búsqueda Auto Refine circular entera da el mismo
  crítico que «Angle Range», bit a bit (1,4753385721353809, el mismo
  círculo), frente a 1,478 publicado. La referencia dice que las dos
  entradas pueden diferir de forma «negligible»; aquí no difieren.
- **A/B árbol contra árbol de todo el 02** (`_auditoria/P4_0248/ab_d231a.py`,
  c3c625c frente a este): 194 modelos, **0 de 1821 números distintos**.
- **Ciclo:** `verificar_cierres.py` entero, 218 cierres y 0 bajadas; prompts
  regenerados (43, con D250); auditorías con 0 ERROR en el 02 y en la raíz;
  instantánea `Evaluaciones/0.1.248`.
- **D231 sigue abierta** hasta 0.1.249 (las juntas por superficie), con la
  medida escrita en su ficha.
- **D250 abierta** en P5, al final.

## 5. Lo que se reporta y NO se corrige

- **D250: la Auto Refine no circular no encuentra la superficie del
  Tutorial 20.**
  - Da 1,3303 frente a 1,268, y con más vértices peor.
  - Simulated Annealing, en el mismo modelo, da 1,2680.
  - La Path Search baja a 1,2412, por debajo del publicado; no se ha mirado
    si su crítica tiene los extremos enterrados (D244).
- **Las juntas por superficie** se rechazan hasta 0.1.249.

## 6. Verificación

- **Suite entera:** 5504 de 5504, en 75,8 min, con la verificación de
  cierres en paralelo parte del tiempo.
- **Selección** de Generalized, anisótropos, Snowden, diálogos y tablas de
  materiales, i18n, catálogo, norma de diseño, Janbu, resistencia, MCP y
  propiedades: 581 de 581.
- **Test nuevo:** 22 de 22. Discriminación: 21 de 22 contra 0.1.247.
- **Banco:** el Tutorial 20 con las dos entradas, la sonda de las búsquedas
  no circulares, el A/B (0 de 1821) y el ciclo.

**Qué falta por probar:**
- **Las juntas por superficie**, que son D231b (0.1.249).
- **Un caso publicado de «Angle or Surface»:** ningún problema de los
  manuales ni ningún tutorial lo usa. El ancla es el Tutorial 20 a través de
  la entrada equivalente.
- **El diálogo en la aplicación real**, con un usuario: solo se ha probado
  sin pantalla.
