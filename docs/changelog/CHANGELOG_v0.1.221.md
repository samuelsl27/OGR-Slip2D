# OGR Slip2D v0.1.221

Cuarta y última de las cuatro versiones que cierran lo que quedaba del
paquete P4 del banco de verificación:

- **D212 — la marcha de fuerzas entre dovelas de la interpretación lleva el
  soporte que aplicó el método.** Hasta ahora rehacía el equilibrio de cada
  dovela con las cargas del método (el agua, el sismo y su sentido, desde
  D173), pero sin ninguna fuerza de soporte. Sobre un talud reforzado
  enseñaba las fuerzas entre dovelas, la línea de empuje y el diagrama de
  cuerpo libre de un talud desnudo. Desde D196 (0.1.216), además, su N se
  separaba en cada dovela cruzada de la columna que publica el método: 6,686
  kN/m frente a 15,607 con Bishop.

Hay dos hallazgos nuevos, que se reportan y NO se corrigen (regla 6):

- **D220**: las razones entre dovelas que publican Corps 2 y Lowe-Karafiath
  no son las que usa su solver.
- **D221**: la línea de empuje tiene cambiado el signo de los momentos
  conocidos.

Sección 4.

Cambios en el banco: ninguno. El banco no compara fuerzas entre dovelas.

Lo que cambia en el banco de verificación (`_tools/`, `_auditoria/`, fichas)
está fuera de git.

---

## 0. Lo que se decidió

La ficha pedía decidir qué hace la marcha con la parte tangencial de un
soporte. La marcha aplica el vector que aplica el propio método:

- la parte NORMAL, entera, como carga cartesiana;
- la TANGENCIAL, movilizada a `t_active + t_passive/F`, a lo largo de la
  base y en el sentido que resiste el deslizamiento.

Es el mismo vector en todas las familias; se comprobó en el código antes de
escribirlo:

- **Bishop y Janbu** meten su componente vertical en el equilibrio vertical
  de cada dovela: `−f_y` es `support_vertical_load`, bit a bit.
- **Spencer y GLE** toman la normal como carga y la tangencial como el
  `t_mob` de `interslice.solve_branch`.
- **La familia de inclinación prescrita** hace lo mismo con la normal y suma
  la tangencial a su `k0`.

Cada método la moviliza con SU F:

- Bishop, con la de la última pasada;
- Janbu, con la sin corregir (el F0 de D211);
- Spencer y GLE, con la de la rama de fuerzas, que es la que resolvió el
  equilibrio por dovela;
- la familia prescrita y el Ordinario, con la suya.

El momento respecto del punto medio de la base:

- La parte tangencial actúa sobre la cuerda en el cruce, y ese punto medio
  está en la misma cuerda, así que su momento es nulo.
- La parte normal da `(x_app − x_c)·nf_v − (y_app − y_c)·nf_h`.
- Se suman dos pares:
  - el que dejan las partes normales cuando una dovela la cruzan dos o más
    soportes (`normal_couple`, D150);
  - el de un soporte cuya resultante actúa fuera de su cruce. Hasta ahora era
    un único escalar para toda la superficie (`SupportTerms.couple`); ahora
    también va por dovela (`slice_couple`), porque la línea de empuje de una
    dovela solo debe recibir los pares de sus soportes.

La marcha lee la resistencia donde la leyó el método, con la carga de soporte
de su propia estimación (`sigma_support_load`).

## 1. Los cambios

- **`support_integration.py`**:
  - `support_force_on_slice`, `support_forces`, `support_moments`;
  - `SupportTerms.slice_couple`.
- **Los nueve métodos** publican `details["support_force"]` (`[f_x, f_y]` por
  dovela) y `details["support_moment"]`:
  - Bishop (las dos ramas) y Janbu desde el mismo bucle y con la misma F que
    `sigma_support_load`: `X0Pass.support_force`;
  - Spencer, GLE, la familia prescrita y el Ordinario, en su salida.
  - Sin soporte, las dos claves valen `None`.
- **`postprocess._march`**:
  - suma la fuerza a los dos equilibrios de fuerzas de la dovela y el momento
    a su línea de empuje;
  - linealiza con `sigma_support_load`;
  - `InterSliceState` guarda lo aplicado;
  - interruptor `SUPPORT_IN_MARCH`; la tabla `INTERRUPTORES` del banco pasa a
    26.
- **El diagrama de cuerpo libre** dibuja el soporte («T (soporte)», con su
  `tr()`) sobre su línea de acción, en el punto de la base cuyo momento es el
  publicado.

## 2. Lo medido

Con el clavo a −15° de `test_support_normal_v1137` (50 dovelas; la 46 es la
cruzada), marcha sin el soporte → con él:

| Método | N46 de la marcha | Columna | Cierre relativo | Separación de sus normales |
|---|---|---|---|---|
| Bishop | 6,686 → 15,607 | 15,607 | (método de momentos) | 0,57 → 5·10⁻¹⁶ |
| Janbu (los dos) | 6,565 → 15,381 | 15,381 | 0,296 → 1,6·10⁻⁴ (sin clavo, 1,5·10⁻⁴) | 0,57 → 3·10⁻¹⁶ |
| Spencer | — | — | 0,238 → 6·10⁻⁹ | 0,75 → 0,095 (sin clavo, 0,175) |
| GLE | — | — | 0,302 → 3·10⁻⁹ | 0,79 → 0,014 (sin clavo, 0,013) |
| Corps 1 | — | — | 4·10⁻⁹ | 0,81 → 6·10⁻¹⁶ |

Todo con el clavo activo. Con el pasivo el cuadro es el mismo.

## 3. Tests

**`test_interslice_support_v1221.py`, 14 casos**:
- la marcha es la columna en Bishop y los dos Janbu, con clavo activo y
  pasivo;
- Janbu cierra su equilibrio horizontal a 10⁻⁹ con el solver ajustado;
- Corps 1 reproduce sus normales;
- Spencer y GLE quedan tan cerca de su solución como sin clavo;
- los dos equilibrios de fuerzas de la dovela cruzada, con el vector del clavo
  escrito aparte;
- el momento publicado es el del clavo, y la línea de empuje lo toma;
- lo que publica cada familia, y que `−f_y` es la carga de Bishop y Janbu bit
  a bit;
- la regla 7: apagado vuelve el 6,686; sin soporte, nada se mueve ni un bit.

**Contra 0.1.220 fallan 10 de 14:** 6 por comportamiento y 4 por las claves
nuevas. Pasan el guarda, el control del talud desnudo y los dos casos de la
regla 7, que en el árbol viejo son su comportamiento.

## 4. Hallazgos que se reportan y NO se corrigen

- **D220 — las razones de Corps 2 y de Lowe-Karafiath no son las de su
  solver.**
  - `modified_swedish._boundary_ratios` publica en cada contacto interior el
    `tan` del PROMEDIO de las θ de las dos dovelas. Pero su recursión pone la
    fuerza de la cara derecha de la dovela i con su propia θ_i.
  - Con θ constante (Corps 1) da igual. Con θ variable, la marcha con las
    razones publicadas no reproduce las normales del método ni sin soporte:
    se separa 5,95 (Corps 2) y 2,79 (Lowe-Karafiath) y cierra al 2·10⁻² y al
    2·10⁻³.
  - Con las razones del solver reproduce sus normales a 10⁻¹⁵ y cierra a
    6·10⁻⁹.
  - Solo afecta a lo que enseña la interpretación; ningún factor lo lee.
- **D221 — la línea de empuje tiene cambiado el signo de los momentos
  conocidos.**
  - `postprocess._march` despeja la altura de la fuerza de la cara derecha con
    `y_tR = y_c + ((x_R − x_c)·X_R + known)/E_R`. `known` son los momentos
    antihorarios del resto de fuerzas: la cara izquierda, el peso, el sismo y
    el agua. Como la fuerza de la cara derecha sobre la dovela es
    `(−E_R, −X_R)`, el equilibrio pide `− known`.
  - Con dos empujes horizontales iguales y ningún otro momento, la fórmula da
    `h_R = −h_L` en lugar de `h_R = h_L`, que es la condición de dos fuerzas
    colineales.
  - Medido sin clavo con Spencer: la línea queda en el 0–1,4 % de la altura de
    cada dovela, y el balance correcto la pone en el 9–17 %.
  - Cada dovela incumple su equilibrio de momentos por `2·known`: −1,498
    kN·m/m en la dovela 46 del clavo.
  - El único test que la miraba solo pedía que quedara «dentro de la dovela ±
    0,5 m».
  - El momento del soporte de D212 entra como un momento conocido más, así que
    quedará bien solo cuando se corrija el signo.

## 5. Caminos equivocados

- **El primer test del momento de la dovela cruzada no cerraba (−1,498).** No
  era el soporte: era D221. Resultó ser exactamente `2·known`, y un cálculo
  del balance desde el pie, con el convenio antihorario explícito, lo
  confirmó. El test comprueba ahora que el momento publicado es el del clavo
  y que la marcha lo suma, en magnitud.
- **Corps 1 con el clavo pasivo reproducía sus normales a 10⁻⁸ y no a
  10⁻¹⁵.** Es el ajuste secante de la marcha cerrando el residuo que deja la
  raíz del método; la tolerancia del test es la de la raíz.

## 6. Verificación

- Selección dirigida de 75 archivos (marcha, métodos, soportes,
  interpretación, i18n, chequeos, desembalse): 1314 de 1314.
- Suite entera: **4949 de 4949** (45 min, con el recorrido en seco del banco
  corriendo a la vez parte del tiempo).
- Banco:
  - `d212()` cierra, y da NO SE SOSTIENE contra 0.1.220;
  - D173, D172 y D167 siguen en pie;
  - el recorrido en seco de los 157 cierres no da ninguna bajada;
  - D212 queda retirada, con D220 y D221 abiertas en P4;
  - auditorías a 0 ERROR.
