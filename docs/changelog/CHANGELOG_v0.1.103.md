# OGR Slip2D v0.1.103 — seis ajustes que se veían y otros seis que se ejecutaban, y un test que exigía que siguiera así

Seis ajustes de búsqueda existían **dos veces**: el nombre que la interfaz
enseñaba y guardaba en el `.ogr`, y el nombre que el motor leía. El diálogo
escribía **los dos** desde el mismo control, así que desde la interfaz
coincidían siempre y nada parecía roto. Un proyecto construido por script —o
guardado por una versión anterior— se quedaba con el que **no** se consumía, y
el análisis corría con el valor por defecto del otro **sin decir una palabra**.

Es la **regla 7** otra vez, y es la tercera cara de la misma moneda: A9-1 (el
panel de optimización entero, guardado y leído por nadie), A37-1 (los filtros
de elevación y profundidad, cerrados en v0.1.102) y ahora **D07b**.

Se cierra **D07b** del banco de verificación.

---

## 1 · Los seis pares

| | Lo que se veía y se guardaba | Por defecto | Lo que el motor leía | Por defecto |
|---|---|---|---|---|
| 1 | `path_num_surfaces` | **5000** | `path_num_paths` | **500** |
| 2 | `auto_refine_num_iterations` | **10** | `auto_refine_iterations` | **5** |
| 3 | `auto_refine_divisions_along_slope` | 10 | `auto_refine_divisions` | 10 |
| 4 | `path_segment_length_manual` + `_value` | apagada | `path_segment_length` | **5,0 m** |
| 5 | `path_initial_angle_at_toe_*` | apagadas | `path_min/max_angle_deg`, `path_upper_angle_enabled` | −45 / 45 |
| 6 | `sa_temperature_coefficient` | **8,0** | `sa_temperature_factor` | **0,97** |

**El encargo traía tres. El inventario dio seis**, y esa es la parte que merece
recordarse: la auditoría del banco encontró los pares 1, 2 y 3 porque dos fichas
no cuadraban. Los pares 4, 5 y 6 no los encontró nadie mirando resultados;
salieron de cruzar los 77 campos de `SearchSettings` contra todo lector fuera de
`ogr_gui/`. Un defecto de este tipo **no se ve en los números**: se ve en el
registro de ajustes, y hasta ahora nadie lo había recorrido entero.

Los pares 1 y 2 diferían en el valor por defecto en un factor de **diez** y de
**dos**. El 3 coincidía —y por eso mismo era el peligroso: coincidía por
casualidad—. Los otros tres son más raros que un número mal:

- **El par 4 hacía inalcanzable la longitud de segmento automática.** El motor
  leía `path_segment_length`, donde `0` significa «automático ≈ 0,3·H». Ese `0`
  no lo escribía nadie: el valor por defecto del campo era 5,0, y el diálogo
  volcaba el número del control **sin mirar su propia casilla de «Manual»**,
  desde un `QDoubleSpinBox` cuyo rango empieza en 0,1. Así que **todo** Path
  Search corría con una longitud fija —5,0 m si el proyecto venía de un script,
  lo que enseñara el control si venía de la interfaz— y nunca con la automática,
  salvo en los tres modelos del banco que ponían el `0` a mano. Una casilla que
  no decidía nada: regla 7 en su forma pura.
- **El par 5 dejaba las dos casillas de «Initial Angle at Toe» sin efecto.** El
  motor leía otra pareja de campos, con otro signo y con otra casilla
  (`path_upper_angle_enabled`) que el diálogo no escribía nunca.
- **El par 6 no era el mismo número con dos nombres, sino dos leyes de
  enfriamiento distintas.** Y el hallazgo de verdad está en el motor: el
  recocido **ya fijaba `c = 8.0` a pelo**, con un comentario que afirmaba que el
  parámetro del usuario «influye en el enfriamiento». Era falso.
  `sa_temperature_factor` se guardaba, se recortaba entre 0,5 y 0,999 y **no se
  volvía a leer jamás**. Cablear el coeficiente visible no mueve un solo
  resultado: 8,0 es exactamente la constante que el código llevaba usando.

Y de propina, **un séptimo**, encontrado escribiendo el test de cobertura: la
casilla *inferior* del ángulo de arranque del **Slope Search**
(`initial_angle_at_toe_lower_enabled`) tampoco decidía nada — su ángulo se
pasaba estuviera marcada o no. Los 142 modelos del banco lo guardan en −45, que
es también el valor por defecto de la búsqueda, así que ponerle la puerta no
mueve nada de lo que existe hoy.

## 2 · Cómo se supo, y qué prueba cada evidencia

- **Problema 18 del banco** (Baker 1980 / Spencer 1969, r_u = 0,5):
  `construir_modelo.py` escribe `s.path_num_surfaces = 5000` y `resultados.json`
  registra `generadas = 592, validas = 505`. **505 válidas es el objetivo de
  500**, no el de 5000.
- Ese `+5` no es ruido y conviene entenderlo, porque es lo que **identifica** el
  objetivo: «Number of Surfaces» cuenta superficies **válidas** —la referencia
  lo dice y el bucle lo hace—, y al terminar, el post-proceso *Optimize
  Surfaces* añade hasta cinco refinadas. 500 + 5. Con objetivo 5000 habrían sido
  5005.
- **Problema 14** (Arai y Tagyo 1985, ej. 1): la huella publica 10 iteraciones
  de Auto Refine y se ejecutaban 5.

**Signo del error: inseguro.** Una búsqueda menos densa encuentra una superficie
crítica peor, es decir, un factor de seguridad **más alto**.

### La medida, con los dos efectos separados

El problema 18 recibe **dos** de los seis arreglos a la vez —el recuento (par 1)
y la longitud de segmento (par 4)—, así que medirlo de una pasada habría dado un
número sin causa. Cuatro corridas sobre el **mismo `modelo.ogr`**, cambiando un
ajuste cada vez. Publicado (Spencer, Baker 1980): **1,010**.

| | superficies | segmento | FoS | error | generadas | válidas |
|---|---|---|---|---|---|---|
| a) lo de ayer | 500 | 5,0 m fija | 1,044992 | **+3,47 %** | 600 | **505** |
| b) sólo el recuento | 5000 | 5,0 m fija | **1,013089** | **+0,31 %** | 6059 | **5005** |
| c) sólo el segmento | 500 | automático | 1,014658 | +0,46 % | 1206 | 505 |
| d) v0.1.103 | 5000 | automático | 1,014256 | +0,42 % | 11619 | **5005** |

**De +3,5 % a +0,4 %**, y cada uno de los dos arreglos llega ahí por su cuenta.
Y el criterio de cierre se lee en la última columna: **505 → 5005**, que son
5000 + las cinco de la optimización, la misma firma que delataba el 500.

Dos cosas que conviene decir y no maquillar:

- **(d) sale una pizca por encima de (b)** —1,014256 contra 1,013089, un
  0,12 %—. No es una regresión: son dos búsquedas aleatorias distintas
  muestreando familias de superficies distintas, y las dos están dentro del
  medio punto porcentual del valor publicado. Lo que el criterio prohíbe es
  subir respecto de **(a)**, y (b), (c) y (d) bajan tres puntos.
- **Con segmento automático se generan casi el doble de superficies para las
  mismas 5005 válidas** (11619 contra 6059). En este modelo, H = 30 m, así que
  el automático da segmentos de ~9 m contra los 5 m fijos, y un camino de
  segmentos más largos falla el hueco de salida más a menudo.

**Y la línea base del banco no era reproducible.** La ficha de la auditoría cita
1,0267 para el problema 18; el `resultados.json` guardado en 0.1.97 dice
1,039918; la reproducción controlada de hoy con los ajustes de ayer da
1,044992. Los tres números son de corridas distintas, y sólo el último tiene su
receta escrita. La conclusión de la auditoría —que la búsqueda exploraba la
décima parte— no depende de cuál sea: la sostienen las 505 válidas.

### Problema 14: el defecto era real y no era la causa

| iteraciones | bishop | spencer | GLE | janbu corr. | generadas (bishop) |
|---|---|---|---|---|---|
| 5 (lo que se ejecutaba) | 1,437293 | 1,421697 | 1,425332 | 1,449483 | 1650 |
| 10 (lo que se declaraba) | **1,437293** | **1,421697** | **1,425332** | **1,449483** | **3300** |

Los cuatro métodos, **idénticos hasta el último decimal y sobre el mismo
círculo**, con el doble de superficies evaluadas (159 s contra 368 s).

Las superficies se duplican **exactamente** —330 por iteración, C(10,2) = 45
pares × 10 círculos con las que fallan la construcción descontadas— y el factor
de seguridad **no se mueve ni en el sexto decimal**. Tiene sentido: cada
iteración se queda con el 50 % mejor de las divisiones, así que en la quinta la
ventana ya es el 3 % del talud y las cinco siguientes refinan algo que había
convergido.

Es decir: el ajuste estaba roto, arreglarlo duplica el trabajo, y el **+2,0 %**
de este problema frente al 1,409 publicado **no era esto**. La propia ficha lo
dice desde antes: sobre el círculo que publica el manual OGR da **1,408577**,
un 0,03 % del valor de referencia. La formulación acierta y la búsqueda no llega
a ese círculo, que es **D37**, no D07b. Un cierre que se hubiera medido con una
sola corrida se habría apuntado un tanto que no le corresponde.

**Y una trampa que este A/B evita, para quien mire la ficha regenerada.** Al
regenerar el problema 14, `janbu_corrected` pasa de **1,419078** —lo guardado en
0.1.97— a **1,449483**, un +2,1 %, y su círculo crítico cambia por completo:
(27,665 · 34,066) R 20,62 pasa a ser el mismo de Bishop, (25,220 · 47,661)
R 32,54. Parece el efecto de duplicar las iteraciones, y **no lo es**: en el A/B
de arriba, hecho entero sobre 0.1.103, janbu da 1,449483 con 5 iteraciones y con
10. Es la deriva de v0.1.98 a v0.1.102 sobre una ficha grabada en 0.1.97, con
v0.1.100 —base de dovela de secante a cuerda— como sospechoso principal.

Medir contra una corrida guardada cinco versiones atrás confunde cinco cambios
con uno. Es la razón de que la tabla de arriba tenga las dos filas medidas hoy.

## 3 · Cuál de los dos sobrevive, y por qué

El campo que se ve. No es una preferencia estética: es el único que **significa
lo mismo que el control que el usuario maneja**. El panel de la referencia lo
fija campo a campo —Path Search «Number of Surfaces: 5000», Auto Refine
«Number of Iterations: 10», «Segment Length» con la casilla apagada y el valor
en gris—, y `path_num_paths` o `auto_refine_iterations` son conceptos internos
de OGR que no existen en ningún sitio que el usuario pueda ver.

Antes de colapsar el par 1 había que comprobar que la equivalencia es directa
—que una «path» produce **una** superficie y no varias—, porque si no lo fuera,
colapsar cambiaría el significado del número. Lo es: el bucle corta en
`while result.valid_count < num_surfaces`, contando superficies válidas, y la
documentación de la referencia define su control con esas mismas palabras
(«the total number of valid surfaces generated… invalid surfaces are discarded
and are NOT included in this number»).

Lo que **no** valía era dejar los dos campos y sincronizarlos en más sitios: eso
multiplica las ocasiones de que se separen.

## 4 · El convenio de ángulos, que sí es una decisión

Los pares 1, 2, 3, 4 y 6 son fontanería: un nombre por otro. El 5 no, porque los
dos miembros estaban en **marcos distintos**.

La referencia es explícita: los límites del *Initial Angle at Toe* son ángulos
**absolutos**, medidos en sentido antihorario desde el eje +x, y añade que un
límite superior de 30° para una rotura derecha-izquierda «equivale a» 150° para
una izquierda-derecha. El generador de OGR, en cambio, trabaja en un marco
**pie→cresta** a propósito, y ese comentario del código documenta un error que
ya costó caro (un 1,60 donde tocaba 0,88, con el 97 % de los caminos
descartados).

Decisión: **el ajuste guarda el ángulo absoluto** —lo que significa el control
que ve el usuario— y la conversión al marco del motor vive en **una sola
función**, `toe_frame_angle_deg`, cuyo test no es una captura sino una
identidad: la equivalencia 30 ↔ 150 que publica la referencia **es** esa
reflexión, porque 180 − 150 = 30.

Los ángulos guardados en el marco viejo **no se convierten al migrar**, y se
dice: la conversión necesita la dirección de rotura, que no está en el bloque de
ajustes. Ninguno de los 142 modelos del banco los tiene fuera de su valor por
defecto, así que no hay nada que convertir hoy; el día que lo haya, el análisis
lo avisa en vez de adivinar.

## 5 · Qué gana cuando un `.ogr` trae los dos nombres y discrepan

**El que se aparta de su valor por defecto**, porque es el único de los dos que
demuestra intención. Es el razonamiento de `AdvancedSettings.from_dict` leído al
revés: un valor que nunca llegó a un cálculo no expresa intención que preservar,
y uno que difiere de su defecto sí.

La regla no es teórica; sin ella se rompen tres modelos del banco:

| Caso | visible | legacy | Se honra |
|---|---|---|---|
| Problema 18 (script pone el visible) | 5000 | 500 *(defecto)* | **5000** |
| Problemas 39, 42 y 62 (script pone el legacy) | 5000 *(defecto)* | 300 / 2000 | **300 / 2000** |
| Guardado desde la interfaz | 800 | 800 | 800 |
| Formato viejo, sólo el legacy | — | 250 | 250 |

«Gana siempre el visible» habría subido las búsquedas de los problemas 39, 42 y
62 de 300 a 5000 **en silencio**: el mismo defecto apuntando al otro lado.

Además, `SearchSettings.from_dict` deja de ser un `SearchSettings(**data)` a
pelo, que **reventaba con `TypeError`** ante cualquier clave que dejara de ser
campo — y los 142 modelos del banco y los 6 de `validacion/casos/` las traen.

## 6 · Y que nadie pueda volver a escribir en un campo que no existe

Un dataclass acepta `s.path_num_paths = 300` sin rechistar y el valor no llega a
ningún sitio: **este mismo defecto, reintroducido desde fuera**. Tres
`construir_modelo.py` del banco hacen exactamente eso. Ahora
`check_analysis_settings` —que ya existía para negarse antes que devolver un
número plausible— **rechaza el análisis** y nombra el campo que sí se lee.

## 7 · El test que exigía que el bug siguiera existiendo

`tests/test_surface_options_v112.py` tenía una clase llamada
`TestLegacyFieldsPreserved` que **obligaba** a que los trece nombres sombra
existieran, con este docstring: *«These are read by the solver classes»*. Era
verdad a medias, y esa media verdad es justo la trampa: los leía el solver
mientras la interfaz enseñaba y guardaba otro campo con el mismo significado.

Ahora la clase se llama `TestShadowFieldsAreGone` y el invariante corre al
revés. Si uno de esos nombres vuelve, vuelve el fallo.

## 8 · Lo que se añade para que no pase una cuarta vez

`tests/test_settings_coverage_v1103.py` recorre `SearchSettings` y exige que
**cada campo tenga un lector fuera de `ogr_gui/`**. Los que aún no lo tienen van
en un inventario **congelado** —conjunto exacto, no lista de permisos— con el
defecto dueño de cada uno: trece `optimize_*` son **D08**,
`auto_refine_num_vertices_along_surface` es **D32**, y
`sa_num_fos_compared_before_stopping` y `block_multiple_groups` son **D07c**,
abierto hoy. Un campo nuevo sin lector falla en el acto; cerrar un defecto
obliga a bajar el inventario en vez de dejarlo crecer.

Un test así habría cazado A9-1, A37-1 y D07b, los tres.

## 9 · Lo que esto le cambia al usuario

- **Todo Auto Refine guardado pasa de 5 a 10 iteraciones**: el doble de trabajo
  y un factor de seguridad igual o menor — en el problema 14, exactamente igual,
  y 209 segundos más caro.
- **Todo Path Search por defecto pasa de 500 a 5000 superficies** y de segmentos
  de 5,0 m fijos a la longitud automática: diez veces el trabajo, y superficies
  de otra forma.
- El recocido no cambia: 8,0 era ya la constante del código.

Los factores guardados **se moverán**, y sólo pueden bajar o quedarse: es lo que
pasa cuando una búsqueda por fin hace lo que declaraba.

## 10 · Y una lectura que hay que rehacer antes de acusar a nadie

La anomalía **A19-1** (defecto **D21**) dice que el Path Search «con 5000
superficies se queda en 1,649 mientras una rejilla circular encuentra 1,454».
Esa medida se tomó sobre una búsqueda que exploraba **500**, y con segmentos
fijos. No explica por sí sola un 13 %, pero **hay que volver a medirla** antes
de seguir acusando al generador.

---

## Archivos

- `ogr_core/project/settings.py` — trece campos fuera; `_SHADOW_FIELDS` como
  registro único de lo retirado y su sustituto; `SearchSettings.from_dict` con
  la migración y las notas de lo que no se pudo convertir.
- `ogr_slip2d/analysis_runner.py` — las seis ramas leen el campo visible;
  `check_analysis_settings` rechaza un nombre retirado; `settings_warnings`
  saca las notas de migración.
- `ogr_slip2d/search.py` — `PathSearch.num_surfaces` (con `num_paths` como
  alias), `toe_frame_angle_deg`, `SimulatedAnnealingSearch.temperature_coefficient`
  cableado al `c` del programa de enfriamiento.
- `ogr_gui/dialogs/grid_dialogs.py` — fuera los cuatro bloques «Map to legacy».
- `ogr_cli/__main__.py` — `--samples` escribe el campo visible.
- `tests/test_search_effort_v1103.py`, `tests/test_settings_coverage_v1103.py` —
  nuevos.
