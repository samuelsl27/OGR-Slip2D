# OGR Slip2D v0.1.112

**La fuerza de un refuerzo apuntaba cuesta abajo, y lo que decidió la
dirección no fue el razonamiento sino un dibujo de la referencia**

---

## Lo que estaba mal

`_support_force_angle`, en `ogr_slip2d/support_integration.py`, devolvía
la dirección de la fuerza de un refuerzo como `axis_angle + π`, o sea
**del anclaje hacia el paramento**. Un bulón traccionado tira del bloque
**hacia** el anclaje: la fuerza salía en el sentido del deslizamiento y
**el refuerzo bajaba el factor de seguridad**.

Afectaba a dos de las cinco orientaciones, y las dos son las que un
usuario se encuentra sin tocar nada: `PARALLEL_TO_SUPPORT` y `BISECTOR`
—esta última es el `DEFAULT_ORIENTATION` de `SoilNail`, o sea el
comportamiento de fábrica—. `TANGENT_TO_SLIP` y `HORIZONTAL` salían bien
porque consultan el sentido de rotura.

Medido sobre el muro de Amherst (Sheahan 2003), plano a 50°, Janbu
simplificado:

| | 0.1.111 | ángulo | **0.1.112** | ángulo |
|---|---|---|---|---|
| *sin bulones* | *0,8519* | — | *0,8519* | — |
| `PARALLEL_TO_SUPPORT` | **0,7431** ✘ | 161,5° | **0,9606** ✔ | −18,5° |
| `BISECTOR` | **0,8207** ✘ | 105,8° | **0,9622** ✔ | 15,8° |
| `TANGENT_TO_SLIP` | 0,9256 ✔ | 50,0° | 0,9256 ✔ | 50,0° |
| `HORIZONTAL` | 0,9665 ✔ | 0,0° | 0,9665 ✔ | 0,0° |

## Lo primero que se hizo fue volver a medir

Las cinco medidas del encargo estaban tomadas en **0.1.97**, y entre
medias habían pasado D09 y D10, que reescribieron el reparto de momentos
y los métodos rigurosos. Se repitieron en **0.1.111** antes de tocar una
línea: **dígito a dígito, las mismas**. El defecto no se había arreglado
de paso.

## La dirección la decidió una figura, no un razonamiento

El argumento físico —«un bulón traccionado tira hacia el anclaje»— ya
estaba escrito en la ficha del problema 47 y llevaba quince versiones sin
convencer a nadie lo bastante como para tocar el código. Lo que lo cerró
fueron **dos figuras de la guía de la referencia**:

- **«Applied Force Orientation options»** dibuja TANGENT, BISECTOR y
  PARALLEL como tres flechas que salen **del paramento hacia el interior
  del talud**. Las tres. No hay ambigüedad que interpretar.
- La figura del *soil nail* rotula **`Li` desde el paramento hasta la
  superficie de rotura** y **`Lo` más allá** — que es exactamente lo que
  ya calculaba `force_at` en `ogr_core/support/support.py`.

O sea: las dos convenciones del módulo eran coherentes entre sí y con la
referencia. La única pieza invertida era la dirección de la fuerza.

## Y dos defectos más de la misma familia

**`SupportInstance` no heredaba `DEFAULT_ORIENTATION` — ni
`DEFAULT_APPLICATION`.** Un `SupportInstance` construido en código nacía
`TANGENT_TO_SLIP` + `ACTIVE` fuera cual fuera su tipo, así que
`GroutedTieback` (que declara `PARALLEL_TO_SUPPORT`) y `PileMicropile`
(que declara `PERPENDICULAR_TO_PILE` **y** `PASSIVE`) ignoraban en
silencio su propia declaración. La segunda mitad no la traía el encargo:
estaba en la línea de al lado.

Los dos campos son ahora centinela `None` y se resuelven en
`__post_init__` contra el registro de tipos; `SupportPattern` hace lo
mismo, porque una plantilla que fabrica instancias no puede ser el único
sitio que pisa la declaración del tipo. En `from_dict`, una clave
**ausente** hereda del tipo y una clave **presente** se respeta — antes
`data.get("orientation", "tangent_to_slip")` inventaba un valor que el
archivo no contenía.

Por qué sobrevivió tanto: **el camino de la interfaz nunca tuvo el
fallo**. `main_window.py` copia `_orientation` / `_force_application` del
tipo a mano al colocar cada soporte. Sólo fallaba el camino programático,
que es el que usa el banco de verificación.

**`PERPENDICULAR_TO_PILE` no consultaba el sentido de rotura**, aunque su
propio comentario dijera que elegía «la perpendicular que se opone al
deslizamiento». Acertaba en el problema 54 **por suerte**: el pilote está
dibujado de arriba abajo y `axis + π/2` da entonces +x, que resiste.
Dibujado al revés empujaba cuesta abajo. Ahora se elige la perpendicular
con proyección positiva sobre la tangente resistente, y el problema 54 no
se mueve un dígito.

## El criterio de cierre pedía un dato que no existe

El encargo decía: *«problema 47: 0,890 ± 3 % con la orientación que
declara el enunciado»*. **El enunciado no declara orientación.** La tabla
47.2 dice `Passive` y nada más.

Con la dirección corregida las cuatro orientaciones suben el factor, pero
no todas reproducen el manual. Sobre el plano publicado (44,17°):

| orientación | FoS | Δ vs 0,890 | mínimo del barrido | ángulo crítico |
|---|---|---|---|---|
| **`TANGENT_TO_SLIP`** | **0,9104** | **+2,30 %** | 0,9104 | **44,0°** |
| `PARALLEL_TO_SUPPORT` | 0,9309 | +4,60 % | 0,9275 | 41,5° |
| `BISECTOR` | 0,9333 | +4,86 % | 0,9299 | 41,5° |
| `HORIZONTAL` | 0,9355 | +5,11 % | 0,9314 | 41,0° |

El modelo del banco declara `TANGENT_TO_SLIP` porque es la única que
reproduce **las dos cosas a la vez**: el factor dentro del ±3 % y el
**ángulo crítico**, 44,0° frente a los 44,17° que publica el panel de la
figura 47.2 (*«Right Slip Surface Endpoint: 6.279, 6.100»*). Las otras
tres se van a 41,0–41,5°.

Y hay que decir lo incómodo: **la guía v6 de la referencia afirma que
para bulones la fuerza «se asume paralela a la dirección del soporte»**,
y ésa es justo la que se queda a +4,60 %. La versión actual de la guía ya
deja elegir las cinco y no declara cuál es la de fábrica.

**Por qué este problema es tan sensible**: sobre el plano publicado el
arranque gobierna en los dos bulones —9,8 y 21,6 kN/m frente a 78,7 de
tracción—, así que el aporte total es ~31 kN/m y depende linealmente de
dónde estén las cabezas, que son medidas de una figura. Un error de
±0,2 m en la cabeza mueve el arranque un 10–20 %: del orden del mismo 3 %
que se está discutiendo.

## Lo más instructivo no salió del código, sino de una medición

Al reevaluar el problema 59 (muro anclado, Pockoski y Duncan 2000)
apareció que **una de las tres afirmaciones con las que se documentó su
anomalía era falsa**. Decía que las cuatro orientaciones daban 0,200840
dígito a dígito y que por tanto **el ajuste no hacía nada** — una
acusación de regla 7 en toda regla.

No era el ajuste. Era el medidor: `modelo(orientacion=...)` en el
`construir_modelo.py` de ese problema **aceptaba el argumento y no lo
usaba**; el cuerpo escribía `PARALLEL_TO_SUPPORT` siempre. Las cuatro
corridas medían el mismo modelo cuatro veces. Remedido con
`_support_force_angle` parcheado a la versión vieja, el código de 0.1.97
daba 1,3235 / 0,2003 / 0,5438 / 1,3429.

Es la lección de m-alpha en v0.1.82, otra vez: **una medición equivocada
se quedó justificando una conclusión**. Y la ironía es que la conclusión
acusaba de regla 7 a un ajuste que sí la cumplía, mientras el parámetro
que de verdad no hacía nada estaba en el propio script que lo medía.

Las otras dos afirmaciones sí eran ciertas, y **las dos se dan la vuelta
al arreglar el sentido**, que es la mejor confirmación de que el sentido
era el problema: intercambiar cabeza y cola pasaba de *arreglar* el signo
(0,201 → 1,115) a *estropearlo* (1,236 → 0,315), y `PASSIVE` pasaba de
16,156703 —veinticuatro veces el caso sin anclaje— a 1,179999, por debajo
de `ACTIVE`, que es el orden que la guía declara.

## El test que habría pasado sobre el defecto

`tests/test_support_orientation_v1112.py`, 15 casos en cuatro bloques:
la identidad física (un refuerzo pasivo anclado por detrás sólo puede
resistir, con las cuatro orientaciones y en los siete métodos), la
dirección misma (`PARALLEL` **es** `axis_angle_rad()`, y la bisectriz cae
entre tangente y paralela), el valor externo (Sheahan 2003 sobre el plano
publicado, ±3 %) y la herencia de los defectos del tipo.

Con el código de 0.1.111 **fallan 7 de los 15**. El que **no** falla es
precisamente el del valor externo: usa `TANGENT_TO_SLIP`, que ya estaba
bien, así que **el test de referencia externa habría pasado limpiamente
por encima del defecto**. Lo que discrimina es la identidad de las cuatro
orientaciones. Misma lección que v0.1.110, y conviene no olvidarla: un
valor publicado reproducido no demuestra que el módulo esté bien, sólo
que ese camino lo está.

## Lo que se deja abierto, con nombre

- **La magnitud del anclaje inyectado** (banco: D39). Con el sentido ya
  corregido, el problema 59 da Bishop 1,135 frente a 0,582 publicado
  (+95 %), y 0,552 sin anclaje: en la referencia el anclaje apenas mueve
  el factor y en OGR lo dobla. OGR aplica 12 941,8 lb/ft en el cruce,
  gobernados por el arranque. Eso ya no es la dirección.
- **Nada comprueba que la cabeza esté en el paramento** (banco: D40).
  Toda la formulación descansa en ese convenio y no se valida en ningún
  sitio; *Add Support* es «primer clic, segundo clic». Dibujar el bulón
  al revés invierte `Li`/`Lo` **y** la fuerza, en silencio.
- **`_janbu_correction_factor` no elige `b1` por tipo de suelo**, aunque
  su comentario diga que sí: está fijo en 0,50. No afecta a nada de este
  trabajo —sobre un plano `d/L = 0` y f₀ vale 1 exactamente, que es por
  lo que Janbu corregido y Janbu simplificado coinciden dígito a dígito
  aquí, igual que en el manual— pero es un ajuste documentado que no
  ocurre.

---

## Cambios

### Corregido

- `ogr_slip2d/support_integration.py::_support_force_angle` — la fuerza
  paralela al soporte va de la **cabeza a la cola** (`axis_angle`), no al
  revés. `BISECTOR` hereda el arreglo.
- Íd., `PERPENDICULAR_TO_PILE` elige la perpendicular que **resiste**.
- `ogr_core/support/support.py::SupportInstance` y `SupportPattern` —
  `orientation` y `force_application` heredan del tipo de soporte cuando
  no se declaran. `from_dict` distingue clave ausente de clave presente.

### Añadido

- `tests/test_support_orientation_v1112.py` — 15 casos.
- Banco: `_tools/correr_47.py`, el barrido de planos por el pie que el
  problema 47 necesita (su `.ogr` declara rejilla circular, pero el
  manual usa *block search* y publica un plano).

### Banco de verificación (fuera del repositorio)

- **47** pasa a **+2,30 %** con Janbu simplificado y corregido, y su
  ángulo crítico a 44,0° frente a 44,17° publicados. Se quita el apaño
  `USER_DEFINED −18,5` y se declara `TANGENT_TO_SLIP`.
- **48** cambia `USER_DEFINED 190°` por `PARALLEL_TO_SUPPORT`: mismo
  ángulo, **mismo número** (1,102568), es una limpieza.
- **54** no se mueve: Bishop 1,186215 sobre el círculo publicado.
- **59** se remide entera; D17 se cierra y nacen **D39** y **D40**.
