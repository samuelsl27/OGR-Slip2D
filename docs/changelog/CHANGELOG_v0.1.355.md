# OGR Slip2D v0.1.355

**El informe PDF sale en el idioma de la interfaz, y su pie dice la licencia del programa (D335, última parte;
D335 cerrada).** Decimosexta y última versión de la tanda P8k.

## 0. Lo que se encontró

- **El núcleo no puede importar el diccionario de la interfaz**, así que el informe, que se escribe en el
  núcleo, salía siempre en inglés. Ahora `generate_report` recibe `translate` y `method_name`, y sin ellos
  escribe lo de siempre. Por decisión de la propietaria (2026-10-20):
  - la ventana pasa los suyos y el informe sale en el idioma de la interfaz;
  - el API y el servidor MCP no pasan nada y siguen escribiéndolo en inglés.
- **Basta con una función para traducir.** `core_messages.note_text` dice un mensaje con código por su código
  y una frase fija por `tr()`. Así el resumen y las notas de la norma de cálculo, que llevan código desde
  0.1.353, salen en castellano por el mismo camino que los títulos del informe.
- **Los nombres de método del informe eran una tabla propia** («Ordinary / Fellenius», «Corps of Engineers
  #1»). La ventana pasa los de `ogr_gui/labels.py`, los mismos que enseña en todas partes.
- **Cuatro textos no llevan entrada**, porque en castellano se escriben igual: «Total», «Circular», «FS» y
  «variable». El diccionario no admite una entrada igual a su clave, y `tr()` los devuelve tal cual.
- **El nombre de un material, del proyecto o de un modelo de resistencia no se pasa todo por `translate`.**
  Un material que se llamara «Clay» saldría «Arcilla». Solo pasan los textos fijos del informe y el nombre
  del modelo de resistencia, que es del programa.
- **«ODF» (over-design factor) es una abreviatura del programa, no de una norma.** En castellano queda
  «FSD» (factor de sobredimensionamiento), junto a «Factor de sobredimensionamiento», que es el término que
  ya usaba el diccionario.
- **El pie decía «GPL-3.0»**, que no es la licencia de este programa. Ahora dice «AGPL-3.0-or-later», con
  permiso de la propietaria y solo en ese texto: no se tocan `LICENSE`, `CLA.md` ni las cabeceras SPDX.
- **Dos fallos míos de proceso en esta tanda:** lancé un test y luego una captura del informe mientras corría
  la suite entera de 0.1.350 y de 0.1.351. Ninguno cambia un resultado, pero compiten por los núcleos. Lo
  digo porque la regla es no hacerlo.

## 1. Qué cambia

- **`ogr_core/report/report_generator.py`:**
  - `generate_report(..., translate=None, method_name=None)`;
  - cada texto fijo pasa por `translate`: los títulos, las claves de las tablas, las unidades, el sentido de
    la rotura, la búsqueda, las cabeceras de la tabla de dovelas, los contornos, las cargas de la norma y
    el «Página n»;
  - las frases con valores pasan a plantillas («Method: {0}», «Load '{0}'», «Page {0}»), con el mismo
    inglés;
  - el pie dice AGPL-3.0-or-later.
- **`ogr_api/report_figures.py`:** `method_figures(..., translate=None)` traduce la escala, la superficie
  crítica de la leyenda y el centro crítico. `render._draw_grid` lee la etiqueta del centro de la rejilla.
- **La ventana:** Generar informe pasa `translate=note_text` y `method_name=method_name`, al informe y a las
  figuras.
- **El castellano:** 65 entradas nuevas (61 del informe y 4 de las figuras).

## 2. Tests

- **`tests/test_report_spanish_v1355.py`** (nuevo, 6 casos):
  - **sin `translate` el informe escribe lo mismo que en 0.1.354, texto a texto.** Son 98 textos con palabras
    de párrafos, celdas y pie, tomados del informe de 0.1.354 sobre el modelo del test (con la norma EC7
    DA1-C1 y las figuras), con las marcas de fecha enmascaradas. La única diferencia es la licencia del pie;
  - **con el `translate` de la ventana, en castellano:** no queda ninguno de 26 textos fijos ingleses; salen
    los métodos en castellano, el resumen de la norma y su nota de peso, y «Página 1»;
  - las palabras de las figuras pasan por `translate`;
  - la ventana lo pasa y el API no.

**Con el código de 0.1.354 fallan los 6.** Cinco fallan porque `method_figures` no acepta `translate`, y el
de la ventana porque esta no lo pasa. Sin ese argumento, el de texto a texto fallaría igual en el pie, que
allí dice GPL-3.0. En el primer intento fallaba él mismo en este árbol: enmascaraba la marca de fecha antes
del filtro de textos con palabras, y la referencia se tomó en el orden contrario.

## 3. Verificación

- **El test de esta versión**, 6/6. En el primer intento fallaba uno, el de texto a texto, por el propio test
  (el orden de las máscaras, §2).
- **Los vecinos:** 267/267, en 20 archivos: el informe y sus figuras, el render y el PNG del agente, el
  diálogo del informe y la norma, el API, el servidor MCP, las anotaciones, el castellano, los mensajes del
  núcleo, las capas y las licencias.
- **El inglés no cambia:** sin `translate`, los 98 textos del informe de 0.1.354, salvo la licencia del pie.
- **Suite entera:** 6494/6494, `EXIT=0`, 80 min.
- **Banco:**
  - raíz: `verificar_cierres.py` entero, 89 comprobaciones (una más, `d335`), 0 bajadas. D335 queda
    **CUBIERTO POR TEST**: 423 códigos en 15 catálogos, ninguno sin castellano y ninguno que la ventana no
    conozca; el informe toma `translate` y `method_name`, y su pie dice AGPL-3.0-or-later; y los nueve
    tests de la tanda existen;
  - manual 02: `verificar_cierres.py` entero, 238 fichas, 0 bajadas;
  - **D335 retirada** al índice de cerrados, con su sección en `Evaluaciones/0.1.355`;
  - instantánea `Evaluaciones/0.1.355`, prompts (33) y auditorías con 0 ERROR.
- **Ningún número del motor cambia:** solo cambia quién escribe la frase.

## 4. Pendiente

- **D335 cerrada.** Quedan abiertas en P8:
  - **D340:** los avisos que el motor calcula y la ventana no enseña;
  - **D342:** un campo de filtración guardado pierde los códigos de sus notas.
- **La quinta prueba de la interfaz, a mano.** El prompt para Claude Desktop está en
  `_auditoria/P8_interfaz/PROMPT_prueba_GUI_0.1.355.md`.
