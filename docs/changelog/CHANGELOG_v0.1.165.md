# OGR Slip2D v0.1.165

**El encargo de P-D96 pedía que la interfaz dijera lo que la línea de
comandos dice desde v0.1.127 —que con una norma de diseño activa el número
publicado es un factor de sobredimensionamiento y no un factor de
seguridad— y está hecho. Pero su paso 1 está medido y es falso: poner la
frase como primera nota NO la lleva a la barra de estado. La barra sólo
guarda un mensaje temporal, y la línea del factor, que se emite después, la
sustituye antes de que nadie la lea. La nota vale por el panel; quien
arregla la barra es el rótulo.**

Cierra **D96**. **Cero dígitos movidos**, y medido: de los **1635 archivos
`.ogr`** del banco, **ninguno** activa `design_standard`, así que el «cero»
es consecuencia y no coincidencia. **No sale defecto nuevo**: la anomalía
que aparece al medir ya estaba numerada como **D93**, y lo que se aporta es
la medida que su propio paso 1 pide.

---

## 1. El defecto

`run_analysis` devuelve el informe en `outcome.factor_report`
(`ogr_slip2d/analysis_runner.py:1691`). `ogr_cli/__main__.py:228-248` lo
lee: rotula la columna «Over-design factor» y escribe la frase que explica
por qué. La interfaz lo guardaba en `_ComputeWorker`
(`ogr_gui/main_window.py:145`) **y no lo leía nadie** — el grep de
`factor_report` en `ogr_gui` daba exactamente dos líneas, la que lo escribe
y la que lo inicializa a `None`.

De modo que la misma corrida se describía bien en un terminal y mal en una
ventana. Es la regla 7 en su historia más antigua, la que la propia ficha
cita en su primera línea: los coeficientes parciales estuvieron dos
versiones configurables sin aplicarse (v0.1.52 → v0.1.57). Se aplican desde
entonces; lo que faltaba era decirlo.

El número siempre fue correcto. Lo que faltaba era el nombre.

## 2. Lo que la ficha da por sentado y la medición desmiente

Seis cosas, y tres cambian el trabajo.

**(1) Su paso 1 no hace lo que dice que hace.** La ficha escribe que
poniendo la frase la primera «sale en la barra de estado (que enseña la
primera)». No sale. `_on_compute_done` enseña la primera nota
(`main_window.py:3004`) y **veinticuatro líneas después** enseña la línea
del factor (`:3027`), y una `QStatusBar` guarda **un** mensaje temporal:

```
after note : 'NOTE first'
after fos  : 'Critical FoS (bishop): 1.234'
```

La nota sólo sobrevive cuando la corrida no encontró superficie crítica,
que es justo el caso en que no hay número que rotular mal. Por eso el
arreglo no puede quedarse en el paso 1: **el rótulo de la línea 3028 es lo
único que la barra llega a enseñar** en una corrida con resultado. Queda
fijado en `test_the_first_note_does_not_survive_in_the_status_bar`, y la
propiedad de Qt en la que se apoya, aparte, para que un fallo diga cuál de
las dos se rompió.

**(2) Dos de sus tres citas ya no apuntan a código.** El sitio que rellena
`last_compute_warnings` no es la línea 2967 sino la **2993**; el panel de
notas no está en 3041-3061 sino en **3077-3097** — 3041-3065 es
`_ordinary_pore_pressure_warning`. Las de `_ComputeWorker` (116, 145) y las
de la CLI (228-248) sí eran correctas.

**(3) Su receta de reproducción no selecciona nada.** La ficha manda correr
`python tests/_runner.py --list design` y promete que salgan al menos
`test_m6_v157.py`, `test_project_settings_m2_v152.py` y
`test_cli_wiring_v177.py`. Salen **cero**, con **código 2**: el runner casa
el patrón contra el *stem* del archivo (`_runner.py:247-252`) y ningún test
del proyecto se llama `*design*`. Peor, su línea de verificación
—`_runner.py design cli_wiring i18n_coverage`— sale con **código 0** y dos
archivos, ignorando `design` en silencio, de modo que **la verificación de
la ficha nunca corría los tests de norma de diseño**. La selección buena es
`m6 project_settings_m2 cli_wiring user_surfaces`.

**(4) El nombre del test.** `_v1160` es la versión en que se redactó la
ficha; la convención es que `_vNNNN` es la versión en que **aterriza**, así
que es `test_design_factor_report_gui_v1165.py`. Igual que D91, D95 y D98.

**(5) `d96()` no existía**, aunque el criterio de cierre la cite como si
estuviera escrita. Igual que D91, D95 y D98.

**(6) Su inventario se queda corto.** Nombra tres superficies; el rótulo
estaba mal en **seis**, y dos de las que faltan son las que el usuario mira
primero.

## 3. El arreglo

### Un solo decisor — `ogr_gui/reported_quantity.py`

`_reported_quantity` sale de `interpret_window.py` a un módulo propio, con
su comentario de v0.1.127 intacto: se le pregunta **al resultado y al
informe de la corrida**, nunca a `project.settings`, porque una ventana que
lee los ajustes puede contradecir los resultados que enseña —los ajustes
cambian después de una corrida; lo que la corrida hizo, no—. Módulo aparte
y no `interpret_window`, porque el dock de resultados y la ventana
principal tendrían que importar un módulo enorme para una función de diez
líneas.

`kind` **no gana un cuarto valor**. Un factor de sobredimensionamiento es
`critical.fos` calculado sobre datos factorizados: mismo campo, mismas
unidades, mismo `%.3f`. Lo que cambia es el nombre, no la magnitud, así que
los `kind` que ya se comparaban siguen valiendo sin tocarlos.

### Dos funciones, y separarlas es medio arreglo

`fos_label(factor_report)` no recibe el resultado, y eso **no** es un
descuido que convenga «simplificar». La barra de estado y el dock imprimen
`critical.fos` y sólo eso, **también en una corrida Ky**, donde ese número
es un factor de seguridad de verdad y correctamente rotulado —el tooltip de
Interpret lo enseña como `FS(0)`—, sólo que no es la magnitud que la
búsqueda minimizó. Darles el rótulo sísmico habría puesto «Critical seismic
coefficient» encima de un factor de seguridad: exactamente el defecto que
este módulo existe para evitar, con el signo cambiado. Se detectó
escribiéndolo mal primero.

### La precedencia, y aquí la interfaz NO copia a la CLI

El rótulo sigue al **valor que se imprime**: objetivo Ky → rótulo sísmico;
si no, informe aplicado → sobredimensionamiento; si no, factor de
seguridad. La CLI lo resuelve al revés (`__main__.py:242`: `if
seismic_objective and not factored`), de modo que una corrida Ky con norma
imprime un valor de Ky bajo el encabezado «Over-design factor». Es un
rótulo equivocado, la ficha prohíbe expresamente tocar la salida de la CLI,
y por tanto **se reporta y no se corrige** (§ 6). La divergencia va fijada
en un test para que nadie la «unifique» sin leer esto.

### El informe se guarda junto a sus resultados

`self.last_factor_report`, con la disciplina que v0.1.155 dejó escrita para
las notas: pertenece a **esa** corrida, así que se limpia en los **tres**
sitios que ya limpian las dos listas de notas (`__init__`, `act_new`,
`act_load_demo`). Hay un test que compara los recuentos de los dos
`= None` / `= []` para que un cuarto sitio de reinicio no nazca cojo.

### Seis superficies, no tres

| Sitio | Antes | Ahora |
|---|---|---|
| `main_window.py:3050` barra de estado | `tr('Critical FoS')` | rótulo consciente |
| `main_window.py:3006` notas | — | la frase, **la primera** |
| `interpret_window.py` resumen | `_reported_quantity()` | + rama factorizada |
| `widgets/results_dock.py:76` | `"Critical FoS:"` **sin `tr()`** | rótulo + `tr()` |
| `interpret_window.py` combo | `f"FoS = …"` fijo | rótulo consciente |
| `interpret_window.py` barra de método | `tr("   |   FS = %s")` | rótulo consciente |

Las tres últimas son gemelos que el inventario de la ficha no ve. El dock
decía «Critical FoS» **en inglés** mientras la barra de estado decía «FS
crítico» tres píxeles más abajo, y las dos sobre un factor de
sobredimensionamiento. Y las dos de Interpret son el mismo silencio dentro
de la ventana: el combo y la barra de método llevaban rotulando «FoS» las
corridas Ky **desde v0.1.127**, cuando el panel de resumen de esa misma
ventana ya decía «Critical seismic coefficient». La barra de método es
además el camino de **una sola** magnitud —el combo sólo existe con más de
un método—, o sea el que la mayoría de las corridas toma; arreglada la
ventana y no ella, la ventana se habría contradicho a sí misma en la
versión que venía a arreglar precisamente eso.

### El caso todo-unidad, y la nota que las dos interfaces tiraban

Con la norma activa y los seis coeficientes a 1.0, `apply_design_factors`
pone `applied = True` igualmente (`design_factors.py:143`) y el número es
un factor de seguridad corriente. El rótulo **sigue a la CLI** para que las
dos interfaces no se contradigan, y lo que impide que ese rótulo mienta a
solas es `report.notes`, que se publica junto a la frase: contiene «The
standard is enabled but every factor is 1.0, so nothing changed», y hasta
ahora **ninguna de las dos interfaces la leía**.

La frase lleva dos puntos y el panel agrupa por prefijo `"<método>: "`. No
la parte: la guarda de `_split` sólo toma prefijo si no tiene espacios
(`analysis_notes_panel.py:52-57`), y «Design standard applied» los tiene,
así que cae bajo **Model**. Comprobado leyendo la guarda y fijado en un
test, no supuesto.

### El panel obsoleto

El refresco del panel abierto estaba **dentro** de `if
self.last_compute_warnings:`, así que una corrida sin notas dejaba en
pantalla las de la corrida anterior aunque la lista se acabara de vaciar
dos líneas antes: el único caso en que el panel está garantizadamente mal
era el único que no lo refrescaba. Sale del `if`.

## 4. Lo que se probó

- **La suite entera, sin argumentos**: 3513/3513.
- **El test nuevo contra el árbol de 0.1.164**: falla **16 de sus 25**
  casos, que es la prueba de que mide algo. Los 9 que pasan son los que
  deben pasar: las dos premisas medidas, las identidades que el arreglo
  tiene que **conservar** (el número que enseña la ventana es el que
  devolvió el motor; sin norma el rótulo no cambia) y las pruebas del
  módulo nuevo.
- **Ninguna aserción fija un factor de seguridad.** Lo que se comprueba son
  identidades y nombres. Una instantánea de la aritmética de hoy no
  protegería nada.
- **Cero dígitos movidos**: no se toca una línea ejecutable de cálculo, ni
  una constante, ni una tolerancia, ni un valor por defecto.
- **El banco no hace falta re-correrlo, y eso está medido**: de los **1635**
  archivos `.ogr` del árbol del banco —1563 bajo el manual 02, que es lo
  que recuenta `d96()`— **cero** tienen `design_standard.enabled`. Se
  dice porque las cuatro versiones anteriores sí tuvieron que re-correrlo,
  y la razón de que aquí no haga falta es un censo, no una comodidad.
- Regla 3: no hay acción nueva, así que no hay nada que añadir a la barra
  de menús; `test_menu_reachability_v142.py` sigue verde.
- Regla 2: las dos claves nuevas tienen su entrada española, con el término
  castellano estándar («factor de sobredimensionamiento»), y el presupuesto
  de `test_i18n_coverage_v141.py` no se mueve.

## 5. Un error propio, detectado y corregido

La primera versión del arreglo daba al dock de resultados el rótulo
completo, el que también decide entre Ky y Newmark. El dock imprime
`critical.fos` **siempre**, así que en una corrida Ky habría publicado
«Critical seismic coefficient» sobre un factor de seguridad — el defecto de
esta misma ficha con el signo cambiado, introducido al arreglarla. De ahí
que haya dos funciones y no una, y que la razón esté escrita donde se
declara la segunda.

## 6. Reportado y no corregido (regla 6)

**D93 (ya abierta) — el probabilístico mezcla dos magnitudes.** Se creyó
nueva al medirla y no lo es: la ficha D93 —«la crítica sale del proyecto
FACTORIZADO y las muestras se evalúan sobre el SIN factorizar»— la describe
entera, y el «cf. D93» de la propia ficha D96 apuntaba ahí. Su paso 1 pide
exactamente esta medida «antes de tocar nada (regla 6)», así que aquí queda
tomada. `apply_design_factors` se llama **sólo** en
`analysis_runner.py:1578`.
`_deterministic_criticals` (`main_window.py:1613`) pasa por `run_analysis`
y sale factorizado; `run_global_minimum` y `run_overall_slope` reciben el
proyecto **sin** factorizar. Medido con `eurocode7_da1c2` sobre un talud
homogéneo, con una variable de dispersión ~0 para que la muestra sea el
material tal como el usuario lo escribió:

```
sin factorizar        FoS = 1.133368056
factorizado           FoS = 0.908398545
columna determinista      = 0.908398545   (factorizada)
media de las muestras     = 1.133368036   (SIN factorizar)
```

La ventana de estadística pone un factor de sobredimensionamiento de 0,908
al lado de una distribución centrada en 1,133 —un **25 %** de diferencia— y
calcula PF y β sobre las muestras sin factorizar. No se corrige aquí: mover
eso mueve dígitos y es una decisión sobre qué significa un análisis
probabilístico bajo una norma, no un rótulo — que es justo lo que D93 pide
decidir. La ficha D93 **no se edita** para meterle esta medida: es una ficha
abierta y ajena, y el precedente de 0.1.162 es no tocar su texto; queda
aquí, que es donde este proyecto guarda lo que se encontró.

Y una consecuencia que esta versión crea y conviene no perder: con D96
cerrada, la ventana ya **rotula** su columna determinista como factor de
sobredimensionamiento, así que las dos magnitudes que D93 denuncia están hoy
etiquetadas de forma distinta en la misma pantalla —«Over-design factor»
arriba, una distribución de factores de seguridad debajo—. El rótulo no
arregla D93; la hace visible.

**`factor_resistance` no lo lee nadie.** Está en el diálogo
(`project_settings_dialog.py:1188`), se persiste, y el preset
`eurocode7_da2` lo pone a **1.1**, pero `apply_design_factors` lee cinco
coeficientes y ése no está entre ellos. Es literalmente el defecto que la
ficha cita en su primera línea, vivo dentro de la misma función. No se
corrige: aplicarlo mueve dígitos para quien use DA2 y exige decidir con una
referencia cómo entra un coeficiente de resistencia en equilibrio límite.

**`factor_permanent` sólo hace de interruptor.** Se lee
(`design_factors.py:96`) pero el bucle de cargas multiplica los **dos**
grupos por `f_var` (`:127-130`). Con permanente 1.35 y variable 1.0 no se
factoriza nada **y `rep.loads` cuenta igual**, así que `summary()` diría «N
load(s) factored» siendo falso — y esa frase es justo la que esta versión
pone delante del usuario. Además `rep.loads` cuenta *atributos*
(`magnitude`, `magnitude_1`, `magnitude_2`), no cargas: una carga
trapezoidal cuenta dos.

**La CLI rotula un Ky como sobredimensionamiento** (§ 3, precedencia).

**`act_open` no limpia nada** (`main_window.py:939`): abrir otro proyecto
deja en pantalla los resultados y las notas del anterior.
`last_factor_report` hereda el mismo defecto, pero **junto a los resultados
a los que pertenece**, así que el rótulo no llega a mentir sobre el número
que se está viendo. La ruta `failed` (`:2973`) tampoco limpia.

**Las notas de `_compute_transient`** (`:2836-2841`) se lanzan a la barra en
un bucle —sólo sobrevive la última— y no llegan al panel: una tercera
fuente que `_analysis_notes()` no cubre.

**El PDF y el DXF siguen diciendo FS.** `report_generator.py:252` («Factor
of Safety (FS)») y `:306`, y `dxf/exporter.py:311`, son lo que el usuario
entrega a un tercero y no saben nada del informe. Quedan fuera por alcance:
necesitan un argumento nuevo en `ogr_core`.

**La cabecera del panel de notas** dice «none of them changes a factor of
safety» y ahora convive con una nota que dice que el número no es un factor
de seguridad. No es falso —la nota no mueve ningún número— pero se deja
escrito.
