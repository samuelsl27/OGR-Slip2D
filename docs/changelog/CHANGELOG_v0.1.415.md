# OGR Slip2D v0.1.415

**Escalar, Rotar y Expandir / contraer se comportan igual. No queda el marcador en el pivote, los dos resultados se
leen en la barra, los dos diálogos dicen lo mismo del pivote y Expandir no deja vértices alineados (D353).**

Es la cuarta de la tanda P8n. La geometría que resulta es la misma: el área, las regiones y los vértices que son
esquinas.

## 0. Lo que se encontró

Cada punto de la ficha (la quinta prueba de la interfaz, 0.1.355, H14) se midió antes de tocarlo.

- **El círculo naranja del pivote** es el marcador del forzado (`_last_snap`).
  - El clic del pivote resuelve el forzado, y el modo de escalar o rotar no lo vuelve a mover: `mouseMoveEvent`
    solo fuerza en los modos de dibujo.
  - Nada lo borraba después: se quedaba hasta cambiar de modo. Es la misma clase de falta que D323.
  - Lo mismo pasaba al cancelar con Esc un dibujo de Expandir: `_cancel_drawing` no lo tocaba, y `_finish_drawing`
    sí.
- **El mensaje de escalar no lo tapaba nadie.** Se midió con la ventana real a 1200 px, registrando cada
  `showMessage` de la barra con su origen.
  - Tras el clic del pivote solo se escriben la ayuda del modo, «Ahora pulsa el pivote…» y el mensaje del
    resultado; en los 2,5 s siguientes, nada más.
  - Los dos mensajes duraban 2 s, y los dos se cortaban donde empiezan los indicadores: quedaban unos 240 px en
    castellano. Se leía «External Boundary escalado…» y «External Boundary rotado 9…».
  - Lo primero que se perdía era justo el resultado, y el nombre salía en inglés: es el nombre guardado, que es el
    nombre del tipo.
  - La prueba vio el de rotar y no el de escalar porque su captura llegó antes de los 2 s.
- **El diálogo de rotar no tenía la nota del pivote**, aunque los dos se abren con el pivote pulsado ya escrito.
- **Expandir con una polilínea** siempre deja los dos puntos de corte como vértices del exterior nuevo
  (`cand_keep_* = [cut1] + … + [cut2] + …`). La única limpieza, `_dedupe`, quitaba duplicados y no alineados.
  - Ampliando el ejemplo por la derecha, (50, 0) y (50, 15) quedaban en medio de los lados nuevos de abajo y de
    arriba.
  - No movía ningún número: el rebanador integra el terreno entre sus quiebros, y las regiones dependen del área.
    Pero el exterior tenía ocho vértices donde hay seis esquinas.

## 1. Qué cambia

- **`ogr_gui/canvas/canvas_view.py`:**
  - `_clear_transform_target` borra el marcador del forzado. Se llama al pulsar el pivote (antes de emitir), con
    Esc y al cambiar de modo;
  - `_cancel_drawing` también lo borra.
- **`ogr_gui/main_window.py`:**
  - Escalar y Rotar escriben con la misma forma, el resultado delante y el contorno detrás:
    - «Escalado ×1.2: Contorno exterior», o «Escalado ×(1.5, 0.5): …» con dos factores distintos;
    - «Rotado 90°: Contorno exterior»;
  - duran 6 s, como el mensaje de una anotación añadida (`_transform_done`);
  - el nombre del contorno va en el idioma de la interfaz cuando es el de por defecto (`_boundary_label`), y si no,
    el que se le dio.
- **`ogr_gui/i18n/__init__.py`:** las dos plantillas nuevas en castellano; se retiran las dos viejas.
- **`ogr_gui/dialogs/boundary_dialogs.py`:**
  - una sola nota del pivote, `_pivot_note()`, la misma clave `tr` de antes, en los dos diálogos;
  - el de rotar lleva también `hold_wrapped_height`, como el de escalar (D321).
- **`ogr_core/geometry/expand_shrink.py`:** `_drop_straight` quita del exterior nuevo los dos puntos de corte cuando
  quedan sobre el segmento de sus vecinos.
  - La tolerancia es relativa: 1e-9 de la diagonal.
  - Se exige que el punto quede entre sus vecinos, para no quitar una punta de ida y vuelta.
  - Cualquier otro vértice alineado es del usuario y se queda.
  - Lo usa también el `external_reshape` del API, que llama a la misma función: el agente recibe lo mismo.
- **`tests/test_transform_tools_v1415.py`**, nuevo, con 13 tests.
- El número en los nueve sitios y el contador de los dos README.

## 2. Qué se probó

- **`tests/test_transform_tools_v1415.py`,** con el lienzo real (mostrado, a un zoom conocido, con el forzado puesto):
  - no queda el marcador tras escalar, tras rotar, tras Esc con un contorno elegido y tras cancelar un dibujo de
    Expandir;
  - los dos mensajes tienen la forma común en castellano, se lee el resultado al ancho de la ventana y duran 6 s;
  - los dos diálogos llevan la misma nota, en castellano;
  - Expandir:
    - el caso de la prueba queda con seis vértices, ninguno alineado, y 1200 m²; el arco quitado sigue siendo
      [(50, 0), (50, 15)];
    - un punto de corte que es esquina se queda;
    - un vértice alineado del usuario se queda;
    - un contorno de material que acaba en un punto de corte que se quita da las mismas regiones y materiales que
      la misma expansión sin la limpieza (950 y 250 m²);
    - deshacer y rehacer devuelven exactamente el proyecto.
- **Un hueco del primer borrador del test, cazado al discriminarlo:** el caso de deshacer comprobaba «seis
  vértices». El exterior del ejemplo ya tiene seis, y el manejador no expandía porque faltaba entrar en el modo como
  lo hace el menú. Ahora comprueba también el área y (60, 0).
- **La discriminación,** con el árbol de 0.1.412 y el test copiado: fallan 12 de 13. Pasa la esquina que se queda,
  que es una guarda.
- **`d353()`** da SIGUE ABIERTO con 0.1.412, por los cuatro puntos, y CUBIERTO POR TEST con 0.1.415.
- **Los vecinos:** escalar y rotar con clics, expandir (dibujo, API y reglas F2), el vértice de cierre, el redibujado
  del lienzo, los diálogos de contorno, el censo de modos, el castellano, las traducciones, el tamaño de los
  diálogos y el deshacer del API: 266 de 266.

- **La suite entera con `--jobs 4`:** **7044 de 7044, `Failed: 0`**, sin `Leaks` ni `Chunks died`, en 26,9 min. La
  serie no toca: 16 commits desde la última.
- **El banco:**
  - `verificar_cierres.py` entero en la raíz da 126 comprobaciones con 0 bajadas;
  - el del 02 en seco da los mismos veredictos (234 de 234);
  - D353 se cierra: instantánea, retirada, `PAQUETES` podado, cadena tachada, prompts y auditorías con 0 ERROR en la
    raíz y en el 02.

## 3. Reportado y sin tocar

- **Otros mensajes de la ventana nombran el contorno por su nombre guardado, en inglés:** Eliminado, Copiado, Movido
  y «Añadido … con N vértices», este con `display_name`. Es la misma causa, pero la ficha no los pedía.

## 4. Qué falta

- Verlo a mano en el escritorio real, a la anchura de la pantalla de la prueba:
  - el mensaje, y si los 6 s bastan para leerlo;
  - el pivote sin el círculo;
  - la nota del diálogo de rotar;
  - el exterior ampliado.
