# OGR Slip2D v0.1.317

***Preferences* ya no tiene casillas que nadie lee (D299).** Primera versión de
la tanda P8h.

## 0. Lo que se encontró

`PreferencesDialog` tenía un grupo «Display Options...» con tres casillas. Ni
`_accept` ni ninguna otra línea del programa las leía, y desde D290 se guardan el
idioma y el tema, no estas, así que volvían a su valor inicial cada vez que se
abría el diálogo. Medido, casilla a casilla, lo que prometían:

| Casilla | Lo que hay en el programa |
|---|---|
| «Show Tabs for Multiple Windows» | no existe ninguna interfaz con pestañas: ni `setTabPosition`, ni `tabifyDockWidget`, ni modo documento |
| «Mark file as modified after importing» | ya ocurre siempre: desde 0.1.302 toda importación es un paso de deshacer y marca el proyecto |
| «Default to compressed format when saving» | no existe: el `.ogr` es JSON plano, y solo el archivo de resultados HDF5 comprime, siempre |

Un ajuste que no mueve nada es peor que no tenerlo (regla 7): el usuario cree que
el programa lo respeta.

## 1. Qué cambia

**Decisión de la propietaria (2026-10-15):** se quitan las tres.

- Se quitan las tres casillas y el grupo «Display Options...», que se quedaba
  vacío.
- Sus tres claves de traducción quedan sin uso en el diccionario. No hay un test
  de claves sin uso, y no estorban.

## 2. Tests

`tests/test_preferences_controls_v1317.py`, 4 casos:

- **todo control con valor que crea el diálogo** (casilla, desplegable, caja
  numérica, línea de texto, botón de opción) lo lee `_accept`, medido en el
  código con el AST;
- **en el diálogo real,** todo control con valor está entre los que lee
  `_accept`. Así no puede volver una casilla sin lector;
- **las tres casillas no están;**
- **control:** Guardar sigue emitiendo el idioma y el tema, como dejó D290.

**Con el código de 0.1.316 fallan 3 de los 4,** por las tres casillas sin
lector. El que pasa en los dos árboles es el control. Se corrió sobre una copia
del árbol de 0.1.316 sin el buscador editable.

## 3. Verificación

- **Suite entera:** 6111/6111, código de salida 0, a la primera (57 min).
- **Banco:** `d299()` en el `verificar_cierres.py` de la raíz: **CUBIERTO POR
  TEST**. Ciclo de cierre:
  - `verificar_cierres.py` entero: 59 comprobaciones, 0 bajadas;
  - instantánea `Evaluaciones/0.1.317` antes y después (`--forzar`);
  - `retirar_cerrados.py --escribir D299`;
  - poda de la lista P8 y D299 tachada en la fila P8;
  - `generar_prompts.py`: 34 prompts y las mismas 19 FALTA;
  - `auditoria_invariantes.py` en la raíz y en el 02, con 0 ERROR.
- **Los tests vecinos**, antes de la suite: 42/42 (*Preferences*, idioma, temas,
  traducciones de Qt, tema oscuro e i18n).
- **Ningún número cambia.**

## 4. Pendiente

- A mano: *File → Preferences…* con sus dos desplegables.
