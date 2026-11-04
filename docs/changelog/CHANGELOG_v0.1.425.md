# OGR Slip2D v0.1.425

**Una estadística dice cuántas de sus muestras incumplen una regla por la que la propia corrida se rechaza (D376).**
- Global Minimum y Overall Slope cuentan las muestras que incumplen una regla de la corrida, y la sensibilidad cuenta
  los puntos de su barrido. Un aviso de la corrida (`stat.samples_break_rules` o `stat.points_break_rules`) lo dice
  regla por regla, con la frase de la primera muestra que la incumple.
- Ejemplos: un kh negativo, un kh o un kv que el factor sísmico de la norma saca de rango, un modelo de resistencia con
  el que no se puede calcular, o una línea de desembalse por encima del nivel freático.
- **Ningún número cambia:** toda muestra se sigue evaluando como antes.

Es la tercera de la tanda P5c. La ficha sale de la sonda S7 de la auditoría del cómputo (`AUDITORIA_COMPUTO_v0.1.377.md`
§10, A7). **Decisión de la propietaria (2026-11-04): opción C, solo decirlo.** Rechazar esas muestras (A) o acotar la
variable en el cero (B) movería la estadística, y se decide aparte.

## 0. Lo que se encontró

- **El mecanismo.**
  - `check_analysis_settings` rechaza lo que una corrida no puede calcular tal como está configurada. Una corrida
    determinista con kh < 0 se rechaza (D206, 0.1.219).
  - `run_configured_statistics` la pregunta una vez, sobre el modelo **sin muestrear**. Después cada muestra escribe sus
    valores en un clon (`apply_sample`), y nadie vuelve a preguntar.
  - `default_dispersion` da a una variable de media nula (kh, kv, el desplazamiento del nivel freático) una desviación
    de 0,1 y un rango de ±0,3 absolutos. Así que, por defecto, la mitad de las muestras de kh salen negativas.
- **Medido en la auditoría** (S7, 0.1.377), y aquí otra vez: el modelo del 028 con kh de media nula y la dispersión
  por defecto, 200 muestras de Monte Carlo.
  - **99 tienen kh < 0**, de −0,29 a +0,29.
  - Global Minimum las evaluaba todas, sin fallos ni notas.
- **El desembalse invertido, que la ficha leyó sin medirlo, también pasa:**
  - `wrap_for_drawdown` comprueba la línea de desembalse cuando se **construye** el método, y el conductor estadístico
    construye los métodos una vez, desde el proyecto sin muestrear;
  - una variable del nivel freático lo desplaza en cada muestra, y puede dejarlo por debajo de la línea;
  - el test nuevo lo mide en el talud del Appendix G.
- **Un hallazgo que no se toca (regla 6).** La sensibilidad descarta en silencio el punto cuya evaluación falla
  (`sensitivity.py`, el `except` del barrido): no lo cuenta ni dice la causa. Global Minimum y Overall Slope sí la dicen
  desde D127 (0.1.169). Se propone una ficha nueva.

## 1. Qué cambia

- **`ogr_slip2d/probabilistic.py`:** un colector `_SampleRules`.
  - Al crearse, pregunta `check_analysis_settings` sobre el modelo sin muestrear y guarda sus códigos. Lo que el modelo
    ya incumple no se cuenta: eso lo rechaza la puerta, y un llamador que se la saltara lo vería contado en cada
    muestra.
  - `see(índice, clon)` pregunta **la misma función** sobre el clon muestreado, antes de `prepare`. Así no se copia
    ninguna regla. Lo hace una sola vez por índice, porque las muestras son las mismas para todos los métodos. Solo
    lee el clon, y si la comprobación revienta lo cuenta como `stat.raised`.
  - `publish` da un aviso por corrida, con cada regla contada y la frase de la primera muestra que la incumple, valores
    incluidos. El orden es por recuento y después por código, nunca por llegada.
  - Global Minimum y Overall Slope lo llaman tras `apply_sample`. Overall Slope lo hace antes de construir la búsqueda,
    así que una muestra cuya búsqueda falla también cuenta.
- **`ogr_slip2d/sensitivity.py`:** lo mismo por punto del barrido (variable, punto), con `stat.points_break_rules`.
- **`ogr_slip2d/stat_messages.py`:** `stat.samples_break_rules`, `stat.points_break_rules` y `stat.rule_counted`
  («{n} veces; la primera: {regla}»). La lista de reglas va separada con «; », porque cada regla es una frase entera.
- **`ogr_gui/i18n/__init__.py`:** su castellano.
- **`tests/test_stat_notes_v1353.py`, cambiado a propósito:** los tres códigos en `_LATER`, y `_SampleRules.see` y
  `_SampleRules.publish` en el censo `_CODED`.
- **`tests/test_sample_rules_v1425.py`,** nuevo, con 8 tests.
- El número en los nueve sitios y el contador de los dos README.

## 2. El coste, medido y aceptado por la propietaria

- `check_analysis_settings` cuesta ~0,3 ms en un clon recién hecho, sobre todo por las reglas de resistencia de cada
  material y los `import` locales de la función. En un clon ya usado son 0,08 ms.
- **028** (5 materiales, ~11 ms por muestra), GM con N = 200, A/B en el mismo proceso, alternando:
  - con la comprobación, 2,239 y 2,240 s; sin ella, 2,189 y 2,191 s;
  - **+2,3 %**.
- **036** (1 material, ~6 ms por muestra), GM con N = 1000:
  - con, 6,045 y 5,962 s; sin, 5,953 y 6,076 s. El ruido es mayor que el efecto;
  - contando el trabajo, ~2 %.
- En Overall Slope, donde cada muestra es una búsqueda entera, el coste es despreciable.
- **Decisión de la propietaria (2026-11-04): se deja así**, con una sola fuente de reglas, en vez de preguntar solo
  cuando una variable «toca» una regla, que sería un conocimiento copiado.

## 3. Qué se probó

- **`tests/test_sample_rules_v1425.py`,** 8 tests, 4,3 s con el arranque:
  - **el recuento es exacto**, contra una cuenta hecha sin el código que se prueba:
    - los valores negativos de la columna de kh que sorteó la propia corrida, en Global Minimum (N = 40), en Overall
      Slope (con una fábrica que se niega a buscar, así que cuenta antes de la búsqueda) y en los cinco puntos del
      barrido (−0,3, −0,15, 0, 0,15 y 0,3: dos);
    - el desembalse invertido en el Appendix G con el nivel inicial a 103 y la línea a 95: los desplazamientos por
      debajo de −8, porque con las dos líneas horizontales ahí es exactamente donde la línea queda por encima del
      nivel. La regla sale con su código, `setting.drawdown_line_above`;
  - **nada se mueve:** la misma corrida con el colector parcheado a nada da los mismos factores y los mismos índices de
    muestra (A/B en el mismo proceso);
  - una corrida sin muestras que incumplan nada no dice nada, y lo que ya incumple el modelo sin muestrear no se cuenta;
  - el aviso en castellano.
- **Discriminación.** En el árbol anterior (worktree de 83880d1, 0.1.424) fallan 6 de 8:
  - 5 por comportamiento, porque no hay nota;
  - 1 por no tener `_SampleRules`.
  - Pasan los 2 invariantes negativos («no dice nada»), que valen en los dos árboles.
- **Vecinos:** los 20 archivos de estadística, sensibilidad, variables aleatorias, mensajes, Overall Slope, métodos de
  desembalse y cambios de masa: 392 de 392.
- **Suite entera** con `--jobs 4`: 7127 en verde, 1 saltado, 0 fallos, sin fugas ni tramos muertos.
- **Banco de pruebas del cómputo**, lote `version`: los 23 casos idénticos a 0.1.377, K19 y K20 incluidos.
- **Las once probabilísticas del banco**, corridas otra vez: idénticas bit a bit a `Evaluaciones/0.1.411` (19 números
  por archivo del 028 y 31 en el del 036), y sin claves sin pareja. Ninguna de sus muestras incumple una regla, así
  que no ganan ninguna nota. Tardaron 2200 s porque compartieron la máquina con los tests de la versión siguiente.
- **`d376()`**, nueva en el `verificar_cierres.py` de la raíz, con el caso de S7 en vivo (el 028, kh de media nula,
  200 muestras de Monte Carlo, semilla 11): **CUBIERTO POR TEST**.
  - La nota cuenta 99, que son exactamente las muestras con kh < 0, con la regla `rule.seismic_kh_negative`.
  - Se evalúan los 200 factores.
  - Discriminada con el motor de 0.1.424: **SIGUE ABIERTO**, sin nota y con los 200 evaluados. Es la medida de S7.
- **El VC de la raíz entero:** 136 comprobaciones, todas cierran, y 0 bajadas. **El del 02 en seco:** 242 de 242
  iguales, por la primera línea de cada ficha.
- **El cierre del banco:** `Evaluaciones/0.1.425` de la raíz, D376 retirada al índice, podada de `PAQUETES` y tachada en
  la cadena de P5. `auditoria_invariantes.py` da 0 ERROR en la raíz y en el 02.

## 4. Lo que queda

- **A o B de la ficha** (rechazar las muestras que incumplen una regla, o acotar la variable en el cero) quedan por
  decidir, con su propia ficha. Las dos mueven la estadística.
- **La sensibilidad descarta en silencio los puntos que fallan** (véase §0): propuesta de ficha nueva.
