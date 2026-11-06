# Sarma con dovelas no verticales (D357)

## Qué hace

Añade un décimo método de equilibrio límite: Sarma con dovelas no verticales, es decir, cuñas entre caras
inclinadas, con F por reducción de la resistencia hasta que la aceleración crítica Kc vale el kh aplicado. Y
las superficies no circulares del usuario, donde se le dan los ángulos y la c/φ de cada interfaz.

## Por qué

Hay mecanismos de cuñas que las dovelas verticales no representan, porque no transmiten el empuje de una cuña a
otra a través de una cara inclinada: escombreras sobre un suelo débil inclinado, núcleos de presa, roturas por
una veta.
- En el problema 4 del manual 03 del banco, Bishop da 3,77 donde el mecanismo de dos cuñas da 1,198. Por eso
  las filas del 4 están en NO COMPARABLE (D122) y la del 5 en «DISCREPANCIA de método» (D123).
- Kc es además la medida sísmica natural del método: «el talud aguanta 0,05 g».

## Fuentes (decisión de la propietaria, 2026-11-04)

Sarma (1979), *J. Geotech. Eng. Div.* ASCE 105(GT12), 1511–1524, **no se ha conseguido**. El PDF que llegó
con ese nombre es Sarma (1973), *Géotechnique* 23(3), 423–433: el mismo título, con dovelas verticales.

La propietaria decidió desarrollarlo con lo que hay en `referencias/Documentacion_Guia`:
- **Sarma (1973)**, consultado. Se cita por el concepto de Kc, por F como el factor que reduce la resistencia
  hasta Kc = 0 y por la aceptabilidad física: sin tracción, y Fₗ > 1 en las caras.
- **La recurrencia de 1979** se implementa desde la derivación propia del equilibrio de fuerzas de una cuña,
  escrita en `plan.md`. Sarma (1979) se cita por el método, como «no consultado».
- **Lo que ninguna fuente consultada fija** lo fijan los valores publicados, y se dice dónde.

## Criterios de aceptación

### Identidades (0.1.442)

- [ ] Una sola cuña sobre un plano da F = (c L + (W cos α − U) tan φ)/(W sen α) a 1e-8 relativo, con y sin
      agua.
- [ ] Caras verticales y resistencia de cara nula, sobre las MISMAS dovelas de `slice_surface`, dan el F de
      `JanbuSimplified` del motor a 1e-10.
  - Se mide en seco, con agua libre y con kh = 0,1 y kv = ±0,05 (convenio de D170).
  - En la planificación ya se midió a ≤ 5·10⁻¹³ en el 4 seco y saturado y en el 5.
- [ ] Reflejar el modelo en x da el mismo F.
- [ ] Con el sentido de cortante fijo y el cinemático: iguales donde la compatibilidad da el sentido por
      defecto, distintos donde no.

### Casos publicados (0.1.443, la referencia externa)

- [ ] Problema 4 del manual 03, con la interfaz de (108; 6,4) a (82,85; 56,89):
  - seco: 1,198 ± 1 %;
  - saturado, con la freática en la escombrera: 0,434 ± 1 %.
- [ ] Problema 5, con los ángulos y c/φ de su tabla 5.2, 10 vértices y γw = 1: 1,091 ± 1 %.
- [ ] Contraste independiente con `_tools/cunas_sarma.py` del banco, a 1e-6 y en sus dos modos de sentido. Es
      un contraste de implementación, no la referencia externa. Medido en la planificación:

      | Caso | Sentido fijo | Sentido cinemático |
      |---|---|---|
      | 4 seco | 1,198339 | 1,198339 |
      | 4 saturado | 0,434662 | 0,434662 |
      | 5 | 1,088271 | 1,089053 |

- [ ] **Convenio fijado por los publicados:** F reduce c y tan φ en bases Y caras. Reducir solo las bases, el
      convenio de 1973, daría +14,8 %, −58 % y +2,8 %, y queda escrito en el test.
- [ ] **Regla de raíz:** F es la raíz MAYOR de Kc(F) = kh. El 4 saturado da 0,4347 y no la otra raíz, 0,1467,
      aunque la primera esté a ~1,4 % de un polo.

### Integración (0.1.444–0.1.445)

- [ ] No se activa por defecto, y ninguno de los nueve métodos mueve un número:
  - la suite entera en verde;
  - `verificar_cierres` del banco (raíz y 02) sin bajadas.
- [ ] `model_hash` de un proyecto sin Sarma no cambia, y un `.ogr` anterior abre.
- [ ] Un archivo con Sarma abre en una versión anterior, con la nota de método no registrado.
- [ ] Cada ajuste nuevo mueve el número (regla 7), con un test cada uno:
  - dovelas, tolerancia e iteraciones;
  - ángulos;
  - resistencia de interfaz y su c/φ;
  - contactos de material;
  - sentido del cortante;
  - cada dato por vértice.
- [ ] Con desembalse rápido o B-bar, `[bishop, sarma]` da Bishop igual al bit y Sarma no calculado, con UNA
      nota.
- [ ] Una rejilla `[bishop, janbu, sarma]` deja vacío el `SliceShare`, y los verticales salen iguales al bit.
- [ ] Ky(1) = max(0, sup_{F≥1} Kc(F)), dentro de las tolerancias de `yield_acceleration`. El 4 saturado da
      Ky = 0.
- [ ] Con c/φ de cara dada, F_diseño = F/γ a 5·10⁻⁹, también con γR;e ≠ 1.

### Superficies no circulares del usuario (0.1.427)

- [x] Ida y vuelta por el `.ogr`. Sin polilíneas, la clave no se escribe y la huella no cambia.
- [x] En una corrida no circular, cada método vertical da sobre la polilínea del usuario el MISMO F que
      `surface_evaluate`. En una corrida circular se salta, con su nota.
- [x] En la ventana:
  - acciones propias para añadir y gestionar, alcanzables desde el menú Superficies;
  - en gris con tipo circular;
  - se deshacen.

### Ventana (0.1.444–0.1.447)

- [ ] La casilla de Sarma y su grupo de ajustes en Métodos, en gris cuando no aplican.
- [ ] La tabla de ángulo, c y φ por vértice, desde el menú Superficies y desde el menú contextual del vértice.
- [ ] La herramienta de ángulos con el ratón: rayo en vivo, clic o tecleo de 0 a 360°, y deshacer.
- [ ] Interpret dibuja las cuñas: polígonos, caras inclinadas y filas de cara.
- [ ] Todo texto nuevo pasa por `tr()` con su español, y toda acción está en un menú.

### Ángulos optimizados (0.1.448)

- [ ] F optimizado ≤ el de cada política (vertical, bisectriz, normal media) en la misma superficie, y se
      repite igual dos veces.
- [ ] Problema 1: sus figuras 1.2 y 1.3, digitalizadas con la lectura declarada, con ángulos optimizados, dan
      1,382 / 1,324 del programa de referencia dentro de una tolerancia que cubra la digitalización.

### Cierre (banco)

- [ ] `d357()` da CUBIERTO POR TEST, y `d122()` y `d123()` siguen cerrando, re-anclados a la comparación con
      Sarma.

## Validación numérica

Por orden de fuerza:
1. La forma cerrada de una cuña.
2. La identidad con Janbu simplificado, Janbu (1954, 1973), sobre las mismas dovelas: un camino ya validado del
   motor.
3. Los problemas 4 y 5 del manual 03: fuente original Hoek (1987) y valores del programa de referencia.
4. El problema 1 digitalizado, para los ángulos optimizados.
5. La herramienta independiente `cunas_sarma.py`, como contraste de implementación.

## Fuera de alcance

- Sarma (1973) con dovelas verticales y X = λFᵢ: es otro método. Si los problemas 6, 8 o 9 del 03 resultan
  ser de 1973, se declaran por escrito.
- Soportes con Sarma: se rechazan con código.
- Desembalse rápido y presión en exceso: no se calculan, con su nota.
- La línea de empuje.
- La búsqueda de cuco del problema 2.
- El muestreo estadístico de la c/φ de cara dada a mano: se declara y se avisa.
- Una resistencia de cara fuera de Mohr-Coulomb, salvo dada a mano.
