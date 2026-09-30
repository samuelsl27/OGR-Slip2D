# OGR Slip2D v0.1.225

**D218 — Generalized Anisotropic deja de dar τ = 0 en silencio, y sus tramos
son inclinaciones ABSOLUTAS de la base.**
- Hasta 0.1.224 una regla cuyo modelo no se podía construir, un ángulo que
  ninguna regla cubría o un material al que el diálogo había borrado las
  reglas dejaban la base **sin resistencia**, sin avisar.

**D216 — Anisotropic Linear interpola tan φ, como escriben las ecuaciones de
la referencia**, y no el ángulo.

Primera versión de la tanda de las cinco fichas abiertas (D215–D219) y de los
hallazgos que salieron al prepararlas; el plan aprobado está en la memoria del
proyecto. Cero modelos del banco usan estos dos modelos: no se mueve ninguna
fila.

Lo que cambia en el banco de verificación (`_tools/`, `_auditoria/`, fichas)
está fuera de git.

---

## 0. Lo que se decidió, y por qué

### D218: las cuatro maneras de llegar a τ = 0

1. **La excepción tragada.** `_model_for_angle` envolvía `StrengthModel.from_dict`
   en `except Exception: return None`, y `shear_strength_ctx` convertía ese
   None en τ = 0. Un id de modelo que ya no existe o un parámetro desconocido
   dejaban la base sin resistencia.
2. **El ángulo sin regla.** Un hueco entre dos tramos daba el mismo cero.
3. **El diálogo (hallazgo A, al preparar la tanda).** `_store` reconstruye la
   resistencia desde los editores, y este modelo no tiene ninguno. Bastaba
   enseñar un material Generalized y pulsar Aceptar para que quedara
   `rules = []`, y con ello τ = 0 en todas las bases.
4. **El pliegue.** El ángulo solo se plegaba a (−90, 90] cuando se restaba un
   buzamiento. Un soporte lee el modelo en el ángulo de su eje (`atan2`, en
   (−180, 180]), así que a 165° no encontraba regla y se quedaba con cero.

Es la clase de D56 y D94: un no-número convertido en un número que parece
bueno.

### D218: las bandas, absolutas

La propietaria pidió investigarlo. La documentación de la referencia describe
dos entradas para este modelo:

- **«Angle Range»**: tramos contiguos de −90 a +90 con un material cada uno,
  sin estratificación ni superficie en el diálogo. Su tutorial del modelo
  (Tutorial 20, p. 20-5) lo dice sin rodeos: «Angles in the dialog are
  measured from horizontal, so 90° represents vertical». Modela una
  estratificación subhorizontal dando a su material la banda −10..10.
- **«Angle or Surface»**: un material base más juntas por ángulo o por
  superficie (una superficie por junta), con transición A/B, coseno o lineal.

OGR implementa la primera. En 0.1.126 le añadió restar el buzamiento de una
superficie anisótropa enlazada, y eso:
- no tiene fuente;
- lo pone en otro marco que la función anisótropa, que la referencia describe
  con las mismas palabras y que 0.1.215 (D195) fijó como absoluta;
- no lo fijaba ningún test con un número.

**Se quita.**
- «Qué modelos leen una superficie» pasa del diálogo a
  `rules.SURFACE_READING_MODEL_IDS`: Anisotropic Linear y Snowden.
- Un Generalized que ya enlaza una superficie **se rechaza hasta revisarlo**
  (`rules.material_surface_refusal`, el molde de D209): sus tramos elegirían
  ahora otras reglas.
- Al guardarlo, el diálogo quita el enlace.
- La entrada «Angle or Surface» queda como ficha nueva, D231.

### D218: qué es un conjunto de reglas válido

`rules.generalized_anisotropic_rules_refusal` fija qué es un conjunto de
reglas válido. Lo preguntan la API, el análisis y el diálogo.

- **Estructura: la de la referencia.** El primer tramo empieza en −90, cada
  uno empieza donde acaba el anterior y el último acaba en +90.
  - Un hueco es un ángulo sin resistencia.
  - Un solape es una regla a la que nunca se llega, porque gana la primera
    (regla 7).
- **Modelos.** Cada modelo, presente y construible.
- **Orden de las comprobaciones.** La estructura va antes que los hijos, así
  que el mensaje «0.1.218» de una tabla antigua anidada sigue ganando.

**El modelo.**
- Calcula con lo que se le dé, y donde antes devolvía cero **lanza**
  `IncompleteGeneralizedAnisotropic`.
- Pliega siempre, y el límite pertenece al tramo inferior con el margen de
  1e-9 grados de la función anisótropa: el ángulo llega en radianes, y
  degrees(radians(−30)) es −29,999999999999996.
- Construye cada modelo hijo una vez y lo guarda mientras su dict no cambie;
  lo compara por valor, así que editarlo en su sitio lo reconstruye.
- Responde por sus hijos a `NEEDS_LAYER_TOP` y `NEEDS_SLOPE_DISTANCE`.
  Hallazgo N: un hijo que mide la cu desde la cara del talud no recibía la
  distancia y caía a su lectura sin contexto sin decirlo.

**El diálogo.**
- `_store` conserva las reglas.
- `_ok` juzga solo las resistencias que esta sesión ha cambiado (y los
  materiales nuevos). Un Generalized que no se puede editar aquí y que solo
  se ha mirado no bloquea aceptar otros cambios; el análisis lo sigue
  rechazando.
- Todavía no hay editor de reglas: llega en 0.1.228 (D218b). Hasta entonces,
  elegir Generalized para un material sin reglas se rechaza con un mensaje
  que dice que las reglas se definen por la API o un script.

### D216

Entre A y B la documentación de la referencia define
c = c1(1 − t) + c2·t y tan φ = tan φ1(1 − t) + tan φ2·t, con
t = (|α| − A)/(B − A) (imágenes `eq_aniso_linear5` y `eq_aniso_linear9`, y
el texto: «the cohesion and the tangent of the friction angle can be
computed»). OGR interpolaba el ángulo: con φ1 = 15° y φ2 = 30°, a t = 0,5 daba
22,5° donde las ecuaciones dan 22,9113369°.

- **Sin rechazo de archivo viejo**, a diferencia de D209: los parámetros
  significan lo mismo y lo que estaba mal era la fórmula. Los extremos no se
  mueven ni un bit.
- **Regla nueva `rules.anisotropic_linear_refusal`**: 0 ≤ A ≤ B. La
  referencia llama a A «an angular range on either side of the bedding plane
  orientation» y a B − A el ancho de la transición.

## 1. Los cambios

- **`ogr_core/materials/builtin_models.py`:**
  - `GeneralizedAnisotropic` reescrito: pliegue siempre, marco absoluto,
    caché, `NEEDS_*` derivados y `IncompleteGeneralizedAnisotropic`;
  - `GENERALIZED_SURFACE_NOTE` nuevo;
  - `AnisotropicLinear._c_tan_phi`: `shear_strength_ctx` usa tan φ
    directamente; `_c_phi_for_angle` sigue devolviendo grados;
  - docstrings al día, también el de la función anisótropa.
- **`ogr_core/project/rules.py`:**
  - `generalized_anisotropic_rules_refusal`, `anisotropic_linear_refusal`,
    `SURFACE_READING_MODEL_IDS`, `reads_anisotropic_surface` y
    `material_surface_refusal`;
  - `strength_model_refusal` los pregunta.
- **`ogr_slip2d/analysis_runner.py`:** `check_analysis_settings` añade
  `material_surface_refusal`.
- **`ogr_api/ops/model.py`:**
  - enlazar una superficie a un modelo que no la lee es un conflicto;
  - cambiar a uno de esos modelos quita el enlace, con una nota (lo que ya
    hacía el diálogo).
- **`ogr_gui/dialogs/material_properties_dialog.py`:** `_store` conserva las
  reglas, `_ok` juzga lo cambiado, textos nuevos en `_TABLE_REFUSALS`, aviso
  del enlace, fórmulas al día y el conjunto de modelos, importado de
  `rules.py`.
- **`ogr_core/materials/material.py`:** comentario del enlace.
- **`ogr_gui/i18n/__init__.py`:** ocho entradas en español.

## 2. Lo medido

- **Plano.** Sobre una superficie plana a 25° todas las bases tienen el mismo
  α, y AL debe ser un Mohr-Coulomb con (c(α), φ(α)). En 0.1.224, con Bishop,
  2,71658 frente a 2,73128; ahora coinciden a 1e-11 en los nueve métodos.
- **El soporte a 165° en Generalized:** 0,0 en 0.1.224; ahora 22,838 kPa, lo
  mismo que a −15°.

## 3. Tests

- **`tests/test_generalized_anisotropic_honest_v1225.py` (31 casos):**
  - los rechazos, uno a uno;
  - el motor lanza;
  - marco absoluto y pliegue;
  - identidades: Generalized de hijos Mohr-Coulomb = la función anisótropa
    con esas filas en los nueve métodos, y un tramo único = el hijo;
  - la distancia al talud del hijo;
  - la caché;
  - la superficie enlazada, en el análisis, la API y el diálogo;
  - el diálogo;
  - un test de guarda para las traducciones de `_TABLE_REFUSALS`, que se
    traducen a través de una variable y el test de cobertura no ve.

  Contra 0.1.224 fallan 24 de 31: 12 por comportamiento y 12 por un símbolo
  que no existía.
- **`tests/test_anisotropic_linear_tan_v1225.py` (8 casos):** las ecuaciones a
  mano, 22,9113369°, los extremos bit a bit, el escalón A = B, la identidad
  del plano en los nueve métodos y la regla. Contra 0.1.224 fallan 5 de 8,
  todos por comportamiento.
- **Cambia a propósito `tests/test_snowden_bedding_v1218.py`, en sus dos casos
  de anidación.** Enlazaban una superficie al material Generalized, cosa que
  ahora se rechaza; ahora fijan el paso del contexto al hijo sobre el propio
  modelo.

## 4. El banco

- Cierran D216 y D218, con `d216()` y `d218()` en `verificar_cierres.py`.
- Se abren como fichas los hallazgos de la preparación:
  - D224 y D225, que se corrigen en 0.1.226 y 0.1.227;
  - D226–D231, reportados y sin corregir.
- Cero filas movidas: ningún modelo del banco usa Generalized ni Anisotropic
  Linear.

## 5. Caminos equivocados

- **La constante escrita a mano del punto medio**, 22,911315°, estaba mal: es
  22,9113369°. La ficha solo daba 22,91°.
- **El test «los extremos, bit a bit»** usaba α = 30° como extremo de la roca.
  degrees(radians(30)) es 29,999999999999996, que cae dentro de la transición
  por un pelo; se usa 35°.
- **`_ok` iba a juzgar los materiales «visitados».** La revisión crítica del
  plan señaló que un Generalized que el diálogo no puede editar bloquearía
  Aceptar solo por haberlo mirado; se juzga lo que ha cambiado.
- **`NEEDS_LAYER_TOP` y `NEEDS_SLOPE_DISTANCE` fueron primero dos
  `@property`.** En la instancia respondían bien, pero en la CLASE devolvían el
  objeto propiedad, que es verdadero. `test_undrained_depth_v1120`, que pide
  que solo el modelo de distancia al talud active ese cálculo caro, lo cazó en
  la suite entera (5015 de 5016). Ahora son un descriptor que responde False a
  la clase y lo que digan los hijos a la instancia; el test no se toca.
- **La superficie en Generalized iba a conservarse como extensión declarada.**
  La investigación no encontró ninguna fuente para restar el buzamiento, y sí
  una que dice que los tramos se miden desde la horizontal.

## 6. Verificación

| Comprobación | Resultado |
|---|---|
| Selecciones dirigidas (archivos tocados) | 397 casos, en verde |
| Primera suite entera | 5015 de 5016: el descriptor de `NEEDS_*`, ver §5 |
| Suite entera tras el arreglo | 5016 de 5016 |
| `d216()` y `d218()` | CUBIERTO POR TEST; NO SE SOSTIENE contra 0.1.224 |
| `--seco` completo | 163 cierres; 0 bajadas, 0 subidas, 0 nuevas |
| `auditoria_invariantes.py` | 0 ERROR en el 02 y en la raíz |
