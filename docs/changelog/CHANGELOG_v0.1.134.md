# OGR Slip2D v0.1.134

**El aviso que protegía el cambio de marco de v0.1.103 vigilaba el campo
equivocado, y por eso callaba justo en el caso más frecuente.** Un proyecto
guardado antes de v0.1.103 con el *Initial Angle at Toe* marcado en su valor
por defecto —45°— se reabría, se calculaba con ese número leído en un marco
distinto, y **no decía nada**.

Cierra **D07c(d)** del banco de verificación, el último de los cuatro que el
inventario de ajustes de v0.1.103 dejó señalados. **No mueve ningún factor de
seguridad de ningún modelo del banco**: los 142 modelos que llevan el campo
retirado lo llevan en su defecto y con los dos ángulos desactivados.

Lo que merece recordarse es que **el encargo estaba mal enunciado en sus dos
premisas comprobables**, y que el defecto real sólo apareció al mirar qué
escribía la interfaz vieja.

---

## 1 · Las dos premisas falsas del encargo

**«El valor migra tal cual, con la rama genérica».** Nunca lo hizo. La rama
genérica de `SearchSettings.from_dict` cubre exactamente tres campos
(`path_num_paths`, `auto_refine_iterations`, `auto_refine_divisions`); los
ángulos tienen su propia rama **desde el mismo commit que hizo el cambio de
marco** (`314f78a`, v0.1.103), y esa rama descarta el valor y emite una nota.
La decisión que el encargo pedía tomar —avisar en vez de convertir— llevaba
treinta y una versiones tomada, escrita con su razón y sujeta por
`test_angles_are_reported_rather_than_guessed`.

**«En el banco, ninguno tiene el campo viejo».** El `grep` del encargo sólo
miraba el primer nivel de `02_Slide2_Problema*/`. Recorriendo los 563 `.ogr`
del banco: **142 lo llevan**. La conclusión aguanta —los 142 lo llevan en su
defecto exacto `(-45.0, 45.0, False)`, y los campos supervivientes también en
el suyo— pero la cifra que la sostenía era otra.

## 2 · El defecto real: el gemelo no era el que había que vigilar

La interfaz de v0.1.102 escribía **los dos nombres desde el mismo widget**:

```python
s.path_initial_angle_at_toe_lower_deg = self._p_lower_sb.value()   # v
if self._p_lower_cb.isChecked():
    s.path_min_angle_deg = -abs(self._p_lower_sb.value())          # -|v|
```

El widget es idéntico en v0.1.102 y hoy —mismo rótulo, mismo rango −180..180,
mismo defecto 45—. Lo que cambió es qué hace el motor con ese número:

| | v0.1.102 | hoy |
|---|---|---|
| campo que lee el motor | `path_min_angle_deg` = −\|v\| | `path_initial_angle_at_toe_lower_deg` = v |
| marco | pie→cresta, directo | absoluto, convertido por `toe_frame_angle_deg` |

`toe_frame_angle_deg` no existía antes de v0.1.103. De ahí salen dos cosas que
la nota anterior no podía cubrir:

- **el gemelo no aporta información**: es el espejo negado del superviviente,
  así que el número que entra al cálculo es el del superviviente, escrito en
  el marco viejo y leído en el nuevo;
- **su defecto es el espejo del defecto de la caja**. El usuario que marcó la
  casilla y la dejó en 45 guardó el gemelo en −45, que es exactamente su
  defecto, de modo que el disparador «el gemelo se aparta de su defecto»
  **no se dispara nunca en el caso más probable**.

Medido antes de tocar nada:

```
(A) marcó Lower y tecleó 30 -> avisaba
(B) marcó Lower y tecleó 45 -> NO avisaba, y el ángulo se aplicaba
(C) no lo marcó nunca       -> no avisaba, y es lo correcto
```

Y el aviso era **de un solo uso**: `asdict` no reexporta el nombre retirado,
así que la primera vez que el usuario guardara, el gemelo desaparecía, el
número sin convertir se quedaba, y ya nada volvía a avisar.

## 3 · Cuánto costaba

Sobre `02_Slide2_Problema079/modelo_1_path.ogr` y `…081/modelo_1_path.ogr`
(Path Search, Bishop simplificado, cresta a la derecha, 2 000 superficies):

| configuración | P079 | P081 |
|---|---|---|
| tal como está guardado (Lower sin marcar) | FS 1,252166 · 391 válidas | FS 1,095438 · 848 válidas |
| archivo pre-0.1.103 reabierto: 45 leído como absoluto | **sin resultado · 0 válidas** | **sin resultado · 0 válidas** |
| el valor convertido (−45 pie→cresta) | FS 1,252166 · 391 válidas | FS 1,095438 · 848 válidas |

Y barriendo el ángulo tecleado sobre P079 (1 500 superficies), el fallo
resulta **ruidoso, no silencioso**:

| tecleado | leído como absoluto | convertido |
|---|---|---|
| 5, 10, 20, 30 | 0 válidas | 0 válidas |
| 45 | 0 válidas | FS 1,252165 · 286 válidas |
| 60 | 0 válidas | FS 1,250686 · 682 válidas |

En este modelo el valor sin convertir **nunca** produce resultado: +v queda por
encima del límite superior automático y la ventana sale vacía. El usuario ve
«sin resultado», no un número equivocado — lo cual rebaja la gravedad y **es
un argumento a favor de avisar en vez de convertir**, porque no hay ningún
número mentiroso que rescatar. Es un solo modelo, y de él no se concluye que
la ventana salga vacía en toda geometría.

## 4 · Lo que se ha cambiado

En `SearchSettings.from_dict`, el marcador de «este archivo es anterior a
v0.1.103» pasa a ser la **presencia** de cualquier gemelo retirado, nunca su
valor. Si el archivo lo trae y el ángulo del superviviente viene activado, se
avisa: ese número se leía en el marco pie→cresta y ahora es absoluto, y **no
se ha convertido**. La nota del gemelo se conserva para el caso que sí cubre
—un modelo construido por script que fijó sólo el nombre retirado y dejó el
superviviente apagado—, y se calla cuando el superviviente está encendido,
porque decir lo mismo dos veces enseña a saltarse los dos avisos.

**No se convierte nada.** La conversión sigue necesitando la dirección de
rotura, que no está en este bloque; esa parte de la decisión de v0.1.103 se
mantiene intacta.

## 5 · Dos cosas que aparecieron por el camino

- **El ángulo superior estaba muerto antes de v0.1.103.** La interfaz de
  v0.1.102 nunca escribía `path_upper_angle_enabled`, así que el motor recibía
  siempre `None`. Reabrir con v0.1.103 lo activa por primera vez: eso es la
  regla 7 arreglándose, no una regresión. Sólo el ángulo **inferior** tenía
  significado vivo que preservar.
- **La referencia convierte en silencio.** Su única página sobre abrir un
  formato anterior dice que importa todas las funciones principales y que, si
  algo falla, escribas a soporte; no documenta ningún aviso por ajuste cuyo
  significado haya cambiado. No es criterio que este proyecto tenga que
  copiar, pero era el dato que faltaba para decidir con algo delante.

## 6 · Deuda anotada, no resuelta

Ninguna cadena de `settings_warnings` tiene entrada en español, y son
`f-string`s con valores interpolados, así que el `tr(note)` del punto de uso
no podría casar ninguna clave aunque existiera. La cadena nueva sigue el mismo
camino que las demás. Resolverlo bien pide separar la parte fija de la
interpolada en todas ellas, y eso es su propio trabajo.

## 7 · Tests

`tests/test_settings_migration_v1134.py`, 10 tests. Tres de ellos fallan
contra el código anterior —comprobado retirando el cambio y volviéndolo a
poner—, incluido el central: el archivo que marcó la casilla y la dejó en 45.
