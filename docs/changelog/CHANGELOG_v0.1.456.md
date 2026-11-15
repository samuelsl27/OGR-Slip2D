# OGR Slip2D v0.1.456

**La copia de un contorno lleva sus dos `id` nuevos (D425).** Un contorno lleva dos `id`: el suyo (`Boundary.id`, el
que resuelven los materiales, deshacer y el agente) y el de su polilínea (`Polyline.id`, que se escribe en el `.ogr`).
Copiar contorno de la ventana renovaba solo el primero (desde 0.1.59), así que la copia y el original compartían el
`Polyline.id`. La copia del agente (`boundary_edit` con `copy`) renovaba los dos (desde 0.1.196).

Medido con 0.1.455 (640827f) sobre el talud de ejemplo con una lente de material y una línea piezométrica añadidas,
las dos que la regla de D410 deja copiar (`_auditoria/P10_D419_D428/medir_d425.py` del banco, con su log):

| | 0.1.455 | ahora |
|---|---|---|
| copiar la lente y la línea piezométrica en la ventana | 6 contornos, 6 `Boundary.id`, **4** `Polyline.id` | 6, 6 y 6 |
| guardar y abrir | lo mismo | lo mismo |
| la misma copia por el agente | dos `id` nuevos | igual |

Ahora la ventana y el agente preguntan una copia del núcleo, `copy_boundary(b, dx, dy)`
(`ogr_core/geometry/transforms.py`, junto a `translate`): `translate` y los dos `id` nuevos. Cada puerta conserva su
desplazamiento: la ventana (2, 2) y el agente su `dx` y su `dy`. **Ningún número cambia:** ningún lector resuelve por
`Polyline.id`. Es la vigesimonovena versión de la tanda P10 y la cuarta del plan aprobado el 2026-11-14.

## 0. Lo que se encontró

- **El paso 0 tuvo que adaptar el guion de medida.** El de 0.1.435 copiaba el nivel freático, una lente y el
  exterior del ejemplo. Desde 0.1.455 (D410) la ventana no copia el nivel freático ni el exterior, y el guion
  fallaba al buscar la copia. Ahora dice el rechazo, copia además una línea piezométrica (sección 1b) y lee las
  copias que hay. El log de 0.1.435 se queda al lado, escrito por el guion anterior. Con 0.1.455:
  - la lente y la línea piezométrica comparten su `Polyline.id` con el original;
  - el agente da los dos `id` nuevos, y rechaza copiar el nivel freático y el exterior.
- **Nada resuelve un contorno por su `Polyline.id`.** Se escribe en el `.ogr`, y por eso entra en el hash del
  documento: el resultado caducado, los cambios sin guardar y la comprobación de deshacer que la ventana comparte con
  el agente (lo midió la revisión, con un registro de cada lectura). Ningún lienzo ni el motor lo leen. Hasta esta
  versión lo ponían dos líneas del código al editar, y las dos lo conservan a propósito: el desfase del exterior
  (`ogr_core/geometry/expand_shrink.py`) y `set_vertices` del agente (`ogr_api/ops/model.py`). Ahora lo pone también
  `copy_boundary`, nuevo. El material, deshacer y el agente resuelven por `Boundary.id`; el DXF no escribe ningún
  `id`, y la filtración por elementos finitos va por los nodos de su malla. El defecto es un invariante roto, dos
  objetos del modelo con un mismo `id`, sin efecto en ningún número.
- **Solo hay dos copias de un contorno.** Las otras ediciones de la ventana que hacen `deepcopy` son el mismo contorno
  editado y conservan los dos `id` a propósito: mover, insertar, mover o borrar un vértice, Convertir
  (`convert_boundary`) y el tipo de un objeto de bloques.
- **Se reporta sin tocar, a ficha nueva al cerrar** (decisión de la propietaria al planificar): dos contornos con el
  mismo `Boundary.id` no los hace ningún camino de la ventana; llegan con un `.ogr` editado a mano, un guion o
  `python_exec`, y `Project.from_dict` y `project_validate` no dicen nada. Con ellos, Borrar en la ventana quita los
  dos y deshacer devuelve uno (medido con 0.1.455, sección 4 del guion).
- **La revisión adversaria (un agente)** no encontró fallos en el código del cambio. Comparó en memoria la copia vieja
  de la ventana, la vieja del agente y `copy_boundary` en 64 casos: todos los tipos, colores, anchos y visibilidad
  propios, una capa débil suprimida, objetos de bloques, un nombre que no es texto y desplazamientos de 0 a 1e300.
  Salen iguales bit a bit, salvo los `id`, y no comparten ningún objeto. Comparó también la ventana y el agente entre
  los árboles de 0.1.455 y 0.1.456, en los dos idiomas: la copia sin `id`, el paso de deshacer, la barra, el rechazo
  y el JSON del agente salen iguales. Encontró, y se arregló:
  - **(media, del test) un `id` derivado del original** (el suyo y un sufijo) pasaba los 10 casos del borrador, y dos
    copias de un mismo contorno compartían entonces los dos `id`. Ningún caso copiaba dos veces ni copiaba una copia.
    Ahora un caso lo hace, por la ventana y por el agente;
  - **(baja, del test) una copia que tocara el original** (su ancho, su visibilidad) pasaba, porque el caso leía lo
    esperado después de copiar y solo miraba los vértices. Ahora lo lee antes y compara el original entero;
  - **(baja, del test) un objeto de bloques compartido** entre la copia y el original pasaba, porque ningún caso tenía
    uno. Ahora un caso del núcleo lo tiene;
  - y cinco frases de este changelog y de la cabecera del test: «ningún lector» (el hash lo lee), «dos líneas» (ahora
    tres), el DXF y la filtración «por `Boundary.id`», la vuelta por el archivo «por el agente» (el caso del agente no
    la hacía, ahora sí), «solo con un `.ogr` a mano», y la lista de ediciones con `deepcopy`, a la que faltaban dos.
- **Se reporta sin tocar:**
  - **(baja, anterior) los `.ogr` que ya tienen el `Polyline.id` repetido.** Todo archivo guardado entre 0.1.59 y
    0.1.455 tras un Copiar de la ventana lo lleva, y 0.1.456 lo abre igual, sin migración y sin aviso: lo pide el
    prompt de la ficha. Una copia nueva no lo arregla (medido por la revisión). **Por decisión de la propietaria**
    va con la ficha nueva de los `Boundary.id` repetidos;
  - **(informativo, anterior)** Expandir / contraer dibujado y la limpieza con simplificación hacen un `Polyline.id`
    nuevo para el mismo contorno. No repiten ningún `id`;
  - **(muy baja)** un mutante que da a la copia el mismo texto como `Boundary.id` y como `Polyline.id` sobrevive. Es
    inocuo: son dos espacios de nombres que nadie cruza;
  - **(muy baja)** sin PySide6, los casos de la ventana vuelven sin probar nada en vez de salir omitidos, como el
    resto de los tests de la ventana del proyecto.

## 1. Qué cambia

- **`ogr_core/geometry/transforms.py`:** `copy_boundary(b, dx, dy)` devuelve un contorno nuevo: el original desplazado
  (`translate`), con un `Boundary.id` y un `Polyline.id` nuevos. El docstring de `translate` dice que conserva los dos,
  porque es el mismo contorno movido. `ogr_core.geometry` la exporta.
- **`ogr_gui/main_window.py`, `_do_copy_boundary`:** tras la regla de D410, `copy_boundary(orig, 2.0, 2.0)`. Antes
  hacía `deepcopy`, renovaba `Boundary.id` y desplazaba los vértices a mano.
- **`ogr_api/ops/model.py`, `boundary_edit` con `copy`:** `copy_boundary` con su `dx` y su `dy`, en vez de su
  `translate` y sus dos `id` a mano. Su JSON no cambia.
- Ninguna cadena nueva, ningún ajuste ni ninguna acción nuevos.

## 2. Qué se probó

- **`tests/test_copy_boundary_ids_v1456.py`** (12 casos, unos 2 s en el runner). Lleva una ventana real para el
  archivo, y ningún diálogo se ejecuta.
  - **La referencia es una identidad:** tras copiar, `len(set(ids)) == len(ids)` para `Boundary.id` y para
    `Polyline.id`, en el modelo y tras `to_dict` y `from_dict`, por la ventana y por el agente, también tras copiar
    dos veces un contorno y copiar una copia.
  - **La copia** es el original desplazado (2, 2) vértice a vértice, e igual en todo lo demás, campo a campo, y el
    original no cambia. La de la ventana y la del agente son la misma salvo los `id` (y el material, que en el test
    es de otro proyecto). Deshacer la quita, y rehacer la devuelve con sus `id`. La del núcleo no comparte ningún
    objeto con el original, tampoco el de un objeto de bloques.
  - **El control:** mover es el mismo contorno, y conserva los dos `id` por la ventana, por el agente y en
    `translate`.
  - Un espía en `copy_boundary` ve las dos puertas, con el desplazamiento de cada una.
- **Discriminación:** en el árbol de 0.1.455, sin el buscador editable, fallan 6 de los 12 casos: cuatro por lo que
  hacen (los `id` repetidos tras una copia y tras dos, el espía que no ve a nadie, el rehacer con `id` repetidos) y
  dos por el nombre nuevo. Pasan los seis controles: mover y `translate` conservan los `id`, la copia del agente ya
  los tenía nuevos, y la copia ya era el original desplazado.
- **Mutantes** (`mutants_d425.py`, en el banco): 13, todos muertos. Tres son de la revisión: los `id` derivados del
  original, la copia que toca el original y el objeto de bloques compartido. Los diez primeros:
  - la ventana: la copia de 0.1.455 (solo `Boundary.id`), y la copia sin desplazar en y;
  - el núcleo: la copia que conserva el `Polyline.id` o el `Boundary.id`, la que mueve el original, la que cambia
    un campo (el nombre), y un `translate` que renueva el `Polyline.id` (un mover que haría una copia);
  - el agente: su copia propia de 0.1.455, su `dx` y su `dy` cambiados, y la copia que conserva el `Polyline.id`.
- **Vecinos**, con los patrones `copy_boundary_ids copy_convert_boundary_rule add_boundary_step spanish_texts f2_ops
  f2_rules transforms expand_shrink` (cada uno comprobado con `--list`): 137 casos en verde.
- **La suite entera** con `--jobs 4`, una sola vez y tras la revisión: **7740 casos, 7739 en verde, 0 fallos y 1
  omitido**, sin fugas ni tramos muertos. La serie no toca (34 commits desde la última).

## 3. Qué queda

- La ficha nueva de §0: dos contornos con el mismo `Boundary.id` al leer un `.ogr`, y en ella los `Polyline.id`
  repetidos que traen los archivos guardados tras un Copiar de la ventana entre 0.1.59 y 0.1.455.
- En el plan del 2026-11-14 sigue D426 (0.1.457): el talud de `examples/quick_slope.py` declara su dirección.
