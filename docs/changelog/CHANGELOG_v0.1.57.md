# OGR Suite v0.1.57 — Changelog

**Lanzamiento:** 7 de agosto de 2026
**Desarrollador:** Samuel Sáez López — Estudiante de Doctorado, UPCT
**Licencia:** AGPL-3.0-or-later

> **Fase M6.** Con ella se cierra el **plan de interfaz completo: las
> nueve fases terminadas.**

---

## 🔴 Lo más importante: los coeficientes parciales ya se aplican

v0.1.52 los hizo **configurables**; hasta ahora **no cambiaban nada**. Un
ajuste que no hace nada es peor que no tenerlo, porque el usuario cree que
el análisis lo respeta.

`ogr_core/project/design_factors.py` los aplica **transformando una copia
del proyecto**, no modificando el solver. Esa decisión importa:

- todas las vías de análisis —determinista, probabilística, transitoria,
  optimización— reciben los valores minorados automáticamente, porque
  todas leen el mismo proyecto;
- el motor sigue siendo un solver de equilibrio límite puro, **sin noción
  de ninguna norma**, así que añadir un código de diseño es una tabla de
  números y no un cambio en la matemática;
- el proyecto del usuario **nunca se modifica**, de modo que desactivar la
  norma restaura los resultados exactos.

### El rozamiento se minora sobre tan φ, no sobre φ

Es lo que especifica el Eurocódigo 7, y la diferencia no es despreciable:
**30° / 1.25 = 24.00°**, mientras **atan(tan 30° / 1.25) = 24.79°**.
Pequeña, pero equivocada de una forma que discreparía en silencio con una
comprobación a mano.

### Verificación numérica

| Norma | FoS del caso de referencia |
|---|---|
| Sin coeficientes | 0.9074 |
| Eurocódigo 7 DA1-C2 | **0.7259** |
| Eurocódigo 7 DA3 | **0.7259** |
| Eurocódigo 7 DA1-C1 | **0.9074** (sin cambio) |

**DA1-C1 no cambia el resultado, y eso es correcto**: solo minora
acciones, y este modelo no tiene cargas externas. Es una buena
comprobación de que los coeficientes de material no se aplican donde la
norma no lo pide. DA1-C2 y DA3 coinciden porque sus coeficientes de
material son idénticos y solo difieren en las acciones.

## 🆕 Parameter Calculator

`ogr_core/materials/parameter_calculator.py` deriva las constantes de
Hoek-Brown Generalizado —**mb, s, a**— a partir del GSI, la constante de
roca intacta **mi** y el factor de alteración **D**, con las ecuaciones de
Hoek, Carranza-Torres y Corkum (2002).

Validado contra las definiciones: con **GSI = 100 y D = 0** da exactamente
**mb = mi, s = 1, a = 0.5**.

Dos cuidados:

- **D = 2 es una singularidad**: 28 − 14·2 = 0 deja mb indefinido. Se
  acota justo por debajo y **se avisa**, en lugar de devolver infinito —
  una constante de resistencia infinita produce una envolvente sin sentido
  en silencio.
- **El GSI y D dependen del criterio del técnico**, así que las tablas de
  guía (30 litologías, 6 bandas de GSI, 8 métodos de excavación) se
  muestran **junto a los campos** y no escondidas en la ayuda: un número
  escrito sin ese contexto es la causa habitual de una envolvente
  incorrecta, y ninguna precisión posterior lo repara.

El botón **GSI…** aparece solo con el criterio Hoek-Brown Generalizado,
cuyos parámetros son **derivados**; con Mohr-Coulomb el calculador no
tendría sentido.

## 🆕 Registro de sesiones

El menú Window eran **tres `lambda: None`**. Ahora lista las ventanas
abiertas, marca la activa con un punto y las no guardadas con un
asterisco — las dos cosas que un usuario necesita de esa lista, y la razón
de que un menú estático fuera inútil.

Se **reconstruye cada vez que se abre**, así que no puede quedar obsoleto,
y las ventanas se dan de baja al cerrarse, o el menú listaría ventanas
inexistentes. *New Window* abre una sesión **independiente**, no una vista
del mismo modelo: dos ventanas editando un proyecto permitirían que un
cambio en una invalidase los resultados mostrados en la otra sin ninguna
señal.

## 📊 Tests

**1234 tests, 1234 verdes** (+37 desde v0.1.56; suite 100 % desde
v0.1.21).

Cobertura (`tests/test_m6_v157.py`): minoración del rozamiento (**tangente
y no ángulo**, factor unidad, cero, siempre menor, factor inválido);
aplicación (desactivado devuelve el mismo objeto, **original intacto**,
cohesión dividida, regla de la tangente, informe, y **coeficientes todos
unidad reportados como sin efecto**); llegada al análisis (**los
coeficientes bajan el FoS**, **DA1-C1 no altera un modelo sin cargas**,
DA1-C2 y DA3 coinciden, y desactivar **restaura el número original**);
calculador (**definiciones con GSI = 100**, caso publicado, alteración
decreciente, **D = 2 acotado y no infinito**, GSI acotado, tablas
poblazas); diálogo del calculador (cálculo al abrir, actualización en
vivo, litología que rellena mi, **s en notación científica para macizos
pobres**, aviso de D = 2, y **botón solo con Hoek-Brown Generalizado**);
y registro de sesiones (alta, baja al cerrar, asterisco, lista completa,
**menú que no queda obsoleto**, y ventana nueva independiente).

## 🏁 Plan de interfaz completo

| Fase | Contenido | Versión |
|---|---|---|
| I1 | Contexto visual de Interpret | v0.1.49 |
| I2 | Motor de contornos | v0.1.50 |
| M1 | Data Tips y forzado | v0.1.51 |
| M2 | Project Settings | v0.1.52 |
| I3 | Menús de Interpret | v0.1.53 |
| M3 | Menú Tools y capa de anotación | v0.1.54 |
| M4 | Búsqueda enfocada y optimización | v0.1.55 |
| M5 | Menús menores | v0.1.56 |
| M6 | **MDI y utilidades avanzadas** | **v0.1.57** |

---

© 2026 Samuel Sáez López — UPCT — AGPL-3.0-or-later
