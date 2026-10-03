# OGR Slip2D v0.1.249

**D231b: las juntas de «Angle or Surface» pueden seguir una superficie
anisótropa del modelo, y se cierra D231.** En 0.1.248 cada junta tenía un
ángulo fijo. Ahora puede nombrar una superficie anisótropa. En cada base de
dovela toma la orientación de la superficie en su punto más cercano y, cuando
ese punto es un vértice, la del segmento dibujado primero. Después se calcula
como una junta por ángulo.

Octava versión de la tanda D226–D232, que cierra D231 (0.1.248 y 0.1.249).

## 0. Lo que se encontró, y dónde

- **Banco:** 0 de 230 modelos con una superficie anisótropa, y ninguno con
  Generalized. El cambio no puede mover un número del banco.
- **La regla de la referencia** para una junta por superficie: «The point on
  the anisotropic surface that is closest to the given slice base is found,
  and the angle of the anisotropic surface at that point is taken as the
  angle of anisotropy for the given slice base». Es la regla que OGR aplica a
  las superficies anisótropas desde 0.1.126 (`anisotropy_angle_at`), en el
  centro de la base. Los soportes la leen igual desde D228, así que se
  reutiliza tal cual y no hay nada que decidir.
- **Un test que estaba mal escrito.** El caso del vértice tomaba un punto
  cuyo punto más cercano no era el vértice, sino el interior del segundo
  tramo. El motor tenía razón. Se cambió el punto por uno que cumple las dos
  condiciones: antes del principio del segundo tramo y pasado el final del
  primero.

## 1. El motor

- **`SliceContext.surface_angles`**: {id de superficie: orientación}.
  - El rebanador lo mide en el centro de cada base, con
    `joint_surfaces(project)` una vez por superficie de deslizamiento, y lo
    guarda en `Slice.surface_angles`.
  - Los soportes lo miden en su punto (`joint_surface_angles_at`, en
    `_soil_reading` y en `equivalent_c_phi_at`; `_PointAsSlice` gana el
    campo, el último y None por defecto).
- **`GeneralizedAnisotropic`** con `definition = "surface"`: cada junta
  nombra su superficie (`surface_id`) y `_joint_angle` lee su orientación del
  contexto. Si no la hay (la superficie no está, o no hay base), lanza: el
  modelo no contesta con un ángulo que nadie dio. Sin dovela, el mínimo de
  la base y las juntas, como antes.
- **Reglas:**
  - `generalized_angle_or_surface_refusal` deja de rechazar «surface» y pide
    a cada junta por superficie que nombre la suya;
  - `generalized_surfaces_refusal(material, project)`: la superficie tiene
    que estar en el modelo. La preguntan el análisis, la API y el diálogo;
  - `surface_in_use_refusal(project, id)`: no se borra una superficie que lee
    una junta. La preguntan la API (Conflict, con la pista) y la ventana (un
    aviso en la barra de estado; la superficie se queda).

## 2. La interfaz y la API

- **Diálogo de materiales.** «Superficie» se puede elegir cuando el modelo
  tiene una superficie anisótropa; sin ninguna sigue en gris y la pista dice
  que se dibuje antes. La tabla pasa a Superficie anisótropa | A | B |
  Material, con un desplegable de las superficies del modelo. Lo que la tabla
  no enseña (el ángulo de una junta por superficie, la superficie de una
  junta por ángulo) se conserva, así que volver a «Ángulo» recupera los
  ángulos. Una junta que sigue una superficie que ya no está se rechaza al
  aceptar, con su razón.
- **Las razones de «Angle or Surface» se traducen** en el diálogo: base y
  juntas sin resistencia, A y B, la superficie que falta. En 0.1.248 salían
  en inglés.
- **API y MCP.** `definition: "surface"` y `surface_id` por junta. Borrar una
  superficie en uso es un Conflict. La guía del MCP lo explica.

## 3. Tests

**`tests/test_generalized_surface_joints_v1249.py`** (9 casos):

- **Identidad:** una superficie recta a 20° es la junta a 20°, en los nueve
  métodos (1e-12). Las dovelas llevan la orientación (1e-13).
- **La regla de la superficie:** en un quiebro manda el segmento dibujado
  primero, y dibujarla al revés cambia la resistencia allí. Sin base, el
  modelo lanza y lo dice; sin dovela, el mínimo.
- **Soportes:** en una superficie plegada, cada punto lee su orientación
  local (1e-12), y los dos tramos dan resistencias distintas.
- **Reglas, archivo y diálogo:** la superficie que falta se rechaza antes del
  análisis; borrar una en uso lo rechazan la API y la ventana; el archivo la
  guarda; el diálogo la edita y conserva el ángulo.

**Discriminación** contra `git archive` 2935bbd (0.1.248), con el runner de
ese árbol: **8 de 9 fallan**. Varios fallan por comportamiento: la
superficie recta lanzaba «not implemented», el soporte no podía leer el suelo
y «Superficie» estaba deshabilitada. El que pasa es el ida y vuelta del
archivo, que 0.1.248 ya guardaba tal cual.

**Cambia a propósito** una aserción de
`test_generalized_angle_or_surface_v1248::test_its_codes`: `definition =
"surface"` sin superficie ya no es «no implementado»
(`generalized_aos_surface`), sino «la junta tiene que nombrar su superficie»
(`generalized_aos_joint_surface`).

## 4. El banco

- **A/B árbol contra árbol de todo el 02** (`_auditoria/P4_0249/ab_d231b.py`,
  2935bbd frente a este): 194 modelos, **0 de 1821 números distintos**.
- **`d231()`**, CUBIERTO POR TEST. Comprueba en vivo:
  - una junta A/B es Anisotropic Linear;
  - el Tutorial 20 con las dos entradas da el mismo Bishop sobre el círculo
    crítico, a menos de 0,5 % de 1,478;
  - una superficie recta es su ángulo.

  Comprueba además el censo, los dos A/B, la búsqueda del Tutorial 20 con
  las dos entradas y las dos discriminaciones. Contra los motores de 0.1.248
  y 0.1.247 dice NO SE SOSTIENE.
- **Ciclo de cierre:**
  - `verificar_cierres.py` entero: 219 cierres y 0 bajadas;
  - instantánea `Evaluaciones/0.1.249`;
  - D231 retirada al índice, podada de `PAQUETES` y tachada en la cadena
    P4, que queda con D249;
  - prompts regenerados (42);
  - auditorías con 0 ERROR en el 02 y en la raíz;
  - instantánea rehecha con `--forzar`;
  - `--seco` completo después de retirar.
- **La tanda D226–D232 queda terminada**: D226, D227, D228, D229, D230, D231,
  D232 y D233 cerradas. De ella nacieron D249 (Ru y la columna) y D250 (la Auto
  Refine no circular), abiertas.

## 5. Lo que se reporta y NO se corrige

- **«Closest» por superficie** compara los desfases con las orientaciones
  locales de cada superficie. Si dos superficies se cruzan, la más próxima
  puede cambiar de una base a la de al lado. Es lo que la regla dice; se
  anota porque puede sorprender.
- **D250** (la Auto Refine no circular en el Tutorial 20) sigue abierta.

## 6. Verificación

- **Suite entera:** 5513 de 5513, en 61,4 min, con el A/B y la verificación
  de cierres en paralelo parte del tiempo.
- **Selección** de Generalized, anisótropos, Snowden, diálogos y tablas de
  materiales, i18n, catálogo, norma, Janbu, resistencia, MCP, propiedades,
  adherencia, soportes, contornos, rebanador y menús: 1058 de 1058.
- **Test nuevo:** 9 de 9. Discriminación: 8 de 9 contra 0.1.248.
- **Banco:** censo, A/B (0 de 1821), `d231()` y el ciclo de cierre (219
  cierres, 0 bajadas).

**Qué falta por probar:**
- **Un caso publicado con juntas por superficie:** no lo hay; el ancla es la
  identidad con la junta por ángulo y, por ella, el Tutorial 20.
- **El borrado de una superficie en uso desde la aplicación real:** se probó
  el método de la ventana, no un clic.
