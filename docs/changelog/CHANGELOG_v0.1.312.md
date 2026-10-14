# OGR Slip2D v0.1.312

***Move Boundary* arrastrando mueve el contorno y deja un paso de deshacer
(D307).** Tercera y última versión de la tanda P8f2.

## 0. Lo que se encontró

- **La vista previa escribía sobre vértices inmutables.** Para enseñar el
  arrastre, la rama «Drag entire boundary live» de
  `CanvasView.mouseMoveEvent` movía los vértices DEL PROYECTO con `v.x = …` y
  `v.y = …`. Y `Vertex` es `@dataclass(frozen=True, slots=True)`.
- **Medido con la reproducción** (`_auditoria/P8_interfaz/repro_d307.py`,
  0.1.300):
  - el primer movimiento y la suelta lanzaban `FrozenInstanceError`;
  - `boundary_dragged` no se emitía, así que el paso de deshacer que ya
    preparaba `MainWindow._on_boundary_dragged` no se registraba;
  - el contorno no se movía.
- **Roto en todo el historial de git.** `Vertex` es inmutable desde el primer
  commit (v0.1.59), y el arrastre es de v0.1.9.
- **Ningún test tocaba** el modo, la señal ni el manejador.
- **Ni siquiera un clic sin mover funcionaba.** La suelta «restauraba» siempre
  los vértices con `v.x = …`, así que pulsar y soltar sobre un contorno con la
  herramienta activa también lanzaba `FrozenInstanceError` (lo midió el test
  nuevo en el árbol de 0.1.311).
- **Además, cada movimiento reconstruía la escena entera** (`refresh()`,
  regiones de material incluidas).
- **Lo que sí funcionaba:** el arrastre de vértices y el cuadro numérico
  *Move Boundary*.

## 1. Qué cambia

**Decisión de la propietaria (2026-10-14): un fantasma discontinuo.**

- **Al mover, el lienzo dibuja una copia discontinua del contorno**
  (`_make_drag_ghost`):
  - es un `BoundaryItem` con la pluma del contorno en trazos, sin selección ni
    *hover*, por encima del resto;
  - sigue al ratón con `setPos`;
  - el modelo no se toca y la escena no se reconstruye.
- **Al soltar, se quita el fantasma y se emite `boundary_dragged`** si hubo
  desplazamiento. `_on_boundary_dragged`, sin cambios, registra un solo
  `ReplaceBoundaryCommand` («Edit Boundary»). Ya no hay nada que restaurar.
- **Esc a medio arrastre lo cancela y deja la herramienta,** como con un dibujo
  en curso. Un segundo Esc sale de ella.
- **Un cambio de herramienta también lo cancela** (`set_tool_mode`), y como no
  se escribió nada, no hay nada que devolver.
- **`refresh_scene` olvida el fantasma,** que `scene.clear()` borra. El
  siguiente movimiento lo vuelve a crear.
- **Sale `_drag_boundary_orig_verts`.** Sin textos nuevos.

## 2. Tests

`tests/test_move_boundary_drag_v1312.py`, por el lienzo real (pulsar, mover y
soltar con `QMouseEvent`, y Esc):

- **mientras se arrastra:**
  - el proyecto no cambia (JSON);
  - el fantasma está en la escena, desplazado lo mismo que el ratón;
  - nada llega a `sys.excepthook`;
- **al soltar:**
  - el contorno se desplaza exactamente eso;
  - queda un paso «Edit Boundary» que deshacer y rehacer llevan y traen en
    JSON;
  - el fantasma ya no está;
- **un clic sin mover no deja paso;**
- **Esc a medio arrastre** lo cancela, deja la herramienta y no deja paso; el
  segundo Esc sale de ella;
- **un cambio de herramienta a medio arrastre** también lo cancela;
- **una reconstrucción de la escena a medio arrastre no lo rompe;**
- **control:** el arrastre de vértices sigue dejando un paso.

## 3. Verificación

- **Suite entera:** 6079/6079, código de salida 0, a la primera (57 min).
- **Con el código de 0.1.311 fallan 5 de los 6 casos**, todos con
  `FrozenInstanceError`. El sexto, el arrastre de vértices, es el control de lo
  que no se puede mover y pasa en los dos árboles. Se corrió sobre una copia del
  árbol de 0.1.311 sin el buscador editable.
- **Los tests vecinos**, antes de la suite: 349/349. Son el lienzo, los
  vértices, los contornos, deshacer, el dibujo, el ajuste y la superficie de tres
  puntos.
- **La reproducción** (`repro_d307.py`): sin excepción, el contorno se mueve y
  queda un paso, «Edit Boundary».
- **Banco:** `d307()` en el `verificar_cierres.py` de la raíz, registrada en
  `COMPROBACIONES`: **CUBIERTO POR TEST**. Ciclo de cierre:
  - `verificar_cierres.py` entero: 54 comprobaciones, 0 bajadas;
  - instantánea `Evaluaciones/0.1.312` antes y después (`--forzar`);
  - `retirar_cerrados.py --escribir D307`;
  - poda de la lista P8 y D307 tachada en la fila P8;
  - `generar_prompts.py`: 38 prompts y las mismas 19 FALTA;
  - `auditoria_invariantes.py` en la raíz y en el 02, con 0 ERROR.
- **Ningún número cambia:** es interfaz.
- **Tanda P8f2 terminada:** D309 (0.1.310), D308 (0.1.311) y D307 (0.1.312).

## 4. Pendiente

- A mano: un arrastre de *Move Boundary* en la ventana, con Esc a medio
  arrastre.
