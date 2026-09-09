# OGR Slip2D v0.1.155 — D62: cinco silencios, y ninguno era el que decía la ficha

El encargo P-D62 pedía contar cuántos soportes colocados no contribuyen a
la superficie que el análisis reporta, y por cuál de **cinco** razones.
Contarlos era lo correcto. Casi todo lo demás que la ficha daba por
sabido resultó no serlo, y medirlo antes de escribir es lo que ha dado la
versión.

---

## 1 · Las tres premisas del encargo que se cayeron

**(1) No son cinco `continue`, son cuatro — y el quinto se mudó, no
desapareció.** La ficha enumera «tipo desconocido» como uno de los cinco
`continue` de `compute_support_effects`. Ya no lo es: **D66 (v0.1.149)**
cambió el bucle a `for support, stype in support_type_pairs(project)`, y
`support.py:393` descarta ahí los soportes cuya clase no resuelve
(`if st is not None`). El soporte **no llega al bucle**. Sigue siendo
silencioso —el defecto es real— pero se cuenta comparando la lista de
colocados con la de pares resueltos, no con un contador dentro del bucle.
Lo confirma por otra vía `CHANGELOG_v0.1.138.md:162-167`, que enumeraba
los cinco y es anterior a D66.

**(2) Las líneas del encargo ya no existen.** Dice «842, 851, 859, 880,
907»; en HEAD eran 837, 846, 866 y 893. Y el `awk` que la ficha propone
como comprobación cuenta además el `continue` de `_bond_profiles:786`,
que **no oculta ningún soporte**: sólo salta los tipos sin perfil de
adherencia.

**(3) La premisa del umbral es falsa, y ésta es la que cambia el
diseño.** El encargo teme «una pared de avisos» en los problemas 87–94
porque serían «quince láminas de las que sólo unas pocas cortan cada
círculo». Contando cuántas cortan el círculo crítico que cada
`resultados.json` publica, en las 24 filas método-modelo:

| Modelo | Bishop | Spencer | GLE |
|---|---|---|---|
| 087 | 1 mudo | 1 | 0 |
| 088 | 7 | 7 | 7 |
| 089 | 8 | 8 | 8 |
| 090 | 1 | 0 | 0 |
| **091** | 1 | **13** | **12** |
| 092 | 1 | 0 | 0 |
| 093 | 1 | 1 | 1 |
| 094 | 1 | 1 | 0 |

La mayoría son 0 ó 1, no «unas pocas». **No hacía falta ningún umbral de
silencio**: la agregación *es* el umbral. Una línea por método es la
forma que tienen todas las demás notas; la pared habría sido una línea
por soporte.

Comprobado después con el motor, no sólo con geometría: el 87 con Bishop
da **1 de 15** y el 91 con Spencer da **13 de 15**, exactamente lo que la
cuenta geométrica anticipaba.

**Y el hallazgo que sale de ahí**: en el problema 91, **Spencer reporta
su factor apoyado en 2 láminas de 15** mientras Bishop usa 14. Los dos
números se publican uno al lado del otro en la comparativa y nada decía
que descansan sobre modelos de refuerzo distintos. Es el escenario que
D62 describe, en un modelo publicado del banco, y hasta hoy era invisible.

---

## 2 · La sexta vía, que el encargo no trae y es la peor

Las cinco de la ficha dejan fuera **un** soporte cada una.
`resolve_support_terms:289` deja fuera **todos**:

```python
    try:
        effects = compute_support_effects(project, surface, slices)
    except Exception:  # noqa: BLE001
        return _EMPTY_TERMS
```

Cualquier excepción —de un tipo, de un plugin, de un perfil— y la
superficie se tasa sin ningún refuerzo, con `present=False`, en todos los
métodos y todas las superficies. El usuario con nueve bulones obtiene el
talud sin reforzar y ninguna señal.

Se **diagnostica** aquí y **no se corrige**: estrechar ese `except` es
defecto aparte y D62 no puede mover un número. La nota lo dice y nombra
la clase de la excepción.

---

## 3 · Lo que se ha hecho

`compute_support_effects` gana un parámetro **keyword-only**
`reasons: Optional[list] = None` y anota `(id del soporte, razón)` en cada
punto de abandono. La forma no se ha inventado: es exactamente la de
`slice_surface` (`slicer.py:1333`), con sus constantes documentadas con
bloques `#:`, y su consumidor en `search.py` ya paga `reasons=[]` **por
superficie de prueba**, una ruta mucho más caliente que ésta.

**Coste, contado y no cronometrado** (la regla de AGENTS.md cuando el A/B
no resuelve): con `reasons=None` se añade una comparación `is not None`
por soporte, y sólo en las ramas que ya se abandonaban. Nada para un
soporte que contribuye. Frente a los ~2,5 ms que cuesta una superficie,
no es medible, y no se ha intentado medirlo.

Recogerlas ahí y no rederivarlas en la nota es el punto: la regla que
decide y la que cuenta tienen que ser el mismo código, o una de las dos
se queda obsoleta —lo que `support_notes.py:11-15` ya tiene escrito.

`uncontributing_support_notes(project, result)` compone **una** línea
agregada sobre la superficie que la corrida reporta, con la forma de
`reversed_support_notes`: saca `surface` y `slices` del propio resultado,
así que no recalcula ninguna búsqueda. Se engancha en `analysis_runner`
detrás de la nota de D40 —que es la afirmación más específica, sobre un
soporte que **sí** cruza— y como frase separada, porque el encargo
prohíbe mezclar dos diagnósticos con criterios de ruido distintos.

**Desviación del plan, consciente**: las razones (3) y (4) son hechos de
modelo y el plan las mandaba a `support_notes.py` como notas aparte. Van
en la misma nota agregada, porque el criterio de cierre pide *una* nota
con el desglose de las cinco razones, y separarlas habría dicho lo mismo
dos veces. El comportamiento observable es el que el plan pedía: no hay
umbral, así que esas dos siempre avisan.

### La razón (2) es inalcanzable, y se dice en vez de fingirla

`_slip_polyline` se construye a partir del **mismo** `s_list` que luego se
recorre buscando índice, y el slicer rechaza todo intervalo de anchura no
positiva: las dovelas son contiguas y monótonas en x, así que todo punto
de esa polilínea cae dentro de alguna. `slice_idx` **nunca** es `None`.
La guarda se conserva —es real y no cuesta nada—, su docstring lo dice, y
su test la ejercita con una lista de dovelas **agujereada a mano**, con un
comentario diciendo que ningún modelo puede producirla.

### Tres subcadenas que la redacción no podía usar

El banco decide si D40 sigue cerrado **leyendo el texto de los avisos**:
`verificar_cierres.py:729` acepta un aviso como la nota de D40 cuando
contiene `stable` y `head` a la vez. Y hay dos más: `edge of the search
grid` (`:1205`) y `path_optimize` (`:1327`). Cualquiera de las tres
habría puesto un cierre verde en `RE-ENUNCIADO` sin que el motor hubiera
cambiado. La prohibición es más ancha de lo que parece —`unstable`
contiene `stable`, `ahead` contiene `head`— y hay un test que lo
comprueba sobre cada nota que el módulo produce, más el recíproco: que la
nota de D40 sigue llevando las dos, para que los dos canales sigan
distinguiéndose.

---

## 4 · La otra mitad: una nota que nadie podía leer

`run_analysis` devolvía la lista de notas, la ventana la guardaba en
`last_compute_warnings`… y mostraba `[0]` en la barra de estado quince
segundos. **El resto no lo leía nadie** en todo el repositorio. La
interfaz de terminal las imprime todas desde v0.1.77, así que los dos
frontales discrepaban sobre lo que había dicho la misma corrida, y el
gráfico era el lado que perdía información. Con doce notas posibles, cuál
sobrevivía lo decidía el orden en que se anexan.

- **`AnalysisNotesPanel`** (`ogr_gui/dialogs/analysis_notes_panel.py`),
  no modal, calcado de `DxfProblemsPanel`: agrupa por método, pone
  primero las de modelo, y tiene *Copiar todo* porque una nota que hay que
  recopiar a mano deja de citarse.
- **Acción `Analysis Notes...`** en el menú **Analysis**, detrás de
  *Interpret*. Sin eso sería un módulo invisible, que es la regla 3.
- **La barra de estado** sigue enseñando la primera, pero ya no **como si
  fuera la única**: dice cuántas se está callando y dónde leerlas.
- **`last_compute_warnings` se inicializa en `__init__`** —no existía
  hasta el primer cálculo, así que preguntar antes daba `AttributeError`—
  y **se limpia** en *New* y en *Load Demo*, que limpiaban los resultados
  pero no las notas: las del proyecto anterior describían al nuevo.

### i18n: el motor no lleva `tr()`, y no es un olvido

Medido: ni `reversed_support_notes`, ni `support_identity_notes`, ni
`daylight_tangent_note`, ni `m_alpha_margin_note` tienen entrada en
`ogr_gui/i18n/__init__.py`; `test_i18n_coverage_v141.py:41` sólo escanea
`ogr_gui/`; y `ogr_slip2d` **no importa `ogr_gui` en ningún sitio**, así
que no podría llamar a `tr()` aunque quisiera. Una entrada para un
f-string con `%d` sería además peso muerto y empujaría contra
`test_no_lazy_identity_translations`. La regla 2 gobierna el texto de los
**widgets**, y ahí sí se ha cumplido: las ocho cadenas nuevas del panel,
de la acción y de la barra de estado llevan `tr()` y su entrada española,
con terminología geotécnica castellana. Queda escrito aquí para que no se
vuelva a discutir.

---

## 5 · El test — `tests/test_support_silence_v1155.py`

27 comprobaciones. Un modelo mínimo por razón, cada uno afirmando la
**lista entera** de razones —un modelo que disparase la suya por otra vía
pasaría una comprobación más floja—, más los casos que callan.

Los dos anclajes numéricos son identidades, no capturas:

- un proyecto con un soporte mudo da el mismo factor, **dígito a dígito**,
  que el mismo proyecto con ese soporte borrado. Ésa es la prueba de que
  la nota describe un cero real y no añade término a ninguna ecuación;
- pedir las razones no cambia lo que la función devuelve: `reasons=None` y
  `reasons=[]` dan los mismos efectos.

**Con 0.1.154 fallan 20 de las 27.** Diecinueve por símbolo inexistente o
firma vieja, y una **por comportamiento**:
`test_the_note_arrives_prefixed_with_its_method` recibe `[]` donde ahora
recibe la nota — que es el defecto, exactamente.

---

## 6 · No regresión, medida

| Qué | Resultado |
|---|---|
| Suite completa, sin filtrar | **3255 / 3255** (3228 + los 27 nuevos) |
| A/B de los ocho muros 87–94, código nuevo contra 0.1.154 | **120 valores comparados, 0 movidos**; las dos salidas idénticas **byte a byte** |
| `verificar_cierres.py D40` | **SE SOSTIENE**, y no dispara en ningún modelo |
| Las 18 notas que D62 produce en 87–94, pasadas por el criterio literal de `d40` | **ninguna** lo dispara, y ninguna lleva las subcadenas reservadas |
| Con 0.1.154, el archivo de test nuevo | 20 de 27 fallan; 19 por símbolo o firma, **1 por comportamiento** |

El A/B se hizo contra el **código**, no contra los `resultados*.json` del
banco, y a propósito: esos archivos están congelados en **0.1.148**, así
que regenerarlos habría mezclado siete versiones de cambios ajenos con
éste y no habría dicho nada sobre D62. Lo que se compara son los mismos
ocho modelos y los mismos veinticuatro círculos publicados, evaluados con
el código de 0.1.154 y con el de 0.1.155: factor de seguridad y los
cuatro términos de soporte (`present`, activo, pasivo y presión normal).
Regenerar el banco a 0.1.155 es trabajo aparte, y arrastra la deriva de
D78.

**Lo que sí cambia a propósito**: `ejecutar_caso.py:401` escribe
`"avisos": list(salida.warnings)` en cada `resultados*.json`. Las filas
con soportes ganan una línea. Ningún factor se mueve; el JSON no es
idéntico byte a byte, y eso es el efecto pretendido, no una regresión.
`generar_comparativa.py` **no lee ningún campo de notas** —sólo
`metodos[mid].fos`, `fos_optimizado`, `fos_sin_corrida` y
`fos_en_circulo_publicado`—, así que la comparativa no puede moverse
salvo que se mueva un factor.

---

## 7 · Defectos nuevos, reportados y NO corregidos

Serie D del banco, continuando desde D93:

| # | Qué | Estado |
|---|---|---|
| **D94** | `resolve_support_terms:289` traga cualquier excepción y devuelve `_EMPTY_TERMS`: **todos** los soportes desaparecen a la vez, en todos los métodos, con `present=False`. Peor que las cinco vías de D62 juntas | **Diagnosticado** aquí (la nota lo dice y nombra la excepción); el `except` no se toca |
| **D95** | Un perfil de adherencia que no se puede construir (`_bond_profiles:789`) degrada la fuerza a su envolvente de tensión nula en silencio, y eso **sí** mueve el número. Además, `PileMicropile` en modo Ito-Matsui devuelve **exactamente 0,0** sin perfil, así que aflora como la razón (5) y no como lo que es | ABIERTO |
| **D96** | La interfaz calcula `factor_report` y lo tira: `main_window.py:145` lo guarda y **nadie lo lee**. La CLI sí lo imprime. Los coeficientes parciales ya estuvieron dos versiones sin aplicarse (v0.1.52→57); ahora se aplican y su informe no se ve | ABIERTO |
| **D97** | `support_integration.py:862` compara cotas con **igualdad exacta de floats** en un proyecto cuya regla es que las tolerancias geométricas van relativas al tamaño del modelo. Un muro dibujado 1e-15 fuera de nivel **no** toma el rechazo: mide su diagrama desde un extremo elegido por ruido de redondeo, que es el «número plausible y erróneo» que el propio comentario dice evitar. `reversed_support_notes:622` ya lo hace bien (`tol = 1e-6 * length`) | ABIERTO |
| **D98** | `support_integration.py:886` traga la excepción de `shear_at`: el soporte pierde la mitad de su capacidad declarada y **sigue contribuyendo**, así que la nota de D62 no dice nada de él | ABIERTO |

**D97 no se corrige aquí a propósito**: hacer la comparación relativa
cambia qué soportes toman el rechazo, y eso mueve números. Es defecto
nuevo con su propia evidencia, no un remate de éste.

---

© 2026 Samuel Sáez López — UPCT — AGPL-3.0-or-later
