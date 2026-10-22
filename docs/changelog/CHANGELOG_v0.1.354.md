# OGR Slip2D v0.1.354

**Lo que dice la exportación DXF lleva un código estable y la ventana lo dice en castellano; el censo de
superficies rechazadas del API agrupa como la ventana; y el castellano usa un solo término para el
desembalse rápido y para la superficie de tanteo (D335, octava parte).** Decimoquinta versión de la tanda
P8k.

## 0. Lo que se encontró

- **El plan pedía añadir `by_code` a `invalid_summary`, y esa clave ya existe.** Tiene los códigos de error
  de la referencia (−112, −101…) desde que existe el censo. La agrupación nueva se llama **`by_group`**:
  - es el código de la razón, con los valores que cambian de una superficie a otra elididos («…»), como
    agrupa la ventana desde D314;
  - una razón sin código, o un recuento sin evaluación (los extremos fuera del terreno, el círculo que no
    corta dos veces), es su propio grupo.

  `by_reason` y `by_code` no cambian.
- **El resumen de la exportación iba dentro de un marco traducido** («Exportado a %s | 4 entities —
  …»), así que la mitad de la frase salía en inglés. Lo mismo pasaba con lo que se saltaba. Ahora cada
  pieza lleva su código, y los métodos se enseñan por su nombre.
- **Las dos frases que la exportación escribe sin ser mensajes se quedan como están:**
  - la etiqueta que dibuja junto a cada superficie, dentro del archivo DXF («bishop_simplified  FS =
    1.2345»), es contenido del dibujo;
  - el `TypeError` para quien llama con la firma anterior a 0.1.341 es para un programador.
- **Los términos:**
  - «descenso rápido» salía en cinco entradas, más «tras el descenso» en una sexta, y «desembalse rápido» en
    doce;
  - «superficie de prueba» salía en cinco y «superficie de tanteo» en cinco.

  Se queda el término que ya usaba la mayoría, y `test_terms_spanish_v1323` gana las dos reglas.
- **La frase de la superficie probabilística crítica** decía en castellano «las búsquedas Grid, Slope, Path
  y Block», con los nombres ingleses. Ahora usa los de las opciones de superficie: por rejilla, de talud,
  por caminos y por bloques. Se vio en 0.1.353, y el generador no deja cambiar una entrada que ya existe, así
  que se cambia aquí, a mano.

## 1. Qué cambia

- **`ogr_core/dxf/messages.py`:** `EXPORT_MESSAGES`, **8 códigos** `dxf.export.*`: el paquete que falta, el
  archivo que no se escribe, el resumen y sus capas, y lo que se salta (la malla, una superficie que el
  motor no sabe dibujar, una imagen que no se puede leer). Es una tabla aparte de la de la importación,
  que el test de 0.1.334 ata a sus muestras de 0.1.333.
- **`exporter.py` y `annotation_export.py`:** cada frase con su código.
- **`ogr_slip2d/interpretation.py`:** `invalid_group` e `invalid_summary(...)["by_group"]`.
- **La ventana:** la barra de estado de Exportar DXF y su cuadro de error leen los códigos.
- **El castellano:** 7 entradas nuevas (la de la capa no tiene palabras), seis entradas pasan a «desembalse
  rápido», cinco a «superficie de tanteo», y la de la superficie probabilística crítica nombra las
  búsquedas.

## 2. Tests

- **`tests/test_dxf_export_census_v1354.py`** (nuevo, 11 casos):
  - **el inglés es el de 0.1.353, byte a byte:** 10 muestras que cubren los 8 códigos. Son las expresiones y
    el `ExportReport` de 0.1.353, ejecutados con esas entradas;
  - cada código tiene su castellano, con los campos de la plantilla;
  - **censo AST** de las tres funciones;
  - la ventana lee los códigos;
  - **una exportación real**, en castellano: su resumen y la superficie que se salta, bajo el nombre del
    método;
  - **el censo:** una condición en tres superficies con dos valores distintos es un grupo, y un recuento sin
    evaluación es el suyo propio;
  - la superficie probabilística crítica nombra las cuatro búsquedas como las opciones de superficie.
- **`tests/test_terms_spanish_v1323.py`, cambio deliberado:** dos reglas más («descenso rápido» y
  «superficie de prueba») y tres comprobaciones de dónde quedan.

**Con el código de 0.1.353 fallan los 11**, también los de comportamiento: la exportación real no llevaba
código, el censo no tenía `by_group`, y la superficie probabilística crítica decía «Grid, Slope, Path y
Block». Con la versión nueva de `test_terms_spanish_v1323` también fallan allí dos de sus cuatro casos: la regla de
«descenso rápido», que encuentra sus cinco entradas, y la comprobación de dónde quedan los términos.

## 3. Verificación

- **El test de esta versión**, 11/11. En el primer intento fallaban dos, los dos del propio test:
  - el censo tomaba como frase el especificador de formato («.4f») de la etiqueta que se dibuja en el DXF,
    que en el árbol de Python es un f-string anidado;
  - el rechazo falso del censo no tenía el atributo `converged`, que lee `error_code`.
- **Los vecinos:** 427/427, en 23 archivos: el DXF (importación, exportación, anotaciones, problemas), el
  API, los rechazos del terreno, los extremos de las polilíneas, los límites del talud, los términos, el
  castellano, la superficie probabilística crítica, los mensajes del núcleo, *Interpretar* y el desembalse.
- **El inglés no cambia:** las 10 muestras del test son las expresiones y el `ExportReport` de 0.1.353,
  ejecutados.
- **Suite entera:** 6488/6488, `EXIT=0`, 90 min.
- **Banco:**
  - raíz: `verificar_cierres.py` entero, 88 comprobaciones, 0 bajadas;
  - manual 02: `verificar_cierres.py` entero, 238 fichas, 0 bajadas;
  - D335, con su octava parte apuntada;
  - instantánea `Evaluaciones/0.1.354`, prompts (34) y auditorías con 0 ERROR.
- **Ningún número del motor cambia:** solo cambia quién escribe la frase.

## 4. Pendiente

- **D335 sigue abierta.** Queda el informe PDF en el idioma de la interfaz (0.1.355), con el que se cierra.
