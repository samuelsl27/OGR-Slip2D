# OGR Slip2D v0.1.338

**El PNG que genera el agente (`model_render`) dibuja la capa de anotaciones, con la misma geometría que el
lienzo y el DXF (D336, primera parte).** Sexta versión de la tanda P8j.

## 0. Lo que se encontró

- **`render_png` no dibujaba anotaciones.** Pintaba el modelo, las cargas, los soportes y las superficies,
  pero no lo que el usuario había dibujado encima (D336, abierta al planificar la tanda).
- **El encuadre, encontrado por el test al escribirlo.**
  - Los ejes del PNG tienen aspecto igual con `adjustable="datalim"`, y al dibujarse matplotlib recalcula
    uno de los límites a partir de los límites de los DATOS («Ignoring fixed x limits to fulfill fixed
    data aspect…»).
  - Una anotación lejana entra en esos datos. Medido: una línea hasta (1000, 1000) reencuadraba el dibujo
    entero y movía 43 714 píxeles, aunque los límites se habían fijado.
  - Tras dibujar la capa, los ejes recuperan los límites de datos del modelo.

## 1. Qué cambia

- **`ogr_api/render_annotations.py`** (nuevo), el adaptador de matplotlib de las primitivas de
  `ogr_core.annotations.drawing`:
  - los trazos van en coordenadas del modelo, con el color, el grosor y el tipo de línea de su anotación,
    y el relleno debajo;
  - las marcas (puntas de flecha, marcas de cota y de ejes, el arco de un ángulo, la cruz) van **en
    píxeles** en su punto, con `IdentityTransform() + ScaledTranslation`, y miden lo mismo que en el
    lienzo;
  - los rótulos van con `annotate` y un desplazamiento en puntos;
  - la imagen va sobre su rectángulo y debajo del modelo, o en su marco si no se puede leer.
- **`render_png(..., annotations=True)`** dibuja la capa sobre el modelo y dentro de su encuadre.
- **`model_render`**, en el API y en el MCP, gana el parámetro `annotations`.

## 2. Tests

- **`tests/test_png_annotations_v1338.py`** (nuevo, 10 casos):
  - **una forma rellena de un color que no tiene ninguna otra cosa** cubre más de 500 píxeles de ese
    color; ninguno con la capa apagada (regla 7) o la forma oculta; y lo mismo por la operación
    `model_render`;
  - los rótulos son los de las primitivas: el valor de una cota y las coordenadas de los ejes;
  - una punta de flecha mide `ARROW_PX` en píxeles;
  - **una anotación lejana deja el PNG idéntico, byte a byte, al PNG sin anotaciones**;
  - una imagen se dibuja, y una que falta es su marco con su nombre;
  - **ningún adaptador calcula geometría propia:** ni el lienzo, ni el DXF, ni el PNG llaman a `outline`,
    `measured_value` o `nice_step`.

**Con el código de 0.1.337 fallan 9 de los 10.** El que pasa, «oculta no se dibuja», pasa porque allí no se
dibuja ninguna. Se corrió sobre un `git archive` de 0.1.337, sin el buscador editable.

## 3. Verificación

- **El test de esta versión**, 10/10. A la primera dio 9/10: el de la anotación lejana encontró el
  reencuadre (sección 0).
- **Los vecinos:** 20/20 con el render y `model_render`, y 119/119 en 7 archivos (el render del API, los
  campos de agua, las lentes, el puente vivo, el servidor MCP, el resultado inicial del transitorio y los
  inventarios del API).
- **Suite entera:** 6331/6331, `EXIT=0`, 84 min.
- **Banco:**
  - `verificar_cierres.py` entero: 85 comprobaciones, 0 bajadas;
  - D336 sigue abierta, con su primera parte apuntada;
  - instantánea `Evaluaciones/0.1.338`, prompts (34) y auditorías con 0 ERROR.
- **Ningún número del motor cambia:** solo se dibuja.

## 4. Pendiente

- **0.1.339:** el informe PDF con una figura por método (D336, segunda parte).
- **Un aviso de matplotlib en cada PNG, visto en la suite de esta versión.** Fijar los límites alrededor de
  la capa apaga la autoescala, y al dibujar matplotlib avisa de que ensancha uno de ellos para el aspecto
  igual: «Ignoring fixed y limits to fulfill fixed data aspect with adjustable data limits.». Sale 26
  veces en la suite de 0.1.338 y ninguna en la de 0.1.337. El PNG es el correcto, pero el aviso ensucia
  stderr, también el del servidor MCP. Se corrige en 0.1.339, que toca el mismo bloque.
