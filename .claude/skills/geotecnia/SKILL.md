---
name: geotecnia
description: Convenios, unidades y fuentes de las formulaciones geotécnicas del proyecto. Úsalo al tocar métodos LEM, resistencia, filtración o presiones intersticiales.
---

# Convenios geotécnicos de OGR Suite

## Unidades internas (SI, siempre)

| Magnitud | Unidad interna |
|---|---|
| Longitud | m |
| Fuerza | kN |
| Tensión, cohesión, presión | kPa |
| Peso específico | kN/m³ |
| Permeabilidad | m/s |
| Ángulos | **grados** en la interfaz y en los parámetros; radianes solo dentro de una fórmula |

La conversión a las unidades del usuario ocurre **en la capa de interfaz**,
nunca en el motor. Un solver que conociera unidades imperiales sería un
solver más difícil de validar.

## Convenios de signo

- **Presión intersticial**: positiva en compresión. La succión es
  **negativa**.
- **Cara de rezume**: reacción positiva = agua **entrando**. El convenio
  inverso provocó oscilación en el solver no saturado y hubo que resolverlo
  con bandas de histéresis.
- **Ángulo de la base de dovela**: positivo cuando desciende hacia el pie.
- **Coeficientes parciales**: los de material **dividen** (reducen
  resistencia); los de acción **multiplican** (aumentan carga). Siempre en
  el sentido desfavorable.

## Fuentes de las formulaciones

Cita siempre la fuente original, nunca el programa que la implementa.

| Tema | Fuente |
|---|---|
| Bishop simplificado | Bishop (1955) |
| Janbu | Janbu (1954, 1973) |
| Spencer | Spencer (1967) |
| Morgenstern-Price / GLE | Morgenstern y Price (1965) |
| Lowe-Karafiath | Lowe y Karafiath (1960) |
| Hoek-Brown generalizado | Hoek, Carranza-Torres y Corkum (2002) |
| Resistencia no saturada | Fredlund et al. (1978), envolvente bilineal con φ_b |
| Richards en forma mixta | Celia, Bouloutas y Zarba (1990) |
| Optimización por paseo aleatorio | Greco (1996) |
| Comprobación m-alpha | Whitman y Bailey (1967) |

## Trampas que ya nos costaron caro

- **Janbu corregido**: el factor `d` usa la distancia perpendicular máxima
  de la cuerda a la superficie, **no** la altura máxima de dovela.
- **tan φ, no φ**: los coeficientes parciales minoran la **tangente**.
  30°/1.25 = 24.00°, pero atan(tan30°/1.25) = 24.79°.
- **Intersección con el terreno**: hay que tomar el primer par de cruces
  consecutivo con arco bajo el terreno, no el par extremo. Tomar los
  extremos daba +40 % de error en taludes con berma.
- **Zona saturada en transitorio**: la forma mixta de Richards degenera
  porque θ es constante. Se resuelve con una función de almacenamiento
  generalizada W(P) con expresiones distintas para P<0 y P≥0.
- **m-alpha**: el círculo crítico validado contra la referencia **también**
  lo incumple. Es diagnóstico, no criterio de validez.
