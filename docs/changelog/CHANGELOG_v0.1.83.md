# OGR Slip2D v0.1.83 — 1697 superficies se esfumaban del recuento, y el denominador se movía solo

Tercera pasada de verificación del plan de v0.1.82, punto por punto y con
comandos en lugar de memoria. Salieron tres cosas sin hacer. Una de ellas
estaba escrita en el plan con todas las letras y se dio por hecha.

**Ningún cálculo cambia.** El mínimo global sigue siendo 0,884517 en
(88 , 70,5). Lo que cambia es lo que el programa dice que ha analizado.

---

## 1 · El recuento no cerraba

El plan de v0.1.82 decía, sobre el descarte por curvatura inversa:

> Si devuelve `False`, `slice_surface` devuelve `None` → **la búsqueda la
> cuenta como inválida, que es lo que hace Slide**.

No la contaba. `GridSearch.run` hacía `if res is not None:`, así que un
círculo que no llegaba a analizarse no entraba ni en `valid_count` ni en
`invalid_count`: **desaparecía**.

Sobre la malla de referencia del Ejemplo 1:

| | generados | se esfumaban | lo que informábamos |
|---|---|---|---|
| curvatura inversa **ON** | 4851 | **1697** | «2966 / 3154» |
| curvatura inversa **OFF** | 4851 | **2218** | «2448 / 2633» |

Dos defectos, y el segundo es el peor:

1. Se perdía el **35 %** de la población sin decirlo. Truncado silencioso,
   que es justo lo que este proyecto se prohíbe en otros sitios.
2. **El denominador se movía al cambiar un ajuste.** Un número que el
   usuario compara entre corridas no puede depender de una casilla; si
   cambia, no compara nada.

### La identidad que ahora se comprueba

La documentación de referencia publica la aritmética de la población:

> el número total de círculos generados por malla es (intervalos en X + 1)
> × (intervalos en Y + 1) × (Radius Increment + 1)

Para 20×20 con incremento 10: **21 × 21 × 11 = 4851**. Y ahora cierra:

```
curvatura inversa ON : 2966 válidas + 1885 inválidas = 4851
curvatura inversa OFF: 2448 válidas + 2403 inválidas = 4851
```

El reparto se mueve —el ajuste hace su trabajo— pero **cada superficie que
sale de un lado entra en el otro**, y eso también se comprueba. Es una
identidad de la referencia, no una captura de lo que imprime el código:
regla 1.

Para comparar: Slide informa 4851 = 3277 válidas + 1574 inválidas.

`SearchResult` gana `total_count`, que es el denominador honesto. No vale
`len(evaluations)`: una superficie que no se pudo analizar **no tiene
`LEMResult` que guardar**, así que nunca llega a esa lista, pero se generó.

`AutoRefineSearch` ya lo contaba bien desde siempre; solo la búsqueda en
malla lo hacía mal. Las búsquedas por muestreo (Path, Block, Slope,
recocido) cuentan superficies *válidas* hasta un objetivo y ya informan de
sus intentos en `attempts`; mezclar las dos contabilidades haría el número
menos legible, no más.

### El resumen de no válidas, en consecuencia

Ahora distingue dos poblaciones en lugar de fingir que hay una: las que
tienen **código de error** —analizadas y rechazadas, agrupadas por motivo—
y las **descartadas antes de dovelarse**, que se cuentan en el total pero no
tienen motivo bajo el que agruparse ni geometría que dibujar en «Surfaces
with error code». Informar solo de las primeras dejaría el rechazo corto en
dos tercios.

---

## 2 · Show Slices no creaba la consulta

`Show Slices` y `Query Slice Data` caían al mínimo global **sin crear la
Query**. Las dovelas se dibujaban, así que parecía hecho; pero la lista de
consultas se quedaba vacía, la superficie no salía en negro con sus líneas
radiales, y *Delete Query* respondía «no hay consultas que eliminar» justo
después de haberla usado.

La referencia es explícita: *«if you select Show Slices before any queries
have been created, SLIDE will automatically create a Query for the Global
Minimum»*. `_ensure_a_query()` ya existía y hacía exactamente eso —lo usaba
`Graph Query`—; faltaba llamarlo desde los dos sitios.

---

## 3 · Había dos búsquedas por celda, y las dos eran las malas

El plan pedía *reutilizar* la búsqueda de la celda de la malla. En v0.1.82
se escribió una nueva —que deduce la malla **del resultado**— y las dos
viejas se quedaron donde estaban: en el hover y en el clic, leyendo la malla
de `project.settings.search`.

O sea que la ventana tenía tres, y las dos que de verdad se usaban al mover
el ratón arrastraban el fallo que el docstring de la nueva ya describía:
**si el usuario edita la malla y no recalcula, el clic se resuelve contra
una malla de la que no salió ninguno de los números en pantalla.**

Sustituidas por la nueva. Unas 60 líneas duplicadas menos, y un test que
mueve la malla después de calcular y exige que la selección siga acertando.

---

## Lo que se implementó de otra forma, y se queda

Revisado y decidido: seis puntos del plan de v0.1.82 están hechos de otra
manera. Se documenta aquí para no volver a auditarlo.

| El plan decía | Está así | Por qué se queda |
|---|---|---|
| `tension_crack_x`, `tension_crack_top_y` | `tension_cracks: list` + propiedad `reverse_curvature` | Un círculo puede invertirse por **los dos** extremos; dos campos sueltos solo cubren uno |
| `DEFAULTS_BY_FIELD` | `ContourSettings.for_field()` | Mismos valores; una fábrica se documenta y se prueba mejor que un dict de clase |
| Paleta por interpolación HSV 0°→240° | 24 literales medidos | La rampa **no** reproduce la última banda (azul puro, no 230°). El dato es la medición |
| `QPainterPath` compartido en *All Surfaces* | Un item por superficie, sin tope | Medido: 2966 superficies en **209 ms**. El tope era el problema, no el número de items |
| Botón «Auto Range» | «Ajustar a los resultados» | La casilla de auto-rango está justo encima; dos controles con el mismo nombre confunden |
| «Pick the minimum surface to query» | «Pick the surface to query — Esc to cancel» | No solo se eligen superficies mínimas: también se elige por cualquier punto de la masa |

---

## Tests

- `test_reverse_curvature_v182.py` — tres nuevos: la identidad 21×21×11, que
  el denominador no se mueve con el ajuste, y que `len(evaluations)` **no**
  es el denominador.
- `test_interpret_query_v182.py` — cuatro nuevos: Show Slices y Query Slice
  Data crean la consulta; y la selección sobrevive a que se edite la malla
  después de calcular.

Suite completa, sin argumentos: **1789 de 1789**.

---

© 2026 Samuel Sáez López — UPCT — AGPL-3.0-or-later
