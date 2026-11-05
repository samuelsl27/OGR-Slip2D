# OGR Slip2D v0.1.427

**Superficies no circulares del usuario, guardadas en el modelo (D357, primer paso).**
- Una polilínea dibujada a mano en la ventana o dada por el API se guarda en `Project.user_polylines`:
  - viaja en el `.ogr`, solo si hay alguna;
  - se deshace;
  - cada corrida **no circular** la analiza junto a la búsqueda, como las circulares analizan los círculos del usuario.
- **Su factor de seguridad es, método a método, el que da `surface_evaluate`** para la misma polilínea.
- Una corrida circular la salta y lo dice. Una no circular salta los círculos y lo dice, como antes.
- **Una sola regla decide si una polilínea es una superficie** (`checked_points`), y la preguntan todas las puertas:
  la ventana, `user_surface_add`, `surface_evaluate` y la corrida.
  - **`surface_evaluate` deja de evaluar ordenada, como si fuera otra superficie, una polilínea que retrocede en x:
    ahora la rechaza.** Lo decidió la propietaria (§0).

Es la primera versión de la tanda P9 (D357, el método de Sarma con dovelas no verticales, 0.1.427–0.1.434). Va primero
porque no depende de ninguna fuente. El método cuelga sus ángulos y resistencias de interfaz de los vértices de una
superficie que se queda en el modelo, y hasta hoy no existía ninguna.

## 0. Lo que se encontró

- **No había superficies no circulares del usuario** (A1 del plan).
  - `project.user_surfaces` solo guardaba círculos.
  - `user_surface_add` rechazaba las polilíneas, la ventana no las dibujaba y el motor las saltaba en las corridas no
    circulares.
  - Una polilínea solo se podía evaluar una vez, con `surface_evaluate`, y se olvidaba.
- **El ajuste de los extremos al contorno exterior vivía solo en el API** (`ogr_api/ops/analysis.py`, D244 y D259).
  - La corrida no puede importar el API, y una regla que solo aplica una puerta es como dos puertas acaban dando dos
    respuestas.
  - Se bajó al motor palabra por palabra (`ogr_slip2d/surface.py`, `snap_polyline_ends`), y el API lo envuelve con
    sus propias palabras.
  - Lo siguen cubriendo los tests de D244 y D259 (24 de 24).
  - Los scripts de auditoría del banco que importan `_snap_polyline_ends` (`P5_0260`) siguen sirviendo: misma firma y
    mismo efecto.
- **`SlipSurface` ordena sus vértices por x al construirse** (`surface.py:147`). Una puerta que no pregunte si la
  polilínea avanza en x evalúa **otra superficie sin decirlo**:
  - **`surface_evaluate` lo hacía desde que existe.** `[[19, 25], [31, 14.5], [25, 18], [37, 15]]` daba 1,178925 en el
    talud de ejemplo, el factor de la polilínea ordenada, sin nota.
    - Es anterior a esta versión; se lo presenté a la propietaria antes de tocarlo (regla 6).
    - Decidió que se rechace, con la misma regla que el resto (opción a).
  - **La corrida lo habría hecho con una polilínea guardada que retrocede** (un `.ogr` editado a mano, o un script que
    no use `from_points`).
    - Lo encontró la revisión de esta misma versión (`revisar`), antes de publicarla, y lo corregí aquí.
    - A/B en el mismo proceso con la regla apagada: la polilínea en zigzag salía con el factor exacto de la ordenada
      (1,1789246253059356) **y se anunciaba como la superficie crítica del usuario**.
    - Con la regla no se analiza, y se dice (`search.user_polyline_not_a_surface`).
  - **Un tramo vertical** llegaba a `surface_evaluate` como «Moving the ends of the polyline onto the External Boundary
    would make x stop increasing», un movimiento que nadie había pedido. Ahora dice lo que es.
- **Un `.ogr` editado a mano con una polilínea sin puntos** habría parado toda corrida no circular: un `IndexError` al
  nombrarla en una nota.
  - Ahora se rechaza con su nota, y la polilínea de al lado se sigue analizando.
  - El lienzo y el gestor tampoco se paran con ella.
- **Caminos equivocados, para quien repita algo de esto:**
  - **La primera identidad del test** comparaba la corrida con una búsqueda construida a mano. Difería en 2,4·10⁻⁴
    porque esa búsqueda usa la tolerancia por defecto del método, no la del proyecto. No es un defecto, y el test pasa
    ahora por la búsqueda configurada.
  - **El caso de «un extremo que no se puede mover» no lo era:** (−40, 60) iba a parar a (0, 25), que sigue a la
    izquierda del vértice siguiente.
  - **Ocho archivos quedaron en CRLF** por reescribirlos con `Path.write_text`. La regla de escribir en bytes estaba en
    mi memoria. Se devolvieron a LF en bytes, sin ningún otro cambio.
  - **La suite entera encontró dos cosas que las corridas filtradas no veían:**
    - el inventario de acciones fija cuántas hay mapeadas (`test_f3b_ops_v1201`): 116, y ahora son 118;
    - **«superficie de deslizamiento» es una forma retirada**, en favor de «superficie de rotura»
      (`test_voice_and_terms_v1325`), y yo la había usado en cuatro textos nuevos. Se cambiaron los cuatro, y
      también el tooltip nuevo con mayúscula, que el test no ve.
  - **Un campo `{fos}` en una plantilla** casaba con la sigla retirada «FoS» del español (`test_terms_spanish_v1323`
    mira los textos sin distinguir mayúsculas). Se llama `{factor}`.
  - **Un comentario decía que el `QGraphicsPathItem` esquiva D395.** D395 midió también `QGraphicsRectItem`, que
    comparte el mismo `setPen`, y aquí (Python 3.14) no se puede medir. Se reescribió sin esa afirmación: un solo
    elemento y un solo `setPen` por superficie, tenga los vértices que tenga.
- **Una desviación del plan, a propósito.**
  - El plan decía que el ajuste de extremos lo usaría también «la herramienta de la ventana». No es así: la ventana
    guarda la polilínea como se dibujó, y el motor la ajusta al **analizarla**, como a una que llega por el API.
  - Así, una polilínea guardada sigue valiendo si después se edita el terreno, y hay un solo sitio que decide dónde
    empieza una superficie.
  - Está apuntada también en el plan de la spec 009.
- **La revisión adversaria de esta versión** (seis lentes independientes y tres escépticos por hallazgo, en solo
  lectura).
  - Sacó 34 hallazgos. 52 de los 108 agentes murieron por el límite de uso, así que verifiqué a mano los que se
    quedaron sin votos.
  - **Se corrigieron aquí los 22 que trae esta versión o que esta versión extiende a las polilíneas.** Los
    preexistentes van a la propietaria (§3).
  - **Uno habría dejado la suite en rojo:** las dos acciones nuevas quedaban en gris sin decir por qué en la barra de
    estado. `tests/test_disabled_reasons_v1294.py` exige un status tip en toda entrada gris del menú (D289b), y mis
    corridas filtradas no incluían ese archivo.
  - **Una polilínea guardada con puntos de tres coordenadas, un punto `None` o un diccionario paraba la corrida
    entera.** `checked_points` solo leía `p[0]` y `p[1]`, y el motor volvía a desempaquetar los puntos crudos. Ahora:
    - `_points_of` exige pares de números;
    - el motor construye su superficie con lo que devuelve la regla;
    - `ends()` nombra cualquier polilínea sin romperse.
  - **Un factor que el cribado rechaza** (m-alpha) entraba en la población sin ninguna nota: F = 0,22 junto a un
    1,38 publicado. Ahora lo dice `search.user_polyline_inadmissible`.
  - **Dos polilíneas con los mismos extremos** (lo normal al dibujar de la misma cresta al mismo pie) daban la misma
    frase, y la corrida guarda cada frase una vez, así que se perdían notas. Las notas nombran ahora cada polilínea
    por su número en la lista, como el gestor, y por su número de vértices.
  - **En la ventana:**
    - una polilínea rechazada se perdía entera y no quedaba nada que corregir: ahora el lienzo pregunta la regla
      antes de soltar el dibujo, dice el motivo y deja los puntos para «Deshacer el último vértice»;
    - el motivo era siempre «tiene que avanzar en x», también con una coordenada no finita (la tabla de
      coordenadas acepta «nan»): `NotASurface.kind` da ahora el motivo verdadero;
    - el modo de dibujo sobrevivía a un cambio a tipo circular, y la ventana guardaba lo que el API rechaza: ahora
      la ventana también lo rechaza.
  - **`project_get('user_polylines')`** daba «Unknown section» en un modelo sin polilíneas, y su gemela
    `user_surfaces` daba `[]`. Ahora da `[]`.
  - **`surface_evaluate` cambiaba de contrato sin decirlo:** ahora lo dicen su descripción MCP, `herramientas.md` y la
    guía.
  - **El docstring que bajé al motor copiaba entre comillas dos frases de la documentación de la referencia.** Venía
    del API desde 0.1.258, y AGENTS.md no permite copiar su texto, así que se parafraseó.
  - **Cuatro tests no podían fallar por lo que decían probar:**
    - el de «la polilínea sale intacta» corría en un modelo donde el motor no escribe nada en su copia: ahora lleva
      una grieta de tracción y un extremo fuera del terreno;
    - el del rechazo en la ventana pasaba aunque el manejador se cayera, porque Qt se traga la excepción de un
      slot: ahora llama al manejador y lee la barra de estado;
    - el del gestor borraba siempre la primera polilínea: ahora elige la segunda de dos con los mismos extremos, y
      deshace;
    - la nota del salto en circular se comprobaba con una rejilla de 294 círculos: ahora con 18.
  - **El censo de funciones con notas codificadas** (`test_search_notes_v1349`) no incluía `_evaluate_user_polyline`.
  - **La spec 009** no marcaba como hecho nada de 0.1.427.

## 1. Qué cambia

- **`ogr_core/geometry/user_polyline.py`** (nuevo):
  - `UserPolylineSurface`: puntos e id;
  - **`checked_points`, la regla:**
    - pares de números;
    - dos puntos finitos como mínimo;
    - una polilínea dibujada de derecha a izquierda se invierte;
    - la x tiene que avanzar estrictamente;
  - **`NotASurface`** (un ValueError): su `kind` dice qué regla falló, para que la ventana dé el motivo en su
    idioma;
  - `from_points` aplica la regla. `from_dict` no vuelve a comprobar la geometría, a propósito, para que un archivo
    editado se siga abriendo; la corrida sí la comprueba;
  - `ends()` y `vertex_count()` nombran cualquier polilínea, también una mal guardada.
- **`ogr_core/project/project.py`:** `Project.user_polylines`, escrita en el `.ogr` solo si no está vacía. Un modelo
  sin polilíneas conserva su huella (`model_hash` y `document_hash` resumen todo el `to_dict`).
- **`ogr_core/project/commands.py`:** `LIGHT_ATTRS` gana `user_polylines`, así que el deshacer las recoge.
- **`ogr_slip2d/surface.py`:**
  - re-exporta `UserPolylineSurface`;
  - `slip_surface_of` crea una superficie nueva en cada evaluación, porque el motor escribe en la que recibe (la grieta
    de tracción mueve su último vértice), y la construye con lo que devuelve la regla;
  - `snap_polyline_ends` y `EndMove`, bajados del API.
- **`ogr_slip2d/search.py`:**
  - `_evaluate_user_surfaces` evalúa las polilíneas en las corridas no circulares y las salta, con su nota, en las
    circulares;
  - `_evaluate_user_polyline` hace, por orden:
    - la regla;
    - el ajuste de extremos;
    - `evaluate_surface`;
    - las notas, también la del cribado;
  - `_polyline_at` nombra la superficie por su número, sus vértices y sus extremos.
- **`ogr_slip2d/search_note_messages.py`:** diez códigos `search.user_polyline_*`, con su español en
  `ogr_gui/i18n/__init__.py`.
- **`ogr_api/ops/search_objects.py`:**
  - `user_surface_add` acepta `{'type': 'polyline', 'points': ...}`, solo con el tipo de superficie no circular
    (`Conflict` si no);
  - `user_surface_delete` borra de las dos listas.
- **`ogr_api/ops/analysis.py`:**
  - `_snap_polyline_ends` envuelve al motor;
  - `surface_from_spec` aplica `checked_points` a la polilínea.
- **`ogr_api/ops/project.py`:** `project_get` lee `user_polylines` como lista vacía cuando el archivo no la escribe.
- **`ogr_mcp/server.py`, `ogr_mcp/guide.py` y `docs/mcp/herramientas.md`:** `user_surface_add`, `user_surface_delete` y
  `surface_evaluate` describen la polilínea y su regla.
- **`ogr_api/inventory.py`:** mapea las dos acciones nuevas.
- **Ventana:**
  - `ToolMode.DRAW_USER_SURFACE`, con su cursor y su texto de estado;
  - el lienzo pregunta la regla antes de soltar un dibujo:
    - si no es una superficie, dice el motivo verdadero y deja los puntos para corregirlos;
    - si lo es, la entrega por la señal `user_surface_drawn`;
  - el lienzo dibuja las polilíneas guardadas, discontinuas;
  - Superficies → **«Añadir superficie no circular»** y **«Gestionar superficies no circulares...»**:
    - en gris con tipo circular, y lo dicen en la barra de estado (`gate`, D289b);
    - las de círculos no cambian;
  - la ventana rechaza una polilínea que le llegue con tipo circular, con la frase del API;
  - cada polilínea dibujada es un paso de deshacer, y cada borrado también.
- **Tests cambiados a propósito:**
  - **`tests/test_f2_ops_v1196.py`:** la polilínea, que antes se rechazaba siempre, ahora se acepta con el tipo no
    circular. La razón está en su docstring.
  - **`tests/test_window_undo_v1301.py`:** `MODEL_ATTRS` gana `user_polylines`.
  - **`tests/test_search_notes_v1349.py`:** las muestras de los diez códigos, `USER_PL_SKIPPED` con los dos números,
    y `_evaluate_user_polyline` en el censo de funciones con notas codificadas.
  - **`tests/test_add_surface_three_points_v1168.py`:** `_HINTS_TOTAL` pasa de 46 a 47, por el texto de estado nuevo
    con su español.
- El número en los nueve sitios y el contador de los dos README.

## 2. Qué se probó

- **`tests/test_user_polylines_v1427.py`,** nuevo, con 46 tests. Las dos corridas compartidas de los nueve métodos cuestan
  menos de 1 s, y el archivo entero unos 4 s de reloj, 1,3 s de ellos en importar la ventana.
  - **Identidad:** en una corrida no circular, el factor de la polilínea guardada es, bit a bit y en los nueve métodos,
    el que da `evaluate_surfaces` (la puerta de `surface_evaluate`). Con un extremo movido, `surface_evaluate` da el
    mismo factor a 2·10⁻⁶, que es su redondeo a seis decimales.
  - **Compite por el mínimo:**
    - gana a la búsqueda Path de 5 superficies en los métodos en que su factor es menor, y la nota lo dice;
    - en los demás no cambia la crítica;
    - la población de la búsqueda y sus contadores no se mueven.
  - **Persistencia:**
    - ida y vuelta por el `.ogr`;
    - un `.ogr` viejo abre;
    - sin polilíneas no se escribe la clave y la huella no cambia;
    - viaja con la copia de diseño y con un paso de deshacer.
  - **Una regla para todas las puertas:** la polilínea en zigzag `_ZIG` (`_WINNER` con dos vértices intercambiados,
    que ordenada ES `_WINNER`) la rechazan:
    - el modelo y la ventana;
    - el lienzo, que conserva el dibujo;
    - `user_surface_add` y `surface_evaluate`;
    - la corrida, con su nota.
  - **Lo que no cambia:** `surface_evaluate` sigue aceptando una polilínea dada de derecha a izquierda, con el mismo
    factor bit a bit.
  - **Lo que un archivo editado o un script pueden guardar** (sin puntos, un punto, NaN, tres coordenadas, `None`, un
    diccionario) se rechaza con su nota y no para la corrida. Un array de numpy se analiza, con el factor de la lista.
  - **Cada nota, en una corrida real:**
    - rechazada por el rebanador;
    - quitada por un filtro;
    - sin factor (Bishop con una iteración);
    - un factor que el cribado rechaza;
    - dos polilíneas con los mismos extremos dan dos notas;
    - círculos y polilíneas guardados a la vez, cada tipo con los suyos.
  - **La ventana:**
    - menú alcanzable;
    - gris con su motivo en la barra de estado;
    - el modo de dibujo;
    - lo que entrega el lienzo y el dibujo que no es una superficie;
    - un paso de deshacer;
    - el rechazo con tipo circular;
    - el dibujo de las polilíneas guardadas;
    - el gestor, que borra la elegida, se deshace y aguanta una polilínea mal guardada.
- **A/B en el mismo proceso de la regla en el motor:** con `checked_points` apagado, la `_ZIG` guardada sale con el
  factor exacto de `_WINNER` (1,1789246253059356) **y se anuncia como la crítica del usuario**. Con la regla, no se
  analiza y se dice. El control repetido da lo mismo.
- **Discriminación en el árbol de 0.1.426** (`git archive` de 98bbae3, sin el buscador editable y comprobando los
  `__file__`):
  - fallan los 28 tests que tenía el archivo entonces;
  - 25 por la ausencia de los nombres nuevos, que es lo que es una función nueva;
  - 3 del API por comportamiento: se rechazaba toda polilínea.
- **Vecinos:** superficies, menús, español, inventario, MCP, lienzo, mensajes, deshacer, huellas, polilíneas, notas,
  F2, D244/D259, API, licencia, motivos de lo gris, tooltips, retroanálisis, Newmark, Interpretar y resultados.
  - 84 archivos y 1215 tests. El único fallo fue el del campo `{fos}` (§0), y se corrigió.
- **Suite entera con `--jobs 4`,** dos corridas:
  - **la primera:** 7180 en verde y 2 fallos, los dos de esta versión (el número del inventario y la forma retirada,
    §0);
  - **la segunda, tras corregirlos: 7182 en verde, 1 saltado y 0 fallos,** sin fugas ni tramos muertos.
  - Tardó 21,5 min, frente a los 20,1 de referencia, y sin ningún proceso ocupando un núcleo.
  - La última corrida en serie fue hace 5 commits, así que no toca otra.
- **El banco** (fuera de git). Ningún número debería moverse: un modelo sin polilíneas sigue el camino de siempre.
  - **Cierran las comprobaciones que tocan las superficies del usuario y los extremos de polilínea:**
    - en la raíz, D346, D381 y D369, llamadas sin fusionar ni escribir su JSON (el VC de la raíz no tiene modo seco);
    - en el 02, D58, D244, D256 y D259, con `--seco`.
  - **`auditoria_invariantes.py`: 0 ERROR en la raíz** (71 AVISO, con `--seco`) **y en el 02.**
    - El del 02 no tiene modo seco: ignoró el argumento y reescribió su `INVARIANTES.md` e `invariantes.json`.
    - Frente a la instantánea 0.1.411, las diferencias son del trabajo del banco entre medias (45 → 31 defectos
      abiertos, 16 archivos distintos de la instantánea), no de esta versión.

## 3. Qué queda abierto

- **Preexistentes que encontró la revisión, para la propietaria (regla 6).** No se tocan sin su decisión. Varios los
  extiende esta versión a las polilíneas, porque ahora una polilínea del usuario puede ser la crítica de una corrida
  no circular.
  1. **(alta) El retroanálisis ignora las superficies del usuario.**
     - `back_analysis.py:579` recorre `run.evaluations` y no `run.user_evaluations`.
     - Medido: con la polilínea del usuario como crítica (F = 1,1232, Janbu), el retroanálisis publica 190,99 kN/m,
       de una superficie de la búsqueda con F = 1,309, cuando la polilínea necesita **259,02 kN/m**. Es del lado
       inseguro.
     - Con círculos ya pasaba (166,33 frente a 145,99 kN/m).
  2. **(media) Con Newmark, una superficie del usuario crítica se queda sin desplazamiento.** La cabecera pasa a Ky
     sin aviso, y la tabla enseña 8,95 cm como máximo cuando la crítica se movería 34,8 cm
     (`analysis_runner.py:2442`, solo `result.evaluations`).
  3. **(media) `results_query` `filter` y `raw_data`, y el filtro y el CSV de Interpretar, dejan fuera las superficies
     del usuario.** Con la crítica en F = 1,1789, el filtro `fos_max = 1,2` sale vacío. Ninguna fila dice que es del
     usuario. Es de v0.1.201.
  4. **(media) El panel de resultados e Interpretar dicen «No results»** cuando la búsqueda no deja población (un foco
     lo rechaza todo) y la polilínea del usuario es la crítica válida.
  5. **(media) Un redibujado a mitad de un dibujo** (la edición de un agente, Opciones de superficie) deja muertos los
     elementos de la vista previa. Todas las herramientas de dibujo de la sesión lanzan `RuntimeError` desde
     entonces, y el dibujo se pierde (`canvas_view.py:587`).
  6. **(media, regla 2) «Drawing cancelled.» y «Need at least 3 distinct points to close a boundary.»** salen en inglés.
     Estaba anotado en el changelog de 0.1.168.
  7. **(baja) Lo que esta versión arregló para las polilíneas sigue pasando con los círculos:**
     - un círculo que el cribado rechaza no deja nota;
     - sus acciones, en gris con tipo no circular, no dicen por qué en la barra de estado;
     - su modo de dibujo sobrevive a un cambio de tipo.
  8. **(baja)** La nota «ninguna superficie válida» cuenta como de la búsqueda las superficies del usuario que rechaza
     el rebanador.
  9. **(baja)** `surface_evaluate` explica una superficie quitada por un filtro como «does not cut the model», mientras
     la corrida nombra los filtros.
  10. **(baja)** El informe PDF no dice que el mínimo global es una superficie dibujada a mano.
  11. **(baja)** El test de formas retiradas distingue mayúsculas. Tres entradas de antes de esta versión empiezan
      por «Superficies de deslizamiento», entre ellas el tooltip de los círculos, que queda junto al nuevo, que ya
      dice «de rotura».
- **Las pruebas a mano de la ventana,** que hace la propietaria:
  - dibujar con el ratón y terminar con Intro o con el botón derecho;
  - la tabla de coordenadas, Esc, «Deshacer el último vértice» tras un rechazo;
  - el gestor, deshacer y rehacer;
  - el gris al cambiar el tipo;
  - una polilínea añadida por un agente con la ventana abierta.
- **Lo que sigue en la tanda P9:** 0.1.428, el núcleo del solver de Sarma, sin registrar.
