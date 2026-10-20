# OGR Slip2D v0.1.335

***Añadir superficie (centro y radio)* se hace en el lienzo, con el centro y un punto de la
circunferencia, como en la referencia (D142, primera parte).** Tercera versión de la tanda P8j.

## 0. Lo que se encontró

- **El modo existía y nadie entraba en él.** `ToolMode.ADD_SURFACE_CR` tenía su cursor y su ayuda («Pulsa
  el centro y después un punto de la circunferencia») desde v0.1.3, y la acción tecleaba el centro y el
  radio en dos diálogos (D142, medido en v0.1.168).
- **La referencia lo dibuja:** el centro con un clic, y el radio arrastrando o escrito.
- **Lo que quedaba de D142 antes de esta versión:** cuatro modos en los que no entraba nadie
  (ADD_SURFACE_CR, SCALE_BOUNDARY, ROTATE_BOUNDARY y EXPAND_SHRINK). Esta versión cablea el primero; los
  otros tres van en 0.1.336.

## 1. Qué cambia

Por decisión de la propietaria (2026-10-19, cablear como la referencia):

- **El lienzo:**
  - en ADD_SURFACE_CR, el primer clic fija el centro y el segundo, un punto de la circunferencia; emite
    `centre_radius_picked(cx, cy, px, py)`;
  - un segundo clic a menos de `_MIN_PERP_PX` píxeles del centro no da radio. Se ignora y se conserva el
    centro, como el flujo de tres puntos ignora un clic repetido: con el forzado activo, el clic cerca del
    centro cae exactamente en él;
  - mientras se mueve el ratón, la vista previa enseña el radio y la circunferencia;
  - **Intro escribe lo que no se ha pulsado:** el radio, si ya hay centro, o el centro y el radio, si no
    lo hay (`centre_radius_typed`). Es el camino tecleado de antes, que así no se pierde.
- **La ventana:**
  - la acción entra en el modo;
  - `_on_surface_cr_picked` y `_type_surface_centre_radius` son un paso de deshacer cada una, «Add user
    surface», y comparten `_add_user_circle`, que añade el círculo, sale del modo y lo dice;
  - un diálogo cancelado no deja paso.
- **La etiqueta pierde los «…»**, porque ya no abre un diálogo (la convención de D102): «Añadir superficie
  (centro y radio)».

## 2. Tests

- **`tests/test_add_surface_centre_radius_v1335.py`** (nuevo, 11 casos), con clics reales en el lienzo
  mostrado, el zoom conocido y sin forzado:
  - **dos clics dan el círculo con el centro en el primero, y su radio es `hypot` de los dos, exacto** (la
    referencia es la geometría, regla 1);
  - el primer clic no añade nada, y un clic sobre el centro se ignora conservándolo;
  - es un paso de deshacer;
  - la vista previa enseña la circunferencia;
  - Intro pide el radio tras el centro, o los dos sin centro, y un radio cancelado no añade nada ni deja
    paso;
  - Esc y un cambio de modo olvidan el centro pendiente (D308), y la herramienta sigue.
  - **En el árbol viejo la acción abre el diálogo de puntos**, que sin pantalla bloquea la corrida (la
    primera prueba sobre 0.1.334 se colgó): el test sustituye los dos diálogos por una negativa en cada
    caso, así que allí falla en vez de bloquear.
- **Cambios deliberados:**
  - `test_add_surface_three_points_v1168`: ADD_SURFACE_CR sale de los modos en los que no entra nadie, y
    la etiqueta vecina pierde los «…»;
  - `test_undo_settings_annotations_v1305`: el paso «Add user surface» se comprueba en los dos caminos,
    el tecleado y el pulsado.

**Con el código de 0.1.334 fallan 10 de los 11 casos nuevos y los cuatro cambiados a propósito.** El que
pasa, «sin nada pulsado, Intro pide los dos», es precisamente el camino tecleado de antes: allí la acción
pide el centro y el radio. Se corrió sobre un `git archive` de 0.1.334, sin el buscador editable.

## 3. Verificación

- **El test de esta versión**, 11/11, y los vecinos, 169/169 en 9 archivos: los modos de v1168, deshacer, las
  superficies del usuario, el diccionario y los censos de castellano.
- **Suite entera:** 6283/6283, `EXIT=0`, 72 min.
- **Banco:**
  - `verificar_cierres.py` entero: 81 comprobaciones, 0 bajadas;
  - D142 anota `ADD_SURFACE_CR` en sus partes; quedan tres modos para 0.1.336;
  - se abre **D339**, encontrada al preparar 0.1.336: el menú pasa `checked=False` como índice a
    *Escalar*, *Rotar* y *Expandir / contraer*, que operan sobre el primer contorno. Medida en la ventana
    real, y se arregla en 0.1.336;
  - D334 queda medida: la polilínea no hace nada, y el contorno de material que se dibuja después recorta
    el exterior de 550 a 450 m² en vez de añadirse;
  - instantánea `Evaluaciones/0.1.335`, prompts (38) y auditorías con 0 ERROR.
- **Ningún número cambia:** un círculo del usuario es el de antes, con el centro y el radio que se den.

## 4. Pendiente

- **0.1.336:** Escalar y Rotar con clics, EXPAND_SHRINK retirado y la polilínea de expandir/contraer
  (D142, segunda parte, y D334, que se mide antes).
