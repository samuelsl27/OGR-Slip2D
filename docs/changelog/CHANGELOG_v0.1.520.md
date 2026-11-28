# OGR Slip2D v0.1.520

**D468, corrección: una cara vertical del terreno solo es corte obligado con agua libre DELANTE de ella.**
0.1.519 la cortaba también con el agua por encima de su pie solo detrás, y eso movió el rebanado validado
del problema 059 del banco. Lo vio la suite entera de 0.1.519: 20 fallos, todos en dos archivos.

## 0. Lo que se encontró

- **Los 20 fallos** son de `tests/test_lambda_closure_v1180.py` (11) y `tests/test_lambda_floor_v1184.py`
  (9). Los dos usan el círculo publicado del 059.
  - El muro del 059 está en x = 0, de 0 a 20, y su freático nace justo en el pie, en (0, 0). Una
    tolerancia detrás de la cara está 0,00046 m por encima del pie: es agua del terreno, no agua libre.
  - Con la regla «en cualquiera de los dos lados», el muro pasó a ser un corte nuevo. El rebanado cambió
    y con él la búsqueda de λ que esos tests fijan (por ejemplo, F_m pasa a 0,55897).
- **El error es mío y del censo.** El censo de 0.1.519 (`censo_d468_0.1.518.log`) sí listaba el 059,
  pero lo descarté como «el borde izquierdo del modelo», y no lo es: el terreno sigue a la izquierda de
  x = 0. Contado bien, la regla de 0.1.519 movía el 059. La de 0.1.520, solo con agua delante, se queda
  en el 092 (dos modelos), y allí el A/B no movía nada.
- **Lo que queda sin arreglar, reportado.** Con el agua por encima del pie solo detrás de una cara, la
  dovela que contiene la cara sigue leyendo agua libre sobre la cuerda de su tope. Con el freático a 5
  delante y a 17 detrás, eso da 196,2 kN/m con 97 dovelas, sin agua contra la cara. Es un defecto
  aparte: la profundidad del agua libre se mide sobre la cuerda del tope de una dovela que cruza un
  escalón. Arreglarlo cortando en la cara mueve el 059, así que necesita su propia ficha y su decisión.

## 1. Qué cambia

- `ogr_slip2d/slicer.py`, `_wet_faces`: el nivel se lee solo delante de la cara, una tolerancia hacia el
  lado bajo, como en `end_face_water`. La docstring dice por qué.

## 2. Tests

- `tests/test_interior_face_ponded_d468_v1519.py`: el caso sin agua delante pasa a
  `test_no_water_in_front_the_rule_does_nothing`. Sin corte y sin empuje, las dovelas son las de la
  regla apagada, bit a bit. El artefacto de la cuerda queda dicho en la cabecera, sin fijarlo en un
  test: fijarlo consagraría el defecto.
- `interior_face`, `end_face`, `lambda_closure` y `lambda_floor`, con `--jobs 4`: 51 en verde, los 20
  de antes incluidos.

## 3. Suite

La suite entera, con `--jobs 4`, tras el commit.
