# OGR Slip2D v0.1.222

Cierra las dos fichas que nacieron al cerrar D212 en 0.1.221. Las dos tocan
solo lo que enseña la interpretación: ningún factor de seguridad se mueve.

- **D221 — la línea de empuje queda en equilibrio de momentos.** Despejaba la
  altura de cada empuje con el signo de los momentos conocidos cambiado, así
  que ninguna dovela estaba en equilibrio de momentos. Ahora el signo es el
  que pide el equilibrio, y la línea se recorre desde los dos extremos libres
  hacia la dovela central.
- **D220 — Corps 2 y Lowe-Karafiath publican las razones entre dovelas con
  que resolvió su recursión.** La marcha de la interpretación reproduce ya sus
  normales, sin soporte y con él.

Hay un hallazgo nuevo, que se reporta y NO se corrige (regla 6):

- **D222**: Corps 2 y Lowe-Karafiath no son invariantes por simetría. El
  mismo talud reflejado da otro factor: −0,88 % y −0,10 % con 50 dovelas.

Sección 4.

Cambios en el banco: ninguno. El banco no compara fuerzas entre dovelas ni
líneas de empuje.

Lo que cambia en el banco de verificación (`_tools/`, `_auditoria/`, fichas)
está fuera de git.

---

## 0. Lo que se decidió

### D221: el signo, y desde los dos extremos

**El signo.** `known` es el momento antihorario, respecto del punto medio de
la base, de todo lo que actúa sobre la dovela salvo su empuje derecho: el
empuje izquierdo, el peso, el sismo, el agua y el soporte. La cara derecha
empuja la dovela con `(−E_R, −X_R)`, así que el equilibrio pide
`y_R = y_c + ((x_R − x_c)·X_R − known)/E_R`. El código sumaba `+known`.

**Por qué no basta el signo.** Con el signo bien, cada dovela queda en
equilibrio, pero una línea recorrida desde UN extremo arrastra hasta el otro
el desequilibrio de momentos de toda la masa:

- solo los métodos de equilibrio completo tienen la línea de empuje entre sus
  incógnitas (Spencer, Morgenstern-Price: DW&B 2014, Tabla 6.2);
- un método de fuerzas (los dos Corps, Lowe-Karafiath, Janbu) deja un
  desequilibrio de momentos de la masa;
- también deja uno, pequeño, la marcha de Spencer y GLE, porque no es su
  solver.

Cerca del extremo derecho, donde E → 0, ese desequilibrio dividido por E da
alturas absurdas: 2968 alturas de dovela en Corps 1, en el talud de
`test_support_normal_v1137`.

**El ancla externa** que pedía la ficha es la documentación de la referencia,
que describe así su línea de empuje:

- la calcula sumando momentos respecto del centro de la base de cada dovela;
- como su posición se conoce en la primera y en la última dovela, la recorre
  desde los dos extremos hacia la dovela central;
- la de la dovela central es el promedio de los dos recorridos.

Así queda implementado:

- el recorrido desde la derecha empieza en la base del extremo derecho, como
  el de la izquierda;
- cada dovela da la altura de su empuje IZQUIERDO con su equilibrio;
- los dos recorridos atraviesan la dovela central `m = n // 2`, y cada una de
  sus dos caras toma el promedio.

El equilibrio de una dovela es lineal en las alturas de sus dos caras. Por
eso la central queda en equilibrio, y sus dos vecinas llevan la mitad del
desequilibrio de la masa cada una, justo donde las fuerzas entre dovelas son
mayores.

El documento de la referencia apoya el peso en el punto medio de la base
(«pasa por el centro de la base»). OGR lo sigue poniendo en el centroide de
la dovela, que es lo exacto: el test escribe el centroide aparte.

**Bishop y el Ordinario.** Son métodos de momentos que suponen fuera las
fuerzas entre dovelas, y su marcha no cierra (26 % y 4 %). No tienen línea de
empuje: la referencia no la calcula para ellos, y la interpretación de OGR
tampoco la ofrece en su capa. El diagrama de cuerpo libre sí la usa, así que
había que decidir qué hacer:

- se recorren también desde los dos extremos, con la fuerza que la marcha deja
  en el extremo derecho puesta en la base;
- así su desequilibrio va al centro con el resto;
- desde un solo extremo, Bishop daba alturas de −4,6 a 12 dovelas (percentiles
  5 a 95); desde los dos, de −0,8 a 1,6;
- su diagrama de cuerpo libre queda en equilibrio de momentos igualmente.

Interruptor `postprocess.THRUST_LINE_BALANCED`: el signo y el recorrido desde
los dos extremos, juntos.

### D220: se publica lo que usa el solver

`_march` de la familia de inclinación prescrita:

- pone la resultante de la cara derecha de la dovela i con la θ_i de esa
  dovela;
- la cara izquierda de la i+1 recibe el mismo vector (`theta_prev`);
- así el contacto i+1 lleva `tan θ_i`.

`_boundary_ratios` publicaba en cada contacto interior `tan` del promedio de
las dos θ.

Se cambia la publicación, no el solver: lo que la marcha tiene que
reproducir es el estado del método. El espejo de la recursión (`orient`)
niega α y θ, pero conserva el orden de las dovelas, así que la regla es la
misma en los dos sentidos. El test lo comprueba con el talud y con su reflejo:
el original marcha con `orient = −1` y el reflejo con `+1`.

Con θ constante (Corps 1), `0,5·(θ + θ)` es θ exacto, y las razones no cambian
ni un bit.

Interruptor `methods.modified_swedish.BOUNDARY_RATIOS_AS_SOLVED`.

Si D222 cambia algún día dónde se evalúa θ, la publicación tiene que seguirla.
El test de D220 lo vigila: exige que la marcha reproduzca las normales.

## 1. Los cambios

- **`postprocess._march`**:
  - el signo de `known`;
  - guarda por dovela el momento de todo menos sus dos empujes (`other`);
  - llama a `_thrust_from_both_ends`, que hace el recorrido desde la derecha y
    el promedio en la central.
- **`modified_swedish._boundary_ratios`**: `[tan θ_0] + [tan θ_i]`.
- **Tests**:
  - nuevo, `test_interslice_thrust_v1222.py`;
  - cambia a propósito `test_interslice_support_v1221.test_the_line_of_thrust_takes_it`,
    con la razón escrita en él. La dovela 46 del clavo cae en la mitad
    derecha, así que su momento mueve ahora la altura de su empuje IZQUIERDO,
    y con signo (antes solo podía pedirse el tamaño). Las alturas a su derecha
    no se mueven ni un bit.
- La tabla `INTERRUPTORES` del banco pasa a 28, las mismas que el motor.

## 2. Lo medido

Talud de `test_support_normal_v1137`, sin soporte, 50 dovelas.

**La línea de empuje**, en fracción de la altura de cada dovela (percentiles
5, 50 y 95):

| Método | 0.1.221 (mediana) | 0.1.222 | y del extremo derecho en 0.1.221 |
|---|---|---|---|
| Spencer | 0,000 | 0,08 / 0,13 / 0,18 | −608 237 m |
| GLE | 0,000 | 0,04 / 0,12 / 0,23 | +163 210 m |
| Corps 1 | 0,000 | 0,09 / 0,13 / 0,17 | −267 679 m |
| Corps 2 | 0,006 | 0,19 / 0,42 / 0,54 | 10,09 m |
| Lowe-Karafiath | 0,001 | 0,10 / 0,14 / 0,19 | +4 476 200 m |

- En 0.1.221 la línea quedaba pegada a la base.
- En 0.1.222 los dos extremos libres están en la base, que en este talud está
  a y = 12 m.
- En 0.1.221 el extremo derecho era el residuo de cierre dividiendo un momento
  finito. En Corps 2 salía una cifra razonable solo porque su marcha no
  cerraba (D220).

**El equilibrio de momentos de cada dovela**, escrito aparte con el convenio
antihorario:

- las 48 dovelas que no son vecinas de la central, a menos de 10⁻⁹ de la
  escala, en los siete métodos probados;
- las vecinas 24 y 26, con la mitad del desequilibrio de la masa cada una.

Ese desequilibrio (kN·m/m):

| Spencer | GLE | Corps 1 | Corps 2 | L-K | Janbu | Bishop |
|---|---|---|---|---|---|---|
| 0,186 | 0,085 | −62,8 | −69,8 | 60,1 | 286,5 | 170,6 |

En Spencer y GLE es pequeño, como debe ser en un método de equilibrio
completo; en los de fuerzas no lo es.

**D220.** La marcha frente a las normales del método, en fracción de
`max(1, |N|)`:

- Corps 2: 5,95 → 1,4·10⁻¹⁵. El cierre, 2,2·10⁻² → 5,6·10⁻⁹. Con las razones
  viejas, el ajuste secante no encontraba horquilla.
- Lowe-Karafiath: 2,75 → 4·10⁻¹⁵. El ajuste secante cerraba ya a 10⁻⁹ con las
  razones viejas, reescalándolas, pero sin dar las normales. Sin el ajuste,
  2,79 y 2·10⁻³, que son las cifras de la ficha.
- Corps 1: igual.

## 3. Tests

**`test_interslice_thrust_v1222.py`, 12 casos**:

- el caso colineal, sobre siete dovelas hechas a mano: a través de una dovela
  sin rozamiento sobre base horizontal el empuje conserva su altura (estática:
  dos fuerzas en equilibrio son colineales). La línea vieja la reflejaba
  respecto de la base, 0,995 → −0,995;
- el equilibrio de momentos de cada dovela:
  - en siete métodos sobre el talud desnudo, en tres con el clavo activo y
    pasivo, y en tres bajo un estanque con sismo (kh 0,1, kv 0,05);
  - todas en equilibrio salvo las dos vecinas de la central, y esas dos con
    el mismo residuo;
  - la suma de los residuos es el momento de las fuerzas exteriores respecto
    del origen, que no depende de la línea: comprueba las cuentas del propio
    test;
- los dos extremos libres en la base;
- la familia reproduce sus normales, sin soporte, con el clavo activo y pasivo
  y reflejada (las dos orientaciones de la recursión);
- la regla 7 de los dos interruptores, y que ninguno mueve una fuerza.

**Contra 0.1.221 fallan 9 de 12, los 9 por comportamiento.** Pasan los dos
casos de regla 7 cuyo estado apagado es el comportamiento viejo, y el de que
ninguna fuerza se mueve.

## 4. Hallazgo que se reporta y NO se corrige: D222

- **Corps 2 y Lowe-Karafiath no son invariantes por simetría.**
  - El contacto entre dos dovelas toma la θ de la de su izquierda en el orden
    de índices, que siempre va de izquierda a derecha en x. En el modelo
    reflejado, el mismo contacto toma la θ de la otra dovela.
  - Medido con el talud y su reflejo respecto de x = 0:
    - Corps 2: 1,923682 frente a 1,906777 (−0,88 %) con 50 dovelas; −0,22 %
      con 200;
    - Lowe-Karafiath: 1,861010 frente a 1,859092 (−0,10 %); −0,026 % con 200;
    - Corps 1, Spencer, Janbu y Bishop coinciden a 10⁻¹⁵.
  - DW&B (2014, Tabla 6.1 y Fig. 6.14c) sitúan la inclinación en el contacto.
  - Mueve factores del banco, así que la decisión es de la propietaria:
    - evaluar θ en el contacto como promedio de sus dos dovelas;
    - o evaluarla con las pendientes del terreno y de la base en su x.

## 5. Caminos equivocados

- **Solo el signo.** Fue lo primero que se probó. Las dovelas interiores
  quedaban en equilibrio (residuos de 5·10⁻¹⁴), pero la última se llevaba el
  desequilibrio de toda la masa, y las alturas cerca del extremo derecho se
  disparaban: 2968 alturas de dovela en Corps 1, −272 en la siguiente. Lo que
  arregla eso es el recorrido desde los dos extremos, no una tolerancia.
- **Desde los dos extremos solo si la marcha cierra.** Una primera versión
  exigía un cierre relativo por debajo de 10⁻³ para tratar el extremo derecho
  como libre, y dejaba Bishop y el Ordinario recorridos desde la izquierda.
  - Así quedaban en equilibrio exacto, pero con alturas de −33 a 29 dovelas
    (Bishop) y de −167 a 150 (Ordinario), y el diagrama de cuerpo libre de
    esas dovelas se volvía ilegible.
  - Desde los dos extremos, con la fuerza del extremo derecho en la base, se
    quedan en −6 a 6 y en −2,5 a 1,9, y el umbral desaparece.
- **La ficha D220 decía 2,79 para Lowe-Karafiath.** Era la marcha sin el
  ajuste secante; `compute_interslice_state` da 2,75. Las dos son el mismo
  defecto.

## 6. Verificación

- Selección dirigida (marcha, familia prescrita, interpretación): 223 de 224
  antes de cambiar a propósito el test de D212; después, 42 de 42 en los tres
  archivos afectados.
- Suite entera: **4961 de 4961** (42 min 35 s, con el recorrido en seco del
  banco corriendo a la vez unos 16 min).
- Banco:
  - `d220()` y `d221()` cierran, y dan NO SE SOSTIENE contra 0.1.221;
  - el recorrido en seco de los 159 cierres no da ninguna bajada;
  - D220 y D221 quedan retiradas, con D222 abierta en P4, sin prompt largo;
  - auditorías a 0 ERROR (en el 02, los mismos 753 hallazgos que en
    0.1.221);
  - la tabla `INTERRUPTORES` pasa a 28.
- Falta por probar a mano: la capa de la línea de empuje y el diagrama de
  cuerpo libre en la ventana de interpretación. Ningún test los abre (el
  diagrama es un diálogo modal).
