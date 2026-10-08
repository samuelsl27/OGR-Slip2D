# OGR Slip2D v0.1.275

**El diálogo de propiedades hidráulicas edita la curva de usuario y `kr_min`,
y con el modelo *User Defined* Ks ES el primer punto de la curva (D271).**
Hasta esta versión, la página *User Defined* era una sola frase: la curva
solo se podía fijar desde un script o la API. Elegir *User Defined* en la
interfaz dejaba un material sin curva, es decir, kr = 1 en todo el dominio.
`kr_min`, que mueve el caudal de todo modelo con zona seca, no se veía ni se
podía cambiar.

## 0. Lo que se encontró

- **«Ks is taken from the first point of the user curve» era falso.**
  - La página lo decía y deshabilitaba el campo Ks, pero la conductividad
    salía del campo `ks`, y la curva solo normalizaba kr por su primer
    punto: k = ks·k(ψ)/k₁. Una curva cuyo primer punto no fuera `ks` no era
    la curva que el usuario había escrito.
  - El *Plot* también escalaba la curva por ese campo deshabilitado.
  - **Decisión de la propietaria:** la regla va en el núcleo. Con
    *User Defined*, Ks es el primer punto.
  - **Censo:** los 20 materiales *User Defined* del banco (19 en los scripts
    del 05 y uno en los `.ogr`) ya tenían `ks` igual al primer punto.
    Ninguna fila se mueve.
- **El campo Ks tenía 12 decimales.** Abrir el diálogo y pulsar Aceptar
  redondeaba un Ks por debajo de ~1e-10, y convertía 1e-13 en el mínimo de la
  caja, 1e-14. El banco tiene permeabilidades de 1e-13. Es el mismo defecto
  que tenía Ss en D191.
- **Un punto por debajo de kr_min·k₁ no hace nada,** porque kr se recorta a
  `kr_min`, y nadie lo decía. El dren del problema 9 cae siete décadas frente
  a las seis del suelo por defecto.
  - Esto **no** es un problema que inutilice el material: `problems()` hace
    que la API rechace el material, y habría rechazado el dren del 9. Va en
    `notices()`, un método nuevo de avisos que no bloquean.
- **Ventanas modales y textos sin traducir.**
  - El *Plot* era modal (`dlg.exec()`), en contra de AGENTS.md, y colgó la
    medida de discriminación de esta versión contra 0.1.274.
  - Los textos de *Pick*, el eje «Permeability k» y 15 de los 17 mensajes de
    `problems()` no tenían español. Pasan por `tr(variable)`, y eso el test
    de i18n no lo ve.

## 1. Qué cambia

### Núcleo (`ogr_core/hydraulic/`)

- **`HydraulicProperties.saturated_k()`**, la Ks con la que se calcula: el
  primer punto de la curva con *User Defined*, y `ks` en los demás casos.
  - Pasan por ella `principal()` (y con él la conductividad),
    `k_at_suction`, el número automático de pasos del transitorio
    (`seepage._auto_time_steps`) y la tabla de propiedades de la interfaz.
  - Interruptor `USER_KS_FROM_CURVE`, con alta en `INTERRUPTORES`,
    (0, 1, 275).
  - El campo `ks` no se toca: el viaje de ida y vuelta de un `.ogr` lo
    conserva.
- **`HydraulicProperties.notices()`** avisa de los puntos de la curva que
  quedan por debajo de kr_min·k₁.
- **`permeability_models.parse_user_curve_text`** lee el CSV de dos
  columnas. Es hermano de `parse_grid_csv_text`.

### API (`hydraulic_set`)

- Con *User Defined*, un `ks` que contradiga el primer punto se rechaza
  (`Conflict`), porque no movería nada. Uno que coincide, o ninguno, se
  sincroniza con el primer punto.
- Los avisos de `notices()` van en `notes`.

### Diálogo (`hydraulic_properties_dialog.py`)

- **La página *User Defined* tiene la tabla de la curva:**
  - succión matricial en kPa y permeabilidad en m/s, con unidades en las
    cabeceras;
  - botones + Fila, − Fila e Importar CSV…;
  - las celdas se escriben sin pérdida (`_exact_text`);
  - se ordena por succión al aceptar, y una tabla con los mismos puntos que
    la curva cargada deja la lista como estaba;
  - las filas que no son dos números se dicen en el texto de problemas.
- **El campo Ks**, con *User Defined*, enseña el primer punto y es de solo
  lectura. En todos los modelos es una caja sin pérdida (`_PreciseSpinBox`).
- **`kr_min`** va en el grupo de permeabilidad, en una caja sin pérdida, con
  una línea que explica qué hace.
- **El texto de problemas** enseña `problems()`, `notices()` y las filas
  mal escritas.
- **El *Plot*:**
  - ya no es modal;
  - dibuja los puntos de la curva sobre su interpolación;
  - escala con `saturated_k()`;
  - sus textos van con `tr()`.
- **Traducciones:** 27 claves nuevas, entre ellas todos los mensajes de
  `problems()` y `notices()`. El presupuesto de mensajes sin envolver baja de
  64 a 63 (el título «Plot»).

## 2. Tests

`tests/test_user_curve_dialog_v1275.py`, 17 casos. Con 0.1.274 fallan 16, y
el del *Plot* se cuelga en el `exec()` modal. El que pasa es el de la curva
desordenada, porque el diálogo viejo no escribía la curva.

- Tres puntos introducidos desordenados y un `kr_min`: se guardan ordenados,
  con Ks igual al primer punto.
- **Regla 7, con un permanente no saturado** (la presa rectangular de
  Gardner):
  - un punto de la curva lo mueve 0,12 m;
  - `kr_min` lo mueve 0,31 m.
- Abrir y aceptar sin tocar deja idénticos al bit:
  - una curva con 1,234567e-9 y 1e-13, y `kr_min` de 1e-12;
  - una curva desordenada;
  - un Ks de 1e-13.
- El *Plot* no es modal y dibuja la función y los puntos.
- Ks es el primer punto con *User Defined*. Con otro modelo, o con el
  interruptor apagado, es el campo.
- Todos los mensajes de `problems()` y `notices()` tienen su español.
- La API rechaza un Ks contradictorio, sincroniza el campo y avisa del
  suelo.

Falta la **prueba manual** en `python -m ogr_gui`: tres puntos y *Plot*, y un
permanente que cambia al cambiar un punto.

Suite entera: **5799 de 5799**.

## 3. Cierre en el banco

`d271()` en el `verificar_cierres.py` de la raíz exige:
- que el diálogo escriba `user_curve` y `kr_min`;
- el test (curva, `kr_min`, regla 7 y la ida y vuelta sin cambios);
- en vivo, que Ks sea el primer punto.

Veredicto: **CUBIERTO POR TEST**.
