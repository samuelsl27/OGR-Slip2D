# OGR Slip2D v0.1.268

**La función de contenido de agua del transitorio se ve y se edita con todos
los modelos de permeabilidad (D191).** θs, θr, α, n, m y Ss están en un grupo
común del diálogo de propiedades hidráulicas, y cada uno mueve el transitorio.
La retención de van Genuchten con cualquier modelo queda **declarada** como
convenio de OGR: lo que decía el docstring («la referencia la mantiene
separada») era falso, y la lectura literal de la ayuda (almacenamiento
γw·mv constante) queda **refutada por la medida**. Además entra el test de
Celia et al. (1990), que los prompts daban por existente y no existía.
Ningún número del motor cambia.

## 0. Lo que se encontró

### Lo que dice la referencia

- **θs, θr y mv son comunes a todos los modelos.** α, n y m son solo del modelo
  van Genuchten.
- **mv se presenta como la pendiente de la curva de contenido de agua** que
  necesita el transitorio, sin fórmula.
- **La versión 6 metía la curva de contenido de agua dentro de la función
  elegida**, con una pestaña propia en la de usuario.
- **Ningún texto dice que una curva de van Genuchten sirva a todos los
  modelos.** El docstring de `water_content` lo atribuía a la referencia, y
  es un convenio de OGR.

### La puerta de medida (en `_auditoria/P6_0268/` del banco)

**Tres almacenamientos no saturados**, contrastados con las figuras publicadas
(Slide y FlexPDE de Pentland et al. 2001), rasterizadas y digitalizadas a
30 px/m:

| Medida | vG α 0,036 (banco) | vG α 3,6 | Ss = γw·mv constante |
|---|---|---|---|
| 17, freática a 16 383 h en x = 38 (figura: 2,57) | **2,62** | sin cruce | 2,06 |
| 17, freática a 16 383 h: x en y = 6 (figura: 30,0–31,1) | **30,4–30,8** | 26,8 | 28,3 |
| 17, frente a 15 h: x en y = 8 (figura: 16,6–17,1) | 18,3 | **16,6–17,0** | **16,6–17,0** |
| 18, carga en el talud a 19 656 h (fig. 18.5): error máximo | **0,61 m** | 2,77 m | 5,10 m |

- **La lectura literal, mv constante también sobre el freático, es la que
  peor reproduce** la historia temporal del 18. Queda refutada, y no se añade
  esa opción.
- **α = 0,036 es la mejor en los tiempos largos.** Adelanta 1,5 m el frente
  temprano del 17.
- **Decisión de la propietaria:** convenio de van Genuchten, sin opción nueva.
- **El α por defecto de un material NUEVO es 3,6.** Con él los transitorios 17
  y 18 se alejan mucho de la referencia. No se toca: es también la
  permeabilidad de van Genuchten y movería scripts y proyectos. Va a la ficha
  D275.

### El test de Celia et al. (1990) no existía

El docstring del solver lo cita desde v0.1.30, y los prompts largos de D121 y
D124 lo daban por existente («los tests de Celia», entre lo que no se podía
mover). No había ninguno.

- **Los datos.** El artículo está ya en `Documentacion_Guia` (lo aportó la
  propietaria). Sus datos (13): α = 0,0335 1/cm, θs = 0,368, θr = 0,102,
  n = 2, Ks = 0,00922 cm/s, carga −1000 cm, cabeza a −75 cm, un día. La
  solución de malla densa de su figura 6a se digitalizó corrigiendo la
  inclinación del escaneo.
- **Lo medido sobre la forma.** El transitorio de OGR conserva la masa
  exactamente (razón 1,000000 en todas las corridas). Con elementos de 1 cm
  el frente queda a 0,3 cm de la malla densa del artículo. Con 2,5 cm se
  retrasa 1–3 cm y depende del paso de tiempo: el kr se evalúa en el
  centroide del elemento, donde el artículo promedia la K de los nodos. Es
  una observación, sin ficha.
- **Un paso de tiempo no converge en 50 iteraciones.** Ocurre en cada corrida
  y necesita 54. El test usa 300.

## 1. Lo que cambia

- **El diálogo de propiedades hidráulicas.** Lleva un grupo «Water content
  function (transient analysis)», visible con todos los modelos:
  - **θs, θr y Ss son nuevos.** Ss lleva diez decimales: con seis, abrir y
    aceptar ponía a cero un Ss de 10⁻⁷.
  - **α, n y la m personalizada se mueven a ese grupo** con los mismos
    widgets, porque son a la vez la permeabilidad de van Genuchten y la
    retención de todos los modelos. La página van Genuchten dice con `tr()`
    que los usa.
  - **Una nota dice que es un convenio de OGR.**
  - **Lo que hace inservible el material** (`problems()`) se dice dentro del
    diálogo, sin bloquear ni abrir cuadros modales. Ahí avisa, por ejemplo,
    una curva de usuario vacía.
  - **θs, θr y Ss se ponen en gris sin transitorio**, porque nada más los lee
    (regla 7). La regla vive en `ogr_core/project/rules.py`
    (`transient_storage_is_read`).
  - **Las etiquetas de modelos y suelos pasan por `tr()`**, con su
    traducción. «Simple», «Brooks-Corey», «Fredlund-Xing», «Gardner» y «van
    Genuchten» se suman a la lista de traducciones idénticas permitidas, con
    su razón.
- **`HydraulicProperties.water_content`.** El docstring dice que la retención
  común es un convenio de OGR, con la medida. También el comentario de
  `COMMON_FIELDS` y la nota de `hydraulic_set` en la API.

## 2. Tests

- **`tests/test_retention_dialog_v1268.py`, 12 casos.**
  - **Regla 7 a través del diálogo:** con una curva de usuario, cambiar cada
    uno de θs, θr, α, n, la m personalizada y Ss, y aceptar, mueve las cargas
    de un transitorio pequeño (una columna con el freático dentro y la base
    subiendo) más de 1 cm.
  - **El grupo:** el gris sigue la regla; se ve con todos los modelos; un Ss
    de 10⁻⁷ sobrevive; avisa de la curva vacía.
  - **Discriminación:** con 0.1.267 fallan 8 de los 12.
- **`tests/test_transient_celia_v1268.py`, 3 casos.**
  - todos los pasos convergen;
  - el frente a −2, −5 y −9 m de carga queda a ±1 cm de la malla densa
    (53,5 / 56,6 / 57,4 cm);
  - la razón de balance de masa es 1 a 10⁻⁶.
  - Es validación de un motor que no cambia: pasa también con 0.1.267.

## 3. Banco

- **`referencia.json` de 17–20** con la clave `retencion` {fuente, razon}. Se
  conserva α = 0,036, así que no se mueve ninguna fila.
- **Ficha nueva D275** (el α por defecto), en P6.
- **El banco no se re-corre:** el motor no cambia para los transitorios
  (`storage_at` y `storage_content` son los mismos), y el A/B de 0.1.266 ya
  los dio idénticos al bit en este entorno.
- **Cierres.** `d191()`: CUBIERTO POR TEST. D191 retirada, P6 podado y la
  cadena tachada. La comprobación de cierres de la raíz completa: 0 bajadas.
  Auditorías: 0 ERROR.

## 4. Verificación

- **Suite entera, sin argumentos: 5736/5736** (los 5721 de 0.1.267 más los 15
  nuevos).
- **Lo que queda sin probar:** el diálogo en la aplicación real (`python -m
  ogr_gui`): el grupo común con cada modelo, el gris sin transitorio y la nota
  de *Simple* de 0.1.267. Los tests lo recorren sin pantalla.
