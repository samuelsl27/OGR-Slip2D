# OGR Slip2D v0.1.197

**Primer bloque de correcciones antes de F3.** Se arreglan dos defectos de
geometría que v0.1.196 dejó reportados. El propietario eligió la solución
recomendada en los dos (2026-09-24).

- **Una lente es un hueco de la región que la rodea.** Mueve números. Una
  región de material cerrada dentro del modelo quedaba tapada por la región
  de fuera, y pintarla pintaba el modelo entero.
- **Un contorno cerrado nunca guarda su vértice de cierre.** El DXF lo
  repetía desde v0.1.59.

Ningún modelo guardado cambia: se compararon los 247 modelos vivos del
repositorio y del banco, antes y después, y coinciden en regiones, materiales
y áreas. Por el camino aparecieron cinco defectos vecinos (§3) y un defecto
latente del mallador en 11 regiones de 5 problemas del banco (§3.5).

---

## 1. Las lentes

### El defecto

`polygonize`, de Shapely, devuelve la cara que rodea la lente **con su
hueco**. El constructor de regiones solo se quedaba con
`f.exterior.coords` y tiraba el hueco. Así la lente quedaba cubierta por dos
regiones, y cada consulta de material devolvía la primera que la contuviera.

Medido antes de corregir, en el talud de 550 m² con una lente débil de
80 m²:

| | Antes | Ahora |
|---|---|---|
| Pintar el suelo fuera y luego la lente | Todo el modelo débil | Solo la lente débil |
| FoS del círculo de prueba | 0,4030 | 1,4667 (1,6725 sin lente) |
| Suma de las áreas de región | 630 m² | 550 m² |
| Malla de elementos finitos (modelo de 1500 m²) | 1550 m² | 1500 m² |
| Nodos interiores marcados como contorno | 8 | 0 |
| Error de carga en el flujo 1D de Darcy | 7,6 m | 7e-9 m |

### Lo que se cambió

- **`MaterialRegion`** (`ogr_core/geometry/regions.py`) gana `holes` (anillos
  en sentido horario) e `inside_point`.
  - `area` y `centroid()` restan los huecos.
  - `contains(x, y)`: dentro del anillo exterior y fuera de todo hueco.
  - En una región sin huecos las tres cosas se calculan exactamente como
    antes.
- **Todos los que consultan regiones** respetan los huecos:
  - las consultas de material de `Project` (`_in_region`); sin huecos solo
    añade la lectura de un atributo por región;
  - la asignación al pintar;
  - la herencia por huella;
  - la poda de asignaciones;
  - el lienzo (`QPainterPath` par-impar);
  - las ayudas al pasar el ratón;
  - la imagen PNG del agente;
  - `regions_info` de la API;
  - el mallado.
- **La huella de una asignación guarda los huecos de su región**, en una
  clave `footprint_holes` que solo se escribe si hay huecos, así que un
  archivo sin lentes se guarda byte a byte igual. **Esto no estaba en el
  plan.** Salió al escribir el test: sin los huecos en la huella, si se parte
  una lente después de pintarla, la mitad sin pintar hereda el material de
  la región de fuera. La huella de fuera también contiene la lente, y en caso
  de empate gana la asignación más reciente. El test
  `test_a_piece_of_a_split_lens_keeps_the_lens_material` lo fija.
- **El mallado** discretiza también los anillos de los huecos. El registro
  de nodos compartido hace que la malla de la lente y la de fuera sean
  conformes.
- **`generate_mesh_for_project`** toma los materiales de `resolve_regions()`,
  que es lo mismo que lee el equilibrio límite (ver §3.5).
- **La API y el agente admiten lentes:**
  - `boundary_add(type="material", closed=true)`;
  - en `model_define`, `{"points": [...], "closed": true}` dentro de
    `material_boundaries`;
  - `annotation_to_boundary` de una forma cerrada con `type="material"`.

  Se sigue rechazando, con el motivo, una polilínea ABIERTA que vuelve a su
  inicio: sus extremos se prolongan como un corte y dejan una región espuria
  (medida en v0.1.196). También se rechaza un anillo sin área.

## 2. El vértice de cierre

El lector DXF añade el primer punto al final de toda polilínea cerrada
porque el saneador recorre las aristas de un anillo sin dar la vuelta y
necesita el lado de cierre como segmento real. `_to_boundary` pasaba ese
formato al modelo tal cual.

Nueva regla: `drop_closing_vertex` (`ogr_core/geometry/cleanup.py`).

- **Tolerancia** relativa al propio polígono (1e-6 × su diagonal), la misma
  con la que la inspección llama «duplicado» a un vértice. Un CIRCLE cierra
  a −2,4e-16·r, no exactamente.
- **Nunca deja menos de tres vértices.**
- **Se aplica:**
  - en `_to_boundary`, donde un formato se convierte en el otro; el formato
    de anillo sigue **dentro** del paquete DXF;
  - en `Project.add_boundary`, lo que cubre una anotación convertida o un
    script;
  - al abrir un `.ogr`. Es idempotente y no reinterpreta nada, como la
    normalización de huellas de v0.1.14, así que `from_dict(to_dict())`
    sigue siendo la identidad. De los 247 modelos vivos, **ninguno** traía
    el cierre repetido.

Además:

- **Vista previa DXF.** «N → M vertices» cuenta los vértices del archivo y
  los que se guardan. Antes contaba los del anillo interno del saneador, y
  eso contradecía la promesa del docstring del importador.
- **`find_intersections`** mira también el lado de cierre de una polilínea
  cerrada. Esto se reportó en v0.1.196, y la repetición era lo único que
  hacía revisar ese lado en un modelo importado.
- La nota de `dxf_import` ya no atribuye duplicados al lector.

Medido: mover el vértice 0 del modelo importado da 580 m², igual que en el
dibujado (antes 575). El desfase de un rectángulo importado da
(w+2d)(h+2d) (antes salía una punta). En el lienzo ya no hay dos asas en el
mismo punto.

## 3. Lo que se encontró por el camino

1. **Una línea que acaba sobre una lente la atravesaba.** La soldadura y el
   «¿acaba en otro corte?» solo miraban las líneas abiertas y el exterior.
   El extremo quedaba «colgando», se prolongaba 10 diagonales y partía la
   lente y la región de fuera. Ahora los anillos cerrados son destino de
   soldadura.
2. **La herencia por contorno cerrado la ganaba el MAYOR.** El comentario
   decía «gana el de dentro» y ordenaba de menor a mayor, pero el bucle no
   tenía `break`. Solo se nota con lentes anidadas.
3. **`convert_boundary(…, MATERIAL)` cerraba a la fuerza.** Convertir en
   material un nivel freático abierto lo cerraba con una cuerda a través
   del modelo. Ahora conserva el indicador de cerrado de origen.
4. **Las ayudas al pasar el ratón nunca leyeron el material pintado.**
   Construían sus propias regiones con `build_regions`, cuyo material solo
   conoce los contornos cerrados, así que una región pintada decía «no
   material assigned». Ahora usan las regiones resueltas.
5. **El mallador leía el material en el centroide, que no siempre está
   dentro de la región.** Con una lente centrada, el centroide de la región
   de fuera cae en la lente. En una región no convexa puede caer en la
   región vecina.
   - Medido en los 247 modelos vivos: **11 regiones de 5 problemas** tienen
     el centroide en otra región: 005/006 (la validación 007-acads-2b), 020,
     027 y 042.
   - Ninguno calcula el agua por elementos finitos: los once usan nivel
     freático, sin malla ni propiedades hidráulicas. **No se mueve ningún
     número guardado.**
   - Es un defecto latente: quien hubiera mallado uno de esos modelos habría
     tenido una región entera con el material de la vecina.

### Dos caminos equivocados

- **Una lente del mismo material movía el FoS 7e-6.** Esperaba cero y era
  otra cosa: la circunferencia de prueba cortaba la lente, y el rebanador
  pone cortes de dovela obligatorios donde la superficie cruza un contorno
  de material (v0.1.66). Es otra partición en dovelas, no un error de la
  lente. El test de la regla 1 usa por eso la cuña plana con la lente
  **dentro** de la masa, y ahí el FoS es idéntico al de la cuña sin lente.
- **`Path.contains_point` de matplotlib no aplica regla de relleno a un
  camino compuesto:** decía que el hueco estaba dentro. El test del PNG
  dibuja el camino con Agg, el mismo motor de `render_png`, y lee el píxel.

## 4. Tests

| Archivo | Casos | Anclaje |
|---|---|---|
| `test_lens_regions_v1197.py` | 20 | Ver abajo |
| `test_closing_vertex_v1197.py` | 8 | Ver abajo |
| `test_f2_ops_v1196.py` | 0 (2 cambiados) | Ver abajo |

**`test_lens_regions_v1197.py`:**

- **Áreas exactas:** región de fuera = exterior − lente; lente dentro de
  otra lente = anillo. La tolerancia sale de la rejilla del redondeo × el
  perímetro.
- **Cuña de Coulomb (Coulomb 1776; Duncan & Wright 2005 §6):**
  - una lente del mismo peso deja el FoS **idéntico**;
  - una lente más pesada da la forma cerrada con
    W = γ₁·A + (γ₂−γ₁)·A_lente dentro de 2e-6 cuando sus lados caen en
    bordes de dovela, y dentro de la banda (γ₂−γ₁)·t·b cuando no.
- **Pintura:** la lente y lo de fuera se pintan por separado, en los dos
  órdenes, y una lente partida conserva su material.
- **Líneas:** una línea que acaba en la lente se detiene; una que la cruza
  parte las dos regiones según las áreas.
- **Herencia:** gana el contorno cerrado de dentro.
- **Elementos finitos:**
  - área mallada igual a la del modelo;
  - la lente se malla una vez;
  - ningún nodo interior queda como contorno;
  - la carga del flujo 1D es la solución cerrada de Darcy en **todos** los
    nodos. Este test discrimina: sin huecos el error llega a 7,6 m. Curioso:
    el caudal por la sección salía bien incluso con la lente duplicada.
- **Otros consumidores:** el lienzo, la ayuda al pasar el ratón y el PNG
  respetan el hueco.
- **`convert_boundary`** mantiene abierta una línea abierta.
- **API:** se acepta una lente y se rechazan el anillo abierto y el
  degenerado.

**`test_closing_vertex_v1197.py`:**

- DXF de ida y vuelta exacta;
- el vértice 0 movido da 580 m²;
- el desfase de un rectángulo importado da (w+2d)(h+2d);
- el círculo de DXF no guarda su casi-copia;
- la vista previa cuenta «6 → 6»;
- un `.ogr` con la repetición se normaliza al abrir;
- `add_boundary` quita la repetición, pero a una polilínea abierta no le
  toca los extremos;
- se informa del cruce que toca solo el lado de cierre.

**`test_f2_ops_v1196.py`, dos tests cambiados.** Fijaban el rechazo de las
lentes que este bloque levanta:

- el anillo **abierto** se sigue rechazando y el **cerrado** se acepta;
- una forma cerrada ya no se rechaza como material, pero sí como nivel
  freático.

La cabecera del archivo dice ahora que el duplicado del DXF está decidido.

## 5. Verificación

- **«Cero dígitos movidos»:** los 247 modelos vivos (los 7 de `validacion/`
  y 240 del banco, manuales 02 a 07) tienen las mismas regiones, materiales
  y áreas antes y después, comparados en el mismo árbol con la línea base
  guardada antes de tocar código.
- **Selección dirigida** de regiones, asignaciones, herencia, malla,
  filtración, transitorio, no saturado, DXF, F2, API, MCP, anotaciones,
  geometría y ayudas: 627 casos en verde; el único fallo era un test ya
  actualizado al que la corrida llegó antes que el cambio.
- **Suite entera y sin argumentos:** 4412/4412, sin aviso FILTERED RUN,
  con los siete paquetes medidos de este árbol. v0.1.196 traía 4384; los
  +28 son los dos archivos nuevos. Tardó 33 min (12:48 → 13:21).
- **No medido:** el rendimiento. Sin huecos, cada consulta de material
  añade una lectura de atributo por región (decenas de nanosegundos) sobre
  una prueba de punto en polígono que ya cuesta más. Manda el razonamiento sobre el
  trabajo añadido (AGENTS.md).

## 6. Qué falta

- Bloque 2: rehacer *Change Slope Angle*, con su plan corto antes.
- Bloque 3: cargas puntuales relativas al contorno.
- Después, F3.
- Fuera de este bloque, y reportado:
  - *Convert Tool to Boundary* de la interfaz sigue sin pasar por las
    reglas (segundo exterior, sin deshacer);
  - el camino sin Shapely no admite lentes;
  - la herramienta de dibujo de la interfaz no cierra un contorno de
    material: hoy las lentes entran por DXF, por anotación convertida o por
    el agente.
