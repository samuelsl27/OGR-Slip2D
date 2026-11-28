# OGR Slip2D v0.1.517

**Revisión de la tanda 0.1.512–0.1.516: el empuje del agua libre en la cara de salida (D450) se lee con
el agua que hay delante de la cara, no con la de su propia abscisa.** Es un defecto que introdujo 0.1.515
y que encontró la revisión de la tanda contra las siete reglas antes de la suite entera.

## 0. Lo que se encontró

- **El defecto, medido.** `end_face_water` leía el nivel en la x de la cara. Pero un nivel freático
  dibujado solo sobre el suelo, desde la cara hacia dentro, está definido justo ahí y en ningún sitio
  delante. Es lo que se dibuja para un freático que sale por el acantilado, una cara de rezume. Con el
  bloque de D450 y el freático de (50, 17) a (101, 17), la profundidad del agua libre en x = 49 es 0 (el
  terreno de delante está seco), y aun así la primera dovela recibía **44,145 kN/m** hacia la masa. Eso
  sube el factor, del lado inseguro, y en las dos lecturas: la de las cuñas usa la misma función.
- **Lo que no tenía el defecto:** el borde del modelo. Allí la envolvente del terreno no tiene cara
  vertical, y una superficie que acaba en el borde se rechaza (`end_below_ground`).
- **El banco no se mueve:** el agua del 092 sí está delante de su cara. El círculo publicado da
  1,041729 (`modelo.ogr`) y 1,006893 (`modelo_sin_conexion.ogr`) en el mismo proceso, igual que con
  0.1.515, así que su corrida de 0.1.515 sigue valiendo. El censo de D450 vuelve a dar las mismas 2
  caras. Ese censo lee el nivel en la propia cara, así que cuenta de más y no de menos.

## 1. Qué cambia

- `ogr_slip2d/slicer.py`, `end_face_water`: recibe `outside` (−1 en el extremo izquierdo de la masa, +1
  en el derecho), y el nivel se lee una tolerancia del modelo por fuera de la cara, con la abscisa
  dentro del terreno del modelo. Sin agua delante no hay empuje. El nivel que da la presión es ese, el
  del agua que está contra la cara.
- `_apply_end_face_water` y las cuñas (`ogr_slip2d/sarma/wedges.py`) le pasan el lado de fuera.

## 2. Tests

- `tests/test_end_face_ponded_d450_v1515.py`, un test más (`test_no_pond_in_front_of_the_face_no_thrust`):
  con el freático desde la cara, ningún empuje en el rebanador ni en las cuñas, y lo mismo en el espejo.
  Con 0.1.516 cae, porque da 44,145. Los seis de antes siguen igual: 7 en verde.

## 3. El resto de la revisión

Sin defectos en las otras reglas. Lo que se apunta y no se cambia:

- D467: la corrida deja fuera la superficie con `elevation > centre_y`, y `required_force` devuelve None
  con |brazo| < 1e-9. Entre los dos hay una franja de 1e-9·R por encima del centro en la que la corrida
  la deja fuera como «por encima del centro» y la llamada directa no le da ninguna fuerza. Las dos la
  dejan fuera.
- D456: Interpretar escucha ahora `status_message` del lienzo. Los mensajes que el lienzo ya emitía en
  sus modos (Measure, Dimension Length) salen en su barra de estado, y antes no los oía nadie.
- 0.1.513 se publicó con un test roto (`test_sarma_angle_tool_v1469`), porque el patrón de su corrida
  no incluía el área `sarma`. Se arregló en 0.1.515 y está declarado allí.

## 4. Suite

La suite entera se corre después de esta versión.
