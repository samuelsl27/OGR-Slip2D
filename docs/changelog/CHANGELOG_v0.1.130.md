# OGR Slip2D v0.1.130

**Un resultado que ha convergido deja de contarse como un cálculo
fallido.** Spencer y GLE escribían la relajación del criterio de empuje
interdovela en `error_message`, y ese campo es un veto: puntúa la
superficie `inf` y la excluye de `critical` sin salida de socorro. El
mensaje decía *«the answer is reported with the criterion relaxed»* y la
respuesta no se reportaba — se borraba.

Sale de repartir por causa el defecto **D37** del banco de verificación,
que llevaba desde 0.1.97 con la causa sin establecer. Lo que merece
recordarse no es el arreglo, que son cuatro líneas: es que **la causa que
el defecto proponía no era ninguna de las tres**, que la mitad de las
filas que contaba no eran comparables, y que el arreglo, medido, **no
mueve ni un factor de seguridad**.

---

## Qué estaba mal

`LEMResult` lo tenía escrito desde v0.1.32 (`methods/base.py:66-77`):

```python
    admissible: bool = True
    # Why the surface was judged inadmissible. Deliberately NOT stored in
    # ``error_message``: that field marks a FAILED calculation and feeds
    # ``is_valid``, whereas an inadmissible surface has a perfectly
    # converged (but physically unreliable) factor of safety.
    admissibility_note: str = ""
```

Y `interslice.py:564` decía lo mismo desde el otro lado: la pasada estricta
sobre el empuje **«es una PREFERENCIA, no un veto»**, con la razón medida —
en un talud muy reforzado las caras salen en tracción neta a cualquier λ, y
convertir eso en un NaN pierde cobertura a cambio de nada.

`spencer.py` y `gle.py` hacían lo contrario en las cuatro ramas donde
formulan el resultado. Una superficie con el criterio relajado quedaba
`is_valid=False`, y con eso:

- `surface_score` la puntúa `inf` (`search.py:149`);
- `SearchResult.critical` la filtra **sin el `ok or valid`** que sí protege
  a las inadmisibles (`search.py:210`);
- en Auto Refine, Simulated Annealing, PSO, el refinado de Slope Search y
  `_optimize_each_minimum` ni siquiera entra en `evaluations`, así que
  tampoco siembra el refinado de su vecindario.

## Lo que cuesta, medido

A/B en el mismo proceso, con el comportamiento anterior reconstruido
envolviendo `compute_fos`, **y en serie**: la rejilla se reparte por
procesos y un hijo reimporta el módulo, así que la primera medida —en
paralelo— dio las tres columnas idénticas al último dígito y **no medía
nada**. Es la trampa que AGENTS.md describe para el cronómetro, con otra
cara.

| problema · método | válidas | inválidas | inadmisibles | FoS |
|---|---|---|---|---|
| 85 · GLE, antes | 1106 | 8280 | 6 | 2,209135 |
| 85 · GLE, ahora | **1877** | **7509** | **777** | 2,209135 |
| 90 · Spencer, antes | 1898 | 5284 | 0 | 0,95209 |
| 90 · Spencer, ahora | **3124** | **4058** | **1226** | 0,95209 |
| 93 · Spencer, antes | 2166 | 5016 | 0 | 1,021155 |
| 93 · Spencer, ahora | **3178** | **4004** | **1012** | 1,021155 |
| 60 · Spencer, antes | 27 | 81 | 0 | 1,583149 |
| 60 · Spencer, ahora | **29** | **79** | **2** | 1,583149 |

La rama «antes» reproduce dígito a dígito lo que el banco tiene archivado
de 0.1.127, que es el control de que el A/B mide lo que dice medir.

**771, 1226 y 1012 superficies** pasan de *cálculo fallido* a *resuelta
pero no admisible*, que es lo que son. Y **el factor de seguridad no se
mueve en ninguno de los cuatro**, porque `critical` prefiere las
admisibles y sólo cae al resto cuando no hay ninguna. Eso no es un arreglo
a medias: es lo que «preferencia, no veto» significa, y que el número no se
mueva es la comprobación de que el defecto era un archivado equivocado y
nada más.

## Lo que NO se ha movido, y por qué importa

**«No hay bracket de λ» sigue siendo un veto.** Las dos ramas sin bracket
mezclaban dos juicios en un solo campo, y sólo uno se ha movido. Cuando la
búsqueda de λ no encuentra ningún cambio de signo, ambos métodos devuelven
el par más cercano y ponen `converged = abs(F_f − F_m) < 0.02`: eso es un
cálculo que ha fallado, se queda en `error_message` y se queda inválido.

La distinción estuvo a punto de perderse, y era el error de diagnóstico más
caro de esta versión. El encargo atribuía el problema 85 a *«la búsqueda de
lambda sin converger»* y el 91 a *«centro en el borde de la rejilla»*.
Medidos, los dos caen por la rama **sin bracket**: lo que el banco publica
sobre su círculo es un **valor de reserva**, no una medida, y ningún
arreglo del flag de empuje hace que su búsqueda lo encuentre. Haberlos
metido en el mismo saco que el 90 y el 93 habría reclamado un arreglo para
cuatro filas que el cambio no alcanza.

## D37, repartido: la causa no era ninguna de las tres

La ficha proponía **resolución de la rejilla, alcance, o el filtro
`min_area`**. Repartidas las 133 filas con `_tools/clasificar_d37.py`:

- **53 no eran comparables.** Una superficie de `referencia.json` puede
  declarar su propio `.ogr`, y cuando lo hace el `f_pub` habla de un modelo
  y el mínimo de otro. El problema 84 aportaba 18 filas así —su círculo del
  perfil I contra el mínimo del perfil IV, hasta −33,90 %— y el 78 doce. No
  eran búsquedas que fallaran: eran **dos modelos distintos restados**;
- **6 son C0**, el método sin bracket (85 y 91);
- **4 son este defecto** (60, 90, 93);
- **72 en 31 problemas son D37 de verdad**, y de las 35 con rejilla
  declarada el centro publicado cae **dentro de la rejilla en las 35**. No
  es alcance;
- **`min_area` no interviene en ninguna.** Cero filas. Medido además a pelo
  en el problema 22: con el filtro de 0 a 50 el círculo publicado da
  **1,122567 en los cinco valores**, sin mover un dígito.

Es resolución, con un límite que hay que escribir: **una rejilla sólo
devuelve círculos centrados en sus nodos**, y un centro publicado con
decimales no es un nodo casi nunca. El 24 ya lo había medido — refinar a
61 × 61 baja de 1,4530 a 1,4441 y **sigue** por encima de 1,4411 — porque
el bracket de radios discretiza además del centro. El criterio de cierre de
D37, tal y como estaba escrito, era insatisfacible.

## Un defecto nuevo, medido y NO corregido: D53

**`evaluate_circle` muta el círculo que recibe** (`search.py:849-855`): le
escribe `x_left`, `x_right` y las grietas de la masa que acaba de analizar.
La intención está escrita y es razonable —que el dibujo y el número hablen
de la misma masa—. La consecuencia no: la función **deja de ser
idempotente**.

Problema 22, mismo proyecto, sin tocar nada entre llamadas:

| | objeto nuevo cada vez | el mismo objeto |
|---|---|---|
| llamada 1 | 1,122567 | 1,122567 |
| llamada 2 | 1,122567 | **1,670570** |
| llamada 3 | 1,122567 | **1,670570** |

En una búsqueda no muerde, porque cada candidata se construye nueva. **En
el probabilístico sí**: `run_global_minimum` reconstruye la superficie una
vez (`probabilistic.py:221`) y la reevalúa en cada muestra (`:241`).
Reproducido sin variar ningún parámetro entre muestras, la muestra 1 da
1,122567 y las demás 1,670570 — toda la distribución se construye sobre un
mecanismo distinto del de la primera muestra.

Queda **reportado y sin corregir** por la regla 6, y porque el arreglo
evidente no es obviamente el bueno: quitar la mutación rompe lo que el
comentario defiende. Ficha completa en el banco.

## El camino equivocado que costó una medida

La primera versión del clasificador evaluaba el mismo objeto `SlipCircle`
dos veces —una con el filtro de área suelto y otra con el del modelo— y
concluyó que en el problema 22 «los dos regímenes miden masas distintas».
Era falso: medía la mutación de arriba. El clasificador construye ahora una
superficie nueva por evaluación, y con eso la causa «otra masa» y la causa
«filtro» **desaparecen las dos**, de una fila y de cero a cero.

## Archivos

- `ogr_slip2d/methods/spencer.py` — las dos ramas
- `ogr_slip2d/methods/gle.py` — las dos ramas
- `tests/test_relaxed_thrust_v1130.py` — nuevo, 10 tests

## Verificación

Suite completa, sin argumentos.
