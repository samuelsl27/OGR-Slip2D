# 001 — ACADS 1(a): talud homogéneo, tensiones totales

**El primer caso de validación del repositorio con un valor de referencia
publicado**, frente a los que ya había, que comparaban contra la salida de un
programa comercial. La diferencia importa y está explicada abajo.

## De dónde sale

En 1988, la *Association for Computer Aided Design* (ACADS) distribuyó cinco
problemas de estabilidad de taludes, con cinco variantes, entre la profesión
geotécnica australiana y otros países. **Treinta y tres programas** los
resolvieron de forma independiente, y un árbitro publicó tanto el valor de
consenso como la dispersión.

> Giam, S.K. & Donald, I.B. (1989). *Example problems for testing soil slope
> stability programs.* Civil Engineering Research Report No. 8/1989, Monash
> University. Problema **1(a)**.

Éste es el más simple de los diez: un talud homogéneo, análisis en tensiones
totales, sin presiones intersticiales. Se pide el factor de seguridad y su
superficie de rotura circular crítica.

## Geometría

Todas las coordenadas vienen **del enunciado en texto**, no de una figura. Es
la razón por la que este caso se pudo construir y sus vecinos —1(c) y 1(d),
de tres capas— no: sus líneas de material solo están dibujadas.

```
Contorno externo (cerrado):
    (20, 20) → (70, 20) → (70, 35) → (50, 35) → (30, 25) → (20, 25)
```

Es decir: base a la cota 20, coronación a la 35, y una cara de talud de
(30, 25) a (50, 35) — 10 m de altura con pendiente 1:2, β = 26.57°.

## Material

| c′ (kN/m²) | φ′ (grados) | γ (kN/m³) |
|---|---|---|
| 3.0 | 19.6 | 20.0 |

Sin nivel freático y sin presiones intersticiales.

## Búsqueda

La del enunciado: rejilla de centros de **20 × 20 intervalos** entre
(22.8, 42.3) y (43.7, 62.6), con **11 círculos por punto** de la rejilla —
4851 superficies en total. 25 dovelas.

Está guardada en el `modelo.ogr`, así que el runner de casos la usa tal cual:
lo que se valida es el análisis que el proyecto describe, no uno que el test
configure por su cuenta.

## Valores esperados, y por qué éstos

La fuente publica cuatro números distintos, y elegir entre ellos es la única
decisión de juicio del caso:

| Valor | Cuál es |
|---|---|
| **1.00** | Factor arbitrado por el árbitro del estudio |
| **0.991** | Media de los 33 programas |
| 0.993 | Media Bishop de 18 programas |
| 0.987 | Bishop del programa comercial de referencia |

`esperado.json` usa **0.991, la media de los 33 programas**. Dos motivos:

1. Es el valor con respaldo estadístico, no la opinión de un árbitro sobre un
   problema cuya solución exacta nadie conoce.
2. No consagra el resultado de **ningún** programa concreto, ni siquiera el que
   sirvió de guía de interfaz. Un caso de validación que copia la salida de un
   competidor no es una validación: es un empate acordado.

La **tolerancia es 2 %** y no menos, porque la propia fuente no es más precisa
que eso: el valor arbitrado (1.00) y la media (0.991) difieren un 0.9 % entre
sí. Exigir 0.5 % —lo que se le pide a un método LEM sobre un círculo dado—
sería exigirle a la fuente una precisión que no tiene, y el caso fallaría por
la calidad de la referencia y no por la del código.

## Qué protege

Los otros casos del proyecto fijan el **método** evaluando un círculo conocido.
Éste fija la **búsqueda**: el círculo crítico hay que encontrarlo.

Por eso el mismo modelo se usa además en
`tests/test_acads_validation_v178.py` para validar **Slope Search**, que hasta
v0.1.78 no tenía ninguna referencia externa — daba un número, y que fuera el
correcto era una suposición. Contra este caso da 0.9874, un 0.4 % por debajo
de la media publicada y ligeramente más crítico que la propia rejilla, que es
lo que debe hacer una búsqueda dirigida.

## Si falla

No toques el caso. El valor esperado es un hecho citable de 1989; si el código
deja de reproducirlo, lo que ha cambiado es el código.
