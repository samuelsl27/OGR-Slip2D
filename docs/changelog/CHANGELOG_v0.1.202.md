# OGR Slip2D v0.1.202

**Cuarto bloque de correcciones, antes de F4.** Cinco puntos que dejó
abiertos v0.1.201, dos de ellos decididos a partir de la documentación de
referencia:

1. *Abrir* limpia el proyecto anterior.
2. El retroanálisis con Janbu estaba mal: una fuerza no nula en el factor
   sin soporte.
3. Las muestras inadmisibles ya no cuentan en la probabilidad de rotura.
4. El tipo de la rejilla de presiones lo decide el método de agua.
5. El banco del manual 05 se corrige: sus curvas de usuario vuelven a kPa.

---

## 1. *Abrir* limpia el proyecto anterior

*Nuevo* y la demo limpiaban a mano los resultados:

- el panel de resultados;
- `last_search_result(s)`;
- los avisos del cálculo;
- las notas de estadística;
- el informe de coeficientes.

*Abrir* no limpiaba nada de eso. Tras abrir un archivo, el panel enseñaba el
resultado del proyecto anterior, e *Interpret* u *Optimize Surfaces*
trabajaban con sus superficies sobre el modelo recién abierto.

Toda la limpieza vive ahora en un único sitio, `_attach_project`, por el que
entran los tres caminos. También limpia el solver de agua de la sesión y el
último barrido de desembalse, que no limpiaba ninguno de los tres.

## 2. El retroanálisis con Janbu

**Comprobado con un ejemplo construido**, como pediste:

- talud de 10 m, c′ = 6 kPa, φ′ = 22°, dos círculos, 30 dovelas;
- en el factor de seguridad que el propio solver da a la superficie **sin
  soporte**, la fuerza necesaria tiene que ser cero.

| Método | F₀ del solver | Fuerza «necesaria» en F₀, antes | Después |
|---|---|---|---|
| Janbu simplificado (R = 27) | 1,39263 | **217,5 kN/m** | 0 |
| Janbu simplificado (R = 33) | 1,67459 | **217,7 kN/m** | 0 |
| Janbu corregido (R = 27) | 1,48570 | **269,3 kN/m** | 0 |
| Janbu corregido (R = 33) | 1,78535 | **287,7 kN/m** | 0 |
| Bishop (R = 27) | 1,50856 | 0,23 kN/m | 0,23 kN/m |

Había dos defectos en `back_analysis.py`:

- **cos²α.** El solver divide cada término resistente por
  n_α = cos²α·(1 + tan α·tan φ/F), que es cos α·m_α. El retroanálisis
  partía de `[c b + (W − u b) tan φ]/m_α` y lo **multiplicaba** por cos α.
  - Con las sumas viejas, R/D daba 1,12063 donde el solver da 1,39263.
  - Con la corrección da 1,39267.
- **f₀.** Janbu corregido itera con F sin corregir y multiplica por f₀
  (Janbu 1973) al final. El retroanálisis usaba el objetivo corregido
  dentro de las sumas. Ahora evalúa con F/f₀.

Bishop conserva un residuo de 0,2 kN/m, que viene de su estimación de la
normal.

**Números guardados:** ninguno. El único caso del banco con retroanálisis
(02-037) usa Bishop.

## 3. Una muestra necesita un factor de seguridad para contar

**Decisión, a partir de la referencia.** La guía define la probabilidad de
rotura sobre los análisis **válidos**:

> «If the safety factor could not be calculated for some analyses, then
> numtotal = total number of VALID analyses»

Además declara «INVALID», con código −112, una superficie con
m_α < 0,2 (y con −120 si falla la comprobación de tracción).

**Lo que hacía OGR:**

- **Global Minimum y sensibilidad** reevaluaban cada muestra con una
  `GridSearch` desnuda:
  - m-alpha siempre activo, aunque el proyecto lo apagara;
  - tracción siempre apagada, aunque el proyecto la activara;
  - aceptaban la muestra con `is_valid`, que no mira la admisibilidad.
- **Overall Slope** tomaba el `critical` de la búsqueda, que recurre a
  una superficie inadmisible cuando no hay otra. La superficie crítica
  probabilística acumulaba también las inadmisibles.

**Ahora:**

- los tres motores reevalúan con `settings.admissibility_kwargs()` del
  propio proyecto;
- cuentan una muestra solo si es válida **y** admisible (`counts_as_sample`);
- las demás van a `failed_samples`, con su código en `lost_by_cause`
  («−112 m-alpha», «−120 tensile stress»). Esa clave está en el resumen de
  cada método, para el agente y la interfaz.
- La frase del aviso del 20 % no cambia; hay un test que la vigila.

**Test:**

- un círculo cuyo m_α cruza 0,2 cuando la cohesión va de 0 a 6 kPa;
- las muestras de cohesión baja caen en −112, no cuentan, y la PF usa las
  que quedan;
- con m-alpha apagado en el proyecto vuelven todas (regla 7).

**Medido en el banco:** no se mueve ninguna cifra.

- Las 11 probabilísticas del manual 02 (P028 ×10 con Global Minimum y P036
  con Overall Slope; 2931 s) coinciden con su línea base cifra a cifra,
  incluida la PF 3,0 % de la del 036.
- La del Ej001 del manual 04 (Overall Slope, 100 muestras) sigue en PF
  9,0 % y FS medio 2,139, exactos frente a la publicada, sin ninguna muestra
  fallida.
- Las dos del Ej005 (sin y con correlación, Bishop y Janbu, 100 muestras)
  coinciden cifra a cifra con su línea base, sin muestras fallidas. Dan PF
  25 / 31 % y 19 / 26 %; el manual publica 25 / 30 % y 21 / 25 %.

Ninguno de esos modelos tiene muestras que caigan en −112 o −120: el filtro
nuevo no descarta nada en el banco. Donde sí cambia la cuenta es en el test
construido a propósito y en la repetición a mano de
`test_probabilistic_v135`, que ahora reevalúa con los mismos criterios de
admisibilidad que el motor.

## 4. El tipo de la rejilla de presiones es el del método

**Decisión, a partir de la referencia** (*Water Pressure Grid*):

> «Set the desired Water Pressure Grid type in the Project Settings
> dialog. Each point is defined by x and y coordinates, and a value,
> corresponding to the … type … selected in Project Settings.»

La referencia también dice que la opción solo se habilita con uno de los
tres métodos de rejilla. **En la referencia, la rejilla guarda (x, y, valor)
y el tipo es del método.**

OGR hacía lo contrario: `WaterPressureGrid.value_type` convertía los valores
y el método solo encendía la rejilla, así que la mitad del método que dice
el tipo no se leía (regla 7).

**Ahora:**

- `pore_pressure_at` recibe el tipo del método (`value_type_for_method`);
- la rejilla ya no lo guarda.
- **El cargador conserva lo que el archivo significaba.** Si un `.ogr`
  trae el tipo de la rejilla y un método de rejilla distinto, el método
  pasa a ser el de la rejilla, que es con el que se leía.
- `value_type=` se sigue admitiendo al **construir** una rejilla (los
  scripts del banco lo pasan). Queda como tipo *declarado*: no se guarda y
  no convierte. Si el método lo contradice, `check_analysis_settings` se
  niega a calcular, en vez de leer la rejilla de una forma en silencio.
- **Interfaz:**
  - *Water Pressure Grid* solo se habilita con un método de rejilla
    (`rules.grid_refusal`);
  - el diálogo muestra el tipo del método, en solo lectura.
- **Agente:** `water_grid_set(value_type=…)` fija el método `grid_<tipo>`
  en el mismo paso de deshacer.

**Números guardados:** ninguno.

- Hay 56 modelos con rejilla en el repositorio y el banco: el 012 y el 013
  del manual 02 y sus instantáneas.
- Todos son `grid_pore_pressure` con `value_type = pore_pressure`.
- Ningún archivo usa carga total ni carga de presión.

## 5. El banco del manual 05

**El recuento de v0.1.200 se quedó corto.** Decía «cambian 4 de 265
modelos», pero:

- los problemas 006, 007, 009, 017, 018, 019 y 020 construyen su curva de
  usuario en el script, convirtiendo de kPa a metros (`kpa / GW`);
- no tienen `.ogr`, así que el A/B sobre archivos no los vio;
- con v0.1.200 esas curvas quedaban unas 9,81 veces mal.

Eran **4 + 7**. El defecto estaba abierto en el banco como D121.

**Corregido** (fuera de git):

- las siete curvas vuelven a kPa, como las da el manual;
- el 014 convierte su curva de Gardner a kPa (ψ·9,81), y su docstring ya no
  dice «en metros»;
- el 010 y el 011 pierden las variantes `alpha_kPa` / `a_kPa` y sus
  resultados, como pedía el criterio de cierre de D121.

**Medido.** Manual 05 entero con v0.1.202 frente a `Evaluaciones/0.1.159`:
1166 valores comparados, 24 movidos y 13 sin pareja. Los 13 sin pareja son las
dos variantes retiradas.

- **006, 007, 009 y 014: idénticos al dígito.** La curva en kPa leída en kPa
  da exactamente lo mismo que la curva en metros leída en metros. Es la
  comprobación de que la corrección de unidades de v0.1.200 es consistente.
- **010 y 011:** sus variantes en la unidad equivocada ya no existen. El 010
  queda a +0,01 % del caudal de Clement et al. (1996) y el 014 a 0,009 % de la
  solución cerrada de Gardner (1958).
- **001, 004 y 005 son los tres que usan el modelo *Simple*.** Es el que
  cambió de unidad en v0.1.200:
  - en el 001, x_a pasa de 4,152 a 4,227 m. En la malla del manual se aleja
    de Slide (+2,3 % → +4,1 %); en la malla fina se acerca a la solución
    cerrada (−4,0 % → +1,0 %);
  - el 004 no se mueve ni en la última cifra, aunque su kr mínima baja de
    0,954 a 0,634: la superficie libre sigue tocando el dren en su base;
  - el 005 solo publica contornos. P(15, 8) sube un 24 % sin cambiar ninguna
    fila.
- **La comparativa del 05** pasa de 116 OK / 28 REVISAR / 16 DISCREPANCIA
  / 215 sin cifra a **116 / 25 / 16 / 213**:
  - cinco filas desaparecen con las variantes retiradas;
  - **una cambia de estado: 05-001 x_a pasa de REVISAR a DISCREPANCIA**
    (+4,11 % frente a Slide y +6,00 % frente a la solución cerrada, en la
    malla del manual). Es un efecto de la corrección de unidades que el
    propietario decidió en v0.1.200, a través del modelo *Simple* (D190).
- **D121 se cierra** (CUBIERTO POR TEST). Su comprobación buscaba el test por
  el nombre del archivo; ahora busca la clase
  `TestEachModelGetsItsOwnUnit`, que es la que fija las unidades.
- **Nace D190** para *Simple*. Ninguno de los cinco pares de
  `_SIMPLE_PARAMS` tiene fuente (regla 1), y mientras la succión llegaba en
  metros la curva casi no actuaba y no se notaba. No lo corrijo: una curva
  plausible sin fuente es justo lo que AGENTS.md prohíbe inventar. El prompt
  pide leer la definición de la referencia o declararla convenio propio.

## 6. Lo que destapó la corrida: un valor por defecto movió el banco sin que cambiara un archivo (D191)

La primera corrida del 05 movía **017, 018, 019 y 020** —los transitorios no
saturados— hasta un **−49 %** en el nivel freático. La conversión de
unidades no lo explicaba: con la misma conversión, 006, 007 y 009 salían
idénticos.

**La causa, medida con un A/B en el 017:**

- v0.1.200 cambió el α por defecto de van Genuchten de 0,036 a 3,6 1/m, que
  es el loam de Carsel y Parrish (1988) en la unidad correcta.
- El cargador de `.ogr` conserva 0,036 en un archivo sin la clave. Esa parte
  estaba prevista.
- Los scripts del banco construyen `HydraulicProperties(...)` en Python y
  tomaban el valor por defecto nuevo.
- El almacenamiento del transitorio lee la retención de van Genuchten con
  **cualquier** modelo de permeabilidad, también con una curva de usuario.

| α (1/m) | y_freatica (x = 38; t = 16 383 h) | H(38, 1) | H(30, 2) |
|---|---|---|---|
| 0,036 | 2,765 m (igual que 0.1.159) | 2,413 | 5,950 |
| 3,6 | 1,405 m (−49 %) | 1,362 | 4,554 |

A 0,5 m de succión, la capacidad de retención pasa de 0,0007 a 0,179 1/m:
seis veces el almacenamiento específico de ese problema (0,0294 1/m).

**Decisión, para que nada guardado se mueva.** Los scripts del 05-017–020 y
del 02-102 (van Genuchten, que también reconstruye su `.ogr` por script)
fijan α = 0,036 con la razón escrita. Es el mismo criterio que ya aplica el
cargador. Tras fijarlo, los cuatro vuelven a 0.1.159 al último dígito.

**La corrección de v0.1.200 estaba incompleta.** Decía que no se movía ningún
modelo guardado, y era cierto para los archivos. No lo era para un modelo
construido por script: 05-017–020 se habrían movido en cualquier corrida
entre v0.1.200 y esta.

**Reportado sin corregir (D191, regla 6).** La interfaz no enseña θs, θr ni
Ss en ninguna página, y α y n solo en la de van Genuchten. Aun así, el
transitorio los lee con cualquier modelo. Un usuario con una curva de
usuario obtiene un transitorio que depende de cinco parámetros que no ve ni
puede cambiar; el agente sí puede, con `hydraulic_set`. Además, el manual
solo da mv en esos problemas, así que ninguno de los dos α es «el del
manual». Arreglarlo exige leer qué hace la referencia sin función de
contenido de agua y añadir una página de interfaz, que no es de esta
versión.

## 7. Reportado, sin corregir

- **D190.** El modelo *Simple* no tiene fuente (§5).
- **D191.** El transitorio lee una retención que la interfaz no enseña
  (§6).

Las dos están en `ERRORES_Y_DISCREPANCIAS.md` del banco, en el paquete P6,
con su prompt largo y su comprobación de cierre (`verificar_cierres.d190()`
y `d191()`).

## 8. Tests

`tests/test_block4_v1202.py`, una clase por punto:

- **`TestOpenForgetsThePreviousProject`.** Abre un `.ogr` con el diálogo
  sustituido (sin modal) y comprueba que no queda nada del proyecto
  anterior: panel, superficies, avisos, notas, informe de coeficientes,
  estadística, retroanálisis, solver de agua y barrido de desembalse.
- **`TestTheBackAnalysisAgreesWithTheSolver`** (regla 1: consistencia con
  un camino ya validado). Con Bishop, Janbu simplificado y Janbu corregido,
  la fuerza necesaria en el F₀ del solver es menor que una tolerancia
  pequeña frente al peso de la masa, y por encima de F₀ hace falta fuerza.
  Con el código viejo, Janbu da 217 kN/m.
- **`TestASampleNeedsAFactorOfSafety`.**
  - Las muestras −112 no cuentan, y la PF usa las que quedan.
  - Con m-alpha apagado en el proyecto vuelven todas (regla 7).
  - Un `critical` inadmisible en Overall Slope es una búsqueda perdida.
- **`TestTheGridTypeIsTheMethods`.** Comprueba:
  - las tres conversiones, según el método;
  - la migración de un archivo discrepante;
  - el rechazo de un tipo declarado que el método contradice;
  - que el agente fija el método en un paso;
  - que la acción de la interfaz está deshabilitada sin un método de
    rejilla.

**Tests actualizados, con su razón:**

- `test_water_pressure_grid_v123` y `test_water_surfaces_v162`:
  `pore_pressure_at` recibe el tipo;
- `test_probabilistic_v135`: la repetición a mano reevalúa con la
  admisibilidad del proyecto;
- `test_groundwater_ops_v1200`: el texto de la nota del agente.

**Fuera del repositorio** (banco, fuera de git):

- los scripts 006, 007, 009, 014 y 017–020 y el 02-102;
- las notas de nueve `referencia.json`;
- `verificar_cierres.py` (D121 encuentra su test; D190 y D191 nuevas);
- `generar_prompts.py` (P6).

**Verificación:** la suite entera, sin filtros, pasa **4518 de 4518**.

Una primera pasada se cortó al 44 % por dos motivos:

- **Dos fallos reales.** Faltaban cuatro traducciones del diálogo de la
  rejilla: «Total Head», «Pressure Head», «(not a grid method)» y su ayuda.
  Ya están.
- **Tests de la versión siguiente.** El archivo de tests de F4, que ya estaba
  en `tests/` sin estar en git, llama a `main(["--attach"])`. Sin F4, argparse
  hace `sys.exit(2)`, y el runner, que captura `Exception` pero no
  `SystemExit`, termina la suite sin totales. La suite de esta versión se corrió
  sin los archivos de F4.

**Reportado sin corregir.** Que una prueba que sale con `sys.exit` corte la
suite entera, en vez de contar como un fallo, se corrige en v0.1.203.
