# 002 — Yamagami y Ueta (1988): talud homogéneo

**El caso más exigente de la carpeta**, y el único hasta ahora que valida
**dos métodos** contra una referencia de revista.

## De dónde sale

> Yamagami, T. & Ueta, Y. (1988). *Search for noncircular slip surfaces by
> the Morgenstern-Price method.* Proc. 6th Int. Conf. on Numerical Methods in
> Geomechanics, Innsbruck, pp. 1219–1223.

Greco (1996) reanalizó después el mismo talud, lo que da una segunda opinión
publicada sobre la superficie no circular.

La diferencia con el caso `001` importa: aquél se apoya en la media de 33
programas, que es un consenso; éste es un valor **de los autores**, calculado
y publicado en la literatura. Ninguno de los dos es la salida de un programa
comercial.

## Geometría

La figura del manual de verificación lleva **las coordenadas rotuladas sobre
el propio dibujo**, así que no hay que medir sobre una escala:

```
Contorno externo (cerrado):
    (0, 0) → (25, 0) → (25, 10) → (15, 10) → (5, 5) → (0, 5)
```

Talud de 5 m de altura entre (5, 5) y (15, 10) — pendiente 1:2, β = 26.57° —
sobre un estrato de 5 m hasta la cota 0.

## Material

| c′ (kN/m²) | φ′ (grados) | γ (kN/m³) |
|---|---|---|
| 9.8 | 10 | 17.64 |

Sin presiones intersticiales.

## Valores esperados

| Método | Publicado | OGR | Error |
|---|---|---|---|
| Bishop simplificado | **1.348** | 1.3539 | 0.44 % |
| Fellenius / Ordinario | **1.282** | 1.2860 | 0.31 % |

Tolerancia **1.5 %**. Es la más estrecha de la carpeta y se la puede permitir
porque la fuente es un valor calculado y publicado, no una media entre
programas que discrepan.

Que los **dos** métodos acierten importa más que cualquiera de ellos por
separado: Fellenius y Bishop difieren aquí un 4.9 %, así que reproducir los
dos a la vez fija también la diferencia entre ellos, no solo su nivel.

## Qué protege

Como el `001`, fija la **búsqueda**: la superficie crítica hay que
encontrarla. Y añade una segunda propiedad — que la relación entre un método
simplificado y uno de equilibrio de momentos sea la publicada.

## Lo que este caso NO valida

Spencer y GLE **no** están en `esperado.json` a propósito. Sobre este modelo
y sobre los otros dos casos de la carpeta, ambos devuelven prácticamente el
valor de Bishop, mientras la referencia los sitúa por debajo. Está reportado
con evidencia en `docs/audits/spencer_gle_interslice_v179.md`; hasta que se
resuelva, incluirlos aquí sería consagrar el comportamiento que está en duda.

## Si falla

No toques el caso. El valor esperado es un dato publicado en 1988.
