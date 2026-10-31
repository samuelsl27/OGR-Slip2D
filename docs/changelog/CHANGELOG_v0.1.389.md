# OGR Slip2D v0.1.389

**La suma de momentos alrededor de un eje se arma con una geometría sumada una sola vez** (V10 de la fase 3 de la
auditoría del cómputo, `docs/audits/AUDITORIA_COMPUTO_v0.1.377.md`).

**Lo medido en K11** (banco 104, enjambre multimodal 50 × 50, Spencer), con una corrida por proceso nuevo y en orden
ABBA:
- de 115,8 y 117,4 s a **93,6 y 94,6 s (−19 %)**;
- las 2118 evaluaciones, idénticas en las cuatro corridas (el mismo hash de factores, iteraciones y convergencia).

Clase A: los mismos productos en el mismo orden. Lo demuestra la huella de los 23 casos, 23 de 23 idénticos a 0.1.377.

## 0. Lo que se encontró

- **La puerta de medida.** En K11, `moment_balance.moment_terms` se llama 704 399 veces, con 25 dovelas por llamada, y
  se lleva 34,7 s de 115,5. La llama la rama de momentos de Spencer y GLE en cada pasada de cada λ.
- **De todo lo que suma, solo cambian entre llamadas** el momento de las normales y el de la resistencia. Lo demás es
  fijo durante la resolución, porque la superficie, las cargas y los términos del soporte se resuelven una vez, antes
  de montar el sistema, y nadie los modifica después:
  - el marco de cada base y el signo de su cortante;
  - el momento del peso;
  - las fuerzas tangenciales activas y pasivas;
  - el sismo, el agua, la parte normal del soporte y los pares.
- **Las condiciones de los revisores del plan, cumplidas:**
  - el peso y los términos externos se suman con las mismas llamadas `moment(...)` de antes, incluidas sus componentes
    nulas, que no se simplifican;
  - el término pasivo de cada dovela se suma justo después de su cortante;
  - con `forces=None`, las cargas de cada dovela se resuelven como antes.
- **Lo que encontraron los mutantes.** El orden del término pasivo no lo veía ningún test con datos realistas: la suma
  en coma flotante no es asociativa, pero con esos valores las dos sumas coincidían. Un caso construido a mano fija ese
  orden: con la cortante primero el resultado es 0, y con el pasivo primero, 2⁻⁵³.

## 1. Qué cambia

- **`ogr_slip2d/moment_balance.py`:**
  - **`moment_geometry(...)`:** lo que no lee la iteración. Devuelve una `MomentGeometry`, que guarda por dovela
    `(x, y, tx, ty, nx, ny, signo de la cortante)`, el momento pasivo de cada dovela, el momento del peso y el
    externo;
  - **`moment_terms_at(geometry, resisting, normals)`:** las dos sumas que sí leen la iteración;
  - **`moment_terms`** conserva su firma y es las dos en fila; la siguen usando Bishop y el Ordinario.
- **`ogr_slip2d/interslice.py`:** la rama de momentos de `GLESystem` en superficies sin centro construye la geometría
  en su primera llamada y, en cada pasada, solo suma las normales y la resistencia. La construye en la primera llamada
  y no al montar el sistema para que una geometría que lance lo haga donde lanzaba la suma.
- **`tests/test_moment_geometry_v1389.py`**, nuevo: 7 tests.
- El número, en los nueve sitios, y el contador de los dos README.

## 2. Qué se probó

- **`tests/test_moment_geometry_v1389.py`:**
  - **la suma es la de 0.1.388, bit a bit.** Su `moment_terms` está copiada en el test. La nueva `moment_terms`, y
    `moment_terms_at` sobre `moment_geometry`, dan las mismas cinco sumas con dovelas en los dos sentidos, agua, sismo,
    la parte normal del soporte, pares, fuerzas tangenciales activas y pasivas (con ceros entre ellas), la rotación dada
    o no, y las fuerzas dadas o no (con dovelas reales de un talud con nivel freático y sismo);
  - **una resolución de Spencer y una de GLE en una poligonal son las de 0.1.388:** cada método, por el camino nuevo y
    con la suma entera en cada llamada (la referencia, sustituida y devuelta), en un talud con agua, sismo y un soporte
    activo y otro pasivo. Se comparan el factor, λ, las iteraciones y cada detalle;
  - **el orden del término pasivo**, con el caso construido a mano;
  - **la geometría se suma una vez por resolución** y la parte de la iteración, muchas.

  Ninguno pasa de 0,35 s.
- **Seis mutantes,** cada uno cazado:
  - el pasivo antes de la cortante;
  - sin el pasivo;
  - sin el par;
  - la rotación fija;
  - la geometría rehecha en cada llamada;
  - sin la parte normal del soporte.
- **Los tests de momentos en poligonales, de Spencer y de GLE**, juntos: 152 de 152 (`test_noncircular_moments_v1105`,
  `test_noncircular_validation_v192`, `test_moment_axis_v1126` y los de los dos métodos).
- **El banco:** la huella de los 23 casos frente a 0.1.377, 23 de 23 idénticos (`all identical`, código 0). En las
  corridas de identidad, frente a las de 0.1.388:
  - K09 (Block Search de Spencer y paseo), de 32,1 a 26,6 s;
  - K10 (Path Search y paseo), de 96,5 a 73,5 s;
  - K11, de 111,0 a 87,2 s;
  - K12 (Simulated Annealing de Spencer), de 8,4 a 6,3 s;
  - K13, que es Bishop no circular y no pasa por aquí, se queda en 57,2 s.
- **La suite entera con `--jobs 4`:** **6841 de 6841, `Failed: 0`**, sin `Leaks` ni `Chunks died`, en 26 min.

## 3. Lo que queda

- **V11–V18,** cada una con su OK. La siguiente es V11: el Bishop no circular, con el mismo memo de V6 y la geometría
  de esta versión. Antes de dar su cifra hay que contar las pasadas de K13, como pide el plan.

## Archivos

- `ogr_slip2d/moment_balance.py`
- `ogr_slip2d/interslice.py`
- `tests/test_moment_geometry_v1389.py` (nuevo)
- `docs/changelog/CHANGELOG_v0.1.389.md` (nuevo)
- `README.md`, `README.es.md`
- `pyproject.toml`, `ogr_gui/main_window.py` y los `__init__.py` de `ogr_core`, `ogr_slip2d`, `ogr_fem2d`,
  `ogr_gui`, `ogr_cli`, `ogr_api` y `ogr_mcp` (el número)
