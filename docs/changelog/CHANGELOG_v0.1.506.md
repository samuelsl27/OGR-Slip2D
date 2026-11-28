# OGR Slip2D v0.1.506

**Todo campo de contornos que no es el factor de seguridad empieza en Viridis**, una paleta cuya
luminosidad crece con el valor. Son los campos hidráulicos y el Ky y Newmark de una corrida sísmica,
en la ventana y en la figura del informe. El factor de seguridad conserva su leyenda medida: Rainbow
en 24 bandas, de 0 a 6. Propuesta D5 de la spec 006 de OGR FEM2D (2026-11-28); la propietaria eligió
el alcance el mismo día. Ningún número cambia.

## 0. Lo que se encontró

- **Antes de esta versión empezaban en «Hot to cold»:**
  - las tres magnitudes hidráulicas (presión de poros, altura total, altura de presión), por
    `ContourSettings.for_field`;
  - el Ky y Newmark, por `for_reported` (D438, 0.1.500), con el rojo en el extremo crítico;
  - en la figura del informe, el Ky con `RdYlBu` y Newmark con `RdYlBu_r` (D423).
- **Por qué no sirve «Hot to cold».** Es divergente y clara en el centro: su luminosidad sube y
  luego baja (medida en el test con la L\* de CIE 1976). El orden de los valores no se lee en una
  copia en gris, ni lo lee quien no distingue el rojo del verde. Un divergente solo dice algo cuando
  el centro tiene sentido, y ni una altura, ni una presión, ni un Ky, ni un desplazamiento lo tienen.
- **Una incoherencia que ya estaba.** La ventana de Interpretar agua subterránea
  (`ogr_gui/interpret_groundwater_window.py`) y el PNG del agente para el agua (`ogr_api/render.py`)
  ya usaban Viridis. En cambio, el lienzo principal pintaba esas mismas magnitudes con «Hot to cold».
  Desde ahora dicen lo mismo.
- **La guía de interfaz** ya resolvía este choque a favor de Rainbow, pero solo para el factor de
  seguridad (identidad, v0.1.82). Su fila de «Cuando chocan» dice ahora qué se queda y qué cambia.

## 1. Qué cambia

- `ogr_gui/contours.py`:
  - `FIELD_PALETTE = "Viridis"`, con su porqué;
  - `for_field` lo usa en todo campo que no es `fos`;
  - `for_reported` lo usa en Ky y en Newmark. **El extremo crítico pasa del rojo al oscuro**: en Ky,
    el menor valor; en Newmark, el mayor, con `reverse`, como antes.
- `ogr_api/report_figures.py`: `grid_data` da `viridis` para el Ky y `viridis_r` para Newmark, que
  es lo que dibujan la figura del informe y el PNG del agente. El factor sigue con el dibujo de
  siempre.
- `spec/constitution/guia-de-interfaz.md`: la fila de la paleta en «Cuando chocan».

**Lo que se aparca, por decisión de la propietaria:** la propuesta D10 de FEM2D (puntos relativos
`@dx, dy`, polares `@d<ángulo` y la coma decimal en la barra de coordenadas). Llega al adoptar el
paquete `ogr-gui`, que hoy no está en el `.venv` de Slip2D.

## 2. Lista de comprobación de la guía de interfaz

- Identidad: el factor de seguridad sigue con su arco iris medido de 24 bandas y su rango fijo de 0
  a 6 (test). La crítica, la seleccionada y los mínimos no cambian de color.
- Color: la luminosidad crece con el valor en todo campo que no es el factor (test, con la L\*
  calculada de su fórmula). La leyenda sigue llevando sus números.
- Coherencia: la ventana, el informe y el PNG del agente dibujan el Ky y Newmark con la misma
  paleta y el mismo extremo crítico.
- Ninguna acción, menú ni mensaje nuevo, y ningún diálogo modal.
- **Gemela en `ogr_ui`:** `contours` tiene una gemela en OGR-GUI, y FEM2D ya cambió su defecto allí.
  Hay que avisar a la sesión de OGR-GUI de que Slip2D lo hace también, para que no se separen.

## 3. Tests

- `tests/test_contour_palette_viridis_v1506.py` (nuevo, 8 tests, solo aritmética):
  - la fórmula de L\* en sus puntos fijos;
  - los colores de Viridis y sus ocho bandas, con la L\* creciente, y el control: «Hot to cold»
    tiene su máximo en el centro;
  - los tres campos hidráulicos, y el factor con su leyenda;
  - el Ky oscuro en su mínimo y Newmark oscuro en su máximo;
  - los mapas de color de la figura del informe.

  Contra 0.1.505 fallan 5 de 8: los que miden la paleta nueva. Pasan los de la fórmula, el control
  y la leyenda del factor.
- **Cambios declarados** en dos tests anteriores, que fijaban la paleta vieja:
  - `tests/test_contour_dialog_seismic_v1502.py`: *Restore Defaults* da «Viridis» donde daba «Hot to
    cold»;
  - `tests/test_report_figures_seismic_v1450.py`: `viridis` y `viridis_r` donde daba `RdYlBu` y
    `RdYlBu_r`. El test «red is still the critical end» pasa a «the dark end is the critical one».
- Áreas `contour`, `report_figures`, `slide_legend`, `interpret` y `render`, con `--jobs 4`: 344 en
  verde.

## 4. Numeración

Las fichas del núcleo vuelven a correrse una: 0.1.507 D443, 0.1.508 D444, 0.1.509 D445, 0.1.510
D446 y 0.1.511 D449.

## 5. Suite

La suite entera se corre al final de la tanda.
