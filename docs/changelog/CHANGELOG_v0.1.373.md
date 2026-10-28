# OGR Slip2D v0.1.373

**El runner de tests deja de acumular dos cosas que encarecían la suite cuanto más avanzaba.** Tras cada
archivo devuelve `sys.path` y las dos carpetas de la corrida a como estaban. Además, congela con
`gc.freeze()` lo que sobrevive a la colección que ya hacía entre archivos. Es la etapa 1 del plan que
salió de la auditoría de la suite (`docs/audits/AUDITORIA_SUITE_v0.1.372.md`), aprobado por la
propietaria. **Ningún módulo del programa cambia**, salvo el número de versión.

## 0. Lo que se encontró

La auditoría midió la suite entera de 0.1.372 con un instrumento externo, sin tocar el árbol. Todo está en
el informe; aquí, lo que lleva a esta versión.

- **La mitad del «2–2½ h» era la máquina.** `TextInputHost.exe`, el teclado táctil de Windows, llevaba
  girando un núcleo desde el 22-10, con 92 h de CPU. Hacía todo un 40–50 % más lento, también el código de
  un solo hilo. Coincide con la tanda P8l, cuando la suite saltó de 54–62 min a 91–151.
  - Cerrado, la suite entera tarda **87,6 min** con los 6628 casos en verde.
  - La lección queda en AGENTS.md en la etapa 4: antes de llamar anomalía a una duración, mira qué procesos
    comen CPU.
- **El `gc.collect()` del runner entre archivos costaba 13,6 de esos 87,6 min.** Existe desde 0.1.302 (D310)
  para que la basura del archivo anterior se libere en el hilo principal. Cada colección completa recorre
  todos los objetos vivos, a ~320 ns por objeto:
  - con 1,3 M objetos al principio, 0,4 s por archivo;
  - con 10,3 M al final, 3,4 s.
- **`sys.path` crecía una entrada por archivo, hasta 369.** 242 archivos hacen
  `sys.path.insert(0, str(Path(__file__).parent))` al importarse. Esa carpeta ya es `sys.path[0]`, por ser
  la del script, y nadie la quitaba.
  - Inocuo para los resultados, pero no para los pools. Cada trabajador `spawn` recibe la lista entera y,
    por cada módulo que importa al arrancar, la recorre con un `stat` por entrada.
  - Medido A/B en el mismo proceso, alternando 12 y 369 entradas: un pool de 4 pasa de 0,50–0,70 s a
    2,4–3,6 s, y la rejilla de 539 círculos con pool de 0,7–1,2 s a 3,6–4,4 s. La secuencial no cambia.
  - Es la causa de que `test_optimizations_v111::test_grid_completes_quickly` (< 5 s) fallara en la suite
    entera y pasara solo. Su pool abre en el archivo 233, con unas 200 entradas.
- **Dos tests del runner dejaban la corrida en otras carpetas** (anomalía D-d del informe).
  `test_runner_provenance_v189` y `test_runner_selection_v180` llaman a `main()` de otra copia del runner,
  que apunta `OGR_BRIDGE_DIR` y `OGR_SETTINGS_DIR` a carpetas nuevas. No las devolvían, así que todo archivo
  posterior corría en ellas. Inocuo hoy, pero el estado de la corrida dependía del orden.
- **Un camino equivocado de la auditoría, por si alguien lo repite.** La primera medición nocturna se colgó
  6 h en `test_console_language_demo_v1329`. La causa fue mía: lancé la suite con `PYTHONFAULTHANDLER=1`.
  - Esa variable llega a los trabajadores `pythonw.exe` que ese test fuerza. Sin `stderr`, mueren al
    arrancar.
  - Con el `sys.path` ya crecido, el padre se quedó bloqueado para siempre escribiendo sus datos de
    arranque en la tubería. Con un `sys.path` corto da `BrokenProcessPool` en 0,08 s.
  - También afecta al programa (anomalía D-g, reportada sin corregir). Con la suite, nunca
    `PYTHONFAULTHANDLER` ni `-X faulthandler`.

## 1. Qué cambia

**`tests/_runner.py`, bucle de archivos de `main()`:**

- **Congelar tras colectar.** Después de `gc_guard.release()` y `gc.collect()` viene `gc.freeze()`.
  - Lo que sobrevive pasa a la generación permanente, y la siguiente colección, la del runner o las
    automáticas de cualquier hilo, recorre solo lo creado desde entonces.
  - El orden importa: primero se colecta, así que la basura del archivo anterior se sigue liberando, en el
    hilo principal, como pedía D310.
  - Lo que se pierde: un ciclo de basura formado por objetos ya congelados no se recoge nunca. Por la misma
    razón, nunca se recoge en un hilo ajeno, que era el aborto de 0.1.302.
- **Devolver el estado tras cada archivo.** Se guardan `sys.path` y las dos variables de `_RUN_FOLDERS`
  antes de cargar el archivo, y se devuelven en un `finally` tras su último test.
  - `sys.path` se devuelve sobre la misma lista (`sys.path[:] = …`), para quien la tenga.
  - Dentro de su archivo, el `insert` sigue viéndose, que es lo que el archivo pide.
  - Comprobado antes: de las 248 inserciones de los tests, 247 son la carpeta `tests/`, escrita de cinco
    maneras. La otra es la raíz del repositorio, que el bloque `__main__` del runner ya pone. Ningún archivo
    depende de una ruta que otro añadiera.

**`tests/test_runner_state_v1373.py` (5 casos):** `main()` de una segunda copia del runner sobre dos
archivos de test desechables. El primero inserta una marca en `sys.path`, guarda 5000 listas vivas y cambia
`OGR_SETTINGS_DIR`; el segundo apunta lo que ve. Contra el runner de 0.1.372 fallan los tres invariantes:

| Runner | La marca llega al 2.º archivo | La carpeta vuelve | Objetos congelados de más |
|---|---|---|---|
| 0.1.372 | sí | no | 0 |
| 0.1.373 | no | sí | 5023 |

`test_gc_guard_v1302` sigue exigiendo `gc_guard.release()` y `gc.collect()` en el bucle, y siguen.

## 2. Medida

Dos suites enteras el 2026-10-28, en serie, con la máquina sin otro trabajo y sin `TextInputHost`. La
primera, con el mismo instrumento externo que midió la E1 de 0.1.372; la segunda, la de siempre, sin
argumentos. Las dos, **6633/6633, código 0, sin aborto 127**.

| | 0.1.372 (E1, instrumentada) | 0.1.373 instrumentada | 0.1.373 normal |
|---|---|---|---|
| Suite entera | 87,6 min | **68,6 min** | **67,5 min** |
| `gc.collect()` del runner entre archivos | 13,6 min | 0,06 min | — |
| Tiempo dentro de los tests | 72,7 min | 67,9 min | — |
| Vida de los 149 pools, sumada | 12,6 min | 8,2 min | — |
| Un pool de 4 vacío, al final de la suite | 3,4–4,2 s | 0,6–0,8 s | — |
| `sys.path` al final | 369 | 11 | — |
| `test_grid_completes_quickly` (límite 5 s) | 3,1 s | 1,2 s | — |
| Memoria privada del proceso al final | 10 227 MB | 10 749 MB | — |
| Mínimo de memoria libre del sistema | 265 MB | 318 MB | 359 MB |
| Lecturas de página por segundo, media | 239 | 121 | 154 |

- **−19 min, un 22 %.** La auditoría estimaba ~72 min. Las cuentas cuadran:
  - el `collect` del runner aporta 13,5 min, de los 11 estimados;
  - los pools, 4,4 min, de los 3–4 estimados;
  - las colecciones automáticas dentro de los tests, 1,1 min, que no estaban estimadas. Bajan de ~80 s a
    ~14 s porque tampoco recorren ya lo congelado. El GC del hilo principal, sumado entero, pasa de 897 s
    a 18 s.
- **Unos 18 s de la diferencia entre las instrumentadas son del propio instrumento**, que cuenta los
  objetos con `gc.get_objects()` y ya no ve los congelados. No cambia la conclusión.
- **El precio es +522 MB** al final de la corrida: los ciclos de basura entre objetos congelados no se
  recogen. No se traduce en más paginación: el mínimo libre del sistema y las lecturas de página son
  iguales o mejores que en 0.1.372. Cuenta para la etapa 3, donde la memoria decide cuántos procesos
  caben a la vez.
- **El test de tiempo de la rejilla deja de depender de cuántos archivos corrieron antes**: 1,2 s con el
  pool en el archivo 233, como en una corrida suelta.

## 3. Qué no cambia

- **Ningún número del programa.** Solo cambian el runner, un test nuevo, la versión y los README.
- **`python tests/_runner.py` sin argumentos** corre los mismos archivos, en el mismo orden, con el mismo
  veredicto.
- **Las anomalías D-b, D-c, D-e, D-f, D-g, D-h y D-i del informe**, con sus correcciones previstas:
  - D-c, D-e y D-f, los tests que dejan estado, van con el detector de fugas de 0.1.374;
  - D-h, el segfault al salir de la CI, va en la etapa 5.
