# OGR Slip2D v0.1.279

**Cada biblioteca de parámetros del botón *Pick* dice de dónde salen sus
números, y la de Brooks-Corey pasa a ser una tabla publicada (D273).**
- **Lo que había hasta ahora:**
  - un solo comentario citaba «representative literature figures (van
    Genuchten 1980; Carsel & Parrish 1988; Brooks & Corey 1964)» para las
    cuatro bibliotecas;
  - la lista de *Pick* decía «Soil (literature values)» en todas;
  - solo van Genuchten tenía una tabla detrás.
- **Lo que cambia:**
  - **Brooks-Corey** son ahora las 11 texturas USDA de Rawls, Brakensiek y
    Saxton (1982);
  - **Gardner y Fredlund-Xing** se declaran ilustrativas.

## 0. Lo que se encontró

- **Brooks y Corey (1964) no publican medias por textura.** La tabla de
  referencia por textura es la de Rawls, Brakensiek y Saxton (1982), «Hydrologic
  soil properties classified by soil texture».
  - La biblioteca vieja tenía cinco texturas sin fuente: la arena tenía
    λ 2,0 y ψb 5 kPa, cuando la tabla da 0,592 y 0,71 kPa. Era siete veces
    su presión de burbujeo.
  - Ningún modelo del banco usa *Pick*, así que no se mueve ninguna fila.
- **La fuente, en dos pasos.**
  - El primer PDF que llegó con el nombre «Rawls Brakensiek Saxton (1982)
    Trans ASAE» era en realidad **Saxton y Rawls (2006)**, *SSSAJ*
    70:1569–1578. Cita la tabla de 1982 pero no la reproduce. Está anotado
    en `Documentacion_Guia/INDICE.md`.
  - La propietaria aportó después la tabla misma, recortada del artículo de
    1982: `Documentacion_Guia/Fig_Tablas_Libro_Estimation of Soil Water
    Properties_Rawls_W_J/`.
- **La tabla da dos medias para cada parámetro**, la aritmética y la
  geométrica («antilog of the log mean»). Decisión de la propietaria: la
  **geométrica**, porque ψb y λ se reparten de forma aproximadamente
  lognormal. La aritmética de ψb es del orden del doble (arena: 15,98 cm
  frente a 7,26).
- **Gardner (forma racional) y Fredlund-Xing:** no se ha encontrado ninguna
  tabla de medias por textura. Sus parámetros se ajustan a los datos de cada
  suelo. Decisión de la propietaria: declararlas ilustrativas, sin
  retirarlas.
- **La forma de Fredlund-Xing.**
  - OGR usa kr = 1/{ln[e + (ψ/A)^B]}^C, que es exactamente la ec. 2 de la
    ayuda de la referencia («Fredlund-Xing permeability function»).
  - No se ha podido contrastar con el artículo de 1994, que no está en
    `referencias/`. No se abre ficha: OGR coincide con la definición que
    imita.
- **La caja de ψb tenía 3 decimales.** *Pick* habría escrito 0,712 en vez de
  0,712206 kPa, y Aceptar habría redondeado un valor puesto por la API. Es
  la clase de Ks (D271) y Ss (D191). Pasa a 6 decimales.

## 1. Qué cambia

- **`permeability_models`** (núcleo):
  - `_RAWLS_1982_BC` es la tabla en sus unidades (cm, -). La biblioteca de
    Brooks-Corey se construye desde ella con ψb [kPa] = cm × 9,81/100. Con
    el γw por defecto del proyecto, la altura de burbujeo es exactamente la
    de la tabla, y el comentario explica por qué ese γw.
  - `LIBRARY_SOURCES` (modelo → «Autor (año)» o `None` = ilustrativa) y
    `library_source(model)`, exportados por `ogr_core.hydraulic`. Es la
    única fuente de verdad, y la leen el diálogo, el API y el banco.
  - Hay un comentario «ILLUSTRATIVE, no published table by texture» encima
    de Gardner y de Fredlund-Xing.
- **El diálogo:** la lista de *Pick* dice «Soil (values from Carsel &
  Parrish (1988))», «… Rawls, Brakensiek & Saxton (1982)» o «Soil
  (illustrative values, no published source)». Hay 2 cadenas nuevas con su
  español, y la vieja se sustituye.
- **El API:** la nota de `hydraulic_set(library=…)` dice la fuente o
  «illustrative values, no published source». La descripción del MCP también.

## 2. Tests

`tests/test_pick_library_v1279.py`, 9 casos:

- **La tabla de Rawls et al. (1982), copiada del artículo**, contra la
  biblioteca:
  - las once texturas;
  - λ igual a lo impreso y ψb igual al cm × 9,81/100 a 1e-12;
  - kr = 1 hasta la altura de burbujeo de la tabla y < 1 pasada ella
    (regla 1).
- **Las fuentes:** van Genuchten y Brooks-Corey citadas, Gardner y
  Fredlund-Xing sin fuente, y toda biblioteca declarada.
- **La nota del API**, por modelo.
- **El diálogo:**
  - la etiqueta de la lista para cada modelo, con `getItem` sustituido;
  - *Pick* y después Aceptar conservan 0,712206.

`test_gw_gui_v129` (Pick activo solo con biblioteca) y `test_unsaturated_v127`
no cambian. La tabla de Carsel y Parrish la sigue comprobando
`test_groundwater_ops_v1200`.

## 3. Verificación

- **Suite entera:** 5838 / 5838, con código de salida del proceso 0.
- **El test nuevo en el árbol de 0.1.277:** no carga
  (`LIBRARY_SOURCES` no existe). Sus 9 casos fallan.
- **`d273()` del `verificar_cierres.py` de la raíz:** CIERRE DOCUMENTAL.
  - Brooks-Corey: SE SOSTIENE, con su test.
  - Gardner y Fredlund-Xing: ilustrativas, en el código y en el diálogo.
- **Banco:** cero filas movidas, porque ningún modelo usa *Pick* (el grep de
  la ficha).

## 4. Lo que no se ha probado

- La prueba manual de *Pick* en el diálogo.
- Fredlund y Xing (1994) contra la forma que usa OGR (falta el artículo).
