# OGR Suite v0.1.52 — Changelog

**Lanzamiento:** 6 de agosto de 2026
**Desarrollador:** Samuel Sáez López — Estudiante de Doctorado, UPCT
**Licencia:** AGPL-3.0-or-later

> **Fase M2: Project Settings completo.** De cuatro páginas a las **nueve**
> que describe la especificación.

---

## 🆕 Las cinco páginas que faltaban

`Transient`, `Statistics`, `Random Numbers`, `Design Standard` y
`Advanced`. Los datos ya existían en el modelo y eran alcanzables desde
otros diálogos; lo que faltaba era el sitio central donde verlos y
cambiarlos.

**Transient** — opciones del solver y **recuento de etapas definidas**,
para ver de un vistazo si hay un transitorio configurado. La tabla de
etapas se sigue editando en el menú Agua subterránea, junto a las
condiciones de contorno de las que depende, y la página lo dice.

**Statistics** — tipo de análisis, método de muestreo, número de muestras
e intervalos de sensibilidad, con los *tooltips* explicando qué implica
cada elección (Overall Slope repite toda la búsqueda por muestra; el
hipercubo latino equivale a unas cinco veces más muestras de Monte Carlo).

**Random Numbers** — generador y semilla. La **semilla se deshabilita** con
el generador aleatorio, en lugar de dejarla con aspecto de tener efecto.

**Design Standard** — coeficientes parciales con presets de Eurocódigo 7
(DA1-C1, DA1-C2, DA2, DA3). Los coeficientes **solo son editables en
Personalizado**: dejarlos editables con una norma seleccionada
tergiversaría la norma.

**Advanced** — comprobación de tracción, aceleración de Steffensen, factor
inicial y rango de lambda.

## ⚖️ Dos ampliaciones del modelo

**`RandomNumberSettings`** con `effective_seed()`: devuelve la semilla en
modo pseudoaleatorio y `None` en aleatorio, para que el muestreador se
siembre del reloj. La distinción importa: un flujo pseudoaleatorio es
**reproducible**, que es lo que hace defendible un resultado probabilístico
en un informe; uno sembrado del reloj explora distinto en cada corrida,
que es como se comprueba que una conclusión no es artefacto de una
semilla.

**`DesignStandardSettings`** con los presets del Eurocódigo 7,
**desactivado por defecto**: aplicar coeficientes parciales en silencio
cambiaría todos los factores de seguridad con los que el usuario haya
comparado antes, así que tiene que ser una elección explícita. La tabla de
presets es constante de clase y **se excluye de la serialización**, para no
inflar cada archivo de proyecto con datos que no son estado.

## 🚫 Lo que deliberadamente NO se añadió

La comprobación de **m-alpha** no aparece en Advanced, y la página explica
por qué: rechaza superficies cuyo denominador de la normal baja de 0.2, y
se midió que **también rechaza el círculo crítico validado contra la
referencia**. Es un diagnóstico, no un criterio de validez, y permanece en
las opciones de búsqueda. Hay un test que comprueba que la explicación
sigue ahí y que no se ha colado una casilla.

## 📊 Tests

**1066 tests, 1066 verdes** (+31 desde v0.1.51; suite 100 % desde
v0.1.21).

Cobertura (`tests/test_project_settings_m2_v152.py`): números aleatorios
(reproducibilidad, siembra por reloj, round-trip); norma de diseño
(desactivada por defecto, presets que cargan sus coeficientes, **DA1-C1
que afecta a acciones y no a materiales**, reinicio a la unidad,
Personalizado que no toca los valores, todos los presets completos, y
**PRESETS excluido de la serialización**); estructura del diálogo (las
nueve páginas en orden, todas con `apply`, navegación); y una clase por
página con sus reglas — recuento de etapas, exclusividad del transitorio,
semilla deshabilitada, coeficientes solo editables en Personalizado, todo
deshabilitado al desactivar, y la ausencia justificada de m-alpha.

## ⏳ Siguiente

**Fase I3** — las **21 entradas de menú de Interpret** pendientes: Data
(4), Query (5), Groundwater (6) y Statistics (6).

---

© 2026 Samuel Sáez López — UPCT — AGPL-3.0-or-later
