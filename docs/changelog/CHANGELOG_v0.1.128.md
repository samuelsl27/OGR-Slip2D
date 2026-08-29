# OGR Slip2D v0.1.128

**El Auto Refine no circular existe**: el ajuste que lo configuraba
llevaba desde v0.1.10 sin que nadie lo leyera, y la búsqueda que decía
configurar devolvía círculos.

Cierra **D32**. Y lo interesante no es lo que se escribió, sino que el
algoritmo ya estaba publicado, que la comprobación evidente **no vale**, y
que el arreglo destapa un ajuste que puede tirar la mitad de las
superficies sin decirlo.

---

## Qué estaba mal

`SearchSettings` ofrecía `auto_refine_num_vertices_along_surface = 12`
comentado «only non-circular», metía `AUTO_REFINE` en
`NON_CIRCULAR_METHODS` y el diálogo enseñaba la casilla. Pero
`build_search` **despachaba por el método y nunca miraba el tipo de
superficie**, así que un modelo con `surface_type = "non_circular"` y
`search_method = "auto_refine"` se guardaba sin una queja, se abría sin
una queja y devolvía **círculos**. Pedirle 37 vértices no cambiaba nada:
el objeto construido ni siquiera guardaba el número.

Regla 7 literal, y de la peor especie. **Un ajuste inerte que fabrica un
falso acuerdo es peor que uno que produce un error**: si la mitad no
circular del banco se hubiera montado con `auto_refine` —que es lo que
sugieren los enunciados de los problemas 70, 71, 74 y 82, que declaran
*auto refine search* y publican columna no circular—, la fila «no
circular» habría publicado el mismo número que la circular y se habría
leído como que las dos familias coinciden. Que es justo la conclusión que
un banco de validación existe para poder sacar.

## No hubo nada que inventar, y eso se comprobó antes de escribir

La ayuda publica el método entero en su propia página, distinta de la del
circular: se generan los mismos círculos, **cada uno se convierte en una
polilínea subdividiendo el arco en divisiones aproximadamente iguales**
con el número de vértices pedido, **el factor de seguridad se calcula
sobre la polilínea**, el refinamiento sigue igual, y la optimización se
aplica después y está **ON por defecto**.

Leer eso antes de tocar el código evitó las dos decisiones que el
razonamiento habría tomado mal: cuántos segmentos son N vértices (N−1, lo
dice con un ejemplo) y si la conversión reparte por x o por arco.

## Lo que ya estaba en el código y no se vio a la primera

`_candidate_surfaces()` **resuelve un círculo crudo sobre sus masas
deslizantes sin gastar un solo LEM**: extremos, curvatura inversa, grieta
de tracción del usuario, recorte compuesto y contención, todo geometría.
Eso es exactamente el paso que la conversión necesita, y es la razón de
que la variante no circular cueste lo mismo que la circular —un análisis
por masa, no dos— y de que conserve el paseo por varias masas de v0.1.84.

`_as_optimisable` **parecía** la conversión que hacía falta y no lo era,
por tres razones que la descartan cada una por su cuenta: exige un círculo
ya resuelto, reparte por **x igual** y no por divisiones del arco, y
devuelve n+1 puntos para un argumento de n. Cambiarla habría movido las
respuestas multimodales del enjambre, que son seis modelos del banco.

El despacho se parte con **una costura de una línea**: `_evaluate_trial`,
que en la clase circular devuelve el círculo mismo. La generación y el
refinamiento son literalmente el mismo código, que es lo que garantiza que
el Auto Refine circular —cuatro modelos del banco— no se mueva un dígito.

## La comprobación evidente no vale, y la buena es otra

La validación natural es refinar la polilínea y ver que reproduce el arco.
**Con Bishop no converge**, y no porque la conversión esté mal. Medido
sobre el problema 77: −2,64 % con 8 vértices, −2,55 % con 32, −2,56 % con
128. Plano. Eso no es discretización, es el **eje de momentos**: una
polilínea no tiene centro de rotación, el eje automático no es el centro
del círculo del que se cortó, y un método sólo de momentos tiene derecho a
notarlo. Ya estaba medido y nombrado —**anomalía D47**, en el docstring de
`moment_axis` desde v0.1.126—, así que el hallazgo aquí fue reconocerlo en
vez de perseguirlo.

**Spencer satisface equilibrio de fuerzas Y de momentos, así que su
respuesta no puede depender de dónde se tomen los momentos**, y es el
único instrumento honesto para esta pregunta. Sobre el talud de los tests:
**+0,2920 %, +0,0472 %, +0,0151 %, +0,0096 %** para 8, 16, 32 y 64
vértices —cerca de un factor cuatro por duplicación, que es lo que hace un
polígono inscrito— y luego plano sobre el suelo de tolerancia del propio
solver. Bishop en el mismo círculo se para en +0,31 %.

Por eso el test afirma **convergencia** y no una tolerancia a un número de
vértices concreto: convergencia es la propiedad que tiene una conversión
correcta y no tiene una incorrecta, y es la mitad de la comparación que el
eje de momentos no puede contaminar. El tamaño **y el signo** del residuo
de D47 dependen del modelo (−2,55 % en el 77, +0,30 % en el talud de los
tests), lo cual confirma que no es una constante del método.

## El defecto que aparece detrás

Una polilínea de N vértices tiene N−1 segmentos, **cada vértice es un
límite de dovela obligatorio** desde v0.1.89, y el rebanador rechaza
entera la superficie cuyos segmentos superan a las dovelas
(`if len(segments) > num_slices: return None`). El spinbox de vértices
llega a 100 y las dovelas por defecto son 25: **el rechazo está a un
control de distancia**, y esta búsqueda es la primera que deja pedir el
número de vértices directamente.

Y **no falla limpiamente**, que es lo peor. Las fronteras de material y el
nivel freático son cortes obligatorios también, y varían **por
superficie**: así que la búsqueda analiza en silencio las superficies que
cruzan pocas capas y tira las que cruzan muchas. Medido en el problema 77
con 30 dovelas: 12 vértices evalúan 69 superficies, 30 vértices evalúan
**40**, y nada decía que 29 se habían quedado por el camino. Una búsqueda
sesgada presentada como completa.

Se atiende por los dos lados, porque ninguno basta solo:

- lo **predecible** (N−1 > dovelas rechaza todas) lo avisa
  `settings_warnings` antes de calcular;
- lo **observable** lo cuenta la propia búsqueda y lo dice: «34 de las 74
  superficies que formó esta búsqueda no se pudieron rebanar». La
  predicción no puede saber los cruces de capa; la corrida sí.

La primera versión de este aviso sólo miraba si la corrida había devuelto
**cero** superficies. Estaba mal, y lo destapó medirlo: el caso frecuente
no es cero, es cuarenta de setenta y cuatro.

## Y el desajuste que sobrevive al arreglo

`surface_type` y `search_method` se guardan por separado y nada los
comparaba nunca. `non_circular` + `grid` sigue devolviendo círculos en
silencio, y es el mismo defecto con otra cara. Ahora `settings_warnings`
lo dice. Ningún modelo del banco tiene hoy una pareja incoherente —censo:
141 `circular+grid`, 33 `non_circular+path`, 6 `non_circular+block`, 6
`non_circular+particle_swarm`, 4 `circular+auto_refine` y **cero**
`non_circular+auto_refine`—, así que el aviso no puede mover un número
publicado. Está para el modelo que se escriba mañana.

## En la interfaz

El spinbox de vértices se decidía **en el constructor del diálogo**:
abrirlo en Circular y cambiar el radio a No-Circular no lo hacía aparecer,
así que el control que decide la conversión quedaba inalcanzable y
`apply()` no tenía nada que escribir. Ahora se construye siempre y se
muestra u oculta.

Le faltaba además la fila **Optimize Surfaces**, que sí tienen Annealing,
enjambre, Path y Block. Sin ella la opción que la referencia deja ON por
defecto para este método habría estado activa y sin forma de tocarla desde
el panel que la gobierna.

Y una trampa que sólo apareció al probar el diálogo de verdad: la casilla
de optimización se resolvía al abrir, así que **abrir en Circular y
cambiar a No-Circular dejaba la respuesta circular (apagado), y `apply`
escribía ese apagado explícito** — apagando, por el acto de cambiar de
tipo, la opción que la referencia deja encendida. Se recalcula al cambiar
el tipo, y **sólo si el ajuste sigue en automático**: quien ha marcado o
desmarcado la casilla ha contestado la pregunta, y su respuesta no es un
valor por defecto que recalcular.

De paso, `_refill_methods` reimplementaba a mano las dos familias mientras
las constantes importadas se guardaban sin usarse. Ahora filtra a través
de ellas: mismo orden en el desplegable, una sola fuente.

---

## Ficheros

- `ogr_slip2d/search.py` — `_evaluate_trial` en `AutoRefineSearch`;
  `AutoRefineNonCircularSearch` con `_arc_polyline`, el recuento de
  superficies irrebanables y su nota.
- `ogr_slip2d/analysis_runner.py` — despacho por pareja,
  `_surface_type_notes`, `_auto_refine_vertex_notes`, y `_optimize_notes`
  dejando de disparar sobre la pareja legítima.
- `ogr_core/project/settings.py` — `is_auto_refine_non_circular`, el
  predeterminado de `optimize_enabled_for`.
- `ogr_gui/dialogs/grid_dialogs.py` — fila siempre construida, fila de
  optimización, `_sync_auto_refine_rows`, familias desde las constantes.
- `ogr_gui/i18n/__init__.py` — el tooltip nuevo.
- `tests/test_auto_refine_noncircular_v1128.py` — 25 tests.
- `tests/test_settings_coverage_v1103.py` — fuera la entrada D32 del
  inventario congelado. El inventario falla en las dos direcciones, así
  que quitarla es lo que exige cerrar el defecto.

## Qué queda

- Los problemas **70, 71, 74 y 82** siguen corriéndose con Path Search por
  sustitución. Volver a montarlos con el método que declara su enunciado
  movería filas de la comparativa y necesita su propia ficha —ahora que el
  método existe.
- El rótulo de totales del panel Auto Refine publica
  `divisiones × círculos × iteraciones` cuando el algoritmo recorre
  **pares**, C(divisiones,2): con los valores por defecto dice 1000 donde
  corresponden 4500. Reportado y **no corregido** (regla 6); ya anotado en
  `docs/PENDIENTES.md`.
- **D47** sigue abierto y ahora tiene un segundo modelo que lo mide, con
  el signo contrario al del primero.
