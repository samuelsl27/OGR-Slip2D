# OGR Slip2D v0.1.310

***Restaurar valores* de *Ajustes de proyecto* repone solo lo que enseñan sus
páginas, y lo escribe al Aplicar o Aceptar (D309).** Primera versión de la
tanda P8f2.

## 0. Lo que se encontró

- **La ficha se quedaba corta.** Contaba 10 campos borrados: 9 de `search` y
  `back_analysis.target_fos`.
  - **Medido antes de tocar nada:** se construyen las páginas sobre un
    `ProjectSettings()` y su `apply()` se dirige a una copia con las 152 hojas
    de los ajustes cambiadas.
  - Las páginas escriben **72** campos. Los otros **80** no los enseña
    ninguna, y `_defaults` los sustituía todos, al momento y sin aviso:

    | Sección | Campos sin página |
    |---|---|
    | `search` | **los 72**: la rejilla y los límites dibujados en el lienzo, el eje, la optimización, Block Search… |
    | `back_analysis` | los 4 |
    | `groundwater` | `transient_stages` y `transient_initial_bcs`: **un transitorio configurado perdía sus etapas y su estado inicial** |
    | `statistics` | `seed` |
    | `summary` | `date_created`: se vaciaba |

- **Una premisa de la ficha era falsa.** Decía que «la página *Search* enseña
  5 de los ~70 campos».
  - La clase `_SearchPage` existía, pero **nunca estuvo en `_PAGES`**. El
    comentario de esa tupla dice desde v0.1.9 que la búsqueda vive en
    *Surface Options*.
  - Era código muerto desde el primer commit del historial (v0.1.59): el
    diálogo no enseña ningún campo de `search`.
  - Engañó a quien redactó la ficha, y por eso se borra.
- **El precedente.** *Surface Options* ya hacía lo correcto: repone sus campos
  en los controles y escribe al Aceptar.

## 1. Qué cambia

**Decisión de la propietaria (2026-10-14):** solo lo que enseñan las páginas, y
sin escribir hasta Aplicar o Aceptar.

- **`_defaults` (`ogr_gui/dialogs/project_settings_dialog.py`):**
  1. construye cada página sobre un `ProjectSettings()` nuevo, para que enseñe
     los valores por defecto;
  2. la dirige a una COPIA de los ajustes (`_part_of`, por identidad: cada
     página guarda en `self.s` los ajustes o una de sus secciones);
  3. llama a su `apply()`;
  4. reconstruye las páginas sobre la copia;
  5. no escribe nada ni avisa a la ventana.
- **No hay una segunda lista de campos.** Lo que vuelve es lo que escribe el
  `apply()` de cada página. Una segunda lista es el defecto que v0.1.74 ya
  sacó de este mismo método.
- **`_apply`:** tras *Restaurar*, copia la copia en los ajustes campo a campo
  (`_copy_fields`):
  - escribe solo lo que difiere;
  - conserva la identidad de las secciones (`settings.search` sigue siendo el
    mismo objeto).
- **Sin *Restaurar* no cambia nada:** las páginas editan los ajustes, como
  antes.
- ***Restaurar* y *Cancelar* dejan el proyecto intacto y sin paso de
  deshacer.** *Restaurar* y *Aceptar* dejan un paso «Change settings».
- **Un efecto visible.** Con el transitorio activo, *Restaurar* y *Aplicar* lo
  apagan, porque el interruptor está en la página *Groundwater*. Sus etapas y
  su estado inicial se conservan, y volver a marcarlo los recupera.
- **El botón lleva una ayuda** que dice qué repone y qué no, con `tr()` y su
  castellano.
- **`_SearchPage` se borra**, y con ella los dos imports que solo usaba.

## 2. Tests

`tests/test_restore_defaults_v1310.py`, 9 casos:

- **La reproducción,** sobre el demo:
  - hay rejilla, límites, eje, `optimize_max_iterations`, retroanálisis,
    transitorio con dos etapas y estado inicial, semilla, fecha, y un campo
    cambiado en cada página;
  - *Restaurar* no escribe nada;
  - *Aplicar* repone los diez de las páginas, comparados con un
    `ProjectSettings()` nuevo y no con literales, y no toca los demás.
- **Las 152 hojas cambiadas:**
  - tras *Restaurar* y *Aplicar*, cada una vale lo que valía o su valor por
    defecto, nunca un tercero;
  - las repuestas son exactamente la unión de lo que escribe cada página por
    su cuenta;
  - cada página repone al menos un campo (regla 7);
  - ninguna de `search` se repone.
- **El supuesto del mecanismo:** el `self.s` de toda página es los ajustes o
  una de sus secciones directas, y una parte anidada hace saltar
  `LookupError`.
- **Las secciones conservan su identidad,** y un segundo *Aplicar* tras
  *Restaurar* sigue llegando a los ajustes.
- **Por la ventana:**
  - *Restaurar* y *Aceptar* dejan un paso que conserva la rejilla, y deshacer
    y rehacer lo devuelven en JSON;
  - *Restaurar* y *Cancelar* no dejan paso.
- **Lo que se enseña tras *Restaurar*:**
  - los valores por defecto;
  - la página *Transient* cuenta las 2 etapas que se conservan;
  - su compuerta sigue al interruptor que ahora enseña *Groundwater*, apagado.

**Con el código de 0.1.309 fallan 6 de los 9**, cada uno por su causa:
- *Restaurar* escribía al momento;
- la rejilla quedaba en `None` al *Aceptar*;
- la página *Transient* contaba 0 etapas;
- las secciones cambiaban de identidad;
- `_part_of` y `_make_page` no existían.

Se corrió sobre una copia del árbol de 0.1.309 sin el buscador editable.

## 3. Verificación

- **Suite entera:** 6067/6067, código de salida 0, a la primera (unos 55 min).
- **Los tests vecinos**, antes de la suite: 274/274. Son todas las páginas del
  diálogo, deshacer, i18n y las dos cotas del ángulo de la base.
- **La reproducción** (`repro_d309.py`, que ahora mide también tras *Aplicar*):
  0 campos de `search` cambiados tras *Restaurar* y tras *Restaurar* +
  *Aplicar*; `back_analysis.target_fos` sigue en 1,7.
- **Banco:** `d309()` en el `verificar_cierres.py` de la raíz, registrada en
  `COMPROBACIONES`: **CUBIERTO POR TEST**. Ciclo de cierre:
  - `verificar_cierres.py` entero: 52 comprobaciones, 0 bajadas;
  - instantánea `Evaluaciones/0.1.310` antes y después (`--forzar`);
  - `retirar_cerrados.py --escribir D309`;
  - poda de la lista P8 y D309 tachada en la fila P8;
  - `generar_prompts.py`: 40 prompts y las mismas 19 FALTA de paquetes
    anteriores;
  - `auditoria_invariantes.py` en la raíz y en el 02, con 0 ERROR.
- **Ningún número del motor cambia:** el arreglo es de interfaz y no mueve
  ningún valor por defecto de `ProjectSettings`.

## 4. Pendiente

- A mano: *Restaurar valores* con una rejilla dibujada y un transitorio con
  etapas.
