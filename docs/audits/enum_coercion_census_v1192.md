# Censo de campos enumerados — v0.1.192 (D154)

Qué hace cada clase del modelo cuando un campo que es una enumeración
recibe una **cadena** en vez de un miembro, construyéndola en código (tests,
guiones, `_tools/`). El cargador de `.ogr` convierte en todas ellas, así que
un modelo leído de disco nunca tiene el problema; lo que se censa es el
camino en código.

> Sin marcas comerciales, según la regla de `docs/reference/`.

---

## 1. Lo que motivó el censo

D154: `Material(pore_pressure="water_table")` guardaba la cadena, toda
comparación `== PorePressureType.WATER_TABLE` salía `False` y el talud se
evaluaba **seco**, sin excepción ni aviso. Sobre el círculo publicado del 059
con Spencer: **1,0886090318268722** con la cadena frente a
**0,5592600533686025** con el enum (+94,6 %). Y `to_dict()` reventaba después
con `AttributeError`, o sea al **guardar**, cuando el número equivocado ya se
había calculado. La ficha pedía, antes de decidir el alcance, mirar si las
demás clases tienen el mismo agujero.

## 2. Cómo se hizo

- **Barrido en tiempo de ejecución**, no una lista a mano: todos los
  `dataclass` de `ogr_core`, `ogr_slip2d` y `ogr_fem2d` cuyos campos están
  anotados con una `Enum`, resolviendo cada anotación campo a campo. Resolver
  las anotaciones de golpe (`typing.get_type_hints`) **perdía `Material` y
  `SupportInstance`**, porque tienen referencias adelantadas que no se
  resuelven en su módulo; el primer barrido dio 13 clases y el bueno **17**.
- **Efecto de la cadena**, ejecutado donde la clase se construye sin contexto
  y leído en el código donde hace falta un modelo entero (se dice cuál es cuál).
- **Llamadores**: grep de construcciones y asignaciones con cadena en el
  repositorio y en el banco (`_tools/`, los 99 `construir_modelo.py` y las
  instantáneas de `Evaluaciones/`). **Cero cadenas** en todos: 55 argumentos
  `pore_pressure=PorePressureType.X` en 31 archivos de tests, 42 en los
  `construir_modelo.py` vivos y 7 en `_tools/`, todos enums o expresiones que
  devuelven un enum.

## 3. Resultado

Ninguna de las 17 clases convierte en el constructor. Por efecto:

| Clase | Campo(s) | Con una cadena | Cómo se sabe |
|---|---|---|---|
| `Material` | `pore_pressure` | **silencioso**: talud seco (+94,6 % en el 059); `to_dict` y `tooltip_html` revientan | ejecutado |
| `SupportInstance`, `SupportPattern` | `orientation` | **silencioso**: cae al `return axis_angle` final (`support_integration.py:935-954`), o sea paralela al soporte | código |
| `SupportInstance`, `SupportPattern` | `force_application` | **silencioso**: `"active"` no es `ForceApplication.ACTIVE` y el soporte se trata como **pasivo** (`support_integration.py:1435`) | código |
| `TensionCrackProperties` | `mode` | **silencioso**: `"filled"` da el nivel en el FONDO de la grieta (4,0) en vez de arriba (10,0); `"percent_filled"` al 50 % igual | ejecutado |
| `LineLoad`, `DistributedLoad` | `orientation` | **silencioso**: `"horizontal"` da (0, −1), vertical, en vez de (1, 0); `"angle_from_horizontal"` a 30° igual; `to_dict` revienta | ejecutado (`LineLoad`) |
| `DistributedLoad` | `distribution` | **silencioso sólo si hay `magnitude_2`**: `"constant"` no es `CONSTANT`, así que `pressure_at` interpola de `magnitude_1` a `magnitude_2` (`loads.py:64`); sin `magnitude_2` devuelve `magnitude_1` y no se nota | código |
| `HydraulicProperties` | `model` | **silencioso**: `"van_genuchten"` da kr = 1,0 a 50 kPa de succión en vez de 0,0103 (97× la conductividad); `to_dict` revienta | ejecutado |
| `HydraulicProperties` | `simple_soil_type` | no medido | — |
| `Boundary` | `btype` | **ruidoso**: `AttributeError` en su `__post_init__` (lee `default_color`). Además se serializa por NOMBRE (`BoundaryType[...]`), no por valor | ejecutado |
| `WaterPressureGrid` | `value_type` | no medido | — |
| `Units` | `system`, `time`, `permeability`, `failure_direction` | no medido | — |
| `SeismicRecord` | `source_unit` | no medido | — |
| `Distribution` | `dist_type` | no medido | — |
| `RandomVariable` | `kind` | no medido | — |
| `Annotation` | `kind` | no medido | — |
| `FocusObject` (`ogr_slip2d`) | `kind` | no medido | — |
| `DxfLayerInfo` | `kind`, `proposed_kind` | no medido | — |
| `NodeBC` (`ogr_fem2d`) | `bc_type` | no medido | — |

**`ProjectSettings` sigue el convenio contrario** y no entra en la tabla: sus
campos «enumerados» (`GroundwaterSettings.method`,
`SearchSettings.surface_type`, `search_method`, `weak_layer_handling`,
`MethodsSettings.enabled_methods`) están anotados `str` y guardan `.value`.
Ahí el error simétrico es pasar un **miembro**: compara distinto y `asdict`
metería un objeto `Enum` en el JSON. La interfaz ya se protege con
`getattr(method, "value", method)` (`grid_dialogs.py:555`, `:590`).

## 4. Respuesta

- **`Material.pore_pressure`: corregido en v0.1.192.** `Material.__setattr__`
  convierte con `PorePressureType(value)` —la conversión del propio cargador,
  así que no es una regla nueva— tanto al construir (el `__init__` del
  dataclass asigna por `setattr`) como en cualquier asignación posterior, que
  un `__post_init__` habría dejado abierta. Un miembro se devuelve a sí mismo;
  una cadena inválida (`"WATER_TABLE"`, `"piezo_line"`, `None`) falla con
  `ValueError` en la línea que la escribe. Test:
  `tests/test_material_enum_coercion_v1192.py`.
- **Las seis clases silenciosas (`SupportInstance`, `SupportPattern`,
  `TensionCrackProperties`, `LineLoad`, `DistributedLoad`,
  `HydraulicProperties`): reportadas como D183, no corregidas** por decisión
  del propietario, para no ensanchar una tanda de cinco fichas. Nadie les pasa
  cadenas hoy, así que su arreglo tampoco movería un dígito; lo que falta es
  revisar antes los valores por defecto por tipo de los soportes
  (`_default_orientation`, `_default_application`) y los lectores tolerantes
  (`fa.value if hasattr(fa, "value") else str(fa)`, `support.py:327`), que
  sugieren que alguna vez circularon cadenas por ahí.
- **`Boundary`: sin cambio.** Falla ruidosamente, que es lo que la ficha pide.
- **Las nueve no medidas**: quedan en D183 con su columna en blanco. Que no
  se haya medido no quiere decir que sean inocuas.

## 5. Por qué el arreglo de `Material` no mueve ningún número

Por identidad y no por muestreo: (1) `PorePressureType(miembro)` **es** el
miembro, así que todo llamador que ya pasaba un enum recibe exactamente el
mismo objeto; (2) el censo de llamadores da **cero** cadenas en el
repositorio y en el banco; (3) el banco carga sus modelos por `from_dict`, que
ya convertía. Lo único que cambia de comportamiento es lo que antes estaba
mal: una cadena válida ahora da el talud mojado, y una inválida revienta donde
se escribe en vez de al guardar.
