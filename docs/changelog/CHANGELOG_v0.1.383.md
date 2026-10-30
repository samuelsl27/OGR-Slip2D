# OGR Slip2D v0.1.383

**`Mesh.locate` deja de recorrer la malla entera.** Un índice de rejilla elige qué elementos se prueban, y la
respuesta es la del recorrido, objeto por objeto.
- **Medido en K17** (banco 010, rejilla de Bishop de 396 círculos sobre el campo de presiones del MEF), en un mismo
  proceso y en el orden nuevo, viejo, viejo, nuevo, nuevo, con el código final: de 8,45 y 8,28 s a **1,04, 0,92 y
  0,92 s (×9)**, con los 322 factores evaluados idénticos bit a bit.
- **El trabajo:** de 545,9 llamadas a `Element.contains` por consulta a 3,55. La media cuenta las 16 primeras
  consultas, que recorren la malla mientras no hay índice.
- **En el banco de pruebas,** frente a la corrida de 0.1.377, en las dos corridas de la huella (antes de la
  revisión y con el código final):
  - K17 pasa de 8,27 a **1,03 y 1,10 s**;
  - K18, el desembalse de `test_transient_v130` con presiones del MEF, de 18,8 a **8,9 y 9,3 s**;
  - K15, la presa con dren al pie, de 12,3 a **8,5 y 8,4 s**, porque su flujo por secciones también localiza;
  - K16, el transitorio, de 62,9 a 56,8 y 57,3 s, dentro de lo que se mueve la máquina.

  Los casos sin malla no pasan por el código cambiado y se movieron entre −20 y +54 %. Los extremos son K04 y K05,
  que abren un pool para pocos círculos y miden sobre todo su arranque: es la máquina, con corridas sueltas.

Es la V5 de la fase 3 de la auditoría del cómputo (`docs/audits/AUDITORIA_COMPUTO_v0.1.377.md`), la primera que
toca el programa. Es de clase B: idéntica por construcción y demostrada con la huella de los 23 casos del banco de
pruebas, **23 de 23 idénticos** a 0.1.377. Además, por decisión de la propietaria, `python_exec` y la terminal de la
ventana dejan caducos los índices alrededor de cada script.

## 0. Lo que se encontró y lo que se decidió

- **La puerta de medida se reproduce.**
  - La primera corrida de K17 dio 12,3 s, frente a 8,3–8,8 el 29 de octubre, con 12,2 s de CPU: la máquina
    estaba más lenta, sin ningún proceso girando. Repetida minutos después, 7,93 s.
  - `Mesh.locate`, con el cronómetro grueso: 6,82 de 7,86 s (87 %).
  - 9552 consultas y 5 248 005 elementos probados, 549,4 por consulta: idéntico, al elemento, a lo medido en 0.1.377.
- **El índice** (`_Locator`):
  - una rejilla uniforme sobre la caja de cada elemento, ensanchada por un margen **certificado**
    (`_certified_box`): una cota de error en coma flotante que garantiza que todo punto que `contains` acepta cae
    dentro;
  - los elementos sin caja certificada van a una lista que se prueba en cada consulta: láminas cuyo determinante
    no se conoce ni en signo, triángulos planos, vértices no finitos y cajas que cubrirían más de 64 celdas;
  - una consulta prueba, por posición creciente en la lista de elementos, los candidatos de su celda mezclados con
    esa lista, con la misma llamada `e.contains(mesh, x, y)`, y devuelve el primero que acepta;
  - se construye a las 16 consultas de una misma malla, que es lo que cuesta construirlo (11 ms frente a 0,7 ms
    por recorrido en el banco 010), y se publica de una sola vez.
- **Por qué devuelve lo mismo que el recorrido:** todo elemento que acepta la consulta es candidato.
  - **Los certificados,** porque la consulta cae en su caja, y la celda de una coordenada es una fórmula monótona,
    la misma para las esquinas de una caja y para la consulta.
  - **Los demás,** porque se prueban siempre.

  Así, el primero que acepta en orden de lista es el mismo, y `contains` no cambia.
- **El lema.** Se apoya en el modelo estándar de la aritmética en coma flotante (Higham, 2002, *Accuracy and
  Stability of Numerical Algorithms*, 2.ª ed., §2.2 y lema 3.1). Con u = 2⁻⁵³ y γₙ = nu/(1 − nu), para un triángulo
  de vértices en binary64 y una consulta p de la caja lejana F:
  1. **El determinante.** `contains` calcula d̂ con cuatro redondeos por término. Si Pd es la suma de los productos
     de las diferencias redondeadas, |d̂ − d| ≤ γ₄(|A_d| + |C_d|) ≤ 8u·Pd + 2⁻¹⁰⁷⁰ = ε_d. Se certifica solo si
     |d̂| ≥ 1e-15, es finito y ε_d ≤ |d̂|/4. Entonces |d| ≥ d_min = |d̂| − ε_d > 0 y |d̂/d − 1| ≤ ρ = ε_d/d_min ≤ 1/3.
  2. **Los numeradores.** Con X_k = máx(x_k − Fx0, Fx1 − x_k) e Y_k igual en y, se cumple |x_k − x| ≤ X_k para
     todo p de F. Así |n_i| ≤ P_i y |n̂_i − n_i| ≤ γ₄P_i, con P₁ = X₂Y₃ + X₃Y₂ y P₂ = X₃Y₁ + X₁Y₃.
  3. **Las coordenadas.** λ̂_i = (n̂_i/d̂)(1 + δ) da |λ̂_i − λ_i| ≤ Λ_i(u + ρ + γ₄(1 + u))/(1 − ρ) + holgura = E_i,
     con Λ_i = P_i/d_min (i = 1, 2). La holgura de underflow es 2⁻¹⁰⁷³/d_min + 2⁻¹⁰⁷⁴. El redondeo doble de
     `1.0 - l1 - l2` da E₃ = E₁ + E₂ + γ₂(1 + Λ₁ + E₁) + u(Λ₂ + E₂).
  4. **Si `contains` acepta,** λ̂_i ≥ −tol, luego λ_i ≥ −tol − E_i. Los pesos negativos suman como mucho
     s = 3·tol + E₁ + E₂ + E₃. Como p = Σλ_i v_i con Σλ_i = 1, x − x_mín = Σλ_i(x_i − x_mín) ≥ −s·W, y lo mismo en
     los otros tres lados.
  5. **La caja guardada:** [x_mín − 2sW, x_máx + 2sW] × [y_mín − 2sH, y_máx + 2sH], un ulp más hacia fuera y
     recortada a F. El 2 absorbe el redondeo de evaluar la cota.
  6. **Sin desbordamiento:** con todas las coordenadas de F por debajo de 1e100, ningún producto ni cociente de
     `contains` desborda, así que el modelo estándar vale dondequiera que acepta. Por encima, no hay índice. El
     margen propio de la cota sí puede llegar a infinito, en una aguja cerca del límite; entonces el elemento no
     tiene caja.
- **Lo que comprobaron otros, sin anclarse en mi derivación** (un workflow de cinco agentes antes de integrar):
  - **Un revisor, en aritmética racional exacta,** sobre 1495 triángulos y 341 959 consultas:
    - |d̂ − d|/ε_d llega a 0,24;
    - |λ̂ − λ|/E llega a 0,12;
    - la excursión máxima de un punto aceptado es 0,53·sW, frente a un margen de 2·sW.
  - **Un cazador de contraejemplos:** 52 009 589 llamadas reales a `contains` sobre 7974 triángulos (agujas,
    láminas en el límite, coordenadas UTM y micrométricas, determinantes justo por encima de 1e-15) y 0 puntos
    aceptados fuera de su caja. El peor deja libres dos tercios del margen guardado, que es el peor caso
    analítico: una excursión de 2·tol·W frente a un margen de 2sW ≈ 6·tol·W.
  - **Dos auditores,** de quién toca la malla y de con qué tipos se la consulta.
- **Lo que esa revisión cambió del plan.** Los dos refutadores encontraron huecos en los bordes, ninguno fatal:
  - **Solo floats exactos,** en los nodos y en las consultas (`type(x) is float`). El plan admitía float e int.
    Pero una subclase de float puede redefinir la resta, y el float64 de numpy obedece al estado de error de numpy,
    que el recorrido de un elemento saltado podría disparar. Con nodos float32, además, numpy 2 calcula `contains`
    en float32. Todo eso va al recorrido literal; ningún llamador del programa pasa otra cosa que floats de Python.
  - **La tolerancia y el umbral del determinante, compartidos:** `CONTAINS_TOL` es el valor por defecto de
    `contains` y `DEGENERATE_DET` el umbral de `barycentric`. Cambiar uno sin el otro rompería la cota.
  - **Una holgura de underflow que exista.** Un revisor proponía 2⁻¹⁰⁷⁵, que en binary64 se redondea a 0,0; se
    usan 2⁻¹⁰⁷³/d_min y 2⁻¹⁰⁷⁴.
  - **El determinante infinito.** El enunciado del plan certificaba |d̂| = ∞ (∞ ≤ ∞/4), y dos revisores lo
    encontraron por separado. Ahora se exige finito, y las coordenadas, por debajo de 1e100.
  - **Una excepción al leer la malla la deja en el recorrido.** El índice lee todos los elementos; el recorrido,
    solo los anteriores al acierto. Una malla con un nodo que no existe lanzaría en la consulta 16 donde el
    recorrido respondía.
  - **El índice se publica con una sola asignación,** construido entero antes. Hay dos rutas reales con dos hilos
    sobre la misma malla: el cálculo de la ventana con las consultas del puente del agente, y las llamadas paralelas
    del servidor MCP sobre un resultado guardado.
  - **`__getstate__` copia el diccionario y quita el índice y el contador.** Una malla copiada, enviada a un
    trabajador del pool o guardada por el deshacer se serializa con los mismos bytes que antes. Lo lee `getattr`,
    porque la copia no pasa por `__init__`.
  - **Un tope de 64 celdas por caja,** y sin índice si más de la mitad de los elementos no tienen caja: un elemento
    diminuto en una caja lejana enorme llenaría la rejilla.
- **Las auditorías:**
  - **Ningún código del programa ni de los tests edita una malla en el sitio** después de localizarla: se sustituye
    entera (`set_fem_mesh`, `from_dict`, el deshacer con una copia profunda). Solo un script del usuario podría
    hacerlo (`python_exec`, la terminal de la ventana).
  - **Todos los llamadores pasan floats de Python finitos:** las ocho búsquedas, las fuerzas entre dovelas, el
    flujo por una sección, la API y la estadística. Ningún test parcheaba `contains` ni heredaba de `Mesh`.
- **La revisión del código ya integrado** (un segundo workflow: tres revisores y un verificador por hallazgo):
  - Ninguno encontró una malla del programa en la que el índice devuelva otro objeto que el recorrido. Un fuzz de
    101 mallas adversarias dio 0 discrepancias en 166 864 consultas, y otro de 12 mallas mixtas, 0 en 34 092.
  - **Un riesgo real, ya arreglado:** la construcción pedía `len()` a las listas fuera de su `try`. Una malla
    fuera de contrato, con `nodes=None` o los elementos como iterador, habría lanzado `TypeError` cada 16
    consultas donde el recorrido respondía. Ahora el error se captura y la malla sigue en el recorrido.
  - **Otro riesgo real, que decidió la propietaria:** un script de `python_exec` que mueve un nodo en el sitio,
    después de 16 consultas, dejaba el índice viejo. La consulta de punto respondía «fuera de la malla» donde
    0.1.382 daba el elemento; lo reprodujo un verificador con la API pública.
    - **La decisión:** el contador de scripts. `invalidate_mesh_indexes()` lo mueve antes y después de cada script
      de `python_exec` (`ogr_api/pyexec.py`) y de cada orden de la terminal de la ventana, y todo índice
      construido antes caduca, sea de la malla del proyecto, de un resultado guardado o de un solver.
    - **Lo que queda fuera:** un script que edita una malla después de que el propio script haya reconstruido su
      índice. Para eso está `Mesh.forget_index()`, y la guía de `python_exec` lo dice.
    - **Para el detector de fugas:** el contador cambia en cada script, y va a su lista blanca, con su porqué.
  - **Huecos de los tests, cubiertos:**
    - nada probaba que la lista de «siempre» se reordena cuando lleva elementos de las dos clases;
    - el caso de la subclase de `Element` consultaba un punto fuera de la caja lejana y no podía fallar;
    - el primer caso de «sin caja» salía por el umbral del determinante y no por el redondeo que decía su
      comentario;
    - nada probaba las puntas del triángulo que `contains` acepta, que es lo que más se aleja de los vértices;
    - nada probaba que el índice se publica entero;
    - ninguna consulta mezclaba un float con un no float;
    - tres `== 0` no podían fallar.

    Ahora cada uno de once mutantes falla al menos un test.
- **Hallazgos sin ficha, para que decidas** (regla 6):
  - **Las fuerzas «effective» con el MEF** (Lowe-Karafiath y los dos del Corps): el extremo superior de cada cara de
    dovela cae fuera de la malla por el *snap* de las regiones (en Ej_1, el nodo extremo está en 119,9999996) y
    toma u = 0. Son 47 de las 432 consultas de cara de una superficie, con baricéntrica entre −8,3e-9 y −2,6e-7.
    V5 no lo cambia, porque da lo mismo que el recorrido. Que sea un defecto depende de lo que deba valer u en el
    terreno.
  - **Con el índice, el pool no compensa en estos modelos:** la rejilla de 539 círculos del modelo 010 tarda 1,2 y
    1,4 s en serie y 2,7 y 1,8 s con el pool, en dos corridas. Es un dato para V8 (el umbral del pool).
  - **Lejísimos, `contains` acepta el primer elemento:** a (1e17, 1e17), todas las diferencias a los vértices se
    redondean igual, los numeradores salen 0 y el recorrido devuelve el elemento 0. Por eso el índice deja al
    recorrido lo que cae fuera de la caja lejana. No afecta a ninguna consulta del programa.
  - **Las líneas de corriente tienen su propio recorrido lineal** (`ogr_fem2d/solvers/streamlines.py`), con otra
    fórmula y otra tolerancia. El plan lo descartó, y V5 no lo toca.

## 1. Qué cambia

- `ogr_core/fem/mesh.py`:
  - `CONTAINS_TOL` y `DEGENERATE_DET`;
  - `Mesh.locate`, `Mesh._after_scan`, `Mesh.forget_index` y `Mesh.__getstate__`;
  - `_certified_box`, `_Locator`, `_build_locator` y `_grid_of`;
  - `invalidate_mesh_indexes` y su contador.
- `ogr_api/pyexec.py` y `ogr_gui/widgets/terminal.py`: el contador antes y después de cada script.
- `tests/_leaks.py`: el contador en la lista blanca, con su porqué.
- `docs/mcp/herramientas.md`: la fila de `python_exec`.
- `tests/test_mesh_locator_v1383.py`, nuevo: 26 tests.
- El número, en los nueve sitios, y el contador de los dos README (6752).

## 2. Qué se probó

- `tests/test_mesh_locator_v1383.py`, frente al recorrido de 0.1.382 copiado literalmente como oráculo:
  - vértices, aristas y sus prolongaciones, a uno y dos ulps;
  - las esquinas de cada caja certificada y las puntas de lo que `contains` acepta;
  - puntos dentro, alrededor y fuera de la caja lejana;
  - elementos solapados, una lámina sin caja que gana donde acepta, un triángulo plano y la lista de «siempre»
    con las dos clases;
  - la cota en triángulos sueltos (aguja, UTM, micrómetros, horario);
  - los tipos y las mallas que van al recorrido;
  - el trabajo contado, las copias, la caducidad, la publicación entera, una malla rota y listas sin longitud;
  - los scripts de `python_exec` y de la terminal, con la comprobación previa de que el índice viejo habría
    respondido otra cosa.

  Tardan 0,36 s el que más.
- Once mutantes del código, cada uno cazado por al menos un test.
- Los tests de la malla y del acoplamiento (nueve archivos, 176 tests) y los de `python_exec` (8), solos: en verde.
- **Diferencial frente al recorrido viejo, en el mismo proceso,** antes de la revisión y otra vez con el código final:
  - las tres mallas distintas que guarda el banco (1441, 2852 y 386 elementos): 67 569 consultas, 0
    discrepancias;
  - las fuerzas «effective» de Lowe-Karafiath y de los dos del Corps, en 27 círculos de Ej_1 acoplado: idénticas;
  - K17, la rejilla de 396 círculos: los 322 factores idénticos en las cinco corridas del A/B;
  - el modelo de K17 con una rejilla de 539 círculos: serie igual a paralelo, y serie igual al recorrido viejo,
    con 438 evaluaciones.
- La huella de los 23 casos frente a 0.1.377: 23 de 23 idénticos (`all identical`, código 0), las dos veces: antes
  de la revisión y con el código final.
- La suite entera con `--jobs 4`: **6752 de 6752, `Failed: 0`**, sin `Leaks` ni `Chunks died`, en 28,3 min. La
  última serie en verde fue `8c4dcd3`, hace 7 commits.

## 3. Lo que queda

- **V6–V18,** cada una con su OK. La siguiente es V6: lo que no lee F en Bishop circular y en Janbu, una vez por
  solución.
- **Los hallazgos de arriba,** para que decidas si abren ficha.

## Archivos

- `ogr_core/fem/mesh.py`
- `ogr_api/pyexec.py`
- `ogr_gui/widgets/terminal.py`
- `tests/test_mesh_locator_v1383.py` (nuevo)
- `tests/_leaks.py`
- `docs/mcp/herramientas.md`
- `docs/changelog/CHANGELOG_v0.1.383.md` (nuevo)
- `README.md`, `README.es.md`
- `pyproject.toml`, `ogr_gui/main_window.py` y los `__init__.py` de `ogr_core`, `ogr_slip2d`, `ogr_fem2d`,
  `ogr_gui`, `ogr_cli`, `ogr_api` y `ogr_mcp` (el número)
