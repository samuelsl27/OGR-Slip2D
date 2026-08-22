# OGR Slip2D v0.1.101 — dos puertas al mismo motor, y la que respondía por una lámina de 0,9 pies

`BaseSearch` tiene dos entradas públicas al cálculo. Sobre el **mismo círculo**
daban dos factores de seguridad distintos, y cuál te tocaba dependía de qué
método hubieras llamado:

```
evaluate_circle (search.py)  -> 1,407143     <- el mecanismo real, 22 pies
evaluate_surface(search.py)  -> 34,319865    <- una lámina de 0,9 pies
```

Un **factor 24**, sin un solo aviso. Se cierra la anomalía **A27-1** del banco de
verificación (defecto **D06**).

---

## 1 · Qué pasaba

Un círculo que corta el terreno **más de dos veces** no define un mecanismo de
rotura: define varias masas deslizantes **disjuntas**, y el factor de seguridad
del círculo es el **menor** de los de ellas. Recorrerlas se añadió a
`evaluate_circle` en **v0.1.84**, y su comentario lo explica.

`evaluate_surface` se quedó fuera de aquel arreglo. Llamaba a `slice_surface`
directamente, y un círculo sin extremos resueltos lo resuelve
`SlipCircle.intersect_with_ground`, que devuelve **la primera masa por la
izquierda** — la primera, no la crítica.

El caso que lo delata es el círculo que publica el **problema 27** del banco
(Malkawi & Sarma 2001, tomado del manual de referencia de XSTABL v5, Sharma
1996): centro (59,52 · 219,21), R = 157,68 pies. Ese arco pasa por
`y = 63,005416` en `x = 38`, o sea **5,4 milésimas de pie por encima** del
vértice del pie (38 · 63). Con eso corta el terreno **cuatro veces**:

| Masa | Extensión | Espesor máx. | Qué es |
|---|---|---|---|
| A | x = 17,619 → 37,952 | 0,935 ft | una lámina, sin significado mecánico |
| B | x = 38,010 → 169,893 | 22,09 ft | **el mecanismo real** |

y `evaluate_surface` respondía por la **A**:

| Método | masa A (lo que devolvía) | masa B (lo correcto) | factor | publicado |
|---|---|---|---|---|
| Bishop simplificado | 34,319865 | 1,407143 | 24,4 | 1,396 |
| Janbu corregido | 34,525574 | 1,402560 | 24,6 | 1,391 |
| Lowe-Karafiath | 5,000000 | 1,406884 | 3,6 | 1,411 |
| Spencer | 34,195401 | 1,407122 | 24,3 | 1,402 |
| GLE / M-P | 34,195401 | 1,407132 | 24,3 | 1,398 |

Lowe-Karafiath no es la excepción amable que parece: sobre la lámina **topa con
su propio techo de 5,0** en lugar de informar de un 34, con lo que el disparate
queda disimulado como un número plausible.

## 2 · El arreglo

Un solo archivo, `ogr_slip2d/search.py`. El bucle sobre las masas —trocear,
exigir tres dovelas, filtrar por `min_area`, resolver, quedarse con el menor—
estaba escrito **dos veces**: entero en `evaluate_circle` y, dentro de
`evaluate_surface`, la misma secuencia sin el recorrido. Sale a un privado,
`BaseSearch._best_of_masses`, y las dos puertas lo comparten; `evaluate_surface`
reparte por tipo de superficie:

```python
if isinstance(surface, SlipCircle):
    return self.evaluate_circle(project, surface)
return self._best_of_masses(project, (surface,))
```

No se ha generalizado `_candidate_surfaces` a polilíneas, y la razón está medida
más abajo: una polilínea no tiene masas entre las que elegir.

`evaluate_circle` conserva intacto su contrato de escribir la masa analizada
sobre el círculo del llamante — si no, el dibujo y el número discrepan.

## 3 · Lo que se encontró por el camino, que es la mitad del valor

### 3.1 · El rodeo escondía la anomalía de su propia verificación

La ficha del defecto daba como prueba una corrida del banco sobre el círculo
publicado. Esa corrida **imprime el número bueno desde antes del arreglo**: el
guion del banco lleva tiempo repartiendo los círculos a `evaluate_circle` a
mano, con un comentario que cita esta misma anomalía. Es decir, el criterio de
cierre de un defecto se comprobaba con una herramienta que lo rodeaba.

Es el mismo patrón que **A27-1b**, donde el `SlipCircle` que sale mutado de
`evaluate_circle` hacía que la anomalía «desapareciera» si se medía en el orden
equivocado. Dos veces la misma lección: **una medida que no puede fallar no
mide**. La verificación real vive ahora dentro de la suite.

### 3.2 · Las cifras heredadas eran de otro modelo

La ficha decía 36,540278 frente a 1,410782, factor 26. Esos números son de
**antes** de activar el peso saturado de Soil 1 (124,2 pcf, que estaba guardado
y sin usar: un 6,3 % de peso de menos bajo el nivel freático). Con el modelo
correcto son 34,319865 y 1,407143, factor 24. La anomalía era real; su tamaño,
no el que se venía citando.

### 3.3 · El segundo caso del criterio de cierre no existe

D06 pedía además que el círculo publicado del **problema 37** dejase de
resolverse sobre «una lámina bajo la banqueta izquierda». Medido:

```
terreno:  (0,5) (5,5) (17,17) (40,17)
raíces:   4,9985   5,0017   17,7718        <- tres, no cuatro
masas:    [5,0017 , 17,7718]               <- una sola
las dos puertas: 0,765359   (publicado 0,764; extremos 5,00 / 17,773)
```

Los 5,94 unidades² que un auditor de áreas contó como segunda masa están entre
el **borde izquierdo del modelo** (x = 0, donde el arco va a y = 2,78 bajo un
terreno a y = 5) y la primera raíz. `candidate_chords` empareja raíces
**consecutivas** y nunca el borde del modelo, y hace bien: una masa que sólo
aflora por un extremo no es un mecanismo. El 37 vale como **regresión**, no como
caso.

### 3.4 · Un test que falló y enseñó algo: la tolerancia de fusión se traga el roce

La primera versión del test daba por hecho que el mismo arco, entregado como
**polilínea** de 26 vértices sobre las dos masas, sería rechazado por asomar
sobre el terreno. No lo es: devuelve 1,5632.

El motivo no es el rechazo, que funciona —basta con **0,05 pies** de asomo para
que `slice_surface` descarte la superficie entera—, sino **dónde se juzga**: en
los bordes de dovela. El vértice colocado en `x = 38,0` no llega a ser borde,
porque `_slice_boundaries` fusiona cortes más próximos que una milésima del
ancho de rotura (0,152 ft aquí) y ya tenía un cruce del nivel freático en
`x = 37,9498`. Lo que se trocea es entonces el **polígono de cuerdas** por los
vértices, que sí va por debajo del terreno.

No es una respuesta equivocada sobre el círculo: es la respuesta correcta sobre
**otra superficie**, la que se ha entregado. Queda anotado en el test para que
el siguiente no repita el intento, y **no se ha tocado la tolerancia**: hacerlo
sería mover el troceado de todo el programa por una hipótesis de un test.

### 3.5 · Dos rechazos que `evaluate_surface` no tenía, y que ahora sí

Esto también salió de un test que falló. Al repartir los círculos por
`evaluate_circle`, `evaluate_surface` hereda sus dos descartes:

- el **salto temprano por caja envolvente** (un círculo que no puede alcanzar el
  modelo);
- la **regla de contención** para superficies circulares no compuestas, que la
  referencia informa como error −103 y que `composite_surfaces` desactiva.

El círculo de control de la primera versión del test —centro (90 · 130),
R = 70— es justo uno de esos: una sola masa, pero se sale por el lecho rocoso.
Antes `evaluate_surface` le daba un número y `evaluate_circle` lo rechazaba.
**Ahora las dos puertas lo rechazan**, y eso es lo que se quería: una superficie
no puede depender de por dónde entres, ni para responder ni para negarse. Hay
una clase de test para ello.

Comprobado que el reparto **no mueve el caso de una sola masa**: sobre el
círculo de referencia de Ej_1 (88,0 · 70,5 R 47,212) las dos puertas ya
devolvían el **mismo float bit a bit en los nueve métodos** antes del cambio, y
lo siguen devolviendo.

## 4 · Tests

`tests/test_disjoint_masses_v1101.py`, seis clases, 17 casos, 1,4 s. El modelo
del problema 27 se construye dentro del test —el banco vive fuera del
repositorio— con el perfil y el lecho rotulados en la figura 27.1 y la tabla
27.1 de materiales. El **nivel freático se declara como lo que es**: una medida
por píxeles, no un dato publicado, y por eso los valores publicados se exigen al
1 %, la misma tolerancia que ya usa `test_published_cases_v179.py` para un
círculo crítico publicado.

Nada de lo que afirma es una instantánea:

1. **La premisa** — cuatro cortes, dos masas, 0,935 ft contra 22,09 ft, el roce
   de 5,4 milésimas — sale de coordenadas publicadas, sin ningún factor de
   seguridad de por medio.
2. **La selección es una identidad**: el factor del círculo entero tiene que ser
   **igual** —no parecido— al **mínimo** de los factores de sus masas evaluadas
   una a una. Se cumple bit a bit en los cinco métodos. Y las dos masas tienen
   que estar lejos (`max > 2·min`), o el caso no probaría nada; el listón está
   puesto al más flojo de los cinco, que es Lowe-Karafiath con su techo.
3. **El ancla externa**: los cinco métodos, **por `evaluate_surface`**, dentro
   del 1 % de la tabla 27.2, que publica dos programas independientes. Es la que
   dice que la masa elegida es la *correcta* y no sólo la menor, y es la que
   fallaba antes de este cambio.
4. **Lo que no debe romperse**: sobre un círculo de una sola masa,
   `evaluate_surface` devuelve el mismo float que `slice_surface` +
   `compute_fos` a pelo, que es el camino que tenía.
5. **Las polilíneas**: 0,5 y 0,05 pies de asomo se rechazan; el arco de la masa
   real, intacto, se analiza y cae a 0,15 % del círculo.
6. **Los rechazos compartidos**: el círculo que se sale del terreno y el que no
   alcanza el modelo, negados por las dos puertas.

## 5 · Lo que queda abierto

- **A27-1b**, a propósito: `evaluate_circle` deja mutado el `SlipCircle` que
  recibe. Está documentado y es deliberado —si el círculo no se queda con la
  masa analizada, el dibujo y el número discrepan—, y el criterio de cierre de
  D06 no lo incluye. Lo que sí conviene recordar es su efecto de medición: una
  segunda evaluación sobre el mismo objeto reutiliza esos extremos.
- La tolerancia de fusión de `_slice_boundaries` (§ 3.4) puede hacer
  desaparecer un vértice de la superficie cuando cae junto a un cruce de
  material o de nivel freático. Medido y anotado; no tocado.
