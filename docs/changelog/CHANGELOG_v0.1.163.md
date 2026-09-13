# OGR Slip2D v0.1.163

**El encargo de P-D95 pedía que un perfil de adherencia que no se
construye dejara de degradar la fuerza en silencio, y está hecho; pero el
comentario que justificaba ese silencio —«cae en su envolvente de tensión
nula, que es conservador: nunca MÁS refuerzo del que daría el estado
tensional»— es falso en su propio término para la mitad de los tipos a los
que afecta. Ni `PileMicropile` en modo Ito-Matsui ni `HelicalAnchor`
tienen envolvente a tensión nula ninguna, porque su resistencia sale del
terreno y no de un parámetro propio: los dos contestan exactamente 0,0. No
era «menos refuerzo», era NINGUNO, y el factor de seguridad se convertía
en el del talud desnudo.**

Cierra **D95**. **Cero dígitos movidos**: ni una línea ejecutable de
cálculo, ni una constante, ni un valor por defecto, ni una tolerancia.

---

## 1. El defecto, medido

`ogr_slip2d/support_integration.py`, en `_bond_profiles`:

```python
        try:
            profiles[support.id] = build_bond_profile(project, support, stype)
        except Exception:  # noqa: BLE001
            # A profile that cannot be built leaves ``force_at`` to fall
            # back on its zero-stress envelope, which is conservative:
            # never MORE reinforcement than the stress state would give.
            continue
```

Medido sobre las fixtures de la suite, rompiendo el muestreo del tipo —no
parcheando nada global— con OGR 0.1.162:

| tipo | F sana | F con perfil roto | factor | razón que emitía |
|---|---|---|---|---|
| `Geosynthetic` (`coefficient`) | 77,0105 kN/m | **0,0** | 1,917941 → **1,551095** | `no_capacity` |
| `HelicalAnchor` | 39,4168 kN/m | **0,0** | 1,840330 → **1,551095** | `no_capacity` |
| `PileMicropile` (Ito-Matsui) | 152,5946 kN/m | **0,0** | 1,506769 → **1,144634** | `no_capacity` |
| `GroutedTiebackFriction` (a=60) | 69,4509 kN/m | 44,5321 | 2,060558 → 1,877843 | **ninguna** |

Los tres primeros valores de la derecha son **bit a bit** los del mismo
modelo con sus soportes borrados: 1,5510949308871327 y 1,1446339358448414.
No «parecidos» — idénticos, porque el soporte desaparece del equilibrio
entero.

Y hay una segunda mitad, que es la que da nombre a la ficha: el
diagnóstico. Esos soportes afloraban por `SUPPORT_NO_CAPACITY`, «develops
no capacity where it crosses», que es una afirmación sobre el **modelo**
cuando la verdad era una afirmación sobre el **tipo**. El comentario de esa
constante llevaba avisando de la confusión desde 0.1.155 sin poder
evitarla:

> Worded as "develops no capacity where it crosses" and never as "its type
> has zero capacity", because a bond profile that failed to build lands
> here too [...] and that is a different fact about a different cause.

La cuarta fila es peor todavía y la ficha no la menciona: el tieback con
adhesión **sí** conserva envolvente, así que sigue dentro del equilibrio
con el 64 % de lo que debería, y por eso nunca llega a la guarda que
escribe una razón. No es que dijera la razón equivocada: **no decía nada
en absoluto**.

---

## 2. Cinco cosas que la ficha da por sentadas, y la medición desmiente

1. **Sus citas de código ya no apuntan a código.** La ficha sitúa
   `_bond_profiles` en 753 y su `except` en 785-793; está en **859-901**.
   `PileMicropile` Ito en 1104-1129 → **1141-1168**; `Geosynthetic` en 1386
   → **1416-1442**; `compute_support_effects` en 849-1077 → **978-1242**. Y
   `build_bond_profile` **no vive en `support.py`**, sino en
   `ogr_core/support/bond.py:289`.
2. **Son CUATRO tipos con perfil y DOS ceros duros, no tres y uno.** Falta
   `HelicalAnchor` (`helical_anchor.py:416-453`), que sin perfil fabrica
   placas a cero y un `tau_integral` nulo. Su propio comentario lo dice con
   todas las letras —«unlike the two older stress-dependent types, this one
   has no envelope at zero stress to fall back on»— y es exactamente la
   misma omisión que la ficha de D98 hizo con este mismo tipo. Es, además,
   el soporte del problema **111** del banco.
3. **El 049 no es el caso del 0.0, que es donde el paso 5 mandaba mirar.**
   Su `pile_micropile` trae `failure_mode: "shear"`, y en esa clase
   `NEEDS_BOND_PROFILE` no es constante de clase sino una `@property` que
   devuelve `self._ito()`: en modo Shear **no se construye perfil ninguno**
   y D95 no puede tocarlo. Lo mismo el 054. El único Ito-Matsui del banco es
   el **106**, con sus cuatro modelos, y ahí es donde se ancla la medida.
4. **Sus dígitos son de 0.1.159.** Publica 0,984824 → 0,950281 para el 091;
   0.1.160 metió la tolerancia en cada `.ogr` y movió 83 problemas. La línea
   base es `Evaluaciones/0.1.160` (precedente d79/d94/d98).
5. **El test no se llama `_v1160`.** El sufijo `_vNNNN` es la versión en que
   el test **aterriza**, 0.1.160 ya tiene el suyo
   (`test_no_vendor_names_v1160.py`) y esto sale en 0.1.163. Y `d95()` **no
   existía**: el criterio de cierre la nombra como si estuviera escrita.

---

## 3. Lo que el encargo no pedía y la medición obligó a meter

El `except` ancho se tragaba también un **`SupportEvaluationError`
tipado**, y eso convierte a D95 en el mismo defecto que D98 un escalón más
abajo. `docs/plugins.md:180-182` publica como contrato:

> raise `SupportEvaluationError` where the MODEL cannot be priced — a
> geometry that degenerates, a parameter set that does not describe
> anything, **a profile that will not build** — and let a bug be a bug.

y el docstring de la propia excepción (`support.py:120-123`) repite la
promesa. **Medido: con 0.1.162 un tipo que lanzaba la excepción documentada
desde `interface_tau` obtenía EXACTAMENTE la misma respuesta que uno con
un `TypeError` dentro** — tragada, tasada con la envolvente, y reportada
como «no desarrolla capacidad». Un autor de plugin que hacía justo lo que
el documento le dice recibía la única respuesta que el documento descarta.
Lo señala el propio changelog de 0.1.162 al dejarlo reportado: «`_bond_profiles`
sigue ancho y mudo y además se llama FUERA del bucle, así que un
`SupportEvaluationError` desde `build_bond_profile` tampoco llega a ningún
manejador (es P-D95)».

---

## 4. El arreglo

**La caché deja de perder el fallo.** `_bond_profiles` devuelve un
`_BondProfiles`, subclase de `dict` con dos registros: `failed`
(`support.id` → nombre de clase de excepción) y `refused` (`support.id` →
el texto de `reason`). Subclase y no un segundo atributo del proyecto
porque la caché se tira en **tres** sitios de `project.py` (171, 504, 517)
y un segundo atributo sería una cuarta cosa que recordar: un solo objeto no
puede dejar que un fallo sobreviva a los perfiles que explica. A nivel de
**módulo**, porque la rejilla picklea el proyecto a sus procesos hijos y
pickle resuelve una clase por nombre cualificado. Y los dos registros se
inicializan **por instancia**: un mutable de clase sería estado de módulo
compartido entre análisis, que es la fuga de la regla 5.

Se guarda **el texto y no la instancia**, y no por higiene. Medido:

```
deepcopy  FALLA: TypeError: SupportEvaluationError.__init__() missing 1 required positional argument: 'reason'
pickle    FALLA: TypeError: SupportEvaluationError.__init__() missing 1 required positional argument: 'reason'
```

`__init__` toma dos argumentos y `args` guarda uno, así que `cls(*args)` se
queda corta. Esa caché llega a un `copy.deepcopy(project)` por muestra del
motor probabilístico (`random_variables.py:309-316`) y a `pickle` en la
búsqueda paralela: guardar la instancia habría roto los dos. La subclase
sí sobrevive a ambos con sus atributos intactos, comprobado.

**El `except` se parte en dos, y el ORDEN es medio arreglo**, igual que en
D98: `SupportEvaluationError` es un `RuntimeError`, así que un
`except Exception` puesto delante se la traga igual que antes.

**La excepción tipada llega al manejador de D94**, lanzada de nuevo dentro
del bucle por soporte. Dos decisiones ahí:

- va **después** de las guardas de cruce y rebanada, no al principio del
  `try`. Si fuera al principio, un bulón que ni siquiera corta la
  superficie saldría como `not_priceable` en vez de `no_crossing` —«the
  common case»—, y en una rejilla eso estamparía `support_failure` en casi
  todas las superficies de la corrida y taparía la nota de D62 entera;
- se lanza una **instancia nueva**, no la guardada: re-lanzar un mismo
  objeto acumula traceback a lo largo de las miles de superficies que
  evalúa una búsqueda.

**Dos razones nuevas, y no una.** Porque los cuatro tipos no fallan igual:

- `bond_profile_no_force:<Exc>` — el perfil falló y el tipo no tasa nada sin
  él. El soporte **sí** pone cero fuerza, así que entra en el recuento de
  «N de M no pusieron fuerza», que es verdad; lo que cambia es que ya no
  entra como `no_capacity`. Séptima entrada de `_UNCONTRIBUTING_PHRASES`,
  en el grupo de ENTRADA ROTA, detrás de `not_priceable`;
- `bond_profile_failed:<Exc>` — el perfil falló y el tipo **sí** tiene
  envolvente, así que el soporte sigue en el equilibrio con menos refuerzo
  del que el modelo declara. Misma forma que D98 y mismo trato: fuera del
  recuento y con frase propia, colocada **detrás** de la de D98 porque un
  test lee esa frase en `extra[0]` desde 0.1.162.

El nombre de la excepción viaja tras el sufijo en las dos, por la razón ya
escrita para `shear_failed`: «no se contó» y «no se contó PORQUE
`TypeError`» no son la misma ayuda para quien arregla el plugin. La tabla
de frases formatea un `%d` y nada más, así que para la primera el nombre se
pega como paréntesis al fragmento (`_BOND_RAISED`) en vez de perderse.

Las cuatro formas de la frase, medidas:

```
The only support placed puts no force on the reported surface: it could not
be given a bond profile, and its type prices nothing without one (building
it raised RuntimeError). This factor of safety is the one for the slope
with no reinforcement at all.

None of the 2 supports placed put any force on the reported surface: 1
could not be given a bond profile, and its type prices nothing without one
(building it raised RuntimeError), 1 does not cross it. [...]

1 support was priced off its zero-stress envelope: building its bond
profile raised RuntimeError, so it carries less reinforcement than the
model declares. That is a defect in the support type rather than a
property of the model.
```

La tercera es la que enseña por qué las dos razones no podían compartir
lista: ese soporte **contribuye**, y la cola de la función no llega a
correr, de modo que no se publica «0 of the 1 supports placed put no
force» — una frase sobre nada en absoluto, y la trampa que costó su propio
test en D98.

---

## 5. Los dos gemelos de la GUI

Ni el tooltip del lienzo (`graphics_items.py`) ni el Support Force Diagram
(`support_force_diagram.py`) pasan por `_bond_profiles`: construyen su
propio perfil y se tragaban el fallo cada uno en un `except` ancho suyo.
Arreglado el motor y no ellos, habrían sido las **dos únicas bocas que
quedaban cerradas**, y encima en el sitio donde el usuario mira primero: el
diagrama pintaría siete curvas planas a cero para un anclaje helicoidal
mientras el análisis ya explica en palabras por qué ese cero.

`support_bond` gana un canal `failures` —el idioma que el motor ya usa con
`reasons`—, propagado por `support_series` y por `series()`, de modo que la
terna que los tests leen no cambia de forma. Las dos cadenas nuevas van por
`tr()` con su entrada castellana (*perfil de adherencia*).

Se deja fuera, con la razón escrita: `ito_matsui_notes._has_negative_pressure`
también se calla con perfil ausente, pero el motor ya emite
`bond_profile_no_force` para ese mismo soporte, y una segunda frase sobre
el mismo hecho no ayuda a nadie.

---

## 6. Qué se probó

- **`tests/test_bond_profile_failure_v1163.py`**, 33 tests, ninguno un valor
  capturado: identidades contra el talud desnudo, desigualdades entre dos
  corridas del solver real, y el orden de las dos cláusulas leído del
  fuente con los comentarios quitados. Contra el árbol de 0.1.162 **falla 16
  de 33**, que es la prueba de que mide algo.
- El perfil se revienta **sin parchear nada global**: subclase de un tipo ya
  registrado, alcanzada por `type_ref`, que lanza en su propio muestreo. El
  disparador es la **presencia del contexto** y no un umbral sobre la
  tensión: `build_bond_profile` llama siempre con las seis claves
  (`project`, `x`, `y`, `pore_pressure`, `depth`, `axis_angle_rad`) y la
  caída de `force_at` llama `interface_tau(0.0)` posicional y sin ninguna,
  así que la separación es exacta y no depende de que ninguna muestra caiga
  en σ' = 0.
- El pilote Ito-Matsui se mide sobre la fixture publicada de Cai y Ugai
  (`test_ito_matsui_pile_v1123.py`) y no sobre una propia: ahí el pilote es
  **vertical**, y sobre el eje horizontal de los demás tests se pararía en
  `no_crest` antes de calcular fuerza ninguna, de modo que habría medido la
  guarda equivocada.
- **Suite entera: 3464 tests, 3463 en verde**, y el único rojo era este
  changelog sin escribir.

### El banco: los doce problemas con perfil

Se re-corrieron los **12 problemas cuyos tipos piden perfil de adherencia**
—030, 031, 087–094, 106 y 111—, que son los únicos que este cambio puede
tocar: `_bond_profiles` ni siquiera entra en el bucle para un tipo que no
declara `NEEDS_BOND_PROFILE`. Son 23 corridas y 25 archivos de resultados,
3,0 h de reloj, de las cuales los ocho muros geosintéticos se llevan 16
corridas a ~700 s cada una. Los otros nueve problemas con soporte no se
tocan: ninguno pide perfil, y para ellos manda el razonamiento —una
consulta a un `dict` vacío por soporte.

- **853 números comparados contra `Evaluaciones/0.1.160`, CERO movidos**,
  cero claves perdidas, los 25 archivos a 0.1.163. La comparación es
  recursiva por RUTA y no sólo por `metodos`, porque el 111 guarda su tabla
  en un esquema propio y es justo el problema del único anclaje helicoidal.
- Las 17 claves que hay hoy y no había en 0.1.160 son **todas
  `traccion_bases`**, el campo que `ejecutar_caso.py` empezó a escribir
  después de aquella instantánea. Se dicen porque un recuento que no
  distingue «igual» de «no había con qué comparar» es la trampa de D79.
- `balance_evaluaciones.py`: **559 filas → 559, las 559 IGUAL, sin pareja
  0/0**.
- El **111** —único anclaje helicoidal, y los dos números que SALEN del
  perfil— clavado: τ = 78,0187 kPa y F = 73,5309 kN/m, que son además los
  publicados. El **106** —único Ito-Matsui del banco— con sus nueve
  escenarios idénticos.
- `_auditoria/TRACCION_BANCO_0.1.163.md` **idéntico al de 0.1.162 salvo el
  número de versión**, y ése recorre los 111 problemas sobre sus superficies
  publicadas, no sólo los doce.
- `verificar_cierres.py D95` → **CUBIERTO POR TEST**.

**El censo, que es lo que convierte «cero dígitos movidos» en una
consecuencia y no en una coincidencia**: instrumentando `_bond_profiles`
por `sitecustomize` —y no desde el script, porque la rejilla reparte con
`ProcessPoolExecutor` y en Windows el arranque es `spawn`, así que el
trabajo ocurre en procesos hijos— el registro quedó **VACÍO**: ni un solo
perfil del banco dejó de construirse. Ningún modelo pasa por la rama que
este arreglo toca, y por eso los números no podían moverse.

Los dos constructores del 106 y del 111 reescriben sus `.ogr`, que es como
el banco los produce. Comparados campo a campo contra 0.1.160: **8
diferencias en cada uno y las 8 son uuids regenerados y
`date_created`**. Cero geometría, cero materiales, cero parámetros de
soporte, cero claves ganadas o perdidas.

---

## 7. Reportado y no corregido (regla 6)

- **El banco queda MEZCLADO**, y hay que decirlo: los 12 con perfil están a
  0.1.163 y los otros nueve con soporte —047, 048, 049, 050, 054, 059, 060,
  085 y 086— siguen a 0.1.162, así que `d94()` y `d98()` salen **PENDIENTE
  DE CORRIDA**. No es un dígito movido: es «resultados de otra versión», y
  es la consecuencia directa de haber elegido los doce en vez de los
  veintiuno. 0.1.161 dejó el banco en el mismo estado por la misma razón.
- **`d79()` sigue sin sostenerse por lo mismo que en 0.1.162**, y no por
  esto: su único punto pendiente es «filas marcadas que no tocaba: 085
  GLE/M-P», que aquel changelog ya diagnosticó —el censo de D79 buscaba
  `modelo.ogr` y el 085 tiene `modelo_activo.ogr`—. El 085 es
  `user_defined`, no pide perfil de adherencia y no se ha re-corrido aquí,
  de modo que no puede venir de esta versión. El censo de admisibilidad
  vuelve a dar **4 inadmisibles de 178** superficies publicadas, igual que
  cuando D79 se cerró.
- `max(0.0, float(...))` en el cortante convierte en 0,0 y sin decir nada
  tanto un NaN (`nan > 0.0` es falso) como un negativo. Patrón de D56 un
  escalón más abajo, y sigue en pie.
- El `try` que lee el sentido de rotura cae a `is_l2r = False` ante
  cualquier excepción, en silencio y con consecuencia numérica.
- La salida temprana de `uncontributing_support_notes` tapa la frase de
  `bond_profile_failed` cuando **otro** soporte del mismo modelo quedó
  `not_priceable`. Es la misma renuncia que D98 documentó, se acepta y queda
  escrita en el docstring: levantarla exigiría evaluar la superficie una
  segunda vez ahí, que es justo lo que D94 quitó.
