# OGR Slip2D v0.1.285

**La rueda del ratón solo cambia una caja numérica o un desplegable que tenga
el foco (D286).** Hasta ahora, al bajar un diálogo largo con la rueda, la caja
que pasaba bajo el puntero cambiaba de valor sin que el usuario la tocara.

## 0. Lo que se encontró

- **La prueba de la interfaz** de 0.1.284, hecha por Claude Desktop
  (`_auditoria/P6_0284/INFORME_prueba_GUI_0.1.284.md`, H13), giró la rueda en
  *Definir propiedades hidráulicas* para bajar el panel.
  - La caja «a» de Gardner pasó de 0,01 a 0.
  - Se canceló. Con Aceptar, el material se habría guardado con a = 0 sin que
    nadie lo escribiera.
- **Reproducido sin pantalla** (`_auditoria/P8_interfaz/repro_d286.py`): con
  el foco en otra caja, tres vueltas de rueda sobre «a» la llevan a 0.
- **La causa.** Qt da a toda caja numérica y todo desplegable la política de
  foco `WheelFocus`: la rueda los enfoca y los cambia. Nada en `ogr_gui`
  filtraba la rueda fuera del lienzo.
- **De la misma prueba se abrieron otras once fichas,** D287–D297, en un
  paquete nuevo de interfaz (P8).

## 1. Qué cambia

- **`ogr_gui/wheel_guard.py`**, un filtro de eventos de toda la aplicación que
  instala `MainWindow` al construirse:
  - al pulirse una caja numérica o un desplegable, `WheelFocus` pasa a
    `StrongFocus`: se enfocan con clic o tabulador, ya no con la rueda;
  - una vuelta de rueda sobre uno que no tiene el foco se ignora y se da por
    tratada, así que Qt la pasa al contenedor, que se desplaza.
- **Lo que no toca:** el lienzo (la rueda sigue siendo el zoom), las listas,
  las tablas y las barras de desplazamiento.
- **El coste:** el filtro ve todos los eventos de la aplicación, pero hace una
  sola comparación del tipo de evento salvo en la rueda y el pulido.
- **Interruptor `wheel_guard.WHEEL_NEEDS_FOCUS`:** apagado, vuelve el
  comportamiento de 0.1.284. No mueve ningún número del motor, así que no
  entra en `INTERRUPTORES`.

## 2. Tests

`tests/test_wheel_guard_v1285.py`, 6 casos, sobre el diálogo hidráulico real:
- una caja y un desplegable sin foco no cambian con la rueda;
- la misma caja con el foco sí cambia;
- las cajas y los desplegables pierden `WheelFocus` al pulirse;
- la ventana principal instala el filtro;
- apagado, la rueda vuelve a cambiar una caja sin foco.

**Lo que el test no ve:** un evento de rueda mandado a mano no es espontáneo,
así que Qt no lo pasa al contenedor ni mueve el foco. Que el panel se desplace
se comprueba a mano.

## 3. Verificación

- **Suite entera:** 5880 / 5880, con código de salida del proceso 0.
- **El guion de reproducción**, con el filtro instalado como lo instala la
  ventana, dice «no cambia».
- **`verificar_cierres.py` de la raíz:** `d286()` da CUBIERTO POR TEST;
  29 comprobaciones, ninguna bajada.

## 4. Lo que no se ha probado

- **A mano en la ventana:** que la rueda sobre los campos de *Definir
  propiedades hidráulicas* desplace el panel, y que con una caja enfocada la
  cambie.
