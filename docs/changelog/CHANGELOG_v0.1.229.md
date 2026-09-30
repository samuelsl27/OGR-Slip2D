# OGR Slip2D v0.1.229

**D215 — Snowden Modified Anisotropic Linear es el modelo que documenta la
referencia, y nace la C/Phi Function.** Hasta 0.1.228 OGR tenía otro modelo
con ese nombre: c1, φ1, c2, φ2 y un solo B, con una transición en coseno
simétrica del ángulo φ. La propietaria decidió el 2026-09-30 adoptar el
modelo de la referencia, registrar «C/Phi Function» como tipo propio,
quitar el coseno, y que un `.ogr` viejo se abra con su equivalente y no
calcule hasta que se revise.

Quinta versión de la tanda D215–D219. El banco no tiene ningún material
Snowden ni C/Phi: cero filas movidas.

Lo que cambia en el banco de verificación (`_tools/`, `_auditoria/`, fichas)
está fuera de git.

---

## 0. Lo que dice la referencia y lo que se decidió

**La documentación de la referencia**, leída de nuevo antes de escribir
nada:
- Snowden se define sobre Anisotropic Linear (Mercer 2012, 2013) con dos
  añadidos: una función de anisotropía **no simétrica** de cuatro parámetros
  (A1, A2, B1, B2) y **funciones de resistencia** no lineales para la
  estratificación y el macizo, cada una «Shear-Normal function» o
  «Cohesion-Friction function».
- Entre ambas hay «a linear transition»: la resistencia de una orientación
  intermedia es «a weighted average determined by the linear transition of
  the anisotropy function».
- Su figura de la función no simétrica pone A1 y B1 a la izquierda de 0 (α
  negativo) y A2 y B2 a la derecha.
- La figura del ángulo mide α desde la dirección 1 (la estratificación)
  hasta el plano, en sentido antihorario.
- «C/Phi Function»: c y φ como funciones de σ′ₙ, y «the interpolation is
  done on the cohesion and friction angle level».

**El convenio de signo, comprobado en el código.** La asimetría hace que el
signo de α importe; en Anisotropic Linear daba igual. La base de cada dovela
es `atan2(dy, dx)` con las dovelas de izquierda a derecha: un ángulo
geométrico antihorario que no depende del sentido de rotura. Así que α =
pliegue(base − buzamiento) es el α de las figuras. Un test de espejo lo fija
de extremo a extremo: el talud reflejado, con el buzamiento reflejado y los
dos lados intercambiados, da el mismo factor en Bishop y Spencer (1e-9). Sin
el intercambio da otro.

| Tema | Qué hace ahora |
|---|---|
| Snowden | `PARAMETERS` = `bedding_angle`, A1, B1, A2, B2. Tiene dos funciones anidadas, `bedding` y `rock_mass`, cada una corte-normal o C/Phi, y τ = (1 − t)·τ_estr + t·τ_macizo, con t = recorte((\|α\| − A)/(B − A)): (A1, B1) si α < 0 y (A2, B2) si α ≥ 0. A = B es un escalón. Sin dovela, la orientación más débil (la decisión de D219). Con el buzamiento local de una superficie enlazada si la hay (D208). Por defecto, una fila C/Phi (5, 15) y otra (20, 30) con A = 10 y B = 30: es el Anisotropic Linear por defecto |
| C/Phi Function | Filas (σ′ₙ, c, φ). c y φ (el ángulo) son lineales en σ′ₙ entre filas, con la fila extrema fuera de la tabla (una decisión: la referencia no lo dice), y τ = c + máx(σ′ₙ, 0)·tan φ. La pendiente es exacta por tramos |
| Archivo viejo | Se abre y guarda sus parámetros tal cual (`legacy_params`), y `to_dict` devuelve el dict viejo intacto. Enseña la forma más próxima del modelo nuevo (A1 = A2 = 0, B1 = B2 = B, una fila C/Phi por función), con una nota que dice que los números no son los de antes. El análisis y la API lo rechazan, y si alguien calcula con él lanza `LegacySnowden`. Solo se convierte con una edición |
| Reglas (`rules.py`) | `c_phi_rows_refusal`: al menos una fila, valores finitos, σ′ₙ estrictamente creciente, c ≥ 0 y 0 ≤ φ < 90. `snowden_refusal`: 0 ≤ A ≤ B ≤ 90 a cada lado, y cada función corte-normal o C/Phi con una tabla válida. `Refusal` gana `cause`, para que la interfaz diga qué función y por qué |
| Coeficientes (D224) | Snowden factoriza cada función por su propio modelo (la transición es lineal en las dos resistencias, así que dividir las dos divide la mezcla). La C/Phi divide la c y la tan φ **interpoladas** con dos divisores que solo pone la copia de análisis, y no fila a fila: φ se interpola como ángulo, y factorizar la tan φ de cada fila solo dividiría exactamente en las filas. Snowden deja de ser la excepción de la identidad F_d = F/γ |
| Una función que no se construye | No impide abrir el archivo: la regla la rechaza, y calcular con ella lanza `IncompleteSnowden` |

## 1. Los cambios

- **`ogr_core/materials/builtin_models.py`:**
  - `CPhiFunction`, registrada;
  - `SnowdenModifiedAnisotropicLinear` reescrita, con `SNOWDEN_LEGACY_NOTE`,
    `LegacySnowden` e `IncompleteSnowden`.
- **`ogr_core/project/rules.py`:** `c_phi_rows_refusal`, `snowden_refusal`,
  las dos ramas en `strength_model_refusal` y `Refusal.cause`.
- **`ogr_gui/dialogs/material_properties_dialog.py`:**
  - la tabla `cphi` en las unidades del proyecto;
  - los botones «Bedding Strength Function...» y «Rock Mass Strength
    Function...», con un resumen de cada función;
  - `StrengthFunctionDialog`: elegir tipo y tabla, con los mismos controles
    que el diálogo de materiales. Una tabla sin tocar vuelve exacta, y los
    tests lo manejan sin `exec()`;
  - la carga, el aviso del archivo viejo, `_ok` y `_refusal_text` (el
    texto de la causa detrás del de la función);
  - las fórmulas.
- **`ogr_gui/i18n/__init__.py`:** dieciséis entradas.
- **`ogr_mcp/guide.py`:** 22 modelos, y cómo se escriben C/Phi y Snowden.

## 2. Tests

- **`tests/test_snowden_reference_v1229.py` (38 casos):**
  - la función a mano en los dos lados y las tres zonas, con funciones que
    dependen de σ′ₙ y se cruzan;
  - los lados no son iguales, el escalón A = B, el buzamiento local y un
    eje que apunta a −x;
  - sin dovela, la orientación más débil;
  - **la identidad con Anisotropic Linear**, a 1e-12 en todo ángulo y σ′ₙ
    y en los nueve métodos;
  - el espejo del modelo y el del talud;
  - la regla 7: A1 ≠ A2 y cada función mueven el factor;
  - las reglas, el análisis por nombre y la API;
  - el archivo viejo: va y vuelve, forma más próxima, rechazo, no calcula,
    una función rota no impide abrirlo, y una variable aleatoria sobre c1
    queda «unwritable»;
  - la C/Phi: a mano, interpola el ángulo, una fila es Mohr-Coulomb, la
    pendiente, los divisores de diseño y la regla;
  - el diálogo: funciones enseñadas y conservadas, el subdiálogo sin
    `exec()`, sus rechazos, el cambio de tipo, el archivo viejo que no se
    convierte hasta editarlo, la tabla C/Phi en psf y la guarda de
    traducciones;
  - F_d = F/γ.

  Contra 0.1.228 fallan 37 de 38:
  - 21 porque el modelo viejo no tiene los parámetros nuevos (era otro
    modelo con el mismo nombre, que es el defecto);
  - 13 por símbolo;
  - 3 por comportamiento.

  Pasa el control: el dict viejo va y vuelve.
- **Cambian a propósito:**
  - `test_strength_models_v115.py::TestSnowden`: `test_cosine_midpoint` pasa a
    `test_linear_midpoint`;
  - `test_snowden_bedding_v1218.py`: el material pasa a ser la forma más
    próxima del de antes, y el caso bit a bit lee `weight` y `_blend`
    (`_c_phi` ya no existe); lo que protege no cambia;
  - `test_design_factors_categories_v1226.py`: Snowden deja de ser la
    excepción de la nota y de F_d = F/γ.

## 3. El banco

- **D215 cerrada con `d215()`.** Sus comprobaciones van por separado para
  que, contra un árbol viejo, cada una falle por lo que es. Comprueba:
  - la función a mano en los dos lados y las tres zonas;
  - la identidad con Anisotropic Linear en Spencer;
  - el archivo viejo;
  - la C/Phi;
  - que no quede coseno y que los `PARAMETERS` sean los de la referencia.

  Contra 0.1.228, NO SE SOSTIENE, también por comportamiento: el archivo
  viejo se acepta sin rechazo.
- **`d208()` actualizada, y su afirmación sigue en pie.** Su material es
  ahora la forma más próxima del de 0.1.218, y la comprobación de código
  mira la llamada a `_local_bedding_deg`.
- PAQUETES (P4) podado y la cadena de P4 tachada.
- **Cero filas.**

## 4. Caminos equivocados

- **`write_text` en Windows convierte `\n` en `\r\n`.** Mis scripts de
  edición dejaron en CRLF `builtin_models.py` y, en la versión anterior,
  `verificar_cierres.py` del banco. Los dos vuelven a LF, y los scripts
  escriben ahora con `newline="\n"`. Git normalizaba los del repositorio,
  así que no llegó nada a un commit; el del banco, fuera de git, sí llevaba
  CRLF desde 0.1.228.
- **La primera versión de `_segment` de la C/Phi** elegía, en una fila
  interior, el tramo que TERMINA en ella, y su docstring decía el que
  empieza. Se vio al releer antes de ejecutar nada, y quedó en «el que
  empieza», coherente con la primera fila y con lo que hay más allá de la
  última.
- **Un script de edición falló a mitad.** Un test estaba en CRLF en el árbol
  de trabajo (git lo normaliza), y la guarda del script lo detuvo antes de
  escribir. Se normalizó y se repitió.

## 5. Verificación

| Comprobación | Resultado |
|---|---|
| Selecciones dirigidas | 639 casos de las áreas vecinas y 38 de Snowden y C/Phi, en verde |
| Suite entera | 5132 de 5132 |
| `d215()` y `d208()` | CUBIERTO POR TEST; D215 NO SE SOSTIENE contra 0.1.228 |
| `--seco` completo | 168 cierres; 0 bajadas, 0 subidas, 0 nuevas (D208 sigue en CUBIERTO POR TEST) |
| `auditoria_invariantes.py` | 0 ERROR en el 02 y en la raíz |

**Queda por probar a mano:**
- los dos botones de función y el subdiálogo en la ventana real;
- abrir un `.ogr` con un Snowden viejo, ver el aviso y aceptarlo tras
  editarlo;
- una C/Phi en un proyecto imperial.
