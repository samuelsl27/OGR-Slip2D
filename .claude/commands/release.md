---
description: Prepara una versión nueva (números, changelog, verificación)
---
Prepara la versión $ARGUMENTS.

1. Sube el número en los **siete** sitios: `pyproject.toml`,
   `ogr_gui/main_window.py`, `ogr_slip2d/__init__.py`,
   `ogr_fem2d/__init__.py` y los `__version__` de `ogr_core/__init__.py`,
   `ogr_gui/__init__.py` y `ogr_cli/__init__.py`. Estos tres últimos se
   quedaron olvidados en 0.1.1 hasta v0.1.59 justo por no estar en esta
   lista. `ogr_data` sigue en 0.0.0 a propósito: es un stub previsto para
   v0.2.0. Comprueba que el diálogo Acerca de lo lee de los metadatos y no
   de un literal.
2. Actualiza el contador de tests en **los dos README** (`README.md` y
   `README.es.md`).
3. Escribe `docs/changelog/CHANGELOG_v$ARGUMENTS.md` siguiendo el estilo
   de los anteriores: registra **qué se encontró**, no solo qué se
   escribió, incluidos los caminos equivocados.
4. Ejecuta la suite completa y confirma que está en verde.
5. Muéstrame el resumen antes de hacer ningún commit.
