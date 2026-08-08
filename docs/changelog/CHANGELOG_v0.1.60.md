# OGR Slip2D v0.1.60 — Changelog

**Lanzamiento:** 8 de agosto de 2026
**Desarrollador:** Samuel Sáez López — Estudiante de Doctorado, UPCT
**Licencia:** AGPL-3.0-or-later

> **El peso específico saturado pasa a ser opcional** y el diálogo de
> materiales deja de perder los datos al cambiar de material. Por el
> camino apareció una **pérdida silenciosa de datos al guardar** que
> llevaba tiempo ahí.

---

## 🔴 El peso específico saturado se aplicaba siempre

Hasta ahora, `Material.gamma_at()` devolvía `sat_unit_weight` para
cualquier punto bajo el nivel freático, sin excepción. No había forma de
decir «este material tiene un único peso específico». El campo γ_sat
además se mostraba en el diálogo incluso en modelos **sin nivel freático**,
donde no puede afectar a nada: un dato editable que el cálculo ignora.

La formulación de referencia lo trata como una **opción**, y solo la
ofrece si existe un nivel freático que separe la zona saturada de la que
no lo está. Ahora:

- `Material.use_sat_unit_weight` (nuevo, por defecto `False`) decide si
  γ_sat interviene. `gamma_at()` solo lo usa si el punto está bajo el agua
  **y** el material se ha acogido a la opción.
- En el diálogo, la etiqueta de la fila es una **casilla**, habilitada
  únicamente cuando el proyecto tiene un nivel freático. Sin él, la
  casilla queda gris con un tooltip que explica por qué.
- γ_sat es el peso específico **aparente saturado**, no el sumergido, así
  que debe ser mayor que el de la zona no saturada. Si no lo es, aparece
  un **aviso no modal** bajo el campo: se avisa, pero no se decide por el
  usuario ni se bloquea el diálogo.

### Compatibilidad hacia atrás, con cuidado

Todo `.ogr` guardado hasta hoy lleva `sat_unit_weight` y lo estaba usando.
Si el defecto nuevo (`False`) se aplicase también al cargar, **reabrir un
proyecto existente le cambiaría el factor de seguridad sin avisar**. Por
eso `from_dict` hace:

```python
use_sat_unit_weight = data.get("use_sat_unit_weight",
                               "sat_unit_weight" in data)
```

Los archivos antiguos se cargan con la opción activada y dan exactamente
el mismo número que antes; solo los materiales creados a partir de ahora
nacen con la opción desactivada.

### Regla 7: el ajuste tiene que mover el número

El test que lo demuestra no captura ningún valor: usa una **identidad
analítica**. Con el nivel freático por encima de toda la superficie de
rotura, todas las dovelas toman la misma rama y el peso de dovela es
lineal en γ, luego

```
Σ W(opción activada) / Σ W(opción desactivada)  ==  γ_sat / γ     (exacto)
```

Se comprueba también que con γ_sat = γ la opción no mueve nada — si no,
la identidad anterior podría estar pasando por el motivo equivocado — y
que el factor de seguridad cambia de verdad (1.581 → 1.434 en el caso del
test).

### El modelo Ru usaba γ_sat por una vía oculta

`pore_pressure.py` calculaba `u = ru · sat_unit_weight · z` leyendo el
campo directamente, **incluso sin nivel freático en el modelo**. Con la
opción desactivada, eso habría dejado a γ_sat moviendo el resultado por
detrás, que es justo lo que prohíbe la regla 7. Ahora pasa por
`gamma_at(True)`, así que respeta la casilla. Ningún proyecto guardado
cambia, porque todos se cargan con la opción activada.

## 🔴 Los datos se perdían al cambiar de material

`_on_select` solo **cargaba** el material seleccionado; nunca volcaba el
que se estaba abandonando. El único camino de los widgets al modelo era
`_apply_current()`, atado al botón *Apply*. Consecuencia: editar un
material y pinchar otro en la lista descartaba la edición en silencio, y
lo mismo ocurría al pulsar *+ Add* o *− Remove*, que también mueven la
selección.

Ahora el diálogo hace lo que el usuario espera:

- El par `_load(row)` / `_store(row)` sustituye a `_apply_current`.
  `_on_select` **vuelca la fila que se abandona** antes de cargar la
  nueva; `_add_material` y `_remove_material` hacen lo propio.
- El botón **Apply desaparece**. Con el volcado automático ya no le
  quedaba nada que hacer: **OK** confirma toda la lista, **Cancel** la
  descarta.

### Y Cancel no cancelaba

Al investigarlo salió un segundo problema, más serio que el anterior: el
diálogo hacía `self.materials = list(materials)` — copia **superficial**.
Los objetos `Material` eran los mismos del proyecto, así que
`_apply_current()` los mutaba directamente y **Cancel solo descartaba las
altas y bajas de la lista, nunca las ediciones de campos**.

Corregido con copias profundas de trabajo. La copia se hace con
`copy.deepcopy`, y esa elección tiene historia (abajo).

## 🔴 Guardar un proyecto destruía las tablas de resistencia

**El camino equivocado que resultó ser el hallazgo más grave de la
versión.** La primera idea para las copias de trabajo del diálogo fue
`Material.from_dict(m.to_dict())`, el mismo truco que ya usa el diálogo de
propiedades hidráulicas. Al comprobar que fuese fiel apareció esto:

```
to_dict strength: {'model_id': 'shear_normal_function', 'params': {},
                   'points': [(0.0, 7.0), (200.0, 99.0)]}
after roundtrip : [(0.0, 5.0), (100.0, 45.0), (300.0, 110.0)]
```

La tabla del usuario se sustituía por la tabla de ejemplo. La causa está
en `StrengthModel.from_dict`, que reconstruía el modelo con
`model_cls(**data["params"])` y **nunca despachaba al `from_dict` de la
subclase**, aunque `ShearNormalFunction`, `DiscreteFunction`,
`AnisotropicStrengthFunction` y `GeneralizedAnisotropic` lo sobrescriben
precisamente porque su estado (`points`, `rules`) no cabe en el
diccionario numérico `PARAMETERS`.

Como `Material.from_dict` es el camino de carga de todo `.ogr`, el efecto
real era: **defines tu curva τ–σ′ₙ, guardas, reabres y te la han cambiado
por la de ejemplo, sin ningún aviso**. Arreglado con un despacho explícito
que mira `model_cls.__dict__` (no el atributo heredado, que recursaría
infinitamente).

Dos lecciones que conviene no perder:

1. `to_dict/from_dict` **no** es una copia profunda de propósito general
   aquí. Además de lo anterior, descarta atributos fijados fuera de la
   dataclass, como el `b_bar` de la bajada rápida de embalse. Por eso el
   diálogo usa `copy.deepcopy`, que además conserva el `id` — del que
   dependen las asignaciones de material a región.
2. El test de ida y vuelta de `Material` existía desde el principio, pero
   solo comprobaba nombre, peso, color y `id`. Un test de serialización
   que no comprueba el campo interesante no protege nada. Ahora también
   comprueba γ_sat, la opción nueva y las tablas.

## 🔧 Coherencia de lectura

γ_sat solo se muestra donde puede aplicarse. Con la opción desactivada,
la tabla de propiedades deja la celda vacía, el informe y la CLI escriben
«—» y ni el tooltip de región ni los *data tips* mencionan el campo.

## 🧪 Tests

Archivo nuevo `tests/test_material_sat_uw_v160.py`, 27 casos:

| Grupo | Qué protege |
|---|---|
| `TestTheOptionMovesTheNumber` | La identidad Σ W(on)/Σ W(off) = γ_sat/γ, el no-op con γ_sat = γ, y el cambio de FS |
| `TestGammaAt` | Semántica de la opción y su defecto |
| `TestBackwardCompatibility` | Un `.ogr` antiguo se carga con la opción activa; ida y vuelta del flag |
| `TestRuUsesTheSameSwitch` | u = ru·γ·z frente a u = ru·γ_sat·z, valores analíticos |
| `TestDialogSaturatedCheckbox` | Habilitación por nivel freático y aviso γ_sat < γ |
| `TestDialogNonDestructiveEditing` | Las ediciones sobreviven al cambio de fila; Cancel cancela; no hay *Apply* |
| `TestStrengthTableSurvivesSerialization` | Regresión de la pérdida de tablas |

Actualizados `test_gamma_below_water_uses_sat` (ahora activa la opción de
forma explícita) y `test_serialization_roundtrip` (comprueba γ_sat y el
flag, que antes no miraba nadie).

Los casos de validación **no se tocaron**: `ej1` no define nivel freático,
luego γ_sat nunca intervenía y el defecto nuevo no puede alterarlos.

## 📋 Limitaciones conocidas, anotadas y no corregidas aquí

- **Dovela entera, no partida.** `slicer.py` clasifica cada dovela por la
  posición del **punto medio de su base** frente al nivel freático. Una
  dovela que lo atraviesa recibe un único γ en toda su altura, en lugar de
  γ_sat en el tramo húmedo y γ en el seco.
- **No hay agua embalsada.** 🔴 Un nivel freático dibujado por encima del
  contorno externo debería generar una región de agua embalsada que
  actúa de dos maneras: **peso del agua sobre el talud** (fuerza vertical)
  y **empuje hidrostático horizontal** contra él. Hoy no genera ninguna de
  las dos. Es la diferencia funcional más importante entre un **nivel
  freático** y una **línea piezométrica** —una piezométrica por encima del
  contorno **no** define agua embalsada—, junto con el γ_sat de esta
  versión y la interacción con las rejillas de presión. Sin ella, la
  distinción entre ambas entidades queda a medias en OGR. Pendiente de una
  versión propia. El test de esta versión **no** se apoya en el hueco: su
  nivel freático discurre **sobre la superficie del terreno**, no por
  encima de ella, para que siga siendo válido cuando el embalse exista.
- **γ_sat como variable aleatoria.** `random_variables.py` permite
  sortearlo de forma independiente de γ. La referencia mantiene la
  diferencia entre las medias en cada muestra. Sin cambios por ahora.

---

© 2026 Samuel Sáez López — UPCT — AGPL-3.0-or-later
