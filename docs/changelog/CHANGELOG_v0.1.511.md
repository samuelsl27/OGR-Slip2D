# OGR Slip2D v0.1.511

**D449: una capa fina entre dos contactos vuelve a ser una región, y cuando el soldado aún une dos
contactos, la ventana y el agente lo dicen.** La decisión fue A + C, de la propietaria, tomada el
2026-11-27 con el censo del banco delante. Las reglas están en OGR Core 0.2.14, que Slip2D fija desde
0.1.505:
- **A** está en el constructor de regiones: un extremo que ya está sobre un segmento no salta a un
  vértice;
- **C** es `rules.contacts_welded`.

## 0. Lo que se encontró

- **El defecto.** El soldado de extremos llevaba un extremo que ya estaba sobre el exterior al
  vértice más cercano dentro de su tolerancia (el 0,8 % de la diagonal), y dos contactos casi
  paralelos perdían la capa que había entre ellos. En el bloque de 100 × 30 de la ficha se perdía
  cualquier capa de menos de 0,9 m (medido con 0.1.462).
- **El censo del banco con 0.1.503** (`_auditoria/P10_D449/medir_regla_a.py`, 230 modelos, 0
  errores) encontró **tres modelos cuyas regiones cambian con A**: la presa de Talbingo, en
  `02/Problema005/modelo.ogr`, `02/Problema005/modelo_aguas_arriba.ogr` y
  `02/Problema006/modelo.ogr`.
  - El extremo del contacto del filtro, en (310,7; 0), estaba sobre la base y saltaba 3,6 m al
    vértice (307,1; 0), así que la banda del filtro no existía.
  - Con 0.2.14 aparece el filtro, de 497,35 m², *Transition* baja de 5331,80 a 5096,72 m², y
    desaparece una astilla de *Rockfill* de 262,27 m².
  - La ficha del 005 ya lo anotaba: «puntos dentro del filtro devuelven Transition».
  - **Es el arreglo, y se declara aquí.** Los factores de Bishop, GLE/M-P, Janbu corregido y Spencer
    de los tres modelos **no cambian ni un bit**: A/B en el mismo proceso, con el original, A y el
    original otra vez (`_auditoria/P10_D449/ab_factores_regla_a.py`). Los tres materiales tienen las
    mismas propiedades (c′ 0, φ′ 45°, γ 20,4).
- **Lo que la regla C avisaría hoy en el banco:** nada. Antes eran esos tres modelos, con la fusión de
  3,6 m.
- **Una trampa de la medida, corregida en el guion del banco.** El primer censo contaba las fusiones
  sobre el constructor original, que no tiene el gancho, y daba 0. Se cuentan sobre la copia sin la
  regla, que reproduce el original región a región.

## 1. Qué cambia

- `ogr_gui/main_window.py`:
  - `_say_welded_contacts` (nuevo) dice en la barra, en el idioma del lector, qué dos contornos de
    material une el soldado y dónde. Lo dice una vez para las mismas uniones (guía D-14), y otra vez
    solo si el modelo deja de tenerlas;
  - se pregunta tras las ediciones de contornos, con un temporizador de 400 ms
    (`_GEOMETRY_EVENTS`), porque construir las regiones no sale gratis en cada evento, y también al
    abrir, si la lectura no ha ocupado ya la barra.
- `ogr_api/ops/project.py`: `project_validate` avisa con `contacts_welded` (con código).

El castellano del aviso entró en `efaa846`.

## 2. Lista de comprobación de la guía de interfaz

- Mensaje: dice qué dos contornos, a qué distancia y dónde se unieron, y qué hacer («Move them apart,
  or end them on the same point.»), en el idioma del lector, una vez y sin diálogo modal.
- Coste: el aviso no se calcula en cada evento, sino cuando las ediciones paran.
- Ninguna acción ni menú nuevos.

## 3. Tests

- `tests/test_endpoint_weld_d449_v1511.py` (nuevo, 6 tests, una ventana para todo el archivo; el
  caso es el bloque de la ficha):
  - con los contactos acabando en el exterior, tres regiones y la capa de 100 × 0,5 = 50 m², la
    solución cerrada, a 1e-5 relativo, sin aviso ni en la barra ni en `project_validate`;
  - con los contactos más allá del exterior, la capa se funde (la premisa), la barra dice qué dos
    contornos y lo dice una sola vez, y `project_validate` avisa con `rule.contacts_welded`;
  - añadir un contorno pone en marcha la comprobación.

  Contra 0.1.510 fallan 4 de 6. Los dos de las regiones pasan, porque el arreglo es del núcleo, que
  ya está fijado.
- Áreas `region`, `lens`, `contact`, `weld`, `boundary`, `undo`, `open`, `mcp`, `api` y `status`,
  con `--jobs 4`: 400 en verde.

## 4. Suite y banco (cierre de la tanda 0.1.503–0.1.511)

- **Suite entera** con `--jobs 4` en `382b65c` y ogr-core 0.2.14 instalado: 7720 casos, 0 fallos, 2
  saltados, sin fugas ni tramos caídos. La última serie en verde fue hace 54 commits (toca a los 100).
- **Banco**, el 2026-11-28:
  - D443, D444, D445, D446 y D449 salen CUBIERTO POR TEST en el `verificar_cierres.py` de la raíz,
    cada una con una medida en vivo; se retiran con la instantánea `Evaluaciones/0.1.511`;
  - quedan 33 prompts, sin ninguna FALTA, y 0 ERROR en las dos auditorías de invariantes;
  - la nota de modelado de la ficha del 005 dice ya que el filtro se resolvió.

  P10 sigue abierto con D450, D455, D456, D463 y D467.
