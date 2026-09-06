# OGR Slip2D v0.1.149

**El encargo de D66 localizaba el defecto en «dos sitios», los dos
diccionarios `{TYPE_ID: tipo}` de `support_integration.py`. Eran ocho, y el
camino de menú con el que la interfaz «modificaba» un soporte escribía un
atributo que nadie leía.** Cada tipo de soporte lleva ahora un `id` propio,
la instancia lo nombra por `type_ref`, y un solo resolutor contesta a la
pregunta que ocho sitios contestaban por su cuenta. El problema 50 del banco,
sin modelo desde agosto, se construye con sus siete juegos y sale dentro del
3 %; el 49 pierde su rodeo sin mover un dígito.

---

## Lo que había

`project.support_types` es una **lista**, pero el cálculo la convertía en un
diccionario indexado por la constante de clase `TYPE_ID` y resolvía cada
`SupportInstance` por su `type_id`, que es la clase. Dos `SoilNail` de
capacidades distintas colapsaban en el **último** declarado, sin aviso, sin
error, y el `.ogr` guardaba y cargaba los dos: el proyecto parecía correcto y
sólo el cálculo mentía. Es lo que bloqueaba el 50 del banco (catorce filas de
bulones en siete juegos de parámetros) y lo que obligaba al rodeo del 49 (dos
tirantes de capacidades distintas, el segundo reescrito como `SoilNail`
porque con el 100 % de adherencia las dos clases dan la misma fuerza).

Contados, no eran dos sitios sino **ocho**: `_bond_profiles` y
`compute_support_effects`; `resolved_types` de las notas de modelo, del que
colgaban las de helical, Ito-Matsui y ubicación de la fuerza; `_walls` del
muro; el lienzo (tooltip y menú contextual); el diagrama de fuerzas; y los
tres diálogos con combo de tipo, cuyo dato era `TYPE_ID`, así que dos juegos
de una clase eran **una** entrada y el usuario no podía elegir entre ellos
aunque quisiera. Y la asimetría que daba la forma del arreglo:
`SupportInstance` tenía `id`; el tipo, no.

Había además una inconsistencia interna que nadie había medido: el motor
tomaba el **último** juego de la clase (es lo que hace un diccionario);
Add Support, el diagrama de fuerzas y los combos tomaban el **primero**.

## Lo que apareció de paso (regla 6: se dice antes de tocarlo)

- **`Modify Support` no modificaba un soporte.** Escribía
  `support.support_type = tipo`, un atributo que ninguna `SupportInstance`
  tiene y que el motor nunca leyó; sus etiquetas eran nombres de CLASE, así
  que con dos juegos `index()` devolvía siempre el primero; y
  `_support_label` leía ese mismo atributo, así que la lista de soportes
  decía «1: support, 2: support…».
- **Cuatro lectores más del mismo atributo inexistente**: la tabla de
  propiedades de soportes (columna *Type* vacía y ni un parámetro que
  comparar), los data tips, *Support Force Analysis* de Interpret («capacity
  not defined» en todas las filas) y las **variables aleatorias de soporte**
  (`ogr_core/statistics/random_variables.py:272-279`, que leen `PARAMETERS`
  en la instancia, que no los tiene: ningún parámetro de soporte ha sido
  nunca muestreable, regla 7 en la parte probabilística). Por decisión del
  propietario, los tres de pantalla y Modify Support se corrigieron con el
  resolutor en esta versión; las variables aleatorias quedan **reportadas**,
  como tarea propia.
- **`Ungroup Support Pattern`** filtra por `getattr(s, "pattern_id")`, que
  ni `SupportInstance` ni `SupportPattern.generate_along_segment` asignan:
  responde siempre «No support belongs to a pattern». Reportado.

## Qué cambia

- `ogr_core/support`: campo `id` (uuid, `compare=False`, **el último** de la
  dataclass para no mover ningún constructor posicional) en los nueve tipos;
  los siete con serialización genérica lo escriben solos, `UserDefined` y
  `RetainingWallEFP` lo escriben a mano; un `.ogr` anterior carga con id
  nuevo. `SupportInstance.type_ref` y `SupportPattern.type_ref`, escritos
  **sólo si están**, para que un proyecto que nunca nombró un juego produzca
  el mismo JSON que antes. `resolve_support_type` (referencia → **primer**
  juego de la clase → registro), `support_type_pairs` y
  `unresolved_support_refs`, exportados por el paquete.
- Motor: los dos diccionarios desaparecen; `support_notes.resolved_types`
  pasa a ir por id de juego y nace `supports_by_type`; las notas de helical,
  Ito-Matsui y muro van por pares (dos juegos de pilotes o de anclajes son
  dos, no el último); nota nueva `support_identity_notes` en
  `settings_warnings` cuando el motor **adivina**: una instancia sin
  referencia con varios juegos de su clase, o una referencia a un juego que
  ya no está.
- Interfaz: los combos de tipo llevan el id del juego (Support Properties,
  Add Support Pattern, Modify Support Pattern) y al aceptar fijan `type_ref`
  **y** `type_id` a la vez, para que quien lea sólo la clase no reciba una
  mentira; Add Support fija `type_ref`; Modify Support asigna de verdad, con
  el nombre que el usuario puso a cada juego; Define Support conserva la
  identidad de una fila a través de cada reconstrucción de su objeto
  (parámetro editado, clase cambiada) y da id nuevo a un duplicado, y al
  aceptar resincroniza las instancias (la clase de las que nombran una fila
  cuya clase cambió; referencia a `None` en las que nombran una fila
  borrada); importar tipos de otro proyecto regenera ids; lienzo, diagrama
  de fuerzas, data tips, tabla de propiedades e Interpret usan el resolutor
  y enseñan el nombre del juego, no el de la clase.
- **Desempate para archivos anteriores**: el **primero** declarado, por
  decisión del propietario, porque es lo que Add Support coloca por defecto
  y la primera fila de Define Support. Con un juego por clase primero,
  último y único son el mismo objeto: por eso ningún modelo del banco se
  mueve.

## Qué se probó

- `tests/test_support_identity_v1149.py`, 35 tests: ida y vuelta del id por
  `to_dict` y por `Project`, y de `type_ref` en instancia y patrón; un dict
  anterior carga; orden de resolución (referencia sobre clase, por id aunque
  `type_id` diga otra clase, primero de la clase, huérfana cae a la clase,
  registro, desconocido → `None`); **regla 7 con número**: dos `SoilNail` de
  60 y 120 kN dan 30,0 y 60,0 kN/m a su instancia, FS(A+B) está entre FS(A)
  y FS(B), y con un solo juego FS con referencia `==` FS sin ella; la
  igualdad `GroutedTieback(bond_length_percent=100)` ≡ `SoilNail` del rodeo
  del 49, en once estaciones; las notas (ambigüedad con el juego usado,
  silencio con referencia o con un juego, huérfana); helical e Ito-Matsui
  por juego; y los diálogos offscreen, sin `exec()`.
- Filtrado durante el desarrollo: 295 tests de soportes, helical,
  Ito-Matsui y muro; 74 de menús, i18n, data tips y menús menores.
- **Suite completa**, sin filtrar y con la versión ya subida: 178 archivos,
  **3150 tests, 3150 en verde**. Tardó más de los 5–7½ minutos habituales
  porque corrió a la vez que la auditoría del banco; el reloj no se anota
  como medida.
- Banco: el **49** reescrito con dos `GroutedTieback` de verdad repite
  1,434064 · 1,466513 · 1,444227 · 1,444227; el **50** construido desde su
  transcripción da **+2,0 %** sobre `por_0_0` (1,608529 frente a 1,577) y
  **−0,64 %** sobre `por_0_-5` (1,407976 frente a 1,417). Sobre la segunda
  no cruza ningún bulón —las catorce colas quedan cortas— y el número
  coincide igualmente: el 1,417 del manual es también un factor sin
  refuerzo, lo que respalda la lectura de la figura. La auditoría
  reproducible del banco entero, con el motor nuevo: **167 modelos IGUAL**
  en 99 problemas (el 49 y el 50 dentro), 27 DERIVADO que se rederivan
  exactos, **0 DIFERENTE** y 0 sin script — los ids nuevos de los tipos son
  volátiles para la comparación, como ya lo eran los de las instancias, y
  ningún modelo con un juego por clase cambió de serialización.

## Qué falta

- Las variables aleatorias de soporte y `Ungroup Support Pattern`:
  reportados arriba, no corregidos.
- `_TYPE_COLORS` del lienzo sigue siendo por clase: dos juegos de una clase
  sin color propio se dibujan iguales.
- Cambiar la clase de una fila en Define Support deja `orientation` y
  `force_application` de sus instancias con los valores explícitos que ya
  tenían; el diálogo de instancia los ajusta.
- Los vértices intermedios de las dos superficies del 50 siguen siendo
  lecturas de figura a ±0,5 ft (P050-SUP1), y de ellos depende que el
  refuerzo cruce.
