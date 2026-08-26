# Plan técnico — Análisis de Newmark

## Enfoque

Cinco piezas, en este orden, porque cada una es entrada de la siguiente.

### A · El acelerograma

`ogr_core/loads/seismic_record.py` — `SeismicRecord`: identificador, nombre,
`dt`, la serie de aceleraciones **siempre almacenada en g**, y `pga`
calculada. Se guarda **dentro del `.ogr`** y no como ruta a un archivo
externo: un proyecto que depende de un archivo de fuera es la trampa que este
programa ya pagó una vez con los campos de filtración FEM (corregido en
0.1.78). Del orden de 60 kB por registro de 5000 muestras.

Importación de texto en los dos formatos que Jibson (1993) nombra: **pares
tiempo-aceleración** y **una sola columna a intervalo constante**. La unidad
de entrada se declara (g, cm/s², m/s²) y se convierte al entrar, para que
dentro haya una sola.

### B · El coeficiente sísmico crítico

`ogr_slip2d/yield_acceleration.py` — resuelve `FS(k_h) = objetivo`.

**Barrido ascendente desde `k = 0` y bisección en el primer cruce.** No una
bisección ciega: «crítico» es el coeficiente **más pequeño** que baja el
factor al objetivo, y `FS(k)` no está garantizada monótona en los nueve
métodos. `FS(0) ≤ objetivo` devuelve 0 —lo que la referencia documenta—; sin
cruce por debajo del techo no hay respuesta y se dice.

Engancha en `BaseSearch._analyse` (`ogr_slip2d/search.py`), la única puerta
por la que las siete búsquedas, la optimización y el muestreo probabilístico
llegan al motor. El valor viaja en `LEMResult.details["ky"]`, el hueco que
`ogr_slip2d/methods/base.py` declara para extras del método.

### C · El desplazamiento

`ogr_slip2d/newmark.py` — el esquema de Wilson y Keefer (1983) como Jibson
(1993) lo publica: mientras el bloque desliza la resistencia se toma **en el
sentido del deslizamiento**, el deslizamiento **para** cuando la velocidad
relativa deja de ser positiva, y las dos integraciones son **trapeciales**.
`g = 980,665 cm/s²` exactamente.

Cuatro polaridades —directa, invertida, media, **máximo** (por defecto)— y el
sentido cuesta arriba prohibido por defecto, que es la cuarta hipótesis que
Jibson enumera. Factor de escala del registro.

### D · El objetivo de la búsqueda

`BaseSearch` gana un objetivo único; las comparaciones que hoy dicen
`res.fos < best.fos` pasan por él y `SearchResult.critical` ordena por él. Por
defecto **es el factor de seguridad**, de modo que con los modos apagados la
salida es bit a bit la de siempre.

**El modo Newmark reutiliza el objetivo de Ky.** El desplazamiento de bloque
rígido es monótono no creciente en `a_c` porque el integrando `(a − a_c)₊` lo
es punto a punto; luego máximo desplazamiento ⟺ mínimo Ky, y el registro no
hace falta integrarlo dentro de la búsqueda: se integra una vez por superficie
al final, para informar.

Las guardas de cordura (`0.2 ≤ fos ≤ 100`) siguen siendo sobre el **factor**:
son filtros de validez, no objetivos.

### E · Interfaz

- Página *Seismic* nueva en Project Settings, con los dos interruptores donde
  la referencia los pone, y el selector de registro deshabilitado si Newmark
  está apagado —igual que la página *Transient* hace con lo suyo—.
- `Loading → Seismic Records...`, acción registrada con `_mk` y colgada en
  `_build_menus` junto a `seismic`.
- Interpret informa Ky o desplazamiento en lugar del factor cuando el modo lo
  pide.
- Traducciones, y «Newmark» a la lista blanca de identidades como nombre
  propio —igual que «Monte Carlo» e «Ito & Matsui»—, **sin subir el tope**.

## Archivos que se tocan

| Archivo | Qué cambia |
|---|---|
| `ogr_core/loads/seismic_record.py` | **nuevo** |
| `ogr_core/loads/__init__.py`, `ogr_core/project/project.py` | `Project.seismic_records`, en `to_dict`/`from_dict` |
| `ogr_core/project/settings.py` | `SeismicAnalysisSettings` |
| `ogr_slip2d/yield_acceleration.py` | **nuevo** |
| `ogr_slip2d/newmark.py` | **nuevo** |
| `ogr_slip2d/search.py` | objetivo único; Ky en `_analyse`; `critical` por objetivo |
| `ogr_slip2d/analysis_runner.py` | los dos modos y sus avisos |
| `ogr_gui/dialogs/project_settings_dialog.py` | página *Seismic* |
| `ogr_gui/dialogs/seismic_records_dialog.py` | **nuevo** |
| `ogr_gui/main_window.py` | acción + menú *Loading* |
| `ogr_gui/interpret_window.py` | informar Ky / desplazamiento |
| `ogr_gui/i18n/__init__.py`, `tests/test_i18n_coverage_v141.py` | traducciones y un nombre propio |
| `tests/test_newmark_v1127.py`, `tests/test_yield_acceleration_v1127.py` | **nuevos** |
| `docs/changelog/CHANGELOG_v0.1.127.md` | **nuevo** |
| Los siete sitios de versión | 0.1.126 → 0.1.127 |

## Contra qué se valida

Ver `spec.md`, sección *Validación numérica*. En una línea: la mitad del
desplazamiento contra la **forma cerrada de Newmark (1965)** y cuatro
identidades exactas; la mitad de Ky contra `tan(φ − β)` y contra el `k_c`
**publicado** de Loukidis, Bandini y Salgado (2003); y el conjunto contra los
tres primeros escenarios del problema 104 del banco.

## Riesgos

- **El objetivo toca las siete búsquedas.** Mitigación: por defecto es el
  factor, y el test exige salida **bit a bit** idéntica.
- **Coste**: Ky son ~8 evaluaciones donde hoy hay una. Es un modo que se pide.
  Se mide con A/B en el mismo proceso, y si los controles no separan del
  efecto, manda el razonamiento sobre el trabajo añadido.
- **`FS(k)` puede no ser monótona.** Por eso el barrido y el primer cruce.
- **La geometría del 104 es una inferencia triple.** Se publica la cadena
  entera y el escenario 2 sirve de comprobación independiente.
