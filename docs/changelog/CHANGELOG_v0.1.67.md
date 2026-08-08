# OGR Slip2D v0.1.67 — la normal de base carga el agua, y la conversión R ↔ Kc=1

Dos cosas sin relación aparente, unidas porque la segunda destapó la
primera.

---

## 1. La normal de base ignoraba el agua embalsada

v0.1.61 añadió el agua embalsada y actualizó las ecuaciones de equilibrio
para llevarla: la iteración de todos los métodos usa
`slice_forces(...).w_total`, suelo más el agua que descansa sobre la
dovela. Lo que **no** se actualizó fue el bloque de post-proceso que
rellena `LEMResult.base_normal`, que se quedó en `s.weight` — solo suelo.

Medido sobre la geometría de la presa de Pilarcitos, con el embalse sobre
el paramento aguas arriba:

| dovela | W suelo | W agua | w_total | **N reportada** | **N con w_total** |
|---:|---:|---:|---:|---:|---:|
| 4 | 1121 | 6755 | 7876 | **1630** | **7256** |
| 8 | 1749 | 5928 | 7677 | **2339** | **6876** |
| 12 | 2007 | 5101 | 7108 | **2657** | **6181** |

Un factor de tres. Y no es un número que solo se muestre: alimenta
`checks.base_effective_stresses` y, por tanto, **la comprobación de
tensiones de tracción que puede invalidar una superficie**. La misma
omisión estaba en `checks` por su cuenta, así que la comprobación de
admisibilidad juzgaba un talud cargado por un embalse con un tercio de la
fuerza normal real — la diferencia entre "está traccionando" y no.

### Una segunda incoherencia en el mismo bloque

La tensión normal efectiva en la base es `N/l − u`, con `l` la **longitud
de base**. Se calculaba como `N/b − u`, con `b` el **ancho de dovela**:
difieren en un factor cos α, y además discrepaba de
`checks.base_effective_stresses`, que lo tenía bien.

Conviene decir qué **no** era un error: el `u·b` que aparece en el
numerador del factor de seguridad de Bishop es otra cantidad y está
correcto. Sale del álgebra del equilibrio, no de una definición de
tensión. Los dos usos de `b` parecían el mismo y no lo son.

### Cómo se sabe que ahora está bien

No con un número capturado, sino con la **identidad que la propia
expresión de Bishop es un despeje**. El método simplificado supone cortante
interdovela nulo, luego el equilibrio vertical de cada dovela es
exactamente

```
N·cos α + slide_sign · S · sin α = W_total
```

con `S = [c·l + (N − u·l)·tan φ] / F` el cortante movilizado en la base.
El test la comprueba dovela a dovela sobre los valores **reportados**, con
embalse y sin él, con tolerancia relativa 1e-6. No puede cumplirse si a W
le falta el agua.

Y una comprobación cruzada gratuita: `checks.base_effective_stresses` y el
post-proceso del método calculan la misma tensión por caminos
independientes. Ahora coinciden; antes discrepaban en el factor cos α
además del agua.

### Cómo apareció

No lo encontró ningún test: apareció al montar el caso de validación de
Pilarcitos para la fase 6. Todas las resistencias no drenadas salían cero,
porque `σ'_fc = (N − u·l)/l` daba cero al ser N un tercio de lo debido
frente a una `u` de embalse lleno. El fallo llevaba desde v0.1.61 sin que
nada lo notara, y la suite lo seguía dando por bueno.

---

## 2. Conversión entre la envolvente R y la Kc = 1

Primera pieza de la fase 6, y la que la desbloquea. Los tres
procedimientos multietapa de descenso rápido quieren vistas distintas de
los **mismos** ensayos IC-U: el Corps of Engineers quiere la envolvente R
en tensiones totales, y Lowe-Karafiath y Duncan-Wright-Wong quieren la
Kc = 1. Como son dos representaciones del mismo dato, la conversión es
exacta y biyectiva.

```
d = c_R · (cos φ_R · cos φ') / (1 − sin φ_R)
ψ = arctan[ (sin φ_R · cos φ') / (1 − sin φ_R) ]
```

Derivada de la condición de tangencia del círculo de Mohr en tensiones
totales, con la derivación completa en el docstring del módulo para que sea
auditable. Verificada contra **dos casos publicados independientes**:

| Caso | Entrada | Publicado | Calculado |
|---|---|---|---|
| Pilarcitos | c_R=60, φ_R=23°, φ'=45° | d=64, ψ=24.4° | **64.10, 24.42°** |
| Basso et al. (2024) | c_R=15, φ_R=14°, φ'=28° | d=17, ψ=15.7° | **16.95, 15.73°** |

**La trampa de φ'.** Un tutorial de referencia llama a φ' «ángulo de
rozamiento no drenado». No lo es: es el **efectivo**, el de la envolvente
drenada de esos mismos ensayos. Hay un test que comprueba que usar φ_R en
su lugar falla ambos casos publicados por más de 5 unidades — y el punto
no es el número equivocado, sino que **el número equivocado es una
envolvente perfectamente plausible**, así que nada más en el programa la
señalaría. Por eso `phi_eff` es un argumento explícito y no se lee de
ningún estado global.

Las envolventes **no** se registran como `StrengthModel`. Sería la vía
rápida a la reutilización de la interfaz, pero los modelos del registro
son seleccionables como envolvente principal de un material y ninguna de
estas dos es utilizable como envolvente drenada. Un material conserva su
`strength` efectiva y gana `drawdown_envelope` al lado.

---

## Qué se probó

- `tests/test_base_normal_v167.py`, 7 tests: la identidad de equilibrio
  vertical con embalse y sin él; que la fixture tiene de verdad más agua
  que suelo (si no, la identidad se cumpliría trivialmente también con el
  código antiguo); que quitar el embalse baja todas las normales; y que
  `checks` y el método coinciden.
- `tests/test_drawdown_envelopes_v167.py`, 11 tests: los dos casos
  publicados, la trampa de φ', round-trip exacto a precisión de máquina en
  cinco juegos de parámetros, las identidades de forma cerrada (d lineal
  en c_R, φ_R = 0 ⇒ ψ = 0, φ_R = 90° rechazado) y la envolvente compuesta
  del Corps con su cruce en σ ≈ 104 psf.

Suite completa en verde.

## Lo que queda

La fase 6 propiamente dicha: motor multietapa (etapas 1-3, K₁ y K_f por
dovela, interpolación anisótropa), envolvente compuesta del Corps en el
cálculo, validación contra Pilarcitos y el benchmark de la USACE, y la
interfaz. El motor está escrito y a la espera de que este arreglo lo
desbloquee.
