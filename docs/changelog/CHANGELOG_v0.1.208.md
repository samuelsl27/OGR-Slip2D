# OGR Slip2D v0.1.208

**Las cuatro fichas que quedaban en P0 de la tanda de 0.1.193 —D186, D187,
D188 y D189— se cierran juntas (decisión del propietario, 2026-09-25), y de la
medida nace una quinta, D192, que se reporta y no se corrige.** Sólo D189 toca
el motor. Una masa que la grieta de tracción ya había truncado recupera su
pared cuando se la devuelven sin ella, y con la pared el empuje del agua.
Pasaba con una masa nombrada y con una poligonal reconstruida desde su
diccionario, que es lo que hace el probabilístico con cada muestra.

Todo lo demás es del banco de verificación, que no está en git. Lo que cambia
en `_tools/`, `referencia.json`, la ficha del 75, el índice de cerrados y
`_auditoria/` va descrito aquí y no aparece en el diff del repositorio.

De las cuatro fichas hubo que corregir la premisa antes de escribir código
(§0), y en tres el alcance real era mayor que el escrito.

---

## 0. Lo que estaba mal en los encargos

### D186: cuatro copias, no tres, y tres cierres que tapaban su propia medida

- El conjunto de veredictos que cierran estaba escrito **cuatro** veces y no
  tres. La del `verificar_cierres.py` de la raíz (manuales 03–07) no tenía
  CUBIERTO POR CODIGO, y su `main()` también sobrescribía el archivo sin guarda.
- `d40` y `d56` llamaban también a `_actual`, así que eran dieciocho y no
  dieciséis.
- `d03`, `d49` y `d50` devolvían PENDIENTE **antes** de juzgar la medida: un
  número malo quedaba tapado por un sello de versión.
- `d91`, `d127`, `d129` y `d98` comparaban el banco VIVO con
  `Evaluaciones/0.1.160` («no autoriza ningún dígito»), que es la clase de
  D187. Pasan a un A/B entre fotos.
- D141 no es una ficha: es `d140` registrada con otra clave en una versión
  intermedia. Las otras catorce huérfanas se escribieron **a mano** en el JSON
  el 2026-08-29 y ningún script las produjo nunca.
- `equivalencia_d175.py` escribía `completo: True` a fuego.

### D187: la misma clase en cuatro cierres que pasaban, y el verificador hacía lo que reprochaba

- Cuatro cierres que **pasaban** eran de la misma clase:
  - `d54` y `d54_52` comparaban el banco vivo con una foto dentro de un margen;
  - `d71` etiquetaba «D134» cualquier cosa que moviera una versión posterior;
  - `d133` fijaba dos recuentos (13 renglones; 9 y 9).

  El propietario los metió en D187: misma clase, mismo número.
- Los medidores que meten el repositorio vivo en `sys.path` eran **cuatro** y
  no tres: también `medir_d72.py`, que carga `d83`. Y el propio
  `verificar_cierres.py` hacía lo mismo, en su cabecera y en `d91`, `d96` y
  `d98`. Un detalle agrava la guarda, que compara cadenas: el motor de este
  equipo llega por el buscador de la instalación editable, que Python consulta
  **después** de `sys.path`. Cualquier árbol que se meta en `sys.path` gana, y
  el que se metía era siempre el vivo.
- **`d69` prometía en su docstring una mitad inversa que nunca comprobó.** Dos
  declaraciones de borde se habían quedado sin aviso que las respaldara. El 048
  `modelo_sin_bulones` dejó de buscar en 0.1.159, y en el 094
  `modelo_sin_conexion` D116 sacó a GLE del borde en 0.1.172.
- **D108 se cerró sobre una ficha que seguía diciendo lo falso.** La foto
  0.1.160 ya llevaba un apartado «El caso 2 (no circular) no se compara» con
  la frase «el manual no publica la geometría de las polilíneas», partida en
  dos renglones. Las dos subcadenas exactas de `d108` no la veían. El
  2026-09-12, `fichas_dw.py` regeneró además la ficha con su plantilla de
  antes de D108: volvió la frase en `notas` y se perdió el apartado no
  circular.
- **D44**: la relación que fija el test del repositorio —la separación
  Bishop–Spencer no crece con la fuerza— **no se cumple** en los muros del
  banco. En el 090 pasa de +0,06 % a −0,53 % y a −1,12 % al doblar la
  capacidad; el 087, el 092 y el 094 se quedan sin factor en algún método.
  Esa relación la prueba el test sobre un soporte puramente normal. En un muro
  con componente tangencial la separación se mueve por otras vías. El criterio
  pasa a ser la **ausencia de la firma** del defecto.
- **D74**: la etiqueta «D134» de sus quince celdas era falsa. Los archivos
  vivos son de 0.1.176 en adelante, ya a tolerancia 1e-4, y lo que los movió
  fue D144…D185, no la tolerancia.

### D188: 48 renglones, no once, por tres causas

Se comparó cada renglón del índice de cerrados con el ERRORES de primer nivel
de la instantánea que cita. De 150 renglones, **48 citas estaban rotas**, más
la segunda instantánea de D74 y de D77, que nunca tuvo la sección. Tres
causas:

1. instantánea → retirar → `instantanea.py --forzar`, que recopia el ERRORES ya
   sin la sección (la causa de la ficha);
2. retirar antes de existir la instantánea que el renglón nombra (D140, D148,
   D153, D156, D157, D159);
3. ediciones a mano.

Diez cerrados no tienen la sección en **ninguna** instantánea, y **73
renglones** citaban como segundo puntero `_auditoria/VERIFICACION_CIERRES.md`,
que nadie escribe desde el 2026-09-05 y no los nombra. La comprobación 10 de
`auditoria_invariantes.py` buscaba además el ERRORES y el PROMPTS de la raíz
dentro del 02, y los daba por desaparecidos en cada instantánea.

### D189: la pared se perdía con desplazamiento CERO

La ficha lo atribuía a extremos publicados 0,001 ft por debajo de la línea de
grieta. La medida (§1) enseñó algo más serio: la masa nombrada perdía el empuje
**aunque sus extremos fueran los exactos de la cuerda**. Y lo mismo una
poligonal reconstruida desde su diccionario. El 002 es métrico: sus extremos
quedan 1,55e-3 y 2,16e-3 **m** por debajo, 30 y 41 veces la tolerancia
geométrica del modelo, y eso no lo absorbe ninguna tolerancia. Se declara
(§5).

---

## 1. D189 — la pared de una grieta sobre su propia línea (motor)

### El mecanismo

Una grieta de tracción trunca la superficie donde la alcanza y cierra la masa
con una pared vertical hasta el terreno (Duncan y Wright 2005, cap. 14). El agua
de la grieta empuja esa pared con ½·γw·h² (Terzaghi 1943). La pared viaja en
el objeto superficie (`tension_crack_wall`), y hay dos caminos que devuelven la
misma masa **sin ese objeto**:

- una **masa nombrada**, con `x_left`/`x_right` puestos por quien llama. Es
  como se pregunta por una masa que no es la crítica;
- una **poligonal reconstruida** desde su diccionario: `to_dict` no lleva la
  pared, y es lo que hace `probabilistic._rebuild_surface` con una crítica
  poligonal en cada muestra.

Las dos llegan con la coronación **sobre** la línea de grieta.
`apply_tension_crack_truncation` lee eso como «fuera de la zona», y es la
lectura que hace idempotente la truncación: una segunda pasada no vuelve a
cortar. La masa conservaba su geometría y perdía el empuje, del lado inseguro.

### La medida, antes de tocar nada

`_tools/pared_grieta_d189.py` en el banco, con resultado en
`_auditoria/D189_grieta/medida_0.1.207.json`. Barre la coronación nombrada
alrededor del cruce, δ/diag ∈ {0, 1e-12, 1e-9, 1e-7, 1e-6, 1e-5, 3e-5, 1e-4}
hacia los dos lados:

| caso | cuerda | nombrada, extensión exacta, sin objeto pared |
|---|---|---|
| talud φ = 0 del test de v1109, Bishop | 0,997822 | 1,071402 |
| mismo talud, Spencer | 0,997750 | 1,071224 |
| 002, Bishop | 1,595632 | 1,672457 |
| 002, Janbu corregido | 1,488622 | 1,608924 |
| poligonal del talud φ = 0, `to_dict`/`from_dict` | 0,974957 | 1,053499 |

En el talud φ = 0 la pared va de la cota 34 a la 40 y el empuje es 176,58 kN/m,
**igual a la forma cerrada**. En el 002, la pared está en x = 53,777 (Bishop) y
50,983 (Janbu), de 31,13 a 35,0, con 73,46 kN/m. Los círculos del
probabilístico **no** perdían nada: se siembran por centro y radio, y la cuerda
vuelve a truncar.

### El arreglo

En `ogr_slip2d/slicer.py`, `apply_tension_crack_truncation`: una coronación
que llega a menos de la tolerancia geométrica del modelo de la línea de grieta
(`_model_grid_tol`, 1e-6 de la diagonal, la longitud por debajo de la cual el
modelo no resuelve su propia geometría) es el final de una masa que la grieta
ya truncó. No se corta otra vez, pero se registra su pared en la coronación,
de la línea al terreno.

- Más abajo que esa tolerancia es otra masa y no recibe nada. La
  discontinuidad del modelo de grieta se queda, pero a la escala del modelo y
  no en cero.
- Una pared no más alta que la tolerancia no es una pared, y no se registra.
- La pared no se duplica en la lista de dibujo si la poligonal ya la traía de
  su diccionario.

Interruptor de módulo `CRACK_WALL_ON_LINE` (encendido), leído en cada llamada,
como los de `interslice.py`. Apagado, el comportamiento es el de 0.1.207. El
docstring de `probabilistic._rebuild_surface` decía que la pared no se deduce
otra vez, y se corrige: ahora sí se deduce, y eso rescata su rama de
poligonales.

Re-medido con el motor nuevo en el mismo proceso:

- la cuerda no se mueve ni un bit;
- la nombrada con la extensión exacta **iguala a la cuerda bit a bit** en los
  cuatro casos;
- la poligonal reconstruida da la de la evaluada (0,974957);
- el barrido pasa de forma continua de 0,99782165 (en el cruce) a 0,99782181
  (1e-7·diag por debajo), y a 1e-6·diag por debajo, ya fuera de la
  tolerancia, sigue sin pared, como antes.

### El A/B del interruptor sobre el banco

`_tools/ab_pared_grieta_d189.py` recorre los 19 modelos con contorno
TENSION_CRACK, de los que 5 tienen agua en la grieta. En el mismo proceso,
encendido, apagado y encendido otra vez como control:

- **80 filas publicadas tal como las evalúa el banco: 0 movidas.**
- 45 con sus extremos publicados nombrados a la fuerza: 0 movidas.
- 80 críticas archivadas: 8 cambian, y en las 8 lo único que cambia es la
  pared. Son las poligonales del 052 `*_path`, con la grieta **seca**: la
  pared vuelve al dibujo y no empuja. Cero dígitos movidos.
- Controles idénticos.

Ninguna fila de la comparativa depende del interruptor. Lo que arregla está en
los caminos que el banco no ejerce: la masa nombrada con su extensión exacta y
la poligonal reconstruida.

### El test

`tests/test_tension_crack_named_mass_v1208.py`, sobre el talud φ = 0 de
`test_tension_crack_truncation_v1109.py`, doce casos:

- la cuerda contra la forma cerrada;
- la masa nombrada sin el objeto pared: misma pared, mismo empuje y mismo
  factor, con Bishop y con Spencer, y no se corta otra vez;
- el borde de la regla: media tolerancia por debajo tiene pared; media por
  encima se trunca a la línea; diez por debajo es otra masa;
- la regla 7: apagado, el factor se mueve del lado inseguro;
- la poligonal por `to_dict`/`from_dict` y por `_rebuild_surface`, y la pared
  dibujada una sola vez.

Comparaciones relativas a 1e-12, nunca `==` sobre doubles.

**Discriminación medida** en un `git worktree` de 0.1.207 con sólo el test
copiado (`_auditoria/D189_grieta/discriminacion_test_v1208_en_0.1.207.txt`):
**fallan 6 de 12**. Cinco fallan por comportamiento (la pared que falta y el
factor que se mueve) y uno porque el interruptor no existe. Los seis que pasan
en los dos árboles son los que deben pasar en ambos: la forma cerrada de la
cuerda, el borde a diez tolerancias, «no se corta otra vez» y la guarda del
dibujo.

---

## 2. D186 — cierres que no dependen de la versión instalada (banco)

- **`_tools/veredictos_cierre.py`** (nuevo) define una sola vez los veredictos
  que cierran —SE SOSTIENE, CUBIERTO POR TEST, CUBIERTO POR CODIGO, CIERRE
  DOCUMENTAL, CUBIERTO POR OTRO— y la fusión con el archivo. Lo importan las
  cuatro herramientas del ciclo; el de la raíz, por ruta.
- Las dieciocho pasan a `_de_cierre(d, "Dnn")`, con su versión de cierre en
  `CIERRE`. Los archivos que leen ya eran de versiones ≥ esa, y releídos
  cumplen su criterio. `d03`, `d49` y `d50` juzgan la medida antes que la
  versión.
- **Una corrida sin argumentos ya no puede bajar un cierre en silencio.** El
  veredicto de cierre archivado que una corrida baja se aparta a
  `_auditoria/verificacion_cierres_degradaciones.json`, se imprime y la salida
  es 1. Solo `--reabrir=Dnn` lo acepta. Lo mismo en el `main()` de la raíz.
- Las catorce claves manuscritas entran en `YA` con su texto letra a letra, y
  D141 se retira con su razón (`RETIRADAS`).
- **`d186()`**: CUBIERTO POR CODIGO, con siete medidas:
  - AST sobre los miembros;
  - doble ejecución, con la versión instalada y con 0.1.999;
  - mutación sin historia;
  - una sola definición de los veredictos;
  - la fusión ejecutada sobre datos sintéticos, contra la vieja;
  - ninguna clave sin productor;
  - la equivalencia archivada.

  La equivalencia, `_tools/equivalencia_d186.py`, compara tres archivos: el
  viejo tal cual, que da PENDIENTE en las dieciséis; el viejo con la puerta
  nueva; y el nuevo. Tienen que coincidir salvo las diferencias declaradas
  antes de medir. Se midió con 0.1.208 (§10).

## 3. D187 — cierres que se sostienen por la razón que dicen (banco)

Diecisiete cierres re-anclados, cada uno con su razón en `REENUNCIADOS_D187`.
La regla es una sola: lo vivo contra una foto pasa a foto contra foto, por
`_historico`, más identidades vivas; un recuento fijado pasa a igualdad de
conjuntos.

| cierre | antes | ahora |
|---|---|---|
| D119 | la rama en λ 1,30 se perdía (D148 la curó) | dos caras: con `BRANCH_CYCLE_RESCUE` apagado se pierde en la pasada 69 de 400; con el motor que se envía converge a 1,750585426 |
| D79 | dígitos del 060 y del 090 fijados | bandera: celda = factor formateado y marca ⇔ `admisible` falso, por las funciones del generador; lo histórico por nombre exacto |
| D94 / D95 | 70/99 y 265/853 números contra 0.1.160 | identidades: el rastro del manejador y el del perfil fallido en ningún resultado; más el A/B entre fotos de lo que sale del perfil |
| D116 / D118 | el primer `if` del AST; el banco vivo contra 0.1.160 | todo `if` que pone `converged = True`; A/B entre la foto 0.1.160 y lo que escribió 0.1.172 (14 761 números, 0 movidos sin declarar); `validas + invalidas == generadas` |
| D117 | exactamente dos llamadas en `states()` | toda llamada a `solve_branch` de `GLESystem` con el presupuesto (hoy tres); la puerta con la recuperación de λ apagada, más la mitad de serie; A/B 0.1.172 → 0.1.173 |
| D44 | dos separaciones fijadas | ninguna separación Bishop–Spencer llega al 7 %, la mitad del 14 % mínimo del defecto (hoy, 1,96 % como máximo) |
| D82 / D83 | filas de 13 celdas; dígitos de 0.1.159/0.1.160 | la fila se construye y se lee con `filas_md`, la función que la escribe (15 celdas); los dígitos del cierre, contra las fotos 0.1.158 y 0.1.159 |
| D69 | sólo «todo aviso declarado» | y además «toda declaración respaldada por un aviso»: se declaran los tres bordes `y_min` que avisaban sin declarar (091 Spencer ×2 desde 0.1.176, 093 `modelo_sin_conexion` desde 0.1.178) y se retiran los dos caducados (048, 094) |
| D108 | dos subcadenas exactas en la ficha | la frase buscada normalizada y en presente, en la ficha y en las dos plantillas que la escribían, más la marca positiva (fig. 7.29, y = 0,52) |
| D74 | la columna viva contra la foto de D69, etiquetada «D134» | identidad: el círculo publicado de los 16 modelos evalúa igual, bit a bit, con y sin los límites de talud y el suelo que D74 declaró |
| D54 | el paso A contra el banco vivo al 0,2 % | el paso A contra lo que escribió 0.1.160, en su foto |
| D54(52) | la foto 0.1.127 contra el banco vivo al 0,5 % | foto contra foto (0.1.127 20×20 → 0.1.146 30×30, cifra a cifra), con la prueba de que las fotos están a los dos lados del cambio: las generadas crecen como (31/21)² |
| D71 | la corrida 0.1.147 contra el 101 vivo | 0.1.147 → foto 0.1.159, identidad; 0.1.159 → 0.1.160, el paso de D134 y sólo ahí la etiqueta |
| D133 | 13 renglones; 9 y 9 | tabla = carpeta; archivos en 0.1.97 = declarados en 0.1.97 |

Además:

- **La comparativa tiene función de fila.** `generar_comparativa.py` gana
  `COLUMNAS` y `filas_md`, y la comparativa regenerada sale byte a byte igual.
  La comprobación 9 de `auditoria_invariantes.py` construye la fila con la
  misma función.
- **`_tools/ruta_motor.py`** (nuevo) es la única regla que pone el motor al
  alcance: nada si `ogr_slip2d` ya está importado o se puede importar. La usan
  los cuatro medidores, la cabecera del verificador y `d91`, `d96` y `d98`. Se
  midió en un proceso con otro árbol delante y el repositorio escrito `c:/…`:
  - los medidores viejos metían el repositorio y medían 0.1.207;
  - los nuevos no cambian `sys.path` y usan el árbol elegido.
- **La ficha del 75** se reparó a mano, sin relanzar `fichas_dw.py`, que
  reescribe claves de `referencia.json`:
  - la sección falsa y la línea de notas pasan a lo que produciría la
    plantilla corregida;
  - el apartado no circular sale de la propia `fichas_no_circular.seccion`,
    con los datos de hoy.

  Se corrigieron también las plantillas de `fichas_dw.py` y
  `sanear_notas_no_circular.py`. La sustitución de esta última repetía la
  frase falsa con otras palabras, y la asunción y = 7 que D108 retiró.
- **`d187()`**: CUBIERTO POR CODIGO, con cuatro medidas:
  - (a) los diecisiete dan veredicto de cierre, iguales con la versión
    instalada y con 0.1.999;
  - (b) AST: ninguna de las 8 constantes-foto retiradas vuelve; 36 funciones
    sin lecturas de `Evaluaciones/` por fuera de `_historico`; ningún miembro
    llama a `_actual`;
  - (c) los medidores en otro árbol;
  - (d) **16 mutaciones en memoria, todas vistas por su criterio** y ninguna
    por reventar: el `if` viejo de D116, una llamada sin presupuesto, `_actual`
    de vuelta, filas de 13 celdas, un borde sin declarar y una declaración sin
    aviso, la frase falsa partida en dos renglones, un límite de talud que
    mueve el círculo en 1e-12, un huérfano sin declarar, el rastro del
    manejador, el del perfil, una separación del 10 %, el rescate de ciclo
    apagado… Además, sin historia no cierra ninguna de las trece que leen
    fotos.

## 4. D188 — cada renglón apunta a donde está su historia (banco)

- **`retirar_cerrados.py --escribir`**:
  - exige la instantánea de la versión instalada del banco de la ficha (el 02,
    o la raíz si su veredicto sale del JSON de la raíz); sin ella no escribe
    nada y sale con 2;
  - **antes** de borrar, añade cada sección íntegra a
    `Evaluaciones/<v>/ERRORES_Y_DISCREPANCIAS_retiradas.md`. Sólo añade, y un
    `--forzar` de la instantánea no lo toca;
  - cita esa instantánea y, como segundo puntero,
    `_auditoria/verificacion_cierres.json`.
- **Comprobación 17** de `auditoria_invariantes.py`, «punteros del índice»:
  - ERROR por cada cita `Evaluaciones/<X>` cuyo ERRORES de primer nivel no
    tenga la sección. Buscar más hondo sería trampa: cada instantánea desde
    0.1.159 arrastra copias viejas en `_auditoria/`;
  - AVISO por un segundo puntero muerto;
  - INFO con los renglones sin versión.
- **Comprobación 10**: el ERRORES y el PROMPTS de la raíz se buscan en la raíz,
  y los `_antes_de_retirar.md` y `_retiradas.md`, que se añaden a propósito, no
  cuentan como separación.
- **El índice**, reescrito sin tocar su formato (85 renglones):
  - 49 repuntados a la instantánea que sí tiene la sección, la última que la
    tuvo;
  - los diez sin sección en ninguna, a donde vive su historia:
    `HALLAZGOS_0.1.147.md`, `HALLAZGOS_0.1.159.md`, la copia anidada del 133,
    la decisión de tolerancia, `d136()`, `d140()` y el changelog de 0.1.176,
    y `d181()` con el §5 del changelog de 0.1.192;
  - D74 y D77 con su segunda instantánea en prosa;
  - los 73 segundos punteros muertos, al JSON.

  Queda: 96 citas con su sección, 0 rotas.
- **`d188()`**: CUBIERTO POR CODIGO, con cuatro medidas:
  - la 17 sobre el índice vivo, sin ERROR ni AVISO;
  - la 17 sobre una copia con D49 roto a propósito, que da ERROR y lo nombra;
  - `retirar_cerrados` sobre un árbol temporal: sin instantánea se niega; con
    ella guarda la sección antes de quitarla y cita la instantánea y el JSON;
  - la 10, que lee la raíz.

  Contra el `retirar_cerrados.py` viejo falla dos veces: sin instantánea
  revienta (salida 1), y con ella borra la sección sin guardarla.

## 5. D189 — la puerta única, los generadores y las entradas (banco)

- **Una sola puerta.** `ejecutar_caso.superficie_publicada(s)` lee la entrada,
  construye la superficie y, sólo con opt-in, le pone los extremos que nombra.
  El bucle del banco pasa por ella: 163 parejas (problema, modelo) comparadas
  contra el `ejecutar_caso.py` de la copia de seguridad, **0 distintas**,
  incluido el opt-in del 059.
  - Pasan por la puerta once herramientas que re-evalúan círculos publicados.
    `curva_lambda` ya honraba la masa nombrada y se unifica.
  - Sólo siete archivos llaman a `normalizar_superficie`, cada uno con su
    razón escrita (`NORMALIZAN_D189`).
  - `generico.circulo_de_referencia`, que devuelve un diccionario sin
    extremos, revienta ante un opt-in en vez de ignorarlo.
  - Los cierres que importan los medidores tocados (D113, D145, D146, D147,
    D148, D149, D152, D153, D156, D185) dan **el mismo detalle** que en la
    línea base de 0.1.207.
- **`clasificar_d37.py`**:
  - sobre el 59 da C2-inadmisible, no C5;
  - una C5 tiene que reproducir su `f_pub` archivado al mismo 0,2 % que define
    la fila, o sale `no-reproduce`;
  - `--problemas` escribe `D37_CAUSAS_parcial.md` en vez de pisar el informe
    del banco entero;
  - su docstring decía que `evaluate_circle` muta el círculo. Eso no pasa
    desde v0.1.131, y se volvió a medir en 0.1.207 sobre el 22.
- **Los siete generadores de fichas.** `ficha_simple.py` gana
  `fusionar_anomalias` y `fusionar_superficie`, y `escribir()` acepta `raiz=` y
  fusiona las superficies que recibe.
  - `ficha_59`, `ficha_85` y `fichas_79_81` dejan de correr al importarse.
  - Las anomalías se fusionan por id y las superficies por entrada.
  - `ogr` y `publicado` conservan lo que la ficha no escribe; en el 85 eran
    `reserva`, `no_circular_*` y la procedencia.
  - `escribir_no_reproducibles` deja de reescribir el archivo desde cero.
  - Todos aceptan `--carpeta`.
  - Los cuatro cuya fuente es `resultados_todos.json` de 0.1.160 (059, 085,
    079/081, 086), más vieja que su resultado canónico, **se niegan a escribir
    sin `--forzar`**.
  - `fichas_79_81` ya no crea un `resultados.json` de plantilla donde el
    canónico es otro.
- **Las entradas.** `masa_nombrada: false`, con su razón y su distancia, en 002
  Bishop y Janbu, 013, 042, 077 y 081 `caso2_spencer`. `false` equivale a
  ausente y ninguna cambia un bit. Se leyeron las figuras:
  - la 81.3 dibuja la misma lente que la cuerda; el círculo es casi tangente y
    el radio redondeado mueve los cortes 0,074 ft;
  - la 13.3 dibuja la misma masa, con el desfase de −0,5 de los paneles que ya
    documentó P013-VAL2;
  - en el 042 el `izq` es el fondo de la grieta;
  - en el 077 la cara del modelo no es exactamente la del manual.
- **`censo_extremos_d147.py`** gana, por fila, la tolerancia de su modelo, la
  pared y el empuje de las dos masas y la declaración de la entrada. Gana
  también dos recuentos que `d189()` exige vacíos:
  `INCOHERENTES_CON_LA_TOLERANCIA` y `SIN_FACTOR_SIN_DECLARAR`.
- **`d189()`**: CUBIERTO POR TEST, con seis medidas:
  - el test y su discriminación;
  - el censo re-corrido;
  - el A/B del interruptor;
  - la puerta, por AST y ejecutada;
  - los siete generadores sobre una copia del banco: A59-2 con su
    `cerrada_en`, el opt-in del 59, el `cerrada_en` de A85-1, A79-1 y las dos
    `caso2_spencer`; el banco vivo, intacto;
  - `clasificar_d37` sobre el 59.

---

## 6. Lo que se reporta y NO se corrige (regla 6)

- **D192** (P0, nace aquí; siguiente libre D193). La encontró el A/B del
  interruptor, en su familia de críticas archivadas.
  - Las poligonales críticas se archivan con **cuatro decimales**.
    `039/resultados_no_circular_arcilla.json` tiene la grieta llena, y su
    coronación queda 4,4e-5 m por debajo de la línea, **1,4 veces** la
    tolerancia del modelo (su diagonal es de sólo 31,3 m).
  - Re-evaluada desde el archivo no recibe pared ni empuje, ni con el motor de
    0.1.207 ni con el de 0.1.208: GLE da 1,0334 frente a 1,01262 (+2,05 %) y
    Spencer 1,0202 frente a 0,993957 (+2,64 %), del lado inseguro.
  - Es el mecanismo que D189 arregla, pero la causa es la precisión del
    archivo. Ensanchar la tolerancia del motor para absorberla sería tapar el
    dato: el 002 ya enseñó que un redondeo de datos no lo absorbe ninguna
    tolerancia del modelo.
  - Prompt largo en `_auditoria/doc/prompts_largos/D192.md`. Depende de D189
    (`REQUIERE`).
- **Tres filas declaradas del 075 que el A/B de D116/D118 no puede ver.** Son
  `circulo_publicado/*` de `resultados_todos.json`, un archivo que 0.1.172 no
  reescribió. La primera versión del A/B entre fotos las daba por «ya no
  difieren»; ahora se dicen aparte como fuera del A/B. No es un defecto: es la
  consecuencia de comparar sólo lo que escribió la versión de cierre.

## 7. El banco: qué se re-corre y por qué

- **Ningún `resultados*.json` se re-corre ni cambia.** Las cuatro fichas son de
  herramientas y declaraciones. La mitad de motor de D189 no mueve ninguna fila
  de la comparativa, y el A/B del interruptor lo demuestra sobre los 19
  modelos con grieta.
- Se re-corren sólo medidas:
  - el censo de D147, completo con 0.1.208;
  - el A/B del interruptor;
  - la equivalencia de D186;
  - la comparación clave a clave de todos los cierres, en seco, contra la línea
    base de 0.1.207 (`_auditoria/P0_tanda/antes_seco_0.1.207.json`).

## 8. Errores propios detectados antes de publicar

- La mutación «`_actual` de vuelta» de `d187` leía `__version__` y llamaba a
  `_actual` dentro de una función de `CIERRE`, y la regla AST de `d175` la
  tumbó, con razón. Pasa a un ayudante con nombre propio,
  `_actual_de_vuelta`, exceptuado por escrito como `_doble_ejecucion`.
- La primera versión de las mutaciones contaba como «vista» una que hacía
  reventar el cierre. Una caída no demuestra que el criterio juzgue lo mutado;
  ahora un REVIENTA cuenta como ciega.
- **La comparación clave a clave con la versión ya subida encontró una bajada:
  D175.** `d188` y su árbol temporal leían `ogr_slip2d.__version__` para saber
  qué instantánea espera `retirar_cerrados.py`, y la regla AST de D175 los
  tumbó, con razón. Se me había pasado por no volver a pasar `d175` después de
  escribir `d188`. Ahora le preguntan la versión a la propia herramienta
  (`retirar_cerrados._version_ogr`), que es quien la decide, y D175 vuelve a
  cerrar. Es la razón de esa comparación: un cierre puede caer por un cambio
  que no toca su ficha.
- El A/B entre fotos de D116/D118 daba un AVISO falso (§6).
- `pared_grieta_d189.py` habría sobrescrito su línea base
  (`medida_0.1.207.json`) con la medida del motor nuevo, porque la versión
  instalada seguía siendo 0.1.207. Ahora no pisa una medida existente sin
  `--forzar` y acepta `--salida=`.
- Al fusionar `ogr` y `publicado` en `ficha_85` y `fichas_refuerzo`, volvían
  las claves planas por método que deja `escribir()`, y que la sustitución
  completa quitaba sin decirlo. Se filtran como ya hacía `ficha_59`.
- La primera versión de `d74` no existía como identidad: comparaba contra una
  foto. La de `d69` declaraba los tres bordes y no miraba la mitad inversa, que
  luego encontró los dos caducados.
- `d94`: la frase del manejador está partida en dos literales adyacentes y la
  búsqueda por texto no la veía; se busca por AST. Además, un primer alcance
  lo dejaba PENDIENTE por los `resultados_todos.json` del 059 y el 060, y se
  restauró el de siempre.
- `d79`: las banderas falsas del GLE del 085 no llevan número, y la foto
  0.1.160 no tiene banderas. La mitad histórica pasó a comprobar el registro
  del censo de cierre.
- `d117` (3): con el motor que se envía la puerta ya no dispara. Se re-enunció
  como su test, con la recuperación de λ apagada, y la mitad de serie aparte.
- Dos guiones de cirugía fallaron por la barra doble que el shell entrega
  simple, y uno por un `%` sin escapar. Los tres fallaron antes de escribir
  nada, y se rehicieron como archivos.

## 9. Los tests

- Nuevo: `tests/test_tension_crack_named_mass_v1208.py`, 12 casos (§1). Falla
  6 de 12 en un worktree de 0.1.207.
- Los 54 tests de grieta de tracción (`test_tension_crack*`) en verde con el
  motor nuevo.

## 10. Verificación

- **Suite entera, sin argumentos y sola en la máquina: 4569 de 4569 en
  verde**, en unos 37 minutos (12:14–12:51). Incluye
  `test_version_consistency_v176.py` con los nueve sitios en 0.1.208, y el
  diálogo Acerca de lee la versión de los metadatos, no de un literal.
- **El test nuevo**: 12 de 12 con el motor nuevo; 6 de 12 fallan en el
  worktree de 0.1.207 (§1).
- **A/B del interruptor**
  (`_auditoria/D189_grieta/ab_interruptor_0.1.208.json`, medido sobre el
  repositorio, completo): 0 de 80 publicados y 0 de 45 nombrados movidos. De
  80 críticas, 8 cambian sólo en la pared dibujada. Controles idénticos.
- **Censo de D147, re-corrido entero con 0.1.208**
  (`_auditoria/D147_extremos/censo_0.1.208.json`, huella del motor
  `62f696d4dca8e2c8`):
  - 139 parejas en 94 entradas de 40 problemas. Ninguna es incoherente con la
    tolerancia de su modelo, y la única sin factor (`081:caso2_spencer`) está
    declarada. Queda sin medir la entrada del 099: ningún archivo de resultados
    utilizable evalúa ese problema.
  - Su mitad A/B, sin la puerta y con ella, mismo motor y mismo proceso: 555 de
    557 superficies iguales. Las dos distintas son las del 059 con opt-in
    (`circulo_publicado_figura_59_2` y `spencer`), lo único que la puerta debe
    mover.
- **Equivalencia de D186**
  (`_auditoria/D186_cierres/equivalencia_0.1.208.json`): el
  `verificar_cierres.py` de 0.1.207 da PENDIENTE en las 16. Con la puerta
  nueva, de los 18 miembros (las 16 más `d40` y `d56`), 12 salen iguales y 6
  con diferencias declaradas antes de medir. Ninguna diferencia sin declarar,
  ninguna declarada que no difiera.
- **La prueba real de D186**: todos los cierres en seco con 0.1.208, clave a
  clave contra la línea base de 0.1.207
  (`_auditoria/P0_tanda/antes_seco_0.1.207.json`):
  - 109 con el mismo veredicto;
  - 29 suben a cierre: las 16 de D186 y las 13 de D187;
  - 18 claves nuevas: las 14 manuscritas y D186–D189;
  - ninguna desaparece y **ninguna baja**. La primera pasada bajó D175 (§8);
    ésta es la de después del arreglo.
- **Veredictos escritos**: 156 en el JSON del 02, con 0 bajadas apartadas en
  `verificacion_cierres_degradaciones.json`. Contra el JSON acumulado de la
  instantánea 0.1.207:
  - entran D186–D189 y sale D141 (§2);
  - pasan a cierre tres claves que se guardaban sin él: D79 (NO SE SOSTIENE),
    D94 y D98 (PENDIENTE DE CORRIDA);
  - ninguna baja.

  El JSON de la raíz: 8 comprobaciones con los mismos veredictos que antes.
  Cierra D121.
- **Instantánea `Evaluaciones/0.1.208`**: 1746 archivos copiados y verificados
  byte a byte. `retirar_cerrados.py --escribir` guardó las secciones de
  D186–D189 en `ERRORES_Y_DISCREPANCIAS_retiradas.md` antes de quitarlas del
  archivo vivo, y el `--forzar` posterior las conservó. Es el primer uso del
  mecanismo de D188.
- **Auditoría de invariantes, 0 ERROR en los dos bancos.**
  - 02: 486 AVISO y 258 INFO, frente a 488 y 255 en la instantánea 0.1.207.
    Se van dos AVISO: el borde del Spencer del 091, ya declarado (D69), y la
    instantánea separada del estado vivo. No entra ninguno.
  - Raíz: 62 AVISO. Son 55 archivos medidos con versiones anteriores y 7
    fichas sin prompt largo.
  - La comprobación 17, nueva, encuentra 100 citas del índice con su sección
    en la instantánea que nombran y 57 renglones sin versión. La 10 dice que
    la instantánea coincide con el estado vivo en los 1745 archivos que
    compara.
- **`generar_prompts.py`**: 48 prompts; P0 queda D137 → D138 → D139 → D192.
  Sale con 1 porque faltan nueve prompts largos (D137, D138, D139, D142, D143,
  D150, D151, D168 y D169), todos de antes de esta tanda.
