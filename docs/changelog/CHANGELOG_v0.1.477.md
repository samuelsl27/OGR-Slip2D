# OGR Slip2D v0.1.477

**Solo vive `main`.** La propietaria ha decidido que en cada repositorio de la suite viva una sola
rama, `main`, que lo integra todo, y para esto levanta su regla de «nada de borrar ramas». Es lo
último del prompt 2 de OGR-Core («un solo OGR-Core»), después de la 0.1.476 (la CI de Linux en
verde). Sin cambios de programa: un comentario del lienzo, dos documentos de la spec 010 y la regla
en `AGENTS.md` y `CONTRIBUTING.md`.

## 0. Lo que se encontró

- **Las puntas eran las del prompt** (medido el 2026-11-21 tras `git fetch --prune`):
  `dev/adoptar-ogr-core` `dbc316c` entera en `main`; `dev/extraer-ogr-core` `84e2dea`, 3 commits
  propios (la spec 009 y F1, `2d68c29`); `dev/d370-shutdown` `7d88eb1`, 5 propios;
  `ensayo/envoltorio` `c7110e7`, 5 propios; `ensayo/trial` `478c736`, 4, todos dentro de
  `ensayo/envoltorio`. No había ninguna etiqueta en el repositorio.
- **Una cita más de las tres que daba el prompt.** Un comentario de código,
  `ogr_gui/canvas/canvas_view.py` (D395, la medida de `setPen`), mandaba a la sonda
  `tests/_d370_none.py` «at commit 739885e of branch dev/d370-shutdown». Ese commit no está en
  `main`: tras el borrado solo lo alcanza la etiqueta, y el comentario ahora la nombra.
- **Una memoria de la sesión, superada**: la que decía que `dev/extraer-ogr-core` no se borra ni
  se integra (de antes de la spec 010). La decisión de hoy la sustituye.
- **Las demás menciones de ramas no se tocan.** Los changelogs 0.1.422, 0.1.472 y 0.1.473 y el
  `plan.md` y el `tasks.md` de la spec 010 cuentan lo que pasó entonces. En particular,
  `CHANGELOG_v0.1.473.md` dice que F1 está «en la rama `dev/extraer-ogr-core`, que no se toca»:
  era verdad entonces, y por decisión de la propietaria se anota aquí en vez de corregirse allí.
  **Desde esta versión, F1 y la spec 009 viven en la etiqueta `archivo/dev-extraer-ogr-core`.**
- **El tope de 500 líneas de `AGENTS.md`** (499 antes): la regla nueva ocupa tres, y para pagarlas
  se compactaron el primer punto de la sección, el de la fijación y el párrafo de `--dev-core`, sin
  quitar ningún dato. Queda en 499.

## 1. Las etiquetas

Anotadas, cada una con un mensaje que dice qué conserva y por qué, subidas por su nombre (no con
`--tags`) y comprobadas en GitHub con `git ls-remote` (su `^{}` es la punta de la rama). El
disparador de la CI es `tags: ["v*"]`: no lanzan ninguna corrida.

| Etiqueta | Objeto | Apunta a | Conserva |
|---|---|---|---|
| `archivo/dev-extraer-ogr-core` | `baed6c7` | `84e2dea` | spec 009 (`spec.md`, `plan.md`, `tasks.md`, `censo.md`, `changelog_F1.md`) y F1 |
| `archivo/dev-d370-shutdown` | `dc590b3` | `7d88eb1` | las sondas de D370; el arreglo entró como v0.1.422 |
| `archivo/ensayo-envoltorio` | `5b9c914` | `c7110e7` | el ensayo de la adopción (y `ensayo/trial`) |

## 2. Las ramas

Borradas el 2026-11-21, rama a rama con el OK de la propietaria:

- `dev/adoptar-ogr-core`: `git branch -d` (fusionada) y en GitHub.
- `dev/extraer-ogr-core` y `dev/d370-shutdown`: `git branch -D` y en GitHub; `ensayo/envoltorio` y
  `ensayo/trial`, solo locales, `git branch -D`. `-d` se niega con ellas porque no están en `main`;
  antes de cada `-D` se comprobó que su etiqueta contiene la punta y que está en GitHub.
- `dev/ci-linux-verde`, la rama corta de la 0.1.476, ya se había borrado con `-d` tras fusionarse
  en fast-forward.

Quedan `main` y `origin/main`, y las tres etiquetas.

## 3. La regla

En `AGENTS.md` («Un núcleo y varios programas») y en `CONTRIBUTING.md` («Commits and branches»):
una rama fusionada en `main` se borra, en GitHub y en local; una sin fusionar, solo con el OK de la
propietaria, y si lleva algo que `main` no tiene, antes se archiva en una etiqueta
`archivo/<nombre>`.

## 4. Versión

0.1.477 en los siete sitios. Núcleo fijado sin cambios: `ogr-core` 0.2.2.

## 5. Verificación

- Suite entera en Windows, `--jobs 4`, fuera de pantalla, en el `.venv` (`shared: ogr_core 0.2.2 …
  installed`): **7547 casos, 7545 pasan, 0 fallan, 2 saltados, sin fugas** ni tramos muertos, los
  mismos que la 0.1.476. Sigue el aviso de `test_dialogs_fit_v1315.py` fuera de `tests/_slow.txt`
  (150,0 s esta vez, 126,4 en la 0.1.476); no lo toca esta versión.
- `git branch -a`: `main` y `origin/main`. `git ls-remote origin`: `refs/heads/main` y las tres
  etiquetas `archivo/*` con su `^{}`.
- La CI de `main` sobre esta versión se da a la sesión de OGR-Core con su número.

## 6. Después de la versión: la sección «Development» del README (2026-11-21)

Solo documentación: ni la versión ni una línea de código cambian. Sale de escribir la guía para
montar la suite en un PC nuevo (`DESARROLLO.md`, en la carpeta de trabajo `OGR_Suite`) y de
ensayarla.

- `README.md`, «Development», y `README.es.md`, «Desarrollo», entre «Tests» y «Layout»: la
  instalación para cambiar el programa (con el extra `[mcp]`, como la CI; «Installation» sigue
  dando `pip install -e .`, que es la de quien solo lo usa), la misma receta en PowerShell, que
  el entorno lleva siempre el núcleo de la etiqueta fijada, que la suite va con el Python del
  entorno y sin pantalla, y dónde está la guía de la suite entera.

Lo que se encontró:

- **La suite sale igual en un entorno limpio y con las dependencias de hoy.** Ensayo del
  2026-11-21 en una carpeta temporal: clon de GitHub (`45c5146`), `.venv` nuevo de Python 3.14.7,
  `pip install -e ".[mcp]"`. Trae PySide6 6.12.0 (6.11.1 en el `.venv` de desarrollo), numpy
  2.5.5, scipy 1.18.1, shapely 2.2.0, matplotlib 3.11.2, `mcp` 2.3.0 y typer 0.29.2 (0.27.1 en
  el de desarrollo, anotado en la 0.1.476). Suite entera con `--jobs 4`, fuera de pantalla:
  **7547 casos, 7545 pasan, 0 fallan, 2 saltados, sin fugas** ni tramos muertos, en 33,0 min;
  `shared: ogr_core 0.2.2 … (installed, no git tree)`. Sin ninguna carpeta de fuera del
  repositorio: ni `referencias` ni `historico`.
- **El `.venv` de desarrollo no está limpio**: lleva paquetes que el programa no pide (`yt-dlp`,
  `ipykernel`, `pyserial`…), los mismos que el Python del sistema, y dice `ogr-slip2d 0.1.475`.
  No se toca aquí; al cambiar de PC se crea de cero.
- **Uno de los dos saltados no es de la máquina.** `test_the_fifteen_sheets_give_what_they_gave`
  (`tests/test_support_failure_v1161.py`) busca su modelo en
  `C:/Samuel/OpenGeoRock_Slip2d/referencias/…`, la ruta de antes de `OGR_Suite`; al no
  encontrarlo se salta con «the verification bank is not on this machine», también en el PC de
  desarrollo, donde el modelo sí existe en `Slip2D/referencias/…`. Se salta, por tanto, en todas
  partes desde la reorganización. **Anotado, no corregido**: es un test, y esta entrada no toca
  código.
- `docs/EMPEZAR_EN_VSCODE.md` y `.vscode/tasks.json` siguen diciendo `pip install -e .` y
  `python tests/_runner.py` a secas (sin el extra y sin el `.venv`). No se tocan aquí.
