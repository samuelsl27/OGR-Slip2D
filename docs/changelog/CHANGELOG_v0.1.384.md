# OGR Slip2D v0.1.384

**Las pasadas de una solución de Bishop o de Janbu comparten lo que no lee F.**
- **Antes:** el punto fijo recalculaba en cada pasada, por dovela, las fuerzas, la carga del soporte, la
  linealización de la envolvente, la marca de resistencia nula y la trigonometría, y solo el denominador lee F.
- **Ahora:** la primera pasada guarda todo eso por dovela, y las siguientes solo forman el denominador y el cociente,
  con las mismas operaciones y en el mismo orden.
- **Medido en K03** (caso 001 a 31 212 círculos, Bishop y Janbu corregido, en serie para que el parche llegue a cada
  solución), en un mismo proceso y en el orden nuevo, viejo, viejo, nuevo, nuevo: de 119,3 y 119,1 s a **102,9 y
  102,1 s (−14 %)**, con todas las evaluaciones de los dos métodos idénticas en las cinco corridas. El primer nuevo,
  113,6 s, lleva el calentamiento del proceso; mandan los dos de control, que difieren un 0,8 %.
- **El trabajo:** las linealizaciones de la envolvente dentro de `x0_resisting_pass` pasan de una por dovela y pasada a
  una por dovela y solución. En K03, con 2,96 pasadas por solución:
  - las linealizaciones de la envolvente bajan de 7 360 077 a 4 394 702 (−40 %);
  - las llamadas a `slice_forces`, de 8 055 690 a 5 090 315.

  Son 2 965 375 menos de cada una, justo las visitas de las pasadas que reproducen el memo. Las de fuera del bucle
  (las fuerzas en la base del resultado, las comprobaciones, los sondeos de resistencia nula) siguen siendo
  2 987 052 linealizaciones, al elemento.

Es la V6 de la fase 3 de la auditoría del cómputo (`docs/audits/AUDITORIA_COMPUTO_v0.1.377.md`). Es de clase B:
idéntica por construcción y demostrada con la huella de los 23 casos del banco de pruebas, **23 de 23 idénticos** a
0.1.377, y con serie igual a paralelo en los 12 casos con pool, **12 de 12**.

## 0. Lo que se encontró y lo que se decidió

- **La puerta de medida se reproduce,** al elemento: en K03, 59 090 soluciones (29 545 de cada método), 174 921
  pasadas, 4 373 025 visitas a dovelas y 7 360 077 linealizaciones, como en 0.1.377. `x0_resisting_pass` se lleva
  50,9 s de los 100,1 que suman los dos métodos (el 51 %, como entonces; los segundos, con la máquina de hoy).
- **Qué lee F en una pasada** (`ogr_slip2d/methods/bishop.py`, `x0_resisting_pass`):
  - el denominador, m_α = cos α + signo·sen α·tan φ′/F en Bishop (1955) y n_α = cos²α·(1 + signo·tan α·tan φ′/F) en
    Janbu (1954);
  - y, en una dovela que cruza un soporte **pasivo**, su carga, porque la tensión se moviliza a t_pasiva/F.

  Todo lo demás es función de la dovela y de la solución: `slice_forces`, la carga de un soporte activo, la tensión
  estimada, el punto que impone `_imposed_reader` (fijo durante una solución), la linealización (`_local_c_phi`), la
  marca de `_zero_strength` y el numerador c·b + (W − u·b)·tan φ′.
- **El memo:**
  - es un diccionario de cada `compute_fos`, así que cada pasada de la envolvente propia (D84) y cada etapa de un
    desembalse tiene el suyo;
  - guarda por dovela el numerador, el factor trigonométrico, el producto signo·trig·tan φ′, la marca, la carga y la
    fuerza del soporte (como la tupla que devuelve: cada pasada publica una lista nueva);
  - una dovela con soporte pasivo no se guarda y se calcula entera en cada pasada (la condición es la de
    `support_vertical_load`, copiada);
  - el retroanálisis llama sin memo, porque su `imposed` puede lanzar.
- **La identidad:** el denominador se forma con las operaciones de la forma de una línea y en su orden,
  ((signo·trig)·tan φ′)/F y luego la suma o el producto, y el término es el mismo cociente. La guarda lo distingue al
  ulp: sacar 1/F del denominador, aunque sea solo en la rama que reproduce, hace fallar la prueba de cada dovela sola.
- **La revisión** (un workflow: tres revisores y un verificador por hallazgo):
  - **Pureza e identidad: ningún problema.** Cada valor de una fila es independiente de F en todos los caminos, y
    los modelos de resistencia son puros en su salida: sus cachés son deterministas y la primera pasada ya las llena
    con las mismas claves. El revisor comparó bit a bit con HEAD:
    - 2760 soluciones: 23 modelos de resistencia × sin soporte, activo y pasivo × agua × sismo × Steffensen, 840
      de ellas con pasadas de la envolvente, y 120 excepciones idénticas;
    - 12 desembalses por etapas;
    - 1050 soluciones de los casos de validación;
    - 54 colapsos forzados.
  - **Observadores externos: nada cambia de veredicto.** Un test cuenta las linealizaciones de una solución (643 →
    483) y solo pide que haya alguna. El contador `slice_trips` del banco de pruebas cuenta ahora visitas a dovelas y
    no evaluaciones; queda anotado en su LEEME.
  - **Los tests: dos huecos reales, cubiertos.**
    - La identidad solo se comparaba en la suma de las 40 dovelas, que se traga un ulp por dovela: sacar 1/F del
      denominador pasaba los diez tests y movía F en 3 de 105 soluciones. Ahora cada dovela se prueba sola.
    - Ningún test llegaba a un colapso de m_α en una pasada repetida, que es por donde pasan todos desde la segunda.

    Y dos endurecimientos: un soporte pasivo cuya componente tangencial empuja el deslizamiento (t_pasiva < 0), y
    que cada `compute_fos` pase un memo nuevo y que Janbu lo reproduzca.
  - **Once mutantes del código,** cada uno cazado por al menos un test.

## 1. Qué cambia

- `ogr_slip2d/methods/bishop.py`: `x0_resisting_pass` acepta `memo`, y `BishopSimplified.compute_fos` le pasa uno por
  solución.
- `ogr_slip2d/methods/janbu.py`: lo mismo en `JanbuSimplified.compute_fos` (y en Janbu corregido, que lo hereda).
- `tests/test_x0_memo_v1384.py`, nuevo: 15 tests, 0,21 s el más lento.
- El número, en los nueve sitios, y el contador de los dos README (6767).

## 2. Qué se probó

- `tests/test_x0_memo_v1384.py`, frente a `x0_resisting_pass` de 0.1.383 copiado literalmente como oráculo:
  - cinco factores seguidos, como una solución, con y sin memo: seco, con agua, con agua y sismo, una curva
    potencial leída donde la impone un lector, una curva por el origen con tres dovelas sin resistencia, un soporte
    activo (guardado), uno pasivo (recalculado en cada pasada) y otro pasivo cuya tangencial empuja el
    deslizamiento, en Bishop y en Janbu;
  - cada dovela sola, para que la suma no se trague un ulp;
  - un colapso de m_α y de n_α en una pasada repetida;
  - que cada solución reciba un memo nuevo y lo use en todas sus pasadas;
  - el trabajo contado: una linealización por dovela y solución, y las de las dovelas pasivas en cada pasada;
  - el `compute_fos` entero de Bishop y de los dos Janbu, con las pasadas de la envolvente propia, frente a la misma
    solución sin memo.
- Once mutantes del código, cada uno cazado por al menos un test.
- La huella de los 23 casos frente a 0.1.377: 23 de 23 idénticos (`all identical`, código 0). Los 12 gemelos en serie,
  idénticos a los de 0.1.377, y serie igual a paralelo en los 12 (código 0).
- La suite entera con `--jobs 4`: **6767 de 6767, `Failed: 0`**, sin `Leaks` ni `Chunks died`, en 26,6 min. La
  última serie en verde fue `8c4dcd3`, hace 8 commits.

## 3. Lo que queda

- **V7–V18,** cada una con su OK. La siguiente es V7: congelar las cachés fuera de una búsqueda (Global Minimum, la
  sensibilidad, la sonda y el Optimize suelto).

## Archivos

- `ogr_slip2d/methods/bishop.py`
- `ogr_slip2d/methods/janbu.py`
- `tests/test_x0_memo_v1384.py` (nuevo)
- `docs/changelog/CHANGELOG_v0.1.384.md` (nuevo)
- `README.md`, `README.es.md`
- `pyproject.toml`, `ogr_gui/main_window.py` y los `__init__.py` de `ogr_core`, `ogr_slip2d`, `ogr_fem2d`,
  `ogr_gui`, `ogr_cli`, `ogr_api` y `ogr_mcp` (el número)
