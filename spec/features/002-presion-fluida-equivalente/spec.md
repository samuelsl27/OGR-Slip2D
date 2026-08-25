# Muro de contención por presión fluida equivalente (EFP)

## Qué hace

Añade un tipo de soporte cuya capacidad se define por un **perfil de presión
sobre la altura del muro** — uniforme, triangular, trapecial o dado por una
tabla — que se **integra desde la coronación hasta el punto donde la superficie
de rotura corta el muro** para obtener la fuerza que el muro aporta.

## Por qué

Un muro de contención se dimensiona con un empuje que el proyectista recibe
como *presión fluida equivalente*: tantos kN por metro cúbico, que multiplicados
por la altura dan la presión en el pie. Hoy, para meter ese empuje en OGR
Slip2D, hay que integrarlo a mano y colocarlo como una fuerza puntual — y el
resultado deja de depender de dónde corte la superficie, que es justo lo que
distingue un muro de un ancla.

Es el hueco **D28** del banco de verificación (problema 110).

## Criterios de aceptación

- [ ] `force_at(L, L)` del perfil triangular de 5 ft con 125 psf en el pie vale
      **312,5**, el valor publicado, con error relativo < 1e-12
- [ ] `force_at(L, L)` del perfil trapecial con EFP = 25, *repartido sobre* 60 %
      y L = 10 vale **2000**, el valor publicado, con error relativo < 1e-12
- [ ] El mismo 2000 sale por el perfil **personalizado** definido con la tabla
      equivalente, y el mismo 312,5 sale del 110 por sus **dos** construcciones
      (tabla relativa y triangular con EFP = 25 pcf)
- [ ] El perfil trapecial reproduce las cotas de la figura acotada de la
      referencia: rampas de 0,2H, plano de 0,6H, presión EFP·H en el plano, cero
      en los dos extremos
- [ ] El diagrama de fuerza es cero en la coronación, monótono creciente hacia
      el pie, de derivada continua, e **invariante al partir el paso de muestreo**
- [ ] Un muro EFP de integral P da **bit a bit** el mismo factor de seguridad que
      un `EndAnchored` de capacidad P con la misma geometría, orientación y
      aplicación, **en los nueve métodos**
- [ ] Con φ' = 0 sobre un círculo, el factor coincide con la forma cerrada
      `F_act = Σc'l / (ΣW·arm − T_S)` y `F_pas = (Σc'l + T_S)/ΣW·arm`
- [ ] El punto de aplicación (corte / centroide) **mueve** el factor en Ordinary,
      Bishop, Spencer y GLE, y se comprueba que **no puede** moverlo en los otros
      cinco, que no tienen ecuación de momentos
- [ ] `LoadOrientation.HORIZONTAL` en una carga distribuida deja de ser inerte:
      mueve el factor
- [ ] Cada parámetro del tipo mueve la fuerza (regla 7)
- [ ] El tipo aparece en *Properties → Define Support…* y las cuatro formas de
      perfil cambian los campos visibles del diálogo
- [ ] Todo texto nuevo tiene traducción española
- [ ] Los seis modelos del banco con carga distribuida (9, 25, 26, 37, 60, 107)
      no se mueven **un dígito**
- [ ] Suite completa en verde, sin argumentos

## Validación numérica

Contra la **documentación y el manual de verificación de la referencia**, que
publican cuatro cosas comprobables y no una:

1. **312,5** — área del perfil triangular del problema 110 (5 × 125 / 2).
2. **2000** — área del trapecio del ejemplo trabajado de la página de ayuda
   (EFP = 25, repartido sobre 60 %, muro de 10: (10 + 6)/2 × 250).
3. **Las cotas del perfil trapecial**, acotadas en la figura de la ayuda:
   0,2H / 0,6H / 0,2H con EFP·H en la parte plana. Hacen falta porque **un área
   no fija una forma** y la feature vive de la integral *parcial*.
4. **Spencer 2,566** — publicado en la figura 110.3 del manual, en los dos
   paneles. Exige reconstruir una geometría que el manual no rotula: se
   digitaliza contra los ejes graduados y **decide el residuo del ajuste**; por
   encima de 1 px se declara no recuperable y no se usa.

Y dos identidades analíticas que no dependen de ninguna referencia:

5. **Equivalencia entre tipos de soporte**: lo único que distingue un muro EFP de
   un `EndAnchored` de la misma capacidad es `force_at`, así que con la misma
   geometría deben dar el mismo número **bit a bit** en los nueve métodos. El
   valor de referencia lo produce un tipo ya validado contra los problemas 48 y
   85 — no es una instantánea de lo que este código imprime hoy.
6. **Forma cerrada con φ' = 0** sobre círculo, la que ya usa
   `tests/test_support_active_passive_v1115.py`.

**Identidad descartada, y por qué.** «Un muro EFP de integral P equivale a una
carga lineal horizontal de magnitud P en el mismo punto» **es falsa**: un soporte
se descompone en T_S sobre la base y T_N normal, y una carga horizontal entra por
otro canal. Coinciden en Ordinary circular, en la rama de fuerza de Spencer/GLE y
en los tres métodos de marcha, pero **no** en Bishop —que suma `T_N·tanφ'` al
numerador— ni en los dos Janbu —que difieren en un factor `cos α`— ni en ninguna
superficie no circular. Se comprobó antes de escribirla como criterio.

## Fuera de alcance

- **El dibujo del diagrama de fuerza del soporte** en la ventana de
  interpretación. El valor publicado se comprueba llamando a `force_at`; dibujarlo
  es una feature de presentación con su propia acción de menú.
- **Corregir el desacuerdo entre canales** descrito arriba: se **mide** y se
  publica el número método a método, y se decide después con el dato delante.
- Los cuatro defectos encontrados por el camino (parámetros de soporte que se
  pierden al recargar, `shear_capacity` no consumido, TRIANGULAR y TRAPEZOIDAL
  indistinguibles, `creates_excess_pore_pressure` que no llega al constructor):
  se documentan con evidencia, no se arreglan aquí.
- El **patrón** de soportes para este tipo: una fila de N muros sumaría N veces
  la misma presión, así que se rechaza con su motivo en vez de dar un número.
