# OGR Slip2D v0.1.311

**`segment_picked` tiene un solo dueño, y lo que una acción deja armado se
olvida al salir de su modo (D308).** Segunda versión de la tanda P8f2.

## 0. Lo que se encontró

- **Cinco modos, una señal.** La emite el lienzo tras dos clics en cinco modos:
  - carga distribuida;
  - rectángulo de la rejilla;
  - *Add Support*;
  - patrón de soportes;
  - estirar un soporte.
- **Cada acción gestionaba solo su propio manejador:** lo conectaba antes del
  gesto y lo desconectaba después.
  - `_on_add_support_picked` **se reconectaba a sí mismo** tras cada soporte,
    para colocar varios seguidos.
  - El Esc del lienzo solo vuelve a SELECT: nada desconecta.
- **Medido con la reproducción** (`_auditoria/P8_interfaz/repro_d308.py`,
  0.1.300): *Add Support* y dos clics, Esc, *Add Distributed Load* y dos clics
  en la coronación. Resultado: **2 soportes** y 1 carga.
- **Lo mismo en pequeño:**
  - la carga pendiente (`_pending_dist_load`) y el patrón activo sobrevivían a
    Esc;
  - una rejilla armada y abandonada con Esc seguía conectada. Los dos clics de
    otra herramienta iban también al diálogo de la rejilla, y su manejador
    devolvía el lienzo a SELECT, sacando a esa herramienta de su modo.
- **Lo que hace exacto un despachador:**
  - el lienzo emite la señal solo en esos cinco modos;
  - un clic pendiente no sobrevive a un cambio de modo (D101, 0.1.168);
  - así que el modo en el instante de emitir es el modo en el que se dieron
    los dos clics.
- **Fuera de alcance:** `point_picked` (carga puntual) y `support_clicked`
  (*Delete Support*) usan el mismo idioma de conectar por acción. Tienen un
  solo consumidor y hoy no fallan.
- **Al escribir el test, una trampa del lienzo sin mostrar.** Dentro de una
  ventana que no se ha mostrado, `canvas.resize(900, 600)` no actúa:
  - el lienzo mide 98 × 28 px, a 0,69 px por unidad;
  - la tolerancia de 12 px del ajuste a vértices equivale a unos 17 m;
  - todos los clics del demo caían en (35, 15);
  - es lo que hacía la reproducción, que sigue valiendo para contar.

  El estirado del primer borrador no cambiaba nada por eso. El test sigue a
  `test_add_surface_three_points_v1168`: `resize`, `show()` y sin ajuste.
- **Reportado y NO corregido (no es de D308).** *Add Support* acepta un soporte
  de longitud cero, con la cabeza igual a la cola, cuando los dos clics caen en
  el mismo punto. Con el lienzo de arriba fue el soporte (35, 15) → (35, 15).

## 1. Qué cambia

**Decisión de la propietaria (2026-10-14): un despachador único.**

- **`MainWindow.__init__` conecta `segment_picked` una vez** a
  `_on_segment_picked`. Este reparte el gesto por el modo del lienzo con un
  diccionario modo → manejador, y en cualquier otro modo no hace nada.
- **Las cinco acciones y sus manejadores dejan de conectar y desconectar.**
  Solo fijan lo pendiente y el modo.
  - *Add Support* sigue en su modo para colocar varios seguidos, ya sin
    reconectarse.
  - Cancelar la rejilla solo devuelve el modo.
- **`_forget_pending_picks`, conectado a `tool_mode_changed`,** olvida la carga
  y el patrón cuando el modo nuevo no es el suyo (Esc u otra herramienta).
  - La rejilla armada es el modo mismo, así que salir de él la desarma.
  - Las acciones fijan lo pendiente antes de cambiar de modo, así que entrar en
    él no lo borra.
- **El comentario de D101 en `__init__`,** que explicaba el armado y desarmado
  por acción, se actualiza.
- **Sin textos nuevos.** El inventario de deshacer no cambia: el despachador no
  escribe el modelo y solo llama a métodos `@undo_step`.

## 2. Tests

`tests/test_segment_picked_owner_v1311.py`, por el lienzo real (eventos de
ratón y Esc):

- **la reproducción:** 1 soporte y 1 carga;
- **las cinco acciones encadenadas con Esc:**
  - cada gesto de dos clics escribe UNA cosa y deja un paso (el rectángulo de
    la rejilla va al diálogo abierto, no al modelo);
  - dos clics tras Esc no escriben nada;
  - la señal tiene exactamente un receptor después de cada acción
    (`QObject.receivers`);
- **Esc y un cambio de herramienta olvidan la carga y el patrón;**
- **una rejilla abandonada no recibe los clics de *Add Support*,** que sigue
  en su modo;
- ***Add Support* coloca tres seguidos sin salir de su modo:** tres pasos.

## 3. Verificación

- **Suite entera:** 6073/6073, código de salida 0, a la primera (53 min).
- **Con el código de 0.1.310 fallan 5 de los 6 casos**, cada uno por su causa:
  dos soportes, dos receptores, la carga que sobrevive a Esc y la rejilla
  abandonada que toma los clics. El sexto, tres soportes seguidos, es el
  control de lo que no se puede mover y pasa en los dos árboles. Se corrió
  sobre una copia del árbol de 0.1.310 sin el buscador editable.
- **Los tests vecinos**, antes de la suite: 681/681. Son soportes, cargas,
  rejillas, la superficie de tres puntos, deshacer, menús y F2.
- **La reproducción** (`repro_d308.py`): 1 soporte y 1 carga.
- **Banco:** `d308()` en el `verificar_cierres.py` de la raíz, registrada en
  `COMPROBACIONES`: **CUBIERTO POR TEST**. Ciclo de cierre:
  - `verificar_cierres.py` entero: 53 comprobaciones, 0 bajadas;
  - instantánea `Evaluaciones/0.1.311` antes y después (`--forzar`);
  - `retirar_cerrados.py --escribir D308`;
  - poda de la lista P8 y D308 tachada en la fila P8;
  - `generar_prompts.py`: 39 prompts y las mismas 19 FALTA;
  - `auditoria_invariantes.py` en la raíz y en el 02, con 0 ERROR.
- **Ningún número cambia:** es interfaz.

## 4. Pendiente

- A mano: la secuencia de la reproducción en la ventana.
