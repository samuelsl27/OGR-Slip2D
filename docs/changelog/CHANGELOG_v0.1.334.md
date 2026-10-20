# OGR Slip2D v0.1.334

**Los problemas de la importación DXF llevan un código estable, y el diálogo y el panel de problemas los
dicen en castellano (D314, segunda parte; D314 cerrada).** Segunda versión de la tanda P8j.

## 0. Lo que se encontró

- **Lo que decía la ficha:** los problemas que encuentra el saneador de un dibujo, y por qué falla una vista
  previa, llegaban en inglés al diálogo *Importar DXF* y al panel de problemas. Eran siete frases con los
  números dentro, bajo un prefijo crudo `[external_gap]`.
- **Lo que no decía, encontrado al escribir el test:** los **títulos de los grupos** del panel eran el tipo
  del problema con los guiones bajos cambiados por espacios («External gap», «Dangling end»), pasados por
  `tr()` sin entrada. Salían en inglés en cualquier idioma, y el test de pantalla no los veía: abre el
  diálogo sin archivo, así que el panel nunca se llena.
- **El panel escribía su propio inglés** para el aviso de que las áreas de las regiones no suman la del
  contorno exterior, que no viene del saneador.
- **El mensaje de un archivo que no se puede leer** sigue llevando, tras los dos puntos, el texto del
  sistema operativo o de `ezdxf` («[Errno 2] No such file or directory…»). Ese no se traduce: no es del
  programa.

## 1. Qué cambia

- **`ogr_core/dxf/messages.py`** (nuevo), el catálogo del DXF sobre el mecanismo de 0.1.333:
  - once códigos;
  - el código de un problema es `dxf.` más su tipo, que es como el panel ya los agrupaba;
  - `DxfReadError`, un `RuntimeError` con código, como antes para quien lo capture.
- **El saneador** escribe cada problema por `add_coded_problem`, con la frase, el código y sus valores.
  `add_problem` se queda para los scripts, y un problema escrito así sale tal cual.
- **El importador:**
  - `ImportPreview` gana `error_code` y `error_args`;
  - `area_mismatch_problem(pv)` da con su código el aviso que el panel escribía por su cuenta.
- **El API:** `dxf_inspect` añade `error_code` cuando hay error, y cada problema lleva su `code` y sus
  `args`.
- **La interfaz:**
  - `core_messages` reúne los dos catálogos;
  - el diálogo y el panel dicen cada problema por su código;
  - **cada tipo de problema tiene título propio** («Contorno exterior abierto», «Extremo suelto», «Las
    áreas no cuadran»…), que en la lista del diálogo sustituye al prefijo `[tipo]`.
- **Claves nuevas en el diccionario:** las plantillas del DXF, salvo «No geometry was assigned to any
  layer.», que ya la tenía como consejo del panel, y los ocho títulos.
- **El test de pantalla de 0.1.321 pierde su excepción** para «Could not read the DXF file: ». Su regla
  de «sin fantasmas» fallaría si el inglés volviera.

## 2. Tests

- **`tests/test_dxf_messages_v1334.py`** (nuevo):
  - **el inglés de cada código, con una muestra, es igual a la expresión de 0.1.333, copiada literalmente**;
  - cada código tiene su castellano con los mismos campos, y cada tipo que conoce el panel tiene código y
    título en castellano;
  - **testigos en ejecución** (la frase del código es la que lleva el problema): un dibujo sucio, un
    archivo que no existe, un dibujo sin capa asignada y las áreas que no cuadran;
  - **censo AST de `ogr_core`:** ninguna llamada a `add_problem` y ningún `error =` de una vista previa
    sin su `error_code`;
  - **en castellano:** la lista del diálogo, el árbol del panel y el mensaje de un archivo ilegible.
- **`tests/test_labels_spanish_v1321.py`:** sin la excepción del DXF.

**Con el código de 0.1.333 fallan 13 de los 14 casos nuevos, y el censo de pantalla:** este último por el
mensaje inglés del DXF, que el diálogo enseña ya al abrirse. El 14.º solo mira el propio archivo de test.
Se corrió sobre un `git archive` de 0.1.333, sin el buscador editable.

**Encontrado al pasar los vecinos:** el diálogo dice el error de lectura en dos sitios, al abrirse (lee las
capas para la tabla) y en *Vista previa*. Este segundo era el que se había arreglado primero; el censo de
pantalla abre el diálogo sin pulsar nada y vio el primero. Ahora los dos van por el código, y el test mira
los dos.

## 3. Verificación

- **Los tests de esta versión:** `test_dxf_messages_v1334`, 14/14, y el de pantalla de 0.1.321, sin su
  excepción.
- **Los vecinos**, 220/220 en 12 archivos (el DXF, el castellano, el diccionario, los términos y los
  mensajes de 0.1.333), después de arreglar el error de lectura al abrirse (§2) y la heurística de
  inglés del test nuevo, que buscaba «region» dentro de «región» y ahora busca palabras.
- **Suite entera:** 6272/6272, `EXIT=0`, 72 min.
- **Banco:**
  - `verificar_cierres.py` entero: 81 comprobaciones, 0 bajadas, y D314 **CUBIERTO POR TEST**. La
    comprobación mide que los 41 códigos del motor y los 12 del DXF tienen castellano con sus campos, y
    que un DXF que no existe da su código en la vista previa;
  - instantánea `Evaluaciones/0.1.334`, D314 retirada y tachada en P8;
  - prompts (37) y auditorías con 0 ERROR en la raíz y en el 02.
- **Ningún número cambia:** el saneador y el lector escriben las mismas frases, y lo que se añade son
  campos.

## 4. Pendiente

- **D314 cerrada.** El resto de los mensajes del núcleo, en D335.
- **Siguiente versión, 0.1.335:** *Añadir superficie (centro y radio)* con dos clics (D142, primera parte).
