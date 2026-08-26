# Ancla helicoidal

## Qué hace

Añade el **noveno tipo de soporte**: un fuste con placas helicoidales soldadas
cuya capacidad **no la escribe el usuario** sino que se deduce del terreno que
lo rodea. Siete capacidades compiten en cada punto de la barra —tres de
arrancamiento, tres de descabezamiento y la del tirante— y la fuerza aplicada es
la menor de las tres familias.

Con él entran dos cosas más que el tipo necesitaba y no existían: la **capacidad
a cortante conectada al motor** —declarada por tres tipos desde v0.1.14, editable,
serializada y leída por nadie— y el **diagrama de fuerza del soporte** en
Interpret, que es lo único que permite ver *qué modo manda*.

## Por qué

Ninguno de los ocho tipos de OGR es un ancla helicoidal, y ninguno se le parece:
lo propio de este es que la capacidad **escalona** al pasar la superficie de
rotura por cada placa, porque una placa está o en el terreno anclado o en la
masa móvil y los dos lados se cuentan con ecuaciones distintas.

Con `UserDefined` se puede tabular cualquier diagrama fuerza-distancia, este
incluido. Pero eso comprobaría la interpolación de `UserDefined`, no el modelo
de ancla helicoidal, y el diagrama habría que calcularlo fuera.

Es el hueco **D29** del banco de verificación (problema 111).

## Criterios de aceptación

- [ ] `N_q = e^{π·tanφ}·tan²(45+φ/2)` y `N_c = (N_q−1)·cotφ` reproducen los
      valores publicados 33,2961 y 46,1236 a φ = 35°, con error < 5e-5
- [ ] `N_c → 2+π` (Prandtl 1921) cuando φ → 0, **por continuidad y sin umbral**:
      la diferencia dividida por φ se estabiliza en una constante durante diez
      décadas, de 1e-2 a 1e-12
- [ ] `N_q(0) = 1`, y las dos factores crecen con φ
- [ ] Un ángulo de rozamiento ≥ 90° se **rechaza**, no se recorta
- [ ] El área proyectada equivalente reproduce el 0,023562 m² publicado, y un
      fuste tan ancho como la hélice deja área **exactamente nula**
- [ ] Las **77 celdas** de la Tabla 111.1 —once posiciones por siete
      capacidades— se reproducen con error < 1e-3 kN/m
- [ ] Las tres filas donde una placa cae **exactamente** sobre la superficie
      fijan el convenio: no cuenta en ninguno de los dos lados
- [ ] El **diagrama publicado cada 0,1 m** se reproduce, incluidos los dos
      cambios de modo que ninguna fila de la tabla cubre (descabezamiento →
      tirante en 3,102 m; tirante → arrancamiento en 3,266 m)
- [ ] El **modo que manda** coincide con el color publicado en cada tramo
- [ ] Con **una sola hélice**, corte cilíndrico ≡ hundimiento individual, dígito
      a dígito
- [ ] **Ninguna placa más allá del corte ⇒ fuerza nula**, por grande que sea el
      tirante
- [ ] Sin placa en la masa móvil, las tres capacidades de descabezamiento valen
      la capacidad de la cabeza
- [ ] `force_at ≡ max(0, min(capacity_modes))` para **los nueve tipos**
- [ ] `c + σ'·tanφ ≡ τ(σ')` para los modelos constitutivos, dentro de 1e-9
      relativo: la linearización es una tangente y por eso la elección de dónde
      sale τ no era una elección
- [ ] La fuerza aplicada en (11 · 7,5) del problema 111 vale **73,5309 kN/m** a
      través del motor entero, con error relativo < 1e-4
- [ ] Con `shear_capacity = 0` el resultado es **idéntico bit a bit** al de
      v0.1.123 en los nueve métodos; con cortante > 0 se mueve en los nueve
- [ ] Con orientación paralela al soporte la resultante es **exactamente**
      `hypot(axil, cortante)`
- [ ] Cada parámetro del ancla mueve el diagrama, y los dos que sólo pueden
      moverlo donde gana un modo profundo lo dicen
- [ ] `helix_spacing` **no puede** mover el número con una sola hélice, y el
      diálogo lo deshabilita
- [ ] La acción del diagrama es **alcanzable desde la barra de menús** de
      Interpret, y la ventana es **no modal**
- [ ] El tipo sobrevive a guardar y reabrir, con el número de hélices entero

## Fuera de alcance

- **Capacidad a compresión.** La referencia la ofrece —el cálculo de tracción
  con la capacidad de compresión sustituida y la cabeza a cero—, pero OGR no
  tiene noción de un soporte comprimido: no hay de dónde leer el signo.
  Declarar el parámetro sería declarar un ajuste que no puede mover el número.
- **Los coeficientes `K` y `α`** del método clásico de corte cilíndrico
  (Mitsch y Clemence 1985 para arenas, Mooney y otros 1985 para arcillas). La
  formulación los fija en 1 y lo declara; no hay ningún número publicado contra
  el que validarlos.
- **`N_c = 9` para placas profundas en arcilla**, que es lo que usa la
  literatura de anclas. Se implementa la forma de Prandtl con el factor de
  forma 1,3 de Terzaghi porque es con la que se produjeron los números
  publicados.
