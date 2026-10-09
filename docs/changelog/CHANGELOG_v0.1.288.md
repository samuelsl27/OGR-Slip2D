# OGR Slip2D v0.1.288

**Una entrada de menú desactivada se ve desactivada, y las del agua dicen por
qué (D289).** En un proyecto nuevo, *Groundwater* enseñaba cuatro entradas como
si se pudieran usar; al pulsarlas no pasaba nada, y nada decía por qué.

## 0. Lo que se encontró

- **La prueba de la interfaz** de 0.1.284
  (`_auditoria/P6_0284/INFORME_prueba_GUI_0.1.284.md`, H2): «Define
  Hydraulic Properties…», «Water Pressure Grid…», «Set Boundary Conditions…»
  y «Transient Groundwater…» con la misma tinta que «Mesh».
- **Por qué no se veían en gris.** Las dos hojas de estilo (`ogr_gui/themes`)
  dan color a `QMenu` y no tienen regla `:disabled`. Con una hoja de estilo,
  Qt pinta las entradas desactivadas con ese mismo color.
  - **Medido sin pantalla:** el contraste del texto de una entrada desactivada
    frente al fondo era IGUAL al de una activa (669 / 669 en el tema claro,
    513 / 513 en el oscuro).
  - **El tema oscuro** hacía lo mismo con los botones, las cajas, los
    desplegables, las listas, las pestañas y los grupos: todos tenían color sin
    estado desactivado.
- **Por qué un texto de estado no bastaba.** Qt muestra el texto de estado de
  una acción solo cuando el menú la hace actual, y con los estilos Fusion y
  windows11 nunca hace actual una desactivada (`SH_Menu_AllowActiveAndDisabled`
  = 0; windowsvista y Windows sí). El probador lo vio: con ↓ el foco saltaba
  las entradas desactivadas.
- **Las ayudas de los menús tampoco se veían:** ningún menú tiene
  `setToolTipsVisible`. El motivo que *Water Pressure Grid* llevaba en su ayuda
  desde 0.1.202 no se había visto nunca en el menú.
- **Decisión de la propietaria:** un texto de estado para las entradas del agua.
  Se descartaron «solo el gris» y «no desactivarlas».

## 1. Qué cambia

- **Las hojas de estilo:**
  - en el tema claro, `QMenu::item:disabled` y `QGroupBox::title:disabled`;
  - en el oscuro, además, `:disabled` para botones, botones de herramienta,
    cajas, desplegables, editores, listas, cabeceras, grupos y pestañas.
- **`_update_groundwater_actions`** pone a cada entrada del agua desactivada su
  motivo como texto de estado, y lo quita al activarla:
  - *Define Hydraulic Properties* y *Transient Groundwater*: «Necesita un
    método de agua subterránea por elementos finitos: elígelo en Ajustes de
    proyecto > Agua subterránea.»;
  - *Set Boundary Conditions*, *Compute Groundwater* y *Reset FE Mesh*:
    «Necesita la malla de elementos finitos: Agua subterránea > Malla.»;
  - *Interpret Groundwater*: «Necesita un resultado de agua subterránea: calcula
    primero el agua.»
  - *Water Pressure Grid* pone como texto de estado el motivo que ya tenía en
    su ayuda (`rules.grid_refusal`).
- **`DisabledReasonFilter`**, instalado en todos los menús de la barra: cuando
  el puntero pasa por una entrada desactivada con texto de estado, lo pone en la
  barra de estado. Las entradas activas siguen como siempre.

## 2. Tests

`tests/test_disabled_menus_v1288.py`, 6 casos:
- con cada tema, una entrada desactivada se dibuja con menos contraste que una
  activa. Es una medida sobre la imagen del menú, no sobre la hoja de estilo
  (con la regla: 669 → 285 en el claro, 513 → 207 en el oscuro);
- en cada tema, todo widget interactivo cuyo color de texto fija la hoja tiene
  su color `:disabled`;
- con el método de nivel freático, las entradas del agua llevan su motivo, y
  pasar el puntero por la desactivada lo pone en la barra de estado;
- con un método por elementos finitos, la entrada está activa y sin motivo.

**Lo que se encontró al escribirlo.** El test buscaba el menú con
`QAction.menu()`, y tras cerrar otra ventana el envoltorio de PySide apuntaba a
un menú ya borrado. Se busca con `menuBar().findChildren(QMenu)`. El programa
no usa `.menu()`.

## 3. Verificación

- **Suite entera:** 5895 / 5895, con código de salida del proceso 0.
- **Tests de menús, temas y agua** (6 archivos, 82 casos): verdes.
- **`verificar_cierres.py` de la raíz:** `d289()` da CUBIERTO POR TEST;
  32 comprobaciones, ninguna bajada.

## 4. Lo que no se ha probado

- **A mano:**
  - el menú *Groundwater* de un proyecto nuevo, en gris y con el motivo en la
    barra de estado, con los dos temas;
  - el aspecto del tema oscuro con controles desactivados.
