# OGR Slip2D v0.1.152

**El encargo de D56 pedía que un fallo de convergencia saliera «como fallo,
con su razón». Ya salía así: las catorce rutas que devolvían `nan` o `inf`
ponían las tres cosas —`converged=False`, un `error_message` y el
no-número— y `is_valid` ya exigía `math.isfinite`. Lo que faltaba no era la
razón: era que el campo `fos` dejara de llevar el no-número como carga, y
que la disciplina de mirar `is_valid` dejara de ser un convenio.** Desde
esta versión un `LEMResult` con un no-número es imposible de construir, y un
fallo sin razón también. La medición encontró de paso un tercer caso que el
encargo no traía y que es peor que el `nan`.

---

## Lo que había

La cadena que el defecto documenta, medida en el problema 79 del banco entre
0.1.130 y 0.1.147: método → `resultados_modelo_2.json` → la comparativa → la
ficha. Diecisiete versiones, una fila que pasó de `REVISAR` a `DISCREPANCIA`,
y lo que la paró fue un auditor humano preguntándose por qué un caso daba
`nan` y el otro no.

El síntoma del 79 ya estaba curado —era del banco: la cara del talud tenía
medio pie de más— así que el caso hubo que reconstruirlo. La condición es
**una masa deslizante simétrica respecto de la vertical del centro**: un
círculo centrado sobre terreno llano corta una lente cuyas dovelas se
emparejan con su espejo, peso igual y ángulo de base opuesto, así que
Σ W·sin α se anula y no hay momento motor del que el factor sea el cociente.

Sobre esa masa, **los nueve métodos daban seis respuestas distintas**
(0.1.151):

| Métodos | Respuesta |
|---|---|
| Bishop, Janbu simplificado, Janbu corregido, Fellenius | `inf`, «Zero driving moment» |
| Spencer, GLE | `nan`, «all sampled λ diverged» |
| Corps #1, Corps #2, Lowe-Karafiath | **`5.0`, y el motivo vacío** |

Σ W·sin α = 1,49e-13 frente a un término máximo de 51,1 — residuo relativo
2,9e-15, doce órdenes de magnitud dentro de la guarda de `1e-9`. El caso se
alcanza a propósito, no por suerte del redondeo.

## Lo que la medición encontró, y no estaba en el encargo

### 1 · El 5,0 de los tres métodos de inclinación prescrita

Es **el techo de su propia rejilla de muestreo** (`modified_swedish.py`,
`grid = [0.2 … 5.0]`), devuelto por el fallback de menor residuo cuando
ninguna orientación acorrala una raíz. Salía con `converged=False` y
`error_message` **vacío**.

Es la peor de las tres respuestas. Un `nan` al menos tiene pinta de error; un
5,0 tiene pinta de un talud con factor de seguridad cinco. Y es la forma de
**D20** apareciendo por tercera vez —un valor de reserva vestido de
resultado— con el mismo número que entonces.

### 2 · Lo que hace el programa de referencia, que decidió la forma del arreglo

Consultada su documentación (`Summary_of_Error_Codes`, y salidas reales
suyas): cuando no puede calcular un factor **escribe un código de error
negativo en el lugar del factor de seguridad**, nunca un `nan` ni un `inf`.
Verificado en una salida real: `Error Code -108 reported for 256 surfaces`.

Y el momento motor nulo **no se reporta como infinito**: tiene código propio,
y su descripción publicada dice que existe precisamente para no calcular
factores altísimos cuando la fuerza motora es muy pequeña, en el caso de una
superficie que corta un tramo horizontal del talud. Es literalmente nuestro
caso. Hay códigos hermanos para la iteración que no converge, para m-alpha,
para el momento motor negativo y para el factor cero por resistencia nula.

En los siete manuales de verificación no hay **ni una tabla** que publique
una superficie sin factor de seguridad. Los únicos `nan`/`inf` de toda la
carpeta de referencia están en archivos de OGR.

De ahí sale la decisión: donde no hay factor va **un motivo, no un número**.
`None` es lo que dice eso en este programa, y además revienta donde está el
error en vez de propagarse.

### 3 · La iteración que agota el tope no decía nada, y eso lo encontró la guarda

No estaba en el encargo ni en el plan: salió cuando la suite entera se corrió
con la invariante puesta y **39 tests reventaron**, la mayoría con «*X failed
to converge without saying why*».

Los cinco solvers iterativos —Bishop en sus dos ramas, Janbu, Spencer y GLE—
devolvían el **último iterado** con `converged=False` y absolutamente nada
más: ni mensaje, ni nota. Un número que es donde el solver se paró, no donde
iba. La referencia le da código propio y, en su descripción, **nombra el
ajuste que lo causa**, que es la diferencia entre «esta superficie no tiene
respuesta» y «sube el límite de iteraciones».

Ahora llevan `NOT_CONVERGED_NOTE`, compartida en la clase base por la misma
razón que la de resistencia nula: la condición es una y las respuestas eran
cinco silencios distintos. `is_valid` no se mueve —ya era `False` por
`converged`—, así que ninguna superficie cambia de población.

### 4 · Dos tests llevaban verdes sobre factores que el motor había rechazado

También lo destapó la invariante, y es la misma enfermedad un nivel más
arriba. Medido sobre 0.1.151:

| Test | Lo que leía | Lo que el motor decía de ese número |
|---|---|---|
| `test_efp_wall_v1122.py::test_horizontal_is_no_longer_inert` | **−2,727** | `Non-physical factor of safety −2.727 in iteration`, `converged=False` |
| `test_drawdown_bbar_v169.py::test_the_drawdown_lowers_the_factor_of_safety` (B̄ = 0,25) | **−0,03412** | `Non-physical factor of safety −0.03412 in iteration`, `converged=False` |

Los dos pasaban **por la razón equivocada**: un número negativo es finito, así
que sobrevive a `math.isfinite`, y está por debajo de cualquier cosa, así que
gana toda comparación `<`. El primero «demostraba» que una carga horizontal
baja el factor de seguridad con un valor que no es un factor de seguridad; el
segundo comprobaba que todo B̄ cae por debajo del embalse lleno usando el
único caso que no tenía respuesta.

Los dos tests se han hecho honestos: ahora exigen o un factor físico que
cumpla la desigualdad, o un fallo declarado, y el primero fija además **qué
B̄ resuelven** para que el bucle no pueda pasar en vacío. **Por qué** esos
dos casos se van a factor negativo no se contesta aquí: se reporta aparte.

### 5 · El agujero del retroanálisis

`governing_force` devuelve `math.nan` por diseño cuando ninguna de las dos
hipótesis da una fuerza finita, y el bucle comparaba con `>` sin guarda. Un
`nan` que llegase el primero se quedaba de `best` para siempre —toda
comparación posterior es `x > nan`, que es `False`— y el informe publicaba
una fuerza requerida `nan` sin nota, porque el aviso solo dispara con
`best is None`. Es D56 un nivel más arriba.

### 6 · Dos deslices de tipo

`spencer.py` y `gle.py` pasaban `error_message=None` a un campo declarado
`str`. Corregido en origen y absorbido además por la guarda nueva.

## Lo que se ha hecho

**`LEMResult.fos` pasa a `Optional[float]`.** `None` significa que no hay
factor de seguridad. `__post_init__` impone tres cosas, y las tres eran
alcanzables:

1. un valor no finito no se puede almacenar;
2. no se puede decir «no hay número» y «he convergido» a la vez;
3. **no se puede fallar sin decir por qué** — esta es la que caza el 5,0.

**`reason`, junto a `error_message`.** El código agrupable al lado de la
frase legible, que es el reparto que hace la referencia y lo que permite
decir «este motivo, N superficies» sin analizar prosa. Quince constantes con
nombre en `base.py`, al estilo de `slicer.REFUSED_OUTSIDE_MODEL`, y un
`ALL_REASONS` contra el que el test comprueba que la próxima razón no nazca
como cadena suelta.

**El `nan` deja de nacer.** `GLESystem.branches` señalaba una rama muerta con
`(nan, nan)`; ahora con `(None, None)`, y las doce guardas de finitud de
Spencer y GLE pasan por `branch_pair_ok`. Las cuatro identidades analíticas
de D10 —I1 a I4, a 1e-6— se sostienen sin mover un dígito.

**Los escritores.** `to_dict()` emite `null` y añade `reason`, `admissible` y
`admissibility_note`; el test lo pasa por `json.dumps(..., allow_nan=False)`,
que es lo que rechaza `NaN` e `Infinity` —ninguno de los dos es JSON válido,
y el codificador de Python los emite igualmente si no se le dice que no—.
`save_results` **omite el atributo `fos`** y escribe `reason` en su lugar,
que es lo de la referencia: un lector que se olvide de comprobar recibe un
`KeyError` que nombra la superficie, no un número. El `fos_array` del resumen
mantiene su `np.nan`, y no es lo mismo: es una columna numérica de longitud
fija, ya condicionada a `is_valid`, donde un hueco tiene que ser algo.

**Las cuatro puertas del banco.** La que escribió el `NaN` del 79 —
`_tools/ejecutar_caso.py`, `round(float(r.fos), 6)` sin preguntar por
`is_valid`— y tres más con el mismo defecto en `ejecutar_no_circular.py`,
`ejecutar_probabilistico.py` y `optimizar_caso.py`. Ahora escriben el motivo
donde no hay factor.

## Lo que se miró y se deja como está

El camino «sin bracket de λ» de Spencer y GLE devuelve `0.5·(F_f+F_m)` con
`converged = |g| < 0,02`. Tiene la misma silueta que el 5,0 de Corps, pero no
es lo mismo: cuando `|g| ≥ 0,02` lleva su `error_message`, y cuando es menor
las dos ramas coinciden de verdad y el resultado está convergido. Se queda, y
queda escrito que se miró.

## Lo que se reporta y NO se ha cambiado

La guarda del momento motor nulo es `abs(denominator) < 1e-9`, **absoluta**.
La referencia usa un umbral ocho órdenes de magnitud mayor para la misma
condición, y `AGENTS.md` exige que las tolerancias vayan relativas al tamaño
del modelo. Afecta a qué superficies entran en la población válida, así que
moverlo movería recuentos y podría mover una superficie crítica: **queda
fuera de D56** y se anota como defecto nuevo con esta evidencia.

## Verificación

- **Suite completa y sin filtrar: 3204 de 3204.** La primera pasada con la
  invariante puesta dio 39 fallos, y los 39 eran hallazgos: 33 de la
  iteración muda del punto 3, 3 del tooltip del lienzo, 2 de los tests del
  punto 4 y 1 del `math.isfinite(None)` de `postprocess`.
- `tests/test_no_number_v1152.py`, 16 comprobaciones. **13 de las 16 fallan
  con 0.1.151**, incluidas todas las que fijan la invariante; las 3 que pasan
  son las de contexto (que la masa siga siendo simétrica, que el fallo ya se
  declarase).
- Las cuatro identidades de D10 (I1–I4, a 1e-6), los tres casos
  `test_slide_validation_*` y la recursión EM 1110-2-1902 de
  `test_modified_swedish_v198.py`: sin mover un dígito.
- **Banco, problema 79 re-corrido**: los doce factores idénticos dígito a
  dígito, el círculo publicado en 1,397239 y `caso2_spencer` en 1,44271.
  (El 1,399836 que cita el encargo es de la instantánea 0.1.127, anterior a
  la corrección de la cara del talud; el valor de la corrida vigente es
  1,397239, y es ese el que no se ha movido.)
- **Comparativa regenerada: idéntica byte a byte.** 253 OK, 100 REVISAR, 69
  DISCREPANCIA, los mismos de antes. Ninguna fila nueva.
- Barrido de no-números sobre la corrida vigente: solo
  `02_Slide2_Problema096/resultados_procedimientos.json`, el registro
  histórico que el encargo excluye y que no se ha tocado.
