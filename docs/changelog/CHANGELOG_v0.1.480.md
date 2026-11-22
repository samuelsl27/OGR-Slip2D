# OGR Slip2D v0.1.480

**Fuera las rutas del PC anterior.** La suite se mudó el 2026-11-22 de `C:\Samuel\OGR_Suite` a
`C:\Desarrollo\OGR_Suite`. Ni el programa ni un número se mueven. Los changelogs, las auditorías y
`docs/ORGANIZAR_ESPACIO_TRABAJO.md` cuentan lo que era verdad entonces y no se tocan.

## 0. Lo que se encontró

- **Un test llevaba meses saltándose en todas partes, y vuelve a pasar sin mover un dígito.**
  `test_the_fifteen_sheets_give_what_they_gave` (`tests/test_support_failure_v1161.py`) buscaba su
  modelo en `C:/Samuel/OpenGeoRock_Slip2d/referencias/…`, la ruta de antes de `OGR_Suite`, y se
  saltaba con «the verification bank is not on this machine» incluso donde el banco estaba (lo
  anotó el apartado 6 del changelog de la 0.1.477). Ahora lo busca junto al repositorio,
  `Path(__file__).parents[2] / "referencias" / …`, y **pasa**: los factores de Bishop y Spencer del
  problema 091 que fijó la v0.1.179 siguen iguales bit a bit. Era el riesgo de esta versión: el
  test es una instantánea (su docstring lo dice) y podía haberse quedado atrás mientras nadie lo
  corría. No ha sido así. En la CI sigue saltándose, porque allí no está el banco.
- **AGENTS.md, línea 13**, nombraba `C:\Samuel\OGR_Suite\Core\OGR-Core`. Ahora dice
  `../../Core/OGR-Core` en `OGR_Suite`, sin depender del PC. Sigue en 499 líneas.
- **`.vscode/settings.json`** daba `.venv/bin/python`, que en Windows no existe; el registro de VS
  Code decía «unresolvable, falling back to auto-discovery». La clave admite una sola ruta para
  todos los sistemas, así que pasa a `.venv/Scripts/python.exe`, porque el programa se desarrolla
  en Windows. La CI no usa VS Code. Al lado queda un comentario que dice qué elegir en Linux o macOS.
  El `.code-workspace` de la carpeta Slip2D, fuera de git, ya usaba esa ruta.
- **`.vscode/tasks.json`** lanzaba `python` a secas, que en este PC es el 3.15 del sistema, sin el
  núcleo. Las tres tareas usan ahora el Python del `.venv`, con un `command` por sistema
  (`"windows"` aparte), y la suite completa va con `--jobs 4`, como pide AGENTS.md para publicar.
- **`docs/EMPEZAR_EN_VSCODE.md`**, apartado 3: `pip install -e ".[mcp]"` en vez de
  `pip install -e .`, la advertencia de que `python` es el del `.venv`, y `--jobs 4`. La cifra
  «entre 5 y 7½ minutos» era de v0.1.80; en vez de poner otra sin medir, remite a la tabla de
  AGENTS.md. El resto de la guía (rutas de ejemplo, nombres de carpetas del espacio de trabajo) no
  se ha revisado en esta versión.
- Fuera de git: `comun.py` del banco de cómputo
  (`referencias\Ejemplos\RS2_Verification Manuals\_auditoria\COMPUTO\bench`) deduce ahora `REPO` y
  `BANK` de su propia ruta. Comprobado con el `.venv`: `REPO`, `BANK`, `B02` y `B05` existen. No
  entra en ningún commit.

## 1. Qué se probó

- `test_support_failure_v1161 -k fifteen`, solo: 1 de 1, **pasa** (antes saltado).
- Los dos JSON de `.vscode` se cargan con `json.load`.
- `wc -l AGENTS.md`: 499.
- Suite entera, `--jobs 4`: ver §2.

## 2. Suite

Suite entera con `--jobs 4`, fuera de pantalla, en el `.venv` (`shared: ogr_core 0.2.2 …
(installed, no git tree)`): **7548 casos, 7547 pasan, 0 fallan, 1 saltado**, sin fugas ni tramos
muertos, código de salida 0. Un saltado menos que en la 0.1.479: el de las quince láminas ya
corre, y el único que queda es el de `os.killpg` (solo POSIX). Sigue `SERIAL RUN DUE`.
