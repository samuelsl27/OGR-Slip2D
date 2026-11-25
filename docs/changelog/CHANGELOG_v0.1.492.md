# OGR Slip2D v0.1.492

**El núcleo fijado sube de `ogr-core` 0.2.10 a 0.2.12, y con eso quedan cerradas D429 y D431.**
`pyproject.toml` fija ahora `ogr-core @ git+https://github.com/samuelsl27/OGR-Core@v0.2.12`. Es
una etiqueta anotada, `b1fb233` → `5281b92`, comprobada con `git ls-remote`. El `.venv` la tiene
instalada con `--no-deps --force-reinstall`.

- **0.2.11 (D429).** Un `.ogr` con un valor que esta versión no conoce, un peso que no es número o
  un nombre de material que no es texto se rechaza al abrirlo, con su código, en vez de abrirse
  con otro valor.
- **0.2.12 (D431).** Un patrón de tests que no casa con ningún archivo hace salir al runner con 2,
  aunque otros patrones casen.

La sesión de OGR-Core propuso saltar directamente a la 0.2.12.

`git diff --stat v0.2.10 v0.2.12 -- ogr_core` toca 8 archivos:

| Versión | Qué es | Para Slip2D |
|---|---|---|
| 0.2.11 | `file_messages.py`: los códigos `file.value_unknown` y `file.field_type`. `read_enum` en `_model_from_dict` y en `SeismicRecord.from_dict`. La envolvente y la interpolación, con su lista de valores. `file_shape.ITEM_FIELDS`, con `name`, `unit_weight` y `sat_unit_weight` | Seis rechazos al abrir (§1) |
| 0.2.12 | `testing/runner.py`: `unmatched_patterns` | El contrato de AGENTS.md («un patrón que no case con nada sale con código 2») se cumple también con varios patrones |

## 0. Lo que se encontró

- **Medido con 0.2.12.**
  - Los seis casos de D429 que son del núcleo se rechazan al abrir:
    - `model = "future_model"` y `source_unit = "furlongs"` con `file.enum_unknown`;
    - `drawdown_envelope.kind = "future"` e `interpolation = "kriging"` con `file.value_unknown`
      («Known: r, kc1» y «Known: tps, idw»);
    - `unit_weight = "x"` y `name = 5` o `null` con `file.field_type`.
  - Lo que falta sigue migrando igual: sin `model`, sin `interpolation`, sin `source_unit` y sin
    `drawdown_envelope`.
  - Los dos del motor, búsqueda y muestreo, los rechaza `check_analysis_settings` desde la
    0.1.491.
- **D431, con su REPRODÚCELO.**
  - `--list transient zz_no_casa_d431` da `EXIT=2` y «No test file matches ['zz_no_casa_d431'] —
    the other pattern(s) select 5 file(s); nothing was run.».
  - Sin `--list` (`cli_unreadable zz_no_casa_d431`), también `EXIT=2`, y no sale «Total:», así
    que no se ha corrido nada.
  - El patrón muerto solo sigue dando 2.
- **El paso intermedio, `c6ba3be`, ya probaba los dos núcleos.** Con la fijación en 0.2.12, sus
  ramas por versión ya no tienen sentido y se quitan. Un núcleo que vuelva a tolerar un valor
  desconocido es ahora un fallo, también con `--dev-core`.
- **Censo del banco**: 0 de 30 800 `.ogr` con alguno de estos valores (2026-11-24). Ningún `.ogr`
  válido cambia.

## 1. Qué cambia

- `pyproject.toml`: la fijación, con su comentario.
- `AGENTS.md`: la fijación y la cabecera del runner (`shared: ogr_core 0.2.12 …`). Sigue en 503
  líneas.
- `tests/test_import_messages_v1437.py`: `_TOLERANT` queda vacío sin alternativa y el censo vuelve
  a exigir `read == set(ENUM_NAMES)`. Fuera `_TOLERANT_UP_TO_0210` y `_tolerated`.
- `tests/test_ogr_open_refusals_v1438.py`: `peso_cadena` sale de `_UNCHANGED`. Se exige que
  `project_open` y `properties_import` lo rechacen con la frase de `file.field_type`. Fuera
  `_core_refuses_d429` y `_unchanged`.
- `tests/test_open_unknown_values_v1492.py` (nuevo, 8 tests). El fragmento de D429, con estos
  casos:
  - los seis rechazos al abrir, con su código;
  - el nombre `null`;
  - los textos nombran los valores conocidos, que son la referencia;
  - lo que falta migra igual;
  - todos los valores conocidos abren;
  - la búsqueda y el muestreo los rechaza `check_analysis_settings`;
  - el agente recibe el peso `"x"` como `InvalidArgument` de `project_open`.
- La versión, en siete sitios.

## 2. Qué se probó

- Por áreas, contra 0.2.12: `open_unknown_values`, `import_messages`, `ogr_open_refusals`,
  `setting_refusals` y `version_consistency`, en verde. Solo faltaba este changelog.
- La suite entera con `--jobs 4` (`shared: ogr_core 0.2.12`): 7604 casos, 7602 pasan, 0 fallan,
  2 saltados, sin fugas ni tramos muertos.
- `d429()` y `d431()` en el `verificar_cierres.py` de la raíz del banco (fuera de git), registradas
  en `COMPROBACIONES`: las dos CUBIERTO POR TEST. D429, D430 y D431 cerradas.

## 3. Pendiente

- **En OGR-Core:** la fila de Slip2D en `docs/consumidores.md` pasa a v0.2.12, desde esta versión.
  Si no, su CI de fijaciones sale en rojo.
- **Del changelog 0.2.12 del núcleo, sin decidir:** un `-k` que solo casa en algunos de los
  archivos seleccionados deja entrar los demás sin decir nada.
