# OGR Suite v0.1.55 — Changelog

**Lanzamiento:** 6 de agosto de 2026
**Desarrollador:** Samuel Sáez López — Estudiante de Doctorado, UPCT
**Licencia:** AGPL-3.0-or-later

> **Fase M4: búsqueda enfocada y optimización de superficies.** Dos
> capacidades que afectan al **resultado**, no solo a la comodidad.

---

## 🆕 Objetos de foco

`ogr_slip2d/focus.py`. Una búsqueda en rejilla genera círculos a partir de
los límites del talud y el incremento de radio, lo que significa que la
mayoría barren regiones que el ingeniero ya sabe irrelevantes. Un objeto
de foco acota el conjunto: solo se conservan los círculos que interactúan
con él.

Cuatro tipos: **ventana** (cuadrilátero que el círculo debe atravesar),
**línea** (que debe cruzar), **punto** (por el que debe pasar, dentro de
tolerancia) y **tangente** — condición distinta de cruzar, y la que
permite apuntar a un estrato débil conocido.

**El filtro actúa ANTES de evaluar.** Rechazar un círculo cuesta dos
distancias; evaluarlo cuesta un rebanado completo con iteración. Ese orden
es lo que hace que enfocar merezca la pena en lugar de ser solo ordenado.
Medido sobre el caso de referencia: una tangente a y = 15 deja **17
evaluaciones de 206, un 92 % menos**.

Detalles que cambian el comportamiento: se combinan con **AND** —añadir un
segundo objeto acota más, que es lo que significa enfocar—; un objeto
desactivado o mal formado **no filtra nada** en vez de rechazarlo todo en
silencio; y la tangencia usa la **recta infinita**, porque un círculo
tangente más allá del tramo dibujado sigue siendo tangente a ese plano,
que es lo que representa un estrato.

## 🆕 Optimización por paseo aleatorio

`ogr_slip2d/optimize.py`, siguiendo Greco (1996): perturbar un vértice al
azar, recalcular, conservar el cambio si baja el factor.

### El hallazgo de esta fase: la densificación

Una superficie de búsqueda por trayectorias puede tener **cuatro
vértices**, es decir dos móviles — demasiado poco para que un paseo
reconfigure nada. Medido: **sin densificar el paseo mejora 0.0000**; con
doce vértices baja el factor de **0.8582 a 0.8154 (−0.043)** con 49
perturbaciones aceptadas. Los vértices se insertan siempre en el **segmento
más largo**, para que la libertad extra vaya donde la superficie está menos
definida en lugar de amontonarse en un extremo.

### Dos correcciones más

**El paso se acota por abajo, no expulsa del bucle.** Salir en cuanto el
paso bajaba del mínimo daba un paseo de **diez evaluaciones**, que no
optimiza nada. Ahora el paso se reduce a la mitad tras cada pasada
infructuosa pero con suelo, y la corrida termina por presupuesto de
iteraciones o tras varias pasadas estériles al paso más fino.

**Una pasada, no un solo fallo, termina la corrida.** Parar en la primera
perturbación rechazada abandonaría una superficie a la que solo le faltaba
mover otro vértice.

Y algo que importa: **todo candidato pasa por el filtro de
admisibilidad**. La optimización persigue un factor más bajo, que es
exactamente la dirección en la que están las superficies cinemáticamente
imposibles, así que sin ese filtro la «mejora» sería un artefacto.

## 🆕 Menú Surfaces completo

Submenú **Focus Search** (ventana, línea, punto, tangente y gestor),
**Optimize Surfaces**, **Add Surface (centro y radio)** y submenú **Slope
Limits** con definir, mover y restablecer.

Los límites de talud pasan a `SearchSettings` y llegan al motor. Son
`None` por defecto, que significa **automático**, derivado de la superficie
del terreno: unos límites fijos de una geometría serían incorrectos en
otra, así que solo se almacenan cuando el usuario los define. *Define
Limits* era, hasta ahora, un mensaje de marcador.

Los objetos de foco se guardan en el proyecto, porque forman parte de cómo
se analiza el modelo y no son un ajuste transitorio de vista.

## ⚡ Coste de los tests

La primera versión de este archivo tardaba **48 s** porque rehacía una
búsqueda por trayectorias en cada test. Compartiendo la superficie de
partida y ajustando los presupuestos bajó a **12 s** sin perder ninguno de
los 39 tests. Con la suite rozando ya el límite de tiempo, vigilar esto
forma parte del trabajo.

## 📊 Tests

**1177 tests, 1177 verdes** (+39 desde v0.1.54; suite 100 % desde
v0.1.21).

Cobertura (`tests/test_focus_optimize_m4_v155.py`): foco por punto
(acepta, rechaza, tolerancia, y **un punto dentro del disco no está sobre
el círculo**); tangente (acepta la tangente, **rechaza la secante**, no
alcanza, recta infinita); línea (cruce, distante, **segmento interior que
no corta el arco**); ventana (atraviesa, falla, **centro dentro pero arco
fuera**); combinación (sin objetos acepta todo, **AND**, desactivado, mal
formado, round-trip); integración en el motor (**menos de la mitad de
evaluaciones**, sigue encontrando crítico, todo círculo evaluado cumple,
sin foco no cambia nada, desactivado no se aplica, límites de talud,
persistencia); y optimización (**la densificación es lo que la hace
funcionar**, nunca devuelve algo peor, superficie válida con x creciente,
extremos fijos, semilla reproducible, presupuesto respetado, superficie de
dos puntos rechazada con motivo, round-trip y resumen).

## ⏳ Siguiente

**Fase M5 — menús menores**: File (Import Properties, Export Image,
impresión, archivos recientes), Edit (Picture Format), Loading (Modify
Load), Support (Modify, Move, Ungroup) y Help (About con metadatos).

---

© 2026 Samuel Sáez López — UPCT — AGPL-3.0-or-later
