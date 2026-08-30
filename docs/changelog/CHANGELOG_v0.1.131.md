# OGR Slip2D v0.1.131

**Evaluar un círculo dejaba escrito en él dónde había cortado el terreno,
y la siguiente evaluación de ese mismo objeto respondía por el corte
anterior.** `evaluate_circle` le fijaba al `SlipCircle` que recibía su
`x_left`, su `x_right`, sus grietas y su pared de grieta, «para que el
dibujo y el número no se contradigan». Nadie dibujaba desde ese objeto:
el lienzo, los exportadores y los informes leen `result.surface`. Lo que
sí hacía la escritura era **clavar la llamada siguiente**, porque un
círculo que llega con los extremos puestos nombra una masa y ya no se
vuelve a resolver.

Cierra los defectos **D36** y **D53** del banco de verificación, que eran el
mismo por dos caminos: D36 tenía su propio encargo y D53 salió al repartir D37
en 0.1.130. Cada uno propuso una causa distinta y **las dos eran falsas** — D53
la atribuía a la elección entre masas disjuntas, y sobre `modelo_ru.ogr` ese
círculo define **UNA** masa, la cuerda (45,838 · 158,730). No hay elección que
perder: lo que la segunda llamada pierde es el **recorte compuesto**, y se ve
en el tipo del resultado (`CompositeSurface` la primera vez, `SlipCircle` la
segunda). Lo que merece
recordarse no es el arreglo —son once líneas borradas— sino que **el
enunciado del defecto se equivocaba en su afirmación central y en su
signo**, que el contraejemplo llevaba meses escrito en el propio banco sin
que nadie lo leyera como tal, y que debajo había un segundo defecto que
nadie había mirado.

---

## 1 · Lo que el defecto decía, y por qué no se sostiene

La ficha de D36 insistía en un matiz, en negrita:

> **La mutación por sí sola no da un número distinto.** Volver a evaluar
> el mismo objeto —o uno nuevo con los límites exactos que él mismo
> escribió— devuelve `1.413221`, dígito a dígito.

Es cierto en el problema 27, que es donde se midió. **Y es falso en
general.** Medido en 0.1.130 sobre el problema 22 —Fredlund & Krahn
(1977), el artículo que introdujo la formulación general de equilibrio
límite precisamente para resolver superficies compuestas— con el círculo
que publica el enunciado (120, 90, R = 80) y `composite_surfaces = True`:

```
bishop_simplified   1ª 1.380905  (CompositeSurface)
                    2ª 1.980616  (SlipCircle)
                    3ª 1.980616  (SlipCircle)
      objeto nuevo     1.380905  (CompositeSurface)
spencer             1.380080 / 1.975948 / 1.975948
```

**1,9806 no es un número cualquiera**: es exactamente el que el changelog
de v0.1.111 publica como el defecto D15/A22-1 —el arco analizado *entero*,
con las bases de sus dovelas varios pies por debajo del suelo del modelo,
contra los 1,377–1,382 del artículo, +43 % del lado inseguro—. La segunda
llamada resucitaba un defecto cerrado veinte versiones antes.

La diferencia entre los dos problemas es la que explica el matiz: en el 27
no hay recorte compuesto, así que reevaluar la masa clavada devuelve la
misma masa. La medición que fundó el matiz era correcta y el modelo en el
que se hizo no discriminaba — la misma clase de error que la regla 6
recoge del episodio de `m_alpha`.

### El contraejemplo estaba escrito

`_tools/clasificar_d37.py::diagnosticar`, en el banco, lo tenía en su
docstring desde antes:

> `evaluate_circle` **muta el circulo que recibe** […] Medido en el
> problema 22: 1,122567 la primera vez y 1,670570 la segunda y la tercera.

Se había tropezado con ello, se había esquivado pasando una **fábrica** de
superficies en vez de una superficie, y se había anotado como una
peculiaridad de la herramienta de medida. Nadie volvió a leerlo como lo
que era: la refutación del matiz de D36.

### Y el signo era el contrario

D36 se clasificaba como **«enmascara: no da un número equivocado por sí
solo»**. No: llegaba a dos funciones de usuario. `run_global_minimum`
(`probabilistic.py:221-241`) y `run_sensitivity` (`sensitivity.py:210-234`)
reconstruyen **una** superficie y la evalúan en **todas** las muestras.
Emulando ese bucle con cinco clones **idénticos**, sin perturbar nada:

```
determinista:            1.380905  CompositeSurface
_rebuild_surface ->      SlipCircle, x_left = None
cinco muestras iguales:  [1.380905, 1.980616, 1.980616, 1.980616, 1.980616]
```

Cuatro de cada cinco muestras mentían, en silencio, en cualquier modelo con
Composite Surfaces. Y `_rebuild_surface` **descarta los extremos a
propósito** (no los pasa al constructor) justamente para que cada muestra
se resuelva de nuevo: la mutación deshacía esa intención a partir de la
segunda.

## 2 · El segundo defecto, debajo del primero

La ficha lo dejaba abierto como pregunta —«decide si `x_left`/`x_right`
deben seguir influyendo cuando llegan puestos»— y la respuesta tenía dos
mitades.

Honrarlos **sí** es una función usada: es cómo se pregunta por una masa
que no es la crítica, y es lo que hace
`tests/test_disjoint_masses_v1101.py` para evaluar por separado las dos
masas del problema 27. Eso se queda.

Lo que no puede quedarse es que esa rama —`_candidate_surfaces`, la que
devolvía el círculo tal cual— se saltara **las cuatro** operaciones que la
rama fresca aplica: curvatura inversa, truncado por grieta, **recorte
compuesto** y **contención**. Medido, con la opción compuesta APAGADA:

```
cuerda (45.838, 158.730)      escapa del suelo: True
circulo SIN resolver :  None        <- la contencion lo rechaza
circulo YA resuelto  :  1.980616    <- y_min del arco 10.0, suelo del modelo 15.0
```

Un círculo que el programa rechaza por salirse del modelo devolvía un
factor de seguridad en cuanto sus extremos llegaban puestos, contando el
peso de cinco pies de suelo que no existe. Es el error −103 de la
referencia, atravesado por la puerta de atrás.

## 3 · Qué se ha cambiado

Sólo `ogr_slip2d/search.py`.

- **`evaluate_circle` no toca su argumento.** Se borra la escritura. La
  masa analizada viaja en `result.surface`, que es de donde ya la leían el
  lienzo (`canvas_view.py:803`), los exportadores
  (`interpret_window.py:3426`) y los informes.
- **La rama de extremos puestos trabaja sobre una copia** y pasa por el
  mismo recorte compuesto y la misma contención que la rama fresca. La
  copia no es escrúpulo: `slice_surface` también escribe el truncado por
  grieta sobre lo que recibe (`slicer.py:1222-1227`), así que devolver el
  objeto del llamante habría dejado el arreglo a medias.
- La curvatura inversa **no** se vuelve a aplicar ahí, siguiendo el
  precedente explícito de v0.1.82 en el slicer: un par de extremos ya
  resueltos no se vuelve a agrietar.

Dos lectores de la mutación se han pasado al resultado:
`tests/test_moment_axis_v1126.py::_resolved_circle` ahora lee
`res.surface` (mismo valor, dígito a dígito: era justo lo que la mutación
copiaba), y la docstring de `_circle()` en `test_disjoint_masses_v1101.py`
deja de documentar la escritura como deliberada.

**Ningún otro sitio del programa pasa círculos resueltos**: las siete
búsquedas, el enjambre de partículas, la optimización y las dos entradas
estadísticas construyen un objeto nuevo en cada llamada. Comprobado uno a
uno, y es la razón por la que el arreglo 2 no puede mover un número de hoy
— cierra la puerta antes de que alguien la use.

### El coste, contado y no cronometrado

`composite` y `ext_verts` se calculan ahora antes de la primera salida en
vez de después, así que un círculo que no corta el terreno paga una
consulta de atributo y un `list()` de los vértices del contorno que antes
se ahorraba: del orden de 0,5 µs sobre unos 1500 círculos rechazados de
una rejilla de 5000, es decir **menos de un milisegundo por búsqueda**,
frente a los milisegundos que cuesta *cada* superficie resuelta. Se
prefiere eso a duplicar las dos líneas en las dos ramas, que es la forma
en que este archivo ya se ha estropeado antes.

## 4 · Qué lo sujeta

`tests/test_surface_purity_v1131.py`, quince pruebas sobre la geometría
publicada del problema 22 reconstruida en el repositorio. Los valores se
anclan a **Fredlund & Krahn (1977), tabla 22.3** (1,377 Bishop, 1,373
Spencer, tolerancia 2 %); 1,98 aparece sólo como el número que **no** debe
volver, y es el que publica el changelog de v0.1.111, no una medida de
aquí.

Contra el código de 0.1.130, **siete de las quince fallan**:

| prueba | lo que devuelve el código viejo |
|---|---|
| el objeto sale como entró | `x_left: None -> 45.838`, `x_right: None -> 158.730` |
| tres llamadas, un número | `[1.3814, 1.9806, 1.9806]` |
| y ese número es el publicado | 1.9806 en la segunda |
| el bucle estadístico da muestras iguales | `[1.3814, 1.9806, 1.9806, 1.9806, 1.9806]` |
| el mismo objeto sobre OTRO modelo | responde donde no hay respuesta |
| una masa nombrada se recorta igual | analiza el arco entero |
| una masa nombrada que se sale se rechaza igual | devuelve un factor |

Las otras ocho pasan en las dos versiones: son la premisa geométrica en
forma cerrada, la de que los extremos puestos siguen nombrando una masa
—que es la que impide «arreglarlo» ignorándolos— y la otra mitad de la
regla 7, que la contención deje pasar lo que sí está dentro del modelo.

Suite completa: **2904 / 2904**.

### El banco, y por qué la prueba que pedía el defecto no valía

D36 pedía correr `generar_comparativa.py` y comprobar que no se moviera
ninguna fila. Ese guion **sólo lee los `resultados.json` ya escritos**: no
ejecuta el motor, así que sus filas no pueden moverse pase lo que pase. La
prueba real es volver a correr los casos, y el banco entero cuesta ~9,3 h
(244 ficheros, 33.530 s registrados en sus propios `segundos`).

Se han rehecho **39**: los tres únicos modelos con `composite_surfaces`
—22, 22_ru y 57_compuesto, que es donde el arreglo 2 podía morder—, las
once corridas probabilísticas del banco —que es la vía de producción que
el defecto alcanzaba— y 25 más repartidos entre `grid`, `path`, `block`,
`auto_refine` y superficie publicada.

Contra la copia previa se movieron 65 números, **y ninguno es de este
cambio**: las fichas estaban en **0.1.127**, tres versiones atrás. La
atribución se hizo con el A/B que este proyecto exige — el mismo árbol, el
mismo proceso, cambiando **sólo** `search.py` entre la versión vieja y la
nueva:

| comparación | movidos | idénticos |
|---|---|---|
| ficha 0.1.127 almacenada → `search.py` viejo sobre árbol 0.1.131 | **65** | 1468 |
| `search.py` viejo → `search.py` nuevo, mismo árbol | **0** | **1527** |

Y la tabla comparativa, regenerada antes y después de la re-corrida:
586 filas, **OK 211 / REVISAR 101 / DISCREPANCIA 91** → **210 / 100 / 92**.
(De paso: los `486 filas, 176 / 101 / 95` que citaba el enunciado de D36 ya
no describían el banco antes de tocar nada — la tabla se había regenerado
con trabajo posterior.)

## 5 · Tres cosas que la re-corrida ha sacado, y que NO son de esta versión

Estaban tapadas porque las fichas llevaban desde 0.1.127 sin rehacerse.
Van a ficha aparte, sin tocar (regla 6):

1. **El 27 encuentra ahora un mínimo mucho más bajo**: Bishop 0,4074 →
   0,2308 (−43 %), y lo mismo los otros cuatro métodos, con las válidas
   pasando de 202 a 682 y el círculo crítico moviéndose de (64, 232, R
   148,79) a (68, 224, R 140,02). La columna del círculo **publicado** no
   se mueve (+0,80 %), así que el veredicto de la fila sigue siendo `OK` y
   nadie lo habría visto. Encaja con la apertura de población de 0.1.129
   (focos y Slope Limits llegando a las siete búsquedas); falta decidir si
   0,23 es un mecanismo o una superficie degenerada.
2. **El 79, caso 2 superficial, Spencer: el círculo publicado da `nan`.**
   La fila pasa de `REVISAR` a `DISCREPANCIA`. Antes ese valor no existía;
   ahora existe y no es un número.
3. **El 102, Spencer: el factor sobre el círculo publicado ha
   desaparecido** (2,4582 → sin dato), y la fila pasa de `OK` a
   `SIN DATO`.

## 6 · Lo que se encontró leyendo, y tampoco se ha tocado

Tres cosas, con evidencia, para ficha aparte (regla 6):

1. **`Add Surface (centre & radius)` no hace nada.** Añade el círculo a
   `project.user_surfaces` (`main_window.py:2136-2138`) y **ningún otro
   sitio del repositorio lee ese atributo**: tres apariciones en total,
   las tres en esas tres líneas. Una acción de menú visible cuyo efecto no
   existe — regla 7.
2. **`_rebuild_surface` degrada una superficie compuesta a círculo.** El
   `to_dict()` de una `CompositeSurface` lleva `radius`, así que la
   condición `"radius" in surface_dict` la reconstruye como `SlipCircle`.
   Con la opción puesta se vuelve a componer y no se nota; sin ella, sí.
3. **`generar_comparativa.py` no vale como prueba de no-regresión**, y el
   enunciado de D36 la proponía como tal: ese guion sólo LEE los
   `resultados.json` ya escritos, no ejecuta el motor, así que sus 486
   filas no pueden moverse pase lo que pase. La prueba real es volver a
   correr los casos — y el banco entero cuesta **~9,3 h** (244 ficheros,
   33.530 s registrados en sus propios `segundos`).
