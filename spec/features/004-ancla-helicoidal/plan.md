# Plan — ancla helicoidal (D29)

## Fuentes

| Pieza | Fuente |
|---|---|
| `N_q = e^{π tanφ} tan²(45+φ/2)` | Prandtl (1921), Reissner (1924); forma profunda de Meyerhof (1976), usada para hélices por Perko (2009) |
| `N_c = (N_q−1) cotφ`, límite 2+π | Prandtl (1921) |
| `A·(1,3·c·N_c + q'·N_q)` | **Terzaghi (1943)**, zapata **circular**, sin el término `N_γ` |
| Hundimiento individual (suma sobre placas) | Perko (2009) |
| Corte cilíndrico | Mitsch y Clemence (1985) para arenas; Mooney, Adamczak y Clemence (1985) para limos y arcillas; Perko (2009) |
| Rotura somera | Perko (2009) |
| Reparto en modos a lo largo de la barra | documentación de la referencia, anclada por su cálculo a mano publicado |

## Módulos

`ogr_core/support/helical_anchor.py` — **nuevo**. Las funciones puras primero,
sin proyecto y sin geometría, para poder contrastarlas con su fuente aisladas:
`bearing_factors`, `equivalent_projected_area`, `plate_bearing`,
`effective_spacing`, `helix_distances`, `pullout_capacities`,
`stripping_capacities`. Debajo, el tipo `HelicalAnchor`.

**Sin umbral que calibrar.** `N_q − 1` cancela catastróficamente cerca de φ = 0,
justo donde tiene que dividir una cotangente que crece. Tomando logaritmos
primero —`ln N_q = π·tanφ + 2[log1p(t) − log1p(−t)]`, `t = tan(φ/2)`— los dos
salen exactos a la última cifra para cualquier φ > 0, y el límite llega por
continuidad. El pilote de Ito y Matsui de v0.1.123 **sí** necesitó un umbral
medido; aquella cancelación es irreducible y ésta es removible.

## Cómo llega el estado del terreno

Dos mitades, y sólo una es por unidad de longitud:

- el **cilindro** es `πD·∫τ dl`, y eso es `BondProfile.integral` con
  `interface_tau` devolviendo la resistencia del suelo (`soil_shear_strength_at`,
  la ruta de D19). La integral es lo que hace que un fuste que atraviesa tres
  materiales cobre la resistencia de cada tramo;
- el **hundimiento** existe en las placas y en ningún punto intermedio. Se
  generaliza el muestreador con `station_distances` / `station_value`, evaluados
  en la misma pasada y con el mismo estado de tensiones, y viajan en
  `BondProfile.stations`. Así `force_at(d, L, bond)` **no cambia de firma** y la
  caché sigue siendo una, construida una vez por análisis.

`c` y `tanφ` salen de `equivalent_c_phi_at` porque N_c y N_q los necesitan por
separado. **Medido antes de decidir**: `_local_c_phi` construye una tangente
verdadera, así que `c + σ'·tanφ ≡ τ(σ')` para los diecisiete modelos
constitutivos (diferencia máxima 8,5e-13). La pregunta de qué fuente usar para
τ no era una bifurcación, y un test lo deja atado.

## Las dos ampliaciones

**El cortante llega al motor.** `shear_at` devuelve un SEGUNDO vector,
perpendicular al eje y opuesto al deslizamiento, sumado al axil en
`compute_support_effects`. La regla de qué perpendicular se extrae a
`_resisting_perpendicular` y la usan los dos sitios que la necesitan. Con
`shear_capacity = 0` —que es el valor por defecto de los cuatro tipos que lo
declaran— la suma vectorial devuelve el vector axil bit a bit.

**El diagrama de fuerza.** `capacity_modes` publica los modos con claves ASCII y
`force_at` pasa a ser su mínimo: una sola escritura de cada fórmula. La ventana
es no modal, tiene un desplegable de soportes y marca el corte con la superficie
crítica.

## Riesgos

- **El cortante toca el camino común de todos los soportes.** Por eso se hace
  primero y se afirma la identidad con cortante nulo antes de seguir.
- **`force_at` reescrito en tres tipos ya validados.** Atado con el test de
  identidad sobre los nueve tipos, y es lo que evita el riesgo mayor: dos
  escrituras de la misma fórmula.
- **La orientación por defecto.** La página del tipo no declara ninguna; la
  declara la tabla del modelo de verificación de la propia referencia. Elegida
  **antes** de medir ningún factor de seguridad, a propósito.
