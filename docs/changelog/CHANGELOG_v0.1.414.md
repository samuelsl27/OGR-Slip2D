# OGR Slip2D v0.1.414

**El paso de deshacer de un contorno añadido dice qué se añadió: «Deshacer «Añadir objeto de búsqueda por
bloques»», «Deshacer «Añadir capa débil»»… (D349).**

Es la tercera de la tanda P8n. Ningún número se mueve.

## 0. Lo que se encontró

- **El nombre era una constante:** `AddBoundaryCommand.description = "Add Boundary"`. Valía para todo contorno que
  se añadía con esa orden, fuera un contorno de material, una capa débil o un objeto de búsqueda por bloques.
  - Por eso la prueba de 0.1.355 (H14) vio «Deshacer «Añadir contorno»» al añadir un punto de búsqueda por bloques.
  - Usaban esa orden el dibujo en el lienzo (`_on_boundary_drawn`) y Copiar contorno (`_do_copy_boundary`).
- **Otros dos caminos ya nombraban el tipo,** cada uno con su propia copia de la regla, `f"Add {btype.display_name}"`:
  el `boundary_add` del API y *Convertir herramienta en contorno*.
  - Como la ventana y el agente comparten la pila, el mismo objeto se llamaba «Add Block Search Object» en
    `project_history` si lo añadía el agente, y «Add Boundary» si se dibujaba con el ratón.
  - El castellano de los nueve «Add <tipo>» ya existía y lo comprobaba un test
    (`test_an_add_of_every_boundary_type_has_spanish`).
- **Lo que ya estaba bien no se toca:** dibujar un exterior cuando ya hay uno lo sustituye con «Editar contorno»
  (`ReplaceBoundaryCommand`), y así se queda.

## 1. Qué cambia

- **`ogr_core/project/commands.py`:**
  - `add_boundary_step_name(btype)`, que devuelve «Add <tipo>», es la regla única;
  - `AddBoundaryCommand.description` pasa a ser None por defecto, y `__post_init__` le pone el nombre del tipo. Un
    nombre explícito sigue siendo del que lo da.
- **La regla se mueve al núcleo y los demás la preguntan:** `ogr_api/ops/model.py` (`boundary_add`) y *Convertir
  herramienta en contorno* (`main_window.py`) llaman a `add_boundary_step_name`. El lienzo y Copiar contorno la
  reciben de la orden sin cambiar la llamada.
- **`ogr_gui/i18n/__init__.py`:** se retira la entrada «Add Boundary», que ya no usa nadie.
- **`tests/test_window_undo_v1301.py`, cambiado a propósito:** su censo de nombres literales esperaba «Add Boundary»
  en `commands.py`, y ahora espera «Remove Boundary». El test de los nueve tipos con castellano no cambia.
- **`tests/test_add_boundary_step_v1414.py`**, nuevo, con 6 tests.
- El número en los nueve sitios y el contador de los dos README.

## 2. Qué se probó

- **`tests/test_add_boundary_step_v1414.py`,** con el lienzo real (mostrado, sin forzado, eventos de ratón de verdad):
  - cada modo de dibujo sobre el talud de ejemplo deja su paso con el nombre del tipo:
    - contorno de material, nivel freático, línea de desembalse, línea piezométrica, grieta de tracción, capa
      débil y superficie anisótropa;
    - y los cuatro objetos de búsqueda por bloques: ventana, línea, punto y polilínea;
  - deshacer y rehacer devuelven exactamente el proyecto (`to_dict`, D307–D309);
  - el exterior sobre un modelo vacío se llama «Add External Boundary»;
  - el menú Editar lo dice en castellano para un punto de búsqueda por bloques, una capa débil y un contorno de
    material;
  - Copiar contorno nombra el tipo de la copia;
  - la orden se nombra sola por su tipo y acepta un nombre explícito; ni el API ni la ventana conservan su copia
    de la regla;
  - el agente lee los mismos nombres en `project_history`.
- **La discriminación,** con el árbol de 0.1.412 y el test copiado: fallan 5 de 6. El del API es la guarda: ya
  nombraba el tipo.
- **`d349()`** da SIGUE ABIERTO con 0.1.412 («Add Boundary» / «Deshacer «Añadir contorno»» en los tres) y CUBIERTO
  POR TEST con 0.1.414.
- **Los vecinos:** deshacer, historial y órdenes, Block Search, *Convertir herramienta en contorno*, operaciones
  de contorno, deshacer del API, mover contorno, traducciones, castellano, proyecto y el servidor MCP: 296 de 296.
- **La suite entera con `--jobs 4`:** **7031 de 7031, `Failed: 0`**, sin `Leaks` ni `Chunks died`, en 25,5 min. La
  serie no toca: 15 commits desde la última.
- **El banco:**
  - `verificar_cierres.py` entero en la raíz da 126 comprobaciones con 0 bajadas; D353 y D354, registradas ya,
    siguen abiertas, como deben;
  - el del 02 en seco da los mismos veredictos (234 de 234);
  - D349 se cierra: instantánea, retirada, `PAQUETES` podado, cadena tachada, prompts y auditorías con 0 ERROR en la
    raíz y en el 02.
  - Un tropiezo del cierre, corregido antes de la instantánea final: al podar D349 de `PAQUETES` se quedaron
    comentados los cuatro ids que iban en su misma línea (D353, D354, D351, D355).

## 3. Qué falta

- Verlo a mano: el menú Editar tras dibujar cada tipo de contorno.
