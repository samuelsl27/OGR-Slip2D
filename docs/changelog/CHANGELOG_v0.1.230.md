# OGR Slip2D v0.1.230

**D219 — Janbu corregido lee el tipo de suelo de los modelos anisótropos en
CADA base, y esos modelos, leídos sin dovela, dan la orientación más
débil.**

Es la sexta y última versión de la tanda D215–D219: las cinco fichas
abiertas de partida están cerradas. El banco no tiene ningún material
anisótropo, y el censo lo confirma: ninguna fila se mueve.

Lo que cambia en el banco de verificación (`_tools/`, `_auditoria/`, fichas)
está fuera de git.

---

## 0. Lo que se encontró y lo que se decidió

**El defecto.** La regla de D80 (0.1.214) da al factor de Janbu el `b1` del
tipo de suelo de todas las bases:

- un solo tipo en toda la superficie da su `b1`: 0,69 solo c, 0,31 solo φ,
  0,50 c y φ;
- tipos mezclados dan 0,50.

`base_soil_type`, sin embargo, clasificaba cada MATERIAL sin dovela. La
lectura sin dovela de la función anisótropa era además la fila de **menor
cohesión**. Así, una tabla con un tramo «solo φ» y otro «solo c» se
clasificaba por una sola fila:

| Superficie | b1 hasta 0.1.229 | b1 según la regla |
|---|---|---|
| Toda en el tramo «solo c» | 0,31 | 0,69 |
| Cruzando los dos tramos | 0,31 | 0,50 |

**Lo que hace ahora** (decisiones de la propietaria del 2026-09-30):

- **Tipo por base.** `base_soil_type(material, slice_)` lee con el contexto
  de ESA base cualquier modelo que necesite la dovela y no sea una de las
  clases que la función ya nombra. Son exactamente los cuatro anisótropos, y
  la regla se escribe sin una lista a mano (la lección de D165).
- **El contexto es el del solver.** La base se lee con
  `SliceContext.from_slice`, movido a `ogr_core` bit a bit desde donde lo
  construía cada método (`BishopSimplified._local_c_phi`), así que el tipo
  sale de lo mismo que calcula el solver.
- **Interruptor.** `janbu.SOIL_TYPE_PER_BASE` es el número 31 de
  `INTERRUPTORES` del banco.
- **Sin dovela, la orientación más débil:**

  | Modelo | Lectura sin dovela |
  |---|---|
  | Función anisótropa | La fila de menor resistencia a esa tensión, no la de menor cohesión |
  | Anisotropic Linear | El mínimo a 0° y a 90° de la estratificación. c y tan φ son lineales en t y t es monótono en el ángulo, así que no hay otro mínimo, sean A y B válidos o no. Es bit a bit lo de antes mientras el macizo sea el más resistente, que es el caso normal |
  | Generalized | El mínimo de sus reglas |
  | Snowden | Ya lo hacía desde 0.1.229 |

**Cambios declarados, a propósito:**

- Un tramo de Generalized con SHANSEP o Vertical Stress Ratio lee la
  tensión vertical de la dovela, que es constante frente a σ′ₙ, y la base
  pasa de «φ» a «c».
- Uno con un modelo no drenado por profundidad puede no tener tipo (cu ≤ 0)
  en alguna base, y esa base no participa.
- El interruptor apagado no reproduce 0.1.229 en la lectura sin dovela de
  los anisótropos. Esa lectura vive en `ogr_core` y ningún interruptor de
  aquí la alcanza. Se prueba directamente con los tests de la lectura más
  débil.

## 1. Los cambios

- `ogr_core/materials/strength_model.py`: `SliceContext.from_slice`.
- `ogr_slip2d/methods/bishop.py`: `_local_c_phi` lo llama.
- `ogr_core/materials/builtin_models.py`: las tres lecturas sin dovela.
- `ogr_slip2d/methods/janbu.py`: `SOIL_TYPE_PER_BASE`,
  `base_soil_type(material, slice_)` y `janbu_correction`, que pasa cada
  dovela. El docstring de `janbu_correction` conserva lo que exige `d80()`.

## 2. Tests

**`tests/test_janbu_soil_type_per_base_v1230.py`** tiene 17 casos:

- **La regla de D80 aplicada a mano** en tablas mixtas: 0,69, 0,31, 0,50 y
  0,50. En cada una se comprueba F_corr = (1 + b1·g)·F_simp, con la forma g
  de la superficie calculada en el test.
- **El ancla:** una función con todas las bases en un tramo da el mismo `b1`
  y el mismo factor corregido que el Mohr-Coulomb de esa fila (1e-12).
- Anisotropic Linear y Generalized repartidos entre tramos.
- Generalized con SHANSEP.
- El interruptor mueve el número, y los modelos sin dovela no se mueven.
- Las lecturas más débiles, a mano.
- `from_slice`, con una dovela real, con un sustituto sin peso y con la
  sonda de D207.

Contra 0.1.229 fallan 13 de 17:

- 8 por comportamiento: el `b1` de las tablas mixtas y las lecturas más
  débiles;
- 5 por símbolo.

Pasan los 4 controles. No cambia a propósito ningún otro test.

## 3. El banco

- **D219 cerrada con `d219()`.** Comprueba en vivo:
  - la regla de D80 sobre tres tablas mixtas, con F_corr = f0(b1)·F_simp a
    1e-12;
  - que el interruptor mueve el `b1` (0,50 encendido, 0,31 apagado);
  - la lectura más débil;
  - el código: `janbu_correction` pasa la dovela.

  Además revisa el censo y la discriminación.
- **Contra 0.1.229, NO SE SOSTIENE, todo por comportamiento.**
- **Censo nuevo, `_tools/censo_tipo_por_base_d219.py`.** Recorre las
  superficies de Janbu corregido del banco (las mismas que el censo de D80)
  con el interruptor apagado y encendido, en el mismo proceso:
  - 0 de 59 superficies movidas;
  - ningún material anisótropo;
  - la fila 048 `resultados_no_reproduce` no se mide, igual que en el censo
    de D80;
  - el control sintético sí se mueve (b1 0,31 → 0,50).
- **`INTERRUPTORES` pasa a 31**, con `SOIL_TYPE_PER_BASE` fechado en 0.1.230.
- PAQUETES (P4) podado y la cadena de P4 tachada.
- Quedan abiertas, reportadas y sin corregir, D226 a D231.

## 4. Caminos equivocados

- **El censo se lanzó antes de subir la versión y registró 0.1.229.** El
  cierre lo ata a la versión de cierre (`_de_cierre`), así que se borró y se
  repitió después de subirla.
- **El primer `--seco` dio una bajada, D166.** Su medida en vivo seguía en
  pie: 1872 en el ejemplo publicado y γ′·h bajo 20 y 45 de agua. Lo que
  caía era su comprobación de código, que buscaba `water_weight` dentro de
  `bishop._local_c_phi`, justo lo que esta versión movió bit a bit a
  `SliceContext.from_slice`. El motor no tenía nada que corregir; el cierre
  se actualizó para seguir al código y acepta los dos sitios, así que sigue
  valiendo contra un árbol viejo. El segundo `--seco` es el de la tabla.

## 5. Verificación

| Comprobación | Resultado |
|---|---|
| Selecciones dirigidas | 708 casos de Janbu y áreas vecinas, y 17 del test nuevo, en verde |
| Suite entera | 5149 de 5149 |
| `d219()` y `d80()` | CUBIERTO POR TEST; D219 NO SE SOSTIENE contra 0.1.229 |
| `--seco` completo | El primero, 1 bajada (D166; ver §4); el segundo, 169 cierres, 0 bajadas, 0 subidas, 0 nuevas |
| `auditoria_invariantes.py` | 0 ERROR en el 02 y en la raíz |

**Queda por probar a mano:** un proyecto con una función anisótropa y Janbu
corregido en la ventana de interpretación, mirando el `b1` que publica.
