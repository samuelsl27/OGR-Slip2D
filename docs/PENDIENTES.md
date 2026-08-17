# Pendientes abiertos

Lo que quedó sin cerrar y **por qué**, para que no se pierda entre
changelogs. Cada entrada dice qué falta exactamente y qué haría falta para
cerrarla. Se borra la entrada cuando se cierra, no se marca.

Origen: trabajo sobre los ejemplos Ej_1 y Ej_2 de `referencias/Ejemplos/`
(v0.1.84 en adelante).

---

## 1 · La regla de radios del Grid Search — CERRADO en v0.1.88

La medición que faltaba se ejecutó
(`referencias/Ejemplos/00_2026_08_17_Test_Regla_radios`) y la regla quedó
despejada por lectura directa de los `.s01`, sin ajustar nada. Derivación,
comprobación sobre 949 centros y tablas en
`docs/audits/grid_radius_rule_v188.md`.

Queda **una** pieza sin medir, y sólo ésa: en los seis modelos los Slope
Limits están en su posición automática, así que los datos no distinguen si
`d_max` se mide a los *puntos límite* o a los *extremos del perfil*, ni si
`d_min` se mide sobre el perfil recortado o el completo. Se implementó la
lectura documentada.

### Qué haría falta para cerrar también eso (a ejecutar en Slide2)

> Los modelos **A1** y **B1** tal como están —rejilla de pocos centros,
> `Radius Increment = 1`, dos círculos por centro— pero con los **Slope
> Limits movidos hacia dentro**, cada uno a una `x` que **no** caiga en un
> vértice del perfil. En Ej_1, por ejemplo, x = 20 y x = 100 (sus vértices
> están en 0, 50, 75 y 120).
>
> Los dos radios de cada centro responden las dos preguntas de golpe, y de
> paso dicen si el retranqueo sigue siendo el 5 %.

Sin esa corrida, mover los límites en OGR se comporta según la lectura
documentada, y el docstring de `GridSearch._radius_bracket` lo dice con esas
palabras. No bloquea nada: los dos modelos de referencia y los cinco casos
publicados se reproducen igual.

### Reportado de paso, no corregido: `AutoRefineSearch` recorta igual de mal

`GridSearch._slope_surface` recortaba a los Slope Limits **filtrando vértices
por `x`**, lo que tira el tramo que un límite corta por el medio. v0.1.88 lo
arregló ahí, interpolando las dos abscisas límite.

`AutoRefineSearch.run` (`ogr_slip2d/search.py`, sobre la línea 1031) hace
exactamente lo mismo:

```python
poly_pts = [v for v in top if x0 - 1e-9 <= v.x <= x1 + 1e-9]
```

Con los límites en su posición automática da igual, porque coinciden con los
extremos del perfil — que es el caso de todos los tests y de los dos ejemplos.
Con límites metidos hacia dentro en una `x` sin vértice, la polilínea de
partida termina en el último vértice interior en vez de en el límite.

**No se ha corregido a propósito** (regla 6): no hay dato de referencia para
*esta* búsqueda, así que arreglarlo movería números sin nada contra lo que
comprobarlos. La corrida de Slide2 que pide el apartado anterior serviría
también para esto.

`BlockSearch` (línea 1326) usa sólo el rango de `x`, no la polilínea, así que
no le afecta.

### Decisión tomada en v0.1.88 que conviene revisar: `min_radius = 0`

El predeterminado pasó de 2,0 a **0,0** en `GridSearch` y de 3,0 a 0,0 en
`analysis_runner.build_search`, para que la configuración de fábrica —la que
usan la interfaz y la CLI— muestree **exactamente** la población de la
referencia. La referencia no tiene control de radio mínimo; ofrece *Minimum
Elevation* y *Minimum Depth*.

Está medido que no cambia ningún resultado: con 3,0 y con 0,0 el factor de
seguridad de los cinco casos publicados es idéntico, y sólo se mueven los
recuentos de válidas en unas unidades.

**Lo que queda por decidir es de producto, no de cálculo**: si un usuario de la
interfaz se beneficia de un suelo de 3 m que le ahorre círculos diminutos, o si
vale más que la interfaz reproduzca la referencia sin excepciones. Se eligió lo
segundo. Cambiarlo es una línea en cada sitio; si se cambia, hay que decir en
la documentación que la interfaz **no** reproduce el muestreo de la referencia.

---

## 2 · La geometría degenerada compartida por cinco archivos de test

**Estado**: conocido, sin corregir a propósito.

Siete archivos de test usan este contorno externo:

```
(0,0) (60,0) (60,12) (crest,12) (toe,0)
```

La última arista vuelve por encima de la primera: entre `x = 0` y el pie en
`x = 30`, la superficie del terreno y la base del modelo son la misma recta
`y = 0`, y ese tramo **no encierra suelo**.

v0.1.84 corrigió los dos que dependían de ello para pasar
(`test_supports_v114.py` y `test_slope_search_v117.py`, ambos con 10 m de
cimiento). Los otros cinco —`test_block_search_v117`,
`test_grid_search_v117`, `test_noncircular_v115`, `test_sa_autorefine_v117`,
`test_strength_models_v115`— siguen en verde porque no afirman nada
sensible a la degeneración.

**Por qué no se tocaron**: cambiar cinco modelos que pasan movería números
que nadie ha pedido mover. Queda anotado para quien se lo encuentre.

---

## 3 · Del punto 4 del informe, lo que no se hizo

**Estado**: hecho lo esencial en v0.1.87; queda lo accesorio.

El panel *Query Slice Data* ya se abre, se rellena sin guiones, coincide
con la tabla de la referencia al 0,5 %, resalta la dovela y dibuja las
flechas de fuerzas. La referencia describe además cuatro botones del
diálogo que **no** se han implementado:

- **Hide Geometry / Show Geometry** — oculta todo el modelo menos la
  dovela seleccionada, para capturas.
- **Zoom Slice** — lleva la dovela seleccionada al centro de la vista.
- **Copy** — copia los datos de la dovela al portapapeles.
- El «roll-up» del diálogo (plegarlo sin cerrarlo). Aquí el panel es un
  dock, y un dock ya se pliega, así que probablemente no aplica.

Ninguno cambia un número; son comodidades. Se dejan fuera porque el
informe pedía que el panel **se abriera y mostrara las propiedades**, y eso
está.

Falta también la flecha de **fuerzas entre dovelas**: se dibujan peso,
normal en la base y cortante en la base. Las interdovela solo existen como
tales en los métodos que las resuelven (Spencer, GLE, Lowe-Karafiath), y
dibujarlas para Bishop u Ordinary sería dibujar una hipótesis, que es el
mismo error que v0.1.82 corrigió en la línea de empuje.

---

## 4 · Diagnóstico fuera del runner que no reproducía el fallo

**Estado**: sin explicar.

Diagnosticando la caída de `test_support_increases_fos` (v0.1.84), un
script suelto que replicaba el test **línea por línea** daba el mismo
resultado en el árbol de trabajo y en HEAD, y habría llevado a la
conclusión contraria a la correcta. Instrumentando **dentro** del runner
apareció la diferencia real: HEAD 10 válidas y crítica 2,1279, árbol de
trabajo 0 válidas.

No se ha averiguado por qué el script suelto no reproducía. Mientras no se
sepa, **el diagnóstico se hace dentro del runner**, que es donde ocurre el
fallo.
