# OGR Slip2D v0.1.377

**Fuera de Windows, el código de salida del runner es el veredicto de los tests.** Tras los totales,
`tests/_runner.py` vacía la salida y, en Linux, termina el proceso con `os._exit`, sin la finalización del
intérprete. Desde 0.1.276 esa finalización moría con un segfault en la CI de Linux (código 139), con todos
los tests en verde: la CI estaba siempre en rojo, y un rojo de verdad no se distinguía. **En Windows, no**:
allí `os._exit` rompía la salida de los tramos, medido con un A/B, y se queda el final de siempre.

Es la etapa 5 del plan de la auditoría de la suite (`docs/audits/AUDITORIA_SUITE_v0.1.372.md`), con la
opción A que eligió la propietaria y el ajuste por plataforma que aprobó tras el A/B. **Ningún módulo del
programa cambia**, salvo el número de versión.

## 0. Lo que se encontró y lo que se decidió

- **La decisión de la propietaria (2026-10-28):** la opción A, terminar con `os._exit` tras los totales, en
  vez de investigar antes el segfault, que no tenía plazo.
  - Se hace antes de la auditoría del cómputo, porque esa auditoría exige comparar cada optimización
    también en la CI, y con la CI siempre en rojo eso no era posible.
- **Un camino equivocado mío: `os._exit` en todas las plataformas.**
  - La primera suite de 0.1.377 con `--jobs 4` salió en rojo: **dos de los cuatro tramos murieron con
    0xC0000005** (violación de acceso) después de su último archivo, ya escrito su final.
  - En las cinco corridas en tramos de 0.1.375 y 0.1.376 no había pasado nunca.
  - **La comprobación de completitud de 0.1.375 lo cazó**, que es para lo que está: «chunk 3/4 ran its 83
    file(s) but exited 3221225477 (0xC0000005)».
  - **A/B** con el mismo tramo (sus 83 archivos), solo y dos veces seguidas, cambiando solo la última línea
    del runner:

    | Final | Tests | Final escrito | Código |
    |---|---|---|---|
    | `os._exit` | todos en verde | sí | **0xC0000005** |
    | `sys.exit` (el de siempre) | todos en verde | sí | **0** |

  - **La causa es una diferencia entre plataformas.**
    - En POSIX, `os._exit` es `_exit(2)`: el proceso acaba sin ejecutar ningún destructor de biblioteca,
      que es justo lo que se busca en Linux.
    - En Windows pasa por `ExitProcess`, que sigue descargando cada DLL. Los destructores de Qt se
      encuentran entonces con todo lo que la suite deja vivo, que Python ya no ha finalizado.
    - En aislado no se reproduce: dos `MainWindow` vivas y `os._exit(0)` salen con 0. Depende de lo que
      deje cada tramo.
  - **Lo que queda,** con el OK de la propietaria: `os._exit` solo fuera de Windows.
    - En Windows, el final de siempre, más el vaciado de la salida.
    - Allí un fallo al cerrar sigue viéndose, como siempre.
- **El precio en Linux:** un fallo al cerrar el intérprete deja de verse allí.
  - Queda abierto como **D370** en `ERRORES_Y_DISCREPANCIAS.md` del banco, paquete P8, con su prompt de
    resolución. La ficha recoge lo que ya se descartó (el `sendPostedEvents` de 0.1.276), los candidatos
    sin probar y cómo sacar la pila en una rama `dev/**` con el final de antes.
  - **Sin medir:** si OGR, al cerrarse en Linux, pasa por el mismo desmontaje.
- **Lo que `os._exit` se salta, y por qué no importa:** `os._exit` no corre los `atexit` ni la finalización.
  - Todo lo que una corrida deja (los totales, las duraciones, el registro de la serie, el informe de un
    tramo) se escribe dentro de `main()`, antes.
  - Solo quedan los dos flujos de salida, que se vacían a mano.
  - El padre de `--jobs` sigue comparando el código de cada tramo con sus resultados.
- **El vaciado también arregla algo en Windows.** Con la misma inyección de un fallo al cerrar, el final de
  0.1.376 salía con 139 **y perdía los totales**, que seguían en el búfer; lo comprobé a mano. Ahora el
  fallo se ve y los totales están escritos.
- **Otro hallazgo de la misma suite, abierto como D371 (no corregido):**
  `test_api_jobs_v1194::test_progress_is_written_and_ends_complete` falló con el trabajo ya en `done` y su
  `progress.json` sin la última actualización.
  - **El mecanismo:** el trabajo escribe el progreso con un solo intento (`ogr_api/jobs/worker.py:59-73`),
    también el final. En Windows, ese renombrado falla si el padre está leyendo el archivo en ese momento.
  - **Reproducido de forma determinista:** con el archivo abierto, `_write_progress(d, 5, 5)` devuelve
    `False` y el archivo se queda en 1 de 5.
  - Un cliente del API no lo ve, porque el estado final no lleva progreso. Pero la suite puede salir en rojo
    con la máquina cargada.
  - **No tiene que ver con esta versión:** el trabajo corre en su propio proceso, sin el runner. Lo decide la
    propietaria con su prompt.
- **`PYTHONUNBUFFERED=1` en la CI** (D-i de la auditoría). Con la salida redirigida y con búfer, el log de
  GitHub crecía a saltos, y sus marcas de tiempo no decían cuánto tardaba cada archivo.
- **La subida.** Esta versión sube con las cuatro anteriores (0.1.373–0.1.376), que la CI no había visto:
  cambian el runner a fondo y nunca habían corrido en Linux ni con Python 3.11–3.13.

## 1. Qué cambia

- **`tests/_runner.py`:** el bloque `__main__` vacía `stdout` y `stderr`. Fuera de Windows termina con
  `os._exit(código)`; en Windows, con `sys.exit(código)`, como siempre.
- **`.github/workflows/tests.yml`:** `PYTHONUNBUFFERED: "1"` en el paso de la suite.
- **`tests/test_runner_shutdown_v1377.py` (4 casos).** Lanza el runner real en un proceso propio, con un
  `atexit` que termina con 139, que es lo que hace la finalización en la CI. Comprueba que:
  - fuera de Windows, una corrida en verde sale con 0; en Windows el fallo al cerrar se sigue viendo (139);
  - los totales están escritos en las dos plataformas;
  - la misma inyección sin el runner sale con 139 y pierde lo que no se había vaciado;
  - fuera de Windows, una selección vacía sale con 2.

  Cada plataforma comprueba su rama: Linux en la CI, Windows aquí. Usa la salida con búfer a propósito: la
  CI pone ahora `PYTHONUNBUFFERED`, y sin búfer no habría vaciado que probar.
- **AGENTS.md:** en «Coste de los tests», una frase sobre el código de salida, D370 y Windows.
- **Los dos README:** el número de tests.
- **En el banco, fuera de git:**
  - las fichas D370 y D371 en `ERRORES_Y_DISCREPANCIAS.md`, con la cabecera en «siguiente libre D372» y las
    dos al final del orden de P8;
  - sus prompts largos (`_auditoria/doc/prompts_largos/D370.md` y `D371.md`) y las dos en `PAQUETES` de
    `_tools/generar_prompts.py`;
  - `PROMPTS_RESOLUCION.md` regenerado: 37 prompts, 20 largos y las mismas 17 FALTA de antes;
  - `auditoria_invariantes.py` con 0 ERROR en la raíz y en el 02;
  - el comprobador de citas, sin problemas en D370 ni en D371. Las 20 citas que señala son de prompts
    anteriores.

## 2. Medida

| Corrida | Casos | Resultado | Reloj |
|---|---|---|---|
| `--jobs 4`, con `os._exit` en todas las plataformas | 6712 | **2 tramos muertos con 0xC0000005** y 1 fallo (D371) | 35,6 min |
| A/B del tramo 3 solo: `os._exit` / `sys.exit` | sus tests | todos en verde / todos en verde | 16,2 / 17,1 min; código 0xC0000005 / 0 |
| `--jobs 4`, la de publicar (`os._exit` solo fuera de Windows) | 6712 | verde, sin fugas ni tramos muertos; 0 procesos huérfanos antes y después | 36,4 min |
| CI de GitHub, 3.11 / 3.12 / 3.13 | | _(se rellena tras la subida)_ | |

## 3. Qué no cambia

- **Ningún número del programa.**
- **`python tests/_runner.py`** corre lo mismo y da el mismo veredicto. Fuera de Windows es también, sin
  excepción, su código de salida.
- **En Windows,** el final es el de siempre, con la salida vaciada antes.
- **La CI** sigue en serie, un trabajo por versión de Python.
- **Con esto termina el plan de la auditoría de la suite.** Lo que queda abierto:
  - D370 y D371;
  - la memoria, si limita (liberar las ventanas entre archivos, ficha por proponer);
  - la auditoría del cómputo, con su prompt en
    `referencias/Ejemplos/RS2_Verification Manuals/_auditoria/COMPUTO/PROMPT_optimizar_computo_0.1.376.md`.
