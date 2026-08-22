# OGR Slip2D v0.1.99 — un material sin resistencia mataba la búsqueda, y nueve métodos daban seis respuestas

Un material con `c = 0` y `φ = 0` es un dato legítimo. El problema 27 del banco
de verificación lo exige, porque es lo que publicó su fuente. Hasta esta versión
un círculo cuya masa cayera **entera** dentro de un material así no era una
superficie descartada con un aviso: era el análisis completo muriendo con un
*traceback* que salía de `GridSearch.run` sin capturar.

Se cierra el defecto **D04** del banco (anomalía A27-4).

Lo que se buscaba era un `ZeroDivisionError` en dos métodos. Lo que había eran
**seis respuestas distintas repartidas entre los nueve**, y cinco de ellas
publicaban un número inventado sin decirlo.

---

## 1 · El mecanismo, que es aritmético y no físico

`ogr_slip2d/methods/bishop.py`, bucle de iteración. La única guarda era contra
un resultado **no finito**:

```python
new_fos = numerator / denominator
if not math.isfinite(new_fos):     # 0.0 ES finito: pasa de largo
```

Con `c = 0` y `φ = 0` el numerador de Bishop vale **exactamente** `0.0`, así que
`fos` se queda en `0.0`. En la iteración siguiente:

```python
m_alpha = math.cos(s.base_angle) + (
    slide_sign * math.sin(s.base_angle) * tan_phi / fos)
```

evalúa `0.0 / 0.0`, que en Python es `ZeroDivisionError` y **no** `nan`. La
guarda de `abs(m_alpha) < 1e-6` que hay dos líneas más abajo nunca llegaba a
ejecutarse. `janbu.py` repetía el patrón con `n_alpha`.

## 2 · Lo que no se esperaba: seis modos de fallo, no uno

Medido en 0.1.98 sobre el círculo reproductor del problema 27 —centro (95, 260),
R = 170, masa de x = 106,97 a 167,77 entera dentro de Soil 2—:

| Método | qué devolvía | qué es eso |
|---|---|---|
| Bishop simplificado | `ZeroDivisionError` | mata la corrida |
| Janbu simplificado | `ZeroDivisionError` | mata la corrida |
| Janbu corregido | `ZeroDivisionError` | mata la corrida |
| Spencer | `nan`, «all sampled λ diverged» | **motivo falso**: λ no tenía nada que ver |
| GLE / M-P | `nan`, «all sampled λ diverged» | **motivo falso**, el mismo |
| Corps of Engineers #1 | `fos = 0.2`, sin motivo | **no es un factor de seguridad** |
| Corps of Engineers #2 | `fos = 0.2`, sin motivo | **no es un factor de seguridad** |
| Lowe-Karafiath | `fos = 0.2`, sin motivo | **no es un factor de seguridad** |
| Ordinary / Fellenius | `fos = 0.0`, sin motivo | el único con el número bueno |

El **0,2** es el hallazgo que más costaba ver, porque parece un factor de
seguridad y no lo es: es el **primer punto de la rejilla de F** con la que los
tres métodos de inclinación prescrita buscan el cierre del polígono de fuerzas
(`modified_swedish.py:382`, `grid = [0.2, 0.3, 0.4, …, 5.0]`), devuelto como
`best_fallback` cuando ningún punto cierra. La raíz verdadera está por debajo
del extremo inferior de esa rejilla, así que el método devolvía el extremo.
Salvaba la cara —`converged = False`, así que `is_valid` era `False`— pero
cualquiera que leyese `.fos` leía 0,2.

**Arreglar sólo los tres que reventaban habría dejado cinco métodos publicando
basura silenciosa**, que es exactamente el fallo que la regla 6 existe para
evitar.

## 3 · Qué hay que hacer con el cero, que no es obvio

Un factor de seguridad de cero sobre una masa sin resistencia ninguna es
**físicamente correcto**: esa masa no se sostiene. La pregunta no era cómo
evitar el cero, era qué debe hacer la búsqueda con él. Y no se ha elegido un
criterio: lo dice la documentación de referencia, en su tabla de códigos de
error, para **exactamente** esta condición —*«factor of safety = 0, possibly due
to normal / shear resistance = zero along part of the slip surface»*— en una
página que abre diciendo que cuando no se puede calcular un factor de seguridad
se escribe un código de error **en lugar** del factor, y que esos códigos son la
población que su interfaz llama *superficies inválidas*.

Traducido: **inválida contada con su motivo**, no un factor de cero compitiendo
por ser la superficie crítica. Y tiene que ser así, porque un cero gana toda
búsqueda: la respuesta a «cuál es la superficie crítica de este talud» pasaría a
ser «el trozo que no tiene resistencia», que es verdad y no sirve de nada.

En este programa eso es `error_message` puesto —con lo que `is_valid` es `False`
y las búsquedas la suman a `invalid_count`— y **no** `admissible = False`, que
está reservado para un factor **convergido** que falla un post-chequeo
(`methods/base.py`). El criterio de cierre que D04 llevaba escrito decía
«inadmisibles»; manda la documentación, y queda anotado en el banco.

## 4 · El arreglo, en cuatro capas

**1 · Un predicado compartido**, `LEMMethod.surface_has_no_shear_strength`, en
`methods/base.py`. Cierto cuando **ninguna** dovela ofrece resistencia: `c` y
`tanφ` valen cero en la base de todas, leídos por `BishopSimplified._local_c_phi`
—la única linealización que los nueve métodos ya comparten, así que el veredicto
vale para los modelos no lineales y para la succión igual que para
Mohr-Coulomb—. **Corta en la primera dovela con resistencia**, así que una
superficie normal paga una evaluación de envolvente.

No es una fórmula nueva: es el término resistente de Bishop (1955),
`c'·b + (W − u·b)·tanφ'`, que es idénticamente nulo si y sólo si `c` y `tanφ` lo
son en cada dovela.

**Que acierta, medido**: sobre los **4860** círculos de la rejilla declarada del
problema 27, dispara en **147 de los 147** que reventaban y en **ninguno** de
los otros 4713.

**2 · Seis inserciones que cubren los nueve métodos.** Una línea al principio de
cada `compute_fos`. `lowe_karafiath` hereda de `PrescribedInclinationMethod`,
así que la de `modified_swedish` vale por tres.

| Archivo | Métodos |
|---|---|
| `bishop.py` | Bishop simplificado |
| `janbu.py` | Janbu simplificado y corregido |
| `spencer.py` | Spencer |
| `gle.py` | GLE / Morgenstern-Price |
| `modified_swedish.py` | Corps of Engineers #1 y #2, Lowe-Karafiath |
| `ordinary.py` | Ordinary / Fellenius |

Los nueve responden ahora lo mismo: `fos = 0.0`, `converged = False`,
`is_valid = False`, y el mismo motivo palabra por palabra.

**3 · El respaldo aritmético**, en las dos iteraciones que dividen por F. La
guarda pasa de `not math.isfinite(new_fos)` a
`not math.isfinite(new_fos) or new_fos <= 0.0`, que es **literalmente** lo que
`bishop._general_moment_fos` ya hacía desde v0.1.92 para superficie no circular:
el camino circular era el único que se había quedado sin ella. Protege contra
cualquier **otro** camino que lleve F a cero o a negativo, no sólo contra el
caso físico de la capa 1.

**4 · Una red estrecha en el límite de la búsqueda**, `BaseSearch._analyse`.
`evaluate_circle` y `evaluate_surface` son las **dos únicas puertas** de
cualquier búsqueda al motor —las seis búsquedas, `optimize.py` y el muestreo
probabilístico entran por ahí—, así que ahí se puede enunciar el invariante una
sola vez: *una superficie que no se puede analizar se cuenta y se explica; no
mata la corrida*.

`ArithmeticError` y **no** `Exception`, a propósito. Cubre `ZeroDivisionError`,
`OverflowError` y `FloatingPointError` —los fallos que son de los números—
mientras que un `TypeError` o un `AttributeError` sigue reventando a gritos,
porque ésos son defectos del código. La versión ancha ya se pagó una vez: el
`except Exception` de la tarea de cálculo convirtió el `TypeError` de Slope
Search en un diálogo genérico de «Error» sin resultados, en **todas** las
versiones publicadas hasta la 0.1.77.

## 5 · Lo que se midió, y una cifra de la ficha que estaba mal

La ficha del problema 27 decía «12 círculos». Son **147 de 4860**, un **3,0 %**,
y con `min_area = 200` ya puesta. El «12» era la longitud de la lista de
ejemplos archivada en `anomalias.json`, no un recuento. Ni `min_area` ni ceñir
la rejilla lo evitan: cualquier rejilla que alcance el Soil 2 acaba generando
uno.

La rejilla completa, antes y después:

| | 0.1.98 | **0.1.99** |
|---|---|---|
| generados | 4860 | **4860** |
| válidos | 2864 | **2864** |
| inválidos contados | 1849 | **1996** |
| revientan | **147** | **0** |
| resultado | `ZeroDivisionError` | **termina** |

`total_count` sigue siendo exactamente `(nx+1)(ny+1)(rinc+1) = 18·18·15 = 4860`,
que es la identidad documentada que v0.1.83 puso a proteger. Los 147 aparecen
agrupados por su motivo en el resumen de superficies inválidas de la ventana de
interpretación, sin tocar una línea de interfaz: `invalid_reason` y
`_invalid_reasons` ya agrupaban por `error_message`.

## 6 · Lo que no se ha movido

Los cinco métodos sobre el círculo publicado del problema 27, **bit a bit**:

| Método | 0.1.98 y 0.1.99 |
|---|---|
| Bishop simplificado | 1.4066653935010267 |
| Janbu corregido | 1.4023759518649548 |
| Lowe-Karafiath | 1.4066490294034906 |
| Spencer | 1.4066437252209614 |
| GLE / M-P | 1.4066538699364783 |

No podía ser de otro modo por construcción —el predicado sólo dispara cuando la
resistencia es idénticamente cero, y una superficie validada tiene factor
convergido mayor que cero—, pero se ha comprobado igualmente.

**Aviso para quien lea fichas antiguas**: esos números **no** son los 1,4108 /
1,4056 / 1,4103 / 1,4108 / 1,4108 que se citan en varios sitios. Aquéllos son
los de **antes** del arreglo del peso saturado de Soil 1 (`use_sat_unit_weight`
guardado y desactivado, P027-MAT1). Los `.ogr` ya llevan la casilla puesta, y
pesar la mitad sumergida con 124,2 en vez de 116,4 baja el factor un 0,29 %.

## 7 · Lo que sigue sin cuadrar, y no lo arregla esta versión

Con la búsqueda ya terminando, los cinco métodos convergen al **mismo** centro y
radio —(100,588 · 210,588), R 121,922, una superficie que cae casi entera en el
material sin resistencia— y a un factor que no es el que publica el manual:

| Método | **OGR, búsqueda** | manual |
|---|---|---|
| Bishop simplificado | 0,361113 | 1,376 |
| Janbu corregido | 0,351217 | 1,345 |
| Lowe-Karafiath | 0,426406 | 1,392 |
| Spencer | 0,361113 | 1,382 |
| GLE / M-P | 0,361112 | 1,378 |

No es un defecto de esta corrección, y conviene que quede escrito para que nadie
lo persiga por el camino equivocado: el enunciado restringe el afloramiento a
**dos ventanas separadas** —pie entre x = 38 y 70, coronación entre x = 120 y
180— y OGR sólo tiene un par `slope_limit_left` / `slope_limit_right`, así que la
rejilla puede aflorar donde el manual no deja. Que los cinco métodos coincidan en
la misma superficie dice que el motor es consistente consigo mismo; la
discrepancia está en **qué población se busca**, no en cómo se evalúa. La
búsqueda **termina**, que es lo que esta versión venía a arreglar; no la
convierte en la misma pregunta.

## 8 · El test

`tests/test_robustez_sin_resistencia_v199.py`, nueve comprobaciones repartidas
en las cuatro capas, para que un fallo diga cuál se rompió:

- los **nueve** métodos devuelven `fos = 0.0`, `is_valid = False` y el mismo
  motivo sobre una masa sin resistencia;
- el defecto original, con el predicado desactivado **en la instancia** (no en
  la clase: regla 5), sigue sin reventar gracias al respaldo de la capa 3;
- **regla 7**: el mismo círculo sobre la misma geometría, con resistencia, da un
  factor normal en los nueve. Una guarda que disparase siempre sería peor que no
  tenerla;
- el borde del predicado: una masa que cruza el material débil **y** uno
  competente se analiza con normalidad;
- la rejilla entera termina, la identidad de población se cumple y las
  superficies que no se pudieron analizar salen contadas con su motivo;
- la red de la capa 4, con un método que divide por cero a propósito — y su
  contrario, un método que lanza `TypeError` y **tiene** que seguir reventando.

No es un test de instantánea: el factor de una masa sin resistencia está fijado
por una identidad, no por lo que imprima el código de hoy.

---

## Archivos

- `ogr_slip2d/methods/base.py` — el predicado, el resultado compartido y el
  porqué de las dos decisiones
- `ogr_slip2d/methods/{bishop,janbu,spencer,gle,modified_swedish,ordinary}.py`
  — la llamada al predicado; en `bishop` y `janbu`, además, el respaldo
  aritmético
- `ogr_slip2d/search.py` — `BaseSearch._analyse`, la red estrecha
- `tests/test_robustez_sin_resistencia_v199.py` — nuevo
- versión 0.1.98 → 0.1.99 en los siete sitios
