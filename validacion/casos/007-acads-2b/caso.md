# 007 — ACADS 2(b): presa de Talbingo sobre un círculo dado

## Fuente

> Giam, S.K. & Donald, I.B. (1989). *Example problems for testing soil slope
> stability programs.* Civil Engineering Research Report No. 8/1989, Monash
> University. Problema **2(b)**.

| Valor | Cuál es |
|---|---|
| **2.29** | Factor arbitrado ← el esperado para Spencer y GLE |
| **2.204** | Media Bishop de 11 programas ← el esperado para Bishop |
| 2.239 | Media de 24 programas (todos los métodos) |

## Por qué este caso existe, y por qué no existía antes

Los seis casos anteriores validan una **búsqueda**: el círculo crítico hay que
encontrarlo. Ninguno puede separar un método de otro, y el `001` lo dice con
todas las letras — «en **este** problema la referencia apenas los separa de
Bishop (0.987 contra 0.986), así que acertarlos no demostraba nada».

Éste es el complementario, y es el que faltaba:

- **El círculo está tabulado en el enunciado** (tabla 6.1 del manual de
  verificación: centro 100.3, 291.0 y radio 278.8), así que no hay búsqueda de
  por medio y el número mide el **método**;
- **las dos referencias publicadas se separan un 3.9 %** — Bishop tiene su
  propia media de 11 programas en 2.204 y el factor arbitrado del problema es
  2.29. Un método de equilibrio completo que devuelva el valor de Bishop
  **suspende**.

Eso último no es hipotético. El Spencer de v0.1.105 daba **2.2088** sobre este
círculo, que es el Bishop de OGR dígito a dígito: un −3.6 % contra el arbitrado
y muy fuera de la tolerancia de este caso. La carpeta no tenía ningún caso capaz
de detectarlo, y por eso el defecto sobrevivió ochenta versiones. Ver
`docs/audits/spencer_gle_interslice_v179.md`.

## Geometría

Las coordenadas de los 26 puntos están **en la tabla 5.2 del enunciado** (el
problema 6 remite al 5 para materiales y contornos). Lo que sólo está dibujado
es **cómo se conectan**: la figura 5.1 numera los puntos sobre el dibujo y la
5.2 los colorea por zona, y entre las dos la conexión queda determinada.

Mismo criterio de admisión que el `003`, y con la misma comprobación de que la
ambigüedad no puede mover un número: escollera, transición y filtro tienen las
**tres** las mismas propiedades (c' = 0, φ' = 45°, γ = 20.4), así que de las
cinco líneas interiores sólo las dos que limitan el núcleo pueden afectar al
resultado, y ésas no son ambiguas.

| Material | c' (kPa) | φ' (°) | γ (kN/m³) |
|---|---|---|---|
| Rockfill | 0 | 45 | 20.4 |
| Transition | 0 | 45 | 20.4 |
| Filter | 0 | 45 | 20.4 |
| Core | 85 | 23 | 18.1 |

## Tolerancia

**2 %**, y la fija la fuente y no el código: el factor arbitrado (2.29) y la
media de los 24 programas (2.239) discrepan entre sí un 2.2 %. Pedir más sería
exigirle a la referencia una precisión que no tiene.

Es la misma tolerancia y el mismo razonamiento del `001`.

## Resultado en v0.1.106

| Método | Referencia | OGR | Error |
|---|---|---|---|
| Bishop simplificado | 2.204 (media de 11) | 2.2088 | +0.22 % |
| Spencer | 2.29 (arbitrado) | 2.2894 | −0.03 % |
| GLE / Morgenstern-Price | 2.29 (arbitrado) | 2.3001 | +0.44 % |
| Janbu corregido | 2.073 | 2.0739 | +0.05 % |

## Lo que este caso NO valida

La **búsqueda**. El círculo se lo dan hecho, a propósito: ésa es la razón de
ser del caso. Para la búsqueda están el `001`, el `002` y el `004`.

## Si falla

No toques el caso. Los valores esperados son datos publicados en 1989.
