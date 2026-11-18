# OGR Slip2D adopta `ogr-core` 0.2.0

> Fase 2 de «un solo OGR-Core». Rehecha el 2026-11-18 sobre `main` (`d48e2b3`, v0.1.471) a partir
> de la spec 009 de la extracción (solo en la rama `dev/extraer-ogr-core`, que no se toca) y del
> ensayo de la fase 1 (`referencias/_traspaso_ogr_core_0.2.0`). El número 009 está ocupado en
> `main` por `009-sarma-dovelas-no-verticales`: esta es la **010**.

## Qué hace

OGR Slip2D deja de llevar su copia de `ogr_core` y su paquete `ogr_fem2d`, y pasa a depender de
**`ogr-core` v0.2.0** (repositorio OGR-Core, etiqueta `v0.2.0`), que ya contiene la malla y la
filtración en `ogr_core/fem/` y el runner de tests compartido. Ningún número de ningún método
cambia.

## Por qué

- La spec 009 sacó el núcleo a OGR-Core (v0.1.0, desde `2d68c29`), pero esa rama nunca entró en
  `main`: Slip2D siguió 101 versiones con su copia, y hoy hay dos núcleos que dicen cosas distintas.
  OGR-Core v0.2.0 vuelve a tomar el de Slip2D en `d48e2b3`; a partir de esta spec **el código de
  `ogr_core` solo se cambia en OGR-Core**.
- `ogr_fem2d` es el nombre del programa 03 (OGR FEM2D): mientras Slip2D lo use, los dos programas no
  pueden instalarse en el mismo entorno.

## Lo que hay hoy (medido el 2026-11-18)

- **Suite de partida** (`d48e2b3`, `--jobs 4`, Python del sistema 3.14.7): 8046 casos, 8044 pasan,
  2 saltados, código 0 (`antes/suite_d48e2b3_jobs4.txt`).
- **Huella del banco de cómputo** (lote `version`, 23 casos) en `antes/huella_d48e2b3/`, con las
  versiones de `antes/requisitos_fijados.txt` (95 paquetes).
- **Ensayo** (copia desechable, rama `trial` del bundle): sin `ogr_core/` ni `ogr_fem2d/`, contra
  `ogr-core` 0.2.0, 8002 de 8047 con los 43 fallos explicados uno a uno, y la huella **23 de 23
  idéntica bit a bit**. Con el envoltorio del runner (rama `envoltorio`), `--fast --jobs 4` da 7240
  tests con el mismo resultado.
- **En un entorno virtual de Windows sin consola los pools de procesos mueren**: `pythonw.exe` del
  venv es un lanzador que `multiprocessing` no sabe tratar. No es del núcleo. El censo está en
  `censo.md`.

## Criterios de aceptación

### v0.1.472 — los pools en un entorno virtual

- [ ] En un venv de Windows sin consola, un pool de cálculo corre (sin caer a un proceso) y el hijo
      tiene el mismo `sys.prefix` y resuelve `ogr_slip2d` y `ogr_core` en los mismos archivos que
      el padre.
- [ ] El test caza las dos formas de hacerlo mal: los hijos con el `pythonw.exe` del venv (el pool
      muere) y con el del Python base sin lanzador (otro `sys.prefix`, otro árbol).
- [ ] Fuera de un venv, `child_executable` da lo mismo que en v0.1.471. Ningún número cambia.

### v0.1.473 — la adopción

- [ ] No quedan `ogr_core/` ni `ogr_fem2d/` en el árbol, y ninguna línea importa `ogr_fem2d`.
- [ ] `pyproject.toml` declara `ogr-core @ git+https://github.com/samuelsl27/OGR-Core@v0.2.0`; sin
      `pyclipper` ni el extra `[fem]`, que no usa nadie.
- [ ] `tests/_runner.py` es un envoltorio de `ogr_core.testing.runner`, y `tests/_leaks.py` un
      puente a `ogr_core.testing.leaks`. Las diez entradas de la lista blanca del programa se
      quedan aquí, con su porqué.
- [ ] Los 39 tests que ya viven en OGR-Core salen de aquí, comprobado antes que cada uno es el mismo
      test (`censo.md` §1).
- [ ] Los tests que leían fuentes del núcleo por ruta leen el árbol del núcleo instalado, y **cada
      censo afirma que encontró algo** (`censo.md` §3).
- [ ] Ninguna invariante de los tests del runner y las fugas se pierde: cada una está en OGR-Core o
      aquí, y `censo.md` §4 dice dónde.
- [ ] Versión en siete sitios, y el `ogr_core` que se importa es el fijado en `pyproject.toml`.
- [ ] *Acerca de* da también la versión del núcleo, con su `tr()` y su español.
- [ ] `AGENTS.md`, `CONTRIBUTING.md`, los README, `docs/architecture.md`, `docs/quickstart.md`,
      `docs/plugins.md`, `spec/constitution/tech-stack.md`, `.claude/commands/release.md`, la CI y
      el changelog dicen dónde vive el núcleo; `AGENTS.md` lleva la regla nueva.

### Entorno y banco

- [ ] `.venv` en el repositorio con las versiones de `requisitos_fijados.txt`, `ogr-core` en
      editable desde OGR-Core y Slip2D en editable con `[mcp]`. El Python del sistema, sin tocar.
- [ ] El banco de cómputo y los scripts del banco que importaban `ogr_fem2d` vuelven a correr
      (`censo.md` §6).

### Verificación

- [ ] Suite entera `--jobs 4` en el `.venv`, comparada test a test con la de partida: cada test que
      cambia, falta o sobra, explicado; las cifras, en el changelog.
- [ ] Suite entera en serie, sin argumentos (cambia el runner).
- [ ] Huella del banco, lote `version`: **23 de 23 idénticos** frente a `antes/huella_d48e2b3/`, y
      la procedencia de cada huella dice este árbol y `ogr_core` 0.2.0.
- [ ] `git diff d48e2b3 -- tests/test_slide_validation_* tests/test_acads_* validacion/` vacío.
- [ ] `python -m ogr_gui` (fuera de pantalla), `python -m ogr_cli --help` y
      `python -m ogr_mcp --help` arrancan.
- [ ] CI en verde.

## Validación numérica

No hay cálculo nuevo. La referencia es una **identidad**: el código del núcleo es el mismo
(`ogr-core` 0.2.0 sale de `d48e2b3`), así que todo número debe salir idéntico bit a bit. La
comprobación externa es la huella del banco de cómputo, sacada antes con el árbol de `d48e2b3`, y
los casos de validación del equilibrio límite, que no se tocan.

## Decisiones de la propietaria (2026-11-18)

| # | Pregunta | Decisión |
|---|---|---|
| Q1 | ¿Se fusiona F1 (`2d68c29`)? | **No.** Sus cambios en tests se reproducen con `reescribir_imports.py` y a mano, y se comparan con la rama `trial` del ensayo. El changelog cita `2d68c29` |
| Q2 | Dependencias | Fuera `pyclipper` y el extra `[fem]` (nadie los importa). `ezdxf`, `h5py` y `reportlab` se quedan: los importan los tests |
| Q3 | ¿Los scripts del banco 02 que importan `ogr_fem2d`? | **Sí**, en la fase del banco, junto con los del 05 y `elegibilidad_critica_d155.py` |

## Fuera de alcance

- Cualquier cambio en OGR-Core u OGR-FEM2D. Lo que haga falta del núcleo se pide en la ventana de
  OGR-Core y sale como v0.2.1.
- Cambiar un número o un test de validación.
- Desinstalar Slip2D del Python del sistema, y apuntar el servidor MCP y los accesos directos al
  `.venv`: se decide al final.
- `ogr_core/report` y matplotlib (abierto en OGR-Core 0.2.0 §6).
- Reescribir changelogs, auditorías o specs viejas que nombran `ogr_fem2d`: son historia.
