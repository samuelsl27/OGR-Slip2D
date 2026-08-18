# OGR Slip2D v0.1.93 — el 41 % del cálculo se iba en comprobar que la geometría no se había movido

| Ej_2, rejilla de referencia (4840 círculos) | antes | ahora |
|---|---|---|
| Fellenius | 14,0 s | **5,0 s** |
| Bishop | 18,4 s | **8,1 s** |
| Janbu simplificado | 16,9 s | **7,7 s** |
| Janbu corregido | 16,9 s | **7,7 s** |

**Ningún factor de seguridad se mueve.** Comprobado bit a bit sobre los siete
métodos en las dos rejillas de referencia completas (4851 y 4840 círculos):
mismo FoS, mismo centro, mismo radio, mismo recuento de válidas e inválidas.
Cero discrepancias en catorce comparaciones.

**Y lo que NO se ha arreglado, que importa igual**: Spencer y GLE siguen
tardando **238 s y 249 s** en esa misma rejilla. La segunda optimización de
esta versión, pensada para ellos, resultó **inerte al medirla** — §3. El
motivo está diagnosticado y abierto en `PENDIENTES.md` §6.

---

## 1 · La pregunta era otra: «¿qué cambiamos ayer?»

El punto de partida fue una queja concreta —el cómputo de superficies se ha
disparado, sobre todo en Ej_2— y una hipótesis razonable: algo de las seis
versiones del día anterior. La hipótesis era **falsa en su parte acusadora y
cierta en la descriptiva**, y separarlo requirió medir en vez de leer diffs.

A/B en el mismo proceso, con corrida de control repetida, como manda
`AGENTS.md`. Ej_2 con Spencer, subrejilla de 616 círculos:

| configuración | tiempo | superficies válidas |
|---|---|---|
| bracket de v0.1.87, `min_radius` 3,0 | 8,96 s | 102 |
| bracket de v0.1.88, `min_radius` 0,0 | 27,8 s | 264 |

**+211 %**, con una deriva de control del 17,8 % — muy por encima del ruido.

### Lo que NO fue, y conviene dejarlo escrito

Las tres sospechas más plausibles, todas descartadas por medición:

| cambio | efecto medido |
|---|---|
| extensión de λ (v0.1.90) | −3 %, dentro de la deriva de control |
| `check_m_alpha` por defecto (v0.1.89) | −1 % en Spencer; +8,7 % en Bishop/Ej_1 |
| masas múltiples por círculo (v0.1.84) | 0,97 candidatos por círculo |

Todo v0.1.85 → v0.1.92 junto, en Bishop/Ej_1, suma **+35 %**. El salto grande
es uno solo.

### Y por qué el culpable no se toca

El bracket de v0.1.88 genera **la misma población** —4840 círculos, la
identidad `(nx+1)(ny+1)(rinc+1)`— pero **2,6× más de ellos definen una masa
deslizante real** y llegan a rebanarse y resolverse, en vez de descartarse
barato. Ese trabajo de más **es el trabajo correcto**: es exactamente lo que
metió los radios críticos de la referencia dentro de la población muestreada
(47,2124436 en Ej_1, 60,2564659 en Ej_2) y lo que llevó los cuatro errores de
validación a ±0,13 %. Revertirlo sería cambiar un resultado validado para que
el reloj mienta.

La conclusión útil es la del enunciado invertido: el problema no es **cuántas**
superficies se analizan, sino **cuánto cuesta cada una**. Y ahí lo que
apareció no era de ayer.

## 2 · El 41 %: revalidar una firma que nadie había invalidado

`Project.resolve_regions()` valida su caché reconstruyendo una firma sobre
**cada vértice de cada contorno externo y de material**. El rebanador pide el
material de un punto unas dos veces por dovela, así que en una corrida de 605
círculos eso son **27 342 reconstrucciones y 1,5 M de llamadas a `round()`**
para un modelo cuya geometría no se movió ni una vez.

En el perfil, `_regions_cache_key` era el **41 %** de una búsqueda con Bishop
en Ej_1 y el **42 %** en Ej_2. La primera de las dos funciones más caras del
programa, y no calcula nada.

Esto **no es de ayer**: v0.1.63 ya lo vio —su comentario lo dice con todas las
letras, «rebuilding a signature over every vertex […] costs more than the
point-in-polygon scan it guards»— y lo rodeó en **un** punto de llamada
(`materials_at`) en vez de atacar la causa. Lo que hizo ayer el bracket de
v0.1.88 fue multiplicar por 2,6 el número de superficies que pagan ese peaje.

### Por qué la firma no se puede sustituir por un contador

La tentación evidente —un número de revisión que suba en cada mutación— es
**incorrecta aquí**, y esa es la parte que merece recordarse. El lienzo edita
los contornos **in situ**: `project.boundaries[bi] = new_b` en
`ogr_gui/main_window.py`, arrastres de vértice en
`ogr_gui/canvas/canvas_view.py`. Ninguna de esas rutas pasa por `_notify`. Un
contador de revisión devolvería un mapa de materiales caducado tras un
arrastre de vértice corriente, y el resultado seguiría pareciendo razonable —
que es la peor forma de estar mal.

La firma por contenido es lo que hace segura la edición. Así que no se quita:
se **suspende**, y sólo donde ya rige una garantía más fuerte.

### `Project.regions_frozen()`

Gestor de contexto reentrante. Dentro del bloque, `resolve_regions()` y
`bounding_box()` creen sus cachés sin revalidarlas. Al entrar se resuelve una
vez con la firma todavía viva, de modo que un bloque congelado nunca sirve una
caché que empezó vacía; se libera en `finally`, para que una excepción no deje
el proyecto clavado a una subdivisión caduca.

`BaseSearch.run` pasa a ser **método plantilla**: envuelve con
`regions_frozen()` y delega en `_run()`, ahora el abstracto (renombrado en las
seis búsquedas). Está ahí y no en `analysis_runner.build_search` por la
lección que v0.1.89 dejó anotada tres líneas más arriba en ese mismo archivo:
cuando la interfaz y la construcción directa entran por puertas distintas,
acaban comportándose distinto. Los tests, los scripts y `examples/` construyen
su búsqueda a mano.

Es legítimo porque ya existía la regla de que **un cálculo no modifica el
proyecto del usuario** — los coeficientes de diseño se aplican a una *copia*,
que es otro `Project` con sus propias cachés. El análisis probabilístico y el
barrido de descenso rápido también quedan a salvo: ambos clonan el proyecto
por realización y llaman a `.run()` sobre el clon, y cada `run()` vuelve a
resolver al entrar.

`bounding_box()` se lleva su parte aparte: lo llama `evaluate_circle` una vez
por círculo candidato, y **cada llamada reconstruía la firma dos veces**.

## 3 · El 82 % que no se podía saltar (la optimización que salió inerte)

Ambos métodos buscan λ muestreando una forma calibrada de 14 valores, buscando
un cambio de signo en `g(λ) = F_f − F_m`, y refinando dentro de ese intervalo.
Hasta ahora evaluaban **los catorce** y miraban después.

Cada muestra es un *inner solve* completo. Medido en Ej_2:

- 14,0 *inner solves* por superficie en el muestreo;
- 3,0 en la bisección que de verdad encuentra la raíz;
- **el muestreo era el 82 % del trabajo**.

Y explica la escala del problema: Spencer y GLE cuestan **15× Bishop** por
círculo (44–48 ms contra 2,9 ms).

Ahora el muestreo **para en el primer cambio de signo**. Es neutro por
construcción, y ese argumento es lo único que ha salido bien de este
apartado: `_first_bracket`
recorre pares **consecutivos** en λ **ascendente** y devuelve el **primero**, y
las muestras se añaden en ese mismo orden. Truncar la lista justo después de
ese cambio de signo deja intacto el intervalo que la función habría devuelto —
mismo intervalo, misma bisección, misma raíz.

Las dos rutas que sí necesitan la forma entera quedan intactas, porque el
corte es **condicional a que haya intervalo**:

- sin cambio de signo, el respaldo elige `min(samples, key=|g|)` sobre
  **todas** las muestras;
- sin cambio de signo, se alcanza la extensión perezosa de v0.1.90 (2,0 … 6,0),
  sin la cual una raíz en λ ≈ 3 volvería a ser inalcanzable.

### Y aquí está el error de lectura de esta versión

El «82 %» dice cómo se **reparte** el trabajo, no cuánto se puede **saltar**.
Lo leí como lo segundo. Medido después del cambio, sobre la misma subrejilla
de Ej_2:

| | antes | ahora |
|---|---|---|
| muestras de λ por superficie, Spencer | 14,0 | **13,7** |
| muestras de λ por superficie, GLE | 14,0 | **13,9** |

Es decir: **prácticamente nada**. Y la razón, que es la parte que había que
entender antes de escribir el código: en estos modelos la raíz, cuando existe,
está **arriba** de la forma —la de Ej_1 en λ = 1,4919, el penúltimo valor— y
cuando no existe se cae al respaldo, que necesita las catorce sí o sí. Cortar
en el primer cambio de signo sólo ahorra cuando la raíz cae pronto, y aquí
casi nunca cae pronto.

El cambio se queda, porque es correcto, gratis y sí ahorra en las geometrías
cuya raíz es baja (con la raíz en λ = 0,3 usa 9 de 14). Pero **no es una
mejora de rendimiento de esta versión**, y venderlo como tal sería exactamente
el tipo de número que este proyecto no se cree.

Lo que de verdad haría barato a Spencer queda diagnosticado y sin hacer:
`PENDIENTES.md` §6.

**Efecto colateral, a la vista del usuario**: `iterations` en el `LEMResult`
baja cuando el corte actúa, porque contaba las muestras. El panel de
interpretación lo enseña.

## 4 · Medición de cierre

Las dos rejillas de referencia completas, siete métodos, antes y después:

| caso | método | FoS | antes | ahora | |
|---|---|---|---|---|---|
| Ej_1 | Fellenius | idéntico | 10,3 s | 4,0 s | **−61 %** |
| Ej_1 | Bishop | idéntico | 13,0 s | 6,6 s | **−49 %** |
| Ej_1 | Janbu simpl. | idéntico | 14,3 s | 6,4 s | **−55 %** |
| Ej_1 | Janbu corr. | idéntico | 14,3 s | 7,4 s | **−48 %** |
| Ej_1 | Lowe-Karafiath | idéntico | 33,0 s | 25,2 s | −24 % |
| Ej_1 | Spencer | idéntico | 103,0 s | 87,7 s | −15 % |
| Ej_1 | GLE | idéntico | 111,3 s | 93,7 s | −16 % |
| Ej_2 | Fellenius | idéntico | 14,0 s | 5,0 s | **−64 %** |
| Ej_2 | Bishop | idéntico | 18,4 s | 8,1 s | **−56 %** |
| Ej_2 | Janbu simpl. | idéntico | 16,9 s | 7,7 s | **−54 %** |
| Ej_2 | Janbu corr. | idéntico | 16,9 s | 7,7 s | **−54 %** |
| Ej_2 | Lowe-Karafiath | idéntico | 44,8 s | 48,7 s | **+9 %** |
| Ej_2 | Spencer | idéntico | 266,4 s | 238,2 s | −11 % |
| Ej_2 | GLE | idéntico | 268,3 s | 248,7 s | −7 % |

«Idéntico» es literal: mismo `repr` de coma flotante, mismo centro, mismo
radio, mismos recuentos.

### Cómo hay que leer esta tabla, y qué filas no dicen nada

Son **dos procesos distintos separados por minutos**, que es justamente el modo
de medir del que `AGENTS.md` desconfía. Sólo la mitad superior de cada bloque
resuelve: **−48 % a −64 % está muy por encima de cualquier ruido** y coincide
con el A/B en el mismo proceso, que dio 1,77 s → 0,94 s con una deriva de
control del 1 %.

Las filas de Lowe-Karafiath, Spencer y GLE **no dicen nada**, y el mejor
argumento de que no dicen nada está en la propia tabla: Lowe sale −24 % en un
modelo y **+9 % en el otro**, con un cambio que no puede haberlo perjudicado.
Ese es el suelo de ruido de esta máquina. Los tres métodos rebanan una vez por
superficie y luego iteran mucho, así que la congelación —que ahorra en el
rebanado— apenas les toca; medido aparte en el mismo proceso, la congelación
daba −6 % en Spencer con un control que derivaba un 10 %, o sea nada.

Lo que sí es firme, y no depende del reloj: el trabajo suprimido. Antes, cada
dovela pagaba dos reconstrucciones de la firma —27 342 en una corrida de 605
círculos, 1,5 M de `round()`—. Ahora paga cero.

## 5 · Lo que se dejó fuera a propósito

**El arranque en caliente de λ** —sembrar cada *inner solve* con la `F`
convergida del λ anterior en vez de con `initial_fos = 1.0`— es probablemente
el mayor ahorro que queda en Spencer y GLE. No entra en esta versión porque
**mueve los números dentro de la tolerancia**, y esta versión se ha definido
por lo contrario. Si se aborda, exige revalidar Ej_1, Ej_2 y los cinco casos
publicados de `validacion/casos/`, y su changelog tendrá que enseñar el
desplazamiento de cada uno.

## 6 · Anomalía encontrada de paso, NO corregida

`ogr_gui/canvas/canvas_view.py:1966-1968`, arrastre de un contorno entero:

```python
for vi, v in enumerate(b.polyline.vertices):
    v.x = ox0 + dx
    v.y = oy0 + dy
```

`Vertex` es un `@dataclass(frozen=True, slots=True)`. Reproducido:

```
FrozenInstanceError: cannot assign to field 'x'
```

Es decir, arrastrar un contorno completo lanza al primer movimiento del ratón.
Apareció al escribir el test de invalidación in situ de esta versión —el test
intentó editar así porque el comentario del lienzo dice que es así como se
edita— y se reporta antes de tocarlo, según la regla 6. No entra aquí porque
no tiene nada que ver con el tiempo de cómputo y merece su propio diagnóstico:
hay que averiguar desde cuándo, qué modos de herramienta pasan por ahí y por
qué ningún test lo cubre.

---

## Archivos

| archivo | qué |
|---|---|
| `ogr_core/project/project.py` | `regions_frozen()`; atajos en `resolve_regions` y `bounding_box` |
| `ogr_slip2d/search.py` | `run()` pasa a plantilla; `run` → `_run` en las seis búsquedas |
| `ogr_slip2d/methods/spencer.py` | corte del muestreo de λ en el primer cambio de signo |
| `ogr_slip2d/methods/gle.py` | íd. |
| `tests/test_regions_freeze_v193.py` | la congelación acelera, y la garantía sobrevive |
| `tests/test_lambda_sampling_v193.py` | el corte, y las dos rutas que aún barren entera |

© 2026 Samuel Sáez López — UPCT — AGPL-3.0-or-later
