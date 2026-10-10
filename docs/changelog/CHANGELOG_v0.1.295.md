# OGR Slip2D v0.1.295

**El mensaje del cálculo de agua solo nombra, como calculados con las
propiedades por defecto, los materiales que usan elementos de la malla
(D303).**

## 0. Lo que se encontró

- **La segunda prueba de la interfaz**
  (`_auditoria/P8_interfaz/INFORME_prueba_GUI_0.1.290.md`, H4) usó un modelo con
  tres materiales:
  - «Upper» y «Lower», asignados y con propiedades hidráulicas;
  - «Spare», sin asignar y sin ellas.

  El cálculo terminó con «… (default properties used for: Spare)», y ningún
  elemento usa «Spare».
- **El código.** `_compute_groundwater` llamaba `missing` a todo material sin
  propiedades hidráulicas, se usara o no.
- **No cambiaba ningún número:** era el mensaje. Pero mandaba a buscar donde no
  había nada.
- **Reproducido por la ventana, antes de tocar nada:** con «Lower» también sin
  propiedades, el mensaje decía «Lower, Spare».

## 1. Qué cambia

- **`_compute_groundwater`** nombra solo los materiales sin propiedades que
  tienen elementos en la malla: los `material_id` de `mesh.elements`.

## 2. Tests

`tests/test_default_props_message_v1295.py`, 2 casos, por el cálculo de la
propia ventana:
- un material sin propiedades que ningún elemento usa no se nombra, y si los
  usados las tienen, no hay cola;
- uno que sí usan elementos se nombra, y el que no, no.

Con el código de 0.1.294 fallan los dos.

## 3. Verificación

- **Suite entera:** 5920 / 5920, con código de salida del proceso 0.
- **`verificar_cierres.py` de la raíz:** `d303()` da CUBIERTO POR TEST;
  39 comprobaciones, ninguna bajada.
- **Tests del agua en la ventana** (3 archivos, 38 casos): verdes.
