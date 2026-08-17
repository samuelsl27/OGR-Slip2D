# OGR Slip2D v0.1.89 — nueve modelos de test sin suelo bajo el pie tapaban dos defectos del solver

Esta versión iba a ser fontanería: quitar de cinco archivos de test un
contorno que no encierra suelo, y explicar por qué un diagnóstico fuera del
runner no reproducía un fallo. Los cinco archivos eran **nueve**, y el
contorno no era una fealdad: era un **tapón**.

Sin suelo bajo el pie, **ninguna superficie podía hundirse**, así que las
búsquedas no circulares no generaban nunca el caso difícil. Al poner el
cimiento aparecieron dos defectos reales y un tercero que se deja reportado.

| | antes | ahora | circular |
|---|---|---|---|
| Block Search semilla 7 | 0,6513 | **1,1362** | 1,1239 |
| Block Search semilla 42 | 1,0707 | **1,1574** | |
| Block Search semilla 100 | 0,8212 | **1,1313** | |
| Block Search semilla 2024 | 0,8978 | **1,1647** | |
| Block Search semilla 55 | 1,0339 | **1,1327** | |
| Simulated Annealing | 0,5000 | 1,187 → ver §5 | |

De errático y por debajo de la unidad, a consistente alrededor del mínimo
circular.

---

## 1 · El predeterminado de m-alpha se contradecía a sí mismo

`BaseSearch.check_m_alpha` valía `False`. `ProjectSettings.advanced.check_m_alpha`
vale `True` desde v0.1.84. **El mismo modelo daba dos respuestas según la
puerta de entrada**: por `build_search` —interfaz, CLI, casos de validación— la
comprobación corría; construyendo una búsqueda directamente —todos los tests,
`examples/`, cualquier script— no.

Eso es peor que un ajuste muerto, que es lo que la regla 7 persigue: un ajuste
muerto no hace nada, y éste hacía **dos cosas distintas** sin decirlo.

Lo que tapaba: con el cimiento, SA devolvía **0,500** y Block Search **0,651**
en un talud estable. Las dos superficies cerraban con un tramo casi vertical
(α = −72°, −82°), donde `m_α = cosα·(1 + tanα·tanφ/F)` se vuelve **negativo** y
la formulación de Bishop divide por él. Con la comprobación activada: 1,187 y
1,120, y las superficies **siguen** bajando 9,5 m por debajo del pie. La
profundidad nunca fue el problema; el tramo vertical de cierre sí.

Físicamente tenía que ser así: a 10 m de profundidad σ ≈ γz = 180 kPa, luego la
fricción aporta 180·tan20° ≈ 65 kPa contra 8 kPa de cohesión. El tramo profundo
es unas **nueve veces más resistente**, así que una superficie profunda no puede
ser el doble de crítica que el círculo de pie.

Predeterminado ahora `True` en `BaseSearch` y en las seis búsquedas, con un
test de que **coincide** con el de `ProjectSettings` para que no vuelvan a
separarse.

`reject_tensile` se queda en `False`, y la asimetría es deliberada: la
referencia permite tracciones en la base salvo que el usuario las excluya,
mientras que sus informes **sí** filtran por m-alpha por defecto y cuentan los
rechazos como error −112.

### Lo que más incomoda de este hallazgo

El comentario que hay encima de esa línea, escrito en **v0.1.24**, describe el
mecanismo con estas palabras:

> «Non-circular searches can generate them (e.g. a deep wedge closed by a
> near-vertical rising segment), so this filter is available for all searches.
> **Default OFF to preserve existing results; recommended ON** for non-circular
> searches.»

La recomendación estaba escrita hace sesenta y cinco versiones. Los «existing
results» que preservaba sólo eran estables porque ningún modelo de test tenía
suelo donde hundirse. La geometría degenerada y el predeterminado equivocado se
sostenían el uno al otro.

## 2 · El rebanador no cortaba en los vértices de la propia superficie

v0.1.66 estableció el principio para los materiales: *«dónde la superficie
entra en otra capa es un corte obligatorio: la base de una dovela pertenece a
un material o a otro, nunca a una mezcla»*. No se aplicó a la geometría de la
propia superficie, y vale exactamente igual: **la base de una dovela pertenece
a un tramo de la superficie o a otro, nunca a una mezcla.**

Lo que costó, con la semilla 100 de Block Search:

```
(33.46, 2.08) (35.94, 0.09) (36.08, -4.82) (51.32, 4.90) (58.74, 12.00)
                    └──── Δx = 0.14 m, Δy = -4.91 m → -88.4° ────┘
```

Un escalón casi vertical de **0,14 m de ancho**, con dovelas de **1,26 m**. El
escalón cabía dentro de una dovela, así que ningún ángulo de base era
pronunciado, así que m-alpha no tenía nada que rechazar: su mínimo era **0,50**
contra un límite de 0,2. **La geometría no estaba mal, estaba sin resolver.**

Inerte para círculos, que no tienen vértices — Ej_1, Ej_2 y los cinco casos
publicados no se pueden mover, y no se movieron.

## 3 · Nueve contornos, no cinco

`docs/PENDIENTES.md` listaba cinco archivos. Eran siete sitios en cinco
archivos **más** dos que no figuraban: `test_supports_all_methods_v164.py` y
`test_slice_cuts_v166.py`. Y `test_noncircular_v115.py` tenía tres, no uno.

Es el mismo fallo que `AGENTS.md` documenta para la lista de sitios donde sube
la versión —«una lista en un documento solo vale lo que valga la atención de
quien la lee»— repetido dentro del propio documento de pendientes.

Por eso el orden de trabajo se invirtió: **primero el detector, y que él haga
el inventario**. `ogr_core.geometry.zero_thickness_spans()` mide envolvente
superior menos inferior —no la lista de vértices, que es justo el razonamiento
que tuvo mal la superficie del terreno durante ochenta versiones— y devuelve
los tramos de abscisa donde el contorno no encierra nada. Sobre el contorno
histórico da `[0, 30]`; sobre el corregido, nada.

Inventario tomado ejecutando la suite entera con `Project.add_boundary`
instrumentado: **ninguna frontera degenerada** en las 1892 llamadas. Ese
inventario no se puede quedar obsoleto.

Lleva también `lower_y_at()`, que necesita implementación propia y no un cambio
de signo de `upper_y_at()`: en una cara vertical una envolvente quiere el
extremo de abajo y la otra el de arriba.

**Lo que NO hace**: impedir que un archivo nuevo reintroduzca el contorno. Haría
falta que todos los modelos de test pasaran por una fábrica única, que es más
cambio del que cabe aquí.

## 4 · Por qué el diagnóstico fuera del runner no reproducía el fallo

Cerrado. No era estado global: es el instalable editable, y es determinista.

1. `python C:\otro\sitio\script.py` pone en `sys.path[0]` **el directorio del
   script**, no el de trabajo. Éste es el paso que sorprende: hacer `cd` a un
   árbol no pone ese árbol en la ruta.
2. Ahí no hay ningún `ogr_*`, así que `PathFinder` (posición 2 de
   `sys.meta_path`) no encuentra nada.
3. Responde `_EditableFinder` (posición 3), que instaló `pip install -e .`, y
   **resuelve todo `ogr_*` a una ruta absoluta fija**.

Comprobado con un señuelo: con el `cwd` puesto en un directorio que contenía su
propio `ogr_slip2d`, el import siguió viniendo del árbol instalado y el
`MARKER` del señuelo no apareció nunca.

Así que un script guardado fuera del repositorio importa el árbol principal sea
cual sea el árbol al que te hayas cambiado o el commit que hayas sacado. Por eso
daba lo mismo «en el árbol de trabajo» y «en HEAD»: ejecutaba el mismo código.

`tests/_runner.py` abre ahora cada corrida con una línea de procedencia y
**se niega a ejecutar** si algún `ogr_*` se resuelve fuera de su propio
repositorio:

```
tree: C:\Samuel\OpenGeoRock_Slip2d\OGR-Slip2D  @ 7075819  (5 ogr packages)
```

La resolución usa `find_spec`, que pasa por los mismos buscadores que un import
pero **no ejecuta nada** — importar los cinco paquetes para preguntarles su
`__file__` ejecutaría el código de módulo de medio proyecto antes del primer
test, que es la fuga de estado que la regla 5 existe para evitar. Hay un test
que lo comprueba a nivel de fuente, para que nadie lo «simplifique» a un import.

**Y me lo hice a mí mismo mientras tanto.** La primera suite de v0.1.88 dio
1860/1861 con un fallo de versión, `('0.1.87', '0.1.88')`. La lectura inmediata
—«hay un octavo sitio de versión»— era falsa: `misc_dialogs.py` **deriva**
`VERSION` de `pyproject.toml` al importarse. Lo que pasó es que edité el árbol
con la suite corriendo. La misma clase de error, a los diez minutos de
diagnosticarla.

## 5 · Lo que queda abierto, medido y sin corregir

Tres cosas, todas en `docs/PENDIENTES.md` con sus tablas.

**SA converge peor que un círculo.** Devuelve 1,6564 donde el círculo da 1,1239,
y eso no puede ser: los círculos están en su espacio de búsqueda. Además
`generation_steps` satura en ~260 evaluaciones —1000, 3000 y 10 000 dan
idéntico resultado, que es la regla 7— y no es monótono: 50 pasos dan 1,749 y
300 dan 2,185, peor.

**GLE bajo SA no devuelve nada. Regresión de esta versión, aceptada a
sabiendas.** El cambio del rebanador deja a GLE combinado con Simulated
Annealing con **0 superficies válidas** en las semillas 0 a 7 y con 18, 27, 36,
54 y 72 dovelas. Se aceptó porque el mismo cambio arregla un **número
equivocado** —Block Search devolviendo 0,65-0,82 en un talud estable—, y un
número equivocado que un usuario se creería es peor que una ausencia visible de
número. Está acotado: GLE bajo Block Search da 10-17 válidas y bajo Grid Search
circular está intacto. **Por qué, no se sabe**: las anchuras de dovela no
degeneran y no cambia con el número de dovelas. Hay un test que **afirma el
fallo**, de modo que el día que GLE funcione la suite se pondrá roja y alguien
tendrá que venir a borrarlo.

**La auditoría por círculo** (`docs/audits/percircle_fos_v189.md`), hecha con
los 67 837 valores de referencia de los `.s01`: error mediano por debajo del
0,08 % en las catorce combinaciones método × modelo, y dos divergencias que sólo
se ven en la población — masas deslizantes distintas en Ej_2 (6 círculos, con
los cortes contados) y una cola sin explicar en Ej_1 (49 círculos, donde la
hipótesis de las masas **falla**: sólo hay dos cortes).

---

## Números que se movieron, y por qué

Ninguno se retocó en silencio.

- `test_checks_v132.py::test_disabled_by_default` → renombrado a
  `test_the_defaults_are_asymmetric_on_purpose`: afirmaba que los dos chequeos
  estaban apagados, lo que había dejado de ser cierto del programa entero.
  Añadido `test_the_class_default_matches_the_project_default` para que no
  vuelvan a separarse.
- `test_checks_v132.py::test_critical_skips_inadmissible` → el caso base pide
  `check_m_alpha=False` explícitamente. Se apoyaba en el predeterminado, así que
  al cambiarlo las dos corridas pasaron a ser la misma y el test no comparaba
  nada. **Un test de comparación no puede tomar ninguno de los dos lados de un
  predeterminado.**
- `test_project_settings_wiring_v174.py` → dos casos, ídem.
- `test_checks_v132.py::test_tension_only_on_the_degenerate_surface` → afirmaba
  `bad == [14]`, un índice de dovela, y salen dos porque el tramo patológico
  ahora se resuelve entero. **No se actualizó el índice**: se cambió el aserto
  para que afirme la física —que las dovelas señaladas son exactamente las de
  base a más de 70°—, que es lo que su propio docstring decía comprobar. Habría
  sobrevivido al cambio, y es mejor test.
- `test_postprocess_v122.py` → el umbral fijo de −5 % de `e_max` estaba
  calibrado sobre una discretización que no resolvía la superficie. Con el
  rebanador arreglado, refinando a 18, 27, 36, 54, 72 y 108 dovelas los valores
  **convergen** a −1,60 % (degenerada) y −0,58 % (sana), estables desde 36. Se
  afirma ahora la **separación** —varias veces más tracción, en más interfaces—
  en vez de una constante elegida para caer entre dos números medidos, que es el
  ajuste de parámetros que la regla 1 prohíbe.
- `test_sa_autorefine_v117.py::test_finds_physical_fos` → renombrado a
  `test_does_not_return_a_spurious_sub_unity_fos`. Conserva la guarda para la
  que se escribió —el bug de v0.1.16— y **deja de afirmar cota superior**, que
  sólo pasaría por suerte mientras el pendiente de SA siga abierto.

## Archivos

- `ogr_slip2d/search.py` — `check_m_alpha` predeterminado a `True` en
  `BaseSearch` y en las seis búsquedas.
- `ogr_slip2d/slicer.py` — cortes de dovela en los vértices de la superficie.
- `ogr_core/geometry/ground.py` — `lower_y_at()` y `zero_thickness_spans()`.
- `ogr_core/geometry/__init__.py` — las dos exportadas.
- `tests/_runner.py` — procedencia y guardián de árbol.
- Nueve contornos con cimiento de 10 m, en siete archivos de test.
- `tests/test_degenerate_boundary_v189.py`, `tests/test_runner_provenance_v189.py`
  — nuevos.
- `docs/audits/percircle_fos_v189.md` — nuevo.
- `docs/PENDIENTES.md` — se cierra el punto 4; se abren tres.

## Probado

- Suite entera sin argumentos.
- Inventario de contornos degenerados sobre la suite completa: ninguno.
- Block Search, cinco semillas, contra el mínimo circular del mismo modelo.
- Convergencia de la tracción interdovela en seis refinamientos.
- Alcance de la regresión de GLE: 8 semillas × 5 recuentos de dovelas, y las
  otras dos búsquedas.

## Sin probar

- Por qué GLE falla bajo SA (§5). Es lo primero de la próxima versión.
