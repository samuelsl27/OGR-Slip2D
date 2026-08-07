# OGR Suite v0.1.40 — Changelog

**Lanzamiento:** 2 de agosto de 2026
**Desarrollador:** Samuel Sáez López — Estudiante de Doctorado, UPCT
**Licencia:** GPL-3.0

> **Back Analysis of Support Force.** Determina la superficie crítica que
> requiere la **máxima fuerza de soporte** para alcanzar un factor de
> seguridad objetivo — el punto de partida natural para dimensionar un
> sistema de sostenimiento.

---

## 🆕 `ogr_slip2d/back_analysis.py`

Fiel a la especificación de la referencia:

- En lugar de iterar para hallar el factor de seguridad, **se fija el
  factor al valor objetivo y se despeja la fuerza necesaria**. Como el
  factor está fijo, la suma resistente se evalúa directamente y la fuerza
  sale en **forma cerrada: sin iteración alguna**.
- La fuerza se supone **horizontal**, aplicada a una **cota** indicada por
  el usuario.
- Solo disponible para **Bishop, Janbu y Janbu Corrected**; se rechaza
  explícitamente para el resto.
- Se analizan todas las superficies y se reporta la que exige **mayor**
  fuerza.
- La fuerza se calcula bajo **ambas hipótesis, activa y pasiva**, y las
  dos se reportan siempre.
- El cálculo es **completamente independiente** del análisis principal:
  ni lo usa ni lo altera (verificado comparando la serialización del
  proyecto antes y después).

### Activa y pasiva

Una fuerza **activa** reduce la acción motora (anclaje pretensado),
mientras que una **pasiva** suma resistencia (bulón sin tesar):

    activa:  F = R / (D − T)   →   T = D − R/F
    pasiva:  F = (R + T) / D   →   T = F·D − R

La pasiva es siempre la mayor para objetivos por encima de 1, y por tanto
la conservadora para diseño.

## ✔️ Validación por propiedades analíticas

En vez de comparar contra números guardados, los tests comprueban
propiedades de la formulación:

| Propiedad | Resultado |
|---|---|
| Fuerza nula al pedir el FoS que ya tiene la superficie | ✓ |
| Objetivo por debajo del actual → cero, no negativo | ✓ |
| Crece monótonamente con el objetivo | ✓ |
| **Activa y pasiva coinciden exactamente en FS = 1** | ✓ |
| Pasiva > activa por encima de 1 | ✓ |

La tercera es especialmente útil como control: `D − R/1` y `1·D − R` son
la misma expresión, así que cualquier desliz algebraico rompería la
identidad.

### La firma de comportamiento que exige la referencia

| Cota | Bishop | Janbu |
|---|---|---|
| 0.0 | 435.32 | 2238.04 |
| 25.0 | 674.51 | 2238.04 |
| 40.0 | 1006.23 | 2238.04 |
| 50.0 | 1497.07 | 2238.04 |

**La cota cambia el resultado de Bishop pero deja Janbu intacto**,
exactamente como especifica la referencia: Bishop parte del equilibrio de
momentos, de modo que la cota fija el brazo, mientras que Janbu solo
considera equilibrio de fuerzas, donde una fuerza horizontal entra igual
se aplique donde se aplique. Se comprueba además que una fuerza aplicada
**a la cota del centro** deja el problema indeterminado (brazo nulo) y se
reporta como tal en lugar de dividir por cero.

## 🔴 Un dato engañoso, detectado y eliminado

La primera versión reportaba un `unsupported_fos` calculado como R/D…
pero con R evaluado **al factor objetivo**, no al convergido. Eso daba
0.916 y 0.981 para una superficie cuyo factor real es 0.883, según el
objetivo pedido: un número que parece un factor de seguridad y no lo es.

En vez de dejarlo, el solver ya **no lo inventa** (queda como NaN, con la
razón escrita en el código) y es el driver quien rellena el campo con el
factor **realmente convergido** de la evaluación, que es el único sitio
donde se conoce.

## 🖥️ Interfaz y ajustes

Acción **Back Analysis of Support Force…** con diálogo para el factor
objetivo, la cota y el método, que reutiliza `build_search` para honrar
los mismos ajustes de búsqueda que un cálculo normal. Los resultados —
fuerza requerida, activa, pasiva, factor sin soporte y número de
superficies— se muestran en la barra de estado. Nuevo
`BackAnalysisSettings` serializado en el `.ogr`.

## 📊 Tests

**773 tests, 773 verdes** (+26 desde v0.1.39; suite 100 % desde v0.1.21).

Cobertura: las cinco propiedades analíticas; comportamiento de la cota en
Bishop y Janbu (y Janbu Corrected), e indeterminación en el centro;
restricción de métodos y objetivos inválidos; corrida completa que
**re-deriva superficie a superficie** para confirmar que la reportada es
realmente la de máxima fuerza; proyecto sin modificar; progreso;
monotonía con el objetivo; y round-trip de los ajustes.

## ⏳ Siguiente

Cobertura de **i18n**, y después el **import DXF** con plan propio.

---

© 2026 Samuel Sáez López — UPCT — GPL-3.0
