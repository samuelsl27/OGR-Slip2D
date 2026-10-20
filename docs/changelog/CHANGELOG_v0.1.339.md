# OGR Slip2D v0.1.339

**El informe PDF lleva una figura por método, con su superficie crítica, las anotaciones y, si la búsqueda
tiene rejilla de centros, las isolíneas del factor de seguridad mínimo en cada centro, encuadrada en el
modelo o en el modelo y el área de búsqueda (D336, segunda parte; D336 cerrada).** Séptima y última versión
de la tanda P8j.

## 0. Lo que se encontró

- **El informe no tenía ninguna figura:** solo tablas y texto (D336).
- **El encuadre pedido no se respetaba: medido antes de darlo por bueno.**
  - Con aspecto igual y `adjustable="datalim"`, al dibujar matplotlib ajusta un lado. Si los datos caben
    en la vista, puede **encoger** ese lado hasta los datos, centrado en la vista.
  - Con el encuadre «área de búsqueda», a 1400 × 900 (el tamaño de las figuras), el dibujo quedaba en y
    24,1–58,5 y dejaba fuera **20 de los 64 centros** evaluados. A 1400 × 500 dejaba fuera 38.
  - Ahora los límites de datos pasan a ser el propio encuadre, y matplotlib solo puede ensancharlo:
    0 centros fuera en los cuatro tamaños medidos.
  - Medido con una comparación en el mismo proceso: el código nuevo, el mismo sin esa línea, y otra vez el
    nuevo como control, idéntico al primero.
- **Un aviso de matplotlib en cada PNG desde 0.1.338** (apuntado en su changelog).
  - Fijar los límites alrededor de la capa de anotaciones apaga la autoescala, y al dibujar matplotlib
    avisa de que ensancha uno para el aspecto: «Ignoring fixed y limits to fulfill fixed data aspect…».
  - Salía 26 veces en la suite de 0.1.338 y ninguna en la de 0.1.337. El PNG era el correcto.
  - Ahora la autoescala se vuelve a encender después de fijar los límites. `set_xlim` deja la vista al
    día y nada pide autoescalar después, así que los límites se quedan, el aspecto ensancha el mismo lado
    y no avisa.
- **Una imagen PNG con canal alfa son dos objetos en el PDF:** la imagen y su máscara, compartida entre
  alfas iguales. Contar `/Subtype /Image` daba 3 con dos figuras. El test cuenta imágenes menos máscaras.

## 1. Qué cambia

- **`ogr_api/report_figures.py`** (nuevo). Las figuras se construyen encima del núcleo: necesitan la lectura
  de una búsqueda que hace el motor (`minimum_per_centre`), y el núcleo no puede importarla.
  - `grid_data(sr)`: el FS mínimo de las superficies válidas en cada centro, como lo dibuja *Interpretar*,
    y el centro de la superficie crítica.
  - `figure_extent(project, results, framing)`:
    - `"model"`: la caja del modelo;
    - `"search_area"`: además, todos los centros evaluados, válidos o no, y los de las superficies del
      usuario;
    - siempre con un margen del 5 %, y **el mismo para todas las figuras**, para que se comparen.
  - `method_figures(...)`: una figura por método con superficie crítica. Si el cálculo aplicó coeficientes
    parciales, la escala dice «over-design factor».
- **`render_png(..., extent=, grid=)`:** `grid` dibuja las isolíneas rellenas con su escala, los centros
  como puntos y el crítico como estrella.
- **`generate_report(..., figures=)`:** incrusta las figuras en una sección «Critical Surface by Method»,
  tras los mínimos globales. Cada una lleva su pie: el método y su FS, o ODF con coeficientes parciales.
  Los textos del PDF siguen en inglés, como el resto del informe (D335).
- **El diálogo de opciones** (`ogr_gui/dialogs/report_dialog.py`, nuevo), que *Generar informe* abre antes
  de pedir el archivo:
  - «Superficie crítica de cada método»;
  - «Encuadre: Modelo / Modelo y área de búsqueda». El área de búsqueda sale gris, y dice por qué, si
    ninguna búsqueda tiene rejilla de centros;
  - «Anotaciones», gris si el modelo no tiene ninguna visible.

  Sin figuras, el encuadre y las anotaciones se apagan (regla 7: una opción que no puede mover el informe
  no se ofrece).
- **`report_generate`** en el API y el MCP gana `figures`, `framing` y `annotations`, con los mismos valores
  por defecto que el diálogo. Un encuadre desconocido se rechaza con `NotFound`, como un `what` desconocido
  en `properties_import`.
- **`docs/mcp/herramientas.md`:** `report_generate` y `model_render` describen sus parámetros nuevos.

## 2. Tests

- **`tests/test_report_figures_v1339.py`** (nuevo, 22 casos), sobre la rejilla de `test_f2_ops_v1196`:
  - **una imagen por método** en el PDF, y ninguna sin figuras, por el núcleo, por la operación y por la
    acción de la ventana; y el pie de cada figura;
  - **las isolíneas son el mínimo de cada centro**: los valores dibujados (espiados en `tricontourf`) son
    el FS mínimo de las superficies válidas de cada centro, calculado aparte desde las evaluaciones; el
    menor es el FS crítico y la estrella está en su centro;
  - **el encuadre mueve el dibujo** (regla 7), medido en los ejes tal como matplotlib los dibuja:
    - el área de búsqueda contiene todos los centros evaluados;
    - un centro inválido lejano entra en el encuadre y no en las isolíneas;
    - el del modelo es su caja con su margen, y deja fuera la parte alta de esta rejilla;
  - sin rejilla no hay isolíneas, y el diálogo pone gris el área de búsqueda con su motivo;
  - las anotaciones cambian los píxeles;
  - la escala dice «over-design factor» con coeficientes parciales;
  - **ningún aviso de matplotlib**, con la capa y con un encuadre;
  - el diálogo, en castellano, y la acción: primero las opciones, después el archivo; al cancelar, no se
    pregunta nada más.

**Con el código de 0.1.338 fallan los 22.** Casi todos fallan porque falta el módulo. Los dos que dicen
algo más:
- el del aviso falla porque 0.1.338 lo emite;
- el de la operación falla porque 0.1.338 rechaza `framing`.

Se corrió sobre el árbol de 0.1.338, sin el buscador editable.

## 3. Verificación

- **El test de esta versión**, 22/22. A la primera fallaron cinco, todos del test:
  - contaba las máscaras como imágenes;
  - leía los flujos sin el ASCII85;
  - pedía un centro inválido que esta rejilla no tiene, y pasó a añadirlo lejos;
  - esperaba `InvalidArgument` donde el archivo usa `NotFound`.
- **Los vecinos:** 349/349 en 28 archivos: el informe y su diálogo, el render y `model_render`, el
  diccionario y el castellano, los menús, el servidor MCP y sus transportes, los inventarios del API, el
  deshacer de la ventana, los tamaños de los diálogos, la CI de Linux, la exportación DXF y el ejemplo
  validado Ej_1, que genera un informe.
- **Suite entera:** 6353/6353, `EXIT=0`, 86 min, **sin ningún aviso «Ignoring fixed»** (26 en la de
  0.1.338).
- **Banco:**
  - `verificar_cierres.py` entero: 86 comprobaciones, 0 bajadas;
  - **D336 CUBIERTO POR TEST**, medido allí:
    - el rectángulo verde de la capa cubre 31 648 píxeles del PNG, y ninguno sin ella;
    - un informe de dos métodos lleva dos imágenes, y ninguna sin figuras;
    - el encuadre de búsqueda deja 0 centros fuera;
  - instantánea `Evaluaciones/0.1.339`, D336 retirada, prompts (33) y auditorías con 0 ERROR.
- **Ningún número del motor cambia:** solo se dibuja y se incrusta.

## 4. Pendiente

- **Tanda P8j terminada:** D314, D142, D333, D334, D336, D338 y D339 cerradas. En P8 quedan D335 (los
  demás mensajes del núcleo, y el idioma del PDF) y D337 (el exportador DXF importa el motor).
- **A mano, en la quinta prueba de la interfaz:**
  - el diálogo del informe;
  - el PDF con los dos encuadres, abierto en un visor;
  - el DXF con anotaciones, en un CAD.
