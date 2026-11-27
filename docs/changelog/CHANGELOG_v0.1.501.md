# OGR Slip2D v0.1.501

**D441: la sensibilidad nombra las variables que deja fuera por no tener rango.** Hasta esta
versión desaparecían del resultado sin ninguna nota. Una variable con distribución `none` y con
rango se sigue barriendo, como documenta la referencia, y la guía del agente deja de decir que
`none` la apaga sin más. Ningún factor cambia.

## 0. Lo que se encontró

- **La medida de la ficha, repetida con 0.1.500** (`_auditoria/P10_D441/medir_d441.py`: talud de
  ejemplo, rejilla 3×3, Bishop, 4 intervalos, por la puerta). Idéntica a 0.1.485 y 0.1.453:
  - con la cohesión en `none` ±2, se barre de 8 a 12 kPa (factores de 1,0458 a 1,2097), sin
    nota;
  - con la cohesión sin rango y el rozamiento ±5, la cohesión desaparece del resultado, y `notes`
    y `note_lines` salen vacíos.
- **La nota nueva llega a todas las puertas sin tocar ninguna:**
  - `notes["warning"]` va a la barra de estado, que ya lo leía (`main_window`);
  - `note_lines` va al panel de notas del análisis y al agente (`ogr_api/results.py`);
  - la ventana nombra la variable por su etiqueta, con `variable_keys` (D412).
- **Con el probabilístico `none` tampoco se dice**, a propósito: `stat.vars_not_random` calla la
  razón `none` (`said = … != "none"`). Por eso la guía decía «without one». En la sensibilidad,
  `none` no apaga la variable, así que la frase de la guía no valía para ella.
- La ayuda de la referencia no dice qué hace con una variable seleccionada sin rango. Sigue sin
  medirse.

## 1. Qué cambia

Caso 2 sin decisión. Caso 1, opción **A** de la propietaria (2026-11-27).

- `ogr_slip2d/stat_messages.py`: código nuevo `stat.sens_no_range`. Dice N de M y las claves, con
  su singular, y `kinds` `variable_keys`.
- `ogr_slip2d/sensitivity.py`, `run_sensitivity`: cuando unas variables tienen rango y otras no,
  avisa (`warning`) y nombra las que no lo tienen. Si ninguna tiene rango, sigue el `NO_RANGE` de
  siempre. La regla es `has_range` (D416), sin cambios.
- `ogr_mcp/guide.py`: `none` apaga una variable en los análisis probabilísticos. La sensibilidad
  solo lee el rango: barre toda variable que lo tenga, `none` incluida, y nombra las que no
  (`stat.sens_no_range`).
- `ogr_gui/i18n/__init__.py`: el castellano de las dos plantillas.

## 2. Tests

- `tests/test_sensitivity_unranged_v1501.py` (nuevo, 6 tests):
  - la variable sin rango sale nombrada con su código, en `notes` y en `note_lines`, y con rango
    en las dos no sale nada (regla 7);
  - `none` se barre de 8 a 12 kPa sin nota, y la guía del agente lo dice;
  - ningún factor se mueve: el barrido del rozamiento es el mismo sea cual sea la cohesión, y el
    de la cohesión `none` es el de la misma cohesión con distribución normal, bit a bit.

  Contra 0.1.500 fallan 2 de 6. Los otros cuatro son los de «nada se mueve».
- `tests/test_stat_notes_v1353.py`: las dos muestras del código nuevo (plural y singular).
- Áreas `sensitivity`, `stat_notes`, `core_messages`, `statistics`, `mcp`, `i18n`, `translation`
  y `random_variable`: 303 en verde.
- Banco: `d441()` en el `verificar_cierres.py` de la raíz da **CUBIERTO POR TEST**.
