# Análisis de Newmark

## Qué hace

Calcula el **desplazamiento sísmico permanente** de cada superficie de rotura
integrando dos veces la parte de un acelerograma que excede su **aceleración
crítica**, y calcula esa aceleración crítica —el **coeficiente sísmico crítico
Ky**— resolviendo el factor de seguridad hasta el objetivo.

Tres piezas, y el orden no es negociable: sin acelerograma no hay entrada, sin
Ky no hay aceleración crítica, y sin un objetivo de búsqueda distinto del
factor de seguridad la búsqueda encuentra otra superficie que no es la que se
pregunta.

1. **El acelerograma**, un tipo de dato que el programa no tenía.
2. **El coeficiente sísmico crítico Ky**, por superficie.
3. **El desplazamiento de bloque rígido**, Newmark (1965).

## Por qué

Un factor de seguridad pseudoestático menor que 1 no dice que el talud se
caiga: dice que durante unos instantes la resistencia se supera. Lo que decide
si un terraplén sigue sirviendo después de un terremoto no es ese factor sino
**cuántos centímetros se ha movido**, y ése es el número que un análisis de
Newmark da y un análisis pseudoestático no puede dar.

Y Ky no es sólo un paso intermedio: es la forma en que se comunica la
capacidad sísmica de un talud —«este talud aguanta 0,14 g»— sin depender de
qué terremoto se suponga.

## Criterios de aceptación

### El desplazamiento de bloque rígido

- [x] Un pulso rectangular de amplitud `A·g` y duración `t₀` sobre una crítica
      `N·g` reproduce la forma cerrada de Newmark (1965),
      `u = V²/(2gN)·(1 − N/A)` con `V = A·g·t₀`.
      **Corregido tras medir**: este criterio decía «y el error cae al refinar
      `dt` al orden que le corresponde al esquema trapecial», y lo medido es
      mejor y más simple. Cuando el instante de parada `t_m = (A/N)·t₀` cae en
      una muestra el esquema es **exacto a 1e-15**, con cualquier paso entre
      20 ms y 0,6 ms; el residuo aparece **sólo** cuando la parada cae entre
      muestras, vale ≤ 3,7e-4 con dt = 20 ms y baja a 4e-8 al refinar, y no
      cae suavemente porque depende de dónde caiga la parada respecto al
      muestreo. Un criterio que hablara de «orden de convergencia» estaría
      describiendo algo que este esquema no hace.
- [x] Con `a_c = 0` y las dos direcciones permitidas, el desplazamiento
      relativo es **exactamente** el desplazamiento del terreno (la doble
      integral trapecial del propio registro).
- [x] Con `a_c ≥ PGA` el desplazamiento es **cero exacto**, no pequeño.
- [x] Escalar registro y crítica por `s` multiplica el desplazamiento por `s`;
      escalar el eje de tiempos por `τ` lo multiplica por `τ²`.
- [x] El desplazamiento **no crece** con `a_c`.

### El coeficiente sísmico crítico

- [x] Sobre un plano infinito sin cohesión ni agua, `k_y = tan(φ − β)`
      exactamente — Newmark (1965).
- [x] Sobre el ejemplo 1 de Loukidis, Bandini y Salgado (2003), OGR calcula
      `k_c` y el valor cae dentro de la banda que se fije **tras medir** contra
      los `0,432` (seco) y `0,132` (`ru = 0,5`) publicados.
- [x] Aplicar `k_h = Ky` a la superficie de la que salió devuelve el factor
      objetivo dentro de la tolerancia de convergencia del método. Es la
      comprobación que la referencia se hace a sí misma.
- [x] Un factor inicial `FS(0) ≤ objetivo` devuelve `Ky = 0`, y una superficie
      sin cruce por debajo del techo **no devuelve número**, se explica.

### La búsqueda

- [x] Con los dos modos apagados, las siete búsquedas devuelven salida **bit a
      bit idéntica** a la de 0.1.126.
- [x] Con el modo Ky encendido, la superficie informada es la de **Ky mínimo**,
      y sobre un modelo donde difieren **no** es la de factor mínimo.
- [x] Con el modo Newmark encendido, la superficie informada es la de
      **desplazamiento máximo**, que por la monotonía es la misma que la
      anterior.

### El problema 104 del banco

- [x] Escenarios 1, 2 y 3 (sin sismo, `k = 0,15`, aceleración crítica) contra
      **1,359 · 0,978 · Ky 0,139**, con enjambre multimodal más optimización,
      filtro de área 1 y Spencer. Banda fijada tras medir.
- [x] El escenario 4 **no** se cierra, y la ficha dice qué haría falta.
      Confirmado: falta el acelerograma, y se dejó escrito dónde está y por
      qué no se pudo obtener.

### Interfaz

- [x] *Loading → Seismic Records...* existe, está en la barra de menús y abre
      un diálogo no modal de definición e importación.
- [x] Project Settings gana una página *Seismic* con los dos interruptores, y
      el selector de registro se deshabilita si Newmark está apagado.
- [x] Un registro sobrevive a guardar y reabrir el `.ogr`.
- [x] Todo texto nuevo pasa por `tr()` y tiene traducción española.

## Validación numérica

- **Newmark, N.M. (1965)**, «Effects of earthquakes on dams and embankments»,
  *Géotechnique* **15**(2) 139-160 — la forma cerrada del pulso rectangular y
  `k_y = tan(φ − β)`.
- **Wilson, R.C. y Keefer, D.K. (1983)**, *BSSA* **73**(3) 863-877 — el
  esquema de integración.
- **Jibson, R.W. (1993)**, *Transportation Research Record* **1411** 9-17 — el
  algoritmo paso a paso y la Tabla 1 con tres registros con nombre y su
  desplazamiento.
- **Loukidis, D., Bandini, P. y Salgado, R. (2003)** — el coeficiente sísmico
  crítico publicado, `k_c = 0,432` y `0,132`.
- **Jibson, R.W., Rathje, E.M., Jibson, M.W. y Lee, Y.W. (2013)**, USGS
  Techniques and Methods 12-B1 — el programa que la referencia declara usar.

## Fuera de alcance

- **Bloque flexible: análisis acoplado y desacoplado.** Necesitan velocidad de
  onda de corte por encima y por debajo de la superficie, amortiguamiento,
  deformación de referencia y una respuesta de sitio 1-D que el programa no
  tiene. No se ofrecen en el diálogo, ni siquiera deshabilitados.
- **La quinta opción de polaridad de la referencia** (*All Accelerations*): su
  ayuda no la define y se solapa con el ajuste de sentido. Un control cuyo
  significado no se conoce no se pone.
- **Resistencia pseudoestática por etapas** (el procedimiento de Duncan,
  Wright y Wong aplicado al sismo).
- **El escenario 4 del problema 104**: sin el acelerograma que usó la
  referencia no hay nada contra qué medirlo.
