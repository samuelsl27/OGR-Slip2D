# OGR Suite v0.1.32 — Changelog

**Lanzamiento:** 2 de agosto de 2026
**Desarrollador:** Samuel Sáez López — Estudiante de Doctorado, UPCT
**Licencia:** GPL-3.0

> **Anomalía A3 resuelta** — pero no como se esperaba. La investigación
> de la documentación de referencia reveló que el mecanismo correcto no
> era el filtro de tracción interdovela que se había implementado
> provisionalmente en v0.1.24, sino dos comprobaciones distintas y bien
> definidas; y que la conclusión correcta es **mantenerlas desactivadas
> por defecto**, por una razón que se puede demostrar con números.

---

## 🔍 Lo que dice realmente la referencia

La documentación (`Advanced_Project_Settings`) define dos comprobaciones
posteriores al cálculo:

**1. Tensile Stress Check.** Puede aparecer tensión normal efectiva
negativa en la base de una dovela, típicamente por presión intersticial
alta o por bases muy inclinadas cerca de la coronación. Cuando ocurre,
«las fuerzas de las dovelas pueden no ser cinemáticamente factibles y el
factor de seguridad puede ser inexacto o, en el peor caso, completamente
inválido». La comprobación:

- se ejecuta **después** de converger, nunca durante la iteración;
- prueba solo un **porcentaje de dovelas contado desde el pie**
  (95 % por defecto), porque las de coronación están legítimamente en
  tracción: son, en realidad, la zona de grieta de tracción;
- admite tensión de tracción **cero** para todos los criterios de
  resistencia **salvo** Hoek-Brown, Hoek-Brown Generalizado y
  Shear-Normal Function, que sí tienen resistencia a tracción finita;
- invalida la superficie al superarse (la referencia escribe el código de
  error −120 en lugar del factor de seguridad).

**2. m-alpha Check.** `m_alpha = cos α + sin α·tan φ / F` es el
denominador de la fuerza normal en la base. Whitman & Bailey (1967)
señalaron que por debajo de 0.2 el factor resultante deja de ser fiable:
un valor pequeño y positivo infla la normal y la resistencia al corte, y
uno negativo puede dar resistencia negativa y **factores de seguridad
bajos** — que es exactamente nuestro síntoma.

Ambas están **desactivadas por defecto** en la referencia.

## 🎯 Diagnóstico de A3

Contra la superficie degenerada de Block Search (cuña profunda cerrada
por un segmento a +73.6°):

| Comprobación | Degenerada | Sana |
|---|---|---|
| Tracción en base | **0 dovelas** | 0 dovelas |
| m_alpha < 0.2 | **8 de 18** (mín. 0.067) | 0 (mín. 0.410) |

Es decir: **el culpable es el m-alpha, no la tracción**. Mi criterio
provisional de v0.1.24 (tracción interdovela) apuntaba al fenómeno
equivocado, aunque correlacionara.

Con el check de m_alpha, las tres semillas problemáticas quedan
corregidas —incluida la que el filtro anterior no cazaba—:

| Semilla | Antes | Con m-alpha check | Inadmisibles |
|---|---|---|---|
| 0 | 0.6830 | **1.0907** | 2 de 13 |
| 2 | 0.7768 | **0.9577** | 1 de 9 |
| 6 | 0.7044 | **1.1724** | 2 de 12 |

## 🔴 El resultado que zanja la cuestión

Antes de activarlo por defecto se comprobó qué le hace a la búsqueda
circular ya validada. **El círculo de referencia —el que reproduce el
FoS del software de referencia con 0.02 % de error— tiene él mismo
`m_alpha = −0.010` en 5 de sus 25 dovelas.**

Es decir, activar la comprobación por defecto **rechazaría la propia
superficie que la referencia reporta como mínimo global**, y en una
búsqueda circular completa elevaría el crítico de 0.8994 a 0.9503 (con la
referencia en 0.8829), descartando 170 de 450 círculos legítimos.

Conclusión: **el m-alpha check es un diagnóstico, no un criterio de
validez.** Se entrega implementado, expuesto y documentado, pero
**desactivado por defecto**, exactamente como hace la referencia — y
ahora se sabe por qué esa decisión es la correcta y no una convención.

**Recomendación de uso**: actívalo en búsquedas **no circulares**, donde
delata las cuñas degeneradas; déjalo desactivado en circulares, donde
marca superficies perfectamente válidas.

## 🔧 Rediseño como post-filtro

`evaluate_surface` ya **no descarta** la superficie: le calcula su factor
de seguridad, la marca `admissible = False` con una nota, y la deja en la
lista de evaluaciones. Es `SearchResult.critical` quien excluye las
inadmisibles al elegir la crítica.

Esto resuelve el problema que bloqueaba el diseño anterior: **Simulated
Annealing vuelve a funcionar**, porque su recocido sigue recibiendo el
factor de seguridad de cada candidata para orientarse. Y si *todas* las
superficies resultan inadmisibles, se reporta igualmente la de menor FoS
junto con `inadmissible_count`, en vez de devolver un resultado vacío.

Detalle de implementación: la nota va en un campo nuevo
`admissibility_note` y **no** en `error_message`, porque este último
alimenta `is_valid` y marca un cálculo *fallido*, mientras que una
superficie inadmisible tiene un factor de seguridad perfectamente
convergido, solo que físicamente poco fiable.

## 📊 Tests

**591 tests, 591 verdes** (+12 desde v0.1.31; suite 100 % desde v0.1.21).

Cobertura nueva (`tests/test_checks_v132.py`): m-alpha marca la
degenerada y no la sana, **y también marca el círculo de referencia**
(el resultado que justifica el defecto); porcentaje de dovelas contado
desde el pie; detección de tracción cuando existe de verdad; checks
desactivados por defecto; superficies marcadas y **no** eliminadas;
`critical` que las excluye sin acortar la lista de evaluaciones;
degradación cuando todo es inadmisible; y reenvío de parámetros por los
cuatro buscadores.

Un test de v0.1.24 se actualizó con su justificación escrita: asumía el
diseño antiguo (descartar durante la búsqueda) y el criterio de tracción
interdovela, ambos superados.

## ⚠️ Anomalía nueva detectada (sin corregir)

**A5 — Simulated Annealing con Spencer no produce superficies válidas**
(0 válidas), mientras que con Bishop da 45. Es independiente de los
checks (ocurre con ellos desactivados). Pendiente de investigar.

## ⏳ Siguiente

**Análisis probabilístico y de sensibilidad**, el mayor ausente frente a
la referencia: distribuciones estadísticas, muestreo Monte Carlo y Latin
Hypercube, probabilidad de fallo e índice de fiabilidad.

---

© 2026 Samuel Sáez López — UPCT — GPL-3.0
