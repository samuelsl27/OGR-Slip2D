# 006 — XSTABL (1999): el filtro de profundidad mínima

**El único caso de la carpeta que ejercita un filtro de superficie**, y esa es
la razón de que exista. Los otros cinco validan métodos y búsquedas; ninguno
comprobaba que un ajuste de *Surface Filter* llegara al motor — y durante
muchas versiones no llegaba.

## De dónde sale

> XSTABL Reference Manual (1999). Ejemplo de retroanálisis de refuerzo:
> talud no cohesivo con carga repartida en coronación. Se pide la fuerza de
> refuerzo que lleva el talud a un factor de seguridad de 1.5, y para ello se
> parte del factor sin reforzar.

El enunciado dice explícitamente que sólo se consideran superficies con una
**profundidad mínima de 2 m**, para quitar de en medio los deslizamientos
superficiales de la cara. Ese dato no es un detalle de la solución: es parte
del enunciado, y sin él el problema publicado no tiene la respuesta publicada.

## Geometría

```
Contorno externo (cerrado):
    (0, 0) → (40, 0) → (40, 17) → (17, 17) → (5, 5) → (0, 5)
```

Talud de 12 m entre el pie (5, 5) y la coronación (17, 17), sobre una banqueta
de 5 m de cota a la izquierda. Carga repartida de **40 kN/m²** sobre la
coronación, de x = 17 a x = 30.

Foco de búsqueda en el pie (5, 5) con tolerancia 1 m: el enunciado dice que
se colocó un punto de foco en el pie, así que sólo se consideran círculos que
pasen por él.

El **límite de talud izquierdo en el pie (x = 5) no es un adorno**: el círculo
publicado pasa por debajo de la banqueta —a x = 0 estaría en y = 2.78— y sale
del modelo por su cara vertical izquierda. Sin ese límite el círculo publicado
se descarta por abandonar la región de suelo, y con él todos los centros a la
izquierda de x ≈ −4.5.

## Material

| c′ (kN/m²) | φ′ (grados) | γ (kN/m³) |
|---|---|---|
| 0 | 36 | 20 |

**Dos de estos tres números no los publica el enunciado**, y decirlo importa
más que el resultado:

- **φ = 36°** se *deduce*, no se supone. El enunciado publica Fr = 1.96 con
  φ del material reforzado = 54.93°, y también los valores de XSTABL,
  Fr = 2.044 con 56.04°. La relación es φ_ref = atan(Fr · tan φ):

  ```
  atan(1.960 · tan 36°) = 54.92°     publicado 54.93
  atan(2.044 · tan 36°) = 56.03°     publicado 56.04
  ```

  Dos ecuaciones independientes y un solo φ que las satisface. No hay margen.

- **γ = 20 kN/m³ no se puede deducir**, y se toma con conocimiento de causa:
  con c = 0 el factor de seguridad apenas depende del peso específico. Sobre
  el círculo publicado, γ de 16 a 22 kN/m³ mueve el factor de 0.7595 a 0.7668,
  un 1 % de recorrido total. Con γ = 20 sale 0.7648, un +0.1 % sobre el 0.764
  publicado.

Esa incertidumbre del 1 % es la razón de que la tolerancia sea **1 %** y no
más estrecha, aunque el error medido sea bastante menor.

## Valores esperados

| | Publicado | OGR | Error |
|---|---|---|---|
| Bishop simplificado | **0.764** | 0.76598 | +0.26 % |

Centro crítico (−10.00, 34.69) frente al publicado (−11.41, 35.26): **1.5 m**,
que es del orden del paso de la rejilla (2 m en x, 2.2 m en y).

## Qué protege

**Que el filtro de profundidad mínima mueve el número.** Con el mismo modelo y
el filtro apagado:

| | FoS | centro | espesor máximo |
|---|---|---|---|
| con `min_depth` = 2 m | 0.76598 | (−10.00, 34.69) | 2.02 m |
| sin filtro | 0.72771 | (−20.00, 45.62) | **0.67 m** |

Sin filtro el mínimo es una lámina de 67 cm en la cara del talud, y su centro
cae **en el borde izquierdo de la rejilla** — que es el otro síntoma de que
la respuesta no es un mínimo sino el mejor de lo que se miró. El error contra
lo publicado pasa a −4.7 %, muy fuera de la tolerancia de este caso: si el
filtro deja de llegar al motor, este caso se pone rojo.

Hay una corroboración bonita del criterio, y no es circular: el **círculo que
publica el manual tiene un espesor máximo de dovela de 2.011 m**, justo por
encima de los 2 m que pide su propio enunciado. Si «profundidad» se hubiera
entendido como profundidad media, o medida normal al terreno en vez de en
vertical, el círculo publicado habría caído por su propio filtro.

## Sobre la rejilla

El problema original se corrió con rejilla 24×24 y 60 incrementos de radio.
Este caso usa **16×16 con 40 incrementos** porque se midió que da el mismo
error (+0.26 %) en la mitad de tiempo, y con el centro crítico *más* cerca del
publicado. Bajar más sí degrada: 12×12 con 30 incrementos se va a +1.44 %.

(El 8×8 vuelve a caer en +0.33 %, y **no** es la razón de nada: entre él y la
rejilla fina los valores intermedios son peores, así que ese acierto es suerte
del muestreo y no convergencia. Elegirlo por el número habría sido dejar que
una medición justificara una decisión que no sostiene.)

## Si falla

No toques el caso. El valor esperado es un dato publicado en 1999, y el
enunciado que lo acompaña incluye el filtro de 2 m.
