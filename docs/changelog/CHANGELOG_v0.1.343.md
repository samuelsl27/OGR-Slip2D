# OGR Slip2D v0.1.343

**Los objetos de foco y el círculo de deslizamiento que guarda el proyecto bajan a la geometría del núcleo, y
el cargador del proyecto ya no importa nada de las capas de encima (D337, cuarta parte).** Cuarta versión de
la tanda P8k.

## 0. Lo que se encontró

- **Las dos últimas importaciones del motor en el cargador.** `Project.from_dict` reconstruía los objetos de
  foco desde `ogr_slip2d.focus` y los círculos del usuario desde `ogr_slip2d.surface`.
  - El módulo de foco no usaba nada del motor.
  - `SlipCircle` solo usaba una función de su módulo, `ground_y_at`.
- **La valla de `test_statistical_rebuild_v1154`** enumeraba las clases definidas en `ogr_slip2d.surface`,
  para que ningún tipo serializado se quedara sin decidir qué hace con él un cálculo estadístico.
  - Con el círculo definido en el núcleo, dejaba de ver «circle».
  - Ahora mira los dos módulos. Es un cambio deliberado: cubre lo mismo que antes.

## 1. Qué cambia

- **`ogr_core/geometry/focus.py`:** el módulo de foco, movido entero.
- **`ogr_core/geometry/slip_circle.py`:** `SlipCircle` y `ground_y_at`, palabra por palabra.
- **Reexportación:**
  - `ogr_slip2d.focus` reexporta cada nombre del módulo viejo, también los privados;
  - `ogr_slip2d.surface` reexporta `SlipCircle` y `ground_y_at`.

  Son los mismos objetos.
- **`Project.from_dict`** los importa del núcleo, y su censo queda vacío.
- **Las otras superficies** (compuesta, poligonal, de capa débil) siguen en el motor.

**Cambios deliberados en tests:**
- `test_core_layering_v1340` pierde las dos entradas;
- la valla de v1154 mira también el módulo nuevo.

## 2. Tests

- **`tests/test_focus_circle_in_core_v1343.py`** (nuevo, 5 casos):
  - **un objeto en las dos rutas:** cada nombre del módulo viejo de foco, `SlipCircle` y `ground_y_at`;
  - una superficie compuesta se sigue construyendo con el mismo círculo;
  - el pickle de un círculo y de un objeto de foco vuelve con la misma clase;
  - **un proyecto se carga en un intérprete nuevo sin ningún módulo del motor:** con objetos de foco,
    círculos del usuario, malla y campo de filtración, y devuelve lo guardado, `to_dict` por `to_dict`;
  - el censo del cargador está vacío.

**Con el código de 0.1.342 fallan los 5.** Se corrió sobre un `git archive` de 0.1.342, sin el buscador
editable.

## 3. Verificación

- **El test de esta versión**, 5/5.
- **Los vecinos:** 281 casos del foco, las superficies del usuario, las compuestas, la pureza de las
  superficies, el dibujo de la capa débil, los tres puntos, centro y radio, la reconstrucción estadística, el
  ida y vuelta del proyecto y la serialización. El único fallo fue la valla de v1154, cambiada a propósito
  (sección 0).
- **Comparación A/B, árbol contra árbol.**
  - Se corrió la misma operación sobre 0.1.342 y sobre 0.1.343: análisis y exportación DXF, con los FS
    escritos en sus textos.
  - Cuatro modelos: una rejilla de círculos con cuatro métodos, la misma con superficies compuestas, un
    objeto de foco con un círculo del usuario, y una búsqueda por caminos.
  - Resultado: las mismas entidades y los mismos FS. El modelo con foco da otros FS que el de círculos
    (1,0710 frente a 0,9946 en Bishop), así que el foco y el círculo del usuario se ejercitan.
- **Suite entera:** 6376/6376, `EXIT=0`, 72 min.
- **Banco:**
  - `verificar_cierres.py` entero: 86 comprobaciones, 0 bajadas;
  - D337, con su cuarta parte apuntada;
  - instantánea `Evaluaciones/0.1.343`, prompts y auditorías con 0 ERROR.
- **Ningún número del motor cambia:** el código se mueve palabra por palabra.

## 4. Pendiente

- **0.1.344:** las columnas de suelo y su interruptor bajan al núcleo (D337).
