# OGR Slip2D v0.1.199

**Tercer bloque de correcciones antes de F3: las cargas puntuales normales o
con ángulo respecto al contorno ya empujan en esa dirección.** Hasta esta
versión:

- `LineLoad.direction_vector` no tenía rama para esas dos orientaciones y
  las aplicaba **en vertical, en silencio**;
- la interfaz las ofrecía;
- la capa de operaciones las rechazaba desde v0.1.196.

Ningún modelo guardado cambia de número. De los 265 modelos vivos
(validación, ejemplos y el banco con los manuales 02–07), ninguna carga
puntual usa esas orientaciones: las cuatro que hay son verticales.

---

## 1. El convenio

La documentación de referencia no lo define: dice «normal al contorno» y
admite que el sentido puede salir 180° al revés. El convenio lo decidió el
propietario (2026-09-24).

- **Normal al contorno:** normal a la **superficie del terreno** en el punto
  de la carga (`ground.ground_surface`), apuntando **hacia el terreno**.
  - La tangente del perfil, recorrido de izquierda a derecha, girada 90° en
    sentido horario apunta hacia dentro en cualquier tramo: hacia abajo bajo
    una coronación plana, ladera abajo y hacia dentro en una cara, hacia el
    muro en un escalón vertical.
  - En un **vértice**, la bisectriz de las dos normales vecinas.
- **Ángulo al contorno:** la tangente del terreno (izquierda → derecha)
  girada `angle_deg` en sentido antihorario. **−90° es la normal hacia el
  terreno** y +90° la normal hacia fuera. Es el mismo convenio que el de la
  carga repartida dibujada de izquierda a derecha.
- **Solo sobre el terreno.** Un punto a más del 0,1 % del modelo del perfil
  no tiene contorno al que ser normal. Lo rechazan:
  - la operación del agente (`Conflict`, con el motivo);
  - el cálculo (`check_analysis_settings` nombra la carga);
  - la interfaz, que no la añade y lo dice en la barra de estado.
- **La dirección se calcula** en cada uso y no se guarda al colocar la
  carga, así que sigue a la cara si esta cambia.

## 2. Una sola puerta

`ogr_core.loads.loads.line_load_direction(project, load)` resuelve la
dirección de una carga puntual. Pasan por ella:

- el rebanador (`_line_load_components`);
- el exceso de presión intersticial;
- la imagen PNG del agente;
- el lienzo, que recibe el perfil una vez por redibujado;
- el exportador DXF.

**El exportador DXF** además deja de dibujar las flechas con
`angle_deg or 270`. Esto estaba reportado en v0.1.196: una carga horizontal,
una normal o una a 0° salían verticales. Ahora cada flecha, puntual o
repartida, sigue su dirección.

**Arreglos de texto:**

- el comentario de `DistributedLoad.direction_vector` decía «hacia dentro
  del talud, suponiendo un contorno antihorario». Es falso: la parte de
  arriba de un exterior antihorario va de derecha a izquierda y sus aristas,
  así giradas, apuntan hacia fuera. Solo apunta hacia dentro con la carga
  dibujada de izquierda a derecha, que es lo que la operación del agente ya
  avisaba;
- el tooltip del ángulo en el diálogo de la interfaz explica el convenio y
  pasa por `tr()`.

## 3. Lo que se midió (regla 1)

Se usó la cuña de Coulomb de `test_janbu_wedge_v1142`: cara a 56,3°,
c′ = 5 kPa, φ′ = 30°, γ = 18 kN/m³. Se le pusieron 100 kN/m normales a la
cara en (34, 6). La forma cerrada es:

F = [c′L + (W cos α + N_P) tan φ′] / (W sin α + D_P)

Las componentes N_P y D_P salen de los **vértices del fixture**,
(12, −8)/√208, y no de `direction_vector`.

| Métodos | 35° | 40° | 45° |
|---|---|---|---|
| Janbu (simplificado y corregido), Corps 1 y 2, Lowe-Karafiath | ≤ 2,2e-7 | 2,4e-7 | 4,3e-7 |
| Spencer, GLE | −7,5e-4 / −1,0e-3 | 2,4e-7 | 4,3e-7 |
| Fellenius | −2,4e-2 | −2,9e-2 | −3,4e-2 |
| Bishop | −5,8e-3 | +3,5e-4 | +1,8e-2 |

- **Los métodos de equilibrio de fuerzas** llegan a la forma cerrada al
  redondeo.
- **Spencer y GLE a 35°:** su búsqueda de λ **cae en el camino de reserva**
  (`lambda_search_fell_back`, residuo 1,8e-3, 7 valores de λ perdidos por
  desbordamiento del empuje). Es la familia de D148 documentada en
  `test_anchored_wedge_root_v1177`, no la carga: se reporta y no se afirma.
- **Fellenius y Bishop** no están ligados a esta forma cerrada. La
  componente horizontal actúa a la cota de la carga, por encima de la base,
  y añade un par.
- **Identidades exactas:** normal = `angle_to_boundary(−90°)` =
  `angle_from_horizontal(atan2(−8, 12))` dan números idénticos, y la carga
  vertical da su propia forma cerrada con d = (0, −1).

## 4. Reportado, sin corregir (regla 6)

Mueve números, pero ningún modelo guardado lo ejerce: medido que ninguno
combina cargas con sismo activo.

- **kh y kv actúan sobre la componente vertical de las cargas.** Se suma al
  peso de la dovela y `slice_forces` multiplica ese peso. La referencia
  define la fuerza sísmica sobre el área por el peso específico, y
  `excess_pore_pressure` afirma lo contrario de lo que hace el motor.
- **Se pierde un par.** Si en una misma dovela hay dos fuerzas horizontales
  opuestas, `moment_balance` salta el momento cuando su suma es cero, aunque
  formen un par.
- **Una carga repartida hacia arriba cuenta hacia abajo.**
  `_surface_pressure_at` usa `abs(p·dy)`.

## 5. Tests

**`test_line_load_boundary_v1199.py`, 8 casos:**

- **La forma cerrada** en los métodos de fuerzas, a 35°, 40° y 45°, y
  Spencer/GLE a 40° y 45°.
- **La normal no es la vertical de antes:** otro número, y la vertical
  cumple su propia forma cerrada (regla 7).
- **Identidades:**
  - las tres formas de decir la normal;
  - +90° = normal hacia fuera;
  - la normal en la coronación plana es la vertical;
  - la bisectriz en el vértice de coronación, en forma cerrada;
  - el escalón vertical apunta hacia el muro;
  - el talud en espejo da la normal en espejo.
- **Rechazos** de la operación, del cálculo y de la interfaz.
- **La flecha DXF de una carga horizontal** es horizontal.

**`test_f2_ops_v1196.py`:** los dos intentos que fijaban el rechazo pasan a
un punto fuera del terreno, donde se sigue rechazando.

## 6. Verificación

- Tests dirigidos (bloque 3, operaciones de F2, cargas, DXF): 82/82.
- Suite entera y sin argumentos: **4437/4437**, sin aviso FILTERED RUN,
  con los siete paquetes medidos de este árbol. Tardó 32 min
  (15:41 → 16:13); v0.1.198 traía 4429, y los +8 son el archivo nuevo.

## 7. Qué falta

- F3a (v0.1.200): agua subterránea para el agente y la corrección de
  unidades hidráulicas.
- F3b (v0.1.201): estadística, sensibilidad, retroanálisis, optimización e
  interpretación.
