# OGR Slip2D v0.1.323

**Un solo término castellano para cada cosa:**

- rejilla de presiones de agua;
- altura total y altura de presión;
- descabezamiento;
- carga distribuida, magnitud, expandir / contraer y OSnap;
- FS.

Es la versión de cierre de la tanda P8h.

## 0. Lo que se encontró

Al traducir D300 (0.1.318–0.1.322) salieron tres cosas con dos nombres en la
interfaz en castellano:

- **«Malla de presiones de agua».** El proyecto guarda *malla* para la de
  elementos finitos y *rejilla* para una rejilla: D240 dejó «Añadir
  rejilla», y 0.1.320, «Búsqueda por rejilla». La rejilla de presiones de
  agua es una rejilla de puntos con valores, no una malla de elementos.
- **«Cabeza total» y «cabeza de presión».** Es un calco de *head*, mientras
  que la ayuda del coeficiente Hu de 0.1.320 decía «altura de presión».
- **El fallo por la cabeza de un soporte (*stripping*).** El anclaje
  helicoidal lo llamaba «Descabezamiento», y lo que escribió 0.1.322 para
  los demás tipos, «desprendimiento».

Al preparar la tercera prueba de la interfaz, comparando cada clave nueva de
0.1.318–0.1.322 con las anteriores, salieron cinco más. Esta tanda escribió
cuatro contra los términos que el programa ya usaba, y la quinta es vieja:

- **«Carga repartida»** en las ayudas, las ayudas de datos y las variables,
  cuando los menús dicen «Añadir carga distribuida». El diccionario ya estaba
  mezclado antes: dos mensajes viejos («Carga repartida añadida…» y
  «…eliminada…») también decían «repartida»;
- **«Módulo»** para *magnitude*, cuando el diálogo de cargas dice
  «Magnitud:»;
- **«Ampliar / reducir…»** en el menú contextual del contorno exterior,
  cuando el menú dice «Expandir / contraer el contorno exterior…»;
- **«Forzado a objeto»** en el menú de dibujo, junto a «Snap» y «Orto»,
  que siguen la leyenda de la barra de estado (SNAP, ORTO, OSNAP);
- **«FoS» en castellano** en cinco entradas viejas («FoS frente al
  tiempo…», «FoS medio», «FoS máx:», «FoS mín:», «Marcar FoS = 1.0»),
  cuando otras 31 dicen «FS».

La causa de las de esta tanda es la misma: al escribir el castellano de una clave
nueva no se buscó cómo llamaba el programa a esa cosa.

## 1. Qué cambia

Por decisión de la propietaria, las tres primeras, y por la misma regla (el
término que el programa ya tenía, que fue la que eligió para
«descabezamiento»), las otras cinco, en todo el diccionario:

| Antes | Ahora |
|---|---|
| malla de presiones de agua, método de agua por malla | rejilla de presiones de agua, método de agua por rejilla |
| cabeza total, cabeza de presión | altura total, altura de presión |
| desprendimiento | descabezamiento |
| carga repartida, repartida sobre | carga distribuida, distribuida sobre |
| módulo (de una magnitud) | magnitud |
| Ampliar / reducir… | Expandir / contraer… |
| Forzado a objeto | OSnap (sin entrada: se escribe igual) |
| FoS (en castellano) | FS |

- Son 46 entradas: 26 de las tres primeras, 19 de las otras cinco y una que
  se quita.
- Ninguna clave inglesa cambia, ni ningún texto en inglés.
- *Malla* sigue nombrando la de elementos finitos, *cabeza* la de un
  soporte («Cabeza (x, y):», «placa de cabeza»), y *módulo* el módulo OGR
  FEM2D.

## 2. Tests

`tests/test_terms_spanish_v1323.py` (nuevo), 4 casos:

- **ningún valor del diccionario contiene un término retirado** (las ocho
  formas viejas);
- **los términos nuevos están donde estaban los viejos;**
- **una magnitud es «magnitud»:** ningún valor de una clave con
  *magnitude* dice «módulo»;
- **control:** «Malla de elementos finitos» y «Cabeza (x, y):» conservan su
  sentido.

`test_labels_spanish_v1321` cambia sus cuatro textos esperados a los
términos alineados.

**Con el código de 0.1.322 fallan 3 de los 4 casos;** el control pasa en los
dos árboles. Se corrió sobre un `git archive` de 0.1.322, sin el buscador
editable.

## 3. Verificación

- **Los tests de términos y sus vecinos**, antes de la suite: 189/189.
  - Son términos, etiquetas, soportes, el test de AST, i18n, *Interpret
    Groundwater*, la serie del factor frente al tiempo y estadística.
  - Antes, 235/235 con la rejilla de presiones, el anclaje helicoidal, cargas
    y ayudas de datos.
- **La suite entera se paró dos veces**, al aparecer las alineaciones de §0;
  cada ampliación tiene su propia comprobación en el árbol viejo.
- **Suite entera:** 6151/6151, `EXIT=0`, 62 min.
- **Banco:** `verificar_cierres.py` entero, 61 comprobaciones y 0 bajadas.
- **Ningún número del motor cambia:** solo cambian valores castellanos del
  diccionario.

## 4. Pendiente

- **La tercera prueba de la interfaz,** con Español guardado.
- **D314,** los mensajes del núcleo con códigos estables.
