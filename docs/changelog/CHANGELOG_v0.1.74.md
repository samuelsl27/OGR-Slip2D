# OGR Slip2D v0.1.74 — diez ajustes que no hacían nada, y dos que estaban mal porque no lo hacían

## Qué se buscaba

Auditar los ajustes de *Project Settings* contra la referencia y
comprobar que cada uno tiene una función real. La auditoría completa está
en **`docs/audits/project_settings_v174.md`**; aquí va lo que se
encontró y lo que se cambió.

## El resultado: la regla 7 incumplida a escala

**Diez controles se guardaban, se editaban desde la interfaz, se
serializaban en el `.ogr` y no los leía nadie.** La página **Advanced
entera**. La página **Random Numbers entera**. La tolerancia de
convergencia y el tope de iteraciones de la página Methods.

Es exactamente el fallo de los coeficientes parciales de v0.1.52 →
v0.1.57 —el que motivó la regla 7— repetido a mayor escala y durante más
versiones. Y lo llamativo es que los métodos LEM aceptaban `tolerance`,
`max_iterations` e `initial_fos` **desde el día en que se escribieron**:
lo que fallaba era que todas las llamadas los instanciaban sin argumentos.

Nueve de los diez quedan cableados. El décimo,
`groundwater.excess_pore_pressure`, no tiene motor: es una feature, no un
cable, y va en v0.1.75.

## El hallazgo que merece recordarse

**Un ajuste que no hace nada tampoco tiene forma de estar bien.** Nadie
revisa el valor por defecto de un control que no cambia nada, así que al
cablearlos aparecieron dos defectos incorrectos que llevaban versiones
ahí sin que nada los delatara.

### 1. `check_tensile_stresses` estaba activado, y la referencia lo tiene apagado

La comprobación de tracciones estaba en `True` por defecto. Cablearla tal
cual habría activado el rechazo por tracción en **todo proyecto
guardado**, como efecto colateral de arreglar otra cosa.

Medido antes de decidir (regla 6): sobre la búsqueda en rejilla del caso
Ej1, la comprobación marca **149 de 3077 superficies como inadmisibles**
y el mínimo global **no cambia** (0.884517 con y sin). Es decir: activarla
es seguro en el caso validado, pero cambiar el defecto por la puerta de
atrás no lo es. El defecto pasa a `False`, como la referencia.

### 2. λ estaba limitado a ±1.25, y el caso validado necesita 1.4919

`min_lambda` / `max_lambda` valían ±1.25 mientras la rejilla λ que
Spencer y GLE recorren de verdad es ±1.5. No es una diferencia de
redondeo: **en el círculo de referencia validado, GLE converge en
λ = 1.4919**, fuera de ±1.25.

Honrar el rango almacenado habría recortado la búsqueda por debajo de lo
que necesita un caso que el proyecto valida contra un valor publicado —
un ajuste «cableado correctamente» que rompe una validación. Los defectos
pasan a ±1.5.

**Ambas migraciones son condicionales al valor antiguo**: quien escribió
deliberadamente otra cosa la conserva, porque a partir de ahora significa
algo. Y son seguras precisamente porque los valores almacenados nunca
llegaron a un cálculo, así que no expresan ninguna intención que
preservar.

## Cambios

### La rejilla λ se **recorta**, no se sustituye

La lista `[-1.5, -1.0, -0.6, …, 1.0, 1.5]` no es uniforme a propósito:
es densa cerca de cero, donde converge la mayoría de superficies, y llega
a ±1.5 porque algunas geometrías lo necesitan. Sustituirla por un
espaciado lineal sobre el rango del usuario habría tirado esa
calibración.

`LEMMethod.lambda_grid()` la **recorta** al rango configurado y garantiza
que los extremos se muestrean siempre —sin ellos, un rango estrecho puede
perder el cambio de signo que acota la raíz y reportar «todas las λ
divergieron» para una superficie con solución perfectamente buena—. Con
el rango por defecto devuelve **la lista idéntica**, así que ningún
proyecto guardado se mueve. Hay un test que lo fija literal a literal.

### Steffensen: mismo resultado, menos de la mitad de pasadas

Implementado como extrapolación de Aitken Δ² cada tres iterados, en
Bishop y en Janbu. Sobre el círculo validado, con tolerancia estricta:

| | FoS | iteraciones |
|---|---|---|
| Iteración plana | 0.8827814584 | 19 |
| Steffensen | 0.8827814585 | **7** |

Coinciden hasta **1.4e-11** — es la misma raíz. Y con la tolerancia por
defecto la diferencia es 9e-4, pero en la dirección que importa: la raíz
real es 0.882781, así que Steffensen (0.882815) queda **29× más cerca**
que la iteración plana (0.883730), con el mismo número de pasadas. Ese es
el argumento para dejarlo activado por defecto, y está fijado como test
para que tenga que seguir siendo cierto.

`aitken()` devuelve `None` cuando la segunda diferencia se anula, así que
activar la opción nunca puede hacer fallar una superficie que habría
convergido.

### Había dos semillas, y la visible no era la que se usaba

- `RandomNumberSettings.seed` tenía una **página entera** y no la leía nadie.
- `StatisticsSettings.seed` **no tenía ningún widget** y era la que el
  análisis usaba.

Peor: **ninguna de las cuatro búsquedas aleatorias recibía semilla**. Cada
una llevaba su propio valor arbitrario —42 en una, 1234 en otra, `None`
en dos más—, así que la promesa de la página de que una ejecución
pseudoaleatoria «da exactamente los mismos resultados» era falsa para las
búsquedas.

`ProjectSettings.analysis_seed()` es ahora la única respuesta. La página
Random Numbers decide; `statistics.seed` sobrevive como override
explícito. Rejilla y refinado automático no reciben semilla: enumeran sus
superficies, no sortean nada, y darles un argumento que ignorarían sería
otra forma del mismo problema.

### Función de fuerzas entre dovelas, por fin elegible

GLE aceptaba una desde que se escribió y nadie le pasó nunca otra, así
que el medio seno no era un valor por defecto sino **la única opción
alcanzable**. Cuatro formas con nombre (medio seno, constante,
trapezoidal, seno recortado), habilitadas solo con GLE marcado.

El ancla del test es una **identidad analítica**: Spencer *es* la
solución GLE con función constante, así que los dos tienen que devolver
el mismo número.

Convenio anotado, porque es contraintuitivo y la referencia lo dice
explícitamente: x va de 0 en el extremo **izquierdo** a 1 en el derecho
**sea cual sea la dirección de rotura** — la función no se espeja.

### `lhs_correlate` cableado

Comparte una estratificación de hipercubo latino entre todas las
variables en lugar de darle a cada una la suya. Responde a una pregunta
distinta —«¿y si todo es desfavorable a la vez?»— y por eso la referencia
lo expone como control aparte. Se ignora en Monte Carlo, que no tiene
estratos que compartir.

### Tres bugs del propio diálogo

1. **`RestoreDefaults` reconstruía 4 de las 9 páginas.** Tras pulsarlo
   desaparecían Transient, Statistics, Random Numbers, Design Standard y
   Advanced hasta cerrar y reabrir. La causa: una **segunda lista de
   páginas escrita a mano** dentro de `_defaults`. Ahora hay una sola
   lista, `_PAGES`, y las dos rutas la usan.

2. **La página Transient machacaba la decisión de la página
   Groundwater.** Las dos escribían la opción avanzada y `_apply` recorre
   las páginas en orden, así que elegir *Rapid Drawdown* en Groundwater y
   dejar marcada la casilla de Transient te daba Transient, en silencio.
   La elección tiene ahora **un solo hogar**; la página Transient
   conserva sus opciones de solver y muestra una etiqueta que apunta a
   donde se decide.

3. **Las opciones avanzadas de agua no eran excluyentes en la
   interfaz.** El modelo las declara excluyentes desde v0.1.68, pero
   había dos casillas independientes aquí y una tercera en otra página, y
   `apply` desmarcaba una sin avisar. Pasan a ser **radios**, así que la
   exclusividad se ve en lugar de imponerse por detrás.

Además, la página **Transient se deshabilita** mientras el análisis
transitorio esté apagado, como la referencia: ofrecía una tolerancia de
solver para un análisis que no iba a ejecutarse.

### La comprobación de m-α: ofrecida, pero apagada

Estaba **fuera de la página a propósito** desde v0.1.32, con una nota que
explicaba por qué: rechaza el círculo crítico validado contra la
referencia. La preocupación era correcta; la respuesta, solo a medias.
Que no deba estar **activada** no significa que deba ser **inalcanzable**
— eso es la regla 3 al revés: una capacidad que el motor tiene y la
interfaz esconde.

Se ofrece ahora, **apagada por defecto**, que es una divergencia
deliberada respecto de la referencia (que la trae marcada). La medición
que lo justifica, rehecha antes de decidir en lugar de heredada de la
nota, y **peor de lo que la nota decía**:

| Círculo de referencia validado (Ej1, Bishop, FoS = 0.883074) | |
|---|---|
| m-α mínimo | **−0.0100** (negativo) |
| Dovelas por debajo del límite 0.2 | **5 de 25** |
| Veredicto con la comprobación activa | **rechazado** |

Así que es un **diagnóstico, no un criterio de validez**, y un
diagnóstico no puede venir activado. El aviso vive junto al control que
explica, no en este archivo: una advertencia en un changelog es una
advertencia que nadie lee en el momento en que la necesita.

### Renombrado

`min_initial_fs` → `initial_fos`. Era un nombre equivocado: es el primer
valor de tanteo, no un mínimo. `from_dict` sigue leyendo la clave vieja, y
hay un test que comprueba que **no** actúa como suelo (converge a la misma
raíz partiendo de 0.2 y de 5.0).

## El camino equivocado: un `TypeError` que se manifestó como suite colgada

Merece contarse entero, porque el síntoma no se parecía en nada a la
causa.

Tras cablearlo todo, la suite **dejó de terminar**. No fallaba: se
quedaba parada. Lo primero que hice fue comprobar si de verdad estaba
bloqueada o solo era lenta, y ahí estuvo la pista decisiva: el proceso
había consumido **1042.734 s de CPU**, y veinte minutos después llevaba
**1042.765 s**. Treinta milisegundos en veinte minutos. Eso no es lento,
es bloqueado — y un bloqueo con la CPU a cero no es un bucle infinito,
es una espera.

El log estaba bufferizado y no decía dónde. Relanzada con `python -u` y
un vigilante que compara la última línea cada 45 s, el punto salió
enseguida: `test_statistics_gui_v138.py`, `TestComputeAndResults`.

La cadena, de atrás hacia delante:

1. `_ComputeWorker.run` construye **los cinco métodos a la vez** desde un
   único `lem_kwargs()`.
2. `GLEMorgensternPrice` **sobrescribe `__init__`** y no había crecido con
   el argumento `iterate_steffensen` que se añadió a la clase base.
3. Construir el diccionario de métodos lanzaba `TypeError`.
4. El `try` del worker lo capturaba y emitía `failed`, dejando
   `results` vacío.
5. `_deterministic_criticals()` devolvía `{}`.
6. `_compute_statistics` respondía a un resultado vacío con
   `self._info(...)`, que es un **`QMessageBox` modal**.
7. Sin pantalla, un modal **no vuelve nunca**.

Es literalmente el peligro que documenta AGENTS.md —«no abras diálogos
modales en código que un test vaya a ejecutar»—, alcanzado por un camino
que nadie había recorrido: no lo abrió el test, lo abrió el manejo de
error de un fallo que el propio cambio introdujo.

Lo instructivo es que **una excepción capturada convirtió un error en un
cuelgue**. El `try` que protege al worker de un modelo malo también
oculta un bug de programación, y el modal que informa al usuario de un
resultado vacío es una trampa en un entorno sin pantalla.

La guarda que queda es barata y ataca la clase entera, no el caso:
`test_every_method_accepts_the_shared_configuration` construye **los seis
métodos con el juego completo de argumentos**. Cualquier subclase que
sobrescriba `__init__` y olvide uno falla ahí, en un test que tarda
milisegundos, en vez de colgar la suite media hora después.

## Tests

`tests/test_project_settings_wiring_v174.py` — 33 tests, **uno por
cable**, y todos escritos para fallar si el cable se corta: cambian el
ajuste y comprueban que **el resultado** cambia, nunca que el valor haga
ida y vuelta por el dataclass. Un test de ida y vuelta habría pasado
tranquilamente con los diez ajustes desconectados, que es justamente lo
que pasó durante versiones.

Anclas que no son capturas de lo que el código imprime hoy:

- **identidad analítica**: GLE con función constante ≡ Spencer;
- **identidad analítica**: `aitken` sobre `x_n = 1 + 2^-n` da exactamente 1;
- **propiedad de convergencia**: la misma raíz desde `initial_fos` = 0.2 y 5.0;
- **medición sobre el caso validado**: λ = 1.4919 y las 149 superficies
  rechazadas, ambas comprobadas contra el modelo Ej1 real.

Dos tests existentes se reescribieron contra la nueva ubicación
(`min_initial_fs` → `initial_fos`, y la exclusividad que se mudó de la
página Transient a la de Groundwater). La invariante que protegían no
cambió.

`docs/audits/project_settings_v174.md` recoge el inventario completo
página por página, las divergencias deliberadas respecto de la referencia
—el generador Mersenne Twister frente al Park-Miller que la referencia
ofrece, por ejemplo— y el backlog razonado de lo que falta.

**Probado**: la suite completa y los casos de validación.

**Falta por probar**: el comportamiento de Steffensen sobre geometrías
patológicas. Las mediciones son sobre el caso Ej1 y el talud del fixture;
`aitken` está construido para declinar en vez de dividir por casi cero,
pero eso es un argumento, no un barrido.

## Pendientes que esta versión deja anotados

1. **Excess Pore Pressure**, la única casilla que sigue sin motor. Es una
   feature: necesita Δσv por dovela, campos nuevos en materiales y
   cargas, y validación externa. **v0.1.75**.
2. **`ogr_cli` no aplica el descenso rápido** — anotado en v0.1.72, sigue
   pendiente.
3. **El backlog frente a la referencia**, con nueve entradas razonadas en
   el documento de auditoría. La primera de la lista es *Data Output*.
4. **El botón `Defaults`**: el de la referencia **guarda** la
   configuración actual como valor por defecto de los ficheros nuevos; el
   nuestro **restaura** los de fábrica. Son cosas distintas y solo
   tenemos la segunda.
