# OGR Slip2D v0.1.72 — los parámetros de agua donde corresponden, y el descenso rápido solo cuando se pide

## Qué se buscaba

El diálogo *Define Materials* enseñaba a todo el mundo, siempre, un grupo
entero de **Rapid Drawdown Parameters**: cinco controles para un análisis
que la inmensa mayoría de los proyectos no ejecuta nunca. Ocupaban un
cuarto del diálogo y estaban ahí porque en v0.1.62 se decidió
*deshabilitar en lugar de ocultar*, «para que la capacidad siga siendo
descubrible».

Esa regla es buena, pero se estaba aplicando a la pregunta equivocada.

## El hallazgo: hay dos preguntas distintas, y se estaban mezclando

Deshabilitar-en-lugar-de-ocultar resuelve el caso en que **la elección del
propio material** deja un campo sin sentido: si cambias el tipo de presión
intersticial a Ru, el coeficiente Hu no aplica, pero lo aplicará otra vez
en cuanto vuelvas atrás — y el valor que había debe seguir a la vista.

No resuelve el caso en que **el proyecto entero** deja un campo sin
sentido. Un proyecto sin descenso rápido no va a activarlo desde el
diálogo de materiales: se activa en Ajustes del proyecto → Agua
subterránea → Avanzado. Mantener sus controles en pantalla no los hace
descubribles; solo hace más caro el diálogo para todos los demás.

De ahí la separación que ahora aplica el código, y que es lo que conviene
recordar de esta versión:

| Qué deja el campo sin sentido | Qué se hace |
|---|---|
| La elección del **material** | Deshabilitar (el valor sigue visible) |
| El **proyecto** | Ocultar (el análisis que lo necesita lo trae de vuelta) |

Contrastado con la documentación de referencia, que hace exactamente esa
distinción: sus *Rapid Drawdown Parameters* y *Excess Pore Pressure* solo
existen si la opción avanzada correspondiente está activa, mientras que
sus *Water Parameters* se deshabilitan sin desaparecer.

## Cambios

### 1. La sección se llama «Water Parameters»

El grupo se llamaba *Pore Pressure*. La presión intersticial es la
**magnitud**; lo que hay en ese grupo son las **entradas** que la
determinan. La referencia lo llama *Water Parameters* y tiene razón. En
español, «Parámetros de agua».

### 2. El grupo de descenso rápido aparece solo si hay descenso rápido

`grp_drawdown` se oculta salvo que `groundwater.rapid_drawdown` esté
activo — **y además se deshabilita**. Lo segundo parece redundante, y lo
es para el ojo, pero la garantía que se hace es «B̄ no puede fijarse sin
una ejecución de descenso rápido», y eso es una afirmación sobre los
widgets, no sobre lo que casualmente esté en pantalla.

### 3. Y enseña solo el parámetro que el procedimiento va a leer

B̄ y la envolvente no drenada **no son compañeros, son alternativas**:

- `b_bar` (tensiones efectivas) → casilla *Undrained Behaviour* + **B-bar**;
- `duncan_wright`, `corps_2`, `lowe_karafiath` → casilla + **envolvente**.

Antes se enseñaban los dos a la vez, así que todo usuario de descenso
rápido veía al menos un campo que su análisis ignoraba. Eso es la regla 7
en su versión de interfaz: un control que no decide nada se lee como si
decidiera.

Para saber cuál mostrar hacía falta un dato que el diálogo no recibía:
`main_window` le pasaba `rapid_drawdown` pero no `rapid_drawdown_method`.
Ahora sí.

### 4. La envolvente se muda a un diálogo propio

Nuevo `ogr_gui/dialogs/drawdown_strength_dialog.py`
(`DrawdownStrengthDialog`), tras un botón **Define Strength...**, que es
donde la referencia la guarda. Cinco widgets menos en el editor principal.

El detalle que evita que esto sea un retroceso: **junto al botón hay un
resumen** («R: Cr = 60, φR = 23°»), así que el valor sigue leyéndose sin
abrir nada. Mover un campo detrás de un botón es aceptable; esconder su
valor no lo sería.

`envelope_summary()` vive en el mismo módulo que el diálogo que edita la
envolvente, para que los dos no puedan separarse.

### 5. El grupo de agua responde al método del proyecto

- **Análisis por elementos finitos** (`fea_steady`, `fea_transient`): el
  grupo entero desaparece — la filtración suministra las presiones — y lo
  que el material sigue aportando son φb y el valor de entrada de aire,
  que ya tenían su propia puerta.
- **Rejilla de presiones**: aparece un interruptor nuevo, *Usar la rejilla
  de presiones*.
- **Cualquier otro método**: el interruptor de rejilla no se ve, porque no
  decide nada sin una rejilla.

### 6. `Material.use_grid`, y por qué no devuelve cero

Campo nuevo, por defecto `True` — el único valor que deja intactos los
archivos escritos antes de que existiera, que siempre se comportaron con
la rejilla activa.

La decisión de diseño que merece quedar escrita: con la rejilla
desactivada, `pore_pressure_at` **cae al modelo propio del material** en
lugar de devolver cero. La referencia describe u = 0, y con un material
en el tipo por defecto (`NONE`) el resultado es exactamente ese. Pero un
proyecto creado con superficies de agua y cambiado después a rejilla tiene
materiales con su superficie ya asignada; devolver cero se la tiraría a la
basura en silencio. Caer al modelo propio da u = 0 en el caso que la
referencia describe y conserva la información en el que no describe.

### 7. Regla de la referencia: tres modelos de resistencia no leen agua

*Undrained*, *No Strength* e *Infinite Strength* no consultan ninguna
presión intersticial. Con cualquiera de los tres seleccionado, el grupo de
agua se deshabilita entero. Ofrecer las entradas sugería una influencia
que no existe.

### 8. Bug corregido: dos etiquetas flotando sobre nada

`_apply_unsaturated_visibility` ocultaba los spinboxes de φb y del valor
de entrada de aire, pero **no sus etiquetas**. El código pedía
`wgt.parentWidget()` creyendo que devolvía la etiqueta; devuelve el grupo,
así que la comprobación `if lbl is not None` siempre pasaba y la línea
siguiente volvía a ocultar el spinbox. El resultado: dos títulos sin campo
debajo en todo proyecto que no fuera de elementos finitos.

Quien sabe dónde están sus etiquetas es el `QFormLayout`, así que es a él
a quien se pregunta ahora (`labelForField`).

## Camino equivocado que conviene no repetir

El primer intento de ocultar filas usó `QFormLayout.setRowVisible`, que es
lo obvio y lo correcto… desde Qt 6.4. El helper `_set_row_visible` que
quedó en el código usa `labelForField`, que funciona en cualquier versión
y además cubre las dos formas de fila que este diálogo mezcla: las creadas
con un texto (la etiqueta es un `QLabel` generado) y las creadas con dos
widgets (la «etiqueta» es una casilla o un botón).

## Tests

`tests/test_material_dialog_v172.py` — 21 tests nuevos, organizados
alrededor de la distinción del hallazgo: un bloque para «lo que oculta el
proyecto», otro para «lo que solo deshabilita el material». Confundirlos
es lo que deja una interfaz o recargada u olvidadiza, así que cada mitad
se fija por separado.

El ancla numérica es la regla 7 aplicada a `use_grid`, y es una
**identidad analítica**, no un valor capturado: con una rejilla de valor
CONSTANTE, cualquier interpolación de un campo constante es esa constante
sea cual sea el esquema, así que apagar el interruptor tiene que mover `u`
exactamente esa constante. Se comprueba también que apagarlo no es un cero
en blanco: un material con su propio Ru sigue usándolo.

Cuatro tests de `test_rapid_drawdown_v168.py` y uno de
`test_water_surfaces_v162.py` se reescribieron contra la nueva ubicación.
La invariante que protegían no cambió —la envolvente debe ser alcanzable,
debe hacer ida y vuelta, y sus dos campos deben llamarse según la forma
elegida—; lo que cambió es dónde viven los widgets.

Un detalle del presupuesto de traducciones que conviene no repetir mal:
las dos cadenas de resumen de la envolvente («R: Cr = %.4g, φR = %.4g°» y
su equivalente Kc=1) son **notación pura**, idéntica en los dos idiomas, y
eso hizo saltar `test_no_lazy_identity_translations`. La salida correcta
es la **lista blanca** que ese test ya tiene documentada para símbolos y
cadenas de formato —donde ya viven `"   |   FS = %s"` y `"%s — %s (%d)"`—,
no subir el umbral de 12. El umbral existe precisamente para detectar
entradas olvidadas; subirlo para que pase tu cambio es el descuido que el
test vigila. Una «traducción» distinta de esos símbolos sería incorrecta,
no más española.

**Probado**: la suite completa, 1541 tests, 1540 en verde a la primera y
el restante el de presupuesto de i18n descrito arriba, ya corregido. Los
**24 tests de los casos de validación** (`test_slide_validation_ej1` y
`test_validation_cases`) se ejecutaron además por separado y pasan: era el
criterio de parada declarado, y ningún factor de seguridad de referencia
se ha movido.

**Falta por probar**: la comprobación visual del diálogo con cada uno de
los cuatro procedimientos en una pantalla real; los tests solo pueden
afirmar sobre `isVisibleTo`, no sobre cómo queda el reparto de espacio.

## Pendientes que esta versión deja anotados

Que no se pierdan entre versiones es la mitad del valor de este archivo.

1. **El grupo *Excess Pore Pressure* del diálogo de materiales.** La
   referencia lo tiene (B̄ + casilla «el peso del material genera
   exceso»), y nosotros no. **Se decidió esperar**: hoy
   `groundwater.excess_pore_pressure` solo bloquea interfaz y **ningún
   módulo de cálculo lo lee**, así que añadir su interfaz ahora repetiría
   exactamente el fallo de los coeficientes parciales de v0.1.52 → v0.1.57
   — un control configurable durante dos versiones sin aplicarse. Entra
   con su motor, no antes.

2. **El calculador GSI no escribe nada.** Encontrado al leer este archivo:
   `_open_parameter_calculator` busca los editores en
   `getattr(panel, "_widgets", {})`, pero `_StrengthParamPanel` los guarda
   en `self._editors`. `_widgets` no existe nunca, así que `.get(key)`
   sobre `{}` devuelve siempre `None` y mb, s y a se descartan en
   silencio: el usuario rellena GSI, mi y D, acepta, y no cambia nada.
   **No se corrige aquí**: se arreglará —y se ampliará— con el módulo
   **Rock Data**, que es donde ese cálculo tiene su sitio.

3. **`ogr_cli` no aplica el descenso rápido.** No hay ninguna referencia a
   `wrap_for_drawdown` ni a `check_drawdown_settings` en todo `ogr_cli/`,
   así que un cálculo por terminal con el análisis activo devuelve el
   factor de seguridad ordinario sin decir nada. Es el mismo fallo que
   v0.1.69 corrigió para B̄ dentro de la interfaz, sobreviviendo en el otro
   camino de entrada.

4. **Las anomalías de Project Settings**, que se abordan en v0.1.73 y
   v0.1.74: `RestoreDefaults` reconstruye 4 de las 9 páginas; la página
   Transient machaca la opción avanzada que decidió la de Groundwater; las
   casillas de exceso y descenso rápido no son excluyentes en la interfaz;
   y `failure_direction` no orienta ningún cálculo salvo el ángulo de las
   fuerzas de sostenimiento.
