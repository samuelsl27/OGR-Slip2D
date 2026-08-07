# OGR Suite v0.1.34 — Changelog

**Lanzamiento:** 2 de agosto de 2026
**Desarrollador:** Samuel Sáez López — Estudiante de Doctorado, UPCT
**Licencia:** GPL-3.0

> **Fase P1 del análisis probabilístico: variables aleatorias.** Ya se
> puede declarar qué parámetro de qué objeto del modelo es incierto,
> muestrearlo con correlaciones y aplicarlo al cálculo. Es la pieza que
> conecta el núcleo estadístico de P0 con el motor de estabilidad.

---

## 🆕 `ogr_core/statistics/random_variables.py`

Una variable aleatoria identifica **qué parámetro de qué objeto** es
incierto. Categorías cubiertas, siguiendo las que enumera la referencia:

| Tipo | Parámetros |
|---|---|
| `MATERIAL_STRENGTH` | cualquier parámetro del modelo de resistencia (cohesión, ángulo de rozamiento, y los de los modelos no lineales) |
| `MATERIAL` | peso específico, peso saturado, Ru, presión constante, φ_b, valor de entrada de aire |
| `HYDRAULIC` | permeabilidad saturada y parámetros no saturados |
| `SUPPORT` | los parámetros declarados por cada tipo de soporte |
| `DISTRIBUTED_LOAD` / `LINE_LOAD` | magnitudes |
| `SEISMIC` | coeficientes kh y kv |
| `WATER_TABLE` | desplazamiento vertical de la freática |

**Decisión de diseño: descripción tipo *ruta*, no referencias a objetos.**
Una variable se define por (tipo, id del objeto, nombre del parámetro),
de modo que la definición sobrevive a la serialización y puede aplicarse
a una **copia** del proyecto. Esto último es requisito duro: una corrida
probabilística maneja miles de muestras y **nunca** debe tocar el modelo
del usuario.

El módulo resuelve además las tres convenciones distintas de
almacenamiento que conviven en el modelo — los parámetros de resistencia
viven en un diccionario (`strength.params`), los de material y soporte
son atributos, y las cargas son dataclasses — presentando una interfaz
única de lectura y escritura.

**Detalles que evitan errores silenciosos:**

- Fijar un coeficiente sísmico distinto de cero **activa** también la
  carga sísmica; de lo contrario la muestra se aplicaría y no tendría
  ningún efecto.
- El desplazamiento de la freática es un **offset** de media cero que
  mueve todos los vértices en bloque, conservando la forma de la
  superficie.
- `apply_sample` devuelve **cuántos parámetros se escribieron**, para que
  el motor pueda detectar una definición que ya no case con el modelo
  (por ejemplo, un material borrado desde que se definió la variable).
- Las variables que no son realmente aleatorias (rango nulo) se descartan
  del muestreo.

**`available_variables(project)`** enumera todo lo que *podría* ser
aleatorio, con la media ya fijada al valor actual y una etiqueta legible.
Es lo que alimentará el asistente de tres pasos de la referencia
(elegir objetos → elegir parámetros → definir estadística).

## ✔️ Validación

**Correlación c–φ** aplicada a través del muestreo real del proyecto:
pedida −0.600, obtenida **−0.597**, con las medias y desviaciones
marginales intactas (c: 15.000/1.910, φ: 25.000/2.908).

**Efecto real en el cálculo** — las variables no solo se escriben, mueven
el factor de seguridad en la dirección física correcta:

| Cohesión de Mat1 | FoS | | kh sísmico | FoS |
|---|---|---|---|---|
| 5.95 kPa | 0.7089 | | 0.00 | 0.8834 |
| 11.18 kPa | 0.8095 | | 0.10 | 0.7582 |
| 15.0 kPa | 0.8734 | | 0.20 | 0.6558 |
| 23.50 kPa | 1.0468 | | | |

**Aislamiento comprobado**: tras aplicar una muestra al clon, el proyecto
original conserva exactamente sus valores.

## 🔗 Persistencia

`Project.random_variables` se serializa en el `.ogr`, con round-trip
probado (y ausencia limpia cuando no hay variables definidas).

## 📊 Tests

**648 tests, 648 verdes** (+26 desde v0.1.33; suite 100 % desde v0.1.21).

Cobertura nueva (`tests/test_random_variables_v134.py`): enumeración por
tipo, cohesión y rozamiento presentes por material, media preajustada,
etiquetas legibles, hidráulicas solo si están definidas, freática solo si
existe; lectura y escritura de cada convención de almacenamiento,
autoactivación del sísmico, desplazamiento de todos los vértices de la
freática, y fallo limpio ante objetos o parámetros inexistentes;
**aislamiento del original**, monotonía del FoS con la cohesión y con el
sísmico, y recuento de parámetros escritos; correlación aplicada con
marginales preservadas, independencia por defecto, descarte de variables
deterministas; y serialización de la variable y del proyecto.

## ⏳ Siguiente

**Fase P2 — motor Global Minimum**: análisis determinista previo para
localizar la superficie crítica, N repeticiones del cálculo sobre ella
con las muestras generadas, y estadísticos de salida (media, desviación,
probabilidad de fallo, índice de fiabilidad y datos de convergencia).
Después P4 (sensibilidad), P3 (Overall Slope) y P5 (interfaz).

---

© 2026 Samuel Sáez López — UPCT — GPL-3.0
