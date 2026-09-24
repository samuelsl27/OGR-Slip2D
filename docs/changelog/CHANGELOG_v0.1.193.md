# OGR Slip2D v0.1.193

**Tres fichas del paquete P0 —D175, D174 y D147— y una cuarta, D185, abierta
y cerrada en la tanda. D185 es la única que toca el motor.** Las comprobaciones
de cierre dejan de depender de la versión instalada, y el censo de m-alpha lee
el sismo donde el proyecto lo guarda. `ejecutar_caso.py` evalúa el círculo
publicado del 059 sobre el arco que dibuja la figura 59.2, y no sobre una masa
fusionada de 53 ft. Y al preparar eso apareció D185: desde v0.1.178 Spencer no
encontraba la raíz de ese arco teniéndola, y la contestaba la reserva.

De las tres fichas del encargo hubo que corregir la premisa antes de escribir
código (§0). Las tres son de banco, y el banco no está en git: lo que cambia en
`_tools/`, `referencia.json` y `_auditoria/` va descrito aquí y no aparece en
el diff del repositorio.

---

## 0. Lo que estaba mal en los encargos

### D175: no eran doce, y no todas caían sólo por el nombre

- En seco con 0.1.192 caían, además de las doce de la ficha y **sólo por la
  versión**, D144, D145, D146, D148, D149, D153, D159, D161, D120 y D155.
  Pedían `docs/audits/<x>_v1192.md` o `RESERVA_LAMBDA_0.1.192.md`. `d120` leía
  `ogr_slip2d.__version__` directamente, así que un grep de `_version()` no la
  veía. Son **23**, y el propietario decidió cerrar la clase entera.
- Varias dependían de la versión por **contenido**, no sólo por el nombre:
  `_actual` en `d54`, `d125` y `d163`; `ab.version` en `d113`, que además
  exigía al menos 20 resultados de la versión instalada; `resumen.version` en
  `d114`; `ver75` en `d61`, un campo archivado que nada podía cumplir; y la
  primera línea de sus documentos.
- Dos tenían además **desfase estructural**, por cambios legítimos:
  - `d61` buscaba `check_surface` dentro de `_is_admissible`, que desde
    0.1.192 (D177) llama a `screen_surface` con la nota idéntica carácter a
    carácter;
  - `d119` exigía una clase de test que 0.1.181 renombró, y `d148` exige la
    ausencia de esa misma clase: desde entonces no podían cerrar las dos a la
    vez.
- **La versión de cierre no está en el índice del ERRORES.** Esa columna es la
  instantánea que existía al retirar la ficha, y se equivoca en once casos:
  D113 dice 0.1.187 y cerró en 0.1.188, así que leer su censo por esa columna
  habría leído el de ANTES del arreglo; D54 dice 0.1.147 y su criterio se
  re-ancló en 0.1.160. Las versiones de `CIERRE` salen de los docstrings y del
  sufijo de cada test.
- Cinco censos de cierre no tienen `arbol_medido` (D113, D156, D157, D160 y
  D162).
- P-D175 se equivocaba con D163: sus cuatro cadenas sólo están en
  `CHANGELOG_v0.1.187.md`.
- **La segunda mitad del criterio no se puede cumplir aquí.** «Una corrida sin
  argumentos no cambia ningún veredicto de cierre» es falso por dos causas que
  no son D175: 16 cierres dependen de `_actual` y pasan a PENDIENTE DE CORRIDA
  tras cualquier subida (D186), y otros 11 no se sostienen por causas que no
  son la versión (D187). La ficha se re-enunció antes de cerrarla.

### D174: la mitad C tenía el mismo defecto, y la verificación del prompt era una trampa

- La mitad C del censo leía el sismo igual y **usaba** kh y kv en
  `margenes_de`. Hoy es inerte en número —kv = 0 en todo el banco y kh no entra
  en `w_total`—, pero seis filas de C publicaban kh = 0 donde el modelo tiene
  kh = 0,15.
- El comando de verificación del prompt, `--d111`, se salta la mitad C y
  **sobrescribía el censo canónico**. `d112()` habría pasado sobre nada.
- Re-correr el censo re-cerraba `d111` y `d112` por accidente, porque es
  justo el nombre que buscaban. Por eso D175 fue primero.
- No había guarda de qué árbol se medía.
- `104/modelo_ky` tiene kh = 0 porque ahí Ky se busca, no porque no haya sismo.

### D147: la fila, el alcance, el número del arco y la verificación

- La fila del 059 no publicaba lo que decía la ficha: **0,756384** (+26,9 %,
  de 0.1.181), no 0,772453. Esa cifra era la de la masa fusionada hasta
  0.1.177; D144 la movió (§1).
- El «66» no es el alcance. `ejecutar_caso.py` sólo lee `superficies`:
  46 problemas tienen algún extremo ahí, 107 entradas llevan los dos,
  12 están marcadas `evaluable: false` y quedan **95 entradas circulares
  evaluables**.
- **Aplicar los extremos a todas no da «cero dígitos movidos».** Vienen
  redondeados a tres decimales: nombrar la masa movería 134 de 139 parejas,
  casi todas por redondeo, y rompería dos (§4, D189).
  - En el 002 —grieta llena de agua— sube Janbu corregido un 8,1 % y Bishop un
    4,8 %, con el extremo a 0,0011 ft.
  - En la lente del 081 (`caso2_spencer`) los extremos publicados caen 0,07 ft
    fuera de la cuerda, y la masa nombrada se queda sin factor.
- El número del arco había cambiado. Spencer daba **0,558356 por la reserva**
  (λ 1,156, empuje inadmisible), no 0,5656 con horquilla. Y 0,5656 tampoco
  caía «dentro del 0,59–0,65» de los otros programas, que empieza en 0,59.
- Retirar la marca NO CONCLUYENTE del 059 rompía `d125()`, que la exigía.
- La verificación del prompt era destructiva: `ejecutar_caso.py
  --solo-publicado` vacía los resultados.
- La base citada estaba caducada: es `Evaluaciones/0.1.192`, no 0.1.176.
- No se puede cambiar lo que devuelve `normalizar_superficie`: rompería siete
  llamadores y cambiaría en silencio otros tres.
- A59-2 sólo cuenta como cerrada si lleva `cerrada_en`
  (`generar_comparativa.py`).

---

## 1. D185 — el reintento del compañero (motor)

**Cómo apareció.** En la corrida en seco que acotó D147, `d125()` caía porque
«sobre el arco publicado (0 .. 12,583) el motor no horquilla». Su cierre de
0.1.176 afirmaba lo contrario.

**La bisección** (`_tools/biseccion_arco_059.py` del banco; un worktree por
versión, cada una en un subproceso con la guarda de que ningún `ogr_*` viene de
fuera; `_auditoria/D125_lambda/059_arco_biseccion_0.1.193.json`). El `.ogr` del
059 es idéntico byte a byte en todo el rango.

| versiones | Spencer sobre el arco | cómo | Bishop sobre el arco | masa fusionada |
|---|---|---|---|---|
| 0.1.176–0.1.177 | 0,565573 | horquilla, λ 0,8836 | 0,567809 | 0,772453 |
| 0.1.178–0.1.180 | 0,559420 | reserva, λ 1,0 | 0,559296 | 0,756384 |
| 0.1.181–0.1.192 | 0,558356 | reserva, λ 1,15625 | 0,559296 | 0,756384 |

**El diagnóstico.** 0.1.178 es D144, que corrigió el brazo del soporte en el
momento circular. Es física, y se mide como física: F_f(λ) sale idéntica bit a
bit entre 0.1.177 y 0.1.178, y F_m entre un 1,6 y un 2,1 % más baja. La raíz no
desapareció: se movió a λ ≈ 1,36. Ahí la rama de fuerzas, desde `initial_fos` =
1,0 y aun desde 0,5570 —pegada a la respuesta—, oscila hacia fuera (0,557 →
0,610 → 0,515 → 0,648 → 0,717…) y sale por la puerta de «inadmisible» de
`solve_branch` antes de la pasada 30. Eso es antes de que `STALL_PATIENCE`
arme el rescate y antes de que `CYCLE_RUN` pueda tomarla. Con el rescate armado
desde la primera pasada y arrancando cerca de la respuesta, converge.

**El arreglo.** `interslice.BRANCH_PARTNER_RETRY`, leído en
`GLESystem._solve_states`. Si la rama de fuerzas vuelve `None` y la de momentos
convergió en el MISMO λ, la de fuerzas se resuelve otra vez desde el F de
momentos con `rescue_gate=1`, y el estado nuevo se toma sólo si converge.

- Por qué el F de la compañera: en una raíz F_f = F_m, así que donde las dos
  ramas se cruzan ese F ES la respuesta que la rama perdida busca; y es el único
  arranque que no lee otro λ. Uno prestado de un λ vecino haría depender
  `states(λ)` del orden de las preguntas, y la caché de D159 es una identidad
  precisamente porque no depende.
- Lo que no puede cambiar: sólo actúa donde `solve_branch` devolvió `None`, así
  que una rama que converge, o que termina con un estado que dice por qué paró,
  no se toca. Y sólo puede ADMITIR: un reintento que no converge deja el `None`
  donde estaba.
- Lo que no hace: no reintenta la rama de momentos. Ningún caso lo necesita, y
  un interruptor simétrico sin testigo no demuestra que mueva nada.
- `BranchState.retried`, `GLESystem.n_retried` (los reintentados cuentan también
  en `n_rescued`, porque aceptan por el test del rescate) y
  `_STATES_SWITCH_NAMES`, que mete el interruptor en la firma de la caché. Es
  una lista aparte porque `_BRANCH_SWITCH_NAMES` se comprueba por AST contra el
  cuerpo de `solve_branch`.

Medido sobre el arco en una rejilla de 0,025
(`_auditoria/D185_reintento/tramo_reintento_0.1.193.json`): sin el reintento la
rama de fuerzas se pierde en todo λ desde 1,175, y el reintento los recupera
todos hasta 1,55, en 42 a 106 pasadas. Desde 1,575 tampoco converge la rama de
momentos, así que no hay compañera de la que arrancar, y el reintento no actúa.

Sobre el arco: **0,557188 con horquilla en λ 1,3564**, a un 0,21 % del número
de la reserva. El empuje es inadmisible en todo λ, así que la respuesta se da
con el criterio relajado y `admisible: false`. Eso es física del arco y no el
reintento: la respuesta de la reserva era inadmisible también.

**El censo del banco** (`_tools/censo_reintento_d185.py`: cada superficie con
el interruptor apagado y encendido en el mismo proceso;
`_auditoria/D185_reintento/censo_0.1.193.json`, con el motor y el banco
definitivos). Son 546 filas: 257 críticas archivadas de búsqueda y 289 círculos
publicados, de Spencer y GLE, sin ninguna saltada.

- **Se mueven 6.** Las dos entradas del arco del 059 pasan de la reserva a la
  horquilla (0,558356 → 0,557188). Las cuatro críticas Spencer del 090 y el 093
  siguen en la reserva, con la muestra más cercana a la raíz en λ 1,0.
- Ninguna pasa de horquilla a reserva, y ninguna gana ni pierde factor.
- **Dos cambian de admisibilidad**, las del 090 (abajo).

**Lo que el censo no ve** —el mínimo de una búsqueda entera— lo dicen dos A/B:

- **El 059**, en el mismo proceso, con la búsqueda en serie para que el
  interruptor llegue a cada círculo (`_auditoria/D185_reintento/ab_059_busqueda_0.1.193.json`).
  El mínimo es 0,565633574 en las tres pasadas (encendido, apagado,
  encendido); lo único que cambia es `inadmisibles`, de 32 a 34. El recuento
  neto de superficies con empuje inadmisible sube en dos, y ninguna era la
  ganadora.
- **El 090 y el 093**, re-corridos enteros dos veces con `correr_todo.py
  --forzar 90 93` (`_auditoria/D185_reintento/ab_090_093_0.1.193.json`). La
  pasada A lleva el interruptor apagado EN DISCO, porque la búsqueda reparte
  círculos entre procesos y un parche en memoria no llega a los hijos; tardó
  4772 s. La B lleva el motor definitivo y tardó 4144 s.
  - B − A, que es D185 y nada más: sólo se mueven las cuatro filas Spencer, y los
    cuatro mínimos siguen saliendo **por la reserva**. Bishop, GLE y los
    círculos publicados salen idénticos.
  - **090**: 0,897195 → 0,896155 (−0,12 %) y, sin conexión, 0,902380 → 0,896155
    (−0,69 %). El mínimo nuevo es un círculo (−1,333; 16,824; R 12,938) cuya
    reserva era INADMISIBLE sin el reintento (0,896222 en λ 0,928) y es
    ADMISIBLE con él (0,896155 en λ 1,0). Es la parte que el censo sobre la
    crítica archivada no podía ver: predecía −0,030 % y −0,017 %.
  - **093**: 0,989818 → 0,989734 (−0,008 %) en los dos modelos, sobre el mismo
    círculo.
  - A nivel de rama el reintento sólo añade estados convergidos. A nivel de
    superficie cambia qué muestra elige la reserva, y con ella la
    admisibilidad, **en los dos sentidos**: en el 090 una superficie se vuelve
    admisible, y en el 059 dos se vuelven inadmisibles.
  - A − archivado es deriva de 0.1.181 a 0.1.193 sin D185, y **no se ha
    bisecado**. Bajan los recuentos de inadmisibles de Spencer y GLE en los
    cuatro archivos, y el mínimo Spencer del 093 baja un 0,88 % (0,998622 →
    0,989818) y un 0,38 % sin conexión (0,993611 → 0,989818), porque el círculo
    R 12,938, que en 0.1.181 no era el mínimo, pasa a serlo.

**Dos tests existentes cambian de caso, y no de lo que afirman.**
`test_relaxed_thrust_v1130` (el veto sin horquilla) y `test_thrust_flag_v1185`
(las dos puertas) usaban un talud con 1000 kN/m cuya raíz existía y el solver
no alcanzaba. Con el reintento, esa capacidad horquilla (Spencer 16,1284 en λ
0,5935, GLE 16,1280 en 0,8831). Subir la capacidad no sirve: de 1000 a 3300
kN/m todas horquillan, y desde 3350 todos los λ divergen, que es otra puerta.
La puerta sin horquilla la abre ahora el mismo talud con suelo cohesivo
(φ = 0, c = 30 kPa, 200 kN/m): con φ = 0, F_m no depende de λ y no hay raíz que
alcanzar, que es el mecanismo del problema 85 a escala de fixture. Los dos
archivos pasan igual en el árbol de 0.1.192.

## 2. D175 — la clase entera (`_tools/verificar_cierres.py`)

**`CIERRE`**: las 23 fichas con su versión de cierre.

| versión | fichas |
|---|---|
| 0.1.160 | D54 |
| 0.1.175 | D120 |
| 0.1.176 | D125 |
| 0.1.177 | D119 |
| 0.1.178 | D144 |
| 0.1.179 | D145 |
| 0.1.180 | D146 |
| 0.1.181 | D148 |
| 0.1.182 | D149 |
| 0.1.184 | D153 |
| 0.1.185 | D155, D156 |
| 0.1.186 | D157, D159 |
| 0.1.187 | D160, D161, D162, D163 |
| 0.1.188 | D113 |
| 0.1.189 | D111, D112 |
| 0.1.190 | D114, D61 |

**Ayudantes nuevos:**

- `_historico(ruta)` para lo que se escribió una vez (changelogs, `docs/audits`,
  curvas, informes y los cinco censos sin `arbol_medido`): el nombre exacto de
  la versión de cierre, sin regex. Si falta, lo dice; nunca cae a otro archivo.
- `_censo_desde(carpeta, prefijo, desde)` para lo que se re-mide: regex anclada
  `^<prefijo>_(\d+)\.(\d+)\.(\d+)\.json$`, que deja fuera `_parcial`,
  `_desde…` y `_antes`. El de la versión de cierre se acepta tal cual; uno
  posterior, sólo si lleva `completo` y su `arbol_medido` es el repositorio.
- `_de_cierre(d, ficha)`: `version_ogr` ≥ la de cierre, comparada como tupla.
- `_doc_audit(nombre, ficha)`: `docs/audits/<nombre>_v<menor><parche>.md` de la
  versión de cierre.
- `REPO_MOTOR`: una sola ruta del motor. Dieciocho funciones que la escribían a
  mano sólo cambian eso (comparado por función contra el archivo de 0.1.192).

**En cada miembro**, todo nombre formado con la versión pasa por esos
ayudantes; `_actual` sobre un archivo histórico pasa a `_de_cierre`; la primera
línea de un documento se compara con la versión de su propio nombre; y lo vivo
no se toca. Los dos desfases estructurales se declaran como tales: `d61` acepta
`screen_surface` además de `check_surface` y EJECUTA el cribado (rechaza con
`check_m_alpha` una superficie bajo el límite y la admite sin él); `d119` sigue
la clase renombrada.

Fuera de la clase se ajustaron cuatro, porque violaban la regla AST de
`d175()`: `d132` y `d134` pasan a `_actual` sin cambiar de veredicto; `d79` lee
el `TRACCION_BANCO` más nuevo desde su re-ancla de 0.1.160 y sigue en NO SE
SOSTIENE por sus otras causas (D187); `d158` lee los artefactos de su versión de
cierre y pasa de SIN CRITERIO a PARCIAL, que es su estado real.

**`d175()`**, veredicto CUBIERTO POR CODIGO, con cuatro medidas:

1. AST sobre el archivo entero: `_version()` sólo en `_version` y `_actual`;
   `__version__` sólo en `_version` (y en `d175`, que lo escribe); ni
   `getattr(..., "__version__")` ni `importlib.metadata`; ningún miembro llama
   a `_actual`.
2. Doble ejecución de los 23, con la versión real y con
   `ogr_slip2d.__version__ = "0.1.999"`. Se parchea el paquete y no `_version`,
   porque el archivo corre como `__main__` y un `mock.patch` parchearía otra
   copia; una sonda comprueba que el parche llegó. Exige el mismo
   `(veredicto, detalle)` y un veredicto de cierre, salvo las excepciones
   escritas con su razón (hoy sólo D119, superada por D148: D187).
3. Mutación: con `_SIN_HISTORICO` todo artefacto histórico se da por ausente, y
   ningún miembro puede seguir cerrando. Sin esto, «no depende de la versión»
   se cumpliría también dejando de leer la evidencia.
4. La equivalencia archivada (`_tools/equivalencia_d175.py`): el archivo de
   0.1.192 ejecutado con la versión de cierre de cada miembro contra el nuevo
   con 0.1.193, sobre el mismo árbol y el mismo motor. **18 iguales y 5
   diferencias, las cinco declaradas antes de medir**: D54, D61, D113 y D119 son
   de D175, y D125 es de D147, porque el archivo viejo exige la marca NO
   CONCLUYENTE que D147 retira. Ninguna sin declarar, y ninguna declarada que
   no difiera.

**Por qué no contra el árbol anterior**, que es lo que pedía el prompt. D175
sólo cambia de dónde se lee lo histórico, y la discriminación de cada miembro
contra su árbol previo ya se midió en su propio cierre. Repetirla aquí no
discrimina: doce miembros devuelven «falta el test» antes de ejecutar nada, y
tres medidores del banco (`borde_admisible_d149.py`, `curva_cuna_d119.py`,
`suelo_horquilla_d153.py`) meten el repositorio vivo en `sys.path[0]`, porque
su guarda compara `/` con `\`. En un worktree medirían el motor equivocado
(D187). Lo que prueba que ningún miembro se debilita son la mutación y la
equivalencia.

## 3. D174 — el censo lee `p.seismic`

- `_sismo_aplicado(p)` lee `p.seismic` por atributo, sin `getattr` con valor por
  defecto, y lo usan las dos mitades. Por fila se publican `sismo_activo`, `kh`,
  `kv` y `ky_buscado`; este último sale de `settings.seismic.compute_ky`, que es
  una lectura legítima, para que el cero del 104 `modelo_ky` no se lea como
  «sin sismo».
- El resumen publica las listas de modelos con sismo activo, con kh ≠ 0 y con
  kv ≠ 0, y los controles `A_CONTROL_004_KH` y `C_CONTROL_004_KH`.
- `_modulo_medido()`, `modulo_medido` y `huella_motor` (hash de las fuentes de
  `ogr_slip2d`). `completo: true` sólo sin banderas; con `--d111`, `--d112` o
  una lista de problemas se escribe `censo_<v>_parcial.json`, nunca el canónico.
- En el motor: `_slope()` de `tests/test_slide_sign_by_method_v1189.py` pierde
  `kv`, `kh` y la rama que los escribía en `p.settings.seismic`. Nadie los
  pasaba, así que se quita en vez de corregirse: un parámetro que nadie pasa es
  un ajuste que no hace nada (regla 7). Se actualiza el docstring de
  `tests/test_sigma_seismic_v1191.py`, que lo describía como vigente.

**El censo re-corrido** (`_auditoria/D111_D112_m_alpha/censo_0.1.193.json`,
completo, sobre el repositorio): 8 modelos con sismo activo, 7 con kh ≠ 0,
ninguno con kv ≠ 0 y uno con Ky buscado; el control del 004 vale 0,15 en A y
en C. Comparado clave a clave con el de 0.1.189, sólo cambia lo declarado:

- A: `kh` en las siete filas con kh ≠ 0, más las dos columnas nuevas;
- C: `kh` en las seis filas de Janbu del 004 y el 051, y la versión del
  archivo en la del 059, que se re-corrió; márgenes y signos idénticos;
- B: `segundos` y la versión del motor en las 22 filas que se corren, y la
  versión del archivo en las dos del 059; ninguna fila se mueve;
- el resumen: la versión y las claves nuevas.

**`d174()`**, CUBIERTO POR CODIGO: por AST, ninguno de los 373 archivos
(`_tools` del banco y `tests` del motor) lee ni escribe kh, kv o enabled sobre
`<x>.settings.seismic`, ni directamente ni por un alias; las dos mitades leen
por `_sismo_aplicado`; y las listas del censo coinciden con lo que se cuenta
en vivo en el `seismic` de primer nivel de los `.ogr`, sin un 8, un 7 ni un 0
tecleados. `d111()` y `d112()` leen el censo por `_censo_desde` y exigen que no
esté vacío.

## 4. D147 — la masa nombrada, por opt-in de entrada

- `ejecutar_caso.extremos_nombrados(s)`: `None` si la entrada no pide
  `masa_nombrada`; si la pide, las x de `izq`/`der` o de
  `extremo_izquierdo`/`extremo_derecho`. Un opt-in sin los dos extremos revienta
  con `ValueError` (regla 7). Lo que devuelve `normalizar_superficie` no cambia.
- `_recorrer_superficies` pone `x_left`/`x_right` sólo en ese caso, y archiva
  `masa_nombrada` en `circulo_reevaluado[<método>]`. Un opt-in sobre una
  polilínea revienta. `curva_lambda.py` usa la misma función.
- **A/B de la herramienta** (`_tools/censo_extremos_d147.py`, archivo viejo
  contra nuevo sobre el mismo motor): 557 superficies en 81 problemas, 555
  iguales bit a bit; las dos que difieren son las dos entradas del 059 con
  opt-in. Ninguna sin opt-in se mueve.
- **Censo contrafactual**: qué pasaría si cada entrada nombrara su masa. Cubre
  94 de las 95 entradas evaluables en 40 problemas y 139 parejas; la que falta,
  la del 099, no tiene resultados que la evalúen, y el censo lo dice.
  - Se moverían 134, casi todas por redondeo: mediana |Δ| 0,0004 %,
    percentil 90 0,009 %.
  - Pasan del 0,1 %: el 002 (+8,1 % Janbu corregido, +4,8 % Bishop), el 042
    `modelo_sin_grieta` (+0,29 %) y las dos del 059, que son el opt-in.
  - Una se queda **sin factor**: la lente del 081 (`caso2_spencer`).

  Es la razón medida de que el opt-in sea por entrada.
- `059/referencia.json`: `masa_nombrada: true` en las dos entradas, fuera
  `estado_forzado` y `no_concluyente`, y A59-2 con `cerrada_en: "0.1.193
  (D147)"` y la prosa corregida.
- **`d147()`**, CUBIERTO POR CODIGO: ejecutado sobre el 059, con y sin opt-in
  salen números distintos, y el nombrado es exactamente el de
  `GridSearch.evaluate_circle` con `x_left`/`x_right` puestos; un opt-in sin
  extremo revienta; `normalizar_superficie` sigue devolviendo tres valores; el
  A/B y el censo archivados; y el 059 sin marca, con A59-2 cerrada y su
  `resultados.json` ≥ 0.1.193 con la masa archivada.
- El bloque del 059 de `d125()` exige ese mismo estado más la horquilla
  ejecutada sobre el arco.

---

## 5. Lo que se reporta y NO se corrige (regla 6)

- **D186** (P0): 16 cierres —D03, D20, D38c, D49, D50, D64, D65, D66, D77, D91,
  D98, D127, D129, D132, D134 y D135— usan `_actual` y pasan a PENDIENTE DE
  CORRIDA en cuanto sube la versión. `_auditoria/verificacion_cierres.json`
  conserva sus veredictos sólo porque `main()` acumula, así que una corrida sin
  argumentos los sobrescribiría. Además hay 15 claves huérfanas en ese JSON y
  tres copias del conjunto de veredictos que cierran. Es la mitad de D175 que su
  cierre no podía cumplir.
- **D187** (P0): once cierres archivados no se sostienen por causas que no son
  la versión —dígitos fijados que otras versiones movieron (D79, D94, D95, D118,
  D44), desfase estructural (D116, D117), lectores que no encuentran su fila en
  la comparativa (D82, D83), estado del banco (D69, D108)—, más D74 en PARCIAL,
  D119 superada por D148 y los tres medidores que secuestran `sys.path`.
- **D188** (P0): las fichas retiradas apuntan a instantáneas que ya no
  contienen su sección, porque el orden de cierre reescribe la instantánea
  después de retirar; y D181 no está en ninguna. Esta tanda guarda a mano, dentro
  de la instantánea, las copias de antes de retirar.
- **D189** (P0): lo que destapó el censo de D147.
  - En el 002, la masa nombrada pierde el empuje de la grieta con agua por
    0,001 ft, **comprobado ejecutando**
    (`_auditoria/D147_extremos/mecanismo_002_0.1.193.json`). Hoy la masa
    termina sobre la línea de la grieta y la superficie lleva la pared. Con los
    extremos publicados —que son esa pared, redondeada— la coronación queda
    0,0016–0,0022 ft por debajo de la línea: `apply_tension_crack_truncation` no
    trunca, no registra pared y no se aplica el empuje.
  - La lente del 081 se queda sin factor con sus extremos publicados.
  - `auditoria_reserva_lambda.py`, `auditoria_traccion.py` y otras herramientas
    siguen evaluando la masa fusionada del 059. Medido en una:
    `clasificar_d37.py` clasifica la fila del 059 como **C5-inalcanzable** («la
    búsqueda no lo genera») porque evalúa la masa fusionada, cuando con la masa
    nombrada es **C2-inadmisible**, una exclusión legítima. Además, correrlo con
    `--problemas 59` pisaría `D37_CAUSAS.md` de todo el banco. La fila se
    clasificó en memoria (`_auditoria/D147_extremos/d37_059_0.1.193.json`) y
    queda anotada en la ficha abierta D37.
  - `_tools/ficha_59.py` reescribe `anomalias` de `referencia.json` sólo con
    A59-1: correrlo borraría A59-2 y rompería `d125` y `d147`. La ficha del 059
    se corrigió a mano por eso.

## 6. El banco: qué se re-corre y por qué

- **El 059**, con `correr_todo.py --forzar 59` (24 s): el círculo publicado pasa
  de 0,756384 (la masa fusionada, 0.1.181) a **0,557188** sobre el arco, con
  horquilla y `admisible: false`. Los mínimos de búsqueda de los cinco métodos
  no se mueven ni un dígito. Aparecen `intentos` y `rechazos_foco`, que son
  claves de esquema de D160 (0.1.187) que el archivo de 0.1.181 no tenía, y
  `spencer.inadmisibles` pasa de 32 a 34, atribuido a D185 por el A/B del §1.
- **El 090 y el 093**, los únicos problemas cuyas filas movía el censo de D185,
  con el A/B del §1. En la comparativa se mueven sus cuatro filas Spencer. Las
  del 090 por D185; las del 093 sobre todo por la deriva de 0.1.181 a 0.1.193,
  y un 0,008 % por D185. Todo lo demás de esos archivos sale idéntico.
- **Nada más.** D174 y D175 sólo tocan herramientas de medida; D147 sólo cambia
  lo que lleva opt-in, que es el 059, y el A/B lo demuestra sobre las 557
  superficies.

**El balance contra `Evaluaciones/0.1.192`**
(`_auditoria/BALANCE_0.1.192_a_0.1.193.md`): 559 → 559 filas, 556 iguales y 0
sin pareja.

- **Una cambia de estado.** 059 Spencer pasa de NO CONCLUYENTE a
  **DISCREPANCIA**: el círculo publicado ya no es la masa fusionada (0,7564,
  +26,91 %) sino el arco, «0,5572 ⚠ inadmisible» (−6,51 %). La búsqueda sigue en
  −5,09 %.
- **Dos se mueven sin cambiar de estado.** 090 Spencer pasa de −10,46 % a
  −10,56 %, por D185. 093 Spencer pasa de +4,35 % a +3,42 %, casi todo por
  deriva y un 0,008 % por D185.
- En las filas GLE de 090 y 093 sólo cambia el recuento de descartadas, por
  deriva. En las filas de 059, 090 y 093, la columna de versión pasa de 0.1.181
  a 0.1.193.

## 7. Errores propios detectados antes de publicar

Cinco habrían publicado una afirmación falsa o una medida con otro
denominador:

1. **El censo contrafactual de D147 se saltó 14 entradas sin decirlo, y de ahí
   salió una corrección falsa que casi se publica.** Medía una entrada con
   `modelo` propio «una vez, con `resultados.json`», y 052, 062, 078, 079, 081 y
   085 no tienen ninguno: publicó 80 entradas como si fueran todas. Con esa
   corrida escribí aquí que la exploración se equivocaba al dar por roto el 081,
   porque su entrada `spencer` se movía un 0,0003 %. La entrada rota es la lente,
   `caso2_spencer`, una de las 14 saltadas, y se queda sin factor. Lo destapó
   reconciliar el recuento con el del plan (95 evaluables). Ahora cada entrada
   con modelo propio se mide con el archivo que evalúa ese modelo, y el resumen
   publica `entradas_evaluables` y `ENTRADAS_SIN_MEDIR` con su motivo; `d147()`
   lo exige. Es la misma clase que ya perdía filas en los censos de publicadas.
2. **El censo de D185 se corrió un minuto antes de poner el opt-in del 059.**
   Sus dos filas publicadas del 059 midieron la masa fusionada, así que no vio
   la única que pasa de reserva a horquilla, justo la que motivó la ficha.
   Re-corrido con el estado final: 6 filas se mueven en vez de 4, y las otras
   540 salen idénticas bit a bit entre las dos corridas.
3. **La primera corrida del censo de D185 se saltó 53 archivos** con
   `KeyError: '__carpeta__'`: construía la referencia sin la clave que todos
   los demás llamadores de `evaluar_circulos_publicados` ponen. Re-corrido con
   0 saltados, y `d185()` exige `saltadas` vacío.
4. **La equivalencia de D175 se midió primero con el motor de antes de D185**
   (huella 646fe2a7…) y antes de re-correr el 059. Ahí D125 salía «igual»
   porque el archivo viejo y el nuevo fallaban por lo mismo. Re-medida con el
   motor definitivo, con la diferencia de D125 declarada ANTES de medir, y la
   predicción se cumplió: el viejo sólo falla por la marca que D147 retira.
5. **Dos docstrings afirmaban más de lo que miden.** El de `d147()` repetía
   cifras del plan escritas antes del censo («moveria unas 66 filas»). El de
   `d185()` decía comprobar F_f = F_m en el λ devuelto, y sólo comprueba que no
   salga por la reserva; la identidad la afirma el test.

Y uno que sólo vio la suite entera:

6. **La selección dirigida no incluía el test que el reintento rompía.** Corrí
   `partner_retry relaxed_thrust thrust_flag slide_sign sigma_seismic
   version_consistency lambda` (192/192), y la primera suite entera dio
   **4232/4233** en 26 min 02 s. `test_max_iterations_scope_v1173.py` exige que
   TODA rama que resuelve `GLESystem` lleve `max_passes=self.max_passes` y
   cuenta exactamente dos llamadas a `solve_branch`; el reintento es la tercera.
   Pasa el mismo presupuesto, así que la promesa del test (D117) se cumple, y el
   recuento pasa a 3 con la razón escrita. Sigue siendo exacto a propósito, para
   que la siguiente llamada que se añada tenga que pasar por ahí.

Y los demás:

7. El patrón que `transformar_d175.py` sustituía, `RAIZ = Path(__file__)…`,
   aparecía dos veces en `verificar_cierres.py`. La guarda de «exactamente una
   coincidencia» abortó antes de escribir; se ancló a la línea siguiente y se
   comprobó el archivo contra la copia antes de volver a lanzarlo.
8. La regla AST de `d175()` se encontró a sí misma: `d175` escribe
   `__version__` para la doble ejecución. Queda exceptuada por nombre, con la
   razón al lado.
9. `EXCEPCIONES_D175` conservó D125 después de que cerrara. Una excepción que
   sobra no se nota hoy y tapa mañana una regresión de D125 dentro de `d175()`.
10. El primer fixture de la puerta sin horquilla (5000 kN/m) caía en «todos los
   λ divergen», que es otra puerta. Se barrió y se eligió el suelo cohesivo.
   El docstring de `_reinforced` en `test_thrust_flag_v1185.py` conservó el
   «5000» hasta que se releyó para este changelog.
11. El A/B de la búsqueda del 059 decía primero QUÉ dos superficies pasaban a
   inadmisibles («las que la reserva contestaba sin juzgar su empuje»). Eso no
   se midió; se dice el recuento neto.
12. El prompt de D189 decía que `apply_tension_crack_truncation` no tiene
    tolerancia. La tiene: `1e-9·max(x_right − x_left, 1)`, relativa, y
    despreciable frente a los 0,0012 ft del redondeo.
13. **El comentario de `BRANCH_PARTNER_RETRY` decía dos cosas que no se habían
    medido así.** Que la reserva dio 0,558356 «en toda versión de 0.1.178 a
    0.1.192», cuando de 0.1.178 a 0.1.180 dio 0,559420 en λ 1,0. Y que el
    reintento converge «en todo λ de 1,15 a 1,50 en 40 a 70 pasadas», cifra que
    era del diagnóstico (el rescate armado arrancando cerca de la respuesta) y no
    del reintento. El test, por su parte, decía 1,20–1,55. Medido el tramo del
    reintento, es 1,175–1,55 en 42–106 pasadas. Se corrigieron los dos
    comentarios después de la pasada A y antes de la B, con el AST de
    `interslice.py` idéntico al medido. La huella del motor pasa de
    `f453b0ef3bb08752` a `6a7c38eb0e5e91ad`, y los dos son el mismo programa.

## 8. Los tests

| Archivo | Casos | Fallan en 0.1.192 | Por comportamiento |
|---|---|---|---|
| `test_partner_retry_v1193.py` (nuevo) | 18 | 14 | 9 (5 débiles: falta un nombre) |

Discriminación MEDIDA en un `git worktree` de 0.1.192 con sólo este archivo
copiado dentro. Ningún test fija un factor contra una instantánea. Los anclajes:

- la identidad de Spencer (1967): en el λ que devuelve la búsqueda las dos
  ramas convergen y F_f = F_m a la tolerancia, y g cambia de signo a los dos
  lados;
- el A/B del interruptor en el mismo proceso (regla 7);
- la identidad bit a bit de todo lo que el reintento no alcanza (la masa
  fusionada, GLE sobre el mismo arco, todo λ cuya rama ya tenía estado);
- el contrato del reintento, ejercido INYECTANDO lo que devuelve el solver de
  rama, porque un reintento que falla no ocurre sobre el testigo;
- hechos AST sobre la firma de la caché.

El testigo es el 059 construido en código con su anclaje, y reproduce el banco
dígito a dígito contra el propio modelo del banco: 0,558355659095 por la
reserva sin el reintento, 0,557188309996 con horquilla con él.

Cambian de caso, no de afirmación, `test_relaxed_thrust_v1130.py` y
`test_thrust_flag_v1185.py` (§1): 33 casos, verdes en los dos árboles, medido
otra vez con su versión final en un worktree de 0.1.192.
`test_max_iterations_scope_v1173.py` cuenta tres llamadas a `solve_branch`
donde contaba dos (§7, error 6). Y `test_slide_sign_by_method_v1189.py` y
`test_sigma_seismic_v1191.py` cambian por D174 (§3).

## 9. Verificación

**Estructural.** El diff del motor es `interslice.py` —el interruptor, el campo
`BranchState.retried`, `_STATES_SWITCH_NAMES` en la firma de la caché,
`GLESystem.n_retried`, el reintento en `_solve_states` y su recuento en
`branches`— y los siete sitios de versión. Ningún método de análisis cambia una
línea. En los tests: un archivo nuevo y cinco retocados (§8). Los README ponen
al día su contador (3188 → 4233, caducado desde v0.1.151) y su tiempo (decía
5–7½ minutos).

- **Suite entera, sin argumentos y con el changelog escrito: 4233/4233**, sin
  banner `FILTERED RUN`, sola en la máquina, en 25 min 55 s. 0.1.192 traía
  4215; los +18 son exactamente el archivo nuevo. La primera suite entera dio
  4232/4233 en 26 min 02 s (§7, error 6).
- Selecciones dirigidas: 192/192 (`partner_retry relaxed_thrust thrust_flag
  slide_sign sigma_seismic version_consistency lambda`); 37/37
  `max_iterations_scope` tras el arreglo; 51/51 `agent_scaffolding license`
  tras tocar los README. Y los dos archivos que cambiaron de caso, en su versión
  final, 33/33 en un worktree de 0.1.192.
- `verificar_cierres.py`, primero en seco y después escribiendo sólo lo que
  cierra.
  - D147, D174 y D175 salen **CUBIERTO POR CODIGO**, y D185 **CUBIERTO POR
    TEST**.
  - De los 23 miembros de D175 cierran 22 (D155, RE-ENUNCIADO). D119 sale NO SE
    SOSTIENE, que es su excepción declarada (D187).
  - Los controles D110, D165 y D167 siguen cerrando.
  - D132 y D134 dan PENDIENTE DE CORRIDA (D186), D79 NO SE SOSTIENE (D187) y
    D158 PARCIAL. Esos cinco, y D119, sólo se corrieron en seco: escribirlos
    habría degradado su veredicto archivado, que es justo D186.
  - `verificacion_cierres.json` pasa de 149 a 153 claves, y no cambia ningún
    veredicto existente.
- `d175()`: AST, doble ejecución con 0.1.999 y su sonda, mutación, y la
  equivalencia re-medida con el motor definitivo: 18 iguales, 5 declaradas y 0
  sin declarar.
- Censos con el motor definitivo (huella `6a7c38eb0e5e91ad`):
  - D174: 194 modelos, 37 filas en B y 80 en C;
  - D185: 546 filas, 6 se mueven;
  - D147: el A/B de 557 superficies y el censo de 139 parejas.
- `comprobar_columna_circulo.py`: OK. Sus cuatro avisos son huérfanos del 47,
  anteriores a esta tanda.
- `generar_comparativa.py` y el balance contra `Evaluaciones/0.1.192`: 559 →
  559 filas, 556 iguales, una que cambia de estado (059 Spencer) y dos que se
  mueven sin cambiar (090 y 093 Spencer), 0 sin pareja (§6).
- `retirar_cerrados.py --escribir D147 D174 D175 D185`: 4 secciones retiradas y
  4 renglones en el índice, citando `Evaluaciones/0.1.193`.
  - La instantánea conserva `ERRORES_Y_DISCREPANCIAS_antes_de_retirar.md` y
    `PROMPTS_RESOLUCION_antes_de_retirar.md`, con las cuatro secciones: el
    remedio a mano de D188.
  - A mano: `PAQUETES` podado y con D186–D189, la fila de P0 de la tabla de
    paquetes, y la cabecera del ERRORES en «último usado D189».
- `PROMPTS_RESOLUCION.md`: 50 prompts, 41 largos. El generador sale con 1 por
  los nueve FALTA de antes de esta tanda (D137, D138, D139, D142, D143, D150,
  D151, D168 y D169), ninguno de ella.
- `auditoria_invariantes.py`:
  - 02: **0 ERROR**, 743 hallazgos (488 AVISO y 255 INFO; 0.1.192 tenía 748,
    491 y 257). Los cinco que desaparecen son del 059, cuya ficha corregida a
    mano ya cuadra con su `resultados.json`.
  - raíz: **0 ERROR**, 64 AVISO, ninguno de esta tanda.
- Instantánea `Evaluaciones/0.1.193`: 1726 archivos comprobados byte a byte,
  retomada con `--forzar` después de retirar. Cinco archivos están a 0.1.193: el
  059, y el 090 y el 093 con sus dos modelos.

Y una advertencia que va aquí porque es fácil de leer al revés. Que el censo de
D185 mueva 6 filas de 546 no quiere decir que el reintento sólo toque el 059, el
090 y el 093. El censo mide las críticas archivadas y los círculos publicados,
y el A/B del 090 enseña el límite de eso. Allí el mínimo nuevo es OTRA
superficie, cuya reserva pasa de inadmisible a admisible con el reintento, y se
mueve un 0,69 % donde el censo predecía un 0,017 %. Una superficie así sólo la
ve una re-corrida, y ésta se hizo en el 090 y el 093. El resto de filas Spencer
y GLE del banco no se ha re-corrido con 0.1.193, y su columna de versión lo
dice.
