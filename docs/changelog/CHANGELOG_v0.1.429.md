# OGR Slip2D v0.1.429

**El desplazamiento de Newmark y la cuenta de superficies sin Ky cubren toda superficie que analiza la corrida, también
las que dibuja el usuario. La línea de órdenes ya no esconde los desplazamientos ni aborta con un KeyError (D397).**
- **Hasta hoy solo recibía desplazamiento la población de la búsqueda.** Una superficie del usuario que salía como la
  crítica, la de menor Ky, se quedaba sin él:
  - la cabecera pasaba a Ky sin avisar;
  - las superficies de la corrida enseñaban 8,95 cm como el mayor movimiento, cuando la crítica se movería 34,8 cm.
    Medido con la sonda de la revisión de 0.1.427, que repite la comprobación `d397()` del banco: talud de ejemplo,
    Path de 5 superficies, Bishop, la polilínea [(19, 25), (25, 18), (31, 14,5), (37, 15)] y una sinusoide de 0,3 g,
    2 Hz y 4 s con dt 0,01. El desplazamiento va como 1/f: a 1 Hz serían 69,5 cm.
- **La línea de órdenes tenía dos defectos propios, y cada uno tiene ahora su test:**
  - Decidía «hay Newmark» con la crítica del PRIMER método. Un primer método sin crítica dejaba toda la columna bajo
    «Critical Ky» y escondía el desplazamiento de los demás. Pasa de verdad: Spencer y GLE no encuentran Ky en un plano
    con kh (D143). Ahora pregunta a todos los métodos.
  - Una fila cuya crítica no tenía desplazamiento (la del usuario, hasta esta versión) lanzaba `KeyError`. Eso abortaba
    `compute` con código 1 antes de imprimir la tabla y de guardar ningún resultado. Ahora esa fila dice «—».
- **La nota que cuenta las superficies sin Ky** cuenta también las del usuario. Cuando la del usuario era la única
  superficie y no tenía Ky, la corrida se quedaba sin crítica y no decía por qué.
- **Un modelo sin superficies del usuario no cambia:** `all_evaluations_of` le devuelve su misma lista.

Es la segunda versión de la tanda P10 (D396–D404), antes de Sarma.

## 0. Lo que se encontró

- **El defecto.** `_seismic_notes` (`analysis_runner.py`) recorría `result.evaluations` para adjuntar el desplazamiento y
  para contar las superficies sin Ky.
  - El Ky sí se calculaba para las del usuario, en `_analyse`.
  - Faltaba el paso siguiente, que es el que lee la cabecera: `reported_caption` da NEWMARK solo si la crítica lleva
    desplazamiento.
- **Una anomalía del rebanador, preexistente, que no se toca aquí (regla 6).** El plano de dos vértices de
  `test_yield_acceleration_v1127` ((2, 2)–(30, 10), sobre un talud de 45°) lo rechaza el rebanador:
  - con 25 dovelas, que es el valor del proyecto, y también con 41, 43, 50 y 51;
  - sin dejar ningún motivo en `reasons`, así que la corrida dice el genérico «the slicer refused it».
  - Con 60 dovelas, que son las del test original, no pasa nada, y con un vértice intermedio no pasa con ningún
    número de 5 a 80.
  - Huele a un corte uniforme que cae sobre un corte obligado. Es para una ficha nueva si la propietaria quiere. El test
    usa 60 dovelas y lo dice.
- **Spencer y GLE/MP no encuentran Ky en el plano del test (otro caso de D143, abierta y sin corregir).**
  - Con kh = 0, los nueve métodos dan 2,0203–2,0207, que es tan φ / tan β = 2,0207.
  - Con kh entre 0,10 y 0,30, Spencer y GLE/MP no convergen (con kh = 0,24, Spencer sí), y sus factores sin convergir
    se apartan. Con kh = 0,20, GLE da 1,42 y Janbu 1,12.
  - Su crítica sale None, con la nota «1 of 1 surfaces have no critical seismic coefficient below 1».
  - Janbu (simplificado y corregido), Corps 1 y 2 y Lowe-Karafiath dan 0,25034 ≈ tan(φ − β). Bishop y el Ordinario dan
    0,268 y 0,266: toman momentos, y en un plano no es su caso.
  - Es lo que D143 ya mide en un plano de 40° con kh = 0,15 desde 0.1.214: la raíz de F_f = F_m no cae en ningún
    rango razonable de λ. No se toca aquí. Es el caso real en que un primer método se queda sin crítica, y por eso el
    comentario de la línea de órdenes lo cita.
- **Caminos equivocados:**
  - **El primer intento del test** usaba el plano con las 25 dovelas del proyecto, y la polilínea del usuario no se
    evaluaba. Así salió la anomalía de arriba.
  - **El test de la línea de órdenes** buscaba la fila del método con la primera línea que lo nombraba, y era la nota
    «Note: corps_engineers_1…». Con 80 columnas, además, `rich` partía el rótulo y recortaba los nombres. Ahora corre con
    200 columnas y busca la línea con el borde de la tabla.
  - **El primer test de la línea de órdenes cubría solo una mitad del arreglo.** Quitaba el desplazamiento al SEGUNDO
    método. Con el `newmark_on` de 0.1.428 y el `.get` nuevo pasaba igual, así que revertir `any()` dejaba la suite en
    verde. Lo encontraron tres lentes de la revisión. El comentario, además, daba al `KeyError` una causa imposible
    («a Ky no coefficient reached»): esa crítica es None, y su fila dice «no valid surface». Ahora hay un test por
    mitad, y los dos cambian el PRIMER método.
  - **La cuenta de las superficies sin Ky no tenía test,** aunque el §1 la anunciaba. Partir `valid` en dos listas
    dejaba la suite en verde. Tiene el suyo.

## 1. Qué cambia

- **`ogr_slip2d/analysis_runner.py` `_seismic_notes`:** las superficies válidas salen de `all_evaluations_of(result)`.
  El desplazamiento y la cuenta de «superficies sin Ky» cubren toda superficie analizada.
- **`ogr_cli/__main__.py`:**
  - `newmark_on` pasa a ser «la crítica de algún método lleva desplazamiento»;
  - cada fila lee con `.get` y dice «—» si no lo hay;
  - un comentario en cada mitad dice qué arregla y cuándo pasa. Desde esta versión, una corrida con un registro usable
    da su desplazamiento a toda crítica, y el «—» queda de guarda;
  - se conserva el literal `getattr(first, "objective", "fos")`, que fija `test_seismic_interface_v1127`.
- **`ogr_slip2d/search.py`:** el docstring de `all_evaluations_of` dice que Newmark ya lee por ella. Quedan D400 y D401.
- **`tests/test_newmark_user_surfaces_v1429.py`,** nuevo.
- **`spec/features/009-sarma-dovelas-no-verticales/`:** las versiones de Sarma pasan de 0.1.437–0.1.443 a
  0.1.439–0.1.445, por las dos fichas que la propietaria añadió a la tanda P10 (§3).
- El número en los nueve sitios y el contador de los dos README.

## 2. Qué se probó

- **`tests/test_newmark_user_surfaces_v1429.py`,** 10 tests, 1,08 s el archivo solo. Cuatro corridas pequeñas de un
  plano de 60 dovelas, cada una calculada una vez y compartida. La referencia es Newmark (1965), tres veces, sobre un
  plano.
  - **El montaje:** el plano es la polilínea del usuario, y un foco de punto fuera del modelo rechaza todo lo que genera
    la búsqueda (los focos no se aplican a las superficies del usuario, D58). Así es la crítica de una corrida real.
  - **Ky = tan(φ − β)** a 1e-6 relativo; medido 4,9e-8.
  - **El desplazamiento bajo un pulso rectangular** (0,5 g durante 1 s, dt = 0,000625 s) es
    u = V²/(2gN)·(1 − N/A) al Ky de la propia corrida, a 1e-6 relativo; medido 2,4e-8, que es el residuo del
    integrador cuando el bloque se para entre dos muestras.
  - **Bit a bit** igual a `displacement_for_record(registro, Ky)`.
  - **La cabecera** es NEWMARK, con su desplazamiento en metros.
  - **Sin el foco,** toda superficie con Ky, de la búsqueda o del usuario, lleva desplazamiento.
  - **La cuenta de las superficies sin Ky:**
    - el mismo plano en un suelo de c = 500 kPa;
    - como bloque rígido, su Ky en forma cerrada es unas 8,4 veces el techo de 1. La misma fórmula sin cohesión da
      tan(φ − β) a 1e-12;
    - es la única superficie de la corrida. La nota `method.seismic_no_ky` dice 1 de 1, y la corrida queda sin
      crítica.
  - **En la línea de órdenes,** dos métodos, cambiando a mano el PRIMERO sobre una copia de la corrida compartida:
    - sin crítica: el rótulo es «Newmark disp.», nunca «Critical Ky». Su fila dice «no valid surface» y la otra
      enseña su desplazamiento;
    - con la crítica sin desplazamiento: sale con 0, su fila dice «—», la otra enseña su valor y se guardan los dos
      `.h5`.
- **Discriminación en el árbol de 0.1.428** (`git archive` de 1a665ef, sin el buscador editable, `__file__`
  comprobados): fallan 7 de 10, todos por comportamiento.
  - La crítica del usuario no lleva desplazamiento (`KeyError`).
  - La cabecera sale «ky».
  - La superficie del usuario queda sin Newmark.
  - Los dos de la línea de órdenes fallan: sale «Critical Ky».
  - No sale la nota.
  - Pasan los tres controles: el Ky en forma cerrada, que la crítica es la del usuario y la forma cerrada del bloque.
- **Mutantes en memoria sobre el árbol vivo, cada mitad por separado:**
  - con el `newmark_on` del primer método, fallan los dos tests de la línea de órdenes;
  - con el índice `detail["newmark_displacement"]`, falla el del «—» (sale con 1);
  - con la cuenta solo de la búsqueda, fallan 7 de 10, la nota incluida.
- **Vecinos:**
  - con la primera redacción del test: Newmark, Ky, sismo, línea de órdenes, render y resultados del API, notas de
    método, lo publicado, superficies del usuario, retroanálisis y F2/F3b, 463 de 463;
  - tras la revisión: Newmark, Ky, sismo, línea de órdenes, notas de método, superficies del usuario, retroanálisis,
    render del API, lo publicado, coeficientes de diseño y cachés de los tests, 425 de 425 (23 archivos).
- **Suite entera con `--jobs 4`: 7208 en verde, 1 saltado y 0 fallos,** sin fugas ni tramos muertos, sobre el árbol
  final. La primera corrida, con la primera redacción del test, dio 7205 en verde, 1 saltado y 0 fallos. La última
  serie en verde fue hace 7 commits, y toca a los 100.
- **Banco, en seco:**
  - manual 02: D58, D96, D224, D225, D101, D102, D103, D126, D177 y D210, todas CUBIERTO POR TEST;
  - raíz: D345, D396, D337 y D314, todas CUBIERTO POR TEST;
  - `d397()`, aún sin aplicar al verificador (se añade al cerrar la ficha), probada dentro de él sin escribir nada:
    - con el árbol vivo, CUBIERTO POR TEST: crítica del usuario con Ky 0,10141 y 0,34755 m, la búsqueda con 0,08952 m
      como máximo, ninguna superficie con Ky sin desplazamiento, y la cabecera es Newmark, 0,347549;
    - con el de 0.1.428, sin el buscador editable, SIGUE ABIERTO por lo que calcula: la crítica sin desplazamiento y la
      cabecera en Ky;
    - `sys.path` igual antes y después.
- **Revisión adversaria:** tres lentes (motor, tests y reglas, changelog y banco) y dos escépticos por hallazgo, 27
  agentes.
  - La primera tanda murió entera al agotarse el límite de uso, sin dar ningún hallazgo, y se relanzó.
  - Salieron 12 hallazgos, 8 distintos.
  - **Confirmados y corregidos:**
    - las dos mitades de la línea de órdenes, sin un test cada una, y el comentario con una causa imposible (tres
      lentes);
    - la cuenta sin Ky, sin test;
    - `d397()` aceptaba cualquiera de las dos clases del test. Un votante lo refuta por ser la convención del banco;
      se exige cada una igualmente, porque su docstring promete las dos;
    - el coste del test, las condiciones del 34,8 cm y el docstring de `all_evaluations_of`. Se corrigieron mientras
      se verificaban, y dos votantes los refutan ya sobre el árbol corregido.
  - **Preexistentes confirmados,** en el §3: `surface_evaluate` sin Newmark (2 de 2) y el rótulo de la línea de
    órdenes con norma (2 de 2).
  - **Refutado como defecto:** el denominador de la nota (1 de 2). Va al §3 como opción.
  - **Uno de los escépticos midió aparte** lo de Spencer y GLE (§0), y una sonda propia lo confirmó con los nueve
    métodos.

## 3. Qué queda

- **El resto de la tanda P10, con lo que decidió la propietaria el 2026-11-06:**
  - D405 (el rótulo de la línea de órdenes, punto 2 de abajo) en 0.1.430;
  - D398 (el lienzo a mitad de un dibujo) a D404, en 0.1.431–0.1.437;
  - D406 (`surface_evaluate`, punto 1) en 0.1.438.
  - Las siete versiones de Sarma (D357) pasan a 0.1.439–0.1.445. La spec 009 se renumera +2 en este commit.
- **Preexistentes que encontró la revisión (regla 6).** No se tocaron sin la decisión de la propietaria, que va en cada
  uno.
  1. **(media) `surface_evaluate` no da el desplazamiento de Newmark ni ninguna nota sísmica.**
     - `evaluate_surfaces` (`analysis_runner.py:2337`) es la puerta de `surface_evaluate` en el API y el MCP. Calcula
       el Ky, pero nunca pasa por `_seismic_notes`.
     - Con Newmark activo, la misma polilínea sale de la corrida con 34,8 cm y de `surface_evaluate` solo con su Ky.
     - Tampoco dice que falta el registro ni que el kh del proyecto queda sustituido. Esa nota existe porque el
       factor y el Ky salen entonces de cargas distintas.
     - Su docstring dice que pasa por «exactly what run_analysis goes through».
     - Es de v0.1.194. Desde esta versión, además, las dos puertas ya no dan lo mismo para una polilínea guardada.
     - Ninguna ficha de P10 lo cubría: es hermana de D397.
     - **Decidido:** ficha nueva D406, al final de la tanda P10 (0.1.438), antes de Sarma.
  2. **(alta para un votante, media para el otro) Con norma de diseño y Newmark, la línea de órdenes imprime el
     desplazamiento en centímetros bajo «Over-design factor».**
     - El rótulo se queda en «Over-design factor» (`__main__.py:228`), porque el rótulo sísmico exige
       `not factored`. Pero la fila entra por `newmark_on` y escribe el desplazamiento por 100.
     - El aviso de encima asegura que el valor «must exceed 1». Un talud que se mueve 1,87 m se lee como ODF = 187,
       del lado inseguro.
     - La ventana y el API lo resuelven al revés (`reported_caption`: el rótulo sigue al valor que se imprime).
     - Nace en 0.1.127. v0.1.165 lo reportó para Ky y no lo corrigió, porque la ficha D96 prohibía tocar la salida de
       la línea de órdenes. Lo dicen `reported.py:33-36` y `reported_quantity.py:41-46`, pero no tiene ficha ni test.
     - **Esta versión le da más alcance.** Con la crítica del usuario, 0.1.428 imprimía su Ky factorizado (0,1556)
       bajo ese rótulo, una lectura del lado seguro, porque no supera 1. 0.1.429 imprime sus centímetros, que lo
       superan.
     - El arreglo que proponen los dos votantes es pequeño: la línea de órdenes toma el rótulo y la unidad de
       `reported_caption(result, factor_report)`.
     - **Decidido:** ficha nueva D405, que se arregla justo después, en 0.1.430, antes de D398. Ningún commit lo sube
       mientras tanto.
  3. **(baja, opcional) El denominador de la nota «sin Ky» cuenta ahora las superficies del usuario,** y la columna
     «Valid» de la línea de órdenes solo las de la búsqueda (52 frente a 53 en la sonda).
     - La frase es cierta, y en el API cuadra con `counts.user_surfaces`.
     - La línea de órdenes no dice en ningún sitio cuántas son del usuario, y eso viene de v0.1.157.
     - Un votante lo refuta como intencionado. Lo que propone, partir la cuenta («1 of them drawn by the user»), es
       una mejora y no la corrección de un defecto.
- **La anomalía del rebanador de §0:** ficha nueva D407, por decisión de la propietaria, sin versión todavía.
- **Spencer y GLE sin Ky en un plano con kh (§0):** se añade como evidencia a D143, por decisión de la propietaria.
- **Los README** dicen que la suite completa tarda de 50 a 90 minutos. La cifra medida es 39,7 min en serie y 20,1
  con `--jobs 4` (v0.1.397, AGENTS.md). No es de esta versión: se corrige en 0.1.430, por decisión de la
  propietaria.
