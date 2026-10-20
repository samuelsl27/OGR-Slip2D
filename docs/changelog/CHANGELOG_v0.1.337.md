# OGR Slip2D v0.1.337

**Las anotaciones salen en el DXF exportado como entidades nativas, en una capa propia y con su casilla, y
el diálogo de importación ofrece todos los tipos de geometría (D333).** Quinta versión de la tanda P8j.

## 0. Lo que se encontró

- **La exportación no leía `project.annotations`.** Lo que el usuario dibujaba en el lienzo se quedaba
  fuera del dibujo. La capa `OGR_X_ANNOTATION` solo llevaba el título y las etiquetas de FS.
- **D333.** `_KIND_LABELS` del diálogo de importación no tenía capa débil ni superficie anisótropa.
  - El lector proponía bien esos tipos para `OGR_WEAK_LAYER` y `OGR_ANISO_SURFACE`.
  - Pero `findData` daba −1 y la fila caía en «(ignorar)».
  - Así, lo que el programa exporta en esas dos capas desde v0.1.121 y v0.1.126 volvía como nada por la
    ventana.
- **La geometría del dibujo de las anotaciones vivía en el lienzo**, y el núcleo no podía usarla. Para no
  escribirla dos veces, pasa al núcleo y el lienzo la toma de allí.
- **La tolerancia al reimportar, medida antes de cambiarla.**
  - El catálogo DXF calculaba la diagonal del dibujo con todas las capas, también las que se ignoran, y
    las tolerancias del saneador son un porcentaje de esa diagonal.
  - **Medido:** una anotación hasta (1000, 1000) llevaba la diagonal del ejemplo de 55,9 a 1414, es
    decir, tolerancias 25 veces más anchas.
  - Un extremo de material a 2 o 5 m del exterior se alargaba hasta él sin aviso, cuando sin la anotación
    se avisa de que queda suelto.
  - En el ejemplo sin huecos, la geometría reimportada era idéntica, así que hacía falta el caso del hueco
    para verlo.
  - **Por decisión de la propietaria,** la diagonal deja de contar las capas `OGR_X_`, que solo escribe el
    exportador. Un archivo de otro programa se lee como antes.

## 1. Qué cambia

- **`ogr_core/annotations/drawing.py`** (nuevo, sin Qt), la geometría única de la capa de anotaciones, en
  primitivas:
  - `Stroke` (trazos en coordenadas del modelo), `Mark` (punta de flecha, marca de cota, arco de ángulo,
    cruz: símbolos de tamaño de pantalla), `Label`, `Picture` y `Dimension`, la cota entera para quien
    tiene entidad de cota;
  - con ellas, lo que mide una cota, dónde caen las marcas de los ejes (`axes_ticks`) y hacia dónde apunta
    una flecha se escriben una sola vez.
- **`ogr_core/numbers.py`** (nuevo): `nice_step` baja aquí desde `snap_engine`, que lo reexporta.
- **`ogr_core/annotations/image_size.py`** (nuevo): el tamaño en píxeles de una imagen PNG, JPEG o BMP,
  leído de su cabecera. No se instala ninguna dependencia.
- **`ogr_gui/canvas/annotation_items.py`** pasa a ser el adaptador de Qt de esas primitivas. El lienzo
  dibuja lo mismo que antes, y lo guarda `test_annotations_drawn_v1330` sin cambios. La única diferencia:
  un ángulo de exactamente 180° traza su semicircunferencia por el otro lado.
- **`ogr_core/dxf/annotation_export.py`** (nuevo), la capa en el DXF, en `OGR_X_DRAWING`, por decisión de
  la propietaria:
  - formas → `LWPOLYLINE`, cerrada si lo es, y un `HATCH` sólido para el relleno, con la opacidad como
    transparencia;
  - flecha → su línea y una punta `SOLID`;
  - texto → `TEXT`;
  - cotas de longitud, X e Y → **`DIMENSION` de verdad** (alineada, o lineal a 0° y 90°), y la de ángulo,
    angular;
    - las mide el programa de CAD, **en unidades del dibujo**, también por decisión de la propietaria: una
      de 10 m exportada en milímetros dice 10000;
    - los decimales guardan el milímetro;
    - el ángulo se escribe en sentido antihorario de un brazo al otro, que es como lo mide ezdxf. Medido:
      con los brazos al revés daba 270 en vez de 90;
  - ejes → sus dos líneas, las marcas y las coordenadas;
  - imagen → `IMAGE` enlazada a su archivo, escrita antes que el modelo para que quede debajo. Una que
    falta o cuyo tamaño no se lee es el marco del lienzo, y el informe lo dice;
  - cada entidad lleva el color, el tipo de línea y el grosor de su anotación. El tamaño de pantalla pasa a
    unidades a razón de una milésima de la diagonal por píxel, y la escala de los tipos de línea sigue al
    modelo.
- **La casilla «Capa de anotaciones»**, en el diálogo de exportación, el API (`annotation_layer`) y el MCP:
  - gris y con su motivo si no hay anotaciones visibles;
  - la casilla de siempre pasa a llamarse «Etiquetas (título, factor de seguridad)».
- **D333:** el diálogo de importación ofrece capa débil y superficie anisótropa.
- **`DxfCatalogue.bbox`** no cuenta las capas `OGR_X_` (salvo en un dibujo que no tenga otra cosa).

## 2. Tests

- **`tests/test_dxf_annotations_v1337.py`** (nuevo, 20 casos):
  - **la entidad de cada tipo**, el color de cada entidad, y que una anotación oculta no se escribe;
  - **una cota mide lo que mide la anotación:** `get_measurement()` del programa de CAD, por la unidad
    del dibujo, es igual a `measured_value()`, en metros y en milímetros (regla 1: la referencia es la
    geometría); el ángulo da lo mismo en los dos sentidos de elección; y los decimales guardan el
    milímetro en cada unidad;
  - **los ejes llevan las coordenadas que escribe el lienzo**, y la escala de tipos de línea es la misma en
    metros que en milímetros;
  - **la imagen:** su tamaño se lee como lo lee Qt (PNG, JPEG y BMP escritos por Qt); es una `IMAGE` con su
    archivo y su tamaño en píxeles, escrita antes que el exterior; y una que falta es su marco, y se dice;
  - **la casilla mueve la salida (regla 7)**, sin tocar las etiquetas;
  - la capa se propone como «ignorar» al reimportar y no crea ningún contorno;
  - el API y el MCP llevan la casilla;
  - **el diálogo:** la casilla, gris con su motivo sin anotaciones;
  - **la tolerancia:** la diagonal es la del modelo con una anotación lejana, y los huecos de 2 y 5 m
    siguen avisándose;
  - **D333:** las etiquetas del diálogo cubren todos los tipos del lector, y una capa débil y una
    superficie anisótropa exportadas vuelven por el diálogo con sus vértices.
- **Cambio deliberado:** `test_dxf_export_v148` añade `OGR_X_DRAWING` a las capas que se ignoran al
  reimportar.

**Con el código de 0.1.336 fallan 16 de los 20 casos nuevos.** Los cuatro que pasan allí lo hacen sin
probar nada, porque aquel árbol no exporta anotaciones:
- una oculta no se escribe, pero ninguna se escribe;
- la anotación lejana no llega al archivo, así que la diagonal no cambia y los huecos se avisan.

Las tolerancias se miden ahora con la capa que las movía. Se corrió sobre un `git archive` de 0.1.336, sin el
buscador editable.

## 3. Verificación

- **El test de esta versión**, 20/20. Con el dibujo de v1330 y la exportación de v148, 57/57 a la primera,
  antes del arreglo de la tolerancia.
- **Los vecinos:**
  - 339/339 en 19 archivos: el DXF, las anotaciones, el lienzo, el forzado y su regla, el diccionario, el
    castellano, el MCP y los inventarios del API;
  - y 112/112 de DXF tras el arreglo.
- **Suite entera:** 6321/6321, `EXIT=0`, 82 min.
- **Banco:**
  - `verificar_cierres.py` entero: 85 comprobaciones, 0 bajadas;
  - **D333 CUBIERTO POR TEST**: los tipos del lector tienen todos su etiqueta, y las capas de una capa
    débil y una superficie anisótropa exportadas se proponen y se ofrecen como tales;
  - instantánea `Evaluaciones/0.1.337`, D333 retirada, prompts (34) y auditorías con 0 ERROR.
- **Ningún número del motor cambia.** Un DXF de otro programa se lee como antes: la diagonal solo deja
  de contar las capas `OGR_X_`.

## 4. Pendiente

- **0.1.338:** el PNG del agente dibuja las anotaciones, con estas mismas primitivas (D336, primera parte).
- **0.1.339:** el informe PDF, con una figura por método.
