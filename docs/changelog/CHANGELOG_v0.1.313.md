# OGR Slip2D v0.1.313

**Un soporte de longitud cero se rechaza en todas las puertas, y el análisis lo
nombra (D313).** Primera versión de la tanda P8g.

## 0. Lo que se encontró

- **De dónde sale.** Al escribir el test de D308 (0.1.311), los dos clics de
  *Add Support* cayeron en el mismo vértice y el soporte salió con la cabeza
  igual a la cola. Se abrió D313 a petición de la propietaria.
- **La regla vivía en una sola puerta.** Desde la spec 008, solo `support_set`
  rechazaba «head and tail coincide.», con una comparación exacta. Ni la
  ventana ni el núcleo lo comprobaban.
- **Tres caminos de la ventana lo dejaban pasar.** Medidos con
  `_auditoria/P8_interfaz/repro_d313.py`:
  - *Add Support* con dos clics en el mismo punto;
  - *Stretch Support* llevando una punta sobre la otra;
  - el diálogo de propiedades del soporte, tecleando las mismas coordenadas
    (leído en el código, y medido por el test nuevo).
- **El patrón de soportes no puede:** su longitud tiene un mínimo de 0,01 m.
- **Lo que hacía el análisis.** El factor era el del talud sin refuerzo (FS
  1,091433 en el demo, el mismo que sin el soporte), y la razón decía «it does
  not cross that surface». Es cierto, pero manda a arreglar lo que no es.

## 1. Qué cambia

**Decisión de la propietaria (2026-10-14):** las puertas, el aviso y una razón
propia en el análisis.

- **Núcleo (`ogr_core/project/rules.py`):**
  - `support_has_no_length(project, head, tail)`;
  - `degenerate_supports(project)`;
  - las claves `SUPPORT_NO_LENGTH` y `SUPPORT_NO_LENGTH_IN_MODEL`.
- **La tolerancia es relativa al modelo** (`support_length_tolerance`): una
  milmillonésima de la diagonal de su rectángulo envolvente. El mismo modelo en
  milímetros y en metros da el mismo veredicto.
- **Las cuatro puertas la preguntan:**
  - ***Add Support*** no escribe y lo dice en la barra de estado. No queda paso
    de deshacer y la herramienta sigue activa (D308).
  - ***Stretch Support*** no escribe, lo dice y vuelve a SELECT, como siempre
    tras estirar.
  - **El diálogo de propiedades** comprueba ANTES de escribir nada, ni siquiera
    el nombre. No cierra, y lo dice en una etiqueta del propio diálogo, sin
    nada modal.
  - **`support_set`** pregunta la regla y conserva sus palabras, «head and tail
    coincide.», que un agente puede estar leyendo.
- **`project_validate`** nombra el soporte de longitud cero que venga en un
  `.ogr` o de un guion.
- **El análisis da su propia razón:** `SUPPORT_NO_LENGTH` («has no length: its
  head and tail coincide»), en el grupo de la tabla de D62 que describe entrada
  rota.
  - Se decide solo cuando el soporte ya no cruza la superficie y se piden las
    razones, así que el cálculo normal no paga nada.
  - No mueve ningún factor.
- **El mensaje de la ventana**, con su castellano: «Un soporte necesita dos
  puntos distintos: su cabeza y su cola coinciden.»

## 2. Tests

`tests/test_zero_length_support_v1313.py`, 10 casos:

- **la regla:**
  - es relativa: el mismo modelo a escala 1 y 1000, con un soporte de 1 µm
    (tiene longitud) y otro de 1e-11 (no la tiene);
  - lee vértices y pares;
- **las tres puertas de la ventana, por el lienzo real** (mostrado y sin
  ajuste):
  - ni se escribe ni queda paso, y el mensaje sale en castellano;
  - *Add Support* sigue en su modo;
  - control: un soporte normal entra y un estirado normal mueve;
- **el diálogo de propiedades** no escribe ni el nombre tecleado, y acepta con
  dos puntos distintos;
- **el API** rechaza al crear y al editar, con las mismas palabras;
- **`project_validate`** lo nombra, y no dice nada de un soporte normal;
- **el análisis:**
  - la razón es `no_length` y ninguna otra, y un soporte real que no cruza
    conserva `no_crossing` (control);
  - el factor es el de sin soporte, dígito a dígito (la identidad de D62);
  - la nota dice «no length» y no lleva la pareja «stable» + «head» que el
    banco reserva a D40.

**Con el código de 0.1.312 fallan 8 de los 10:**
- las tres puertas de la ventana porque escriben;
- `project_validate` porque no dice nada;
- la nota porque dice «does not cross»;
- y las importaciones de lo nuevo.

Los dos que pasan son controles: el factor idéntico y el API, que ya rechazaba.
Se corrió sobre una copia del árbol de 0.1.312 sin el buscador editable.

## 3. Verificación

- **Suite entera:** 6089/6089, código de salida 0, a la primera (54 min).
- **Los tests vecinos**, antes de la suite: 516/516. Son soportes, deshacer,
  D308, MCP, i18n y el API.
- **La reproducción** (`repro_d313.py`):
  - *Add Support* con dos clics en el mismo punto deja 0 soportes;
  - *Stretch Support* deja el soporte con 6,52 m;
  - el API rechaza igual;
  - el análisis da FS 1,091433 con la nota «it has no length: its head and
    tail coincide».
- **Banco:** `d313()` en el `verificar_cierres.py` de la raíz: **CUBIERTO POR
  TEST**. Ciclo de cierre:
  - `verificar_cierres.py` entero: 55 comprobaciones, 0 bajadas;
  - instantánea `Evaluaciones/0.1.313` antes y después (`--forzar`);
  - `retirar_cerrados.py --escribir D313`;
  - poda de la lista P8 y D313 tachada en la fila P8;
  - `generar_prompts.py`: 38 prompts y las mismas 19 FALTA;
  - `auditoria_invariantes.py` en la raíz y en el 02, con 0 ERROR.
- **Ningún número cambia:** el soporte de longitud cero ya no daba fuerza.

## 4. Pendiente

- A mano: dos clics en el mismo punto con *Add Support*, y el diálogo de
  propiedades con las mismas coordenadas.
