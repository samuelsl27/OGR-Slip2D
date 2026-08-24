# OGR Slip2D v0.1.110

**El defecto del encargo llegaba ya arreglado, y eso no lo cerraba: faltaba
el test que lo sujeta y faltaba medir el problema que mejor lo prueba. Al
escribir el test, la primera versión habría pasado sobre el defecto que
lleva en el nombre.**

El encargo describía la anomalía **A2-2** (defecto **D14** del banco): el
empuje hidrostático del agua de la grieta de tracción se aplicaba **siempre a
la profundidad completa** del contorno, fuese cual fuese la superficie. La
consecuencia medida era espectacular — la búsqueda del problema 2 caía en un
círculo de R = 1,58 m al que se le aplicaban 73,5 kN sobre un peso propio de
50 kN, dando FoS 0,96 donde sin grieta da 9,67.

Las medidas del encargo eran de **0.1.97**, así que lo primero fue volver a
medirlas. Ya no se reproducían.

---

## 1 · La causa la había quitado la versión anterior

`ddc8942`, la **v0.1.109**, cerró **D13** —el truncado del arco en la
grieta— y con él la causa de D14. El encargo lo había anticipado en su
última línea: *«truncar el arco y calcular el empuje sobre la profundidad
real son la misma cuenta; hazlos en el mismo trabajo»*. Tenía razón hasta el
final: no eran dos arreglos, era uno.

Truncar deja una **pared vertical** desde la línea de grieta hasta el
terreno. El empuje se integra ahora sobre esa pared en vez de sobre el
contorno, así que la profundidad mojada es la real **por construcción**, y
una superficie que no abre pared no recibe nada.

Comprobado, no supuesto:

| | medido en 0.1.110 | publicado | Δ |
|---|---|---|---|
| **P2** bishop, **en la búsqueda** | **1,595773** | 1,596 | **−0,01 %** |
| P2 bishop, círculo publicado | 1,595632 | 1,596 | −0,02 % |
| P2 janbu corregido, círculo publicado | 1,488622 | 1,489 | −0,03 % |
| P2 janbu corregido, en la búsqueda | 1,490008 | 1,489 | +0,07 % |
| P2 spencer / gle | 1,591579 / 1,592259 | 1,592 | −0,03 % / +0,02 % |
| P27 grieta + 6 ft de agua, bishop | 1,52381 | 1,511 | +0,85 % |
| **P42** spencer, círculo publicado | **1,922135** | 1,925 | **−0,15 %** |
| P42 spencer, búsqueda en rejilla | 1,922273 | 1,925 | −0,14 % |

La búsqueda del problema 2 venía de **0,9594, un −39,9 %**.

---

## 2 · Dos correcciones al enunciado del defecto

### 2.1 · El círculo de 1,58 m no recibe un empuje menor: se descarta

El criterio de cierre pedía que el empuje sobre un círculo que no alcanza la
base de la grieta fuese **menor** que el de uno que sí. La respuesta resultó
ser más fuerte que lo pedido: ese círculo está **íntegramente dentro de la
zona de grieta**, no tiene plano de corte sobre el que escribir un
equilibrio, y contestarle un número sería aritmética sobre un mecanismo que
no existe. La referencia tiene código de error propio para ese caso.

### 2.2 · Los 73,46 kN del círculo publicado siguen siendo 73,46, y está bien

Ésta es la parte que conviene no olvidar. La grieta del problema 2 es
**horizontal** a y = 31,13 bajo una coronación **llana** a y = 35,0, así que
la pared mide 3,87 m **se corte donde se corte**. El número repetido nunca
fue la señal del defecto: la señal era que **el círculo de 1,58 m recibiera
la misma**.

Y esto tiene una consecuencia directa sobre cómo se prueba, que es §4.

---

## 3 · El problema 42 era la mejor prueba del banco, y nadie la había cobrado

No estaba en el criterio de cierre; el encargo sólo pedía «comprobarlo
también». Es el que más aporta.

Su manual publica el *Left Slip Surface Endpoint* en **(108,930 · 49,000)** y
el *Left Slope Intercept* en **(108,930 · 53,475)**: **dos puntos distintos
con la misma x**. Eso es el truncado dibujado con números — el arco acaba en
la grieta, y de ahí una pared vertical sube al terreno.

| | 0.1.108 | 0.1.110 |
|---|---|---|
| Spencer, círculo publicado | 1,8746 (**−2,6 %**) | **1,922135** (−0,15 %) |
| Spencer, búsqueda en rejilla | 1,87015 (−2,9 %) | 1,922273 (−0,14 %) |
| Extremo izquierdo de la masa | 105,749 (el terreno) | **108,9297** (la grieta) |
| Extremo derecho de la masa | — | **257,857** (publicado 257,856) |

Y la ficha del 42 leía su propio error al revés: llamaba al −2,6 % *«un buen
acuerdo»*. Los 3,2 m de arco entre 105,749 y 108,930 aportaban resistencia
sobre un plano que no puede aportar ninguna, **siempre del lado inseguro**,
que es lo contrario de lo que un −2,6 % sugiere. Un error con signo conocido
no es un residuo: es una deuda.

---

## 4 · El test, y por qué el primer borrador no valía

`tests/test_tension_crack_thrust_v1110.py`, **11 tests**. La identidad que
pedía el encargo: el empuje de una grieta llena a profundidad h es
½·γ_w·h² por metro de ancho, con h la profundidad mojada **por encima de la
superficie**, y con su brazo a h/3 sobre la base de la columna de agua —
Terzaghi (1943), *Theoretical Soil Mechanics*. Parametrizado con tres
profundidades.

**Y entonces se hizo lo que había que hacer con él: restaurar el algoritmo
pre-0.1.109 por debajo y volver a correrlo entero.**

**Fallan cinco de once.** Los seis que no fallan incluyen **la identidad
completa**, y ésa es la lección de esta versión:

> Sobre una grieta **horizontal** bajo una coronación **llana**, la
> profundidad del contorno en la dovela exterior y la altura de la pared son
> **el mismo número**. Los dos algoritmos coinciden dígito a dígito. La
> identidad no distingue nada — que es exactamente por qué los 73,46 kN
> parecían correctos durante cien versiones.

Un test que sólo tuviera la identidad **habría pasado sobre el defecto que
lleva en el nombre**. Es la misma trampa que la regla 1 describe para las
instantáneas, sólo que disfrazada de forma cerrada.

### El discriminante que sí vale

Una zona de grieta sobre el **pie** del deslizamiento. La grieta se forma en
la cabecera; el pie está en compresión, así que esa zona **no abre pared** y
el empuje es **0 kN**. El algoritmo viejo buscaba una dovela dentro del rango
en x del contorno, la encontraba, y entregaba **680,7 kN** sobre una grieta
que la superficie nunca abrió: factor de seguridad **1,1112 contra 0,7892**,
un 29 % de caída salida de un contorno que el mecanismo no ve.

Y ese margen **no se encoge al refinar la malla**. El otro sí: la diferencia
«profundidad leída a media dovela de la pared» vale 3,6 cm con 60 dovelas y
converge a cero. **Un test cuya discriminación se desvanece al refinar es un
test que dejará de funcionar** — y con truncado, «la dovela exterior» y «la
pared» son cada vez más el mismo sitio.

### Un hallazgo de propina: el empuje viejo sujetaba el talud

Midiendo el A/B salió algo que no se buscaba. Con el algoritmo pre-0.1.109,
**más agua en la grieta SUBÍA el factor de seguridad**: 1,0714 con la grieta
vacía contra 1,1241 con ella llena. El empuje caía en una dovela que no era
la suya, con un sentido que sujetaba el talud. Agua en una grieta de tracción
no puede estabilizar nada, y ahora hay un test que lo dice.

### Regla 7, un hueco que llevaba abierto desde v0.1.7

`percent_filled` existe desde **v0.1.7**, tiene su control en el diálogo de
la grieta, y estaba probado — sobre `water_level_at`, una **función pura dos
capas por debajo del análisis**. Nada comprobaba que mover ese control
moviera el **factor de seguridad**, que es lo único que el usuario le está
pidiendo. Lo mismo con `FILLED_TO_DEPTH`, que es el modo que usa el problema
27 del banco. Ahora los dos tienen su test de punta a punta.

No fue necesario tocar código de producción: la medición demostró que los
siete modos ya llegaban hasta el factor. Lo que faltaba era el test.

---

## 5 · Qué se ha tocado

| Archivo | Qué |
|---|---|
| `tests/test_tension_crack_thrust_v1110.py` | **nuevo**, 11 tests |
| `pyproject.toml`, `ogr_gui/main_window.py`, los cinco `__init__.py` | 0.1.110 |

**Ningún cambio en código de producción.** Esta versión es una medición y un
test; el arreglo estaba en la anterior.

---

## 6 · Qué se ha probado

- La suite entera, sin filtrar.
- Banco: problemas **2** (círculo publicado y búsqueda), **27** con
  `modelo_grieta_agua.ogr`, y **42**, con la comparativa y la auditoría de
  invariantes regeneradas.
- El **A/B contra el algoritmo pre-0.1.109**, restaurado desde `9c2cbd3` y
  puesto debajo del archivo de test entero.

## 7 · Qué falta por probar

- **D13 sigue formalmente abierto** en `ERRORES_Y_DISCREPANCIAS.md`, y con
  razón: su código está corregido desde 0.1.109 y sus criterios se cumplen
  salvo el factor del problema 12 —que se queda a −4,84 % por el spline con
  tensión, con causa nombrada—, pero su revalidación son los **diez** modelos
  con grieta y aquí se han corrido tres. Cerrarlo con esta evidencia sería
  cerrarlo de oídas.
- Los problemas **60 y 73**, omitidos literalmente por D13, y los **56, 57 y
  64**, que necesitan que se les construya el contorno de grieta que hoy no
  tienen.
- El spline con tensión de Franke (1985), anotado en `docs/PENDIENTES.md`.
- La exención del 5 % superior de dovelas en `checks.py` *«porque son, en
  realidad, la zona de grieta de tracción»*. Con un truncado de verdad esa
  excusa se debilita; medirlo sigue siendo otra tarea.
