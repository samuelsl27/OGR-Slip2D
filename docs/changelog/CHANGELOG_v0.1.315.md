# OGR Slip2D v0.1.315

**En castellano y con cualquiera de los dos temas, ningún botón es más estrecho
que su texto y todo diálogo cabe en una pantalla de 1366 × 768 (D293).** Tercera
versión de la tanda P8g.

## 0. Lo que se encontró

Medido sin pantalla, en castellano, con estilo Fusion y antes de tocar nada.

- **La causa de los botones cortados era la hoja del tema.** Daba a todo
  `QPushButton` un `min-width: 70px`, y en Qt un mínimo de hoja de estilo
  SUSTITUYE al que pide el texto. Un layout sin sitio comprimía los botones
  por debajo de su texto.
  - **El transitorio** se abría a 520 px (`resize(520, 480)`) y cortaba sus
    cuatro botones: «Capturar condiciones actuales» recibía 144 de sus 279 px.
    Sin tema, el mismo diálogo pedía 805 px y no cortaba nada.
- **El hidráulico tenía dos causas propias:**
  - su `QScrollArea` recibía unos 190 px para 530–554 px de contenido, y por
    eso salía la barra horizontal;
  - su ancho mínimo lo fijaba una nota en cursiva de la columna izquierda,
    «Names and colours are defined in…»: 486 px, porque en HTML el salto de
    línea es solo un espacio y no tenía ajuste de línea. Además no estaba
    traducida y citaba un menú que no existe («Define Material Properties»;
    el real es *Propiedades > Definir materiales*).
- **El arreglo aprobado no bastaba (regla 6, reportado antes de cambiarlo).**
  Era pasar el `min-width` solo a los botones de las cajas de diálogo. El censo
  de diálogos lo refutó: con el catálogo de Qt en castellano, «Restaurar los
  valores predeterminados» necesita 339 px y recibía 220 en *Display Options* y
  226 en *Snap*, ya al abrir. Dentro de las cajas, el `min-width` seguía
  sustituyendo al mínimo del texto.
  - **Decisión de la propietaria (2026-10-15):** un suelo por código y
    automático.
- **El censo encontró además:**
  - *Define Support* tenía su columna de la lista a 220 px, por debajo de su
    fila de tres botones en castellano («+ Añadir», «Duplicar», «− Quitar»);
  - *Add Grid* tenía una introducción sin ajuste de línea de 1616 px, así que
    su mínimo era más ancho que la pantalla;
  - el panel de notas del análisis cortaba «Copiar todo», que se arregla con
    el cambio de la hoja.
- **Ningún test medía anchos.** El de D282 solo mide la altura, y en inglés, y
  los tests no aplicaban el tema, que es lo que cambia los anchos.

## 1. Qué cambia

- **Las dos hojas de estilo** ya no ponen ningún `min-width` a los botones.
- **`ogr_gui/button_floor.py`** (nuevo, con el patrón de `wheel_guard`) es un
  filtro de la aplicación que instala `apply_theme`.
  - Cuando se pule un botón de una `QDialogButtonBox`, le da un mínimo de
    max(100 px, su texto). 100 px es lo que daba la regla vieja (70 + 14 de
    relleno por lado + borde).
  - Aceptar y Cancelar se ven como antes, y ningún texto se corta.
  - **Solo actúa mientras la hoja de la aplicación es la de uno de nuestros
    temas.** Un test que devuelve la hoja deja el filtro instalado pero inerte
    (regla 5).
- **`ogr_gui/dialog_size.py`** (nuevo):
  - `open_at_content_size(dialog, at_least)` abre un diálogo al tamaño que pide
    su contenido, sin bajar de un mínimo y sin pasar de la pantalla;
  - `VerticalScrollArea` es un área de desplazamiento tan ancha como su
    contenido más la barra vertical, así que solo se desplaza en vertical.
- **El transitorio:** sus botones van en dos filas (añadir/eliminar etapa; las
  dos capturas) y se abre a su tamaño de contenido.
- **El hidráulico:**
  - `VerticalScrollArea`, así que no hay barra horizontal;
  - agarre para agrandarlo;
  - se abre a su tamaño de contenido;
  - la nota de la izquierda con ajuste de línea, traducida y con el nombre real
    del menú.
- ***Define Support:*** la columna de la lista sigue estrecha, pero nunca por
  debajo de su fila de botones.
- ***Add Grid:*** la introducción con ajuste de línea. Su traducción es de D300.

## 2. Tests

`tests/test_dialogs_fit_v1315.py`, 5 casos. Todos en castellano (con el
catálogo de Qt en castellano para los botones estándar), con el tema claro y el
oscuro, y restaurando la hoja, la paleta, el idioma y el traductor.

- **El censo** cubre 44 diálogos de `ogr_gui/dialogs`: los que se abren con el
  proyecto y los que necesitan otros argumentos, construidos a propósito.
  - A su tamaño MÍNIMO, ningún botón con texto se ve más estrecho que su texto.
  - Ese mínimo cabe en 1366 × 728 (768 menos una barra de tareas).
- **El transitorio y el hidráulico** se abren sin botones cortados.
- **El hidráulico** no tiene barra horizontal, ni al abrir ni a su mínimo.
- **Control:** Aceptar y Cancelar siguen en 100 px.
- **El filtro no hace nada sin tema.**

**Con el código de 0.1.314 fallan 4 de los 5:**
- el censo encuentra *Add Grid* (1638 px) y botones cortados en *Define
  Support*, *Display Options* y el panel de notas;
- el hidráulico enseña la barra horizontal;
- el transitorio corta sus cuatro botones;
- el filtro no existe.

El control de Aceptar y Cancelar pasa en los dos árboles. Se corrió sobre una
copia del árbol de 0.1.314 sin el buscador editable.

## 3. Verificación

- **Suite entera:** 6100/6100, código de salida 0, a la primera (59 min).
- **Banco:** `d293()` en el `verificar_cierres.py` de la raíz: **CUBIERTO POR
  TEST**. Ciclo de cierre:
  - `verificar_cierres.py` entero: 57 comprobaciones, 0 bajadas;
  - instantánea `Evaluaciones/0.1.315` antes y después (`--forzar`);
  - `retirar_cerrados.py --escribir D293`;
  - poda de la lista P8 y D293 tachada en la fila P8;
  - `generar_prompts.py`: 36 prompts y las mismas 19 FALTA;
  - `auditoria_invariantes.py` en la raíz y en el 02, con 0 ERROR.
- **Una bajada en el banco que no era del código.** La primera corrida dejó
  D282 en SIGUE ABIERTO: su `d282()` buscaba el texto `QScrollArea()` en el
  diálogo, que ahora es `VerticalScrollArea()`, una subclase. La comprobación
  acepta ahora las dos. Lo que D282 protege (los parámetros en un área con
  desplazamiento, con avisos y botones fuera) sigue igual.
- **Los tests vecinos**, antes de la suite: 356/356. Son agua subterránea,
  transitorio, hidráulico, i18n, temas, menús desactivados, idioma, soportes,
  rejillas, ajuste, visualización, traducciones de Qt y el test nuevo.
- **Ningún número cambia:** es presentación.

## 4. Pendiente

- **A mano:** los dos diálogos en castellano a la resolución real y escalada.
  Los anchos medidos sin pantalla usan la fuente de Fusion, y en Windows la
  fuente es otra.
- **Fuera de alcance:** la traducción de la introducción de *Add Grid* (D300).
