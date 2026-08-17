# OGR Slip2D v0.1.90 — la raíz estaba en λ ≈ 3 y el programa dejaba de mirar en 1,5

Spencer y GLE abandonaban **casi mil círculos por método y por modelo** que la
referencia resolvía sin problema. No por la formulación: porque no llegaban.

Los dos métodos buscan λ muestreando un grid y localizando el cambio de signo
de `F_f(λ) − F_m(λ)`. El grid paraba en ±1,5. Para las superficies difíciles
esa función es monótona y sigue negativa ahí, así que «sin cambio de signo»
nunca quiso decir «no hay raíz»: quería decir **fuera de alcance**.

```
λ = 1,500   F_f 0,7351   F_m 1,0551   F_f−F_m = −0,320
λ = 2,994   F_f 1,1257   F_m 1,1262   F_f−F_m = −0,0005   <-- la raíz
```

| círculos que la referencia resuelve y OGR abandonaba | v0.1.89 | v0.1.90 |
|---|---|---|
| Ej_1 spencer | 936 | **172** |
| Ej_1 gle | 1314 | **422** |
| Ej_2 spencer | 932 | **126** |
| Ej_2 gle | 1433 | **446** |

En tasa de convergencia: GLE pasa del 54-59 % al **86-87 %**, Spencer del
69-71 % al **95-96 %**.

---

## 1 · Cómo se encontró, y qué se descartó por el camino

Empezó como una regresión que yo mismo introduje en v0.1.89: GLE bajo
Simulated Annealing devolvía **0 superficies válidas**. La había aceptado a
sabiendas, atribuyéndola a los cortes de dovela en los vértices.

**Medición 1 — qué salida falla.** De los 61 candidatos de una corrida SA+GLE,
los 61 fallan por la misma:

```
61x  conv=False | GLE: no λ-bracket; using nearest F_f≈F_m
```

**Medición 2 — y exonera el rebanador.** Sobre un candidato real, rebanado con
cortes en vértices y uniformemente, las curvas son casi idénticas y **ninguna
cruza cero**:

| λ | −1,5 | 0 | 1,5 |
|---|---|---|---|
| con cortes en vértices (v0.1.89) | −0,745 | −0,576 | −0,320 |
| uniforme (como antes) | −0,730 | −0,565 | −0,308 |

El rebanador no rompió GLE. Lo que hizo fue mover la trayectoria de la
búsqueda —SA se guía por el factor de seguridad, así que evaluar distinto la
lleva a otros candidatos— y destapar un fallo que ya estaba. La atribución de
v0.1.89 era **incorrecta**, y queda corregida aquí.

## 2 · El rango de la referencia, y un error que ya se había cometido

Sus propios modelos traen `min_lambda: -0.1` y `max_lambda: 6`, con las
casillas de aplicación **desmarcadas**: no restringe λ por defecto. OGR cortaba
en ±1,5 siempre.

Y esto ya había pasado. `ogr_core/project/settings.py` documenta que el rango
era ±1,25 y se subió a ±1,5 en v0.1.74 **porque el círculo validado de Ej_1
converge en λ = 1,4919** — ensanchado exactamente lo justo para el caso que
falló entonces. Es la misma forma de error que la regla de radios de v0.1.88:
un parámetro calibrado contra los casos que se probaron, no contra el
fenómeno. La diferencia es que ahora el número no se elige: es el de la
referencia.

## 3 · El arreglo está construido para no poder mover lo que ya funcionaba

No se ensancha el grid. Se **extiende sólo cuando el grid calibrado no
encuentra bracket**:

1. Muestrear el `_LAMBDA_SHAPE` de siempre, ±1,5.
2. ¿Hay cambio de signo? Entonces exactamente lo de antes, con las mismas
   muestras y el mismo camino de código.
3. ¿No lo hay? Extender hacia el rango configurado (2,0 · 2,5 · 3,0 · 3,5 ·
   4,0 · 5,0 · 6,0) antes de rendirse.

Así, toda superficie que hoy converge sigue igual **por construcción**, y las
evaluaciones extra sólo las pagan las que hoy se rinden.

Sólo hacia λ positivo, y no por descuido: λ es la razón interdovela X/E, y el
lado al que estiran las superficies difíciles es el de interdovela empinada.
El límite inferior de la referencia, −0,1, está muy dentro del grid calibrado.

El rango del usuario **sigue mandando**: con `max_lambda = 1.0` la extensión
sale vacía. Un ajuste que el usuario estrecha a propósito tiene que seguir
significando lo mismo (regla 7).

## 4 · La comprobación de que no se mueve nada, medida y no argumentada

Sobre una muestra de las rejillas de referencia, resolviendo los mismos
círculos con λ cortado en 1,5 y abierto a 6:

| | círculos | idénticos | movidos | ganados | **perdidos** |
|---|---|---|---|---|---|
| Ej_1 GLE | 405 | 155 | 2 | 77 | **0** |
| Ej_1 Spencer | 405 | 190 | 3 | 65 | **0** |
| Ej_2 GLE | 404 | 139 | 3 | 83 | **0** |

**Ninguno perdido, 97-98 % idénticos bit a bit.** Y los pocos que se mueven
resultaron ser lo contrario de un problema: tenían `lambda = None`, es decir se
habían resuelto por la vía de «sin bracket» —promedio de la muestra más
cercana— y ahora encuentran raíz real justo pasado el corte:

```
centro (96 , 75)  r 52,239: λ = 1,531   FoS 1,28671 -> 1,29591   ref 1,29807
centro (96 , 102) r 80,092: λ = 1,525   FoS 1,46849 -> 1,47222   ref 1,46977
```

El primero pasa de 0,88 % de error a 0,17 %.

### Los tres testigos

1. Los siete métodos sobre los círculos críticos de Ej_1 y Ej_2: sin moverse.
2. Los cinco casos publicados: dentro de tolerancia. **69/69** entre los dos.
3. La auditoría por círculo, reejecutada para los dos métodos tocados: las
   tasas de convergencia suben como arriba.

Sobre el testigo 3 hay que decir una cosa que a primera vista parece mala: el
**p90 sube** (Ej_1 GLE 0,358 → 0,467 %). No es una regresión — la población
medida crece un 30-40 % **con los círculos difíciles**, que son los que más
error llevan. La tabla de arriba es la que demuestra que lo que ya se medía no
se ha movido.

## 5 · Reorienta una auditoría que llevaba once versiones abierta

`docs/audits/spencer_gle_interslice_v179.md` buscaba el fallo en la
formulación interdovela desde v0.1.79. La auditoría por círculo de v0.1.89
—67 837 valores de referencia en vez de catorce— ya no encajaba con eso:
**donde convergen, Spencer y GLE son los dos métodos más exactos del
programa** (p99 de 0,62 % y 0,67 % contra el 11-14 % de Fellenius y Janbu). Si
la ecuación estuviera mal, ahí es donde se vería.

El síntoma original —que se separan de Bishop menos de lo que dicen las
referencias publicadas— **no queda explicado por esto**, y esa auditoría sigue
abierta. Lo que cambia es que ya no se puede atribuir a la formulación sin
antes rehacer la comparación **sobre la población completa**, que hasta ahora
no existía porque un tercio de ella no llegaba a resolverse.

## 6 · Corrección de lo que escribí en v0.1.89 sobre Simulated Annealing

`docs/PENDIENTES.md` decía que `generation_steps` «deja de hacer nada». Estaba
**mal medido**, y el mecanismo real apunta a otro sitio. Instrumentado:

| `generation_steps` | K | Ngen0 | Σ Ngen nominal | evaluadas | FoS |
|---|---|---|---|---|---|
| 50 | 4 | 20 | 50 | 151 | 1,7491 |
| 300 | 6 | **50** | 117 | 459 | 2,1854 |
| 1 000 | 20 | **50** | 257 | **462** | 1,6564 |
| 3 000 | 60 | **50** | 657 | **462** | 1,6564 |

`K = generation_steps/50` hace que `Ngen0 = generation_steps // K` valga **50
siempre**; `Ngen` se halva cada pasada hasta un suelo de 10; y la parada a las
3 pasadas sin mejorar congela el total en 462. No es «el ajuste se ignora»: es
un bucle interno de tamaño fijo y una parada que domina.

Y ahora se conocen los parámetros de la referencia, de sus propios modelos:

| | referencia | OGR |
|---|---|---|
| `ngen` | **1000** | 50 (fijo) |
| `nepsilon` | **5** | 3 |
| `ftol` | **0,0001** | 1e-3 |
| `c` | 8 | 8 ✔ |

Eso convierte el pendiente de «investigar» en «cambiar exactamente esto». **No
se hace aquí**: cambia coste y resultados en toda la suite y no hay referencia
externa para el resultado de una búsqueda no circular. Su propia versión.

---

## Archivos

- `ogr_slip2d/methods/base.py` — `_LAMBDA_EXTENSION`, `lambda_grid_extension()`,
  `lambda_grid()` acotado también al grid calibrado, `max_lambda` 1,5 → 6,0.
- `ogr_slip2d/methods/gle.py`, `spencer.py` — extensión perezosa al no
  bracketear; `max_lambda` por defecto.
- `ogr_core/project/settings.py` — `max_lambda` 6,0 y la migración encadenada
  1,25 → 1,5 → 6,0, sólo para quien tuviera el valor por defecto.
- `tests/test_lambda_range_v190.py` — nuevo, 22 casos.
- `tests/test_annealing_bootstrap_v139.py` — GLE vuelve a la lista de métodos;
  se borra el caso que afirmaba su fallo, que era su función.
- `docs/audits/spencer_gle_interslice_v179.md`, `percircle_fos_v189.md` —
  actualizados con el hallazgo.
- `docs/PENDIENTES.md` — se cierra 0a; se corrige y precisa 0.

## Los dos números que se movieron en la suite, y por qué ninguno estaba roto

- `test_project_settings_wiring_v174.py::test_the_two_mistaken_defaults_are_migrated`
  esperaba que la migración de v0.1.74 aterrizara en 1,5. Ahora encadena a
  6,0. Mecánico.

- `test_focus_optimize_m4_v155.py::test_never_returns_a_worse_surface`
  afirmaba dos cosas: el invariante que anuncia su nombre —la caminata no
  acaba peor de lo que empieza, que **sigue pasando**— y de propina
  `abs(rep.initial_fos - f0) < 0.05`.

  Esa segunda comparaba el factor de seguridad de una superficie de 4
  vértices con el de su **densificación a 12**. Son dos superficies
  distintas, y el 0,05 era una captura de cuánto movía la densificación a
  *aquella* superficie. Medido:

  | | superficie crítica del Path Search | f0 | densificada | dif. |
  |---|---|---|---|---|
  | λ ≤ 1,5 | (44,24 · 52,59 · 65,61 · 76,94) | 0,883183 | 0,893447 | 0,010 |
  | λ ≤ 6,0 | **otra** (45,90 · 52,04 · 64,56 · 76,64) | 0,883672 | 0,944834 | 0,061 |

  El arreglo de λ cambió **cuál** de los quince caminos aleatorios sale
  crítico. Nada se rompió; la tolerancia medía otra cosa. Así que **no se
  subió de 0,05 a 0,07**: el aserto se separó en su propio caso y se
  sustituyó por la identidad que quería expresar — sin densificar, el
  optimizador arranca **exactamente** del número que el evaluador da para la
  superficie que recibió. Igualdad exacta, sin tolerancia, y más fuerte que
  lo que había.

## Probado

- **Suite entera sin argumentos: 1911 / 1911, cero fallos.**
- Los tres testigos del §4.
- Extensión perezosa: el grid calibrado es idéntico con `max_lambda` 1,5 y 6,0.
- Migración de proyectos guardados, incluida la cadena desde v0.1.73.

## Sin probar

- Que el arreglo cierre también el síntoma de la auditoría v0.1.79 (§5). Hace
  falta rehacer la comparación con Bishop sobre la población completa.
