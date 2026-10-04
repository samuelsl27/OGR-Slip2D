# OGR Slip2D v0.1.253

**D253: una grieta de tracción termina cada superficie analizada donde ESA
superficie corta la línea de grieta, también cuando una capa débil la ha
recortado.** Hasta 0.1.252, la superficie recortada heredaba la pared de la
superficie de la que salía, y el rebanador la daba por decidida. El resultado
quedaba del lado inseguro, y en las poligonales dependía del orden en que se
evaluaban los casos.

Cuarta versión de la tanda Help + D85, D251/D252, D253, D97, D128 y D131. La
propietaria pidió (2026-10-03) investigarlo en la documentación y analizarlo
en lo matemático, lo físico y lo geotécnico antes de corregir.

## 0. Lo que se encontró

### Dos defectos con una sola causa

Modelo de medida: el talud plano de `test_weak_layer_v1121` (junta de (2, 2)
a (30, 10), con c = 5 y φ = 20), una línea de grieta horizontal en y = 8,5,
Fellenius y 40 dovelas. La junta corta la línea de grieta en x = 24,75.

- **Base poligonal** (la ficha): (2, 2)–(16, 1)–(30, 10).
  - Con «auto_cases» se rebana primero el caso 0, la masa sin junta, y el
    rebanador la trunca en su sitio, en x = 27,67, y le escribe la pared.
  - Los casos con junta son `WeakLayerSurface` sobre esa misma base, y
    heredaban la pared de 27,67.
  - Con «highest» no hay caso 0, y la superficie decide la suya, en 24,75.
  - Resultado, el mismo mecanismo con dos factores: 1,5401 frente a 1,5166
    con la grieta llena (+1,55 %), y 1,5805 frente a 1,5570 seca (+1,51 %).
- **Base circular** (nuevo, medido al corregir). La ficha decía «con círculos
  no pasa» porque el círculo seguía la regla escrita. Pero la regla escrita
  era justo lo que fallaba.
  - Con el círculo de centro (8, 34) y R = √1060, que pasa bajo la junta en
    todo su tramo, la búsqueda trunca el círculo por la grieta antes de mirar
    ninguna capa débil, en x = 28,24, donde ÉL corta la línea.
  - La superficie recortada heredaba esa pared. Entre 24,75 y 28,24 iba por
    la junta POR ENCIMA de la línea de grieta, dentro de la zona agrietada y
    contando resistencia. Y su pared empezaba en y = 8,5, por debajo de su
    propio extremo (9,50).
  - Resultado, en los dos modos: 1,5861 en seco frente a 1,5570 (+1,87 %), y
    1,5455 con la grieta llena frente a 1,5166 (+1,90 %).

### Por qué la regla es la de cada superficie

Ninguna fuente da el orden de forma explícita; se deduce de las definiciones.

- **Documentación técnica:**
  - Duncan, Wright y Brandon (2014), *Soil Strength and Slope Stability*, 2.ª
    ed., p. 15: «once the soil is cracked, all strength on the plane of the
    crack is lost»; y en la p. 236, la superficie termina en la profundidad
    de la grieta;
  - USACE EM 1110-2-1902 (2003), p. 1-4: «shear resistance along tension
    cracks should be ignored»; y en la p. C-36, la superficie se termina
    donde alcanza la cota del fondo de la grieta.
- **La referencia comercial** dice lo mismo con sus definiciones:
  - la grieta se forma donde la superficie de rotura corta el contorno de
    grieta;
  - el extremo de la superficie es su intersección con ese contorno;
  - el agua se mide desde él;
  - y la capa débil recorta la superficie de rotura.
- **La regla vieja** (la grieta se decide sobre la masa antes de recortar)
  solo estaba en un comentario de `surface.py`, sin fuente.
- **En lo matemático:** la superficie recortada es
  `max(base, junta) ≥ base`. Desde la coronación, corta la línea de grieta
  antes que su base, o en el mismo punto, así que su propio corte cae dentro
  del tramo que hereda, y el rebanador lo encuentra ahí.
- **En lo físico y geotécnico:** por encima de la línea de grieta el suelo
  está agrietado y no hay resistencia al corte. La pared es la cara vertical
  de la masa en su propio extremo, y el agua de la grieta empuja ½·γw·h² con
  h medida desde el fondo de la grieta donde la superficie termina.
- **La grieta por curvatura inversa sigue siendo del círculo.** Es seca y
  automática, y es una propiedad del arco que genera la masa (donde se da la
  vuelta), no del contorno de grieta.

### El orden de evaluación, un segundo defecto

Con la herencia corregida, la poligonal con grieta llena aún daba 1,51671 con
«auto_cases» frente a 1,51662 con «highest». La causa:

- `WeakLayerSurface.moment_axis` delega en la base;
- la base es la poligonal que el caso 0 había truncado en su sitio;
- y el eje construido de una poligonal sale de sus extremos.

El caso 0 movía el eje con el que se toma el momento del empuje del agua.
Ahora el caso 0 se analiza sobre una copia (`weak_layers._own_copy`, con
`dataclasses.replace` y los mismos identificadores). Es la misma manera con
la que `_candidate_surfaces` protege ya un círculo con nombre.

**Una coincidencia que conviene saber.** Con la grieta llena, el círculo y la
poligonal dan el mismo factor a todos los dígitos. No es casualidad: el eje
construido de la poligonal (el punto medio de sus extremos más la
perpendicular) es (16 − 8, 6 + 28) = (8, 34), el centro del círculo.

## 1. Los cambios

- **`WeakLayerSurface.__post_init__`** (`ogr_slip2d/surface.py`):
  - hereda de la base la curvatura inversa (en `tension_cracks`);
  - ya no hereda la pared de la grieta del usuario (`tension_crack_wall` ni
    su tupla en `tension_cracks`).
  - El comentario cita las fuentes y la medida.
- **`weak_layers.weak_layer_variants`:** el caso 0 de «auto_cases» se entrega
  como copia propia (`_own_copy`). Copia lo que el rebanador cambia: el
  objeto poligonal, cuya lista reasigna, y la lista de grietas, a la que
  añade.

## 2. Tests

**`tests/test_weak_layer_tension_crack_v1253.py`**, 8 casos.
- **La forma cerrada, en seco** (Hoek y Bray 1981, rotura plana con grieta en
  la coronación). Con la base poligonal y con la circular, y con los dos
  modos:
  - superficie de capa débil, con la pared en 24,75;
  - F igual a la forma cerrada a 1e-12, con el área a mano
    (80 − ½(30 − x_w)(10 − y_c) = 76,0625 m²).
  - Con la línea de grieta en y = 8, la pared en 23 y el bloque de 73 m².
  - Una segunda pasada conserva su pared.
- **Con agua en la grieta**, los cuatro caminos dan un solo número, por debajo
  de la forma cerrada seca.
- **El caso 0:** rebanarlo no toca la base compartida, y es la misma
  superficie (los mismos identificadores y el mismo factor que la poligonal
  sola).
- **La curvatura inversa** se hereda, y solo la pared del usuario no.

**Discriminación** contra 0.1.252, con el envoltorio sin buscador editable:
**6 de 8 fallan**. Pasan los dos controles: la segunda pasada y «la misma
superficie».

## 3. El banco

- **Censo** de los 230 modelos (02 y 03–07): 1 con capa débil (el 109, con
  tres juntas), 19 con grieta y **ninguno con las dos**. Sin grieta, rebanar
  el caso desnudo no lo trunca, así que la copia tampoco cambia nada.
- **A/B árbol contra árbol de todo el 02** (`_auditoria/P5_0253/ab_d253.py`,
  e3f7976 frente a este): 194 modelos, **0 de 1821** números reales
  distintos.
- **La medida del caso circular, archivada**
  (`mide_grieta_circulo_d253.py`): con 0.1.252 las ocho rutas dan seis
  factores distintos; con 0.1.253, dos.
- **`d253()`**, en vivo sobre el modelo archivado:
  - las ocho rutas con la pared en 24,75;
  - en seco, la forma cerrada a 1e-12;
  - con agua, un solo número;
  - el caso desnudo, rebanado aparte con la base intacta;
  - y el A/B y la discriminación archivados.

  Veredicto CUBIERTO POR TEST. Con el árbol de 0.1.252 da NO SE SOSTIENE, por
  las paredes heredadas en 28,24 y 27,67.
- **Verificación entera:** 223 cierres y 0 bajadas.
- **Cierre del ciclo:**
  - instantánea 0.1.253;
  - a la ficha se le añadió, antes de retirarla, la corrección de «con
    círculos no pasa»;
  - D253 retirada (217 cerradas);
  - `PAQUETES` de P5 podado y la cadena tachada;
  - prompts regenerados;
  - auditorías del 02 y de la raíz con 0 ERROR;
  - instantánea con `--forzar`;
  - `--seco` completo tras retirar: 223 claves, iguales al JSON clave a clave.

## 4. Verificación

- **Suite entera:** 5566 de 5566.
- **Selección** de capas débiles, grietas, estadística, probabilística,
  compuestas, curvatura inversa y rebanador: 264 de 264 (17 archivos).
- **Discriminación:** 6 de 8 contra 0.1.252.

**Qué falta por probar:**
- Un modelo real con capa débil y grieta (no hay ninguno en el banco).
- Lo que deje en la superficie la grieta por curvatura inversa de un círculo
  cuyo recorte acaba antes: se sigue dibujando en su sitio, como antes con
  los círculos que trunca la grieta del usuario.
