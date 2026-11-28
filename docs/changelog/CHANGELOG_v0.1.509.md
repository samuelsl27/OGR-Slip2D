# OGR Slip2D v0.1.509

**D445: un `.ogr` con `id` repetidos se abre diciéndolo, en la ventana y en el agente; Borrar quita
el contorno elegido, uno solo.** La parte del núcleo está en OGR Core 0.2.14, que Slip2D fija desde
0.1.505:
- las notas de la lectura (`Project.read_notes`);
- la renovación del `Polyline.id` repetido;
- `duplicate_id_notes`;
- quitar por identidad.

Decisión de la propietaria del 2026-11-27: se renueva el `id` de polilínea, y de los demás solo se
avisa.

## 0. Lo que se encontró

- **El defecto, medido con 0.1.485** con el guion del banco `_auditoria/P10_D445/medir_d445.py`:
  dos contornos con un mismo `id` se abrían sin decir nada, y Borrar en la ventana se llevaba los dos
  (quedaban 0 de 2), mientras que Deshacer devolvía solo uno. El Borrar se arregló en el núcleo:
  `_do_delete_boundary` ya le pasaba el objeto, y el test nuevo lo fija desde la ventana.
- **Las notas de la lectura no llegaban a nadie.** El núcleo las guarda en `read_notes`, y la ventana
  y el agente tenían que decirlas. Para probar Abrir sin el diálogo de archivo, el paso de después
  del diálogo pasa a `_open_path`.

## 1. Qué cambia

- `ogr_gui/main_window.py`:
  - `_open_path` (nuevo; `act_open` lo llama tras el diálogo) dice en la barra, durante 20 s, lo que
    anotó la lectura, junto al aviso de regiones huérfanas que ya había. El archivo se abre siempre;
  - `_read_notes_text` (nuevo) las pone en el idioma del lector, por su código.
- `ogr_api/ops/project.py`:
  - `project_open` devuelve `read_notes`, con sus `warning_codes`;
  - `project_validate` avisa con `duplicate_id_notes`: los `Boundary.id` y los `id` de superficie del
    usuario repetidos, que no se renuevan porque los enlaces los leen.

El castellano de los tres códigos y de las cuatro etiquetas entró en `efaa846`.

## 2. Lista de comprobación de la guía de interfaz

- Mensaje: al abrir se dice qué `id` está repetido y entre qué contornos, en el idioma del lector y
  sin diálogo modal. El archivo se abre igual.
- Deshacer: Borrar quita uno, y Deshacer lo devuelve a su sitio (test).
- Ninguna acción ni menú nuevos.

## 3. Tests

- `tests/test_duplicate_ids_d445_v1509.py` (nuevo, 4 tests, una ventana para todo el archivo; el caso
  es el talud de ejemplo con un contorno de material copiado como lo copiaban 0.1.59 a 0.1.455):
  - la barra lo dice al abrir, se conservan los dos contornos y el `id` de polilínea sale renovado;
  - el control: el talud de ejemplo no dice nada de `id`;
  - Borrar uno de los dos deja el otro, y Deshacer lo devuelve a su sitio;
  - el agente: `project_open` devuelve las notas con sus códigos, y `project_validate` avisa del
    `Boundary.id` repetido, pero ya no del de polilínea, que se renovó.

  Contra 0.1.508 fallan 3 de 4. Pasa el de Borrar, que arregló el núcleo.
- Áreas `open`, `project`, `load`, `copy_boundary`, `undo`, `mcp`, `api`, `core_messages` e `i18n`,
  con `--jobs 4`: 457 en verde.

## 4. Suite

La suite entera se corre al final de la tanda.
