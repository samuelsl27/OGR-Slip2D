# OGR Slip2D v0.1.367

**La nota de una superficie del usuario que no da resultado dice el motivo cuando la búsqueda lo sabe
(«no corta dos veces el terreno»), y un Área mínima que el modelo no declara se dice como el valor por
defecto de la búsqueda (D346, cerrada).** Quinta versión de la tanda P8l.

## 0. Lo que se encontró

- **La quinta prueba de la interfaz** (H8) dibujó un círculo de centro (200, 200) y radio 5 sobre el talud
  de ejemplo, muy por encima del terreno. La nota decía: «… no dio ningún resultado … Filtros activos en
  este cálculo que pueden quitarla: Área mínima 1.».
- **La búsqueda sabía el motivo:** `evaluate_circle` cuenta ese círculo en `_count_misses_ground` y anota
  `REFUSED_MISSES_GROUND`. La nota no lo preguntaba, y enumeraba los filtros que *podrían* haberla quitado.
- **«Área mínima 1» no es un ajuste del modelo** (`min_area: null`): es el valor de reserva que la puerta
  del análisis da a toda búsqueda (`_MIN_AREA_FALLBACK`). Por eso la otra nota, «no hay ningún filtro
  activo», **era inalcanzable** desde un análisis: el área mínima siempre llega como número.
- **Un defecto más en el mismo sitio:** `_last_refusal` no se reiniciaba antes de cada círculo del
  usuario, así que podía quedar el motivo que dejó el bucle de la búsqueda. Hasta hoy no se notaba, porque
  nadie leía el motivo; en cuanto la nota lo lee, hay que reiniciarlo.
- **Hallazgo para una ficha nueva, sin corregir (regla 7, a decisión de la propietaria):** un Área mínima
  **0** escrita por el usuario también se sustituye por la de reserva, por el `or` de
  `analysis_runner._search_common`. Es un ajuste que no hace lo que dice. Le correspondería el número
  D368, que quedó libre. La nota lo dice ahora con verdad («valor por defecto de la búsqueda»), pero el
  ajuste sigue sin aplicarse.

## 1. Qué cambia

- **`ogr_slip2d/search.py`**, solo en las superficies del usuario (fuera del bucle de la búsqueda, sin
  coste para ella):
  - `_last_refusal` se reinicia antes de cada círculo;
  - si el motivo es que no corta el terreno, la nota es **`search.user_misses_ground`**: «… No corta dos
    veces el terreno dentro del contorno exterior, así que no hay ninguna masa deslizante que analizar.»;
  - con otro motivo que la búsqueda conozca, la nota es **`search.user_refused`**, que lleva el motivo
    anidado: «… La búsqueda dice por qué: …»;
  - sin motivo, la nota de los filtros de siempre. Si el modelo no declara el área mínima, su fragmento es
    **`search.filter.min_area_default`**: «Área mínima 1 (valor por defecto de la búsqueda, no un ajuste
    de este modelo)».
- **`ogr_slip2d/search_note_messages.py`:** los tres códigos, con su inglés.
- **Castellano:** tres entradas nuevas.
- **No cambia ningún número, ni el inglés de los códigos que ya había.**

## 2. Tests

- **`tests/test_user_surface_note_v1367.py`** (nuevo, 5 casos):
  - el círculo de la ficha da la nota nueva, en inglés y en castellano, sin «Área mínima»;
  - un círculo que la búsqueda sí evalúa, con una masa de unos 0,13 m² (radio 5, 0,1 m dentro de la cara
    del talud), da la nota de los filtros con el área mínima como valor por defecto. Con el área declarada
    por el modelo sale sin la etiqueta;
  - otro motivo conocido (`unsliceable`) se dice con `search.user_refused`, en los dos idiomas;
  - el motivo que dejó el bucle antes de este círculo no se usa.
- **Cambios deliberados en `tests/test_search_notes_v1349.py`:**
  - una lista `_LATER` con las muestras de los tres códigos nuevos. Su inglés es el de 0.1.367, no el de
    0.1.348, porque entonces no existían;
  - su corrida real exigía que la nota del círculo que no toca el terreno empezara por
    `search.user_no_result`. Ahora exige `search.user_misses_ground`, que es más estricto.

**Con el código de 0.1.366 fallan 3 de los 5 nuevos.** Los otros dos son guardas que el código viejo
también cumplía, porque no leía el motivo.

## 3. Verificación

- **Los tests de esta versión:** 16/16 (los 5 nuevos y los 11 de v1349). El primer intento falló por una
  errata mía en las muestras: el prefijo de los motivos es `search.refused_surface.`, no `search.refused.`.
- **Los vecinos:** 203/203 en 15 archivos: superficies del usuario, notas de búsqueda, de método y de
  modelo, el castellano, los mensajes del núcleo, los límites del talud y las notas de 0.1.363.
- **Suite entera:** 6599/6599, `EXIT=0`, 103 min.
- **Banco:**
  - raíz: `verificar_cierres.py` entero, 101 comprobaciones (una más, `d346`), 0 bajadas. D346 queda
    **CUBIERTO POR TEST**: con corridas de verdad del talud de ejemplo, el círculo de la ficha da
    `search.user_misses_ground`, el que roza la cara da `search.filter.min_area_default` y, con el área
    declarada, `search.filter.min_area`;
  - manual 02: `verificar_cierres.py` entero (la versión toca la búsqueda, aunque solo sus notas), 242
    defectos y 0 bajadas;
  - **D346 retirada**, podada de `PAQUETES` y tachada en la cadena de P8;
  - instantáneas `Evaluaciones/0.1.367` (raíz 983 archivos, 02 3284), prompts (39) y auditorías con
    0 ERROR.

## 4. Pendiente

- La tanda sigue con D347 (0.1.368): el segmento recto que sale de (0, 0) en el lienzo.
