# OGR Slip2D v0.1.498

**D439: una superficie cuyo factor a kh = 0 ya está en el objetivo del Ky, o por debajo, se dice
con código.** Su Ky es 0, como documenta la referencia, y eso no cambia. Pero la corrida no lo
decía, y con Newmark publicaba metros de desplazamiento de un bloque que no se sostiene ni sin
sismo. No cambia ningún número.

## 0. Lo que se encontró

- **La medida de la ficha, repetida con 0.1.496** (`_auditoria/P10_D439_D440/medir_d439_d440.py`):
  el plano de `test_newmark_user_surfaces_v1429` con una norma custom que divide c y tan φ por
  2,5 da F(0) = 0,808357 (forma cerrada 0,808290), Ky 0 y 22,04197816406031 m, sin ninguna nota
  sísmica. Idéntico a 0.1.485.
- **El banco** (paso 0 de la ficha): el único modelo con Ky es `modelo_ky.ogr` del 104 del 02.
  Medido con 0.1.497 (816 s, Spencer, enjambre de partículas): **0 de 2123** superficies válidas
  tienen Ky = 0 con el factor estático en el objetivo. La nota no aparece en el banco.
  - De paso: su crítica da Ky 0,139357 con F 1,364342, y `resultados_modelo_ky.json`, escrito con
    0.1.179, guarda 0,140014 con F 1,365225. Es la deriva acumulada desde esa versión, no de esta.
    No se ha atribuido.

## 1. Qué cambia

Opción **(a)**, la recomendada en la ficha: solo la nota.

- `ogr_slip2d/method_note_messages.py`: tres códigos, como el par `SEISMIC_NO_KY` /
  `SEISMIC_NO_KY_GIVEN`:
  - `method.seismic_static_unstable`: N de M superficies, con su singular;
  - `method.seismic_static_unstable_critical`: lo mismo cuando la crítica publicada es una de
    ellas, con su factor a kh = 0;
  - `method.seismic_static_unstable_given`: la superficie que le dieron a `evaluate_surfaces`.
- `ogr_slip2d/analysis_runner.py`, `_seismic_lines`:
  - el criterio es el mismo que da Ky = 0 en `critical_coefficient_from`: una superficie válida
    con `ky == 0` y un factor igual o inferior a `ky_target_fos`;
  - la nota va detrás de la de «sin Ky» y se construye al final. Así, «la crítica» es la que
    publica la corrida una vez adjuntos los desplazamientos (la prepara D437). La corrida pasa su
    `SearchResult` (`result=`);
  - la dice también una corrida solo de Ky, sin Newmark;
  - la parte de Newmark pasa a `_newmark_lines`, sin cambiar lo que hace.
- `ogr_gui/i18n/__init__.py`: el castellano de las cinco plantillas.

## 2. Tests

- `tests/test_seismic_static_unstable_v1498.py` (nuevo, 7 tests). La premisa va contra la forma
  cerrada: F(0) = (tan φ / 2,5) / tan β < 1 < tan φ / tan β.
  - La nota sale, con su código, en la corrida (`_critical`, con el factor de la crítica), en
    `evaluate_surfaces` (`_given`) y en una corrida solo de Ky.
  - Sin la norma no sale (regla 7).
  - El Ky sigue en 0, y el desplazamiento es el del integrador a ky = 0.
  - Contra 0.1.497 fallan 3 de 7.
- `tests/test_method_notes_v1348.py`: cinco muestras nuevas en `_V1347`, una por plantilla.
- Áreas `newmark`, `method_notes`, `surface_evaluate_seismic`, `i18n`, `translation`, `seismic`,
  `yield_acceleration` y `report_seismic`: 241 en verde.
- Banco: `d439()` en el `verificar_cierres.py` de la raíz da **CUBIERTO POR TEST**.
