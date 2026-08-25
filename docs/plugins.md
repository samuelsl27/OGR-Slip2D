# Extending OGR — Plugin Guide

OGR is built around three independent plugin registries. Adding a new
plugin never requires modifying existing code — just create a new file
and decorate your class.

## 1. Adding a new constitutive model (strength law)

File: `ogr_core/materials/my_model.py`

```python
from ogr_core.materials.strength_model import StrengthModel
from ogr_core.materials.registry import register

@register
class VanGenuchtenShear(StrengthModel):
    MODEL_ID = "van_genuchten_shear"
    DISPLAY_NAME = "Van Genuchten Unsaturated"
    PARAMETERS = {
        "cohesion":       (10.0, "kPa", "Effective cohesion"),
        "friction_angle": (25.0, "deg", "Effective friction angle"),
        "phi_b":          (15.0, "deg", "Matric-suction angle"),
    }

    def shear_strength(self, sigma_n_eff: float) -> float:
        import math
        c = self.params["cohesion"]
        phi = math.radians(self.params["friction_angle"])
        return c + max(0.0, sigma_n_eff) * math.tan(phi)
```

Then import it once at package level (e.g. in
`ogr_core/materials/__init__.py`) so the registry is populated:

```python
from . import my_model  # noqa: F401
```

The new model appears automatically in:
- The *Define Materials* dialog dropdown
- The CLI: `ogr-slip2d-cli strength-models`
- The Bishop / Janbu solvers (via envelope linearisation)

## 2. Adding a new LEM method

File: `ogr_slip2d/methods/spencer.py`

```python
from ogr_slip2d.methods.base import LEMMethod, LEMResult, register_method

@register_method
class Spencer(LEMMethod):
    METHOD_ID = "spencer"
    DISPLAY_NAME = "Spencer"
    SATISFIES_FORCE = True
    SATISFIES_MOMENT = True

    def compute_fos(self, project, surface, slices) -> LEMResult:
        # ... your implementation ...
        return LEMResult(fos=..., converged=True, iterations=n,
                         method_id=self.METHOD_ID,
                         surface=surface, slices=slices)
```

Register it in `ogr_slip2d/methods/__init__.py`:

```python
from .spencer import Spencer  # noqa: F401
```

## 3. Adding a new support type

File: `ogr_core/support/my_support.py`

```python
from dataclasses import dataclass
from ogr_core.support.support import SupportType, register_support
from typing import ClassVar

@register_support
@dataclass
class HelicalAnchor(SupportType):
    TYPE_ID: ClassVar[str] = "helical_anchor"
    DISPLAY_NAME: ClassVar[str] = "Helical Anchor"

    helix_diameter: float = 0.3
    helix_pitch: float = 0.1
    torque_capacity: float = 5000.0

    def force_at(self, distance_from_head, total_length, bond=None):
        return self.torque_capacity  # simplified

    def to_dict(self):
        return {"type_id": self.TYPE_ID, **self.__dict__}

    @classmethod
    def from_dict(cls, data):
        d = {k: v for k, v in data.items() if k != "type_id"}
        return cls(**d)
```

`force_at` is the abstract method — the example used to override
`axial_capacity`, which is only a back-compat alias for it, so the class it
showed could not be instantiated at all.

The example above serialises with `{**self.__dict__}`, which is NOT what the
registered types do: they filter the private attributes and add an `_extras`
sub-dict (`ogr_core/support/support.py:344-352`). Copy the example and the
GUI's own bookkeeping ends up in the `.ogr` file. Write `to_dict` by hand,
naming the fields.

If the capacity depends on the stress state along the reinforcement, declare
`NEEDS_BOND_PROFILE = True` and implement `interface_tau(sigma_v_eff, **ctx)`.
The engine then hands `force_at` a `BondProfile` with the interface strength
already sampled and integrated along the support, built once per analysis
rather than once per trial surface. See `ogr_core/support/bond.py`.

### Optional class declarations (v0.1.122)

Four more class attributes, all read by code outside the type. They exist
because `RetainingWallEFP` needed them and hard-wiring a second
`if TYPE_ID == ...` into the dialog was the alternative:

| Attribute | Read by | What it does |
|---|---|---|
| `TABLE_FIELD` | the Define Support dialog | names a LIST-valued field edited through a table instead of a spin box. It must stay OUT of `PARAMETERS`, like `UserDefined.points` |
| `TABLE_COLUMNS`, `TABLE_TITLE` | the same dialog | the column headers, their accepted range, and the group-box title. Without them the table says "Distance (m)" / "Force (kN)", which is right for exactly one type |
| `PARAMETER_USED_BY` | the same dialog | `{choice: (params it reads,)}` for a type whose first `str` parameter selects a mode. Fields the chosen mode does not read are disabled, because a field that is editable and inert is the same defect as an inert setting and harder to spot |
| `MEASURED_FROM_TOP` | `compute_support_effects` | measure `distance_from_head` from the HIGHER end instead of from the head. `force_at` never sees the instance, so a profile defined from the crest down cannot work out which end that is; a support declaring this and drawn flat is excluded, not guessed |
| `ALLOWS_PATTERN` | the analysis notes | `False` for a type whose capacity is per metre of slope already, so a row of them would apply it once per member |

A type with a table-valued field must write its own `to_dict`/`from_dict` and
**copy the list** when constructing: JSON has no tuples, and two instances
sharing one list object means editing one edits the other.

## 4. Adding GUI translations

In your plugin's init:

```python
from ogr_gui.i18n import add_translations

add_translations("es", {
    "Van Genuchten Unsaturated": "Van Genuchten Insaturado",
    "Matric-suction angle": "Ángulo de succión matricial",
})
```

## 5. Design rules

- The **core** modules (`ogr_core`, `ogr_slip2d`, `ogr_fem2d`) must
  **never import from `ogr_gui`**. This is what keeps the CLI fast
  and the core testable in headless CI.
- Every mutation of a `Project` from the GUI should go through the
  Command pattern (`ogr_core.project.commands`) so undo/redo works.
- When adding a module that produces results, write them via
  `ogr_core.project.results_io.save_results` so they end up in the
  companion `.h5` file next to the `.ogr` JSON.
