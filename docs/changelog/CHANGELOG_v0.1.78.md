# OGR Slip2D v0.1.78 — Slope Search llevaba razón desde v0.1.24, y nadie podía demostrarlo

Esta versión cierra los tres pendientes que v0.1.77 dejó reportados a
propósito. Los tres seguían exactamente como se describieron. Uno de ellos
resultó estar **mejor** de lo que decía el changelog, y averiguarlo fue el
trabajo que más valió.

---

## El hallazgo: había una referencia publicada, y estaba en el disco

v0.1.77 terminaba con esta frase:

> **Slope Search no está validado contra ninguna referencia externa**, y
> ahora que se ejecuta por primera vez desde la interfaz, debería. Que
> produzca un número no dice que sea el correcto.

La búsqueda de una referencia empezó por internet y terminó cuatro
directorios más allá, en la documentación que ya estaba en
`referencias/Documentacion_Guia/`. Allí hay tres manuales de verificación
con **102 problemas**, y los diez primeros no son ejemplos del programa: son
los **problemas ACADS**.

En 1988 la *Association for Computer Aided Design* distribuyó cinco
problemas de estabilidad de taludes con cinco variantes entre la profesión
geotécnica australiana y de otros países. **Treinta y tres programas** los
resolvieron de forma independiente, y se publicó tanto el valor arbitrado
como la dispersión (Giam & Donald, 1989). Eso no es una comparación entre
dos programas: es una referencia externa con respaldo estadístico.

El problema **1(a)** tiene además una propiedad que sus vecinos no tienen:
**la geometría y los materiales están en el texto**, no en una figura. Se
puede construir sin leer un dibujo y sin inventar una sola coordenada.

### El resultado

| Método | OGR (rejilla del enunciado) | Publicado | Error |
|---|---|---|---|
| Bishop | 0.9910 | 0.987 | 0.4 % |
| Spencer | 0.9910 | 0.986 | 0.5 % |
| GLE / Morgenstern-Price | 0.9910 | 0.986 | 0.5 % |
| Janbu corregido | 0.9913 | 0.990 | 0.1 % |

Frente a la **media de los 33 programas, 0.991**: OGR da 0.9910.

Y lo que se buscaba —**Slope Search: 0.9868**, con semillas 7, 42 y 123
dando 0.9871, 0.9868 y 0.9888. Un 0.4 % por debajo de la media publicada, y
*ligeramente más crítico que la propia rejilla* (0.9895), que es exactamente
lo que debe hacer una búsqueda dirigida: la rejilla solo puede poner centros
en su retícula.

**Slope Search no estaba mal. Estaba sin demostrar.** Son cosas distintas, y
la segunda es la que arregla esta versión.

### Por qué el valor esperado es 0.991 y no 1.00

La fuente publica cuatro números: el arbitrado (1.00), la media de los 33
(0.991), la media Bishop de 18 (0.993) y el Bishop del programa comercial
(0.987). El caso usa **la media de los 33**, por dos razones: es el valor con
respaldo estadístico, no la opinión de un árbitro sobre un problema cuya
solución exacta nadie conoce; y **no consagra el resultado de ningún programa
concreto**. Un caso de validación que copia la salida de un competidor no es
una validación, es un empate acordado.

La tolerancia es del **2 %** porque la fuente no es más precisa que eso: el
valor arbitrado y la media difieren un 0.9 % entre sí. Pedir el 0.5 % que se
le exige a un método LEM sobre un círculo dado sería exigirle a la referencia
una precisión que no tiene, y el caso fallaría por la calidad de la fuente.

### Dónde vive

En los dos sitios, y cada uno hace un trabajo distinto:

- `validacion/casos/001-acads-1a/` — **el primer caso ejecutable del
  directorio**, que llevaba versiones montado y vacío, solo con la plantilla.
  El `modelo.ogr` lleva dentro la rejilla del enunciado (20×20 intervalos
  entre (22.8, 42.3) y (43.7, 62.6), 11 círculos por punto), así que lo que
  se valida es el análisis que el proyecto describe.
- `tests/test_acads_validation_v178.py` — los siete métodos sobre el círculo
  crítico, la rejilla, y Slope Search con tres semillas.

### El runner de casos validaba con la búsqueda equivocada

Al meter el primer caso apareció un fallo de la regla 7 en el propio runner:
`test_validation_cases.py` instanciaba `GridSearch` **siempre**, y solo leía
`num_slices`. Un caso que declarase `"tipo": "slope"` se habría ejecutado con
otro buscador **en silencio** — y la rejilla usada habría sido la de por
defecto, no la del problema publicado que el modelo llevaba dentro.

Ahora despacha por `analysis_runner.build_search`, que es «el único punto de
instanciación» de las seis estrategias y por donde pasan la interfaz y el
CLI. Un caso valida **la búsqueda que el programa ejecuta de verdad**, no una
reconstrucción que puede derivar. Los ajustes se aplican sobre una **copia**
de la configuración, y hay un test nuevo que rechaza un `tipo` que no exista,
por el mismo motivo por el que ya se validaban los ids de método.

### Y el caso estuvo a punto de subirse sin su modelo

Al ir a hacer el commit apareció lo que habría sido el fallo más tonto y más
difícil de ver de esta versión: `.gitignore` excluía `*.ogr` en bloque, con
excepciones solo para `examples/`. `validacion/README.md` lleva desde que
existe el directorio diciendo que el modelo **se versiona**, pero la regla es
anterior y nadie las había cruzado.

Lo grave no es la exclusión: es cómo habría fallado. Un caso sin
`modelo.ogr` se **omite, no falla** —a propósito, para que un caso a medio
escribir pueda convivir con los buenos—, así que el repositorio se habría
quedado otra vez con cero casos ejecutables **informando todo en verde**.

Dos arreglos: la excepción `!validacion/casos/**/*.ogr` (los `.h5` de al lado
siguen ignorados, que son salida y no entrada), y un test que exige que
**haya al menos un caso que se ejecute de verdad**. El directorio ya ha
crecido más allá de estar vacío, así que un recorrido vacío pasa a ser un
fallo en vez de un estado.

---

## Lowe-Karafiath: el mismo bug que `janbu_corrected`, en otro archivo

Estaba gris en *Project Settings* con el tooltip «Not yet implemented in OGR
Slip2D», y estaba **registrado, implementado y validado desde v0.1.20** con
error < 1 % contra la referencia. Cincuenta y ocho versiones ofreciendo un
método que el motor calculaba bien y la interfaz no dejaba marcar.

La causa era una tupla escrita a mano en `_MethodsPage` con seis ids,
congelada en v0.1.7, con este comentario encima:

```python
# v0.1.7: Spencer and GLE/Morgenstern-Price are implemented.
# Mark unimplemented Corps of Engineers and Lowe-Karafiath only.
```

Añadir `LEM.LOWE_KARAFIATH` a la tupla habría arreglado el síntoma y dejado
la causa intacta. Es **literalmente el mismo fallo** que `build_method` ya
documenta para `janbu_corrected` (`analysis_runner.py:160-164`): en cuanto
existe una segunda lista de métodos al lado del registro, la única pregunta
es en qué versión se desincroniza.

Así que la lista se ha borrado, no ampliado:

```python
implemented = m.value in set(method_registry())
```

Corps of Engineers #1 y #2 **siguen grises**, porque de verdad no están en el
registro — y el día que alguien los registre se activarán solos.

El test nuevo no dice «Lowe-Karafiath está activo», que sería una tercera
lista. Dice que **el conjunto de casillas deshabilitadas es exactamente
`{LEMMethod} − method_registry()`**, que es la propiedad que hace imposible
volver a desincronizarlas.

---

## El campo de filtración ya viaja dentro del `.ogr`

`Project.to_dict` guardaba `fem_mesh` y no `seepage_result`. Como
`pore_pressure.py` responde 0.0 cuando no hay campo, reabrir un proyecto FEM
resuelto y pulsar *Compute* daba **un talud seco, en silencio** — y un talud
seco es más estable, así que el número salía tranquilizadoramente alto. En el
modelo de prueba la diferencia es del 5 %: **0.8398 con agua contra 0.8831
sin ella**. v0.1.77 lo detectó y se negó a calcular; esta versión es la otra
mitad.

### Se guarda una décima parte, y se reconstruye el resto

De los diez campos de `SeepageResult`, **solo tres son dato**: `total_head`,
`kr` y `gamma_w`. Los demás son funciones de esos tres más la malla y los
materiales, y guardarlos sería guardar los mismos números hasta cuatro veces:

| Campo | Qué se hace |
|---|---|
| `total_head` | **Se guarda.** Es el único dato primario. |
| `pressure_head` | Se reconstruye: `H[i] − y[i]` |
| `pore_pressure` | Se reconstruye: `γw · pressure_head` |
| `velocity`, `gradient` | Se reconstruyen con `_element_fluxes(H, kr)` |
| `reactions` | **No se guarda.** Sus únicos consumidores son la iteración del propio solver y el paso transitorio, que la recalculan. Ningún camino de recarga la lee. |

Medido sobre el modelo de prueba (382 nodos, 677 elementos):

```
.ogr completo          158.8 KB
  fem_mesh             113.8 KB
  seepage_result        13.5 KB
  (guardándolo entero)  99.1 KB   <- lo que se ha evitado
```

**7.3× más pequeño**, y el campo pasa a ocupar el 12 % de la malla a la que
pertenece en vez de igualarla.

### Por qué se guarda `kr` en vez de recalcularlo

Ésta es la única decisión no obvia, y estuvo a punto de salir mal. `kr` se
puede recalcular desde las cargas finales con `_element_kr(H)`… pero **no
daría el mismo valor**: el bucle de Picard escala la conductividad con
`kr(H_k)` y luego resuelve para `H_(k+1)`, así que `kr(H_final)` se parece a,
pero no es igual a, el `kr` con el que se calcularon las velocidades.
Reconstruirlo habría hecho que un proyecto reabierto dibujase vectores de
flujo **ligeramente distintos** de los del proyecto que se guardó. Ese tipo
de discrepancia silenciosa es peor que un fichero un poco más grande.

Guardando `kr` (E floats), la reconstrucción es exacta: `_element_fluxes` es
determinista dados H, las conductividades y kr, y los tres sobreviven. El
test lo comprueba a 1e-9.

### Los tests no son instantáneas

- `u = γw·(H − y)` en **todos los nodos**, que es una identidad analítica, no
  una copia de la salida.
- El bug de extremo a extremo: calcular → guardar → cargar → `Compute` sin
  recalcular filtración. El FoS debe coincidir con el de antes **y diferir
  del seco**. La segunda comprobación es la que impide que el test pase por
  accidente si el campo se vuelve a perder.
- El presupuesto de tamaño, porque «guardar solo lo irreductible» es una
  intención hasta que alguien la mide.

### Dos cosas que aparecieron al hacerlo

1. **Regenerar la malla no limpiaba `transient_results`.** `act_generate_mesh`
   y `_reset_fem_mesh` anulaban `seepage_result` y se dejaban la lista de
   etapas. No se notaba porque nada se guardaba: una lista obsoleta vivía
   hasta cerrar la sesión. Ahora que los campos se escriben, se habría
   guardado una lista indexada por los nodos de la malla **anterior**.
   Corregido en los dos sitios.
2. **Un campo cuyo número de nodos no coincide con la malla se descarta**, y
   la guarda lo reporta igual que a un proyecto sin resolver. Interpolar
   sería aritmética entre números que no se refieren a lo mismo.

### La guarda de v0.1.77 se queda

Su causa más común ha desaparecido, pero las otras son reales: un proyecto
guardado por una versión anterior, una malla regenerada desde entonces, o un
modelo en el que sencillamente nunca se corrió el análisis de agua. Solo ha
cambiado el texto, que culpaba al formato de archivo y ya no es cierto.

---

## Anomalía reportada y NO corregida (regla 6)

**«Number of Surfaces» significa dos cosas distintas según la búsqueda.**

`SlopeSearch(num_surfaces=1500)` devuelve `valid_count ≈ 1900`. No es un
error de cuenta: el bucle de generación corre exactamente `num_surfaces`
veces, y la fase de refinamiento local que viene después añade hasta 8×120
evaluaciones más, todas contadas como válidas.

O sea que aquí «Number of Surfaces» son **superficies generadas**, mientras
que en `PathSearch` son superficies **aceptadas** — esa búsqueda sigue
generando hasta alcanzar el número pedido de válidas, y
`test_slide_validation_ej1.py:302` fija ese significado explícitamente.
`attempts` lo remata: PathSearch lo informa, SlopeSearch lo deja en cero.

Dos búsquedas, dos significados del mismo ajuste, y nada en la interfaz los
distingue. Hay tests nuevos que **fijan el comportamiento actual** para que
cualquier reconciliación futura sea un cambio deliberado con un diff
visible. No son un aval de que esté bien.

---

## Qué se probó

Suite completa, 1664 tests antes de empezar, verde. Los archivos nuevos:

- `tests/test_methods_page_v178.py` (5): el conjunto gris es exactamente el
  no registrado; Lowe-Karafiath activable; Corps sigue gris; todo miembro del
  enum tiene casilla y todo método registrado se ofrece.
- `tests/test_seepage_serialisation_v178.py` (14): la identidad de u en todos
  los nodos; cargas, velocidades y gradientes contra el original; el FoS
  antes y después de guardar frente al seco; la guarda antes y después; un
  campo que no casa con la malla; los tres presupuestos de tamaño; y las
  etapas transitorias.
- `tests/test_acads_validation_v178.py` (14, ~20 s): geometría, rejilla,
  siete métodos sobre el círculo crítico, Slope Search con tres semillas y
  reproducibilidad, más los tres que documentan `valid_count`.
- `tests/test_validation_cases.py`: dos tests nuevos (el tipo de búsqueda
  existe; hay al menos un caso que se ejecuta) y el runner reescrito sobre
  `build_search`. Ejecuta por primera vez un caso real.

Suite completa al cerrar: **1694 tests, 1694 pasan**.

## Qué falta por probar

- **ACADS 1(c), 1(d), 2(a) y 5, y la familia publicada de Arai & Tagyo
  (1985), Yamagami & Ueta (1988) y Greco (1996)**: los factores de seguridad,
  los materiales y los métodos ya están extraídos del texto; **la geometría
  solo existe en las figuras**, que son imágenes rasterizadas dentro de los
  PDF. Son las que validarían las búsquedas no circulares (Path Search y
  Simulated Annealing), que siguen sin ninguna referencia externa.
- Un transitorio de verdad guardado y recargado, con varias etapas resueltas.
  El test actual comprueba que la lista viaja, no que un transitorio completo
  sobreviva.
- El coste del `.ogr` con la malla máxima (200 000 elementos). Está razonado
  —lineal en el número de nodos— pero no medido.

## Pendientes que siguen abiertos

1. **`SlopeSearch` no lee las Slope Limits.** Avisado desde v0.1.77. Ahora
   además hay con qué medirlo: cualquier cambio en qué superficies se generan
   se puede contrastar contra ACADS 1(a) antes y después.
2. **El *Lower Angle* de Slope Search casi no puede mover el número.**
   `search.py:529` hace `ang_lo = min(ang_lo, radians(-70))` **después** de
   leer el valor del usuario, y `analysis_runner.py` pasa el ángulo inferior
   sin mirar su checkbox (al superior sí lo mira). Candidato claro a la regla
   7, pero tocarlo cambia qué superficies se generan, o sea el número, así
   que va con su propia validación.
3. **Dos casillas del panel de Slope Search no se leen nunca**
   (`_sl_composite` y `_sl_tcrack` en `grid_dialogs.py`): `apply()` escribe
   esos ajustes desde los widgets de *Grid*.
4. **El CLI sigue sin análisis probabilístico, barrido de niveles,
   retroanálisis ni informes.**
5. **El `except Exception` de `_ComputeWorker.run` sigue ahí.**
