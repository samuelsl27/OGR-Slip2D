# 005 — Arai y Tagyo (1985), ejemplo 3: el mismo talud, con agua

**El primer caso de la carpeta con presiones intersticiales.** Los cuatro
anteriores son todos análisis en seco, así que ninguno de ellos podía
detectar un error en el cálculo de u.

## De dónde sale

> Arai, K. & Tagyo, K. (1985). *Determination of noncircular slip surface
> giving the minimum factor of safety in slope stability analysis.* Soils and
> Foundations **25**(1), pp. 43–51. Ejemplo 3.

Es **exactamente el talud del caso `004`** con un nivel freático añadido, lo
que le da un valor que no tendría por separado: los dos comparten geometría y
material, así que la diferencia entre ellos aísla el efecto del agua y nada
más.

```
    seco (caso 004):   Bishop 1.451 publicado
    con agua (éste):   Bishop 1.138 publicado
```

Un 22 % de caída atribuible solo a u. Si el cálculo de la presión
intersticial estuviera mal escalado, este caso fallaría y el `004` no.

## Geometría

Rotulada con coordenadas sobre la propia figura, nivel freático incluido:

```
Contorno externo (cerrado):
    (0, 0) → (66, 0) → (66, 35) → (48, 35) → (18, 15) → (0, 15)

Nivel freático:
    (0, 15) → (18, 15) → (30, 23) → (48, 29) → (66, 32)
```

El nivel freático coincide con el terreno en el pie y sube por dentro del
talud hasta la cota 32 en el extremo derecho, quedando 3 m por debajo de la
coronación.

## Material

| c′ (kN/m²) | φ′ (grados) | γ (kN/m³) |
|---|---|---|
| 41.65 | 15 | 18.82 |

Presión intersticial **hidrostática** desde el nivel freático, u = 0 por
encima de él.

## Resultado

| | Bishop |
|---|---|
| Arai & Tagyo (1985), publicado | **1.138** |
| Programa comercial de referencia | 1.117 |
| OGR Slip2D | 1.1199 |

Tolerancia **2.5 %**, por el mismo motivo que en el `004`: el valor de 1985 y
los reanálisis modernos discrepan un 1.9 % entre sí, y OGR cae dentro del
grupo moderno (0.26 % del programa de referencia).

## Por qué solo se declara Bishop

Janbu simplificado y Janbu corregido salen aquí un 8.6 % por debajo de los
valores circulares del programa de referencia — **pero sobre otro círculo**:
el mínimo que encuentran está en (29.20, 35.00) R 23.70, mientras Bishop
converge en (29.20, 41.60) R 29.40. Es una superficie más somera, y para
Janbu simplificado eso es un mínimo legítimamente distinto, no un desacuerdo
de método. La referencia además buscó con *auto refine*, no con rejilla.

Distinguir las dos cosas requiere evaluar ambos métodos sobre el mismo
círculo publicado, y el manual **no publica el círculo de este problema**
como sí hace con ACADS 1(c). Sin ese dato, declarar Janbu aquí sería declarar
una comparación entre búsquedas distintas.

Spencer tampoco se declara, por el motivo general:
`docs/audits/spencer_gle_interslice_v179.md`.

## Si falla

No toques el caso. Y si falla **éste y no el `004`**, mira el cálculo de la
presión intersticial antes que ninguna otra cosa: es la única diferencia
entre los dos modelos.
