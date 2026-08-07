# OGR Slip2D v0.1.24 — Changelog

**Lanzamiento:** 21 de julio de 2026
**Desarrollador:** Samuel Sáez López — Estudiante de Doctorado, UPCT
**Licencia:** GPL-3.0

> Release de **corrección de las anomalías de búsqueda** A1, A2 y A4
> documentadas en `AUDITORIA_v0.1.22.md`, más la investigación completa
> de A3 con un filtro de admisibilidad opcional.

---

## 🔴 A1 + A2 — una única causa raíz: signo del límite angular superior

Ambas anomalías (Path Search rechazando el 97 % de caminos con FoS 1.60;
Slope Search dando 1.05 con solo el 23 % de superficies válidas) venían
del **mismo error de una línea** en los dos buscadores:

```python
ang_hi = math.radians(-(max(beta_deg - 5.0, 5.0)))   # ANTES  (mal)
ang_hi = math.radians( max(beta_deg - 5.0, 5.0))     # AHORA  (bien)
```

El *Initial Angle at Toe* documentado tiene como límite superior
**+(β − 5)°**, no −(β − 5)°. En el marco local usado por el código el
eje +x apunta del pie hacia la cresta, de modo que un ángulo **positivo**
significa que el primer segmento **asciende** al adentrarse en el talud
— que es precisamente lo que hace una superficie que aflora en el pie
(su base es tendida en el pie y se empina hacia la cresta).

Con el signo invertido, la ventana admisible colapsaba a un sector de
~5° de direcciones que se hunden abruptamente (`[−45°, −40°]` para una
cara de 45°). **Prueba decisiva**: la tangente del círculo crítico de
referencia en el pie es **+15.5°**, que queda fuera de esa ventana. Es
decir, la superficie crítica verdadera era *geométricamente imposible de
generar*.

### Resultados (caso de referencia, Bishop, mínimo global = 0.882889)

| Buscador | Antes | Ahora | Error vs ref. | Válidas |
|---|---|---|---|---|
| Slope Search | 1.0487 | **0.8827** | **0.02 %** | 46 → 1036 |
| Path Search | 1.6019 | **0.8681** | (no circular) | 4 → 116 |

Los tres buscadores circulares quedan ahora coherentes entre sí:
Slope 0.8827, AutoRefine 0.8916, Grid 0.8994.

## 🔧 A1 (segunda parte) — "Number of Surfaces" son superficies VÁLIDAS

Según la documentación, el número de superficies pedido es el de
superficies **válidas**: las inválidas se descartan y *no* cuentan.
Path Search generaba `num_paths` **intentos**. Ahora genera hasta
alcanzar `num_paths` válidas, con tope de intentos
(`max_attempts_factor`, 20× por defecto) para que un modelo patológico
no pueda iterar sin fin. `SearchResult.attempts` reporta los intentos
reales.

## 🔵 A4 — versión desincronizada

`ogr_slip2d.__version__` estaba congelado en `"0.1.1"`; ahora sigue a la
versión del paquete.

---

## 🟡 A3 — investigada: artefacto de superficies inadmisibles

Block Search y Simulated Annealing daban críticos ~0.70 (y hasta 0.33 en
algún sorteo) con **varianza enorme entre semillas** (0.68 → 1.28). La
investigación concluye que es un **artefacto**:

- La superficie culpable típica es una **cuña profunda cerrada por un
  segmento casi vertical**: p. ej. vértices
  `(29.1,50) → (47.5,31.9) → (69.8,8.1) → (72.8,18.4) → (79.5,25)`,
  con ángulos de segmento `[−44.5°, −46.8°, +73.6°, +44.7°]`. Se hunde
  17 m por debajo del pie y remonta a 73.6°.
- **No es artefacto de un método**: Ordinary 0.666, Bishop 0.683,
  Spencer 0.683, GLE 0.682 (Janbu 0.326) — todos lo reproducen.
- La documentación de referencia **describe este mismo modo de fallo**:
  una superficie así «no es cinemáticamente factible y el factor de
  seguridad calculado puede ser incorrecto, normalmente **demasiado
  bajo**», y ofrece la opción *Snap Shallow Surfaces to Slope* para
  eliminarla.
- **Criterio discriminante hallado**: un mecanismo físicamente
  aceptable exige fuerzas interdovela **compresivas**. Usando el
  post-procesador de v0.1.22, la superficie degenerada necesita
  **7 de 17 fronteras en tracción con E = −716 kN/m**, mientras que las
  superficies sanas se quedan en el ruido numérico (−15 a −20 kN/m).
  Criterio estándar en la literatura: Krahn (2003), *The limits of
  limit equilibrium analyses*.

### Filtro opcional (desactivado por defecto)

Se añade a **todos** los buscadores el parámetro `reject_tensile`
(con `tensile_tolerance`, 5 % de max|E| por defecto), que descarta las
superficies cuyo campo de fuerzas exige tracción interdovela
significativa.

**Queda OFF por defecto, deliberadamente.** Con el filtro activado
Block Search pasa de 0.683 a 1.091 (semilla 0) y de 0.777 a 1.376
(semilla 2), pero en la semilla 6 no cambia (0.704) y **Simulated
Annealing se queda sin superficies válidas**, porque su recocido se
alimenta de las evaluaciones que el filtro rechaza. Es decir: el filtro
es correcto en su fundamento pero necesita **calibrado y contraste
contra la referencia** antes de activarse por defecto. Se entrega como
herramienta documentada, con la decisión en tus manos.

---

## 📊 Tests

**416 tests, 416 verdes** (+5 desde v0.1.23; suite 100 % desde v0.1.21).

Cobertura nueva:
- `test_a2_slope_search_matches_reference` — Slope Search dentro del 5 %
  de la referencia y > 200 superficies válidas
- `test_a1_path_search_finds_critical_surface` — crítico en rango físico
  (0.6–1.0), no 1.60
- `test_a1_path_search_counts_valid_surfaces` — se alcanzan las válidas
  pedidas y `attempts ≥ valid_count`
- `test_initial_angle_window_includes_reference_tangent` — la tangente
  de referencia (+15.5°) cae dentro de la ventana por defecto
- `TestTensileAdmissibilityFilter` (5 tests) — la degenerada exige
  tracción, la sana no; el filtro rechaza una y conserva la otra; OFF por
  defecto; reenviado correctamente por los cuatro buscadores

### Test corregido

`test_critical_circle_near_grid_centre` → renombrado a
`test_critical_circle_at_least_as_good_as_grid`. Exigía que el centro
del círculo crítico de Slope Search estuviese a < 6 unidades del de una
Grid Search de referencia. La premisa era errónea: la superficie de FoS
tiene un valle ancho y plano (muchos pares centro/radio dan casi el
mismo FoS) y esa malla gruesa (12×12, Δr = 4) **no es verdad de
referencia** — devuelve 1.157 mientras Slope Search encuentra 1.103.
El test penalizaba a la superficie *mejor* por estar en otro centro,
invirtiendo el invariante. Ahora se comprueba la **calidad de búsqueda**
(Slope ≤ Grid × 1.02) y que el círculo esté en el entorno del talud.

---

## 📚 Referencias consultadas

- Documentación de referencia del proyecto: `Path_Search.htm`,
  `Slope_Search.htm`, `Block_Search.htm`, `Optimize_Surfaces.htm`
- Siegel, Kovacs & Lovell (1981), *Random surface generation in
  stability analysis*, J. Geotech. Eng. 107, 996–1002 — origen del
  generador aleatorio de superficies irregulares (vía XSTABL)
- Sharma (1996/2008), *XSTABL reference manual* — "Irregular Surface
  Search" en que se basa Path Search
- Krahn (2003), *The limits of limit equilibrium analyses* — condición
  de admisibilidad de fuerzas interdovela compresivas

---

## ⏳ Siguiente

- **Decisión pendiente (A3)**: activar `reject_tensile` por defecto en
  búsquedas no circulares tras contrastar Block Search contra la
  referencia en el mismo modelo.
- **Fase 1 del plan de agua**: generador de malla FE triangular.
  Decisiones abiertas: librería `triangle` vs. propia; T3 primero.

---

© 2026 Samuel Sáez López — UPCT — GPL-3.0
