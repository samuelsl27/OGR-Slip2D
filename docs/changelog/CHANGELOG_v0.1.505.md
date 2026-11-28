# OGR Slip2D v0.1.505

**La fijación del núcleo sube de `ogr-core v0.2.12` a `v0.2.14`.** La 0.2.13 trae la fila del
informe de Newmark con talud arriba (D437). La 0.2.14 trae la tanda P10: D433, D443, D444, D445,
D446 y D449. Esta versión no adopta aún las fichas en la ventana ni en el agente: eso llega con una
versión por ficha, de 0.1.506 a 0.1.510.

## 0. Lo que se encontró

- **Contra el árbol de OGR-Core, antes de que se etiquetara.** El 2026-11-28 corrió la suite
  entera de `efaa846` con `--jobs 4 --dev-core` contra `0b3f0dc` (0.2.14.dev0): 7673 casos, 0
  fallos, 2 saltados, sin fugas. La etiqueta `v0.2.14` (`2bca1ad`) tiene el mismo `ogr_core`; solo
  cambia el número de versión.
- **`efaa846` (sin versión) dejó lo mínimo** para que la suite pasara con ese núcleo:
  - el castellano de los 10 códigos nuevos de `RULES`;
  - sus muestras en `tests/test_model_notes_v1347.py`, que entran solo si el núcleo las trae;
  - el castellano de la fila de 0.2.13.
- **Lo que cambia de comportamiento con este núcleo, aunque no rompe ningún test:**
  - **Regiones (D449):** cambian las de la presa de Talbingo, en `02/Problema005/modelo.ogr`,
    `02/Problema005/modelo_aguas_arriba.ogr` y `02/Problema006/modelo.ogr`:
    - aparece el filtro, de 497,35 m², que con 0.2.12 se perdía porque el extremo del contacto
      saltaba 3,6 m a un vértice;
    - *Transition* baja de 5331,80 a 5096,72 m²;
    - desaparece una astilla de *Rockfill* de 262,27 m².

    **Es el arreglo**, decidido por la propietaria con el censo delante. Los factores de Bishop,
    GLE/M-P, Janbu corregido y Spencer de los tres modelos no cambian ni un bit (A/B en el mismo
    proceso, `_auditoria/P10_D449/ab_factores_regla_a.py` del banco). Se declara también en la ficha
    del banco al cerrar D449.
  - **Informe (D446):** una coordenada o una magnitud enteras salen con sus decimales (`0` pasa a
    `0.000` en la «List of Coordinates» del talud de ejemplo). Ningún test de Slip2D fijaba un
    texto así.
  - **Borrar (D445):** `remove_boundary` quita un contorno, el objeto, y no todos los que comparten
    `id`. La ventana ya le pasaba el objeto.
  - **Convertir (D443):** `conversion_refusal` rechaza ahora convertir una superficie anisótropa
    que lee la junta de un material Generalized Anisotropic, igual que el borrado. Llega por el
    camino que ya tienen los dos Convertir.

## 1. Qué cambia

- `pyproject.toml`: `ogr-core @ …@v0.2.14`, con su comentario. El `.venv` se reinstaló con
  `--no-deps --force-reinstall` desde la etiqueta.
- `AGENTS.md`: la fijación que cita (dos sitios).
- `tests/test_report_seismic_v1449.py`: lo que pedía la 0.2.13. `TestANetNewmarkRun`, 4 tests, sobre
  el plano de 0.1.429 con talud arriba:
  - la premisa (`net_newmark`);
  - la fila «the one with the largest net Newmark displacement of this method», con el
    desplazamiento de la crítica;
  - el control sin talud arriba;
  - el castellano.

  Más la cadena en `test_every_new_text_has_its_spanish`. Contra 0.2.12 fallan, porque allí la
  fila sigue siendo la del menor Ky.

## 2. La fila de Slip2D en `docs/consumidores.md` de OGR-Core

Para que la lleve la propietaria a esa sesión:

```
| OGR Slip2D | `samuelsl27/OGR-Slip2D` | `v0.2.14` | su v0.1.505 (`e3fe92b`) | `QT_QPA_PLATFORM=offscreen python tests/_runner.py --jobs 4` |
```

## 3. Tests

- `test_report_seismic_v1449`: 25 de 25 con 0.2.14 instalada.
- Suite entera con `--jobs 4` en `d439a93` (0.1.505 más los textos de D433), con 0.2.14 instalada: 7677
  casos, 0 fallos, 2 saltados, sin fugas ni tramos caídos. La primera, en `e3fe92b`, salió igual pero no vale:
  esta sesión tocó cuatro archivos de textos del agente mientras corría. Subida a GitHub tras la segunda
  (`67faf4f..d439a93`).
- **Banco**: D442 (CUBIERTO POR TEST) y D433 (CIERRE DOCUMENTAL) retiradas el 2026-11-28, con la instantánea
  `Evaluaciones/0.1.505`; se abre D467 (el falso 0 de Bishop), en P10, leída y sin medir.

## 4. Pendiente por ficha (0.1.506–0.1.510)

| Versión | Ficha | Qué |
|---|---|---|
| 0.1.506 | D443 | los dos Convertir y el `change_type` del agente llaman a `relink_on_conversion`, con la nota de cada cambio; los dos borrados, a `unlink_on_removal`; `stale_surface_links` en `project_validate` |
| 0.1.507 | D444 | Convertir herramienta en contorno pregunta `boundary_refusal(..., polyline=)`, e Importar DXF pregunta `import_refusal`; el agente deja sus dos comprobaciones propias; el castellano de los `Refusal` nuevos |
| 0.1.508 | D445 | `read_notes` al abrir, en la ventana y en `project_open`; `duplicate_id_notes` en `project_validate` |
| 0.1.509 | D446 | solo tests: las celdas con tres decimales y una cuenta sin ellos |
| 0.1.510 | D449 | `contacts_welded` en la barra y en `project_validate` |
