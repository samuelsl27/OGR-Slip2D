# OGR Slip2D v0.1.196

**Tercera fase del servidor MCP (spec 008, F2).** Un agente ya maneja, sin
abrir la interfaz:

- cargas y sismo;
- soportes;
- la grieta de tracción, el foco y las superficies propias;
- anotaciones;
- DXF, el informe PDF y las transformaciones de contorno.

Alcanza 98 de las 136 acciones de la ventana principal (en v0.1.195 eran 42).
Hay 26 herramientas nuevas: el perfil `full` pasa de 28 a 55 y `compact`
sigue en 14.

Lo que se encontró al dar al agente las mismas acciones que la interfaz:

- **Siete defectos de la interfaz que no mueven números.** Se corrigen aquí,
  por decisión del propietario (2026-09-24), moviendo la lógica al núcleo
  (§2).
- **Uno que sí mueve números: el constructor de regiones no admite huecos**
  (§3.1). Se reporta sin corregir, y la capa de operaciones rechaza lo que
  lo dispara.
- **La cuña con sobrecarga.** Un desfase de 4,4e-5 parecía del motor. En
  realidad venía de cómo lo medía yo (§4).

---

## 1. Qué se escribió

### Operaciones nuevas (`ogr_api/ops/`)

| Módulo | Operaciones |
|---|---|
| `loads.py` | `load_set`, `load_delete`, `seismic_set`, `seismic_record_set`, `seismic_record_delete` |
| `supports.py` | `support_type_set`, `support_type_delete`, `support_set`, `support_pattern_add`, `support_delete`, `support_ungroup` |
| `search_objects.py` | `tension_crack_set`, `focus_set`, `focus_delete`, `user_surface_add`, `user_surface_delete` |
| `annotation_ops.py` | `annotation_set`, `annotation_delete`, `annotation_to_boundary`, `properties_table` |
| `files.py` | `dxf_inspect`, `dxf_import`, `dxf_export`, `report_generate`, `properties_import` |
| `model.py` | `external_reshape` (desfase o polilínea de relleno/excavación), `geometry_cleanup`; `boundary_edit` gana `copy`, `scale`, `rotate` y `simplify` |
| `project.py` | `project_new(template="demo")` |

En total son 54 operaciones, 33 de ellas de edición, y cada una es **un solo
paso de deshacer**. La DXF importada también lo es; en la interfaz no lo es.

El módulo de anotaciones se llama `annotation_ops` y no `annotations`: con
`from __future__ import annotations` en el paquete, `from . import
annotations` devolvía el objeto de `__future__`, no el módulo.

**Cada ajuste se comprueba contra lo que el MOTOR lee, no sólo contra su
tipo**. Es la regla 7 aplicada en la puerta. Se rechaza, con el motivo:

- una carga puntual `normal_to_boundary` o `angle_to_boundary`, porque el
  motor la aplicaría vertical (§3.2);
- `angle_deg` con una orientación que no lo lee;
- `magnitude_end` en una carga constante, y una carga triangular sin él (el
  motor la haría constante en silencio);
- la tolerancia de un foco que no sea punto o tangente;
- `user_angle_deg` sin la orientación `user_defined`;
- un parámetro de soporte que no es campo de su clase, o un token que no
  está entre los suyos. El motor no los comprueba: un pilote trata como
  cortante todo lo que no sea `"ito_matsui"`;
- el valor de agua de la grieta que su modo no lee;
- una superficie propia cuando el tipo de superficie no es circular.

### Movido al núcleo, con la interfaz llamándolo

| Función | De dónde sale |
|---|---|
| `ogr_core.project.demo.build_demo_project` | la demo de la CLI y la de la interfaz, que no eran el mismo modelo (§2) |
| `ogr_core.project.properties_import.import_properties` | `MainWindow._import_properties` |
| `ogr_core.project.rules.set_seismic_records` | `SeismicRecordsDialog.apply` |
| `ogr_core.support.reconcile_support_refs` | `DefineSupportDialog.accept` |
| `ogr_core.geometry.cleanup.inspect_boundaries`, `simplify_boundary`, `model_tolerance` | `act_geometry_cleanup`, `act_simplify_boundary` |
| `ogr_core.geometry.expand_shrink.apply_expand_shrink`, `apply_external_offset` | los dos modos de *Expand/Shrink* |

Además:

- **Los tokens de soporte.** `ogr_core.support.PARAMETER_CHOICES` lista los
  tokens de cada parámetro de texto. El editor conserva sus etiquetas, y un
  test impide que las dos listas diverjan.
- **La identidad de patrón.** `SupportInstance.pattern_id` (nuevo) sólo se
  serializa si existe, así que un archivo antiguo se guarda byte a byte
  igual.

### Resultados «caducados»

`model_hash` deja fuera las anotaciones: el cálculo no las lee, así que
dibujar una cota no invalida un resultado. «Cambios sin guardar» pasa a
medirse con `document_hash`, que sí las incluye.

## 2. Defectos de la interfaz corregidos (no mueven números)

Cada uno se prueba recorriendo el manejador real de la ventana, sustituyendo
sólo su diálogo modal.

1. **Una carga NUEVA perdía «Crea exceso de presión intersticial».** El
   diálogo lo recogía y el constructor no lo pasaba; sólo *Modificar* lo
   escribía. Pasaba en las cargas repartidas y en las puntuales.
2. ***Simplify Boundary* fallaba siempre.** Pasaba una lista de tuplas a
   `simplify_rdp`, que espera un `Polyline`.
3. **El modo dibujo de *Expand/Shrink* fallaba al confirmar** y nunca había
   cambiado un modelo. Construía `MacroCommand(commands=...)`, y el campo se
   llama `children`.
4. ***Geometry Cleanup* tenía tres defectos**:
   - nunca informó de cruces entre contornos: llamaba a `find_intersections`
     con un argumento en vez de dos y se tragaba el `TypeError`;
   - quitaba vértices del modelo vivo sin deshacer ni aviso;
   - su «After cleanup: N boundaries» imprimía `len()` del diccionario del
     informe, que siempre vale 3.
5. ***Ungroup Support Pattern* no encontraba nunca un patrón.** Buscaba
   `pattern_id`, y nada lo asignaba.
6. **La demo de la interfaz no era la de la CLI.** La de la interfaz dibujaba
   un nivel freático sin asignárselo a nadie, así que su agua no daba
   presión intersticial y las dos «Demo slope» daban factores distintos. El
   propietario eligió la de la CLI como canónica.
7. ***Import Properties* no respetaba la identidad del otro proyecto**:
   - conservaba el `id` de cada material del origen;
   - dejaba sus referencias al agua del otro proyecto, que aquí no existe,
     así que el material importado «con su agua» quedaba **seco en
     silencio**;
   - no respetaba el límite de materiales.

## 3. Lo que se encontró y NO se corrige (regla 6)

### 3.1 El constructor de regiones no admite huecos — mueve números

Un contorno de material cerrado sobre sí mismo (una lente) no hace un hueco
en la región que lo rodea: esa región contiene también el área de la lente.

- Medido en la demo: pintar la lente pinta **el modelo entero**, y (20, 5)
  leía «Lens».
- Si la lente es un anillo abierto, además aparece una región espuria de
  25 m² en una esquina.

No se toca el núcleo. La capa de operaciones rechaza un contorno de material
cerrado, tanto en `boundary_add` como en `model_define` y en
`annotation_to_boundary`, con el motivo. La interfaz sigue permitiéndolo.

### 3.2 Cargas puntuales relativas al contorno

`LineLoad.direction_vector` no tiene rama para `NORMAL_TO_BOUNDARY` ni para
`ANGLE_TO_BOUNDARY` y actúa en vertical. La interfaz ofrece las dos
opciones.

El propietario decidió **implementarlas** (2026-09-24), en una tanda propia y
con validación externa, no aquí. Hasta entonces la capa de operaciones las
rechaza.

### 3.3 *Change Slope Angle* gira el contorno entero

`transforms.change_slope_angle` gira TODO el contorno exterior alrededor del
pivote, no sólo la cara del talud. No se da al agente: queda pendiente en el
inventario con la fase `owner`, a la espera de una decisión.

### 3.4 La DXF importada repite el vértice de cierre (nuevo)

`ogr_core/dxf/reader.py`, desde v0.1.59, añade al final de toda polilínea
cerrada su primer punto, y `_to_boundary` lo conserva en un `Polyline`
cerrado. Así, **todo contorno exterior importado de DXF**, por la interfaz o
por el agente, lleva una arista de cierre de longitud cero.

- El exportador lo compensa y lo dice en un comentario.
- En la prueba de ida y vuelta el FoS no se mueve: 1,672366 en los dos
  casos.
- Lo que no se ha comprobado es qué hace ese vértice doble al editar el
  primer vértice, que es donde una arista de longitud cero se convertiría en
  una arista espuria.

`dxf_import` lo avisa y remite a `geometry_cleanup(apply=true)`. No lo quita:
el agente importa el mismo modelo que la interfaz.

### 3.5 Otros, sin efecto en el cálculo

- ***Convert Tool to Boundary* de la interfaz se salta las reglas.** Permite
  un segundo contorno exterior o una lente de material, y no se puede
  deshacer. El puente del agente (`annotation_to_boundary`) pasa por
  `boundary_add`.
- **Las flechas de carga de la DXF exportada ignoran la orientación.**
  `angle_deg or 270.0` dibuja hacia abajo toda carga con ángulo 0, también
  una horizontal o una normal al contorno.
- **`find_intersections` no mira la arista de cierre de una polilínea
  cerrada.** Un cruce sobre la arista de cierre del exterior no aparece en
  *Geometry Cleanup*.
- **El diálogo de patrón de soportes arranca con los primeros valores de los
  enumerados**, no con los del tipo. La capa de operaciones toma los del
  tipo, o si no los de la clase: tres clases son pasivas por defecto.

## 4. La cuña con sobrecarga: un desfase que era mío

Para la regla 1 reutilicé la cuña de Coulomb de
`test_anchored_wedge_root_v1177.py` y le añadí una sobrecarga vertical de
20 kPa, desde la coronación hasta la salida del plano de 40°.

El motor daba 0,868148 y mi forma cerrada 0,868110, un +4,43e-5. **Lo
mismo con 50, 100, 200, 400 y 800 dovelas**, y eso parecía descartar la
discretización y apuntar al motor.

No lo era:

- El peso del suelo sale exacto.
- La carga se muestrea **en el punto medio de cada dovela**, y el motor no
  pone un borde de dovela en el extremo de la carga (x = 38). La dovela que
  lo contiene pierde el trozo cargado.
- 50, 100, …, 800 son **rejillas anidadas**: todas ponen un borde en
  x = 38,00858, así que perdían siempre la misma carga (0,0086 m × 20 kPa).

Con cuentas que no son múltiplos entre sí (50, 51, 73, 400, 997):

- el motor coincide con la forma cerrada **con la carga discretizada** hasta
  el redondeo a 6 decimales, en Spencer, GLE, Janbu y Fellenius;
- contra la carga exacta, el error cae siempre dentro de la banda de media
  dovela de carga.

El test comprueba esa banda y no la regla del punto medio. Así no consagra
la regla, que podría cambiar a mejor.

Queda como observación: el error es como mucho q·b/2 por cada extremo de
carga que cae dentro de la masa. No he comprobado si la referencia pone un
borde de dovela en los extremos de las cargas.

**Otro camino equivocado, más pequeño.** El test de la grieta suponía que una
grieta nueva está seca. Está llena: `WaterLevelMode.FILLED` es el valor por
defecto, como en la referencia. El test pide ahora el modo seco
explícitamente.

## 5. Tests

| Archivo | Casos | Anclaje |
|---|---|---|
| `test_f2_ops_v1196.py` | 36 | Ver abajo |
| `test_f2_rules_v1196.py` | 19 | Ver abajo |
| `test_api_undo_v1194.py` | +1 | Hacer, deshacer y rehacer, exactos, para las 32 operaciones de edición (antes 11); lo que una operación necesita para existir (una carga que borrar, un patrón que desagrupar) lo prepara `PREPARE`, fuera del paso medido |

**`test_f2_ops_v1196.py`** se ancla en:

- **Regla 1.** La cuña con anclaje construida sólo con operaciones da la
  forma cerrada de Coulomb (Coulomb 1776; Duncan & Wright 2005 §6),
  importada de v1177:
  - en 35° y 40° activo y pasivo, y en 45° activo, con Spencer, GLE y Janbu
    dentro de 2e-6;
  - Janbu en las ocho celdas;
  - la forma cerrada del proyecto que construyen las operaciones es
    **idéntica** a la del fixture hecho a mano.
- **La sobrecarga**, dentro de su banda (§4).
- **Regla 7.**
  - Cada ajuste mueve el número: orientación, magnitud, distribución,
    ángulo, kh, el agua de la grieta y la capacidad del anclaje.
  - Cada combinación que el motor no leería se rechaza sin dejar rastro.
- **Formas cerradas geométricas**:
  - giro de 90° y escala sobre un pivote;
  - desfase a inglete de un rectángulo, (10+2)·(5+2);
  - un relleno que suma exactamente el triángulo dibujado.
- **Unidades de registro.** 980,665 cm/s² y 9,80665 m/s² son 1 g exacto.
- **Archivos.**
  - La DXF de ida y vuelta conserva el FoS.
  - Importar propiedades no trae ni ids ni agua ajenos.
  - Un informe PDF sale de un análisis, y no de una superficie evaluada.
  - Una superficie propia se cuenta en el análisis.

**`test_f2_rules_v1196.py`** comprueba:

- cada una de las siete correcciones del §2 por el manejador real, con su
  paso de deshacer;
- que los dos diálogos llaman al núcleo: sustituir la función cambia lo que
  hace el diálogo;
- los tokens del editor frente a `PARAMETER_CHOICES`;
- que `pattern_id` sobrevive a guardar y no aparece si no existe;
- que la tolerancia de inspección escala con el modelo, ×1000 en ×1000;
- que `model_hash` excluye las anotaciones y `document_hash` las incluye.

## 6. Cuánto alcanza ya un agente

`ogr_api/inventory.py`:

| | v0.1.195 | v0.1.196 |
|---|---|---|
| Cubiertas | 42 | **98** |
| Sólo de interfaz | 23 | 23 |
| Pendientes | 71 | **15** (14 de F3 y *Change Slope Angle*, fase `owner`) |

El techo de pendientes baja a 15.

## 7. Verificación

- Selección dirigida de las áreas tocadas (i18n, demo, CLI, limpieza,
  *Expand/Shrink*, simplificar, importar propiedades, MCP, API, inventario,
  DXF, patrones, registros sísmicos, F2): en verde antes de subir versión.
- Suite entera y sin argumentos: **4384/4384**, sin aviso FILTERED RUN, con
  los siete paquetes medidos de este árbol. v0.1.195 traía 4328; los +56
  son 36 + 19 + 1. Tardó 32 min (11:31 → 12:03) y corrió sola en la
  máquina.
- La selección dirigida anterior: 327/327 en 19 archivos.
- Los tests que llaman directamente a los manejadores de la ventana dejan
  tres `RuntimeWarning` de PySide («Failed to disconnect»). Es inofensivo:
  el manejador intenta desconectar una señal que el test nunca conectó, y el
  propio código ya atrapa ese caso.
- La discriminación contra v0.1.195 no se midió en un *worktree*. Los tests
  de la GUI fallarían contra v0.1.195 por el propio defecto: *Simplify* y el
  modo dibujo levantan excepción, y el tick de las cargas y la demo dan otro
  resultado. Los de operaciones fallarían por ausencia.

## 8. Qué falta

- La tanda propia de las cargas puntuales relativas al contorno (§3.2), con
  validación externa.
- La decisión sobre *Change Slope Angle* (§3.3), el vértice doble de la DXF
  (§3.4) y las lentes (§3.1).
- F3: agua con elementos finitos, estadística, sensibilidad, retroanálisis,
  optimización, Ky/Newmark e interpretación. Antes, un plan corto.
- Siguen reportadas y sin corregir las anomalías A1–A14 y la tolerancia de
  Ej_1 de v0.1.194.
