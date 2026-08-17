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

## 0a · GLE bajo Simulated Annealing no devuelve nada — REGRESIÓN de v0.1.89

**Estado**: introducida a sabiendas, medida y acotada. Regla 6.

El cambio del rebanador de v0.1.89 —cortes de dovela en los vértices de la
propia superficie— deja a **GLE/Morgenstern-Price combinado con Simulated
Annealing** con **0 superficies válidas**. Medido en las semillas 0 a 7 y con
18, 27, 36, 54 y 72 dovelas: siempre cero. No es un borde frágil, es
sistemático.

**Por qué se aceptó igualmente.** El mismo cambio arregla un **número
equivocado**: Block Search devolvía 0,65-0,82 en un talud estable cuyo mínimo
circular es 1,1239, sobre superficies con escalones casi verticales más
estrechos que una dovela —invisibles para m-alpha, que veía 0,50 contra un
límite de 0,2. Con el arreglo, las cinco semillas dan 1,13-1,16. Un número
equivocado que un usuario se creería es peor que una ausencia visible de
número.

**Está acotado**, y eso es parte del argumento:

| | con el cambio |
|---|---|
| GLE + Simulated Annealing | **0 válidas** (semillas 0-7) |
| GLE + Block Search | 10-17 válidas, FoS 1,03-1,18 |
| GLE + Grid Search circular | intacto, 340 válidas — los círculos no tienen vértices |

Lo que **no** se sabe: por qué. Las anchuras de dovela no degeneran (mínima
0,31 m, razón máx/mín 5,3), así que no son astillas, y no cambia con el número
de dovelas. Está en `tests/test_annealing_bootstrap_v139.py` como test que
afirma el fallo, de modo que **el día que GLE funcione la suite se pondrá roja
y alguien tendrá que venir a borrarlo**.

Relacionado con el pendiente 0 (SA converge peor que un círculo) y con
`docs/audits/spencer_gle_interslice_v179.md`, donde ya consta que GLE es el método que peor converge: en la auditoría por
círculo de v0.1.89 converge en el 57-64 % de los círculos donde la referencia
sí lo hace. Es probable que los tres sean el mismo sitio.

---

## 0 · Simulated Annealing converge peor que un círculo — NUEVO en v0.1.89

**Estado**: reportado con medidas, sin corregir. Regla 6.

Apareció al arreglar el pendiente 2. Con la geometría corregida, sobre un
talud cuyo mínimo **circular** es 1,1239, SA devuelve **1,6564**. Una búsqueda
no circular no puede hacerlo peor que un círculo: los círculos están en su
espacio de búsqueda.

No es lo mismo que los dos defectos que sí se corrigieron en v0.1.89 (el
predeterminado de m-alpha y los cortes de dovela en los vértices). Con
aquellos arreglados, SA pasó de 0,500 —basura— a un rango físico, y ahí se
quedó corto.

**`generation_steps` deja de hacer nada, y no es monótono.** Medido sobre ese
modelo, con 9 vértices y 25 dovelas:

| `generation_steps` | evaluaciones válidas | FoS |
|---|---|---|
| 50 | 92 | 1,7491 |
| 300 | 257 | **2,1854** |
| 1 000 | 260 | 1,6564 |
| 3 000 | 260 | 1,6564 |
| 10 000 | 260 | 1,6564 |

Dos cosas mal, no una: satura en ~260 evaluaciones por muchas que se pidan
—un ajuste que no mueve el número a partir de 1000, que es la regla 7— y con
300 pasos da **peor** resultado que con 50, lo que apunta a la aceptación o al
enfriamiento, no al muestreo.

Sobre el modelo degenerado antiguo SA daba 1,1220 con 300, 1000 y 3000 pasos
—idéntico, y con 301 evaluaciones en los tres casos—, así que el síntoma
estaba ahí desde antes: lo que la geometría degenerada tapaba no era el
defecto, era el espacio de búsqueda en el que se nota.

Relacionado: `test_annealing_bootstrap_v139.py` ya documenta que el arranque
de SA dependía de la suerte (200 rechazos consecutivos con semillas
desafortunadas). Es probable que sea el mismo sitio.

Qué haría falta: instrumentar cuántas propuestas genera y cuántas acepta por
temperatura, y comprobar el calendario `T_k = T_0 · exp(-c · k^(1/n))` contra
Su (2009), que es la fuente citada en el docstring de la clase. Hasta
entonces, `test_sa_autorefine_v117.py` conserva la guarda de «nada por debajo
de 0,9» y **no** afirma cota superior.

---

## 2 · La geometría degenerada — CERRADO en v0.1.89

Eran **nueve** contornos en siete archivos, no cinco: la lista de aquí estaba
hecha a mano y se había quedado corta. El inventario se toma ahora con
`ogr_core.geometry.zero_thickness_spans()` ejecutando la suite con
`Project.add_boundary` instrumentado, que no se puede quedar obsoleto.

Lo que tapaba está en el changelog de v0.1.89 y en los pendientes 0 y 0a de
este documento.

Queda una limitación dicha: el detector **no impide** que un archivo nuevo
reintroduzca el contorno. Haría falta que todos los modelos de test pasaran por
una fábrica única.

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

## 4 · Diagnóstico fuera del runner — CERRADO en v0.1.89

Explicado, comprobado con un señuelo y con guarda: `pip install -e .` registra
un buscador que resuelve todo `ogr_*` a una ruta absoluta fija, y
`sys.path[0]` es el directorio **del script**, no el de trabajo. El runner
imprime ahora la procedencia y se niega a correr sobre otro árbol. Detalle en
el changelog de v0.1.89.
