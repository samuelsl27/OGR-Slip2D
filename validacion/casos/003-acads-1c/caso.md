# 003 — ACADS 1(c): talud no homogéneo de tres capas

El hermano estratificado del caso `001`, del mismo estudio ACADS. Aporta lo
que aquél no puede: **regiones y asignación de materiales**.

## De dónde sale

> Giam, S.K. & Donald, I.B. (1989). *Example problems for testing soil slope
> stability programs.* Civil Engineering Research Report No. 8/1989, Monash
> University. Problema **1(c)**.

| Valor | Cuál es |
|---|---|
| 1.39 | Factor arbitrado |
| **1.406** | Media Bishop de 16 programas ← el esperado |
| 1.381 | Media de 31 programas (todos los métodos) |

Mismo criterio que en el `001`: la media con respaldo estadístico, no la
salida de un programa concreto.

## Geometría, y cómo se comprobó que está bien leída

Las **coordenadas** están en el texto del enunciado; lo que solo existe en la
figura es **cómo se conectan**. Ésa es toda la diferencia con el caso `001`,
que no necesitó mirar ningún dibujo.

```
Contorno externo:
    (20,20) → (70,20) → (70,24) → (70,31) → (70,35) → (50,35) → (30,25) → (20,25)

Línea de material superior:
    (30,25) → (40,27) → (50,29) → (54,31) → (70,31)

Línea de material inferior:
    (40,27) → (52,24) → (70,24)
```

Las dos arrancan del pie del talud y se bifurcan en (40,27).

**La comprobación independiente.** La figura de resultados del manual publica
el círculo crítico completo: centro (34.121, 43.254), y unos puntos de
entrada y salida en (29.702, 25.000) y (50.991, 35.000). Ambos puntos están a
**18.781** del centro — lo que de paso corrige el radio, que en la figura se
lee con dificultad. Colocando ese círculo exacto sobre esta geometría, OGR
corta el terreno en:

```
    x = 29.703 .. 50.991       (publicado: 29.702 .. 50.991)
```

**Un milímetro.** Si la topografía de las capas estuviera mal leída, el
círculo no podría daylightear donde dice la referencia. La geometría no es
una interpretación plausible: está verificada contra un dato independiente
del factor de seguridad.

## Materiales

| | c′ (kN/m²) | φ′ (grados) | γ (kN/m³) |
|---|---|---|---|
| Soil #1 (superior) | 0.0 | 38.0 | 19.5 |
| Soil #2 (intermedia) | 5.3 | 23.0 | 19.5 |
| Soil #3 (inferior) | 7.2 | 20.0 | 19.5 |

Sin presiones intersticiales.

## Resultado

| Método | Publicado | OGR | Error |
|---|---|---|---|
| Bishop simplificado | 1.406 (media de 16) | 1.4065 | **0.04 %** |

Tolerancia 1.5 %, que cubre la distancia entre la media (1.406) y el valor
arbitrado (1.39), un 1.1 %.

## Lo que este caso NO valida

Sobre el **mismo círculo publicado**, con la geometría ya verificada al
milímetro, Bishop cae a 0.13 % del valor de referencia pero Spencer sale un
2.3 % alto y GLE un 1.4 %. No es una diferencia de búsqueda: es el mismo
círculo. Por eso `esperado.json` solo declara Bishop.

Está documentado con evidencia en
`docs/audits/spencer_gle_interslice_v179.md`. Este caso es, de hecho, el que
más nítido lo deja, porque la referencia separa aquí Spencer de Bishop un
2.1 % y nosotros los juntamos.

## Si falla

No toques el caso.
