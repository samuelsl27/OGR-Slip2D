# OGR Slip2D v0.1.124

**Ancla helicoidal** — siete capacidades compiten a lo largo de la barra y el
diagrama escalona al pasar cada placa; de paso, una capacidad que llevaba
ciento diez versiones sin llegar a ningún sitio encuentra el camino.

---

## Lo que se añade

El **noveno tipo de soporte**: un fuste con placas helicoidales soldadas. Lo
que lo distingue de los ocho anteriores no es la fórmula sino la forma del
resultado: su capacidad **no varía suavemente** a lo largo de la barra, sino
que **escalona** cada vez que la superficie de rotura pasa una placa, porque
una placa está o en el terreno anclado o en la masa móvil y los dos lados se
cuentan con ecuaciones distintas.

Tres modos compiten en cada punto y la fuerza aplicada es el menor:

```
F1  arrancamiento   min(rotura somera, corte cilíndrico, hundimiento) / S
F2  tracción        T / S
F3  descabezamiento [min(los mismos tres, del lado móvil) + H] / S
```

y el arrancamiento y el descabezamiento son cada uno el menor de **tres tipos
de rotura**, que es de donde salen las siete capacidades.

Es el hueco **D29** del banco de verificación (problema 111).

## De dónde sale cada ecuación

Ninguna es de este proyecto, y conviene poder distinguir lo publicado de lo
supuesto:

| Pieza | Fuente |
|---|---|
| `N_q = e^{π·tanφ}·tan²(45+φ/2)` | Prandtl (1921), Reissner (1924); forma profunda de Meyerhof (1976), usada para hélices por Perko (2009) |
| `N_c = (N_q−1)·cotφ`, límite `2+π` | Prandtl (1921) |
| `A·(1,3·c·N_c + q'·N_q)` | **Terzaghi (1943)**, zapata **circular** `q_u = 1,3cN_c + γDN_q + 0,3γBN_γ`, sin el término de peso propio |
| Hundimiento individual | Perko (2009) |
| Corte cilíndrico | Mitsch y Clemence (1985) para arenas, Mooney, Adamczak y Clemence (1985) para limos y arcillas; Perko (2009) |
| Rotura somera | Perko (2009) |

**Y dos simplificaciones que no son nuestras, escritas en el docstring para
que se vean.** El método clásico de corte cilíndrico lleva un coeficiente de
empuje lateral `K` en arenas y un factor de adherencia `α` en arcillas; aquí
valen 1, porque la formulación declara que la tensión sobre el cilindro es la
vertical. No se ofrecen como parámetros: **no hay ningún número publicado
contra el que validarlos**, y un mando sin validar que mueve la respuesta es
peor que no tenerlo. Y para φ = 0 el término de hundimiento vale `1,3 × 5,14`
veces la resistencia sin drenar, donde la literatura de anclas usa `N_c = 9`
para placas profundas en arcilla; se conserva la forma de Prandtl porque es
con la que se produjeron los números publicados.

## Sin umbral que calibrar, y esta vez se puede

`N_q − 1` cancela catastróficamente cuando φ → 0, justo donde tiene que
dividir una cotangente que crece sin límite. La versión literal pierde todas
las cifras ahí. Tomando logaritmos primero,

```
ln N_q = π·tanφ + 2[log1p(t) − log1p(−t)],   t = tan(φ/2)
N_q = exp(·)          N_c = expm1(·)/tanφ
```

los dos salen exactos a la última cifra para cualquier φ > 0, y el límite
`N_c → 2+π` llega **por continuidad**. Medido década a década: la diferencia
dividida por φ se estabiliza en 13,218 desde 1e-4 hasta 1e-12, que es la
derivada de `N_c` en cero.

Merece contraste con la versión anterior: el pilote de Ito y Matsui de
v0.1.123 **sí** necesitó un umbral medido, porque su cancelación es
irreducible. Ésta es **removible**, y una cancelación removible se quita, no
se rodea.

## Cómo llega el estado del terreno: dos mitades, y sólo una es por metro

El cilindro que rompe es `πD·∫τ dl` y eso es la maquinaria de v0.1.116: el
perfil muestreado una vez por análisis. La integral no es un lujo — es lo que
hace que un fuste que atraviesa tres materiales cobre la resistencia de cada
tramo.

Pero el **hundimiento existe en las placas y en ningún punto intermedio**, y
ninguna media por segmento puede sustituirlo. Así que el muestreador se
generaliza: un tipo declara `station_distances(L)` y `station_value(σ'v, ...)`,
se evalúan en la **misma pasada y con el mismo estado de tensiones**, y viajan
en `BondProfile.stations`. Con eso `force_at(d, L, bond)` **no cambia de
firma** para ninguno de los nueve tipos y la caché sigue siendo un solo objeto.

**Y la pregunta de dónde sale τ resultó no ser una pregunta.** La formulación
necesita `c` y `φ` por separado —uno multiplica `N_c` y el otro decide los dos
factores— y además `τ` sobre el cilindro. Podían haber sido dos opiniones
distintas sobre el mismo suelo en el mismo punto. No lo son:
`_local_c_phi` construye una **tangente verdadera**, así que `c + σ'·tanφ` **es**
`τ(σ')` por construcción. Medido sobre los diecisiete modelos constitutivos:
diferencia máxima **8,5e-13**. Queda atado con un test, que es la forma honesta
de decir «son lo mismo».

## Una capacidad que llevaba ciento diez versiones sin llegar a ningún sitio

`shear_at` y `SUPPORTS_SHEAR` los declaraban tres tipos desde v0.1.14. El
parámetro `shear_capacity` era editable, se guardaba en el `.ogr` y **no lo
leía nadie** fuera de `ogr_core/support/support.py`. Un mando configurable que
no puede mover el número es exactamente el defecto que la regla 7 existe para
evitar; quedó documentado en D28 y se cierra aquí.

Lo que hace está escrito con todas las letras en la documentación de la
referencia: «el vector perpendicular a la dirección del bulón, y opuesto a la
dirección de rotura, **se suma al vector de capacidad** […] la fuerza en la
base de la dovela ya no es paralela al soporte sino inclinada en sentido
contrario al deslizamiento». Es decir, un **segundo vector**, no un axil más
grande. Se suma en `compute_support_effects`, y la resultante sustituye al
axil de ahí en adelante: el reparto `T_S`/`T_N`, la bandera activo/pasivo y los
nueve métodos siguen intactos.

**El riesgo de regresión es cero y es medible**: los cuatro tipos que declaran
`shear_capacity` lo traen a 0,0, así que la suma vectorial devuelve el vector
axil **bit a bit**. Va con test sobre los nueve métodos.

De paso, la regla de *qué* perpendicular resiste —que ya estaba escrita y
razonada para `PERPENDICULAR_TO_PILE` desde v0.1.112— se extrae a
`_resisting_perpendicular` y la usan los dos sitios que la necesitan.

## El diagrama de fuerza del soporte

Hasta ahora `force_at` devolvía sólo el mínimo, así que **no había forma de
saber qué modo mandaba**. Para un bulón inyectado eso es una curiosidad; para
un ancla helicoidal es el interés entero, porque siete capacidades compiten y
el ganador cambia dos veces en cinco metros.

Un tipo publica ahora sus modos con `capacity_modes`, y **`force_at` pasa a
ser su mínimo**. Escribir cada fórmula una sola vez es el objetivo: si el
diagrama recalculase las capacidades por su cuenta, las dos escrituras
acabarían derivando. Un test ata `force_at == min(capacity_modes)` para los
nueve tipos.

La ventana es **no modal**, como todo gráfico informativo de este programa, y
lleva un desplegable de soportes, una serie por modo, la envolvente aplicada
más gruesa y una marca en el corte con la superficie crítica. La acción está
en **Data → Support Force Diagram…**, junto a *Support Force Analysis…*, y se
deshabilita con su tooltip cuando el modelo no tiene soportes.

## El problema 111 cierra, y tres afirmaciones de partida eran falsas

Dos de ellas de la propia ficha del banco:

1. **«El manual no publica ningún factor de seguridad».** Lo publica: la
   figura 111.2 lleva **2,746** en su recuadro verde, con los dos hilos que
   Slide2 dibuja desde los extremos de la superficie.
2. **`confianza_geometria: "no aplica"`.** La figura 111.1 está **rotulada
   punto por punto** —(0,0) (15,0) (15,12) (7,5·12) (7,5·5) (0,5), ancla de
   (7,5·7,5) a (12,5·7,5)— y su tabla de propiedades es completa.
3. **Y el manual se equivoca en su propia aritmética**, sin consecuencia:
   escribe `F3 = min(140.5103, …) = 140.5103` donde su línea anterior y su
   Tabla 111.1 dan **104,5103**. Dígitos transpuestos; el mínimo sigue siendo
   73,5309.

**Lo que sí se reproduce, y exactamente:**

| Magnitud | Publicado | OGR 0.1.124 |
|---|---|---|
| Resistencia del suelo sobre el fuste | 78,0187 kPa | 78,0187 |
| Área proyectada equivalente | 0,023562 m² | 0,023562 |
| `N_q` · `N_c` | 33,2961 · 46,1236 | 33,2961 · 46,1236 |
| Hundimiento de una placa | 91,7987 kN | 91,7987 |
| **Fuerza aplicada en (11 · 7,5)** | **73,5309 kN/m** | **73,5309** |
| Tabla 111.1 (11 × 7 = 77 celdas) | — | todas, < 1e-3 |
| Diagrama publicado cada 0,1 m | — | todos, < 1e-3 |

Y algo que no estaba en el plan: el diagrama publicado está dibujado **modo a
modo y en color**, así que **qué capacidad gana** está publicado además de su
valor. Se comprueba: descabezamiento hasta 3,102 m, tirante hasta 3,266,
arrancamiento después. Los dos cambios de modo caen en un tramo que **ninguna
fila de la tabla cubre**, así que sin ellos el modo de tracción podría
eliminarse entero y las 77 celdas seguirían pasando.

## Y una discrepancia medida que no se tapa

**El 2,746 no sale.** Sobre la superficie publicada —digitalizada de la figura
píxel a píxel: (7,5 · 5,0) → (11,0 · 7,5) → (12,5 · 12,0), con el quiebro
exactamente en el ancla— OGR da **1,88** con Bishop y la orientación
declarada, y entre 1,32 y 1,91 en las cuarenta y cinco combinaciones de nueve
métodos por cinco orientaciones. Sin ancla, 1,24.

Lo que se ha comprobado antes de decirlo:

- la **geometría es la del manual**: el peso de la cuña sale 465,5 kN/m contra
  470 calculados a mano, y la longitud de la base 9,014 m contra 9,05;
- el **factor sin ancla es correcto**: un Fellenius a mano sobre dos tramos da
  1,275 contra 1,2840 de OGR;
- está **convergido**: de 20 a 200 dovelas se mueve un 0,1 %;
- y no es un desliz de unidades en ningún dato: `c = 45` daría 3,21, `φ = 45`
  daría 2,64 y `γ = 10` daría 2,65. Ninguno es 2,746.

El manual **no dice con qué método** calcula ese número. Queda anotado como
discrepancia medida y sin causa nombrada, que es lo que se hace con un
resultado que no se entiende: publicarlo. La validación del tipo no depende de
él —el ancla es el diagrama de fuerza, que se reproduce cifra a cifra—.

## Dos cosas que la regla 7 dice mejor cuando se mide dónde

El barrido de parámetros se hace sobre **el diagrama entero**, no sobre un
punto, y por una razón: la fuerza aplicada es un **mínimo**, así que un ajuste
puede ser invisible en una posición y decisivo en otra. Medir un punto sería
medir el mínimo, no el ajuste.

- **El número de hélices** mueve el diagrama en **tres** de cincuenta y una
  posiciones muestreadas, y en ninguna otra. Lo esconden dos cosas: la rama de
  rotura somera, que gobierna el arrancamiento aquí y depende sólo de la
  distancia a la placa **más lejana** —la punta, sean las que sean—, y la
  cabeza, que topa todo lo que queda a su izquierda.
- **El fuste** entra sólo por el área que le quita a la placa, así que sólo
  puede mover un término de hundimiento; y en este modelo **ningún término de
  hundimiento gana nunca**. Subiendo la cabeza y el tirante, los dos mueven el
  diagrama de inmediato.

Las dos cosas están en el test, con su razón. La comprobación evidente —un
parámetro, un punto— habría llamado inerte a un ajuste que no lo es.

## Y una nota sobre el modelo, no sobre el cálculo

Tres avisos, ninguno de los cuales corrige nada: la relación
separación/diámetro fuera de la banda 5–12 que recomiendan las guías de
diseño; un fuste que no es más estrecho que la hélice (que deja área nula, y
entonces el ancla no resiste nada al arrancamiento); y un grupo de hélices que
no cabe en la barra, diciendo **qué separación se usó** en su lugar. Un ajuste
silencioso es cómo un modelo acaba significando algo que el usuario nunca
escribió.

## Fuera de alcance, a propósito

**La capacidad a compresión.** La referencia la ofrece —el cálculo de tracción
con la capacidad de compresión sustituida y la cabeza a cero—, pero OGR no
tiene noción de un soporte comprimido: no hay de dónde leer el signo.
Declarar el parámetro sería declarar un ajuste que no puede mover el número,
que es justo el defecto que esta versión cierra por otro lado.

## Archivos

- `ogr_core/support/helical_anchor.py` — **nuevo**: las siete funciones puras
  y el tipo
- `ogr_core/support/bond.py` — `stations`, y el muestreador que las evalúa
- `ogr_core/support/support.py` — `capacity_modes`, `station_distances`,
  `station_value`; los tres tipos de la familia tieback publican sus modos
- `ogr_slip2d/support_integration.py` — el cortante vectorial y las dos
  funciones de dirección
- `ogr_slip2d/helical_anchor_notes.py` — **nuevo**
- `ogr_gui/dialogs/support_force_diagram.py` — **nuevo**, no modal
- `ogr_gui/interpret_window.py` — la acción de menú
- `ogr_gui/dialogs/define_support_dialog.py` — `shaft_type`, editor entero,
  `PARAMETER_ENABLED_WHEN`
- `tests/test_helical_anchor_v1124.py` — **nuevo**, 46 tests
- `docs/plugins.md`, `spec/features/004-ancla-helicoidal/`

Suite entera: **2647 / 2647**.
