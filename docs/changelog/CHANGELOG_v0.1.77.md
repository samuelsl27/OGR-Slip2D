# OGR Slip2D v0.1.77 — el CLI deja de inventarse el análisis, y Slope Search deja de no existir

## Qué se buscaba

Cerrar el pendiente anotado en tres changelogs seguidos (v0.1.72 §3,
v0.1.74 §2, v0.1.75 §1): **`ogr_cli` no aplica el descenso rápido**, así
que un cálculo por terminal devuelve el factor de seguridad ordinario en
silencio.

## Lo que resultó ser

El enunciado se quedaba corto. El arreglo mínimo eran dos llamadas
—`check_drawdown_settings` al cargar y `wrap_for_drawdown` al instanciar—
y se descartó al comprobar que el descenso rápido no era el problema,
sino un síntoma:

> **`ogr_cli.compute` no leía `p.settings` en absoluto.**

Lo único que consultaba del `.ogr` era la geometría y los materiales que
deserializa `Project.load`. Todo lo demás lo construía con sus propios
valores por defecto de línea de comandos.

La regla que explica el reparto, y que conviene recordar porque predice
dónde volverá a pasar:

- **Lo que vive dentro de `slice_surface` o de los métodos llega al CLI
  gratis**: exceso de presión intersticial (v0.1.75), cargas lineales
  (v0.1.75), dirección de rotura (v0.1.73), sismo, sostenimientos, la
  migración del convenio invertido (v0.1.69).
- **Lo que la interfaz hacía *antes* de llamar al motor, no llegaba.** Y
  eso era exactamente el cuerpo de `_ComputeWorker`.

Tres de esas omisiones fallaban **del lado inseguro y en silencio**:

| Omisión | Qué devolvía el terminal |
|---|---|
| Descenso rápido | El FS **anterior** al desembalse |
| Coeficientes parciales de diseño | Un FS con c', φ' y γ **sin minorar** |
| Campo FE de filtración | Un talud **seco** (u = 0) |

Y el resto devolvía simplemente otro número: cuatro de las seis
búsquedas inalcanzables, la semilla, la tolerancia, el número de
iteraciones, el FS inicial, Steffensen, las comprobaciones de
admisibilidad, y el número de dovelas.

Medido sobre el modelo de Morgenstern (1963) con un círculo fijo en
(60, 380) r = 380:

| | FS |
|---|---|
| Embalse lleno, sin desembalse | 2.7782 |
| **Descenso rápido B̄ completo** | **1.2956** |

El terminal venía informando 2.7782 para un proyecto que pedía lo
segundo.

## El hallazgo que cambió el alcance: Slope Search nunca ha funcionado

Al construir el runner compartido, la primera ejecución de las seis
estrategias por el camino de la interfaz dio esto:

```
grid                   ok, FS = 1.0987
slope                  FAILED -> TypeError: SlopeSearch.__init__()
                                 got an unexpected keyword argument 'slope_limits'
auto_refine            ok, FS = 1.0995
block                  ok, FS = 0.2101
path                   ok, FS = 1.0382
simulated_annealing    ok, FS = 0.5000
```

`SlopeSearch` era **la única de las seis búsquedas que no aceptaba
`**legacy_kwargs`**, así que no recibía ni `slope_limits` ni los tres
argumentos de admisibilidad que `_ComputeWorker` pasa a todas. Elegir
*Slope Search* en Project Settings y pulsar *Compute* lanzaba un
`TypeError`… que el `except Exception` del worker convertía en un diálogo
«Error» genérico sin resultados.

`git log -S "slope_limits=slope_limits"` sitúa la llamada en `0985074`,
**la primera versión pública**. No es una regresión: Slope Search no ha
funcionado nunca desde la interfaz.

Es exactamente el patrón que v0.1.74 ya había pagado caro: *un `try` que
protege de un modelo malo también oculta un error de programación*. Allí
un `TypeError` se manifestó como suite colgada media hora; aquí, como una
función entera que no existe. El manejador se ha quedado —hace falta—
pero con un comentario que dice lo que cuesta, y el nombre del tipo de
excepción sigue en el mensaje porque es lo único que distingue las dos
cosas en pantalla.

Curiosidad incómoda: **el Slope Search del CLI sí funcionaba**, porque no
pasaba los ajustes. Funcionaba por ignorar al usuario.

## Qué se hizo

### `ogr_slip2d/analysis_runner.py` (nuevo, sin Qt)

El único sitio donde un proyecto se convierte en un análisis:

- `check_analysis_settings(project)` — todas las razones por las que el
  proyecto no se puede analizar tal como está. Envuelve el
  `check_drawdown_settings` que ya existía y le suma el campo FE.
- `settings_warnings(project)` — ajustes que la búsqueda elegida no lee.
- `build_method(project, method_id)` — **la única instanciación de
  métodos**, con `lem_kwargs()` y `wrap_for_drawdown` aplicados aquí y en
  ningún otro sitio. Es el argumento que el propio docstring de
  `wrap_for_drawdown` llevaba escrito desde v0.1.68; `ogr_cli` era el
  «second place that forgot».
- `build_search(project, method_id, progress_cb)` — el despacho de las
  seis estrategias.
- `run_analysis(project, method_ids, progress_cb)` — una búsqueda por
  método sobre una **copia minorada**; devuelve resultados, informe de
  coeficientes y avisos.

La tabla de métodos se deriva de `method_registry()` en vez de escribirse
a mano. Los siete métodos registrados son ahora alcanzables desde ambos
caminos:

```
bishop_simplified        1.0987     janbu_corrected      1.1009
gle_morgenstern_price    1.0970     lowe_karafiath       1.1081
janbu_simplified         1.0306     ordinary_fellenius   1.0432
spencer                  1.0978
```

Y un `method_id` desconocido deja de ser un `continue` mudo: se acumula
como aviso. Eso es lo que permitía marcar *Janbu Corrected* en Project
Settings y no obtener nada.

### `ogr_gui/main_window.py`

`_ComputeWorker` pasa de **276 líneas a 52**: el hilo y las señales. Las
cinco búsquedas que funcionaban devuelven **exactamente el mismo número**
(1.0987, 1.0995, 0.2101, 1.0382, 0.5000), y `slope` devuelve 1.0744 donde
antes devolvía una excepción.

`build_search` se queda como delegado, porque tiene cuatro consumidores
(retroanálisis, Overall Slope probabilístico, Optimize Surfaces y el
barrido de desembalse) y ninguno debía cambiar de comportamiento. Ya no
construye un `_ComputeWorker` desechable para capturar el objeto.

`act_compute` usa la comprobación ampliada. Los avisos van a la **barra
de estado, no a un diálogo**: `_on_compute_done` lo ejecuta la suite, y
un modal sin pantalla bloquea indefinidamente.

### `ogr_slip2d/search.py`

`SlopeSearch` acepta y reenvía `**legacy_kwargs` como sus cinco
hermanas. Las comprobaciones de tracción y de m-alfa son ajustes del
proyecto, no de cada búsqueda.

`slope_limits` **no** se le pasa, y esto es deliberado: `SlopeSearch.run`
deriva su ventana de entrada y salida del perfil del terreno y no lee
ningún límite del usuario. Aceptar el argumento habría sido un ajuste que
no hace nada, que es lo que la regla 7 prohíbe. En su lugar,
`settings_warnings` lo dice en voz alta.

### `ogr_cli/__main__.py`

- **Manda el proyecto.** Todas las opciones pasan a `Optional[...] = None`.
  Sin escribirlas se usa Project Settings; escritas, sobreescriben esa y
  solo esa. Los defaults viejos **cambiaban el número**: `--slices 30`
  contra los 25 del proyecto, y `--dr 1.5` → 2 intervalos → 3 radios por
  centro donde un proyecto que pide 10 quiere 11.
- Se calculan **todos los métodos habilitados**, no uno.
- `check_analysis_settings` antes de calcular; cualquier motivo →
  `typer.Exit(3)` con el porqué.
- Con norma de diseño activa la tabla dice **over-design factor**, no FS.
  Es lo que EC7 significa: los coeficientes van a las entradas.
  Comprobado: 1.1382 → 0.9114 con c' y tan φ' entre 1.25.
- Varios métodos → un `.h5` por método, porque `save_results` escribe un
  único `SearchResult`.
- El docstring del módulo decía «guaranteed identical behaviour between
  interactive and automated runs». Ahora es verdad; hasta esta versión
  era la afirmación más falsa del repositorio.

### Y un comando que reventaba, anterior a todo esto

`ogr-slip2d-cli methods` **no funcionaba en una consola de Windows**. Los
`✓` y `—` de su tabla no son codificables en cp1252, que es lo que Python
elige ahí, así que imprimir la tabla lanzaba un `UnicodeEncodeError` y el
comando devolvía un traceback en lugar de una lista. Comprobado contra
`HEAD`: los mismos glifos, el mismo fallo, en todas las versiones
anteriores — en la máquina del propio autor.

`tests/_runner.py:123-131` ya se había topado con esta trampa y la había
documentado. Se aplica el mismo remedio, una vez, en un `@app.callback()`
que corre antes de cualquier comando. Salió al recorrer «los comandos que
nadie prueba porque no calculan», que estaban en la lista de verificación
precisamente por eso.

## Qué se probó

Suite completa con `QT_QPA_PLATFORM=offscreen python tests/_runner.py`.

`tests/test_cli_wiring_v177.py` es nuevo, **26 tests**, y `ogr_cli` no
tenía ninguno antes: ni un fichero de la suite lo importaba. Uno por
cable, y cada uno mueve el número:

- el descenso rápido llega al terminal, y los dos caminos coinciden en el
  mismo círculo hasta 1e-6;
- un descenso rápido con r_u se rechaza con código 3;
- los coeficientes parciales se aplican y el `.ogr` del usuario **no
  cambia byte a byte**;
- `search_method`, `radius_increment`, `num_slices` y la semilla salen
  del proyecto, y una opción escrita a mano sigue ganando;
- un proyecto FEM sin campo se rechaza, y la misma guarda protege la
  interfaz;
- los siete métodos son alcanzables, `janbu_corrected` produce resultado,
  y un id desconocido deja aviso;
- las seis estrategias arrancan por ambos caminos;
- la llamada exacta que rompía Slope Search;
- y los cuatro comandos que no calculan (`methods`, `strength-models`,
  `new-demo`, `info`) más un fichero inexistente, porque uno de ellos
  llevaba roto desde siempre y nadie lo ejecutaba.

Coste: ~15 s el fichero entero. Los dos tests caros son los que hacen
búsqueda aleatoria (4.8 s y 5.7 s); el resto usa una rejilla de 3×3
centros a propósito, porque estos tests miden **qué análisis corrió**, no
lo bueno que es el mínimo.

## Qué falta por probar

- **Un proyecto real, grande, calculado por los dos caminos y comparado
  dígito a dígito.** Los tests usan modelos pequeños.
- **Slope Search no está validado contra ninguna referencia externa**, y
  ahora que se ejecuta por primera vez desde la interfaz, debería. Que
  produzca un número no dice que sea el correcto. Es lo primero que haría
  a continuación.
- El barrido de niveles de desembalse y el retroanálisis usan
  `build_search`; funcionan, pero no hay test que compruebe que el objeto
  que reciben es el mismo de antes del refactor.
- Python 3.11 y 3.13 en CI: en local solo hay 3.14.

## Pendientes

1. **`Lowe-Karafiath` sigue gris en Project Settings** con el tooltip
   «Not yet implemented», y está implementado, registrado y validado
   (`lowe_karafiath.py:49`). Ahora además es alcanzable desde el CLI, lo
   que hace la contradicción más visible. Reportado, no corregido.
2. **`seepage_result` no se serializa en el `.ogr`.** Esta versión lo
   detecta y se niega a calcular, que es barato; guardarlo de verdad es
   otro trabajo, y tiene coste de tamaño de fichero que conviene decidir
   aparte.
3. **`SlopeSearch` no lee las Slope Limits.** Avisado, no implementado:
   cablearlo cambia qué superficies se generan, o sea el número, y eso
   necesita su propia validación.
4. **El CLI sigue sin análisis probabilístico, barrido de niveles,
   retroanálisis ni informes.** Con el runner en su sitio, cada uno es
   ahora un comando pequeño en lugar de una reimplementación.
5. **El `except Exception` de `_ComputeWorker.run` sigue ahí.** Hace
   falta —un modelo malo no debe tirar la aplicación— pero es el segundo
   fallo grave que oculta en cuatro versiones. Merece pensar si los
   errores de programación deberían distinguirse de los de modelo antes
   de que oculte un tercero.
