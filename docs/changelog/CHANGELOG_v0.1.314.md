# OGR Slip2D v0.1.314

**El panel de Block Search de *Surface Options* lee la coronación del modelo
en que se abre (D305).** Segunda versión de la tanda P8g.

## 0. Lo que se encontró

- **El fallo.** `SurfaceOptionsDialog._build_block_panel` llamaba a
  `model_crest_is_on_the_right(project)` con `project`, un nombre que ese
  método no tiene. Cada llamada lanzaba `NameError`, y un `except Exception`
  lo convertía en «coronación a la derecha», fuera cual fuera el talud.
- **Qué decidía.** Solo el texto de la nota bajo los ángulos de proyección
  (`rules.block_angle_notes`), que dice qué límites de la referencia se salen.
  A un talud con la coronación a la izquierda se le decían los límites del
  otro lado: un ángulo admisible salía señalado y uno inadmisible no. Lo que
  guarda el diálogo nunca dependió de esto.
- **El demo es justo ese caso.** Su terreno está más alto a la izquierda
  (y = 25 en x = 0 y 15 en x = 50), así que su coronación está a la IZQUIERDA
  por geometría, aunque la dirección declarada sea de derecha a izquierda.
  Su reflejo respecto a x = 25 sirve de control.
- **El `except` sobraba.** Con un proyecto sin contorno exterior,
  `model_crest_is_on_the_right` ya cae a la dirección declarada.

## 1. Qué cambia

**Decisión de la propietaria (2026-10-14): quitar el `except`.**

- `model_crest_is_on_the_right(self.project)`, sin `try/except`. El
  comentario dice por qué ya no hace falta.

## 2. Tests

`tests/test_block_panel_crest_v1314.py`, 6 casos:

- **la premisa, medida:** el demo tiene la coronación a la izquierda y su
  reflejo a la derecha;
- **coronación a la izquierda** (el demo, con una proyección izquierda de 200° a
  220° y una derecha de −60° a −30°): la nota habla solo de la izquierda, que
  se sale de 95°–175°;
- **coronación a la derecha** (el reflejo): la nota habla solo de la derecha,
  que se sale de 5°–85°;
- **la nota es la de `block_angle_notes`** para la coronación del modelo;
- **un proyecto sin contorno exterior**, con la dirección declarada de
  izquierda a derecha, abre el diálogo y toma la coronación a la izquierda;
- **Aceptar sin tocar nada** escribe los ajustes que encontró, en los dos
  taludes (QUÉ NO SE PUEDE MOVER).

**Con el código de 0.1.313 fallan 3 de los 6:** la coronación a la izquierda,
la nota del demo y el proyecto sin contorno con la dirección declarada de
izquierda a derecha. El caso del proyecto vacío pasaba en el primer borrador
por casualidad, porque la dirección declarada por defecto también da
«derecha». Ahora declara la contraria para que vigile algo.

Los tres que pasan en los dos árboles son controles: la coronación a la
derecha (el código viejo siempre decía «derecha»), lo que guarda Aceptar y la
premisa.

Se corrió sobre una copia del árbol de 0.1.313 sin el buscador editable.

## 3. Verificación

- **Suite entera:** 6095/6095, código de salida 0, a la primera (52 min).
- **Banco:** `d305()` en el `verificar_cierres.py` de la raíz: **CUBIERTO POR
  TEST**. Ciclo de cierre:
  - `verificar_cierres.py` entero: 56 comprobaciones, 0 bajadas;
  - instantánea `Evaluaciones/0.1.314` antes y después (`--forzar`);
  - `retirar_cerrados.py --escribir D305`;
  - poda de la lista P8 y D305 tachada en la fila P8;
  - `generar_prompts.py`: 37 prompts y las mismas 19 FALTA;
  - `auditoria_invariantes.py` en la raíz y en el 02, con 0 ERROR.
- **Los tests vecinos**, antes de la suite: 363/363. Son Block Search,
  rejillas, *Surface Options*, la optimización y deshacer de ajustes.
- **Ningún número cambia:** la nota es texto, y lo guardado no dependía del
  valor.

## 4. Pendiente

- A mano: la nota de Block Search con el talud de ejemplo, que tiene la
  coronación a la izquierda.
