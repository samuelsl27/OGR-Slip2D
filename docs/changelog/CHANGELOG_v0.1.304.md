# OGR Slip2D v0.1.304

**Cargas y soportes son pasos de deshacer (D292).** Tercera versión de la
tanda P8e (0.1.302 fue D310, el aborto de la suite).

## 0. Lo que se encontró

- **16 métodos** añadían, cambiaban o borraban una carga o un soporte sin
  dejar paso:
  - por el lienzo: los clics finales de carga distribuida, carga lineal,
    soporte, patrón y estirado, y el borrado por clic;
  - por diálogo: carga sísmica, registros sísmicos, *Define Support* y las
    propiedades o el patrón de un soporte;
  - por el menú de clic derecho y por cuadros de entrada: *Delete Load*,
    *Modify Load*, *Modify Support*, *Move Support* y *Ungroup Support
    Pattern*.
- **«Cancelar» a medias en *Modify Load*.** Pregunta la magnitud y después la
  del extremo lejano. Cancelar la segunda pregunta dejaba escrita la primera.
- **Visto y no tocado:** el manejador de *Add Support* se queda conectado
  después de usarlo (D308, abierta en el banco con su reproducción). Va
  después de P8e.

## 1. Qué cambia

| Acción | Paso |
|---|---|
| Añadir carga distribuida o lineal (el clic final) | Set load |
| *Seismic Load* | Set seismic load |
| *Seismic Records* | Seismic records |
| *Delete Load* y clic derecho → Borrar | Delete loads |
| Clic derecho → Modificar y *Modify Load* | Set load |
| *Define Support* | Define support types |
| Añadir soporte, Propiedades y *Modify Support* | Set support |
| Añadir patrón | Add support pattern |
| Borrar soporte (clic o clic derecho) | Delete supports |
| Estirar | Stretch support |
| Clic derecho → Modificar patrón | Modify support pattern |
| *Move Support* | Move support |
| *Ungroup Support Pattern* | Ungroup support pattern |

- **Los menús de clic derecho** de cargas y soportes reparten por acción: el
  paso lleva el nombre de lo que se hizo, y estirar (que solo entra en un
  modo) no deja paso.
- ***Modify Load*:** cancelar la segunda pregunta devuelve `STEP_CANCELLED` y
  la carga queda como estaba.
- **El inventario:** salen las 16 excepciones, y `BUDGET` baja de 41 a 25.

## 2. Tests

`tests/test_undo_loads_supports_v1304.py`. Por cada sitio: aceptar deja un
paso con su nombre; deshacer devuelve el JSON exacto y rehacer el aceptado;
cancelar no deja paso. Además:
- *Modify Load* cancelado en la segunda pregunta deja la carga intacta;
- un soporte de la ventana, una carga del agente y un borrado de la ventana se
  deshacen y rehacen en orden.

Con el código de 0.1.303 fallan los 13 casos: ningún sitio dejaba paso
(`([], [])`). Se corrió sobre una copia del árbol de 0.1.303 sin el buscador
editable.

## 3. Verificación

- **Suite entera:** 6006/6006, código de salida 0, a la primera.
- **Los tests vecinos** (cargas, soportes, deshacer, versión, i18n, menús):
  488/488 antes de lanzarla.

## 4. Pendiente

- 0.1.305: ajustes y búsqueda, estadística, superficies y foco, anotaciones,
  DXF y terminal; D306; el cierre de D292 y D306 en el banco.
