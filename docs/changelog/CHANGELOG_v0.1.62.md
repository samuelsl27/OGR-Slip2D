# OGR Slip2D v0.1.62 — quién manda y cuál

Primera de seis fases para saldar la deuda anotada al cerrar v0.1.61. Esta
recoge los cuatro puntos que compartían fichero o eran baratos: el recorte
de la rejilla por el nivel freático, el selector de superficie de agua, los
tres campos fantasma de `Material` y el diagnóstico de Ordinary/Fellenius.

Nada de esto era una funcionalidad que faltara. Los cuatro eran **huecos
entre lo que la interfaz ofrecía y lo que el motor calculaba**, que es la
forma de error que peor se detecta porque no falla: da un número.

---

## 1. La tercera diferencia NF ↔ piezométrica

`pore_pressure_at` tenía un `return` incondicional en cuanto el método de
agua era una rejilla. Con eso, **todo el bloque de nivel freático quedaba
inalcanzable**: ni Hu, ni `h ≤ 0 → u = 0`, ni descenso rápido. Una rejilla
podía devolver presión positiva arbitrariamente por encima del freático.

Ahora un **nivel freático recorta la rejilla**: `u = 0` por encima, el
valor interpolado intacto por debajo. Es un recorte superior, no una
sustitución — por debajo manda la rejilla, que es lo que la hace útil junto
a un campo interpolado que no sabe dónde está la superficie libre.

Una **piezométrica no recorta**, y la asimetría es deliberada: es una
medida de presión, no una superficie libre, así que no dice nada sobre lo
que hay encima. Con esto quedan implementadas las tres diferencias que el
docstring de `ponded_water` venía prometiendo desde v0.1.61.

De paso: el método se comparaba con literales de cadena sueltos
(`"grid_total_head"`…) en vez de con `GroundwaterMethod.*.value`. Renombrar
un método del enum habría desactivado la rejilla en silencio.

## 2. El selector de superficie de agua

`Material.water_surface_id` existía, se serializaba y el solver lo
respetaba **desde v0.1.7**. Lo que no existía era quién lo escribiera:
cero escrituras en todo `ogr_gui/`. Solo lo tocaban un ejemplo y el CLI.

Consecuencia: en cualquier proyecto hecho con la interfaz el campo era
siempre `None`, siempre entraba el fallback *"la primera del tipo"*, y con
dos líneas piezométricas **el resultado dependía del orden de
`project.boundaries`**. La segunda piezométrica era inalcanzable.

Añadido:

- Combo **Water Surface** en el grupo de presión intersticial del diálogo
  de materiales, con la entrada explícita *(la primera de este tipo)* para
  el comportamiento heredado.
- Acción **Assign Water Surface...** en el menú Propiedades, para asignar
  una superficie a varios materiales de golpe. Solo limpia la asignación de
  los materiales que apuntaban **a esa misma** superficie: desmarcar no
  puede borrar en silencio una asignación a otra distinta.
- Módulo nuevo `ogr_core/hydraulic/water_surfaces.py`, que es ahora el
  único sitio que sabe enumerar, nombrar y resolver superficies de agua.

Ahí quedan escritos los **tres criterios distintos de "qué NF vale"** que
conviven en el código. Parecían una incoherencia y no lo son: la presión
intersticial usa **la asignada al material**, el peso específico saturado
pregunta si hay **alguna** por encima, y el embalse toma **la más alta**.
Cada uno es el correcto en su sitio, y escribirlo es más barato que volver
a descubrirlo una tercera vez.

`_interp_y_on_polyline` sube a público como `interp_y_on_polyline` en ese
módulo: era un privado importado desde cuatro paquetes, y uno de ellos
había necesitado un import perezoso para romper el ciclo. El alias privado
se mantiene.

## 3. Tres campos que no existían

`hu`, `auto_hu` y `b_bar` se leían con `getattr` sobre atributos que
**ninguna dataclass declaraba**. Existían solo si alguien los inyectaba en
memoria — y el único que lo hacía era un test. Como no estaban en
`to_dict`, **no sobrevivían a guardar el proyecto**: el diálogo de
materiales llegó a usar `deepcopy` en lugar de `from_dict(to_dict())`
precisamente para no perderlos, con un comentario que lo admitía.

Ahora son campos reales, serializados, con controles en el diálogo: `Hu`
(casilla + spin, porque "sin marcar" significa *usa el valor por defecto
del proyecto*, que un spin no puede expresar), `Auto Hu`, `Undrained
Behaviour` y `B-bar`.

### El cambio que mueve números

`b_bar` pasa a valer **0.0 por defecto**, con una casilla *Undrained
Behaviour* que lo habilita. Antes el `getattr` caía en 1.0, así que **todo
material se comportaba como no drenado con transferencia total** sin que
nadie lo hubiera elegido. El nuevo defecto es el de la referencia y el
conservador de verdad: un material drenante libre no retiene exceso.

Para que reabrir un proyecto guardado no cambiara su factor de seguridad en
silencio, `Project.from_dict` restituye los valores implícitos antiguos
(`undrained_behaviour=True`, `b_bar=1.0`) cuando el fichero trae descenso
rápido activo y **ningún** material lleva las claves nuevas. Es el mismo
truco que v0.1.60 usó con `use_sat_unit_weight`, y por el mismo motivo.

## 4. Ordinary/Fellenius dice lo que le pasa

No es un fallo de la implementación: es el método. Fellenius resuelve el
peso sobre la base sin fuerza interdovela, así que una presión intersticial
alta en un tramo empinado del arco lleva `N' = W·cosα − u·l` por debajo de
cero, el `max(0, …)` tira el déficit y el factor de seguridad sale bajo.
Whitman y Bailey (1967) midieron errores de hasta el **60 %** por esta vía;
Bishop (1955) se queda por debajo del 7 %.

Arreglarlo sería dejar de ser el método de Fellenius. Lo que sí se puede
hacer es **contarlo**: el resultado lleva ahora
`details["negative_effective_normal"]`, y la barra de estado lo avisa tras
calcular. Un número que nadie cuestiona es peor que un número con su
salvedad puesta al lado.

---

## Lo que se encontró por el camino

### El tooltip de B̄ pide algo imposible

El diálogo de ajustes afirma que *Calculate Excess Pore Pressure* es
**requisito** para el descenso rápido con B̄. Pero
`GroundwaterSettings.set_advanced_option` hace los tres avanzados
—transitorio, exceso de presión, descenso rápido— **mutuamente
excluyentes**: activar uno apaga los otros dos. Si el cálculo comprobara
ese requisito, B̄ dejaría de calcular nada en cuanto el usuario usara la API
correcta.

El plan de esta fase incluía añadir esa comprobación. **No se ha añadido**,
y el tooltip queda como está hasta decidir cuál de las dos cosas es la
verdadera. Hay además una incoherencia real de fondo: `apply()` del diálogo
escribe los tres flags a mano, saltándose `set_advanced_option`, así que la
interfaz **sí** permite dejar dos activos a la vez. Pendiente para la fase
del descenso rápido.

### El convenio de signos de la línea de desembalse

`pore_pressure_at` exige `y_drawdown > y_water_table` para aplicar Δu, y
`ponded_water` documenta la línea de desembalse como *el nivel ANTES del
descenso*. Es decir: aquí el NF es el nivel final y la línea de desembalse
el inicial. La referencia usa el convenio contrario — el NF es el inicial
(se rotula "Initial") y la línea de desembalse marca el nivel final, más
bajo. Ambas lecturas dan la misma física si se leen enteras, pero no son
intercambiables al dibujar.

No se ha tocado: no forma parte de los siete puntos y decidirlo sin las
ecuaciones del multietapa delante sería adivinar. Queda anotado para la
fase 6, que es donde el convenio tiene que quedar fijado de una vez.

### El invariante de la rejilla estaba mal formulado

El primer test comparaba la presión interpolada contra el literal `100.0`
y fallaba: la ponderación por distancia inversa de un campo constante
devuelve `99.999999999999972`. La afirmación correcta no es *"el
interpolador es exacto"* sino *"la rejilla pasa intacta"*, así que el test
compara contra el valor que devuelve la propia rejilla —igualdad bit a
bit— y aparte fija que el campo es constante con tolerancia relativa. Es
más fuerte que la versión que falló, y no da por incorrecto algo que
funciona.

---

## Qué se probó

Fichero nuevo `tests/test_water_surfaces_v162.py`, 22 tests. Todos los
anclajes son identidades analíticas o formas cerradas, ninguno es una
instantánea:

- **Recorte de la rejilla**: `u = 0` exacto por encima del NF; por debajo,
  igualdad bit a bit con lo que devuelve la rejilla. Un caso base sin NF
  para que el test no pueda pasar por el motivo equivocado, y la asimetría
  de la piezométrica.
- **Selector**: con Hu = 1, `u = γw·(y_sup − y)`, así que apuntar el mismo
  material a dos piezométricas separadas 8 m cambia `u` en exactamente
  `γw·8`. Y el factor de seguridad se mueve (regla 7).
- **Hu**: escala lineal exacta; Auto Hu = cos²α, que vale exactamente 1 en
  horizontal y exactamente 0.5 a 45°.
- **Round-trip** de los cuatro campos y sus defectos.
- **Migración**: un fichero legado con descenso rápido reabre con
  `u = γw·7 + γw·10`, idéntico a antes; uno que ya trae las claves se
  respeta.
- **Ordinary**: con carga hidráulica extrema hay dovelas con `N' < 0`; en
  seco, ninguna.
- **Interfaz**: el combo ofrece las superficies más el fallback, escribe el
  id, y los controles se **deshabilitan** —no se ocultan— para los modelos
  que los ignoran.

`tests/test_drawdown.py` actualizado al contrato nuevo: la fixture activa
`undrained_behaviour` junto con `b_bar`, y se le añade el test que
comprueba que la casilla **gatea de verdad** — misma geometría, mismo B̄,
sin la casilla no hay exceso (regla 7).

Suite completa en verde, incluidos los 7 casos de validación LEM y el test
de alcanzabilidad de menús, que cubre automáticamente la acción nueva.

## Lo que queda de la deuda

Fases 2 a 6, en este orden: integrar la columna vertical de la dovela
(γ por capa y γsat solo bajo el NF), soportes en los siete métodos, embalse
derivado de las condiciones de contorno de altura total, reparto de dovelas
en las intersecciones, y el descenso rápido multietapa —Lowe-Karafiath,
Duncan-Wright-Wong y Corps 2 etapas—, que sigue bloqueado hasta obtener las
ecuaciones de conversión entre la envolvente R y la Kc = 1 de su fuente
original.
