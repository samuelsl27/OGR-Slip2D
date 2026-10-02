# OGR Slip2D v0.1.236

**D93: un cálculo estadístico se hace sobre el modelo que calcula el
análisis, lo llame quien lo llame, y lo dice.** Con una norma de diseño
activa, cada muestra se prepara como el análisis (los coeficientes parciales
y los enlaces de Generalized Anisotropic) aunque se llame a
`run_global_minimum`, `run_overall_slope` o `run_sensitivity` directamente,
y la interfaz llama a lo que enseña factor de sobredimensionamiento y no
factor de seguridad.

**D246: *Compute Statistics* funciona desde el menú.** Desde 0.1.59 reventaba
con cualquier proyecto que la ventana hubiera adjuntado (nuevo, abierto o la
demo) y la ventana no decía nada. Se encontró al implementar D93.

Primera versión de la segunda parte de la tanda P5 (D93, D87, D89, D88,
D90). El banco está fuera de git.

---

## 0. Lo que se encontró, y dónde

### La premisa del prompt de D93 ya no se sostenía en la puerta

El prompt citaba `_compute_statistics` pasando el proyecto sin factorizar a
las tres funciones. Desde 0.1.201 la interfaz, la API y el servidor MCP
pasan por `analysis_runner.run_configured_statistics`, que calcula el
determinista con `run_analysis` y prepara cada muestra (`prepare`). La
medida del paso 1 ya estaba en el changelog de 0.1.201. El `grep` de cierre
que pedía (`apply_design_factors`) tampoco habría casado: la preparación es
`prepare_analysis_project`.

### Lo que quedaba, medido con 0.1.235 antes de tocar nada

Talud pequeño de `test_cli_wiring_v177`, cohesión 10 ± 2 kPa entre 4 y 16,
EC7 DA1-C2, muestreo LHS con la semilla del proyecto. El determinista de la
puerta es 0,9084:

| Análisis | Puerta | Llamada directa sin `prepare` | Directa con `prepare` |
|---|---|---|---|
| Global Minimum, 200 muestras | media 0,9071, PF 0,850, β −1,041 | media 1,1333, PF 0,120, β 1,194 | = puerta |
| Overall Slope, 40 búsquedas | media 0,9064, PF 0,850, β −1,065 | media 1,1325, PF 0,125, β 1,205 | = puerta |
| Sensibilidad, c de 4 a 16 | F de 0,6365 a 1,1779 | F de 0,7952 a 1,4726 | = puerta |

Quien llamaba a la función directamente (el script del banco, los tests,
`python_exec` del servidor MCP) juntaba un determinista factorizado con
muestras sin factorizar. Además:

- la interfaz no lo decía: `_compute_statistics` no leía
  `out.factor_report`, y la ventana de estadística rotulaba «FoS», a fuego y
  sin `tr()`, lo que con norma es un factor de sobredimensionamiento;
- ningún test cubría Overall Slope ni la sensibilidad con norma;
- el script del banco evaluaba el determinista del círculo dado con el
  método del registro sin configurar (el añadido de 0.1.235 a la ficha).

### D246: la acción del menú reventaba

Al preparar el test de la interfaz con el proyecto adjuntado como lo adjunta
la aplicación, la revisión del plan lo encontró y se reprodujo sobre el
árbol de 0.1.235 intacto:

```
listeners: ['MainWindow._on_project_event', 'CanvasView.set_project.<locals>.<lambda>']
w._compute_statistics() -> TypeError: cannot pickle 'MainWindow' object
  (run_global_minimum -> clone_project -> copy.deepcopy)
```

`MainWindow._attach_project` pone el método de la ventana entre los oyentes
del proyecto, y `copy.deepcopy` copia un método ligado copiando el objeto al
que está ligado: la ventana, que no se copia. Las dos piezas vienen de la
primera versión pública. La excepción sale de la acción del menú y la
aplicación no tiene `excepthook`, así que la ventana no decía nada. La API y
el MCP no fallaban: sus trabajos copian con `ogr_api.snapshot.detached_copy`,
que ya quitaba los oyentes.

**Por qué ningún test lo vio:** todos los de la interfaz de estadística dan
el proyecto a la ventana por asignación (`w.project = p`), y el único oyente
que eso deja es la lambda del lienzo, que `deepcopy` comparte en vez de
copiarla.

La propietaria decidió corregirlo en esta versión (D246, abierta y cerrada
aquí).

### D247: la misma causa, otro síntoma, sin corregir

`_parallel_grid_run` manda el proyecto a los procesos con `pickle` y, si
falla, vuelve a la búsqueda secuencial sin decirlo. El proyecto de la
ventana no se serializa, así que *Compute* desde la interfaz ha calculado
siempre en serie. Con la demo: 6,4 s frente a 3,5 s, el mismo F = 1,091433.
Se abre como D247 y no se toca: arreglarlo hace que la aplicación lance
procesos desde su hilo de cálculo, y eso hay que probarlo en la aplicación
real.

## 1. El motor

- **`prepare=None` es la preparación del análisis** en `run_global_minimum`,
  `run_overall_slope` y `run_sensitivity` (`_analysis_copy`, que llama a
  `prepare_analysis_project`). El método por defecto y el evaluador se
  configuran desde el proyecto preparado sin muestrear, como la puerta los
  configura desde `factored`. Es la tercera vez que un valor por defecto del
  muestreador pasa a ser «lo que hace el análisis»: 0.1.108 lo hizo con el
  método y 0.1.235 con el evaluador.
  - Un `prepare` explícito se respeta tal cual: lo pasa la puerta, y un test
    que cuenta sus llamadas (`test_f3b_ops_v1201`) no ve ninguna de más.
  - Sin norma y sin enlaces, la preparación es el propio objeto: nada más se
    mueve.
  - Declarado en el docstring, porque la opción invierte el viejo desajuste:
    quien calcule su determinista sobre el modelo CRUDO con una norma activa
    tendrá ahora muestras factorizadas junto a él. Nada en la función puede
    saber de qué modelo salió un `LEMResult`.
- **La copia factorizada se distingue y se rechaza.**
  `Project.design_factored_copy` (declarado en `__init__`, no se guarda en el
  `.ogr`, sobrevive a `deepcopy` y `pickle`) lo pone `apply_design_factors`
  en su copia y nunca en el modelo. Los tres `run_*` la rechazan con una nota
  en `notes["error"]`: muestrearla escribiría valores sin factorizar sobre
  valores factorizados y los factorizaría otra vez. La única puerta pública
  a esa copia es `AnalysisOutcome.project`.
- **D246: `ogr_core/project/copies.py::detached_copy`.** La receta de
  `ogr_api.snapshot` llevada al núcleo. `clone_project` la usa conservando
  las cachés de regiones (como el `deepcopy` desnudo: una muestra cambia
  parámetros y no las fronteras de las regiones, y la caché se revalida por
  su firma), y la API la usa en frío, como siempre.

## 2. La interfaz

- `_compute_statistics` guarda el informe de su propia corrida
  (`last_statistics_factor_report`, aparte del de *Compute*: las dos
  corridas no tienen por qué compartir norma), pone primero en las notas
  «Design standard applied to every sample: …» y, con norma, la barra de
  estado dice «Over-design factor: PF = …». Sin norma, la barra lee
  exactamente lo que leía.
- `StatisticsWindow` recibe el informe: una etiqueta propia con lo que son
  los números (oculta sin norma), y los rótulos de los tres gráficos por la
  función nueva `reported_quantity.sample_label`. Pasan por `tr()` cadenas
  que estaban a fuego.
- Los dos gráficos de estadística de Interpret (sensibilidad y convergencia)
  preguntan al informe de la corrida estadística, no al de *Compute*.
- `statistics_factor_lines` y `sample_label` viven en
  `ogr_gui/reported_quantity.py`, con los demás rótulos (D96): una
  decisión, un sitio.
- Doce entradas nuevas en español, con «factor de sobredimensionamiento»
  como en D96; ninguna repite una clave existente (D240).

## 3. Tests

**`tests/test_statistics_design_factors_v1236.py`** (D93), 23 casos sobre el
talud pequeño con EC7 DA1-C2. Ninguno fija un factor de seguridad: todo es
una identidad entre dos maneras de calcular lo mismo, o una diferencia que
tiene que existir.

- **La llamada directa es la puerta:** con las críticas de la propia puerta y
  nada más, las mismas muestras dan los mismos factores, a 1e-12, en Global
  Minimum, Overall Slope y el barrido de sensibilidad.
- **Regla 7:** el comportamiento de 0.1.235, pedido a mano (`prepare` = la
  identidad), da otros números (más de un 10 % por encima, en los tres).
- **Sin norma no se mueve nada:** listas IGUALES, no cercanas.
- **La otra mitad de la preparación:** un rango de Generalized que enlaza un
  material sigue la muestra de ese material; sin preparar, las ocho muestras
  son la copia que guarda la regla.
- **La copia factorizada:** la bandera está en la copia y nunca en el modelo,
  no existe sin norma, sobrevive a las copias de una corrida y no se guarda;
  los tres `run_*` la rechazan.
- **La interfaz:** con norma, la nota, la barra de estado, la etiqueta y los
  rótulos de los tres gráficos dicen sobredimensionamiento; sin norma, la
  ventana es la de siempre. Interpret pregunta al informe de la corrida
  estadística.
- **Una sola puerta:** por AST, el `prepare` por defecto llama a
  `prepare_analysis_project` y lo usan los tres `run_*`.

**`tests/test_statistics_from_the_window_v1236.py`** (D246), 9 casos con el
proyecto adjuntado por `_attach_project`, como lo hace la aplicación: las dos
premisas (la ventana vigila su proyecto con su propio método; un `deepcopy`
desnudo arrastra la ventana), la copia del motor sin vigilantes y con el
mismo modelo, la caché caliente para una muestra y fría para un trabajo de
la API, la copia que se serializa, y *Compute Statistics* desde la acción
del menú, probabilístico y sensibilidad, sin tocar el modelo.

**Discriminación** contra `git archive` 97f9a07 (0.1.235), con el runner de
ese árbol:

- el de D93 falla **17 de 23**: siete por comportamiento, siete por símbolo
  (`_analysis_copy`, la bandera, `_stat_factored`) y tres de interfaz por el
  `TypeError` de D246. Pasan las premisas y «sin norma no se mueve nada», a
  propósito;
- el de D246 falla **7 de 9**, todos con `TypeError: cannot pickle
  'MainWindow' object`; pasan las dos premisas.

Para que los casos de interfaz de D93 no dependan de D246, se repitieron
sobre 0.1.235 con SOLO el arreglo de D246 aplicado: los tres siguen
fallando, y el de la sensibilidad por comportamiento (rotula «Factor of
safety» lo que es sobredimensionamiento).

**Un test protegido que casi cambia:** `test_design_factor_report_gui_v1165`
cuenta las líneas `self.last_factor_report = None` y
`self.last_statistics_notes = []` de `main_window.py` y exige que coincidan.
Convertir el reinicio de `_compute_statistics` en una asignación directa
bajaba una cuenta; el reinicio literal se conserva y las líneas de la norma
se añaden después. El test no se toca.

## 4. El banco

- **`_tools/ejecutar_probabilistico.py`** calcula el determinista sobre el
  proyecto como lo prepara el análisis (`prepare_analysis_project`; sin norma
  es el mismo objeto) y, para el círculo dado del 028, con el evaluador
  configurado (`build_evaluator`) y no con el método del registro sin
  configurar y `min_area = 0`. Es el añadido de 0.1.235 a la ficha de D93,
  que no podía quedarse fuera al retirarla.
- **Base comprobada antes de correr:** los once `resultados_probabilistico*.json`
  vivos eran, byte a byte, los de `Evaluaciones/0.1.235`.
- **Re-corrida del lote** con `correr_probabilistico.py`: 5339 s con la suite
  en paralelo (el 036 solo, 3099 s). Comparados con la instantánea por ruta
  (todo el JSON aplanado, sin `version_ogr` ni `segundos`): **189 números, 4
  distintos y ninguna clave sin pareja**. Los cuatro son el
  `deterministic_fos` del 028, y ninguna muestra se mueve:

  | Corrida | 0.1.235 | 0.1.236 | Diferencia |
  |---|---|---|---|
  | ej4 modo A | 1,438007 | 1,438015 | +0,0006 % |
  | ej4 modo B | 1,447503 | 1,447510 | +0,0005 % |
  | ej5 modo A | 1,158797 | 1,158839 | +0,0037 % |
  | ej5 modo B | 1,179862 | 1,179866 | +0,0003 % |

  Las otras seis del 028 y el 036 (Global Minimum PF 2,240 %, Overall Slope
  PF 3,000 % con 4 mínimos distintos) salen idénticas. Las cuatro diferencias
  quedan por debajo de la tolerancia de convergencia del banco (1e-4).

- **A/B en memoria** (`_auditoria/P5_0236/ab_probabilistico_d93.json`): para
  cada una de las once corridas, el censo de la preparación y Global Minimum
  con el `prepare` por defecto y con la identidad (el comportamiento de
  0.1.235), en el mismo proceso y con las mismas muestras. La preparación es
  el mismo objeto en los once modelos (ninguno tiene norma ni enlaces), y
  **0 de 60 000 muestras** se mueven, con los mismos índices y la misma PF.
  Overall Slope no se paga: con la preparación igual al proyecto, es la misma
  cuenta por construcción.
- **Cierres.** `d93()` y `d246()`, CUBIERTO POR TEST. `d93()` comprueba en
  vivo que la llamada directa sin `prepare` es la preparación del análisis (a
  1e-12) y no el modelo crudo (+24,9 % en la media del talud del test), que
  la copia factorizada se rechaza, el AST, el A/B archivado con los cuatro
  deterministas declarados, los once archivos a 0.1.236 o posterior y la
  discriminación. Con el motor de 0.1.235 (`PYTHONPATH` a su `git archive`)
  los dos salen NO SE SOSTIENE.
- **D247** entra en P5, al final; D93 y D246 se retiran al índice.
- **Ciclo de cierre:** `verificar_cierres.py` completo, **209 cierres y 0
  bajadas**; instantánea `Evaluaciones/0.1.236` (2956 archivos, comprobados
  byte a byte) con las dos secciones retiradas guardadas; `PAQUETES` podado
  y la cadena de P5 tachada a mano; `PROMPTS_RESOLUCION.md` regenerado (47
  prompts, ninguno sin paquete); `auditoria_invariantes.py` con 0 ERROR en el
  02 y en la raíz.

## 5. Lo que se reporta y NO se corrige

- **D247**, arriba.
- **`run_analysis(outcome.project)` factoriza dos veces.** La copia guarda
  la norma activada, así que pasar la copia otra vez por la puerta del
  análisis la vuelve a factorizar. La bandera nueva permitiría rechazarlo,
  pero nadie lo hace dentro del programa; se anota.
- **`_compute_statistics` no enseña los avisos de su corrida
  determinista** (`out.warnings`), salvo el último cuando no hay crítica: el
  de estadística con sismo de `settings_warnings` solo aparece tras un
  *Compute*. Es la decisión de 0.1.170 (D129) y no se cambia aquí.
- **Overall Slope acumula `run.evaluations`, pero la crítica también lee las
  superficies del usuario**: una mínima que sea una superficie del usuario
  entra en `global_minima` y nunca en las estadísticas por superficie.

## 6. Verificación

- **Suite entera:** 5296 de 5297, con el lote del banco en paralelo. El
  único fallo, `test_mcp_transports_v1195::test_the_token_host_and_origin_are_enforced`,
  fue de arranque: el test espera 30 s a que el servidor HTTP responda y,
  con el 036 ocupando los cuatro núcleos, no llegó (`ConnectError` 10061).
  Repetido solo con la máquina libre: 6 de 6. No toca nada de esta versión.
- **Selección de los 37 archivos de estadística, normas, interfaz, i18n y
  API:** 780 de 780, después de restaurar el reinicio literal que cuenta
  `test_design_factor_report_gui_v1165`.
- **Discriminación:** 17 de 23 y 7 de 9 contra 0.1.235, y los casos de
  interfaz de D93 también contra 0.1.235 con solo D246 aplicado.
- **Banco:** la re-corrida del lote (189 números, 4 movidos y declarados),
  el A/B en memoria (0 de 60 000 muestras) y el ciclo de cierre de D93 y D246
  (209 cierres, 0 bajadas).

**Qué falta por probar:**
- **La aplicación real, a mano:** *Compute Statistics* desde el menú con un
  proyecto abierto de disco y con una norma activa (los tests adjuntan el
  proyecto como lo hace la aplicación, pero no abren un archivo).
- **Un modelo del banco con norma de diseño y estadística:** no hay
  ninguno; el efecto de D93 está medido en el talud sintético del test.
