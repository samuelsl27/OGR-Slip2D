# OGR Slip2D v0.1.235

**D92: el cálculo estadístico evalúa cada muestra con la búsqueda que
configura el proyecto, no con una montada a mano.** El análisis probabilístico
Global Minimum y la sensibilidad evalúan de nuevo, en cada copia muestreada
del modelo, la superficie crítica del determinista. Hasta 0.1.234 esa
evaluación usaba una `GridSearch` montada en `probabilistic.py` y en
`sensitivity.py` con el método y las comprobaciones de admisibilidad, y nada
más. No llegaban a ninguna muestra:

- los Surface Filters (Minimum Elevation, Minimum Depth);
- los Slope Limits;
- los objetos de foco;
- el modo sísmico;
- el Minimum Area del determinista (la búsqueda montada a mano llevaba
  `min_area = 0`).

Un círculo que define dos masas deslizantes se contestaba, muestra a
muestra, con la masa que el filtro había quitado al determinista. Es la
tercera puerta de un mismo fallo: 0.1.74 la cerró para las búsquedas y
0.1.108 para los métodos.

Cuarta versión de la tanda P5. El banco está fuera de git.

---

## 0. Lo que se encontró, y dónde

- **La medida de la ficha (0.1.154) sigue en pie.** Sobre la muesca del
  problema 22 (Fredlund y Krahn 1977), el mismo círculo da 3,35931 con la
  búsqueda configurada (Minimum Elevation 30 ft) y 1,38202 con la montada a
  mano. El círculo corta el terreno cuatro veces: el filtro tira la masa
  profunda, la de la capa débil, y deja la somera, la de la muesca.
- **Dos premisas del prompt habían caducado:**
  - el `_factory` de la interfaz que citaba ya no existe desde 0.1.201,
    cuando todo pasó a `run_configured_statistics`;
  - las líneas que citaba se habían movido, y estaban en
    `probabilistic.py:769` y `sensitivity.py:296`.
- **La búsqueda montada a mano ya llevaba la admisibilidad del proyecto**
  desde 0.1.202, por `_admissibility_kwargs`. Faltaba el resto.

## 1. El motor

- **`analysis_runner.build_evaluator(project, method_id, *, method=None,
  num_slices=None)`.** Devuelve una `GridSearch` que nunca se ejecuta, con
  todo lo que `build_search` da a una búsqueda. `method` permite pasar el
  método ya construido: los muestreadores lo construyen sobre el proyecto
  FACTORIZADO (`method_factory`), y el evaluador no puede sustituirlo por
  otro.
- **Por qué una `GridSearch` sea cual sea la búsqueda del proyecto:**
  evaluar una superficie DADA (`evaluate_circle`, `evaluate_surface`) es de
  `BaseSearch` e igual para todas. Las búsquedas difieren en cómo GENERAN
  superficies, y una re-evaluación no genera ninguna.
- **`_search_common`.** Es el diccionario `common` de `build_search`
  sacado tal cual: los mismos argumentos, en el mismo orden y con sus
  comentarios. La semilla se queda en `build_search`, porque es de las
  búsquedas que sortean. `build_search` no cambia de conducta.
- **Los dos muestreadores lo usan:**
  - `run_global_minimum` y `run_sensitivity` piden su evaluador a
    `build_evaluator`, con la importación perezosa de siempre;
  - `_admissibility_kwargs` queda sin uso y se quita;
  - `_evaluate_on` sigue como función global del módulo, porque la
    parchean tres tests;
  - `run_overall_slope` no cambia, porque ya usaba `build_search`.
- **Declarado, con Ky.** Con un modo de coeficiente sísmico crítico, la
  muestra elige entre las masas de un círculo la de menor Ky, como el
  determinista, y paga los cálculos de Ky que eso cuesta. El factor que se
  promedia sigue siendo el factor de seguridad (`result.fos`), porque Ky va
  en `details`. El comentario de `settings_warnings` sobre el sismo y la
  estadística decía «they build the same search per sample», y eso solo era
  cierto para Overall Slope. Ahora lo es también para las muestras.

## 2. Tests

**`tests/test_statistics_search_settings_v1235.py`**, 12 casos sobre la
muesca del problema 22, construida como la construye
`test_statistical_rebuild_v1154.py`. Ninguno fija un número impreso por el
programa:

- **Premisas:**
  - el círculo define dos masas;
  - con el filtro, la base más baja de la masa contestada queda por encima
    de 30 ft;
  - sin el filtro, por debajo.
- **La identidad:** cada muestra de `run_global_minimum` es
  `build_search(...).evaluate_circle` sobre su propia copia muestreada, a
  1e-12.
- **La regla 7:** la búsqueda montada a mano, sobre la misma copia, contesta
  otra masa, y ninguna muestra da su número.
- **La sensibilidad,** punto a punto, cumple la misma identidad.
- **Los ajustes de serie no mueven nada:** en el problema 22 publicado, sin
  filtros, la muestra es el número de la búsqueda montada a mano. Este caso
  pasa en los dos árboles, a propósito.
- **El evaluador lleva lo que lleva la búsqueda:** el número de dovelas, el
  Minimum Area, los dos filtros, las dos ventanas de Slope Limits, la
  admisibilidad (tracción, porcentaje y m-alpha), el modo sísmico y el foco,
  atributo por atributo y con valores que no son los de serie. Además, un
  método pasado como argumento es el que se usa, y un método desconocido no
  da evaluador.
- **Una sola puerta:** por AST, ningún `GridSearch(` en
  `ogr_core/statistics`.

**Discriminación** contra `git archive` 2b13661 (0.1.234): fallan **8 de
12**:
- 3 por comportamiento: la muestra da 1,3600 frente a 3,2136, la regla 7, y
  la sensibilidad da 1,2371 frente a 2,4002;
- 1 por la forma del código: quedan dos `GridSearch(`;
- 4 por símbolo.

Pasan las tres premisas y el caso de los ajustes de serie.

**Cambian a propósito, solo en el texto:**
- el docstring de `_search` y el párrafo «ONE HONEST LIMIT OF THE
  IDENTITY» de `test_statistical_rebuild_v1154.py`;
- el `_search` de `test_random_variable_target_v1164.py`.

Decían que la `GridSearch` montada a mano era la que construye el
muestreador, y desde esta versión no lo es. Siguen siendo la misma
evaluación en sus modelos, que no ponen filtros, límites ni foco: en el de
v1164 la masa mide unos 162 m² frente a un área mínima de 1. Sus asserts no
se tocan.

**Tests protegidos sin cambio de veredicto:** v1154, v135 y v137, y con
ellos los 452 casos de los 20 archivos que ejercitan las corridas
estadísticas.

## 3. El banco

- **A/B en memoria de las once corridas probabilísticas**
  (`_auditoria/P5_0235/ab_probabilistico_d92.json`). En el mismo proceso
  y con las mismas muestras, el lado A usa el evaluador de 0.1.234 (con
  `build_evaluator` parcheado) y el lado B el de 0.1.235. Se comparan
  60 000 muestras: **0 movidas**, los mismos índices y la misma PF en las
  once. El censo de configuración explica por qué: en todas, lo único que
  el evaluador nuevo lleva distinto es el Minimum Area (de 0 a 1,0), y sus
  masas son mucho mayores. Ninguna pone filtros, límites, foco ni sismo.
- **Re-corrida del lote con `correr_probabilistico.py`,** 3489 s con la
  suite en paralelo. Los once archivos pasan de 0.1.202 a 0.1.235.
  Comparados con la instantánea `Evaluaciones/0.1.234` por ruta (todo el
  JSON aplanado, sin `version_ogr` ni `segundos`): **189 números, 0
  distintos y ninguna clave sin pareja**. El 036 sigue en PF 2,240 % con
  Global Minimum y 3,000 % con Overall Slope.
- **D92 cerrada.** `d92()` sale CUBIERTO POR TEST. Comprueba cuatro
  cosas:
  - en vivo, que las cuatro muestras de la muesca son la búsqueda
    configurada, a 1e-12, y no la montada a mano;
  - el AST;
  - el A/B archivado: 11 corridas y ninguna muestra movida;
  - la discriminación.

  Con el motor de 0.1.234 (por `PYTHONPATH` a su `git archive`) sale NO SE
  SOSTIENE: en vivo, 0 de 4 muestras son la configurada.
- **Nota en el prompt largo de D88.** El «evaluador configurado» que pide
  su paso 1 ya existe. Su premisa no cambia con D92: repetida con 0.1.235,
  las muestras siguen en torno a 1,38 con el determinista en 3,3585 y sin
  notas, porque lo que cambia entre sus dos corridas es Composite
  Surfaces, no un filtro.

## 4. Lo que se reporta y NO se corrige

- **D93, ampliada.** Es de la misma clase y del mismo script. Con un
  círculo dado, `ejecutar_probabilistico.py` evalúa el determinista del 028
  con el método del registro (`registro[mid]()`), sin la configuración del
  proyecto, y las muestras con el configurado. Sobre los diez círculos:
  - en seis da el mismo número;
  - en el resto, hasta −0,0037 % (ej5 modo A), dentro de la tolerancia de
    convergencia del banco.

  El determinista del banco debería pasar también por `build_method`.
- **Lo que sigue igual.** `ogr_core/statistics` sigue importando de
  `ogr_slip2d` dentro de las funciones, como ya hacía con `build_method`.
  Esa dependencia hacia arriba no es nueva y esta versión no la amplía.

## 5. Verificación

- **Suite entera:** 5265/5265, en unos 72 min con las corridas del banco
  en paralelo (el reloj no es una medida).
- **Discriminación:** el test nuevo, copiado en un `git archive` de
  2b13661 y corrido con el runner de ese árbol, falla 8 de 12 casos.
- **Selección estadística:** 452/452 en los 20 archivos que ejercitan las
  corridas estadísticas.
- **Banco:** el A/B en memoria (0 de 60 000 muestras), la re-corrida
  completa (0 de 189 números distintos) y el ciclo de cierre de D92.

**Qué falta por probar:**
- **Un modelo del banco con filtros, límites, foco o sismo y estadística a
  la vez:** no hay ninguno. El efecto real de D92 solo está medido en la
  muesca sintética del test.
- **La rama Ky:** el evaluador elige la masa por Ky, pero no la cubre
  ningún test, porque el banco no tiene estadística con sismo.
