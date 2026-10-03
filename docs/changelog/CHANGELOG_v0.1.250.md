# OGR Slip2D v0.1.250

**Help Topics (F1) abre la documentación en línea, en el idioma de la
interfaz.** Hasta 0.1.249 abría una ventana modal con la dirección del
repositorio y una línea sobre el terminal, y la ventana de interpretación
tenía la suya, con otra línea distinta: ninguna de las dos ayudaba. La
documentación vive en la web del proyecto, en inglés y en español, que son
los dos idiomas de esta interfaz.

Primera versión de la tanda que sigue a D226–D232: Help Topics, D85, D251 y
D252, D97 y D128 en 0.1.250–0.1.254, y D131 en el banco de la raíz. Va
primero por decisión de la propietaria (2026-10-03).

## 0. Lo que se encontró

### Lo que había

- **La ventana principal.** `MainWindow.act_help` abría un `QMessageBox`
  modal: «Online docs: https://github.com/samuelsl27/OGR-Slip2D» y que
  *Window → Terminal* abre un REPL. El texto no pasaba por `tr()`.
- **La ventana de interpretación.** Su «Help Topics» abría otra caja con una
  frase sobre el dock de superficies, también en inglés y sin `tr()`.

Dos ayudas distintas, ninguna era la documentación, y una de ellas modal: si
un test la hubiera disparado, se habría quedado bloqueado para siempre.

### Qué dirección, y por qué según el idioma

La web enlaza sus dos índices con `hreflang` (leído en su fuente el
2026-10-03):

| idioma | página |
|---|---|
| inglés (`x-default`) | https://opengeorock.org/docs/index.html |
| español | https://opengeorock.org/es/docs/index.html |

Se pidió la española. La propietaria eligió que F1 siga el idioma de la
interfaz: con la interfaz en español abre la española, y en inglés la
inglesa. Un idioma sin página propia (uno añadido por un complemento) abre la
inglesa, que es la que la web declara `x-default`.

### Por qué esto no es la llamada de red que AGENTS.md prohíbe

El programa no envía ni descarga nada: entrega una dirección pública al
navegador del sistema, y solo cuando el usuario pide ayuda. No se abre nada al
arrancar y *Check for Updates* sigue sin contactar ningún servidor
(`test_check_updates_contacts_nothing` no cambia).

## 1. La interfaz

- **`ogr_gui/documentation.py`, módulo nuevo:**
  - `DOCS_URLS` guarda las dos direcciones en un solo sitio;
  - `documentation_url()` lee `i18n.current_language()`;
  - `open_documentation(window)` las abre.
- **El abridor** es una función de módulo (`_open_url`, sobre
  `QDesktopServices.openUrl`) que se busca al llamar. Los tests la sustituyen,
  así que ninguna corrida de tests abre un navegador.
- **La barra de estado** dice «Abriendo la documentación en el navegador:
  <url>». Si no hay navegador, o si el sistema rechaza la dirección, dice «No
  se pudo abrir el navegador; la documentación está en <url>», para que se
  pueda escribir a mano. Nunca es modal.
- **Las dos «Help Topics»** (F1 en la principal y la de interpretación) pasan
  por esa función, y las dos cajas viejas desaparecen.
- **Textos con `tr()`** y su entrada en español. El presupuesto de mensajes
  sin traducir (64, fijado al recuento real) no se mueve: la caja vieja ya
  llevaba el título con `tr()` y su patrón no la contaba.
- **`docs/quickstart.md`:** la fila de F1 dice que abre la documentación en
  línea, en el idioma de la interfaz.

## 2. Tests

**`tests/test_help_topics_v1250.py`**, 11 casos:
- las dos direcciones son las de la web, en una sola tabla, y cada idioma de
  la interfaz tiene la suya;
- un idioma sin página cae en la inglesa;
- F1 está en el menú Help;
- con la interfaz en español abre la española, y en inglés la inglesa;
- sin navegador, o con un abridor que lanza, la barra de estado da la
  dirección y la ventana sigue viva;
- el manejador no abre nada modal;
- la ventana de interpretación usa la misma puerta y la tiene en su menú
  Help.

El idioma y el abridor se restauran en un `finally` (regla 5).

**Discriminación** contra `git archive` 3031083 (0.1.249), con el runner de
ese árbol: **10 de 11 fallan**.
- Uno falla por comportamiento: el manejador viejo abre un modal.
- Nueve fallan por símbolo.
- Pasa, a propósito, el que comprueba que F1 está en el menú Help, porque ya
  lo estaba.

**Una trampa de medida que salió aquí y que vale para el resto de la tanda.**
El primer intento de discriminación se colgó, y su salida quedó vacía. El
`_EditableFinder` de la instalación editable va detrás de `PathFinder` en
`sys.meta_path` y suministra, desde el árbol de trabajo, los módulos que el
árbol viejo no tiene. El `ogr_gui.documentation` nuevo se importó dentro del
árbol de 0.1.249, el primer caso salió en verde y el segundo disparó la caja
modal del `main_window` viejo.

Los símbolos nuevos dentro de módulos que ya existían fallan bien, y por eso
no se había visto antes. La discriminación se corrió con un envoltorio que
quita ese buscador de `sys.meta_path`, y con `python -u`.

## 3. Verificación

- **Selección** de i18n, menús, licencias, alcanzabilidad e interpretación,
  más el test nuevo: 92 de 92.
- **Suite entera:** 5524 de 5524 (las 5513 de 0.1.249 más los 11 casos
  nuevos), en paralelo con medidas de la versión siguiente.
- **Discriminación:** 10 de 11 contra 0.1.249.
- **Banco:** nada. No hay ficha y no se mueve ningún número.

**Qué falta por probar:**
- **F1 en la aplicación real**, con el navegador del sistema: los tests
  sustituyen el abridor y nadie ha visto todavía la página abrirse en
  pantalla.
- **La página española** depende de que la web publique
  `/es/docs/index.html`. Está en su fuente; que esté desplegada no se ha
  comprobado desde aquí, a propósito: el programa no contacta nada.
