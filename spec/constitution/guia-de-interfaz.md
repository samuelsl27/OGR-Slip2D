# Guía de interfaz de OGR Slip2D

> **Propuesta (2026-11-24), pendiente de aprobación por la propietaria.** Parte de la constitución:
> se consulta antes de diseñar, cambiar o revisar cualquier ventana, diálogo, menú, acción, leyenda o
> mensaje de este programa, y cada prompt de interfaz se cierra con su lista (al final). No sustituye
> a `AGENTS.md`: concreta para la interfaz sus reglas 2, 3, 5, 6 y 7.

## Cómo se usa

1. **Mandan las reglas del proyecto** (`AGENTS.md`). Si una buena práctica choca con una regla, gana
   la regla; los choques ya vistos están en «Cuando chocan».
2. **La base común de la suite no se repite aquí.** Vive en OGR-GUI:
   `../../GUI/OGR-GUI/spec/constitution/referencias-de-diseno.md` (aprobada el 2026-11-24). Allí
   están las ocho fuentes, lo que se toma y lo que no de cada una, los principios **D-1 a D-14**, «Lo
   que no se hace» y la lista de comprobación de una pieza. Esta guía los **cita por su número** y
   dice cómo se aplican en Slip2D; no los copia, porque una regla en dos sitios se queda obsoleta en
   uno de ellos.
3. **Slip2D es la base estética de la suite**, no un programa más que se adapta a ella: OGR-GUI nació
   de su código (v0.1.486) y FEM2D toma su aspecto. Por eso el primer deber de esta guía es **no
   perder la identidad** (abajo). Las fuentes sirven para mejorarla, no para cambiarla por gusto.
4. Si una spec toca la interfaz, su `spec.md` dice qué principios aplica (`D-4`, `D-5`…) y su
   `tasks.md` cierra con la lista del final, marcada o con «no aplica: …».

### Las fuentes

| Fuente | Enlace |
|---|---|
| Laws of UX (Jon Yablonski) | <https://lawsofux.com/articles/> |
| Fluent 2 (Microsoft) | <https://fluent2.microsoft.design/> |
| Checklist Design | <https://www.checklist.design/> |
| Autodesk HIG (Weave) | <https://github.com/Autodesk/hig> |
| Humane by Design | <https://humanebydesign.com/> |
| Growth.Design, psicología | <https://growth.design/psychology> |
| GoodUI | <https://goodui.org/> |
| Deceptive Patterns | <https://deceptive.design/> |

Lo que se toma y lo que no de cada una, en las referencias de OGR-GUI. **Se citan y se enlazan; su
texto no se copia** (Laws of UX es CC BY-NC-ND 4.0; Growth.Design se reserva los derechos).

### Slip2D y `ogr_ui`, hoy

Slip2D **todavía no usa** `ogr_ui`: sus piezas siguen en `ogr_gui/` y la adopción la decidirá su
propia spec. Pero `ogr_ui` 0.1.0 es una copia de esas piezas, así que, hasta adoptarla:

- Un cambio en Slip2D a una pieza que tiene su gemela en `ogr_ui` (`themes`, `button_floor`,
  `dialog_size`, `wheel_guard`, `disabled_reasons`, `widgets/status_bar`, `widgets/legend`,
  `contours`, `background`, `dialogs/progress_dialog`, `user_prefs`, `qt_catalog`, `file_folders`,
  `xy_chart`, `gc_guard`, `canvas/snap_engine`, `dialogs/snap_dialog`, `resources/icons`, `i18n`) se
  apunta en el changelog con la etiqueta **«gemela en ogr_ui»** y se avisa a la propietaria para que
  lo lleve a la sesión de OGR-GUI. Si no, las dos copias acaban diciendo cosas distintas.
- Una mejora que pida una fuente y afecte a esas piezas (un color, un umbral de espera, un
  espaciado) **no se hace primero en Slip2D**: se pide a OGR-GUI, como el núcleo se pide a OGR-Core.

## La identidad de Slip2D: lo que no se pierde

Cada punto salió de una decisión con su versión; cambiar uno es una decisión de la propietaria, con su
spec, no una mejora de paso.

| Rasgo | Cómo es | Por qué |
|---|---|---|
| **Dos ventanas** | El modelo (`MainWindow`) y la interpretación (`InterpretWindow`, y la del agua subterránea), cada una con su barra de menús | Es el flujo que el ingeniero ya conoce: se dibuja, se calcula y se interpreta |
| **Menús en el orden del trabajo** | File, Edit, View, Analysis, Boundaries, Loading, Support, Surfaces, Properties, Groundwater, Statistics, Tools, Window, Help | Ley de Jakob (D-1): el orden de los programas del oficio. Son 14 a propósito; el tope de 9 de OGR Data no rige aquí |
| **Atajos** | Ctrl+N/O/S, Ctrl+Mayús+S, Ctrl+P, Ctrl+Q, Ctrl+Z/Y; **Ctrl+T** calcular, **F2** ver todo, **F7** rejilla, **Ctrl+D** opciones de visualización, **Ctrl+J** ajustes del proyecto, **Ctrl+I** visor de información, **F1** ayuda | Los mismos para lo mismo en toda la suite (D-1); uno nuevo no pisa a ninguno de estos |
| **Mayúsculas** | En inglés, tipo título («Define Hydraulic Properties...»); en español, tipo oración; «...» sin espacio en lo que abre un diálogo | Decidido en OGR-GUI frente a Fluent 2: cambiarlo rompe la coherencia y todas las claves de `tr()` |
| **Terminología** | La geotécnica castellana estándar: dovela, nivel freático, grieta de tracción, coeficiente parcial, superficie de deslizamiento | Regla 2; D-6. La notación del oficio (φ′, c′, kPa, kN/m³), nunca una clave interna |
| **Leyenda del factor de seguridad** | «Rainbow (24 bands)» por defecto: 0–6 en bandas de 0,25, rojo = inseguro, la última «6.000+», pintada con la misma función que el dibujo | v0.1.49, v0.1.82: es la leyenda que el ingeniero lee de un vistazo. «Accessible» (Okabe-Ito) y «Greyscale» están siempre a un clic (D-10, D-12) |
| **Barra de estado** | Coordenadas, entrada X,Y tolerante, palancas DATA TIPS / SNAP / GRID / ORTHO / OSNAP que se pulsan sobre la palabra, texto largo cortado con «…» y entero en su *tooltip* | v0.1.328, v0.1.418 (D325, D355) |
| **Enganche en píxeles** | Tolerancias en píxeles de pantalla convertidas con el zoom, y el diálogo lo dice | v0.1.3, v0.1.51; D-11 |
| **Deshabilitar con su porqué** | Una acción que no aplica sale gris, con un *tooltip* y un mensaje en la barra de estado que dicen qué hacer antes; nunca se oculta | v0.1.288–0.1.328 (D289, D324); D-4. Doce acciones invisibles en v0.1.42 son el porqué de la regla 3 |
| **Notas del análisis enteras** | Todo lo que dijo el cálculo, en un panel no modal, no solo la primera frase en la barra de estado | `analysis_notes_panel`: la interfaz decía menos que la línea de órdenes |
| **Cálculo cancelable** | En segundo plano, con progreso y un Cancelar que para de verdad; el diálogo se queda hasta que el trabajo vuelve | v0.1.365–0.1.366 (D348, D362); D-5 |
| **Temas** | Claro (el de la plataforma más una hoja) y oscuro (también la paleta); colores con nombre de papel (`theme_color`) | v0.1.316 (D301); D-2 |
| **Iconos** | Vectoriales (qtawesome: Font Awesome 6 y Material Design Icons), por **clave semántica** en un solo catálogo (`resources/icons.py`) | Una clave, un significado en toda la suite (D-1) |
| **Gráficos informativos** | No modales | v0.1.308 (D311); además, un modal cuelga la suite sin pantalla |

## Los principios, aplicados a Slip2D

Solo lo que este programa añade a D-n. Lo que D-n ya dice, se lee allí.

- **D-1, lo conocido primero.** Una acción nueva va al menú de su paso del trabajo, no a uno nuevo; si
  hace lo mismo que otra de la suite, lleva su nombre, su icono y su atajo. Lo que se haga distinto
  de los programas del oficio, la spec dice por qué (sin nombrarlos: ver `AGENTS.md`, «Documentación
  de referencia»).
- **D-2, una sola apariencia.** Ningún color literal nuevo en un widget: se pide un papel en
  `ROLE_COLORS`, con valor en los dos temas. Los colores de cada tipo de objeto del lienzo
  (contorno, material, agua, cargas, soportes, superficies, foco) son los mismos en el lienzo, la
  leyenda, la ayuda y el informe.
- **D-3, agrupar con el espacio.** Un diálogo de propiedades agrupa por lo que significa (identidad →
  resistencia → peso → agua), en bloques con título. Márgenes en múltiplos de 4 px mientras no haya
  rampa con nombre.
- **D-4, sin esconder lo que decide.** Lo que mueve el factor de seguridad (método, número de
  dovelas, tolerancia, filtro m-alpha, coeficientes parciales) puede ir plegado, pero se ve con el
  resultado: en las notas del análisis, el visor de información y el informe. Una opción que no mueve
  el número no se añade (regla 7).
- **D-5, espera honesta.** Una búsqueda dice qué hace (búsqueda, superficie, método) y cuánto lleva;
  un cálculo cancelado no deja resultados que parezcan válidos. Los umbrales de Fluent 2 son de
  OGR-GUI: hoy el diálogo de progreso aparece al arrancar (ver «Deuda conocida»).
- **D-6, el texto.** `tr()` y su español (regla 2). El botón dice qué pasa («Calcular», «Descartar
  cambios»). Un número de resultado lleva su unidad y su método («F = 1,402 (Spencer)»).
- **D-7, entradas tolerantes.** Coma o punto, espacios, `12.5, 3.2` o `12.5 3.2`; lo ambiguo se
  rechaza en el campo y dice qué falta. Lo que se acepta se enseña como se entendió, con su unidad.
  La rueda no cambia un campo sin foco (`wheel_guard`).
- **D-8, deshacer antes que confirmar.** Toda edición del modelo es un paso de deshacer, desde la
  interfaz y desde `ogr_api`. Se pregunta solo lo irreversible: sobrescribir, cerrar sin guardar,
  descartar resultados. Ninguna confirmación en código que un test ejecute.
- **D-9, destacar solo lo que importa.** Un resultado obsoleto (el modelo cambió después) se marca de
  forma inconfundible; la superficie crítica destaca porque es la única; los avisos usan `warning` y
  `error`, nunca como adorno.
- **D-10, accesible.** Todo diálogo cabe en 1366×728 en español y en los dos temas
  (`test_dialogs_fit_v1315`); todo se hace con el teclado; Esc cierra sin aplicar. Contraste: ver
  «Deuda conocida».
- **D-11, objetivos a la medida.** Lo frecuente, en la barra de herramientas y en el menú contextual
  del lienzo; objetivos de al menos 24 px útiles.
- **D-12, leyendas que dicen la verdad.** Magnitud, unidad, rango y, si es un resultado, método y
  estado (vigente u obsoleto). Dos figuras que se comparan, con el mismo rango, puesto a propósito.
- **D-13, estado vacío.** La ventana de interpretación sin resultados dice cómo obtenerlos («Sin
  resultados: Analysis → Compute»), y una búsqueda sin superficies válidas dice por qué y qué
  ampliar; no es lo mismo que un error al cargar.
- **D-14, la persona decide.** El programa calcula; quien firma es el ingeniero (`mission.md`). Nada
  «recomienda» un factor; sin telemetría ni red (*Check for Updates* no contacta con nada); un aviso
  se dice una vez.

## Cuando chocan

Los choques generales están en OGR-GUI. Estos son los de Slip2D:

| Choque | Se resuelve así |
|---|---|
| Paleta de luminosidad monótona (D-10, FEM2D) frente a «Rainbow (24 bands)» por defecto | Se queda Rainbow por defecto (identidad, v0.1.82); «Accessible» y «Greyscale» a un clic, y la leyenda lleva siempre sus números, así que el color nunca va solo |
| Pocos menús (Hick; tope de 9 de OGR Data) frente a los 14 de Slip2D | Se quedan los 14: siguen el trabajo. Lo que crece va a submenús de su paso; ningún menú de una sola entrada nuevo |
| Fluent 2 (tipo oración, «…» con espacio) frente a las etiquetas de Slip2D | Como Slip2D (decisión de OGR-GUI) |
| Paridad con los programas del oficio frente a una fuente | Se propone la mejora en la spec; sin OK de la propietaria, gana la paridad, que es lo que el ingeniero ya sabe usar |
| Mejorar una pieza que tiene gemela en `ogr_ui` | Se pide a OGR-GUI; en Slip2D, solo lo que corrige un fallo, con la etiqueta «gemela en ogr_ui» |

## Deuda conocida

Lo que esta guía pide y Slip2D no cumple hoy. **Se reporta, no se corrige de paso** (regla 6): cada
punto necesita su ficha, y los marcados «OGR-GUI» se deciden allí primero.

| Qué | Dónde | Choca con |
|---|---|---|
| «Orthogonal window» del diálogo de enganche: `SnapSettings.ortho_snap_angle_deg` se edita y se guarda, pero el motor de enganche no lo lee | `canvas/snap_engine.py`, `dialogs/snap_dialog.py` | Regla 7; D-4. Igual en OGR-GUI |
| «Fit to results» habilitado cuando no hace nada (entre dos campos automáticos) | `dialogs/contour_options_dialog.py` | D-4, D-9. OGR-GUI |
| Tres papeles del tema claro por debajo de 4,5:1 (`warning` 4,37, `accent` 4,48, `toggle_off` 4,08); el test exige 4,0 | `themes`, `test_dark_theme_v1316` | D-10. OGR-GUI |
| El diálogo de progreso aparece al arrancar, aunque el cálculo dure medio segundo | `background` | D-5. OGR-GUI |
| Sin rampa de espaciado ni escala tipográfica con nombre: cada diálogo escribe sus márgenes | todos los diálogos | D-2, D-3. OGR-GUI |
| Sin pieza de estado vacío: cada ventana lo escribe a mano, o no lo escribe | ventanas de interpretación | D-13. OGR-GUI |

## Lista de comprobación

Al cerrar una tarea de interfaz, la lista de OGR-GUI («Lista de comprobación de una pieza») y,
además, esta. Cada punto se marca o se dice «no aplica: …».

**Identidad**
- [ ] Nada de la tabla «La identidad de Slip2D» cambia sin una decisión de la propietaria.
- [ ] Ningún nombre, marca ni texto de un programa comercial en el código ni en la interfaz.

**Acción**
- [ ] En un menú de su paso del trabajo (regla 3, `test_menu_reachability_v142`), registrada con
      `_mk`, con `tr()` y su español (regla 2, `test_i18n_coverage_v141`).
- [ ] Atajo solo si es frecuente, y sin pisar los de la tabla de identidad.
- [ ] Deshabilitada con su porqué cuando no aplica (`disabled_reasons`), nunca oculta.

**Diálogo**
- [ ] Valores por defecto leídos del modelo, no literales; los que mueven el número, visibles con el
      resultado.
- [ ] Cada control con su test que demuestra que mueve el número (regla 7).
- [ ] Cabe en 1366×728 en español y en los dos temas (`test_dialogs_fit_v1315`).
- [ ] Sin `exec()` ni `QMessageBox` en lo que ejecuta un test; los gráficos informativos, no modales.
- [ ] Probado sin pantalla y sin dejar estado (regla 5): idioma, tema y unidades restaurados con
      `try/finally`.

**Resultado y lienzo**
- [ ] Leyenda con magnitud, unidad, rango, método y estado; lo obsoleto, inconfundible.
- [ ] Colores de objeto los de siempre, en los dos temas; tolerancias en píxeles.

**Proceso largo**
- [ ] En segundo plano, dice qué hace, Cancelar para de verdad, nada publicado si se cancela
      (`test_cancel_v1366`).

**Mensaje**
- [ ] Dice qué pasó, en qué objeto y cómo seguir; se dice una vez; un estado vacío enseña el
      siguiente paso.

**Suite**
- [ ] Si toca una pieza con gemela en `ogr_ui`: anotado «gemela en ogr_ui» en el changelog y avisada
      la propietaria.
- [ ] Ninguno de los patrones de «Lo que no se hace» de OGR-GUI.

---

© 2026 Samuel Sáez López — UPCT — AGPL-3.0-or-later
