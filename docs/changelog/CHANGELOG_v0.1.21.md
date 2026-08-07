# OGR Slip2D v0.1.21 — Changelog

**Lanzamiento:** 30 de junio de 2026
**Desarrollador:** Samuel Sáez López — Estudiante de Doctorado, UPCT
**Licencia:** GPL-3.0

> Release de mantenimiento: se eliminan los **11 fallos preexistentes**
> de la suite, que arrastraban una API obsoleta. **Suite 100% verde por
> primera vez (380/380).**

---

## 🟢 Suite de tests completamente verde (380/380)

Los 11 fallos heredados estaban todos en `tests/test_region_assignments.py`
y respondían a **dos** causas (la segunda quedaba enmascarada tras la
primera):

1. **Firma obsoleta de `MohrCoulomb` (10 tests).** El helper
   `_build_slope_with_horizontal_cut` construía los materiales con la
   API antigua, en la que `MohrCoulomb` llevaba `name`, `phi_deg` y
   `unit_weight`. En la API actual `MohrCoulomb` es un modelo de
   resistencia con solo `cohesion` y `friction_angle`, y es el
   `Material` el que envuelve la resistencia y porta `name`,
   `unit_weight` y `sat_unit_weight`. Reescrito a:

   ```python
   Material(name="Silty clay", unit_weight=18, sat_unit_weight=19,
            strength=MohrCoulomb(cohesion=10, friction_angle=25))
   ```

2. **Mutación de un `Vertex` inmutable (1 test).** Corregido el primer
   error, `test_moving_cut_line_preserves_assignment_if_click_still_inside`
   reveló un `FrozenInstanceError`: el test mutaba `vertex.y = 15`, pero
   `Vertex` pasó a ser un dataclass *frozen* en una versión posterior a
   la que se escribió el test. Como `Polyline.vertices` sigue siendo una
   lista mutable, ahora se reemplazan los elementos por nuevos `Vertex`:

   ```python
   verts[0] = Vertex(verts[0].x, 15)
   verts[1] = Vertex(verts[1].x, 15)
   ```

No se ha modificado código de producción: ambos arreglos están en el
propio test, que se había quedado atrás respecto a la API.

---

## 📊 Tests

**380 tests, 380 verdes** (0 fallos). Sin cambios en el número de tests
respecto a v0.1.20; los 11 que fallaban ahora pasan.

---

## ⏳ Pendiente (próxima iteración)

- Resto de detalles interactivos del visor Interpret (diagrama de cuerpo
  libre ampliado, etc.).
- Desarrollo de funciones de análisis más allá del Interpret.

---

© 2026 Samuel Sáez López — UPCT — GPL-3.0
