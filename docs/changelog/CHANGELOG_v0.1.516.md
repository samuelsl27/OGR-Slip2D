# OGR Slip2D v0.1.516

**D467: con la fuerza por encima del centro del círculo, el retroanálisis de Bishop ya no dice «no hace
falta soporte».** Esa superficie se deja fuera con su nota y se cuenta aparte, como las que la fuerza no
toca (D418). Es la decisión de la propietaria del 2026-11-28, entre las tres que planteaba la ficha:
rechazarla con nota, dar la fuerza con su signo, o dejar el 0 y avisar.

## 0. Lo que se encontró

- **El mecanismo.** Bishop ve la fuerza horizontal T solo por su momento respecto del centro, con el
  brazo `(y_c − y_T)/R` (Bishop 1955). Con la fuerza por encima del centro el brazo es negativo, y
  entonces cualquier fuerza hacia el talud **baja** los dos factores: el activo, R/(D + T·|brazo|), y
  el pasivo, (R − T·|brazo|)/D. Ninguna fuerza hacia el talud lleva esa superficie al objetivo. La
  cuenta daba una fuerza negativa, y el recorte a 0 («the surface already exceeds the target») la
  publicaba como «no hace falta soporte», del lado inseguro, para una superficie por debajo del
  objetivo.
- **Medido el 2026-11-28 con 0.1.514** (`_auditoria/P10_D467/medir_d467.py` y sus logs):
  - **talud de ejemplo** (objetivo 1,419): 150 círculos por debajo del objetivo, **ninguno** con el
    centro por debajo de su coronación, porque la rejilla queda entera por encima del talud;
  - **037 del 02** (objetivo 1,5): **50** círculos por debajo del objetivo, con la cota entre su centro
    y su coronación, salen con el brazo negativo, una fuerza de −1151 a −34 662 kN/m antes del recorte
    y **0 publicado**. Sus controles, con la cota por debajo del centro, dan de 104 a 160 kN/m.
- **Lo que mueve una corrida entera del 037** (`corrida_037_0.1.516.log`, con la regla puesta y quitada
  en el mismo proceso):
  - a la **cota 9 del enunciado**, nada: **334,7721 kN/m** con la regla y sin ella, y ninguna
    superficie con el centro por debajo de la fuerza;
  - a la **cota 15,5**, la fuerza que gobierna es la misma, 1493,0544 kN/m. Pero **22** superficies se
    dejan fuera y se dicen, cuando antes contaban como analizadas con un 0 (2893 analizadas frente a
    2915).

  El 0 nunca gobernaba, porque gobierna la mayor. Lo que escondía es una superficie que esa fuerza en
  esa cota no puede estabilizar, y si lo eran todas, el resultado era un 0 sin nota.

## 1. Qué cambia

- `ogr_slip2d/back_analysis.py`:
  - `ARM_ABOVE_CENTRE_REFUSED = True`, el interruptor de módulo, que se lee en cada llamada para el A/B
    y para el test de la regla 7;
  - `required_force`: con el brazo negativo devuelve la superficie sin fuerza y con la nota
    `above_centre`. La regla es el signo del brazo, geométrica y exacta: no lee ningún factor;
  - `run_back_analysis`: con Bishop, la superficie por debajo del objetivo que la fuerza toca, con
    `elevation > centre_y`, se deja fuera antes de calcular su fuerza. Se cuenta en
    `surfaces_above_centre`, que también va en `summary()`, y no en `surfaces_analysed`. Se dice
    siempre (`above_centre_skipped`), porque esas superficies siguen por debajo del objetivo. Si no
    queda nada que calcular, esa nota es el error, después de la de las que la fuerza no toca;
  - `required_force_of_result` (la ventana): la nota va después de los dos filtros de D418, en el orden
    de la corrida. Una superficie que ya alcanza el objetivo no necesita nada, sea cual sea el brazo.
- `ogr_slip2d/run_messages.py`: tres códigos, `run.back_above_centre_left_out`,
  `run.back_none_above_centre` y `run.back_surface_above_centre`, con su castellano en
  `ogr_gui/i18n/__init__.py`.
- Las ventanas: Interpretar dice la nota de la superficie (`above_centre`) como las dos de D418, y la
  principal pone `above_centre_skipped` en el panel de notas, junto a `untouched_skipped`.
- `ogr_mcp/guide.py`: `back_analysis_run` explica `surfaces_above_centre`. Las notas ya llegaban al
  agente enteras (`back_analysis_summary`).
- Janbu no tiene brazo (`arm = 1`), y no cambia nada para él.

## 2. Tests

- `tests/test_back_analysis_arm_v1516.py` (nuevo, 7 tests, menos de 1 s). El círculo es del talud de
  ejemplo, con centro (28, 22) y R 6: entra por la coronación a y = 25 y sale por la cara a
  y = 17,76. Se comprueba:
  - la premisa: a y = 23,5 el brazo es −0,25 (forma cerrada), la fuerza antes del recorte es negativa
    y, sin la regla, se publica el 0 de antes;
  - con la regla, la nota y ninguna fuerza;
  - la corrida la deja fuera, la cuenta y lo dice como error;
  - junto a un círculo al que la fuerza sí ayuda, gobierna ese, y la nota dice que el otro se quedó fuera;
  - el control: a y = 20, por debajo del centro, la misma fuerza bit a bit con la regla y sin ella;
  - Janbu: la misma fuerza con la regla y sin ella;
  - el camino de la ventana da la misma nota.
- `tests/test_seepage_run_notes_v1352.py`: tres muestras nuevas en su censo, una por código.
- Áreas `back_analysis`, `i18n`, `mcp`, `run_notes`, `core_messages` y `labels_spanish`, con `--jobs 4`:
  232 casos en verde.

## 3. Suite

La suite entera se corre al final de la tanda.
