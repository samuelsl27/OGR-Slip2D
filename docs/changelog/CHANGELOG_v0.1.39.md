# OGR Suite v0.1.39 — Changelog

**Lanzamiento:** 2 de agosto de 2026
**Desarrollador:** Samuel Sáez López — Estudiante de Doctorado, UPCT
**Licencia:** GPL-3.0

> **Anomalía A5 resuelta** — y con un diagnóstico inicial que resultó
> ser equivocado. No era un problema de Spencer, sino del **arranque del
> recocido simulado**, que dependía literalmente de la suerte.

---

## 🔍 El diagnóstico correcto

La anomalía se había registrado como «Simulated Annealing con Spencer no
produce superficies válidas». Al reproducirla apareció el dato que lo
cambia todo: con `seed = 1` **ningún método** produce superficies — ni
Bishop, ni Janbu, ni Ordinary, ni GLE, ni Lowe-Karafiath — y además el
recuento de superficies **inválidas también era cero**. No es que se
rechazaran candidatas: es que **no se generaba ninguna**.

Con otras semillas todo funcionaba. El problema, por tanto, no estaba en
la evaluación sino en el **bootstrap**.

## 🔴 La causa raíz

El arranque construía la superficie inicial sorteando **cada vértice
interior de forma independiente** y confiando en que el resultado pasara
los filtros de admisibilidad. El filtro determinante es el de
**unimodalidad**: la superficie debe descender hasta un único punto bajo
y luego ascender.

Para *n* valores ordenados al azar, la probabilidad de que salgan
unimodales es aproximadamente **2ⁿ⁻¹/n!**, que con los nueve vértices por
defecto queda **por debajo del 1 %**. El bootstrap hacía 200 intentos, de
modo que con la mayoría de semillas acertaba alguno… pero con las
desafortunadas agotaba los 200 sin un solo candidato válido y la búsqueda
devolvía absolutamente nada.

Medido sobre la semilla que fallaba: **200 de 200 intentos rechazados por
unimodalidad**, cero por cualquier otra causa.

## 🔧 La corrección

La superficie inicial se construye ahora **admisible por construcción**:
un cuenco colgado bajo la cuerda que une los puntos de entrada y salida,

    y(t) = cuerda(t) − profundidad · sen(π·t)^potencia

que es de un solo valor en x, queda bajo la cuerda y tiene **un único
punto bajo** — exactamente las tres condiciones que comprueban los
filtros. El azar pasa a controlar la **profundidad y la asimetría** del
cuenco en lugar de cada vértice por separado, de modo que se sigue
explorando pero **toda** candidata generada es válida. La profundidad se
reduce en intentos sucesivos, así que un cuenco más somero siempre acaba
encajando.

Se conserva el sorteo aleatorio original como último recurso, por si una
geometría inusual derrotase al cuenco construido.

## ✔️ Validación

| | Antes | Ahora |
|---|---|---|
| Semillas sin superficies (de 20) | 1 | **0** |
| Spencer con `seed = 1` | 0 válidas | **37 válidas**, crítico 0.8991 |
| Todos los métodos con `seed = 1` | 0 válidas | 20–37 válidas |
| Superficies válidas por corrida (media) | — | 85 |

## 📊 Tests

**747 tests, 747 verdes** (+9 desde v0.1.38; suite 100 % desde v0.1.21).

Cobertura nueva (`tests/test_annealing_bootstrap_v139.py`): la semilla
que fallaba funciona; **ninguna de 20 semillas queda sin superficies**;
**todos los métodos** funcionan sobre la semilla problemática (lo que
documenta que el diagnóstico original era erróneo); Spencer en
particular; y sobre todo, **cada juego de parámetros que produce el
bootstrap pasa los tres filtros** (unimodalidad, x estrictamente
creciente y por debajo de la cuerda), verificado en 25 intentos
consecutivos — que es la propiedad que hace innecesaria la suerte.
Además: la aleatoriedad sigue explorando, los resultados están en rango
físico, se produce un número útil de superficies y la semilla es
reproducible.

## ⏳ Siguiente

Por el orden acordado: **back analysis de fuerza de soporte**, cobertura
de **i18n**, y por último el **import DXF**, que merece plan propio
(simplificación de geometría, detección de intersecciones, autocorrección
y asignación de capas a entidades: contorno externo, materiales, líneas
de agua, soportes).

---

© 2026 Samuel Sáez López — UPCT — GPL-3.0
