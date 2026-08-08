# OGR Slip2D v0.1.68 — descenso rápido multietapa

Última fase de la deuda anotada al cerrar v0.1.61, y la más grande. El
combo de descenso rápido ofrecía cuatro entradas desde v0.1.8 y **solo B̄
calculaba algo**: elegir cualquiera de las otras tres no producía Δu, ni
aviso, ni diferencia. Es la regla 7 en su forma más pura, sostenida
durante sesenta versiones.

Ahora las tres están implementadas y validadas contra un caso publicado.

---

## Los tres procedimientos

Comparten **una sola función** y se distinguen por dos banderas, lo que
convierte una de sus propiedades en estructural en vez de esperada:

| Procedimiento | Etapas | Resistencia no drenada |
|---|---|---|
| Lowe y Karafiath (1960) | 2 | interpolación anisótropa |
| Duncan, Wright y Wong (1990) | 3 | ídem, más comprobación drenada |
| Cuerpo de Ingenieros (1970) | 2 | envolvente compuesta `min(R, efectiva)` |

**Etapa 1** — embalse lleno, tensiones efectivas. De la solución sale, por
dovela, el estado de consolidación que el suelo alcanzó:

```
σ'_fc = N' / Δl                              (2)
τ_fc  = (c' + σ'_fc·tan φ') / FS₁            (3)
```

`τ_fc` es la tensión **movilizada**, no la resistencia: sale de la propia
definición del factor de seguridad, τ = s/FS.

**Etapa 2** — nivel descendido. Cada dovela no drenada recibe una
resistencia interpolada **linealmente en K_c** entre los dos extremos
físicos, ambos evaluados en el mismo σ'_fc:

```
τ_ff|Kc=1  = d + σ'_fc·tan ψ          (ensayos IC-U, cota inferior)
τ_ff|Kc=Kf = c' + σ'_fc·tan φ'        (envolvente drenada, cota superior)

τ_ff = [ (K_f − K_1)·τ_ff|Kc=1 + (K_1 − 1)·τ_ff|Kc=Kf ] / (K_f − 1)   (5)
```

La cota superior es la envolvente **drenada** porque en K_c = K_f la rotura
ocurre durante la propia consolidación, luego σ'_ff = σ'_fc y τ_fc = τ_ff.
La dovela pasa entonces a `c = τ_ff`, `φ = 0`, `u = 0`.

**Etapa 3** (solo DWW) — si la resistencia drenada a la tensión efectiva
posterior al descenso resulta menor que la no drenada, se sustituye y se
recalcula. Una resistencia no drenada por encima de la drenada solo se
sostiene con presiones intersticiales negativas, que la cavitación o el
drenaje parcial pueden no permitir.

Como la etapa 3 **solo puede bajar** una resistencia, `FS_DWW ≤ FS_L-K` se
cumple en cualquier modelo por construcción. Por eso las dos son la misma
función con un `stage3: bool` y no dos rutas paralelas.

## Validación: la presa de Pilarcitos

Duncan, Wright y Wong (1990) publican este caso, y es **una rotura real**:
la presa deslizó en noviembre de 1969 tras un desembalse. Un factor de
seguridad próximo a 1 es la respuesta correcta, no una tranquilizadora.

| Procedimiento | Calculado | Publicado | Error |
|---|---:|---:|---:|
| Duncan-Wright-Wong | 1.0235 | 1.047 | **−2.2 %** |
| Lowe-Karafiath | 1.0249 | 1.052 | **−2.6 %** |
| Corps 2 etapas | 0.8103 | 0.824 | **−1.7 %** |

Los tres a la vez, con una búsqueda fina (pasos de 5 ft, 2145 candidatos,
6 s). La comparación es **entre mínimos** — una búsqueda nuestra contra el
crítico publicado — porque comparar en una superficie elegida por nosotros
sería circular.

El test de la suite usa una rejilla gruesa que cabe en un segundo y cae un
3 % **por encima** de los valores publicados, mientras que la fina cae un
2 % por debajo. Ambas los encierran, que es la forma honesta de decir que
concuerdan; la tolerancia del test la fija la resolución de la rejilla que
puede pagarse, no el método.

## Que el combo mueva el número

`wrap_for_drawdown` envuelve el método LEM en **el único sitio donde se
instancian**, dentro de `_ComputeWorker.run`. Un segundo sitio que se
olvidara devolvería en silencio el factor de seguridad ordinario, que se
parece exactamente a un análisis correcto.

Las dovelas que la búsqueda pasa se **ignoran a propósito**: el
procedimiento necesita la masa rebanada a **dos niveles distintos** de
embalse, y ninguno de los dos es el que el llamante construyó.

Una superficie a la que el procedimiento no se aplica vuelve **inválida
con su motivo**, no como un factor de seguridad bajo que ganaría la
búsqueda. En una búsqueda la mayoría de candidatas son así.

## Las guardas

- **FS₁ < 1 se rechaza con error explícito.** El procedimiento presupone
  que el talud aguantaba con el embalse lleno; por debajo de 1 el estado de
  consolidación queda sobre la envolvente de rotura, K₁ supera a K_f y la
  ecuación (5) deja de interpolar para **extrapolar**, dando resistencias
  decrecientes y finalmente negativas. En una búsqueda automática eso hace
  ganar a superficies con un FS ficticio próximo a cero.
- **Envolvente curva rechazada.** El procedimiento reescribe c y φ en cada
  dovela, así que una envolvente potencial o de Hoek-Brown quedaría
  sustituida por una recta en vez de respetada.
- **Sin envolvente R o Kc=1, rechazo explícito** en vez de resistencia cero.
- **σ'₃c ≤ 0 excluye el cero, no solo los negativos**: es el denominador de
  K₁, y un NaN tragado por un `max(0, …)` posterior dejaría la dovela sin
  resistencia con aspecto de respuesta legítima. La reserva en los casos
  mal condicionados es **la menor de las dos cotas**, nunca un cero mudo ni
  una extrapolación.
- **El descenso rápido exige método de agua = superficies de agua**, y que
  algún material esté marcado como no drenado. Comprobado en el cálculo y
  no solo en el diálogo: un proyecto puede venir del CLI o editado a mano.

## Interfaz

- Las cuatro etiquetas del combo y sus tooltips **pasan ahora por `tr()`**
  con su traducción española (regla 2). Llevaban sin hacerlo desde v0.1.8.
- Selector de envolvente no drenada en el diálogo de materiales, con los
  dos campos renombrados según la forma elegida —`Cr`/ángulo para la R,
  `d`/`ψ` para la Kc=1—. Dos juegos de parámetros compartiendo dos
  spinboxes es justo donde una etiqueta equivocada se convierte en una
  envolvente equivocada, y hay un test que lo fija.
- Aviso al calcular cuando la configuración no admite el procedimiento.

### Dos correcciones pendientes desde v0.1.62

- El tooltip de *Calculate Excess Pore Pressure* decía que era **requisito**
  del descenso rápido con B̄. No lo es: `set_advanced_option` hace los tres
  avanzados **mutuamente excluyentes**, así que exigirlo habría dejado B̄
  sin calcular nada. El texto pasa a decir lo que de verdad ocurre.
- `apply()` del diálogo escribía los tres flags a mano, saltándose
  `set_advanced_option` — era el único sitio capaz de dejar dos activos a
  la vez. Ahora pasa por él.

---

## Lo que queda anotado, no resuelto

**El convenio de la línea de desembalse está invertido entre las dos
implementaciones.** El multietapa toma el nivel freático como nivel
**inicial** y la línea de desembalse como el **final, más bajo**, que es lo
que hacen la referencia y el caso publicado (Pilarcitos: inicial y = 72,
desembalse y = 37). El modelo B̄ de `pore_pressure` usa el contrario: exige
`y_desembalse > y_freático`.

No se ha unificado. Alinearlo movería el factor de seguridad de todo
proyecto guardado que use B̄, y la decisión de si eso se hace —y con qué
migración— es del usuario, no de esta fase. Queda como la deuda que esta
tanda no cierra.

**Grado de confianza del Corps.** La forma `min(R, efectiva)` de la
envolvente compuesta reproduce Pilarcitos con un −1.7 %, lo que la
respalda, pero el apéndice G de EM 1110-2-1902 (2003) es de acceso público
y el benchmark de la USACE que trae (FS = 1.44, con la superficie fijada)
sería el test que la zanja sin margen de búsqueda. Pendiente.

---

## Qué se probó

`tests/test_rapid_drawdown_v168.py`, 27 tests:

- **Caso publicado**: los tres procedimientos contra Pilarcitos, el orden
  (Corps < DWW ≤ L-K) y que la respuesta queda cerca de la unidad, que es
  lo que dice la rotura real de 1969.
- **Propiedades estructurales**: DWW nunca supera a L-K; sus etapas 2 son
  **bit a bit idénticas** (si no lo fueran, la desigualdad podría cumplirse
  por casualidad); y la etapa 1 es mucho más segura que la 2, que es el
  fenómeno entero.
- **Forma cerrada de la ecuación (5)**: τ_ff queda siempre entre sus dos
  cotas; con τ_fc = 0 (K₁ = 1, consolidación isótropa) devuelve
  exactamente la envolvente Kc=1; y nunca es negativa ni no finita, ni
  siquiera con σ'_fc = 0 o τ_fc = 10⁶.
- **Los cinco rechazos**, cada uno comprobado por separado.
- **Regla 7 para el combo**: envolver el método cambia el FS más de un 5 %
  respecto al ordinario, y los tres procedimientos dan tres números
  distintos; B̄ y "sin descenso rápido" devuelven el método intacto.
- **Interfaz**: round-trip de las dos formas de envolvente por el diálogo,
  campos deshabilitados —no ocultos— en un material drenante, y las
  etiquetas siguiendo la forma elegida.

Suite completa en verde.
