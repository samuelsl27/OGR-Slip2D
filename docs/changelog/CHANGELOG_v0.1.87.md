# OGR Slip2D v0.1.87 — el panel de dovelas enseñaba guiones donde la referencia imprime números

Último punto del informe del Ejemplo 2. Con el clic ya arreglado en
v0.1.86, el panel *Query Slice Data* se abre y se rellena — y entonces se
ve lo que le faltaba.

**Ningún cálculo cambia.** Lo que cambia es qué se puede leer de él.

---

## 1 · Cuatro guiones que eran estructurales

El panel listaba fuerza normal en la base, fuerza cortante, resistencia al
corte y tensión normal efectiva, y ponía **«—»** en las cuatro. No era un
cálculo pendiente: **esas magnitudes no son atributos de la dovela**. Las
calcula el método y las guarda en el `LEMResult`, en arrays por dovela:

```
base_normal          len=14
base_shear_force     len=14
base_shear_strength  len=14
```

`show_slice(s)` recibía **solo la dovela**, así que no podía llegar a
ellas. Los guiones eran una consecuencia de la firma, no del solver.

Ahora recibe también el resultado. El panel pasa de 4 campos vacíos a
ninguno.

## 2 · Y una definición que me equivoqué en poner

Al llenar los campos, el primer intento etiquetó `base_shear_force / l`
como «cortante movilizado». Es **falso**: en `bishop.py` ese array es

```python
shears.append(slide_sign * W_eff * math.sin(alpha))
```

o sea `W·sen α`, la fuerza que **empuja** la dovela. Lo destapó que el
número no cuadrara: daba τ_m = 72,25 donde τ_f/F pedía 64,7.

La tabla de la referencia lo zanja. Fila 1 del mínimo global de Ej_2:

```
Shear Strength = 31,082    Shear Stress = 27,8907    FS = 1,11442
31,082 / 1,11442 = 27,8907
```

El *Shear Stress* de la referencia es **τ_f / F**. Se diferencia del
cortante motor exactamente en el factor de seguridad, que es justo lo que
el número significa. Las dos magnitudes se informan ahora por separado y
con su nombre.

Es la moraleja de la regla 1 en pequeño: el campo *parecía* correcto, y lo
único que lo delató fue contrastarlo con un valor externo.

## 3 · Validado contra la tabla de la referencia

No contra lo que imprime el código hoy. Fila 1 de la Slice Data del mínimo
global de Ej_2 (ordinary/fellenius):

| campo | OGR | Slide | dif |
|---|---|---|---|
| Ancho b | 1,047 | 1,04705 | −0,00 % |
| Peso W | 9,40 | 9,40306 | −0,03 % |
| Cohesión en la base | 26,0 | 26 | 0 |
| Ángulo de rozamiento | 30,0 | 30 | 0 |
| Resistencia τ_f | 31,08 | 31,082 | −0,01 % |
| Cortante movilizado τ_m | 27,90 | 27,8907 | +0,03 % |
| Tensión normal σₙ | 8,80 | 8,80223 | −0,03 % |
| Normal efectiva σ′ₙ | 8,80 | 8,80223 | −0,03 % |

Y hay un test que comprueba, dovela a dovela, que
`τ_f = c + σ′ₙ·tan φ` con los parámetros **de la base**, que es donde se
evalúa la resistencia.

## 4 · Las dos columnas que faltaban

La referencia informa *Base Cohesion* y *Base Friction Angle*. No estaban.
Se leen de `strength.params`, no con `getattr(strength, "cohesion")`, que
devuelve `None` y parece un dato ausente en vez de una consulta mal hecha.

## 5 · La dovela seleccionada se dibuja

Como documenta la referencia: «Click on any slice, and the data for the
slice will be displayed in the dialog. Force arrows will also be displayed
on the slice». Cuerpo resaltado y tres flechas — peso, normal en la base y
cortante en la base.

Las flechas se escalan contra **la mayor fuerza de esa dovela**, no contra
una longitud absoluta: una dovela de 9 kN en el pie y otra de 300 kN a
media altura tienen que leerse las dos. Es un diagrama de direcciones y
proporciones; los números están en el panel de al lado.

## 6 · Show Slices se aplica a todas las Query

La referencia es explícita:

> Show Slices operates on a per view basis, and **applies to ALL QUERIES IN
> THE CURRENT VIEW**, if more than one Query exists in a given view.

Se dibujaban las dovelas de **una sola** superficie. Con v0.1.86
permitiendo fijar varias, la opción contradecía a la función de la que
depende. El clic sobre una dovela busca ahora en todas las Query, y decide
por distancia vertical cuando dos se solapan en x.

## 7 · Regla 2 y un aviso de consola

Las ~24 etiquetas del panel, su título y sus cabeceras estaban en inglés
crudo. Todas pasan por `tr()` y tienen su entrada en español. `Material` y
`─ Material ─` se traducen a sí mismas y están en la lista permitida del
test de i18n: es cognado exacto, y «traducirlo» sería inventar una
diferencia.

De paso, `_query_slice` desconectaba una señal antes de conectarla y se
tragaba el fallo, lo que imprimía un aviso `libpyside: Failed to
disconnect` en cada primer uso porque no había nada conectado todavía. Una
bandera dice lo que el `try/except` intentaba preguntar.

---

## Verificación

`tests/test_interpret_slice_data_v187.py`, 11 casos:

- **todas las columnas de la referencia coinciden** con su tabla al 0,5 %;
- τ_m es τ_f/F y **no** es W·senα — la definición que fallé;
- τ_f sigue Mohr-Coulomb con los parámetros de la base, dovela a dovela;
- tras pulsar una dovela **ningún campo queda en «—»**;
- pulsar otra actualiza; solo hay una resaltada a la vez; hay flechas;
- pulsar fuera no cambia nada;
- dos Query dibujan los dos juegos de dovelas, y sin ninguna Query sigue
  funcionando el atajo documentado del mínimo global;
- toda etiqueta del panel tiene entrada en español.

Suite completa, sin argumentos.
