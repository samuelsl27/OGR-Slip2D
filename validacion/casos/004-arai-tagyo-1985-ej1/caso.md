# 004 — Arai y Tagyo (1985), ejemplo 1: talud homogéneo

## De dónde sale

> Arai, K. & Tagyo, K. (1985). *Determination of noncircular slip surface
> giving the minimum factor of safety in slope stability analysis.* Soils and
> Foundations **25**(1), pp. 43–51. Ejemplo 1.

Es uno de los taludes más reanalizados de la literatura: Greco (1996), Kim et
al. (2002) y Malkawi et al. (2001) han vuelto sobre esta familia de ejemplos.

## Geometría

Rotulada con coordenadas sobre la propia figura del manual de verificación:

```
Contorno externo (cerrado):
    (0, 0) → (66, 0) → (66, 35) → (48, 35) → (18, 15) → (0, 15)
```

Talud de 20 m entre (18, 15) y (48, 35) — pendiente 1:1.5, β = 33.69° — sobre
un estrato de 15 m.

## Material

| c′ (kN/m²) | φ′ (grados) | γ (kN/m³) |
|---|---|---|
| 41.65 | 15 | 18.82 |

Sin presiones intersticiales.

## Por qué la tolerancia es del 3.5 % y no del 1 %

Este es el caso que más honestamente ilustra por qué `validacion/README.md`
insiste en que **la tolerancia va en el caso**: aquí la limita la fuente, no
el código.

| | Bishop |
|---|---|
| Arai & Tagyo (1985), publicado | **1.451** |
| Programa comercial de referencia | 1.409 |
| OGR Slip2D | 1.4136 |

Los dos reanálisis modernos coinciden entre sí en un **0.3 %**, y los dos
quedan un **2.6–2.9 % por debajo** del valor de 1985. Esa distancia no es un
error de nadie en particular: es lo que separa una búsqueda de 1985 —
necesariamente más gruesa, con menos dovelas y menos círculos— de una
búsqueda actual, que encuentra un mínimo más bajo porque puede mirar más
sitios. Un mínimo *menor* es un mínimo *mejor*.

Así que el caso espera **1.451, el valor publicado**, con una tolerancia del
3.5 % que abarca esa discrepancia conocida. Lo que discrimina es una
regresión gruesa, no un cambio de la cuarta cifra.

Las dos alternativas eran peores. Esperar 1.409 sería consagrar la salida de
un programa comercial, que es justo lo que `validacion/README.md` prohíbe.
Inventar un promedio entre ambos sería fabricar una referencia que nadie ha
publicado.

## Qué protege

Es el caso menos exigente de la carpeta, y aun así paga su sitio: es el único
con un talud de 20 m y pendiente 1:1.5, mientras que los otros tres son
taludes bajos y tendidos. Un error que escale con la altura o con la
inclinación aparecería aquí antes que en los demás.

## Pendiente

Los ejemplos 2 y 3 del mismo artículo (problemas #15 y #16 del manual, talud
estratificado con capa débil y talud con nivel freático) tienen la geometría
**solo en la figura y sin rotular**, a diferencia de éste. El del talud
estratificado es el que más valdría: es el que Greco (1996) y Kim et al.
(2002) usan para comparar búsquedas **no circulares**, que hoy siguen sin
ninguna referencia externa.

## Si falla

No toques el caso.
