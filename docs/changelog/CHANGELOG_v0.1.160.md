# OGR Slip2D v0.1.160

**El encargo de P-D126 pedía sacar del código el nombre del producto de
referencia y ponerle un test. Las dos cosas están hechas, y el inventario
que había que levantar para hacerlo desmiente tres afirmaciones de la propia
ficha: no eran tres tests sino veinticinco, su patrón no veía dos familias
enteras de apariciones, y la mitad de la regla que nadie había mirado —«ni
copiar su texto»— estaba incumplida en nueve pasajes entrecomillados.**

Cierra **D126**. **Cero dígitos movidos**: no se ha tocado una sola línea
ejecutable de cálculo, ninguna constante, ningún valor por defecto, ningún
assert ni ninguna tolerancia. Lo que cambia es prosa, tres cadenas de
interfaz y tres identificadores privados.

---

## 1. Lo que decía la ficha y lo que había

`AGENTS.md` («Documentación de referencia») permite **leer** la documentación
comercial de `docs/reference/` para entender qué hace una función y cómo debe
comportarse la interfaz, y prohíbe que **el código contenga ninguna
referencia a esos productos ni a sus marcas, ni copie su texto**; las
fórmulas se citan por su fuente científica original.

Medido con 0.1.159 el 2026-09-11, con el patrón que la ficha da:

| Paquete | Líneas | Archivos |
|---|---|---|
| `ogr_core` | 40 | 9 |
| `ogr_slip2d` | 28 | 6 |
| `ogr_fem2d` | 0 | 0 |
| `ogr_gui` | 50 | 15 |
| `ogr_cli` | 0 | 0 |
| `tests` | 41 | **25** |
| **Total** | **159** | **55** |

Los tres primeros números son los que la ficha publica. El cuarto no: la
ficha dice «los tres tests que nombran el producto (`test_block_search_v117`,
`test_convergence_tolerance_v198`, `test_grid_radius_rule_v188`)». Son
**veinticinco archivos y 41 líneas**, y además **el tercero de esos tres no
aparece en la lista**, porque lo que contiene es `Slide2d_Ej_1_General.s01`,
que su propio patrón no casa. Como el criterio de cierre grepea `tests/`
también, el alcance real era 159/55 y no 118/30.

## 2. El patrón de la ficha tenía dos agujeros, y uno se vio al trabajar

`\bSlide2?\b` **no casa con `Slide2d_Ej_1_General`**: entre la `2` y la `d`
no hay frontera de palabra. Son 9 líneas en 5 tests. Eso se sabía antes de
empezar y es lo que decidió el alcance (§5).

Lo que no se sabía es que **tampoco casa con `Slide3`**, por la misma razón
—entre la `e` y el `3` no hay frontera—, y
`ogr_core/support/support.py:6` decía exactamente «the Slide2/Slide3
documentation». Una línea que el criterio de cierre habría dado por limpia.

Y hay una tercera familia que ningún patrón de marcas puede ver: **los
nombres de archivo de su sistema de ayuda**. `Water_Parameters.htm`,
`Add_Material_Boundary.htm`, `Define_Tension_Crack.htm`, `Strenght_Type.pdf`
y `Surface_Options.pdf` aparecían en **10 líneas de 8 archivos**, y **6 de
esas 10 no llevaban la marca en la misma línea**, de modo que eran invisibles
al grep de la ficha. Citar el nombre de un archivo de su ayuda es una
referencia a su documentación igual que la marca.

El test usa por eso `\bSlide[0-9]?\b` —que sí coge `Slide`, `Slide2` y
`Slide3`, y sigue sin coger `Slide2d_Ej_1`— más los cinco nombres de ayuda.
Con ese patrón el árbol de 0.1.159 tenía **165 líneas en 57 archivos**.

## 3. La mitad de la regla que nadie había mirado: el texto copiado

La ficha clasifica las apariciones en tres (convención, comparación numérica,
rótulo) y no contempla ninguna cuarta. Había **nueve pasajes que reproducen
entre comillas frases de su documentación**, que es la otra prohibición
literal de la regla:

- `ogr_core/support/support.py:454` — la carga constante del End Anchored;
- `ogr_core/support/support.py:821` — el Soil Nail como Grouted Tieback con
  bond 100 %;
- `ogr_core/geometry/regions.py:256` — la frase de Automatic Boundary
  Intersection;
- `ogr_slip2d/methods/bishop.py:371` — el brazo del momento de la normal;
- `ogr_slip2d/search.py:2064` — la definición de «slope surface»;
- y cuatro más en `tests/`: `test_interpret_pinned_queries_v186.py:27`,
  `test_interpret_slice_data_v187.py:31`, `test_region_welding_v117.py:17`
  y `test_modified_swedish_v198.py:81`.

A éstos no les basta con quitarles la marca: están **parafraseados**,
conservando exacta la afirmación técnica. La de Bishop es la que más importa,
porque es la que justifica por qué el método no usa la forma `Σ W sinα` sobre
una poligonal, y esa justificación sigue entera.

## 4. Qué se ha escrito en su lugar

Cada mención se ha clasificado y sustituido por una de cuatro cosas:

- **la fuente científica**, cuando la convención tiene una;
- **«the reference»**, **«the reference program»**, **«the reference
  states»**, que es el vocabulario neutro que este repositorio **ya usaba en
  más de 120 sitios** —`ogr_gui/contours.py:237` y
  `ogr_core/project/settings.py:749` son el modelo—, de modo que no se ha
  inventado una manera de hablar: se ha terminado de aplicar la que había;
- **el número y el problema**, en las comparaciones históricas
  (`ogr_slip2d/methods/janbu.py:400`, «gave +2.9 % vs Slide» → «against the
  reference»);
- **prosa propia** en los nueve pasajes de §3.

Dos citas bibliográficas se recortan sin perder la referencia: Su (2009)
conserva autor, año, título y «University of Waterloo» y pierde el coeditor
comercial, y la nota de Corps of Engineers #2 pasa a apoyarse en **«Krahn
(2004)»**, que es autor-año localizable, en lugar de en el nombre de su
programa. **XSTABL se queda** en `ogr_slip2d/search.py`: es un programa
académico citado como origen del algoritmo de Path Search, no está en
`docs/reference/` y no es la marca que la regla persigue.

## 5. Lo que se ha decidido NO limpiar, y por qué

Los tests de validación nombran los archivos de los que leyeron sus números
—`Slide2d_Ej_1_General.s01`, `Slide2d_Ej_2_General.htm`, `.slim`—. **Se
quedan.** Son nombres de archivo en `referencias/`, el banco de verificación,
que la propia ficha autoriza a nombrar al programa cuyo manual reproduce, y
son la procedencia de un número validado: borrarlos dejaría un factor de
seguridad sin nada con que comprobarlo, que es apagar la regla 1 para
satisfacer ésta. El test fija ese límite **por los dos lados**:
`test_the_pattern_leaves_the_bank_provenance_alone` comprueba que el patrón
no los caza, y `test_the_provenance_is_still_written_in_the_validation_tests`
comprueba que siguen escritos, para que una limpieza posterior no se los
lleve por celo.

Por la misma razón **no se renombran** `tests/test_slide_validation_ej1.py`
ni `tests/test_slide_validation_ej2_v184.py` (ni su clase
`TestSlideValidationEj1`): `AGENTS.md` los nombra por ese glob en su lista de
«No hagas» y el banco los cita igual en una veintena de sitios de sus
`PROMPTS_RESOLUCION.md`. De esos dos archivos se ha tocado **sólo prosa**:
cuatro líneas de docstring, ni un número ni un assert.

Sí se renombran tres identificadores que ningún patrón de marcas veía, porque
van en minúscula o pegados:
`MainWindow._expand_shrink_slide_style` → `_expand_shrink_draw_mode`,
`TestSlidePDFAlignment` → `TestReferenceDialogAlignment` y
`TestPowerCurveSlideForm` → `TestPowerCurveReferenceForm`. Los tres son
privados o locales y no los cita nadie fuera de su archivo, comprobado
también contra el banco.

## 6. La paleta no era un comentario

`"Slide rainbow"` era la **clave** de una paleta en `ogr_gui/contours.py`
—`DEFAULT_PALETTE` y `DISCRETE_PALETTES` incluidos— y a la vez el **rótulo**
que el combo de Contour Options enseñaba al usuario. Antes de tocarla se
comprobaron las dos cosas que podían hacerla intocable, y ninguna se cumple:
`ContourSettings.to_dict`/`from_dict` sólo se usan para copiar en memoria
dentro del propio diálogo, **no llegan a ningún `.ogr`**, y la cadena no
aparece en ningún archivo del repositorio ni del banco. Pasa a
**`"Rainbow (24 bands)"`**. Los 24 colores medidos y el comentario que
explica que son una medición y no una fórmula **no se tocan**.

Y al cambiar un rótulo aparece la regla 2, que ese combo incumplía desde
siempre: los siete nombres de paleta se pintaban **sin traducir**, mientras
el combo de modo dos líneas más arriba ya hacía `addItem(tr(label), mode)`.
Ahora el de paleta hace lo mismo —`addItem(tr(name), name)`, con la clave
intacta como dato, así que `findData` y `currentData` siguen igual— y el
diccionario español gana seis entradas. **«Viridis» se queda a propósito sin
entrada**: es nombre propio, como «Monte Carlo» o «Ito & Matsui», y una
traducción idéntica a su clave es justamente lo que
`test_no_lazy_identity_translations` llama entrada olvidada.

Las otras dos cadenas visibles que nombraban el producto —el tooltip del
coeficiente de temperatura en `grid_dialogs.py` y la opción «Draw polyline»
del diálogo de Expand/Shrink— pasan por `tr()` con su castellano. En la lista
de Expand/Shrink se envuelven **las dos** opciones y no sólo la que cambiaba:
la comparación es contra `options[1]` y no contra el literal, así que sigue
funcionando, y media lista traducida habría sido peor que el defecto que se
corrige.

## 7. El test, y por qué se salta un archivo

`tests/test_no_vendor_names_v1160.py` recorre los cinco paquetes y `tests/`
con el patrón de §2 y falla ante cualquier aparición, listando archivo y
línea. **La lista de excepciones está vacía**, y hay un test que comprueba
que sigue vacía, para que añadir una cueste una decisión visible en un diff:
así es como se acumularon las 159.

Y **no se salta ningún archivo, tampoco a sí mismo**. La primera versión sí
lo hacía —por el mismo recurso, y con la misma razón escrita al lado, que
`test_license_v143.py` usa desde v0.1.43 para buscar identificadores GPL
obsoletos— y eso dejaba en pie unas cuantas líneas que el grep del criterio de cierre
seguía encontrando: las marcas que el propio test citaba como dato. Un
criterio que dice «cero» y devuelve doce es indistinguible de un cierre
fingido, y el archivo exento habría sido justo el más propenso a criar la
siguiente excepción. Así que el test **escribe los nombres por trozos**
(`"Sli" + "de"`), que es el recurso habitual para que un guardia no case con
su propia fuente: la lista de excepciones está vacía, no hay salto, y
`test_this_file_is_scanned_like_every_other` comprueba que el guardia está
dentro de lo que vigila.

El test **falla con el árbol de 0.1.159**, y eso está comprobado sobre una
copia de `HEAD`: 165 líneas en 57 archivos. Un test de ausencia que pasara en
los dos lados no vigilaría nada.

## 8. Alcance y comprobación

- Suite entera, sin filtrar, `QT_QPA_PLATFORM=offscreen python tests/_runner.py`.
- `grep` del patrón de la ficha sobre los cinco paquetes y `tests/`: **0**, en
  crudo y **sin excluir ningún archivo**.
- `grep` de los cinco nombres de archivo de su ayuda: **0**, igual.
- `grep` del patrón ampliado (`Slide[0-9]?`): **0**.
- **Cero dígitos movidos.** No hay A/B numérico porque no hay nada que medir:
  no se ha tocado una línea ejecutable de cálculo. La evidencia de que las
  ediciones de prosa no han roto nada es la suite completa, que es donde
  aparecería una cadena que alguien comparaba.
- Versión en los siete sitios y este changelog.

---

© 2026 Samuel Sáez López — UPCT — AGPL-3.0-or-later
