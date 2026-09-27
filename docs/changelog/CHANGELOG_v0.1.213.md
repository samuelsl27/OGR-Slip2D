# OGR Slip2D v0.1.213

Cabeza del paquete P4 del banco de verificación. Dos cambios de motor.

- **D81 — Bishop publica sus columnas por dovela en toda superficie, no solo en
  el círculo.** Además, la normal publicada conserva el signo de m_alpha, por
  decisión de la propietaria.
  - Afectaba a 32 superficies archivadas del banco, no a las tres de la ficha.
  - Con desembalse, Bishop sobre cualquier superficie no circular salía inválido
    siempre desde v0.1.108.
  - **No mueve ningún factor:** 0 de 336 superficies y 0 de 39 241 en las
    búsquedas de desembalse.
- **D84 — una envolvente curva se lee en la tensión que resuelve cada método,
  iterada al punto fijo, y no en la estimación de Fellenius.** Las dovelas que
  entran sin resistencia se declaran.
  - La ficha pedía un cierre documental porque «relinealizar empeora el problema
    40». Esa medida comparaba un resultado a 100 dovelas con un valor publicado
    para 5.
  - Lo que decidió fue una identidad: con el convenio viejo, la resistencia que
    usaba el solver no era la de la envolvente en su propia solución (+2 % en el
    40, −21 % en el 41).
  - **Mueve** solo las superficies con curva de potencia (11 de 336). El 40 pasa
    de +3,17 % a +0,52 % del valor publicado, y el 41 de −22,8 / −26,2 % a
    +4,9 / +2,2 %.
  - Mohr-Coulomb y los demás modelos lineales quedan bit a bit iguales.

Lo que cambia en el banco de verificación (`_tools/`, `_auditoria/`, fichas)
está fuera de git. D38, la tercera ficha de la tanda, es solo de banco y se
documenta en esta misma versión en un commit posterior.

---

## 0. Lo que estaba mal en el encargo de D81

### No eran tres modelos: eran 32 superficies

La ficha hablaba de los problemas 22, 45 y 57. El censo de las superficies
archivadas del banco (`_tools/censo_d81_columnas.py`, 336 superficies de Bishop y
de los dos Janbu) encontró **32 de Bishop sin columnas**, repartidas en unos 27
problemas. Son todas las no circulares: Path Search, Block, capa débil y
compuestas. En todas ellas el banco publicaba `sigma_n_max = None` para Bishop.

### El defecto no era de las compuestas: era de todo lo que no es un círculo

`BishopSimplified.compute_fos` despacha por `isinstance(surface, SlipCircle)`, y
`CompositeSurface` no es `SlipCircle` a propósito, así que va a la rama general.
Lo mismo les pasa a una poligonal y a una capa débil. Con desembalse
multietapa, desde v0.1.108 `rapid_drawdown._stage1_state` rechaza la columna
vacía: **Bishop con desembalse sobre cualquier superficie no circular salía
inválido siempre** (`drawdown_not_applicable`, −111 en la exportación). Entre
v0.1.92, cuando nació la rama general, y v0.1.107 no fallaba: repetía la etapa
1 en silencio.

### La comprobación que pedía la ficha no demostraba nada

La ficha pedía comprobar, antes de publicar la N, que cerrara el equilibrio
vertical de cada dovela sobre los tramos rectos. Ese equilibrio se cumple
**por construcción** para la fórmula que rellena la columna, sobre cualquier
superficie: es de donde sale la fórmula. Una N equivocada en un tramo recto
pasaría igual.

Lo que sí discrimina es el **balance de momentos del propio Bishop** respecto de
su eje, con el término Σ N·f de Fredlund y Krahn (1977), alimentado con las
columnas **publicadas**. Sobre dos poligonales del talud seco de v1107 cierra a
2·10⁻¹⁴. Con N = W·cos α en su lugar se desvía un 7,7 % y un 8,5 %.

Sobre la compuesta de la ficha (la 45.2) esa prueba **no ve nada**:

- el tramo recto es el suelo plano, donde α = 0 y la N de Bishop es exactamente
  W;
- en el arco, la normal de cada cuerda pasa por el eje.

Cualquier N da el mismo balance: con W·cos α coincidía a 13 cifras.

Con la curva de potencia tampoco cierra, y se queda en −4,5·10⁻⁴. La resistencia
publicada es la envolvente releída en la σ′ convergida, y el solver resistió con
la envolvente linealizada en la estimación de Fellenius. Eso es el convenio de
D84, no un defecto de la columna.

## 1. D81 — las columnas de la rama general y el signo de m_alpha (motor)

### El arreglo

- `_general_moment_fos` publica `base_normal_force`, `base_shear_force` y
  `base_shear_strength` con `base_forces_no_interslice_shear`, la función de la
  rama circular y de los dos Janbu, evaluada en el F devuelto. No se usa la N
  que el bucle acaba de emplear: es la misma fuerza (el equilibrio vertical de
  la dovela sin cortante entre dovelas) salvo en dos cosas.
  - La carga del soporte: el bucle la lleva y la columna no. Es la limitación
    conocida que comparten las cuatro, ficha D196, y no se toca aquí.
  - El F: el bucle usa el que entró en la última pasada.
- `base_forces_no_interslice_shear` divide por m_alpha **con signo** (decisión
  de la propietaria, 2026-09-27). Dividía por `max(abs(m_alpha), 1e-6)`, desde al
  menos v0.1.107 y sin razón escrita. En una dovela con m_alpha < 0 eso
  publicaba la normal con el signo opuesto a tres sitios:
  - la del equilibrio vertical;
  - la que reconstruye el chequeo −120;
  - la que la rama general mete en su propio balance.

  La etapa 1 del desembalse lee esa columna.
- El docstring de `moment_terms` decía que Bishop no pasa `sup`; lo pasa desde
  v0.1.137. Se corrige, y se conserva la frase del Ordinario, que sigue sin
  pasarlo.

### Por qué no mueve la admisibilidad

El chequeo −120 **no lee** `base_normal_force`: para Bishop y Janbu reconstruye
la normal (`checks.base_effective_stresses`). Rellenar la columna no puede
mover ni un veredicto ni un mínimo de búsqueda.

### Lo que mueve en el banco (medido, lado A = 0.1.212 extraído con `git archive`)

- **Superficies archivadas** (336, la misma población en los dos lados):
  - **0 factores ni validez movidos**;
  - las 32 sin columnas pasan a tenerlas, y ningún σ′ cambia fuera de ellas;
  - **0 superficies con alguna dovela con m_alpha < 0**.
- **Búsquedas de desembalse** (095–098, 100 y 101; Bishop y Janbu, que son los
  métodos que leen esa columna): 9 búsquedas y 39 241 superficies.
  - **0 mínimos movidos y 0 superficies distintas**;
  - 0 pasadas con m_alpha < 0 en unas 170 000.

  El cambio de signo no toca ningún número del banco.
- **Casos re-corridos con los dos árboles** (022 ×2, 040, 041 no circular,
  044 ×3, 045 ×3, 057 ×2 y 061 ×2; 14 archivos):
  - lo único distinto es el `sigma_n_max` de Bishop sobre superficie no circular,
    que pasa de None a número;
  - por ejemplo, 045: 84,7541; 057 compuesto: 2905,3393 en la búsqueda y
    2906,2685 en la superficie publicada; 041: 276,057.

### Una trampa del banco, no del motor

El 022 y el 040 están corridos con `--solo-publicado` (sin búsqueda). Re-correrlos
sin esa opción les añade búsquedas enteras. El A/B se hizo igual en los dos
lados, y después los dos archivos vivos se volvieron a correr con
`--solo-publicado`.

### Test nuevo

`tests/test_bishop_general_base_forces_v1213.py`, 14 casos:

- las columnas sobre la compuesta de la ficha y sobre una poligonal, y los nueve
  métodos sobre las dos;
- el equilibrio vertical, declarado tautológico;
- el balance de momentos y su control;
- el desembalse sobre compuesta y sobre poligonal;
- la poligonal inscrita que sigue al arco validado de Pilarcitos: etapa 1 a 10⁻⁴
  y factor a 0,5 %;
- el signo de m_alpha sobre una salida de pie empinada;
- dos controles.

**Contra 0.1.212 fallan 11 de 14**, todos por comportamiento. En la salida de pie
la función vieja da +78,53 kPa donde el chequeo −120 da −78,53. En la primera
versión, dos casos pasaban **en vacío** en 0.1.212: `zip` sobre una columna
vacía no itera. Ahora comprueban la longitud primero.

Una cosa que la poligonal inscrita enseñó sobre el propio arco: con 200 y 400
dovelas la poligonal queda a +0,11 % y −0,05 % del círculo en el desembalse. Es
el **arco** el que se mueve (su etapa 2 cambia un 0,18 % entre 200 y 400
dovelas), no la poligonal, que se mantiene a 10⁻⁴.

## 2. D84 — la envolvente curva se lee donde el método resuelve (motor)

### Lo que pedía la ficha y lo que se hizo

La ficha pedía dos cosas.

- **Declarar las dovelas que entran sin resistencia.** Hecho en los nueve métodos,
  no solo en Bishop y Janbu. Spencer, GLE, Corps 1, Corps 2 y Lowe-Karafiath
  linealizaban en el mismo punto de Fellenius (`interslice.py`,
  `modified_swedish.py`), y el Ordinario en su propia N.
- **Un cierre documental**, porque «la corrección evidente empeora el problema 40».
  Eso resultó ser una medida mal leída, y por eso no se cerró documental.

### El argumento viejo era una medida equivocada

El enunciado del 40 (Perry 1993) fija **5 dovelas**, y su 0,944 es el valor de la
referencia a esas 5. La ficha comparaba el resultado de OGR a **100** dovelas con
ese número.

| 40, Janbu simplificado | Fellenius | σ′ propia | contra 0,944 | contra 0,98 (Perry) |
|---|---|---|---|---|
| 5 dovelas (el enunciado) | 0,97388 | 0,94889 | +3,17 % / **+0,52 %** | **−0,62 %** / −3,17 % |
| 100 dovelas | 0,95454 | 0,92947 | — | — |

Las dos referencias externas se contradicen. El 0,98 de Perry sale de un
artículo que no se ha podido leer (CGJ y Wiley, de pago), y no se sabe en qué
punto lee su envolvente.

### Lo que decidió: una identidad, no un ajuste

Cada dovela resiste con la **recta tangente** a la envolvente en el punto donde se
linealiza, y el método la aplica a la σ′ que **él mismo** resuelve. Con una
envolvente cóncava, la tangente tomada en otro punto queda **por encima** de la
curva, y la tomada en un cero recortado, sobre una curva que pasa por el origen,
es **cero**. Medida de la resistencia que usó el solver frente a la de la
envolvente en la σ′ de su propia solución:

| | Dovela peor | Suma |
|---|---|---|
| 40, Bishop / Janbu / Spencer | +11 / +10 / +6 % | **+2,2 / +2,0 / +1,0 %** |
| 41, Bishop / Janbu / Spencer | −100 % (4 dovelas) | **−21 / −21 / −15 %** |

Es decir, el método **no resolvía el equilibrio límite con la envolvente del
material**. Solo en el punto fijo (linealizar en la σ′ que resuelve y repetir
hasta que no cambie) la resistencia usada es la de la envolvente. Es también lo
que describe la documentación pública de otro programa (la tangente en la normal
de la base de cada dovela, con la ordinaria como primera iteración).

De las tres opciones medidas se adoptó esa. La de linealizar solo donde Fellenius
sale negativa arreglaba el síntoma del 41 y dejaba la sobreestimación del resto.

### El arreglo

- **`methods.base.self_consistent_envelope`**, un decorador sobre el
  `compute_fos` de Bishop, Janbu (Corrected hereda), Spencer, GLE y la familia de
  inclinación prescrita.
  - Resuelve una vez.
  - Si alguna dovela tiene una envolvente cuya tangente depende de σ′ (prueba de
    dos tensiones, 5 y 500 kPa), impone como punto de linealización la σ′ propia
    de la solución (`checks.base_effective_stresses`, la de cada método desde
    D172, soporte incluido) y vuelve a resolver hasta que las dos coinciden a
    10⁻⁶.
  - Tiene un tope de 50 pasadas. Si no converge, la superficie queda **no
    convergida** con su razón (`envelope_not_converged`, −111), en vez de
    publicar un factor que no es el de la envolvente.
  - Publica `envelope_stress`, `envelope_passes` y `envelope_converged`.
- **El Ordinario no entra**: su normal no depende de c ni de φ, así que ya
  linealiza en el punto fijo.
- **Los chequeos −120 y m-alpha leen `envelope_stress`**: juzgan donde leyó el
  solver, como D172 hizo con la carga del soporte. La línea de empuje de la
  interpretación también lo lee.
- **Interruptor `ENVELOPE_AT_OWN_STRESS`**, añadido a la tabla `INTERRUPTORES` del
  banco.
- **Mohr-Coulomb y los demás modelos lineales no entran en el bucle**, y quedan
  bit a bit iguales, por construcción y medido.
- **La nota de resistencia nula cambia de sentido.** Con el punto fijo, una dovela
  marcada es una base **a tracción en la propia solución**. El 41 ya no marca
  ninguna. El mismo 41 a ru = 0,8 con Spencer marca las cuatro dovelas de
  cabecera, a −1,6 a −12,2 kPa.

### Lo que mueve (medido; lado A = el convenio de Fellenius en el mismo árbol)

- **Superficies archivadas del banco**: 11 de 336 (Bishop y Janbu), todas de
  problemas con curva de potencia (40, 41, 44, 45 y 61). Las 325 restantes quedan
  bit a bit iguales.
- **Comparativa**: 550 filas iguales de 559.
  - **Mejoran de estado:**
    - 40 Janbu: de +3,17 % REVISAR a **+0,52 % OK**;
    - 41 Bishop: de −22,79 % DISCREPANCIA a **+4,85 %** REVISAR;
    - 41 Janbu: de −26,21 % DISCREPANCIA a **+2,22 %** REVISAR.
  - **Empeora de estado:** 44 Janbu con curva de potencia, de −0,98 % OK a −1,18 %
    REVISAR.
  - **Se mueven sin cambiar de estado:**
    - empeoran 44 Spencer (−1,03 → −1,06 %), 45 Spencer (−0,48 → −0,49 %),
      61 Janbu (−1,40 → −1,74 %) y 61 Spencer (−3,17 → −3,54 %);
    - mejora 45 Janbu (+0,03 → −0,02 %).
- **Búsqueda Path del 41 frente a sus referencias externas** (Charles y Soares
  1984: 1,66; Baker 2003: 1,60 Janbu y 1,56 por programación dinámica):
  - Bishop pasa de 1,4805 a 1,7615;
  - Janbu pasa de 1,3190 a 1,6519.
- **Coste**: de 3 a 5 pasadas por superficie, solo con envolventes curvas. La
  búsqueda del 41, en serie, tarda 146 s en lugar de 60.
- **Limitación conocida, que no aparece en el banco**: una superficie cuyas
  dovelas salgan todas sin resistencia en la estimación de Fellenius no puede
  arrancar el punto fijo. La primera pasada ya no tiene factor, igual que antes.

### Tests

- **`test_envelope_own_stress_v1213.py`** (11 casos):
  - la autoconsistencia en ocho métodos y su control;
  - la identidad de momentos de D81 con curva de potencia, que cierra a 1,1·10⁻¹²
    (con Fellenius, −4,5·10⁻⁴);
  - el 40 dentro del 1 % del 0,944;
  - la regla 7 en los dos sentidos;
  - los chequeos que leen `envelope_stress`;
  - la convergencia y el caso no convergido.
- **`test_zero_strength_slices_v1213.py`** (16 casos):
  - la identidad cos²α < ru con el interruptor apagado, en los nueve métodos;
  - con el interruptor encendido, el 41 sin marcas y la base a tracción marcada;
  - la nota en `run_analysis` y en la API.
- **Contra 0.1.212 fallan 22 de 27**, por comportamiento:
  - el hueco de resistencia del 40 da 11,25 % en una dovela;
  - el 40 da 0,97389;
  - el interruptor no mueve nada.

  Pasan los dos controles de Fellenius, el de la envolvente lineal y dos guardas.
- **Tres archivos existentes** comprobaban que los chequeos linealizan en la
  estimación de Fellenius (D113 con agua embalsada, D172 con soporte, D167 con
  kv), y fallaron 11 casos. **Los 11 codificaban el convenio viejo**; ninguno era
  una regresión.
  - Sus resultados se construyen ahora con el interruptor apagado, con la razón
    escrita en cada archivo: esa estimación sigue siendo la primera pasada y el
    camino apagado.
  - La lectura de la σ′ del solver la fija el test nuevo.
- **Selección de 70 archivos: 1229 de 1229**, `test_slide_validation_*` incluidos.

## 3. Lo que se reporta y NO se corrige (regla 6)

- **D204 — el retroanálisis (`back_analysis.py`) sigue linealizando en la
  estimación de Fellenius.** Es otro planteamiento (el F objetivo es un dato), y
  llevarle el punto fijo es una decisión propia, no un arrastre de D84.
- **D205 — la tabla de dovelas del informe PDF rotula «Base σ [kPa]» y «Shear
  str. [kPa]», pero imprime las FUERZAS en kN/m** (`report_generator.py`). Es
  anterior a esta versión, y D81 lo extiende a Bishop no circular porque ahora
  tiene columnas.
- **La etapa 2 del desembalse en el arco se mueve con el número de dovelas** (un
  0,18 % entre 200 y 400). Lo enseñó la poligonal inscrita del test de D81, que
  se mantiene a 10⁻⁴. Solo medido.

## 4. Verificación

- Suite entera: **4721 de 4721**.
- Tests nuevos:
  - `test_bishop_general_base_forces_v1213.py`: 14 casos, 11 fallan contra
    0.1.212;
  - `test_envelope_own_stress_v1213.py` y `test_zero_strength_slices_v1213.py`:
    27 casos, 22 fallan contra 0.1.212, todos por comportamiento.

  Medido copiándolos a un árbol de 87127cb extraído con `git archive`.
- Banco, lado A 0.1.212 contra lado B 0.1.213:
  - censo de las 336 superficies archivadas de Bishop y Janbu;
  - las 9 búsquedas de desembalse de 095–101;
  - los casos re-corridos 022, 040, 041, 044, 045, 057 y 061;
  - la comparativa entera: 550 de 559 filas iguales, y las 9 que se mueven son
    todas de curva de potencia.
- Cierres del banco `d81()` y `d84()`: CUBIERTO POR TEST con este árbol, y NO SE
  SOSTIENE contra 0.1.212, por comportamiento.
