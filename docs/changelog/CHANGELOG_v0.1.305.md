# OGR Slip2D v0.1.305

**Las últimas ediciones de la ventana son pasos de deshacer, y Cancelar
cancela (D292, D306).** Cuarta y última versión de la tanda P8e: cierra D292 y
D306.

## 0. Lo que se encontró

- **La tercera familia de D292.** Son 23 métodos:
  - ajustes y búsqueda: *Project Settings*, *Surface Options*, *Auto Grid*,
    *Add Grid*, límites del talud y eje de momentos;
  - estadística: *Random Variables*;
  - superficies y foco;
  - anotaciones y *Convert Tool to Boundary*;
  - *Import DXF*.

  Además está *Back Analysis*, que escribía los ajustes.
- **«Cancelar no cancela» (D306), los cuatro casos confirmados:**
  - ***Project Settings*:** Aplicar y Restaurar escriben en los ajustes vivos
    al momento y sin avisar a la ventana. Cancelar después no los devolvía, y
    los menús de agua y estadística no se enteraban de lo aplicado;
  - ***Surface Options*:** su *Optimize Settings* escribe al aceptarse
    (`_on_optimize_settings`). Cancelar *Surface Options* lo dejaba escrito,
    y los dos docstrings se contradecían;
  - ***Add Grid*** no es modal. El rectángulo elegido en el lienzo se escribía
    en los ajustes al elegirlo, antes de Aceptar, y Cancelar no lo devolvía.
    Una elección armada tras cancelar escribía igual;
  - ***Annotations*** edita la capa con cada botón y solo tenía Aceptar: Esc
    lo dejaba todo hecho, sin marcar el proyecto ni redibujar.
- **La terminal** ejecutaba Python sobre el modelo sin paso ni aviso.
- **Deshacer un cambio de *Project Settings > Statistics*** no refrescaba el
  menú *Statistics*. D281 lo había hecho para el menú del agua.
- **Un defecto aparte, que encontraron estos tests: *Define Limits* fallaba
  siempre.** `_move_slope_limits` comparaba la respuesta del diálogo con
  `dlg.Accepted`. Con PySide6 6.11 ese atajo del enumerado existe en la clase
  (`QDialog.Accepted == 1`) pero no en una instancia, así que aceptar
  *Surfaces → Slope Limits → Define Limits* lanzaba `AttributeError` y no
  guardaba los límites. Ningún test llegaba a esa línea. Se reportó a la
  propietaria el 2026-10-13 antes de corregirlo.

## 1. Qué cambia

| Acción | Paso |
|---|---|
| *Project Settings*, *Surface Options*, *Auto Grid*, *Add Grid*, límites del talud, eje de momentos | Change settings |
| *Random Variables* | Random variables |
| Añadir foco / activar o desactivar | Set focus object |
| Borrar foco | Delete focus objects |
| Añadir superficie (centro y radio, tres puntos) | Add user surface |
| *Manage Surfaces* | Delete user surfaces |
| Dibujar, imagen, mostrar u ocultar anotaciones | Set annotation |
| *Delete All Annotations* | Delete annotations |
| *Manage Annotations* | Edit annotations |
| *Convert Tool to Boundary* | Add {tipo}, como `annotation_to_boundary` |
| *Import DXF* | Import DXF |
| Una orden de la terminal que cambie el modelo | Python script |

- **D306, Cancelar cancela** (decisión de la propietaria: lo aplicado
  incluido):
  - ***Project Settings*:** el paso envuelve el diálogo. Cancelar devuelve
    los ajustes con los que se abrió. Aplicar y Restaurar avisan
    (`settings_applied`), y la ventana refresca los menús en el momento;
  - ***Surface Options*:** Cancelar devuelve también lo escrito por su
    *Optimize Settings*. Los dos docstrings dicen ya lo mismo;
  - ***Add Grid*:** el clic en el lienzo solo rellena las casillas. Aceptar
    escribe los límites, nx y ny en un paso. Cancelar desarma una elección
    pendiente;
  - ***Annotations*:** tiene Cancelar. Cancelar o Esc devuelven la capa;
    Aceptar deja un paso.
- ***Back Analysis* ya no escribe `settings.back_analysis`** (decisión de la
  propietaria, como `back_analysis_run`):
  - los valores van al cálculo como argumentos;
  - los últimos tecleados vuelven la vez siguiente para ese proyecto, sin
    marcarlo como modificado;
  - desaparece la escritura de `enabled`, que nadie leía.
- **La terminal** (decisión de la propietaria): cada orden que cambie el
  modelo es un paso «Python script», como `python_exec`. Una orden que llama
  a un método de la ventana que ya es un paso sigue siendo uno solo, por la
  reentrancia de `_model_step`. Una que no cambia nada no deja paso.
- **El menú *Statistics*** se refresca en cada evento del proyecto, también
  al deshacer.
- ***Define Limits*** comprueba `if not dlg.exec()`, como el resto de la
  ventana, en lugar de `dlg.Accepted`.
- **El inventario** de `test_window_undo_v1301`: salen las 23 excepciones, y
  `BUDGET` baja de 25 a 2. Las dos que quedan son las dos mitades del
  arrastre de vértices, que registran el arrastre entero como un solo
  `ReplaceBoundaryCommand`. El docstring de `act_undo` las nombra.
  `AddGridDialog` sale de la lista de diálogos que escriben, porque ya no
  escribe por su cuenta, y su `apply_to_settings` entra en la de métodos que
  escriben.

## 2. Tests

`tests/test_undo_settings_annotations_v1305.py`:
- **los cuatro de D306:**
  `test_project_settings_cancel_after_apply_restores` (Aplicar llega a los
  menús mientras el diálogo está abierto, y Cancelar lo devuelve; Restaurar
  y Cancelar), `test_surface_options_cancel_drops_optimize_settings`,
  `test_add_grid_cancel_drops_the_picked_rectangle` (con la elección armada
  tras cancelar) y `test_annotations_cancel_restores_the_layer`;
- **cada sitio de la familia:** aceptar es un paso con su nombre, deshacer y
  rehacer devuelven el JSON exacto, y cancelar no deja paso;
- ***Back Analysis*:** no escribe nada, no deja paso ni marca el proyecto, el
  valor tecleado llega al cálculo (regla 7) y vuelve la vez siguiente;
- **el menú *Statistics*** tras deshacer;
- **la terminal:** una orden sin cambios no deja paso; una con cambios deja
  uno; una que llama a *Auto Grid* deja uno solo;
- **con el agente:** una anotación, una carga del agente y *Project
  Settings* se deshacen y rehacen en orden;
- ***Define Limits*** aceptado guarda los límites y no lanza nada
  (`test_define_limits_accepted_does_not_raise`).

Con el código de 0.1.304 fallan los 16 casos. Los 15 de deshacer fallan por
no dejar paso o por no cancelar (`settings_applied` aún no existía). El de
*Define Limits* falla por la causa exacta: `AttributeError:
'SlopeLimitsDialog' object has no attribute 'Accepted'`. Se corrió sobre una
copia del árbol de 0.1.304 sin el buscador editable.

## 3. Verificación

- **Suite entera:** 6022/6022, código de salida 0, a la primera.
- **Los tests vecinos** (deshacer, guardián, ajustes, rejillas, anotaciones,
  terminal, análisis inverso, foco, superficies, DXF, estadística, límites
  del talud, versión, i18n, menús): 704/704 antes de lanzarla.
- **Banco:** `d292()` y `d306()` en el `verificar_cierres.py` de la raíz,
  registradas en `COMPROBACIONES`: las dos **CUBIERTO POR TEST**. Ciclo de
  cierre completo:
  - instantánea `Evaluaciones/0.1.305` antes y después (`--forzar`);
  - `retirar_cerrados.py --escribir D292 D306`;
  - poda de la lista P8 de `generar_prompts.py`;
  - D292 y D306 tachadas en la fila P8;
  - `generar_prompts.py`;
  - `auditoria_invariantes.py` en la raíz y en el 02, con 0 ERROR.

### Una comprobación del banco que dejó de ver

La corrida completa de `verificar_cierres.py` apartó una bajada: D297 «SIGUE
ABIERTO», porque «after_edit refresca el titulo: NO». El comportamiento estaba
intacto: `WindowHost.after_edit` sigue llamando a `self.after_save()`, y su
test (`test_material_colours_v1299`) pasó en la suite. Lo que falló fue la
comprobación: buscaba la llamada en los 600 caracteres siguientes a `def
after_edit`, y las cinco líneas que 0.1.303 añadió delante (marcar el
proyecto modificado) la dejaron fuera. `d297()` lee ahora el cuerpo entero del
método, hasta el siguiente `def`, y vuelve a cerrar: 47 comprobaciones,
0 bajadas. La bajada nació en 0.1.303, y no se vio porque en esa versión no se
cerraba ninguna ficha ni se corría `verificar_cierres.py`.

## 4. Pendiente

- **Prueba manual,** o dentro de la tercera prueba de la interfaz tras P8g:
  - alternar pasos de diálogo y del agente, y deshacer hasta el principio;
  - en *Project Settings*, Aplicar y después Cancelar;
  - en *Annotations*, Cancelar y Esc;
  - el texto de *Deshacer* con los dos idiomas.
- D307, D308 y D309, abiertas en P8, después de P8e.
