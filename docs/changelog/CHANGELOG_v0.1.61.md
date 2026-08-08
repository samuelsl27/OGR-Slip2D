# OGR Slip2D v0.1.61 — Changelog

**Lanzamiento:** 8 de agosto de 2026
**Desarrollador:** Samuel Sáez López — Estudiante de Doctorado, UPCT
**Licencia:** AGPL-3.0-or-later

> **Agua embalsada.** Un nivel freático dibujado por encima del talud
> ahora carga el terreno, como debe. Antes devolvía factores de seguridad
> **negativos**. Por el camino aparecieron otros tres fallos, uno de ellos
> con 54 versiones de antigüedad.

---

## 🔴 Un talud sumergido daba un factor de seguridad NEGATIVO

No faltaba una función: el programa entregaba un resultado sin sentido
físico y sin avisar. Reproduciendo el caso de verificación publicado #70
con el código de v0.1.60:

| Modelo | FS que daba | FS de referencia |
|---|---|---|
| Nivel freático 30 ft sobre la coronación | **−1.61** | 1.60 |
| Nivel freático 60 ft sobre la coronación | **−3.32** | 1.60 |

La causa era directa. La presión intersticial `u` recibía **toda** la
altura de agua, incluida la que estaba por encima del terreno, pero el
**peso de esa columna de agua no se aplicaba sobre ninguna dovela**. El
término `W − u·b` se volvía fuertemente negativo, y tanto más cuanta más
agua había.

## La formulación

La documentación de referencia repite tres veces una frase cualitativa
—*«the weight of the water on the slope (vertical force), and also the
horizontal hydrostatic force exerted on the slope»*— y **no da ninguna
fórmula**. Así que se deriva de la hidrostática y se valida.

Agua en reposo sobre el terreno ejerce una presión **normal a la
superficie**, `p = γ_w · d`. Si el terreno tiene pendiente `m = dy/dx`, la
cabeza de una dovela de ancho `dx` mide `dl = dx·√(1+m²)` y su normal
hacia dentro es `(m, −1)/√(1+m²)`, luego

```
F = p · dl · (m, −1)/√(1+m²) = γ_w · d · dx · (m, −1)

   vertical   = γ_w · d · dx        ← el PESO de la columna de agua
   horizontal = γ_w · d · dx · m
```

Los «dos efectos» de la documentación son, por tanto, **las dos
componentes de una única presión normal**, no dos acciones separadas. Esa
lectura es la que hace que todo encaje:

- la componente vertical es exactamente el peso de la columna, que es por
  lo que el método Ru debe incluirla en su presión vertical;
- la horizontal integrada sobre la cara sumergida da el empuje clásico
  `½·γ_w·h²` — comprobado a **precisión de máquina** e independiente del
  número de dovelas;
- el punto de aplicación es el centro de la cabeza de la dovela, que
  comparte la x con el centro de la dovela, así que la componente vertical
  hereda el brazo del peso y solo la horizontal necesita brazo propio.

**La sísmica no toca el agua.** `kh` y `kv` se aplican solo al peso del
suelo. La referencia define la fuerza sísmica como *«coefficient × area of
slice × unit weight of slice material»*, y otro programa comercial lo
razona: el agua no tiene resistencia al corte, así que su movimiento no
genera ninguna fuerza que la masa deslizante deba soportar. Por eso el
peso del agua se lleva en campos propios de `Slice` y **no** se suma a
`weight` (que es lo que se hace con la sobrecarga distribuida).

## El anclaje: caso de verificación #70, reproducido

Del *Slope Stability Verification Manual* (Parte III), problema #70, a su
vez tomado de **Duncan & Wright (2005), figura 6.27, p. 88**. La geometría
estaba en una figura rasterizada dentro del PDF; se extrajo la imagen
incrustada y se leyó de ella:

```
Contorno externo: (0,0) (140,0) (140,45) (105,45) (30,15) (0,15)
Material único:   c' = 100 psf,  φ' = 20°,  γ = 128 pcf,  γ_w = 62.4 pcf
Caso 1: NF horizontal en y = 75    Caso 2: NF horizontal en y = 105
Círculo crítico publicado: centro (49.42, 88.56), R = 76.08
```

Resultados sobre ese círculo, con el árbitro de Duncan & Wright en 1.60:

| Método | γ' boyante, sin agua | NF y = 75 | NF y = 105 |
|---|---|---|---|
| **Bishop** | 1.6003 | **1.6006** | **1.6006** |
| **Spencer** | 1.6003 | **1.6006** | **1.6006** |
| **GLE / M-P** | 1.6002 | **1.6005** | **1.6005** |
| Janbu simplificado | 1.4890 | 1.4901 | 1.4910 |
| Janbu corregido | 1.5804 | 1.5815 | 1.5824 |
| Lowe-Karafiath | 1.6081 | 1.6092 | 1.6099 |
| Ordinary / Fellenius | 1.5128 | 1.2019 | 1.1843 |

Los tres métodos que la referencia publica para este caso dan **1.60** y,
lo que más importa, **el mismo número con 30 y con 60 pies de agua
encima**. Esa invariancia es la firma física del tratamiento correcto: el
peso añadido y el empuje añadido se cancelan exactamente. Un signo, un
brazo o una componente mal puestos la rompen — y de hecho la rompieron
varias veces durante el desarrollo.

La columna boyante es el otro anclaje: los dos procedimientos equivalentes
de Duncan & Wright (pesos totales + fuerzas de contorno + u, frente a
pesos boyantes `γ' = γ − γ_w` sin agua) deben coincidir, y coinciden.

**Ordinary/Fellenius no cumple la equivalencia, y es correcto que no la
cumpla**: su normal en la base es `W·cosα` sin corregir, de modo que con
presiones intersticiales altas `N − u·l` se hunde. Es el error clásico y
documentado del método en análisis en tensiones efectivas, no un defecto
de esta implementación — se comprueba porque ya subestimaba (0.666 frente
a 0.759 de Bishop) en un modelo **sin** embalse.

---

## 🔴 Lowe-Karafiath: el camino equivocado que enseñó más

Con el embalse puesto, Lowe-Karafiath daba **5.0** donde los métodos
rigurosos daban 1.60, y en el caso más profundo el buscador de raíz se iba
a 0.22. La primera hipótesis —un signo mal puesto— resultó falsa: probados
los dos signos, ninguno convergía.

La causa real es conceptual. En la formulación en tensiones totales, la
fuerza que cruza un contorno entre dovelas es la suma de una parte
efectiva y de **la presión de agua integrada sobre la cara, que es
horizontal**. Los métodos que *resuelven* la inclinación interdovela
(Spencer, GLE) o que la suponen horizontal (Bishop, Janbu) son
insensibles al reparto. Lowe-Karafiath la **prescribe** en ½(β+α): obligar
a una resultante dominada por agua casi horizontal a inclinarse 20°
inventa una componente vertical enorme que no existe.

El diagnóstico se cerró con una prueba limpia: con el nivel freático
siguiendo la superficie del terreno (u hidrostática, sin embalse)
Lowe-Karafiath daba 0.768 frente al 0.759 de Bishop, perfectamente sano.
Solo el embalse lo rompía.

Corregido separando el empuje de agua de cada cara interdovela
(`interslice_water_thrust`, que integra la presión intersticial real del
proyecto a lo largo de la cara, no solo la hidrostática). Con eso
Lowe-Karafiath vuelve a 1.609 y recupera la invariancia.

## 🔴 La fuerza de la grieta de tracción llevaba 54 versiones sin usarse

`slicer.py` calculaba `½·γ_w·h_w²` y su cota de aplicación desde v0.1.7,
los guardaba en `Slices.tension_crack_force/_arm`, y **ningún método LEM
los leía**. El empuje del agua en una grieta llena se ignoraba y el factor
de seguridad salía **sobreestimado, del lado inseguro**.

Su test lo tapaba: la aserción vivía dentro de `if
sl.tension_crack_force > 0`, que nunca se evaluaba a algo que pudiera
fallar. Un test de una condición que nunca se cumple no protege nada.

Conectada ahora por el mismo canal que el embalse. Sobre un talud de
prueba, una grieta llena baja el FS entre un **6 % y un 9 %** en los seis
métodos, que es la dirección correcta.

⚠️ **Esto cambia el número** en cualquier modelo con grieta de tracción con
agua. Es una corrección, no una regresión.

## 🔴 Dibujar cualquier superficie de agua rompía el lienzo

`QGraphicsItem` se usaba en el rótulo W / P / D sin estar importado en
ningún sitio, así que pintar un nivel freático, una piezométrica o una
línea de desembalse lanzaba `NameError` y tumbaba el repintado completo.
Sobrevivió porque **ningún test dibujaba una superficie de agua**.
Verificado contra el commit anterior antes de tocarlo.

## 🔴 Tres casillas de agua embalsada que no hacían nada

`show_ponded_water`, `ponded_water_fill` y `ponded_water_hatch` estaban en
`DisplayOptions` y en el diálogo de Opciones de visualización desde
v0.1.23, y no las leía nadie: la casilla existía y no movía un píxel.
Regla 7 incumplida y ya publicada. Ahora el lienzo dibuja la región
embalsada —rayado vertical azul, con relleno opcional— entre el contorno
externo y la superficie de agua, y las tres casillas la gobiernan.

---

## 🔧 Otros cambios

- **Mecanismo general de fuerzas externas por dovela**: `Slice` gana
  `water_weight`, `water_force_h` y `water_force_h_moment`. El momento se
  guarda respecto de `y = 0` en vez de una cota de aplicación porque sobre
  una misma dovela pueden actuar el embalse y una grieta **con signos
  opuestos**, y entonces una «cota media ponderada» no está definida.
  Módulo nuevo `ogr_slip2d/external_forces.py` con el helper que comparten
  los siete métodos.
- **Qué embalsa**: el nivel freático y la línea de descenso rápido. Una
  **piezométrica nunca embalsa**, ni en el cálculo ni en el dibujo — es la
  primera de las tres diferencias documentadas entre ambas entidades, y la
  segunda (γ_sat) se cerró en v0.1.60.
- **Ru**: su presión vertical pasa a incluir el peso del agua embalsada
  (`u = ru·(γ·z + γ_w·d)`), como documenta la referencia. Sigue
  excluyendo las cargas externas y la sísmica.
- El embalse actúa **con cualquier método de agua subterránea**,
  incluido Ru y las rejillas de presión.

## 🧪 Tests

Archivo nuevo `tests/test_ponded_water_v161.py`, 22 casos:

| Grupo | Qué protege |
|---|---|
| `TestVerification70` | El FS árbitro 1.60 con los dos niveles de agua, la invariancia con la profundidad, y que el FS nunca sea negativo |
| `TestDuncanWrightEquivalence` | Pesos totales + agua ≡ pesos boyantes, para los tres métodos rigurosos; Janbu y Lowe-Karafiath dentro de su propia precisión |
| `TestForceDecomposition` | `Σ F_h = ½γ_w(d₁²−d₂²)` exacto; el peso vertical contra el área embalsada en forma cerrada |
| `TestOnlyWaterTablesPond` | La piezométrica no embalsa; la línea de desembalse sí |
| `TestSeismicIgnoresPondedWater` | `kh` proporcional solo al peso del suelo; más agua no aumenta la sísmica |
| `TestRuIncludesPondedWater` | `u = ru·(γ·z + γ_w·d)`, valores analíticos |
| `TestTensionCrackForceReachesTheResult` | La fuerza llega a una dovela y baja el FS en los seis métodos |
| `TestCanvasShowsPondedWater` | Las casillas mueven el dibujo; la piezométrica no; el rótulo no revienta el lienzo |

Actualizado `tests/test_tension_crack.py`: fuera el `if` que hacía vacía la
aserción de `½γ_w h²`, y comprobación de que la fuerza llega a la dovela.

Los casos de validación no se tocaron: `ej1` no tiene nivel freático ni
grieta de tracción.

## 📋 Limitaciones conocidas

- **Tercera diferencia NF ↔ piezométrica**: una rejilla de presiones
  combinada con un nivel freático debería forzar `u = 0` por encima de
  este. Sin implementar.
- **No hay selector de superficie de agua por material**
  (`water_surface_id`): se coge siempre la primera del tipo, así que con
  varias piezométricas el resultado es arbitrario.
- Con **elementos finitos**, el embalse debería venir de las condiciones
  de contorno de altura total, no del nivel freático.
- `Material.hu`, `.auto_hu` y `.b_bar` siguen sin ser campos: se leen con
  `getattr` y solo existen si alguien los inyecta.
- De los cuatro métodos de descenso rápido del combo, solo `b_bar` existe.
- **Dovela entera**, sin partir en tramo húmedo y seco (heredado).
- Los **soportes** solo los integra Bishop.
- La fuerza horizontal del agua entra en el momento **solo para
  superficies circulares**, igual que ya ocurría con el término sísmico.
- **Ordinary/Fellenius** subestima el FS con presiones intersticiales
  altas. Es el método, no la implementación, pero conviene saberlo antes
  de usarlo en un talud sumergido.

---

© 2026 Samuel Sáez López — UPCT — AGPL-3.0-or-later
