# Pilote de Ito y Matsui

## Qué hace

Añade al pilote que ya existe un **modo de rotura** en el que la fuerza no la
escribe el usuario sino que **se deduce del espaciamiento**: la presión lateral
que el suelo en deformación plástica ejerce sobre una fila de pilotes, según Ito
y Matsui (1975), integrada desde el techo del pilote hasta el punto donde la
superficie de rotura lo corta.

## Por qué

`PileMicropile` aplica hoy una fuerza **constante** igual a
`pile_shear_strength / out_of_plane_spacing`: la resistencia estructural del
pilote dividida por la separación. Es el modo *Shear*, y es correcto — pero deja
fuera la pregunta que se hace de verdad al diseñar una fila de pilotes de
estabilización, que es **cuánta carga le llega al pilote según lo juntos que
estén**. Esa carga la fija el suelo, no el acero.

Sin el modelo, reproducir una tabla de factores frente a la separación exige
meter a mano la fuerza de cada fila, calculada fuera. Se estaría verificando la
aritmética de OGR contra un número ajeno, no la formulación.

Es el hueco **D26** del banco de verificación (problema 106).

## Criterios de aceptación

- [ ] Con **hueco igual a la separación** (`D₂ = D₁`, o sea diámetro nulo) la
      Ec. (13) se anula **término a término**: un pilote que no ocupa sitio no
      empuja nada. Error absoluto < 1e-9 sobre un barrido de c, φ y γz
- [ ] La Ec. (13) con `c = 0` reproduce la Ec. (14) del artículo (suelo sin
      cohesión), con error relativo < 1e-12
- [ ] La Ec. (13) **tiende** a la Ec. (23) cuando φ → 0, y la Ec. (23) coincide
      con su **re-derivación** desde las Ecs. (16), (19), (21) y (22)
- [ ] El conmutador de φ pequeño es **continuo**: los dos lados del umbral
      coinciden y el resultado no salta
- [ ] La transcripción coincide con la **segunda impresión** de la misma
      ecuación, la Ec. (10) de Cai y Ugai (2000), escrita con su agrupación `A`
- [ ] `d ≥ D₁` (pilotes que se tocan) se **rechaza con motivo**, no devuelve un
      infinito ni un número plausible
- [ ] **Puerta (a)**: el talud de Cai y Ugai **sin pilote** reproduce su Bishop
      **1,13** dentro del ±2 %
- [ ] **Puerta (b)**: con pilote, las relaciones separación/diámetro 2, 3, 4 y 6
      reproducen la **tendencia** de 1,54 / 1,37 / 1,31 / 1,25, con las **dos**
      orientaciones candidatas medidas y publicadas
- [ ] `failure_mode` mueve el número, y en modo *Shear* **no** lo mueve ni un bit
      respecto de 0.1.122
- [ ] `pile_diameter` mueve la fuerza (por `D₂ = D₁ − d`)
- [ ] `out_of_plane_spacing` la mueve por **dos** caminos a la vez —`D₁` dentro
      de la ecuación y el divisor de fuera— y se comprueba que los dos actúan
- [ ] `force_location` mueve el factor en Ordinary, Bishop, Spencer y GLE y
      **no puede** moverlo en los otros cinco
- [ ] Un pilote en modo *Shear* **no construye** perfil de muestreo
- [ ] Un `.ogr` anterior a esta versión carga en modo *Shear* y da el mismo
      número que hoy
- [ ] El modo aparece en *Properties → Define Support…* y cambia los campos
      habilitados del diálogo
- [ ] Todo texto nuevo tiene traducción española
- [ ] Suite completa en verde, **sin argumentos**

## Validación numérica

Contra **dos fuentes científicas externas**, no contra la ayuda de ningún
programa:

1. **Ito, T. y Matsui, T. (1975)**, «Methods to estimate lateral force acting on
   stabilizing piles», *Soils and Foundations* 15(4) 43-59. Ecs. **(13)**
   (suelo c–φ), **(14)** (c = 0) y **(23)** (φ = 0), con
   `Nφ = tan²(π/4 + φ/2)`, `D₁` la distancia entre centros de la fila y `D₂` el
   hueco entre pilotes.
2. **Cai, F. y Ugai, K. (2000)**, «Numerical analysis of the stability of a
   slope reinforced with piles», *Soils and Foundations* 40(1) 73-84. Su
   Ec. **(10)** es la (13) reescrita —segunda impresión independiente de la
   misma ecuación—; sus Ecs. **(8)** y **(9)** dicen cómo entra en el
   equilibrio, `M_P = (Q·R/D₁)·cos θ`; su **Fig. 2** acota la geometría y su
   **Tabla 1** publica las propiedades; su **Fig. 4** publica los factores.

Y tres identidades analíticas que no dependen de ninguna de las dos:

3. **Diámetro nulo ⇒ fuerza nula.** Exacta, y término a término.
4. **El límite φ → 0.** Los dos sumandos de orden `c·D₁/φ` se cancelan y el
   límite de la (13) **es** la (23).
5. **La linearización de la envolvente es la misma que usan los nueve métodos**
   (`BishopSimplified._local_c_phi`), atada con un test de identidad.

## Fuera de alcance

- **El modo EFW**, el tercero del pilote en la referencia. Ningún problema del
  banco lo valida, así que su única ancla sería la fórmula de la ayuda del
  programa de referencia, que no es fuente científica externa. Se anota como
  hueco con su evidencia.
- **Corregir la formulación**. Zhang y otros (2017), *J. Geotech. Geoenviron.
  Eng.* 143(9), sostienen que la solución de Ito y Matsui subestima la fuerza y
  que a espaciamientos cerrados supera el empuje pasivo. El ancla de este
  problema es Cai y Ugai, que usaron la original; sustituirla dejaría la
  validación sin nada contra qué contrastar. Se **cita**, no se cambia.
- **Recortar `q(z)` a cero** donde la ecuación la da negativa. Se integra tal
  cual y se avisa: recortar muestra a muestra cambiaría el número en silencio.
- **Proyectar la integral sobre la vertical** en un pilote inclinado. La teoría
  no dice qué hacer; se integra a lo largo del soporte y se avisa.
