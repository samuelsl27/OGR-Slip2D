# OGR Slip2D v0.1.228

**D218b — cada tramo de Generalized Anisotropic toma la resistencia de un
MATERIAL del proyecto, y el diálogo de materiales edita los tramos.** Es la
segunda mitad de D218, prevista en el plan de la tanda: la propietaria pidió
el 2026-09-30 «conservar las reglas y hacer el editor como el de la
referencia».

Cuarta versión de la tanda D215–D219. El banco no tiene ningún material
Generalized: cero filas movidas.

Lo que cambia en el banco de verificación (`_tools/`, `_auditoria/`, fichas)
está fuera de git.

---

## 0. Lo que se encontró y lo que se decidió

| Id | Qué pasaba | Qué hace ahora |
|---|---|---|
| D218b | 0.1.225 dejó el modelo honesto, pero el diálogo no enseñaba los tramos («en esta versión se definen por la API o por un script»), y cada regla llevaba su PROPIA copia de un modelo. La entrada «Angle Range» de la referencia asigna «a material to each range»: con copias, editar ese material, muestrearlo en un análisis probabilístico o aplicarle un coeficiente parcial no llegaba al tramo | Una regla puede nombrar su material (`material_id`). El análisis resuelve el enlace sobre SU copia del proyecto (`prepare_analysis_project`), después de los coeficientes, y calcula con la resistencia del material tal como está al calcular |
| Copia | La primera versión de esa copia, con enlaces y sin norma, era `Project.from_dict(project.to_dict())`, la misma que hace la norma. No es una identidad: el cargador migra, y lee un `max_lambda` de 1,5 como un archivo anterior a 0.1.90 y lo convierte en 6,0 (D182; `ogr_api/snapshot.py` ya lo advertía). Medido: 1,5 → 6,0 | Con enlaces y sin norma, una copia superficial con una lista de materiales propia (`_with_own_materials`): el resto se comparte, como cuando el análisis calculaba sobre el proyecto mismo, y las cachés se tiran solo en la copia. Sin enlaces no se copia nada, como antes. Con la norma activa, la copia de siempre: su alcance de D182, reportado en 0.1.194, no cambia aquí |
| Alias | `GeneralizedAnisotropic.to_dict()` entrega los MISMOS dicts de reglas (`list(self.rules)`), así que `Material.from_dict(m.to_dict())` los comparte con el original. Comprobado con un script | El código nuevo construye reglas nuevas en vez de editarlas en sitio (importar propiedades, borrar un material). `to_dict` no se toca: hoy nadie edita una regla en sitio y no mueve ningún número. Se deja dicho aquí |

**Las decisiones:**

- **Formato.**
  - Cada regla conserva su `model` (el formato de todas las versiones), que
    pasa a ser la copia que enseña el editor.
  - El `material_id` es opcional. Una regla sin él (un archivo, la API, un
    script) calcula con su modelo, como siempre.
- **Una sola factorización.** La recursión de coeficientes de Generalized
  (D224) se salta las reglas enlazadas: cada hijo se factoriza una vez, a
  través de su material. La documentación de la referencia dice que los
  coeficientes se aplican a los hijos.
- **Qué enlaces valen** (`rules.generalized_links_refusal`): un material del
  proyecto que no sea el propio Generalized ni otro Generalized. Así no hay
  ciclos. Lo preguntan el análisis, la API y el diálogo.
- **La copia que guarda la regla se refresca** solo para lo que se enseña (al
  aceptar el diálogo y en `material_set`). Nunca decide un número.
- **El editor** es la estructura de «Angle Range»:
  - cada fila es (ángulo hasta, material), y el «desde» es el final del tramo
    anterior (−90° en el primero);
  - una regla con modelo propio se enseña como «(modelo propio: …)» y se
    conserva;
  - Aceptar sin tocar devuelve las reglas idénticas (la regla de D217);
  - una selección nueva de Generalized empieza con un tramo de −90° a +90°
    que toma el primer material posible.
- **Qué juzga Aceptar.** Solo las resistencias que la sesión cambió (0.1.225),
  y además un Generalized cuyo material enlazado cambió: si ese material pasa
  a ser Generalized, Aceptar lo rechaza aunque el Generalized no se tocara.
- **Borrar un material enlazado.**
  - En el diálogo se niega, con el motivo en la etiqueta: un tramo quedaría
    apuntando a nada.
  - En la API es un conflicto, salvo con `reassign_to` (el tramo pasa al
    otro material) o `force` (el tramo conserva su resistencia, sin enlace).
- **La API enlaza por nombre**, en `model_define` y `material_set`:
  `{"angle_min": -90, "angle_max": 0, "material": "Arcilla"}`.
  - `properties_import` reenlaza con la copia importada a la vez o, si no, con
    el material del mismo nombre. Sin ninguno, el tramo conserva su
    resistencia sin enlace, y una nota lo dice.
  - El proyecto de origen no se toca.
- **Agua, desembalse y peso: los del padre.** La documentación de la
  referencia se contradice en el agua; eso sigue en D230, abierta.

## 1. Los cambios

- **`ogr_core/project/design_factors.py`:** `resolve_generalized_links`,
  `has_generalized_links`, `_with_own_materials` y
  `prepare_analysis_project`, exportadas en `ogr_core/project/__init__.py`.
- **`ogr_core/project/rules.py`:** `generalized_links_refusal`.
- **`ogr_core/materials/builtin_models.py`:** `GeneralizedAnisotropic`
  factoriza solo las reglas sin enlace; el docstring explica el enlace.
- **`ogr_core/project/properties_import.py`:** `_relink_generalized`.
- **`ogr_slip2d/analysis_runner.py`:**
  - las seis puertas del análisis llaman a `prepare_analysis_project`,
    también el `prepare` de cada muestra estadística;
  - `check_analysis_settings` pregunta la regla de los enlaces.
- **`ogr_gui/interpret_window.py`:** la misma copia.
- **`ogr_gui/dialogs/material_properties_dialog.py`:**
  - el panel: la tabla `rules` (una columna de elección, sin magnitud),
    `set_rule_materials`, `_choice_combo`, `_rules_from_table` y
    `_TABLE_CAPTIONS`;
  - el diálogo: `_rule_choices_for`, la carga de las reglas, `_store` sin el
    arrastre de 0.1.225 (el panel ya las devuelve), `_ok` (refresco y juicio
    de enlaces), `_remove_material` y los mensajes;
  - la fórmula dice «material per range».
- **`ogr_api/ops/model.py`:** `_link_rules_by_name`, `_check_links`, el
  refresco en `material_set` y los enlaces en `material_delete`.
- **`ogr_mcp/guide.py` y `docs/mcp/herramientas.md`:** cómo se enlaza un tramo
  y qué hacen el borrado y la importación.
- **`ogr_gui/i18n/__init__.py`:** diez entradas nuevas y dos retiradas (las
  que decían «por la API o por un script»).

## 2. Tests

- **`tests/test_generalized_links_v1228.py` (36 casos):**
  - **la identidad, en los nueve métodos y por la puerta del análisis:** un
    Generalized que enlaza materiales Mohr-Coulomb es la función anisótropa
    con las filas de esos materiales, con copias CADUCADAS en las reglas (solo
    da si decide el material), a 1e-12;
  - editar el material mueve F a lo que da la función con la fila editada
    (regla 7);
  - el proyecto del usuario, intacto; sin enlaces, sin copia; `max_lambda`
    1,5 sigue siendo 1,5;
  - una muestra estadística del material llega al tramo, y la estadística
    prepara cada muestra como el análisis;
  - los coeficientes, una sola vez, con enlace y sin él;
  - la regla: colgante, a sí mismo, a otro Generalized; el análisis por
    nombre; la resolución deja los enlaces malos para la regla;
  - la API: enlace por nombre, material aún no definido, a sí mismo,
    refresco, conflicto al borrar, `reassign_to`, `force`, destino
    Generalized;
  - la importación: con la copia, por nombre, sin enlace, y el origen intacto;
  - el diálogo: la tabla, las elecciones, Aceptar sin tocar, una edición, el
    modelo propio, «+ Row», un ángulo que no es número, quitar un material
    enlazado, el refresco al aceptar, un material enlazado que pasa a
    Generalized, una selección nueva, y la guarda de traducciones de los
    rótulos.

  Contra 0.1.227 fallan 34 de 36: 22 por comportamiento, 11 por símbolo y 1
  por estructura (el AST de la estadística). Pasan los dos controles: el
  proyecto del usuario intacto, y Aceptar sin tocar, que ya cumplía D218.
- **Cambia a propósito `tests/test_back_analysis_loads_v1220.py`:** su AST
  pide `prepare_analysis_project` donde pedía `apply_design_factors`, porque
  la copia de análisis la hace ahora esa función.

## 3. El banco

- **D218b** no estaba en ERRORES: el plan la preveía como subdivisión, pero no
  se abrió. Se abre y se retira en el mismo ciclo, y su fila entra en el índice
  de cerrados y en la cadena de P1, tachada, detrás de D218. La cabecera dice
  ahora que D112b y D218b no consumen número.
- **`d218b()`**, con cinco comprobaciones en vivo:
  - la identidad con copias caducadas: Bishop 0,731609, Spencer 0,754975;
  - editar el material mueve F: 0,731609 → 0,747789;
  - `max_lambda` intacto;
  - el enlace colgante, rechazado;
  - el diálogo;

  y además el código (8 llamadas a `prepare_analysis_project` y 0 a
  `apply_design_factors` en el runner y la ventana de interpretación), el
  banco y la discriminación.
- **Contra 0.1.227, NO SE SOSTIENE por comportamiento:** la identidad da
  2,893 frente a 0,732, la edición no mueve F, el enlace colgante no se
  rechaza y no hay tabla. También por símbolo y por código.
- **Cero filas.**

## 4. Caminos equivocados

- **La copia con enlaces y sin norma empezó siendo un viaje por el
  cargador.** Se leyó `ogr_api/snapshot.py` para otra cosa y ahí estaba
  escrito por qué no.
- **`_relink_generalized` editaba en sitio los dicts de las reglas del
  material importado.** Esos dicts son los del proyecto de origen, así que
  habría reenlazado el material del otro proyecto. Se vio al razonar sobre
  `to_dict` y se comprobó con un script antes de ejecutar la importación.
  `material_delete` hacía lo mismo sobre el proyecto vivo: allí no rompía
  nada, porque el deshacer copia con `deepcopy`, pero la copia de análisis de
  la norma sí comparte esos dicts. Se cambió igual.
- **La discriminación se lanzó primero con `PYTHONPATH` apuntando al árbol
  viejo, y pasaban 36 de 36.** El runner pone su propio árbol el primero en
  `sys.path`, y su línea `tree:` lo decía: el repositorio, @ b17f3f7. Se
  repitió desde dentro del árbol archivado. La cabecera del registro de
  0.1.227 dice `PYTHONPATH`, pero su línea `tree:` muestra que aquella corrida
  sí se hizo desde dentro.
- **El cierre `d218b()` fallaba primero contra 0.1.227 solo por un
  `import`.** Se reordenó para que la identidad y la edición discriminen por
  comportamiento.
- **Dos tests del diálogo fallaron por culpa del test, no del código:**
  - `findChildren` devolvía primero el «+ Row» de una tabla anterior, que
    `deleteLater` todavía no había borrado;
  - un material enlazado no puede pasar a ser Generalized, y el caso lo
    intentaba con Sand, que G enlaza.
- **Un comando de más de 8 KB se cortó en Bash.** Los scripts de edición
  largos se escriben a archivo.

## 5. Verificación

| Comprobación | Resultado |
|---|---|
| Selecciones dirigidas | 465 casos de las áreas vecinas y 73 de los enlaces, en verde |
| Suite entera | 5094 de 5094 |
| `d218b()` | CUBIERTO POR TEST; NO SE SOSTIENE contra 0.1.227 |
| `--seco` completo | 167 cierres; 0 bajadas, 0 subidas, 0 nuevas |
| `auditoria_invariantes.py` | 0 ERROR en el 02 y en la raíz |

**Queda por probar a mano:**
- el editor de tramos en la ventana real: elegir, añadir y quitar filas;
- un proyecto con un Generalized que enlaza materiales, guardado y vuelto a
  abrir;
- importar propiedades desde un `.ogr` con enlaces.
