# OGR Slip2D v0.1.192

**Cinco fichas del paquete P1 en una tanda —D154, D176, D177, D178 y D179— y
una sexta, D181, abierta y cerrada en ella. Todas son la regla 7 o su
vecina: un control o un ajuste que no hace lo que dice.** El botón de la
calculadora GSI que no escribía nada, la tolerancia que nadie leía, el
chequeo que se apagaba al reabrir el proyecto, la cadena que dejaba el talud
seco y el −120 que se exportaba como −101. Y D181, que salió al planear D176
y es peor que ella: el diálogo de materiales redondeaba a cuatro decimales
todos los parámetros de resistencia cada vez que se aceptaba, también sin
tocar nada.

De las cinco fichas hubo que corregir la premisa de tres antes de escribir
código (§0). El banco no se re-corre. Por qué ninguna de las seis puede mover
un dígito se argumenta ficha a ficha en el §7, y en cada caso es por
identidad, no por muestreo.

---

## 0. Lo que estaba mal en los encargos

### D178: «las de λ no tienen el problema» es falso

El paso 2 de P-D178 decía que las migraciones de λ «comparan números con
1e−12 y no tienen el problema», y pedía comprobarlo en vez de suponerlo.
Comprobado, **lo tienen**. −1,5 → −0,1 (v0.1.106) y 1,5 → 6,0 (v0.1.90) sólo
miran el valor, así que quien hoy escribe a propósito `max_lambda = 1,5`
reabre el proyecto con 6,0, y `min_lambda = −1,5` vuelve como −0,1.
`test_lambda_range_v190.py:326` lo fija. El comentario de la propia clase
dice que el alcance viejo «sigue estando disponible porque el rango es un
ajuste», y −1,5 es exactamente ese alcance. La ficha prohíbe mover la cadena
de λ, así que se reporta como **D182** y no se toca. En el banco no pasa por
ahí ningún modelo: 0 de 240 `.ogr` vivos llevan ±1,25 o ±1,5.

### D178: había una tercera salida, y es la buena

La ficha ofrecía dos salidas: un campo nuevo con la versión que escribió el
archivo, o retirar la migración. Hay una tercera, y sale de la historia:
`tensile_percent` entró en `AdvancedSettings` en el **mismo commit** que
cambió el valor por defecto a False (`81c997d`, v0.1.74; `git log -S` no
devuelve ningún otro), y `asdict` la escribe en cada guardado. Su ausencia es
exactamente «escrito antes de v0.1.74». Es la regla por la que ya migra el
resto del módulo, la PRESENCIA de una clave (`_SHADOW_FIELDS`, `pre_v1103`,
`Material.use_sat_unit_weight`), y no cambia el formato. Un campo de versión
tampoco habría servido para los archivos que ya existen, que seguirían
necesitando este mismo marcador. Decisión del propietario.

### D154: un `__post_init__` deja la mitad de la puerta abierta

P-D154 pedía convertir en un `__post_init__`. El censo de llamadores encontró
unas veinte ASIGNACIONES posteriores a la construcción (interfaz, tests y
`_tools/`), y un `__post_init__` no las ve. La conversión va en
`Material.__setattr__`: el `__init__` de un dataclass asigna por `setattr`,
así que cubre las dos puertas con una sola regla.

### D154: el número de la ficha era de otra versión

La ficha cita 1,0886090318268722 con la cadena, medido con 0.1.180. Con
0.1.191 la cadena da **1,0886079707982514**, que es **bit a bit** el factor
del mismo talud con `NONE`: «seco» no es una figura. El 1e−6 entre los dos es
deriva del motor entre las once versiones y no mueve el número mojado, que
sigue en 0,5592600533686025.

### D176: el arreglo que pedía la ficha habría escrito s = 0

«Escribir en `panel._editors`» era correcto y no bastaba. Esos editores
redondean a cuatro decimales, así que el botón arreglado habría guardado
s = 0 justo en las rocas de GSI bajo, las de s más pequeña. De ahí D181 (§5).

Y el reproductor de la ficha sigue imprimiendo `False [...] None` después del
arreglo, porque sondea `panel._widgets`, un atributo que no existe ni debe
existir. Lo que cambia es que el botón escribe. En el plan escribí que «debe
dejar de imprimir None», y era falso.

---

## 1. D179 — `tensile_tolerance` se retira

Era la tolerancia del filtro de tracción ENTRE DOVELAS de v0.1.24 («5 % de
max|E|»), que v0.1.32 sustituyó por el Tensile Stress Check en las BASES.
Desde entonces todas las búsquedas lo recibían, lo guardaban en
`self.tensile_tolerance` y ninguna lo leía (`git log -S`: ya estaba muerto en
el primer commit de git, 0985074). Desde v0.1.191 el nombre además se lee
como la resistencia a tracción que esa versión introdujo, que es la del
material.

- Sale de la firma de `BaseSearch.__init__` y del atributo.
- `_base_kwargs` lo consume y lo descarta, con la razón escrita, para que una
  llamada vieja que lo pase por nombre siga construyendo. No se rechaza con
  `TypeError` como `temperature_factor` porque la ficha exige esa
  compatibilidad.
- Se reescribe el comentario de v0.1.24 de `BaseSearch.__init__`, que seguía
  describiendo como vigente el filtro entre dovelas justo encima del de
  v0.1.32, que explica que ya no existe.

## 2. D178 — el chequeo de tracción sobrevive a guardar y abrir

`AdvancedSettings.from_dict` convertía TODO `check_tensile_stresses: true` en
`false`, y su comentario prometía respetar «a un usuario que escribió otra
cosa a propósito». En un booleano el valor por defecto viejo y la elección
deliberada son el mismo valor, así que la condición no podía distinguirlos y
nunca lo hizo. Ahora sólo migra un bloque sin `tensile_percent`. El comentario
se reescribe y dice que las de λ siguen por valor (D182).

Con esto el alcance de D165 deja de estar limitado: la tolerancia de roca
llega también a los proyectos reabiertos. La cabecera de
`test_tensile_strength_rock_v1191.py`, que decía lo contrario, se actualiza, y
también el docstring de la migración en `test_project_settings_wiring_v174.py`.
Su fixture ya era un bloque anterior a v0.1.74 (tiene `min_initial_fs` y no
`tensile_percent`) y sigue pasando sin tocar una aserción.

## 3. D154 — `Material.pore_pressure` se convierte al escribirse

`Material.__setattr__` convierte con `PorePressureType(value)`, la conversión
del propio cargador, así que no es una regla nueva:

- un miembro se devuelve a sí mismo;
- una cadena válida se convierte en su miembro;
- cualquier otra cosa (`"WATER_TABLE"`, `"piezo_line"`, `None`) lanza
  `ValueError` en la línea que la escribe, y no al guardar.

`copy`/`pickle` restauran `__dict__` sin pasar por ahí, lo cual es correcto,
porque lo que restauran ya se convirtió al escribirse. Lo comprueba un test,
porque la búsqueda manda los proyectos a los procesos hijos por ese camino.

**El censo** de los demás campos enumerados está en
`docs/audits/enum_coercion_census_v1192.md`:

- Cubre **17 clases**. Se barrieron en tiempo de ejecución, resolviendo cada
  anotación campo a campo (ver §8, error 4), y ninguna convertía.
- **Seis más son silenciosas como Material**, medido en vivo donde la clase se
  construye sola:
  - `LineLoad` con `"horizontal"` empuja en vertical, (0, −1) en vez de (1, 0);
  - `TensionCrackProperties` con `"filled"` pone el agua en el FONDO de la
    grieta;
  - `HydraulicProperties` con `"van_genuchten"` da kr = 1,0 a 50 kPa de
    succión en vez de 0,0103, 97× la conductividad;
  - `SupportInstance`/`SupportPattern`, leído en el código: `"active"` se
    trata como pasivo y la orientación cae a paralela al soporte;
  - `DistributedLoad.distribution` sólo se nota con `magnitude_2`.

  Todas → **D183**, sin corregir por decisión del propietario, para no
  ensanchar la tanda.
- `Boundary` falla ruidosamente.
- `ProjectSettings` sigue el convenio contrario: campos `str` que guardan
  `.value`.

## 4. D177 — la exportación escribe −120

La ventana decidía el código leyendo la NOTA: «m_alpha» → −112, no convergida
→ −111, todo lo demás → −101. La nota de tracción dice «(error −120)» y se
exportaba como genérica. Ahora el motor dice qué chequeo rechazó la
superficie en vez de dejar que la ventana lo adivine:

- `SCREEN_TENSILE_STRESS` y `SCREEN_M_ALPHA` en `methods/base.py`, en su
  propio `ALL_SCREENS` y **fuera** de `ALL_REASONS`. Aquellas son razones de
  un cálculo que FALLÓ, y una superficie cribada tiene factor convergido.
- `LEMResult.admissibility_reason`, también en `to_dict`. No se reutiliza
  `reason`, cuyo contrato es «vacío en un resultado que tuvo éxito».
- `checks.screen_surface` devuelve `(ok, screen, nota)`. `check_surface` queda
  como envoltorio de dos valores, con la nota **idéntica carácter a carácter**,
  porque la leen la búsqueda, Optimize Surfaces y la ventana.
- `_is_admissible` guarda la razón y `_raw_data_rows` escribe −120 por la
  constante. La rama de −112 conserva el literal `"m_alpha" in note`, que
  exige `test_m_alpha_notes_v1158.py`.
- Una superficie que falla los dos chequeos sale −120, porque el cribado mira
  primero la tracción. Lo fija un test sobre la cuña degenerada de
  `test_checks_v132`, que falla los dos (medido).

La ventana es el único sitio que traduce a códigos: ni la CLI ni el informe
lo hacen (grep).

## 5. D176 + D181 — el botón escribe, y el panel deja de redondear

**D176.** `_open_parameter_calculator` buscaba los editores en
`getattr(panel, "_widgets", {})` y el panel los guarda en `_editors`, así que
aceptar la calculadora no cambiaba nada.

- La escritura se aparta a `_apply_parameter_result`, que un test puede
  llamar sin el `exec()` modal.
- Va por `_StrengthParamPanel.set_param_values`, que convierte con la misma
  función que `set_model` (`_si_to_user`) y **lanza `KeyError`** ante un
  nombre sin editor, en vez de saltárselo, que es como se escondió D176.

**D181 (nueva, medida con 0.1.191).** Los editores eran `QDoubleSpinBox` con
cuatro decimales, `setValue` redondea a ellos, y el diálogo reconstruye la
resistencia desde sus editores cada vez que guarda un material. Abrirlo y
pulsar Aceptar **sin tocar nada**, sobre una roca de GSI 10:

| | antes | después de Aceptar |
|---|---|---|
| s | 4,5399929762484854e−05 | 0,0 |
| mb | 0,4018402645107363 | 0,4018 |
| σt = s·σci/mb | 5,649 kPa | 0 |

Con GSI ≤ 13 se pierde `s` entera; con GSI 20, un 29 %. La tabla de puntos de
los modelos por función tenía el mismo defecto a tres decimales
(`f"{:.3f}"`).

Arreglo:

- `_PreciseSpinBox` guarda a la precisión máxima de Qt (323 decimales), así
  que `setValue` no redondea nada que quepa en un double.
- Muestra el texto más corto que vuelve exacto (`repr`, con el separador
  decimal del locale), de modo que releer su propio texto no pierde dígitos.
- Acepta notación científica.
- Las celdas de la tabla se escriben con ese mismo texto exacto.

Alcance: sólo el panel de parámetros de resistencia. Los demás editores del
mismo diálogo (γ y γsat con 4 decimales, φb con 2, valor de entrada de aire
con 3, ru con 3, u con 2, Hu con 3, B̄ con 3) y los ~95 `setDecimals` del
resto de la interfaz no se censan. No está medido si algún valor realista
pierde algo ahí.

---

## 6. Lo que se reporta y NO se corrige (regla 6)

- **D182** (P1): las migraciones de λ de `AdvancedSettings.from_dict` deciden
  sólo por el valor (§0). 0 de 240 `.ogr` vivos del banco las ejercen.
- **D183** (P1): los seis campos enumerados silenciosos del censo (§3).
- **D184** (P3): `BaseSearch._is_admissible` envuelve el cribado en
  `except Exception: return True`, así que un chequeo que revienta ADMITE la
  superficie sin decir nada. Es pariente de D94. No se mide aquí cuántas veces
  ocurre.
- **Observación, sin número**: el colapso de mα DENTRO de un método
  (`bishop.py`, «mα collapsed» con α griega y `converged=False`) se exporta
  como −111 y no como −112. No sé si la referencia lo trata como −112. Queda
  escrito para quien lea su tabla de códigos.

## 7. Por qué el banco no se re-corre

- **D154**: `PorePressureType(miembro) is miembro`, el banco carga sus modelos
  por `from_dict`, que ya convertía, y hay 0 cadenas en sus
  `construir_modelo.py` (42 argumentos, todos enums) y en `_tools/`.
- **D178**: 0 de 240 `.ogr` vivos llevan el chequeo encendido, y los 240
  llevan `tensile_percent`.
- **D179**: no tenía lecturas.
- **D177, D176, D181**: interfaz y un campo nuevo en el resultado, que el banco
  no lee.

## 8. Errores propios detectados antes de publicar

1. La cabecera del test de D179 decía «3 fallan, 2 pasan» antes de medirlo.
   Medido son 4 y 1: la puerta compartida también falla en 0.1.191, porque
   consumir el nombre nunca fue el problema; el problema era reenviarlo.
2. El primer test de D177 comprobaba `to_dict` sobre un resultado hecho a
   mano, cuyas dovelas son una lista y no un `Slices`, así que reventaba el
   test y no el motor. Ahora usa la cuña real.
3. El primer test de la tabla de D181 leía los puntos de `params`, y los
   modelos por función los guardan en `.points`.
4. El primer barrido del censo usó `typing.get_type_hints` y **perdió
   `Material` y `SupportInstance`**, las dos clases que más importan, porque
   tienen referencias adelantadas que no se resuelven en su módulo. Dio 13
   clases en vez de 17.
5. Escribí la fila de `DistributedLoad.distribution` por analogía con
   `orientation` antes de mirarla. En el código sólo se nota con
   `magnitude_2`.
6. En la primera versión del test de D177 sólo uno de ocho casos fallaba por
   comportamiento contra 0.1.191; los demás fallaban por un nombre que no
   existía. Se añadió el caso de extremo a extremo (búsqueda real, ventana
   real, filas elegidas por la nota que los dos árboles escriben).
7. El barrido de identidad de D181 exigía `tried >= 20`, un suelo por el que
   podía pasar un barrido encogido. Ahora exige la igualdad exacta: los 15
   modelos con parámetros × 2 valores.
8. En el plan escribí que el reproductor de D176 «debe dejar de imprimir
   None» (§0).

## 9. Los tests

Discriminación contra 0.1.191 MEDIDA en un `git worktree` en `ea7931e`,
declarada fila a fila en la cabecera de cada archivo.

| Archivo | Casos | Fallan en 0.1.191 | Por comportamiento |
|---|---|---|---|
| `test_tensile_tolerance_retired_v1192.py` | 5 | 4 | 2 (+1 ausencia AST, +1 firma) |
| `test_tensile_setting_reopen_v1192.py` | 6 | 2 | 2 |
| `test_material_enum_coercion_v1192.py` | 11 | 10 | 10 |
| `test_tensile_export_code_v1192.py` | 9 | 8 | 2 (6 débiles: falta un nombre) |
| `test_gsi_calculator_write_v1192.py` | 9 | 9 | 5 (+1 ausencia AST, 3 débiles) |

Ninguno fija un factor contra una instantánea. Los anclajes:

- la identidad entre el constructor y el cargador (D154);
- la tabla de códigos de la referencia (D177);
- la forma cerrada s = exp((GSI − 100)/(9 − 3D)) de Hoek, Carranza-Torres y
  Corkum (2002), sobre lo que llega al material (D176/D181);
- la identidad «aceptar sin tocar no cambia nada» (D181);
- el marcador en los siete `.ogr` de `validacion/` (D178).

## 10. Verificación

**Estructural.** El diff del motor es:

- `material.py`: un `__setattr__`;
- `settings.py`: una condición y su comentario;
- `search.py`: la firma, `_base_kwargs`, `_is_admissible` y un comentario
  caducado;
- `checks.py`: `screen_surface`, con `check_surface` como envoltorio;
- `methods/base.py`: dos constantes, un conjunto y un campo;
- los siete sitios de versión.

En la interfaz: `_raw_data_rows` y el panel de parámetros del diálogo de
materiales. Ningún método de análisis cambia una línea.

- **Suite entera, sin argumentos y con el changelog escrito: 4215/4215**, sin
  banner `FILTERED RUN`. 0.1.191 traía 4175; los **+40** son exactamente los
  cinco ficheros nuevos (5 + 6 + 11 + 9 + 9). **Dos veces**:
  - 29 min 13 s, con el instrumento de D154 puesto y el cierre del banco
    corriendo a la vez;
  - 29 min 11 s, limpia, sola en la máquina y sobre el estado definitivo.

  Son unos tres minutos más que las dos medidas de 0.1.191 (26 min 10 s y
  25 min 29 s), y **no son de esta tanda**: los cinco ficheros nuevos, cada uno
  solo, cuestan 1,9 + 0,9 + 1,0 + 2,0 + 2,7 = 8,5 s, contando el arranque del
  intérprete de cada uno. Es la deriva que AGENTS.md describe («el reloj total
  no es una medida»), y se dice para que nadie la lea como coste del arreglo.
- **Censo de D154 sobre esa misma corrida**, con un `sitecustomize` que
  envuelve `Material.__setattr__` y registra a un archivo (los hijos de
  `ProcessPoolExecutor` también lo cargan).
  - Proceso principal: **145 093 escrituras de `pore_pressure` con miembro y
    32 con cadena, las 32 de `test_material_enum_coercion_v1192.py`**, que
    las pasa a propósito.
  - Los 234 procesos hijos: cero y cero, porque reciben los proyectos por
    `pickle`.

  En toda la suite nadie más escribe una cadena. El arreglo es identidad
  medida y no sólo buscada con grep, y el control está dentro: el instrumento
  ve las 32.
- Selecciones dirigidas por ficha, todas en verde:
  - D179: 205/205 (`search postprocess cli_wiring`);
  - D178: 216/216 (`project_settings tensile m_alpha_notes lambda_range
    parallel_search v019_features transient_coupling`);
  - D154: 238/238 (`material lambda_closure water_surfaces base_normal
    m_alpha_ponded composite_surfaces cli_wiring`);
  - D177: 311/311 (`interpret tensile checks m_alpha no_number lambda_floor
    lambda_state_cache relaxed_thrust thrust_flag`);
  - D176/D181: 225/225 (`m6 material gsi i18n menu`).
- `verificar_cierres.py D154 D176 D177 D178 D179 D181`: **CUBIERTO POR TEST**
  cinco y **CUBIERTO POR CODIGO** D179.
  - Contra el worktree de 0.1.191, las seis dan **NO SE SOSTIENE**, y por
    comportamiento. D177 exporta `['-101', '-112', '-111']`. D176 deja los
    editores en 2,5 / 0,004 / 0,5. D181 devuelve `s = 0,0` y la tabla a tres
    decimales.
  - Ninguna lee un artefacto con el nombre de la versión instalada (D175).
- `generar_comparativa.py` + balance contra `Evaluaciones/0.1.191`: **559 →
  559 filas, las 559 IGUAL, 0 sin pareja**.
- `retirar_cerrados.py --escribir D154 D176 D177 D178 D179 D181`: 6 secciones
  retiradas y 6 renglones en el índice, citando `Evaluaciones/0.1.192` porque
  la instantánea se tomó antes.
  - Fichas nuevas D182, D183 y D184 con su prompt largo y su paquete (P1, P1,
    P3). Cabecera: último usado D184.
  - A mano: `PAQUETES` podado y las cadenas de P1 y P3 al día.
  - `PROMPTS_RESOLUCION.md`: 49 prompts, 40 largos. El generador sale con 1
    por los **9 FALTA anteriores** a esta tanda (D137, D138, D139, D142, D143,
    D150, D168, D169…), no por la codificación de la consola, como se venía
    suponiendo.
- `auditoria_invariantes.py`:
  - 02: **0 ERROR** (748 hallazgos: 491 AVISO y 257 INFO, el mismo perfil que
    en 0.1.186–0.1.191);
  - raíz: **0 ERROR**, con 64 AVISO, ninguno de esta tanda.
- Instantánea `Evaluaciones/0.1.192` con **1692 archivos comprobados byte a
  byte**, tomada otra vez con `--forzar` después de retirar, con el mismo
  reparto de versiones que la anterior: esta tanda no re-corrió nada.

Y una advertencia que va aquí porque es fácil de leer al revés: que el banco
no se mueva no quiere decir que estos arreglos no hagan nada. Quiere decir
que el banco no construye materiales en código, no guarda proyectos con el
chequeo de tracción encendido, no pasa `tensile_tolerance`, no exporta desde
la ventana y no abre diálogos. Los seis mueven lo que tienen que mover, y
los tests lo demuestran sobre modelos construidos para ello.
