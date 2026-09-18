# OGR Slip2D v0.1.177

**El ancla de 120 kN/m no destruye la raíz de λ del plano de 50°: la desplaza hasta un λ donde la rama de MOMENTOS deja de ser resoluble. Con el ancla Pasiva y Spencer la raíz está en λ = 1,31988 y allí F = 1,748304, que es la forma cerrada de la cuña a 8e-6, mientras la reserva publica 1,765482 (+0,98 %).** Ninguna ruta de cálculo cambia: esta versión mide, escribe la explicación donde la ficha la pedía, y deja el defecto reportado sin corregir. Ficha D119 del banco, prompt P-D119, paquete P2.

---

## 1. El encargo y lo que la medición contestó

D119 era una **pregunta sin contestar** que v0.1.159 §8 dejó abierta: que el plano de 50° con ancla no tenga horquilla de λ estaba medido; *por qué* ese plano y no los de 35°, 40° y 45°, no. El prompt pedía tabular `F_f(λ)` y `F_m(λ)` para β ∈ {35, 40, 45, 50} × {sin ancla, Activa, Pasiva} en λ ∈ [−2, +3], leer las curvas antes de teorizar, y ofrecía tres lecturas: que las ramas se corten fuera del rango, que sean paralelas, o que la rama de momentos muera antes de llegar.

Las curvas están en **`docs/audits/anchored_wedge_lambda_v1177.md`** (16 celdas: las doce de la ficha con Spencer, más las cuatro de GLE donde vive el hallazgo; 101 λ por celda, con los nodos de la rejilla del motor unidos al barrido para que la tabla y lo que el solver muestrea se puedan comparar —en este rango los catorce de la forma y los tres de la extensión caen todos en múltiplos de 0,05, así que la unión no añade ninguno, y el medidor la hace igual porque el rango es un argumento). **Las tres lecturas del prompt caen**, y la tercera es la que más se acerca sin ser lo que dice:

- **No es el telescopado.** El prompt proponía que el término `t_mob·cos a` del refuerzo, que no se telescopa, rompiera la constancia de `F_f`. Es cierto del empuje `e` y falso de la rama: `F_f` sale del balance GLOBAL, donde los cortantes interdovela se cancelan por parejas y los dos términos de refuerzo (`den -= Σ t_active·sec a`, `num += Σ t_passive·sec a`) no dependen de λ. Medido: `F_f` es constante en λ con ancla y sin ella, con dispersión de **1e-14 a 1e-11** sobre el barrido entero, y reproduce la forma cerrada con un error de **7,3e-11 en la peor de las dieciséis celdas**.
- **No son paralelas.** `F_m` se acerca a `F_f` monótonamente: la Pasiva de 50° va de g = −0,0443 en λ = 0,90 a **−0,0051 en λ = 1,275**.
- **No hay raíz fuera del rango: hay raíz, y está justo detrás de donde la rama se pierde.** La rama de momentos de serie converge hasta λ = 1,275 y devuelve `None` desde λ = 1,30.

## 2. El mecanismo, y por qué ningún cerrojo de los que hay lo ve

La iteración amortiguada `F ← 0,5·(F + f_new)` de la rama de momentos deja de ser la contracción monótona que es sin refuerzo —razón +0,89 en la raíz del plano desnudo, la misma familia que v0.1.159 §1 tabuló— y pasa a un **ciclo de período 2 cuya amplitud crece**. La órbita se sale de la región donde F es finito y positivo y `solve_branch` devuelve `None` en la **pasada 69 de 400** (λ = 1,30 Pasiva; 51 en 1,32; 37 en 1,35; y en la Activa 39 en λ = 1,00, 19 en 1,05, 7 en 1,30).

**69 es el número entero de esta versión**: `STALL_PATIENCE` es 80, y el rescate de Wegstein de v0.1.176 entra en la pasada *siguiente* a esa puerta. La rama se ha ido antes de que exista el mecanismo que la salvaría — y por la misma razón bajar `RESCUE_OMEGA_MIN` no cambia nada, medido. Adelantar la puerta (`patience` es **argumento** de `solve_branch`, no una constante: 25 a 50 según el λ) y el MISMO solver converge en 1,28–1,36, con g cambiando de signo en λ = 1,31988. De una a quince combinaciones de puerta y arranque convergen según el λ —quince en 1,28, cuatro en 1,32, una sola en 1,35—, y **todas las que convergen dan el mismo punto fijo**, con dispersión de 2,1e-10 en el peor caso: ese es el control de que lo alcanzado es un punto fijo y no donde una iteración se paró. Que la ventana se estreche según se acerca el cruce es en sí una medida.

Que la raíz recuperada **tenga que ser** la forma cerrada es lo que la vuelve una raíz y no una coincidencia: sobre un plano la masa es una cuña rígida, todo método que cierra equilibrio global de fuerzas debe el mismo número, y `F_f` es esa constante. Medido: 8e-6.

## 3. Por qué ese plano y no los otros, que es lo que la ficha preguntaba

Porque el ancla mueve el cruce **hacia arriba** en λ —sube `F_f` mucho más de lo que sube `F_m` a un λ dado, así que `F_m` tiene que bajar más para encontrarlo— mientras mueve el último λ resoluble **hacia abajo**. A 35°, 40° y 45° el cruce sigue cayendo dentro; a 50° cae fuera: el cruce está en 1,3199 y el solver de serie pierde la rama entre 1,275, que todavía resuelve, y 1,30, que ya no. No hay nada especial del ancla a 50° salvo que ahí es donde esas dos curvas se cruzan entre sí.

Y el resumen de las dieciséis celdas dice algo que la ficha no esperaba: **son tres mecanismos, no uno**. Seis celdas salen por la reserva:

| celdas | qué pasa |
|---|---|
| las **cuatro** de 50° con ancla (Spencer y GLE × Activa y Pasiva) | hay cruce y cae fuera del tramo usable: la rama de momentos se pierde antes. La raíz solo se alcanza en la Pasiva de Spencer; en las otras tres el escape llega antes del cruce incluso con la puerta más temprana |
| **45° Pasiva con Spencer** | `g` conserva UN solo signo en todo el tramo usable y se acerca a cero tan despacio que nada cruza en el rango buscado: aquí la lectura de 0.1.159 es la correcta |
| **45° Pasiva con GLE** | el cruce está y las dos ramas convergen a los dos lados (λ = 0,1 con g = +5,64e-4 y λ = 0,2 con g = −6,14e-5), pero los λ de un lado son inadmisibles y el muestreo estricto los borra; el re-muestreo relajado solo se dispara cuando no sobrevive NINGUNA muestra. Ficha nueva D149 |

En las diez restantes la raíz cae dentro del tramo usable y el motor la refina.

## 4. Lo que la ficha y el prompt daban por sentado, y la medición desmiente

- **«Está fijado en `TestTheFallbackSaysWhatItIsWithoutVetoingIt` (301-370; el caso anclado en 326-327)»**: falso por partida triple. Esa clase vive en `tests/test_interslice_budget_v1159.py:333`, usa `BETA = 45.0` y fija la reserva del plano de **45°** Pasiva (residuo 1,2e-3); las líneas 326-327 caen en otra clase. La que fija este hallazgo es `TestAWedgeWithNoRootSaysSo`, y está en **`tests/test_janbu_wedge_v1142.py:556`**, que es otro archivo. Es esa la «cabecera del test que lo fija» del criterio de cierre, y es la que esta versión re-ancla.
- **Las citas de línea del motor están caducadas**: `interslice.py:392-403` es hoy el final del docstring de `branch_budget` y `432-448` son campos de `SliceRow`; el término de refuerzo vive en **763-784** (`t_mob`, `n_i`, el empuje) y **852-855** (balance global), y `branches()` está en **1229** y no en 707. Por eso nada de este trabajo se localiza por número de línea y todo por nombre de símbolo.
- **El residuo «0,03 a 0,20 que no encoge» SÍ se sostiene**, y se vuelve a medir: 0,1929 → 0,1918 (Activa) y 0,03433 → 0,03433 (Pasiva) entre tolerancia 5e-3 y 1e-10. Lo que era falso no era el número: era la conclusión que se le colgó.
- **El ayudante que el prompt manda copiar mide otro sistema.** `_system()` de v1159 construye `GLESystem(..., sup=None, ...)`, de modo que el refuerzo llega a la rama de fuerzas (por `SliceRow.t_active/t_passive`, que `prepare_rows` rellena desde las dovelas) y **no** al cierre de momentos, que lo recibe por ese argumento. Medir la cuña anclada por ahí habría dado un `F_m` sin ancla contra un `F_f` con ella. El medidor y el test construyen el sistema como lo construye `spencer.py`.
- **El criterio de cierre pedía el archivo de curvas «en `_auditoria/` o `docs/`»**: va en `docs/audits/`, porque la fixture es del repositorio y no hay `.ogr` del banco que la represente, y porque `_tools/curva_lambda.py` —el medidor de curvas de D125— solo sabe medir **círculos**.

## 5. Lo que salió mal por el camino, que es lo que merece recordarse

Ocho errores propios, detectados antes de publicar. Los dos primeros son los que habrían hecho falsa la conclusión:

1. **La primera hipótesis era que la cota `RESCUE_OMEGA_MIN` = 0,1 estaba en medio**: la ω de Wegstein es `1/(1−s)` y un *flip* con pendiente s < −9 pide una ω por debajo del suelo. Encajaba, y es **falsa**: la rama muere en la pasada 69 y el rescate entra en la 81, así que nunca llega a elegir ω. Medido bajando el suelo a 1e-6: no cambia nada. Leer el código habría bastado para sospecharlo y no bastó; lo destapó medir en qué pasada muere.
2. **La ruta de disparo para hallar el punto fijo repulsivo —bisecar `Φ_k(F0) = F_k(F0) − F0`— no mide lo que parece**, y su propio control la tumbó: con k par la bisección cae en el **ciclo de período 2** (un punto de período 2 cumple `F_k(F0) = F0` con k par), y con k impar arrastra el sesgo de arrancar con `X = 0`, porque el estado de `solve_branch` es el par `(F, X)` y no `F` —la misma razón por la que D115 no se pudo cablear—. Contra el motor daba 1,7556 donde el motor da 1,7617. Descartada, y sustituida por la puerta adelantada, que no reimplementa nada.
3. `/tmp` **otra vez**: un archivo escrito con un heredoc de Bash a `/tmp` (que en Git Bash es `AppData/Local/Temp`) no existe para el Python de Windows. Es el error que v0.1.175 dejó documentado y que volvió a costar un intento.
4. Los tramos donde buscar el punto fijo perdido estaban indexados por `(β, ancla)` **sin el método**, y GLE cruza más arriba que Spencer sobre la misma cuña (su raíz sin ancla está en 1,43 contra 1,19): el barrido de GLE medía donde no había nada y publicaba cuarenta filas vacías.
5. El primer resumen del documento afirmaba que las celdas de reserva eran **tres** y que en las tres la raíz caía fuera del tramo usable. Eran **seis** y **tres mecanismos distintos**; lo destapó leer la tabla que yo mismo acababa de generar.
6. Un caso del test exigía que el residuo se moviera menos del 0,1 % con la tolerancia y la medida es 0,55 %: la aserción era más estrecha que el hecho, que es cómo un test verde se convierte en uno que miente cuando cambie el ruido.
7. Otro caso barría λ = 1,5 en las tres celdas y ahí la rama de **fuerzas** de la Activa está cortada por la cota de empuje de D118 — un límite distinto del que la clase mide.
8. `_fixed_point` arrancaba siempre en F = 1,0, y en λ = 1,32 solo llega el arranque cercano a la cuña: la ventana se estrecha según se acerca el cruce, que es en sí una medición y por eso ningún caso depende ya de una sola combinación.

## 6. Los tests, y la cabecera que la ficha nombraba

**`tests/test_anchored_wedge_root_v1177.py`**, 19 casos en seis clases. Ninguna aserción fija un factor de seguridad: lo que se compara es contra la forma cerrada de la cuña calculada en el propio archivo (Coulomb 1776; Duncan y Wright 2005 §6), contra identidades (`F_f` no se mueve con λ) y contra signos. El sufijo es `_v1177` y no el `_v1160` que pedía el criterio porque `_vNNNN` es la versión en que **aterriza**.

Nada de este trabajo toca el motor, así que **este archivo no discrimina contra el árbol de 0.1.176: los 19 pasan también allí**, y decirlo importa más que disimularlo. Lo que sí hace es dejar de ser cierto en cuanto alguien arregle D148: si la puerta del rescate baja de 69, `test_and_it_gives_up_before_the_rescue_could_see_it` falla, que es exactamente el trabajo de un tripwire — obligar a que el arreglo sea deliberado y venga con su propia medición. Los controles de `TestTheFixtureStillDiscriminates` existen por el motivo contrario: casi todo lo que este archivo afirma es sobre una búsqueda que **no** encuentra, y una fixture rota lo haría verde sin trabajo.

**`TestAWedgeWithNoRootSaysSo` pasa a llamarse `TestAWedgeWhoseRootTheSolverCannotReachSaysSo`** en `tests/test_janbu_wedge_v1142.py`, y la cabecera —que es la que el criterio de cierre de D119 nombra— se re-ancla con la explicación medida. **Ni una aserción se movió**, y eso es el argumento: lo que la clase afirma (no hay horquilla, el residuo es 0,03–0,20, no encoge con la tolerancia) sigue siendo verdad entera; lo que era falso era la RAZÓN escrita al lado, «there is no root to converge to». Corregir el nombre cambia **qué defecto** son esas dos filas, no si lo son. Un nombre que afirma lo contrario de lo medido es peor que no tener nombre, y este proyecto ya pagó esa lección en v0.1.173 con un rótulo de diálogo.

## 7. Lo que se reporta y NO se corrige (regla 6)

El prompt dice que no autoriza tocar `solve_branch`, y no se toca. Último defecto del banco antes de esta versión: **D147**. Salen dos:

- **D148 — la rama de momentos con refuerzo se sale de la región admisible en la pasada 69, antes de que el rescate pueda verla, y con ella se pierde una raíz que existe.** Todo lo de las secciones 2 y 3, con una consecuencia que merece su propia línea: **esa salida no tiene contador**. `GLESystem.branches` cuenta los tres motivos tras `if state is None or state.converged: continue`, así que un `None` no incrementa ninguno. Medido sobre los 21 nodos de la rejilla en la celda Activa: 11 λ con la rama de momentos nula y 9 con la de fuerzas desbordada, mientras el resultado publica `lambdas_lost_to_stall = 0`, `lambdas_lost_to_budget = 0` y `lambdas_lost_to_thrust_overflow = 8` — y esos ocho son de la rama de **fuerzas** en λ ≤ −1,5 y λ ≥ 1,5, ninguno en el tramo donde está la raíz. El diagnóstico que v0.1.159, v0.1.171 y v0.1.176 construyeron señala aquí a otro sitio.
- **D149 — el muestreo estricto puede borrar UN lado de una horquilla, y el re-muestreo relajado solo se dispara cuando no sobrevive NINGUNA muestra** (`if not samples and system.n_thrust_rejected:`). Medido en la celda GLE de 45° Pasiva, donde el cambio de signo cae exactamente en el borde de admisibilidad. El daño ahí es de 2,4e-5 y eso es una propiedad de la fixture, no del mecanismo: lo que el mecanismo hace es convertir una horquilla que existe en una reserva silenciosa, justamente en los modelos con soporte.

Y dos observaciones que no abren ficha: `patience` gobierna **dos** cosas distintas dentro de `solve_branch` —cuándo entra el rescate y cuándo corta el estancamiento—, lo que hace que adelantar una obligue a adelantar la otra y es parte de por qué D148 no tiene arreglo barato; y el medidor nuevo del banco es el tercero de su familia (`curva_lambda.py` para círculos, `recorrer_lambda_v1106.py`, y ahora `curva_cuna_d119.py` para la cuña), sin que ninguno pueda hacer el trabajo de los otros dos.

## 8. El banco

**No se re-corre, y es una identidad y no una medición**: los únicos cambios del repositorio son un archivo de test nuevo, un docstring, un documento de auditoría y los siete números de versión. Ninguna ruta de cálculo cambia, así que el cero de dígitos movidos no necesita corrida que lo demuestre.

- `_tools/curva_cuna_d119.py`: medidor nuevo, **solo de medida** —no escribe ningún `.ogr` ni ningún `resultados*.json`—, que construye la fixture del repositorio en código (los módulos de `tests/` no se importan fuera del runner) y regenera entero `docs/audits/anchored_wedge_lambda_v1177.md`.
- `d119()` en `_tools/verificar_cierres.py`, con el molde de cuatro medidas de `d125()`: el test por `_cubierto`, la cabecera **por AST** (un `grep` no distingue una cabecera de una mención en otro docstring, y aquí la mención existe: la cabecera nueva cita el nombre viejo para explicar el cambio), la raíz **ejecutándola** por el medidor, y el archivo de curvas de la versión instalada. Da **CUBIERTO POR TEST**, y se comprobó que **discrimina por los dos lados**: contra el árbol sin el test contesta `NO SE SOSTIENE` nombrando el archivo que falta, y contra el árbol con el test pero sin la cabecera re-anclada contesta `NO SE SOSTIENE` nombrando la clase vieja.
- Ficha retirada al índice, podada de P2, prompts regenerados.

## 9. La suite

**3822/3822, entera y sin argumentos, sin banner `FILTERED RUN`.** v0.1.176 traía 3803, y los 19 nuevos son exactamente los de `test_anchored_wedge_root_v1177.py`. Corrida dos veces: la primera se descartó a propósito porque se lanzó antes de que existiera el changelog —`test_version_consistency_v176` exige el archivo de la versión— y porque mientras corría se regeneraron las curvas, con dos procesos peleándose por los mismos núcleos, que es el ruido que AGENTS.md ya documenta; la que cuenta es la del árbol final, con nada más ejecutándose.

El renombrado de la clase de `test_janbu_wedge_v1142.py` no movió ninguna aserción, y sus 140 casos junto con los de `interslice` pasan igual antes y después.
