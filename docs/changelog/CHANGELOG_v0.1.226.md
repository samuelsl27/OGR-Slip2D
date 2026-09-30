# OGR Slip2D v0.1.226

**D224 — la norma de diseño factoriza cada modelo de resistencia por la
CATEGORÍA de sus parámetros, y no por su nombre.** Con los cuatro
coeficientes de material iguales a γ, el factor de seguridad de la copia
factorizada es F/γ en los nueve métodos. Hasta 0.1.225, la mitad de los
modelos no se factorizaban, y nada lo decía.

Segunda versión de la tanda D215–D219. Ningún modelo del banco tiene la norma
activada (0 de 265 `.ogr` vivos): no se mueve ninguna fila.

Lo que cambia en el banco de verificación (`_tools/`, `_auditoria/`, fichas)
está fuera de git.

---

## 0. Lo que se decidió, y por qué

### El defecto

`design_factors.py` factorizaba un parámetro cuando su NOMBRE estaba en una
lista: `cohesion`, `cohesion_top`, `undrained_strength`, `constant_c` o `c`
entre el coeficiente de la cohesión, y la tangente de `friction_angle`, `phi` o
`friction_angle_top` entre el del rozamiento. Por eso:

| Modelo o dato | Qué le pasaba |
|---|---|
| Anisotropic Linear, filas de la función anisótropa, reglas de Generalized, tablas corte-normal y discreta, SHANSEP, Vertical Stress Ratio, Hoek-Brown (dos), Barton-Bandis, φb, envolventes de desembalse | sin factorizar |
| `undrained_depth_layer`, `undrained_slope_distance` | solo `cohesion_top`: cu(z) = c_top/γ + Δc·z |
| `undrained_depth_datum` | nada (su c se llama `cohesion_datum`) |
| Curva de potencia | solo su `c`, por coincidencia de nombre |
| Undrained | con el coeficiente de la **cohesión** (1,25), no el de cu (1,4 en EN 1997-1, Anexo A, set M2) |
| `factor_resistance` (γR;e, 1,1 en DA2) | en el diálogo, la API y los presets; no se aplicaba en ningún sitio |

Tres nombres de la lista (`undrained_strength`, `constant_c`,
`friction_angle_top`) no existían en ningún modelo.

### La investigación (pedida por la propietaria)

- **La documentación de la referencia.** Su diálogo de coeficientes
  parciales (`partial-factors.png`) tiene cuatro coeficientes de material,
  todos divisores: «Effective cohesion c′», «Effective friction tan(phi)»,
  «Undrained strength cu» y «Shear strength (other models)». Su tutorial de
  Eurocódigo 7 (Tutorial 21) da F = 1,37 y, con DA1-C2, Γ = 1,096 = 1,37/1,25.
- **Frank et al. (2004)**, *Designers' Guide to EN 1997-1*, §11.5, pp. 199–201:
  la reducción de resistencia divide c′ y tan φ′ por el mismo f, y el factor
  de sobredimensionado es ODF = F/(γG·γR;e).
- **La práctica documentada de otro programa de equilibrio límite** (manual de
  2022, §12.3, Tabla 12-1): las mismas cuatro categorías, con la resistencia
  entera para las envolventes curvas (corte-normal, Hoek-Brown generalizado,
  bilineal), la succión con tan φ′, y un «Earth Resistance» que divide todo el
  numerador del F.
- **El EC7 de 2004 no da un coeficiente por parámetro para envolventes
  curvas.** Lo confirman Nilsen (2017) para Barton-Bandis, la propuesta de un
  factor sobre el GSI (Procedia Engineering, 2017) y Zhao (2019).

Las fuentes están en `referencias/Documentacion_Guia/`, ordenadas y con su
`INDICE.md`.

### Lo elegido

**Las cuatro categorías de la referencia.** Cada modelo dice a cuál
pertenecen sus parámetros en un método propio,
`StrengthModel.design_factored(MaterialFactors)`, y no en una lista. La lista
de D165 se quitó precisamente por eso, y un test prohíbe esos conjuntos.

| Categoría | Modelos |
|---|---|
| c′, tan φ′ | Mohr-Coulomb, Drained-Undrained, Anisotropic Linear, filas de la función anisótropa |
| cu | Undrained; los tres por profundidad (c de referencia, gradiente y tope); SHANSEP (A, S, su_min); Vertical Stress Ratio (K, min_strength) |
| τ entera («other models») | corte-normal y discreta (τ de la tabla); curva de potencia (c, a, tan W); hiperbólica (c∞, tan φ0) — exactas por parámetros; Hoek-Brown (dos) y Barton-Bandis — con un divisor de τ que solo pone la copia de análisis |
| por recursión | reglas de Generalized (la referencia: los coeficientes se aplican a los hijos) |
| — | Infinite, No strength |
| material | φb con tan φ′; las dos envolventes de desembalse como c′ (intercepto) y tan φ′ (pendiente) |

- **Un modelo que no declare nada** (un complemento escrito después) se queda
  como está, **con una nota**.
- **γR;e divide las cuatro categorías**, que es dividir todo el lado resistente.
- **Presets** (EN 1997-1, Anexo A): el set M2 lleva γcu = 1,40.
  - **γτ = γφ′ (1,25) es una decisión:** el EC7 no lo define. Se apoya en la
    equivalencia de reducción de resistencia, se escribe así y se puede
    cambiar en «Personalizado».
- **Archivos anteriores a 0.1.226:**
  - con una norma con nombre, toman los dos factores nuevos de su preset;
  - con una personalizada, la cu sigue con el factor de la cohesión (lo que
    tenía) y γτ = 1: los números propios del usuario no se adivinan.
- **Lo que la norma pide y esta versión no hace, se DICE.** El coeficiente de
  acciones permanentes no se aplica: el peso del suelo y las cargas
  permanentes no lo llevan, y todas las cargas toman el variable (D226). Ahora
  es una nota del informe, que llega también a la CLI (antes solo imprimía el
  resumen).

## 1. Los cambios

- **`ogr_core/materials/strength_model.py`:**
  - `MaterialFactors`, `FactoredStrength` y `tan_factored_angle`;
  - `StrengthModel.design_factored`, que por defecto deja nota;
  - `_with_params`.
- **`ogr_core/materials/builtin_models.py`:**
  - `design_factored` en cada modelo;
  - `_DesignDivisor` para Hoek-Brown (dos) y Barton-Bandis: divide en su
    `shear_strength`, viaja en `to_dict` y es 1, bit a bit, fuera de la copia;
  - `_factor_params` y `_factor_points`.
- **`ogr_core/project/design_factors.py`:**
  - `apply_design_factors` por categorías, más φb y las envolventes de
    desembalse;
  - `material_factors`;
  - la nota del factor permanente;
  - `factor_friction_angle` delega en `tan_factored_angle`.
- **`ogr_core/project/settings.py`:**
  - `factor_undrained`, `factor_shear_strength` y `FACTOR_FIELDS` (una sola
    lista para los presets, la API y el catálogo);
  - presets de 8 columnas;
  - `DesignStandardSettings.from_dict`, con la migración.
- **`ogr_api/settings_schema.py` y `ogr_api/catalog.py`:** leen
  `FACTOR_FIELDS`.
- **`ogr_gui/dialogs/project_settings_dialog.py`:** dos filas nuevas, con su
  traducción.
- **`ogr_cli/__main__.py`:** imprime las notas del informe.

## 2. Lo medido

- **F_d = F/γ con γ = 1,3 en los nueve métodos**, sobre un círculo fijo, para
  Mohr-Coulomb, Anisotropic Linear, Generalized de hijos Mohr-Coulomb, SHANSEP,
  el modelo por cota y Hoek-Brown generalizado. El peor caso es 5,1·10⁻¹⁰
  (Corps 1 sobre Hoek-Brown), la tolerancia de la propia iteración.
- **γR;e = 1,1 da F/1,1 a 1e-9.** En 0.1.225 daba F sin cambiar
  (1,48634 = 1,48634).

## 3. Tests

- **`tests/test_design_factors_categories_v1226.py` (21 casos):**
  - ningún modelo incorporado se queda callado, y un complemento deja nota;
  - un factor 1 no cambia nada, bit a bit;
  - τ_d = τ/γ en todos los modelos y a varias σ′ₙ;
  - F_d = F/γ en los nueve métodos;
  - γR;e;
  - cada categoría a mano: c′ y tan φ′ con factores distintos, cu con el suyo,
    el perfil por profundidad entero, las «other models», el divisor que
    sobrevive a otra copia, φb y las dos envolventes;
  - los presets, DA2 y la migración;
  - las notas y la CLI.

  Contra 0.1.225 fallan 20 de 21: 11 por comportamiento y 9 por símbolo. Solo
  pasa el control de Mohr-Coulomb.
- **Cambia a propósito `tests/test_api_settings_v1194.py`:** comparaba seis
  factores con el preset, que ahora tiene ocho en el orden de `FACTOR_FIELDS`.
- **Sigue en pie, y fija el hueco de D226,**
  `test_m6_v157::test_da1c1_leaves_an_unloaded_model_alone`: la DA1-C1 no toca
  un modelo sin cargas porque el peso del suelo no lleva γG.

## 4. El banco

- D224 cerrada con `d224()`.
- D226 sigue abierta (acciones de la norma), con la nota que ahora la declara.

## 5. Caminos equivocados

- **La primera idea para las envolventes curvas** era rechazar el cálculo
  cuando f_c ≠ f_φ, porque la curva no se reparte entre c′ y tan φ′. La propia
  referencia tiene un cuarto coeficiente para eso: la categoría que faltaba no
  era una regla, era un factor.
- **Un envoltorio que dividiera la τ de cualquier modelo** habría cambiado la
  clase del material en la copia, y con ella lo que preguntan `isinstance` el
  desembalse (que exige Mohr-Coulomb), Janbu y los chequeos. Por eso se
  escalan los parámetros donde es exacto, y solo los tres que no se dejan
  llevan el divisor dentro de su propia clase.

## 6. Verificación

| Comprobación | Resultado |
|---|---|
| Selecciones dirigidas | 420 casos, en verde |
| Suite entera | 5037 de 5037 |
| `d224()` | CUBIERTO POR TEST; NO SE SOSTIENE contra 0.1.225 |
| `--seco` completo | 164 cierres; 0 bajadas, 0 subidas, 0 nuevas |
| `auditoria_invariantes.py` | 0 ERROR en el 02 y en la raíz |
