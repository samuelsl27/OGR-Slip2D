# OGR Slip2D v0.1.211

**Tres defectos de la admisibilidad posterior al análisis y del desembalse
multietapa, los tres del paquete P3 del banco de verificación y los tres con
decisión de la propietaria (2026-09-26):**

- **D184:** un cribado que revienta RECHAZA la superficie y lo dice.
- **D194:** una etapa del desembalse sin factor deja la superficie INVÁLIDA con
  la razón de su pasada, en las tres etapas.
- **D200:** en la rama del casquete drenado que cicla, los chequeos juzgan los
  DOS CUERNOS y no las dovelas del llamante.

Se midió antes de corregir, sobre un worktree de 0.1.210, y después sobre este
árbol:

- **0 filas del 095–098 movidas y 0 mínimos de búsqueda movidos**, en 12
  búsquedas enteras y 4 círculos publicados.
- **0 excepciones del cribado** en 0.1.210, en la suite (474 488 llamadas) y
  en el 095–098 (22 492).

Lo que sí cambia está contado:

- 23 superficies más, rechazadas en la rama que cicla (D200);
- 56 superficies que pasan de «no aplica» a la razón real de su pasada (D194).

- **D184 cambia el motor.** `BaseSearch._is_admissible` envolvía el cribado en
  `except Exception: return True`. El `try` pasa a `checks.screen_surface`,
  que ahora declara la excepción: `SCREEN_ERROR`, una nota con el tipo y el
  texto, y −101 en la exportación, aunque ese texto diga `m_alpha`.
- **D194 cambia el motor.** `math.isfinite(None)` en el casquete drenado
  tumbaba la búsqueda entera. Ahora `DrawdownStageFailed` lleva la pasada que
  falló y el envoltorio publica su `reason`.
- **D200 cambia el motor.** `LEMResult.screen_states` lleva los dos cuernos al
  cribado. Se publican las dovelas del último cuerno, sin fuerzas.
- **Del censo nace D202:** la etapa 1 del desembalse fija el estado de
  consolidación con una pasada NO convergida, sin decirlo. Afecta a 796
  superficies del 096, y ninguna fila publicada. Reportada, no corregida.

Lo que cambia en el banco de verificación (`_tools/`, `_auditoria/`, fichas)
está fuera de git y se resume en la sección 6.

---

## 0. Lo que estaba mal en los encargos

### El «27 de 1859» de D200 mezclaba dos denominadores, y el recuento era parcial

- **1859 son las superficies GENERADAS** por la rejilla del 096
  (13 × 13 × 11); las que llegan al envoltorio con resultado son 1380, que es
  el denominador del censo de D112b.
- **El «24 de 27» no estaba archivado en ningún sitio**, solo en la prosa de
  la ficha. El censo nuevo lo vuelve a medir y **se confirma**: el signo
  invertido sobre las dovelas del llamante rechaza 24 de las 27 superficies
  de Janbu en la rama que cicla.
- **La rama que cicla tiene 139 superficies en el 095–098, no 96.** D112b
  corrió 7 de las 12 búsquedas enteras. En el 096 cicla también con Bishop
  (5), Corps 1 (15), Corps 2 (20) y el Ordinario (3).

### D194 no tenía caso en el banco

Ninguna pasada de etapa 3 del 095–098 sale sin factor, así que el `TypeError`
nunca tumbó una búsqueda del banco. Las de las etapas 1 y 2 sí existen: 37 y
19.

### D184 no disparaba, y el censo de D94 no se conserva

- Ni la suite ni el 095–098 lanzan una sola excepción dentro del cribado.
- La receta que la ficha pedía, la de D94, solo existía en la prosa de
  `CHANGELOG_v0.1.161.md`: no queda ningún archivo de aquel censo. Esta vez el
  parche (`sitecustomize`) se archiva junto al censo.

### El alcance del censo de D184 es una decisión, no el banco entero

- La ficha pedía «la suite y el banco». La propietaria decidió la suite y el
  095–098 (el banco entero son ~16 h).
- `d184()` lo dice en su detalle para que el cero no se lea como más de lo que
  mide.
- En el banco, el −120 está apagado en los 194 modelos, así que fuera del
  095–098 solo se ejercería el m-alpha.

---

## 1. D184 — un cribado que revienta rechaza la superficie y lo dice (motor)

### El defecto

`_is_admissible` hacía:

```python
try:
    ok, screen, reason = screen_surface(...)
except Exception:
    return True
```

Una superficie que nadie pudo cribar quedaba ADMITIDA, sin nota, sin
`admissibility_reason` y sin aviso, y podía ser la crítica. Un fallo del
medidor se leía como veredicto: la forma de D94.

### La decisión (de la propietaria)

**Rechazarla y declararlo.** Se consideraron otras dos opciones:

- **Admitirla con nota:** el mínimo no sube, pero una nota en una superficie
  admitida cambia lo que significa `admissibility_note`.
- **Dejar que reviente,** como `_analyse` con un `TypeError`: ahí la
  alternativa era un número equivocado. Aquí es un veredicto equivocado, y
  terminar una búsqueda de horas por una superficie es desproporcionado.

El precio queda escrito en `SCREEN_ERROR`: si esa superficie era la más baja,
el mínimo sube, y la nota dice por qué.

### El arreglo

- `methods/base.py`: `SCREEN_ERROR = "screen_error"`, en `ALL_SCREENS` y
  disjunta de `ALL_REASONS`.
- `checks.screen_surface`:
  - envuelve los dos chequeos y devuelve `(False, SCREEN_ERROR, "admissibility
    checks could not be evaluated (<Tipo>: <texto>)")`;
  - va aquí y no en la puerta, por el argumento de `m_alpha_check`: toda
    puerta que llame a los chequeos dice lo mismo.
- `search._is_admissible` pierde su `try`.
- `interpretation.error_code`:
  - `SCREEN_ERROR` → −101;
  - esa rama va ANTES de la prueba `"m_alpha" in note`, porque el texto de
    la excepción puede decir `m_alpha_sign`;
  - −112 es un veredicto de la pantalla m-alpha, que es justo lo que no
    ocurrió.
- Docstrings que afirmaban el «tragar y admitir»:
  - `checks._material_tensile_strength` y `checks._per_slice`;
  - `TestAnAllowanceNeverBreaksTheCheck` de `test_tensile_strength_rock_v1191.py`.
  
  Su lógica no cambia: devolver 0,0 sigue siendo lo conservador.

### El censo (receta de D94, antes y después)

Se envuelve, se registra a un archivo y se vuelve a lanzar, así que el
manejador de arriba sigue haciendo exactamente lo mismo:

- **suite:** `_tools/censo_cribado_suite_d184.py`, con un `sitecustomize` que
  parchea `ogr_slip2d.checks` al importarse, también en los hijos de la
  búsqueda paralela;
- **095–098:** `_tools/censo_p3_desembalse.py`.

| | suite (casos / llamadas / excepciones) | 095–098 (llamadas / excepciones) | control |
|---|---|---|---|
| 0.1.210 | 4629 / 474 488 / **0** | 22 492 / **0** | ve el caso |
| 0.1.211 | 4664 / 473 499 / 10, **todas del test forzado** | 22 492 / **0** | ve el caso |

En 0.1.211, las 10 excepciones de la suite son las que
`test_screen_error_v1211.py` provoca a propósito, y vuelven como 10
`screen_error` en los mismos casos. Fuera de ese archivo no hay ninguna.

Los controles:

- **Suite:** un hijo de `ProcessPoolExecutor` criba una superficie cuyo
  material revienta al linealizarse. El registro tiene que traer esa
  excepción con el pid del hijo; en 0.1.211 el hijo ya no revienta, devuelve
  `screen_error`. En 0.1.211, 385 procesos llevaron la sonda, todos del árbol
  medido, con 426 archivos de registro y 0 líneas ilegibles (ver la sección 6
  sobre por qué cuenta eso).
- **095–098:** la misma superficie por `GridSearch._is_admissible`. En
  0.1.210 vuelve ADMITIDA sin nota.

---

## 2. D194 — una etapa sin factor deja la superficie inválida con su razón (motor)

### El defecto

- Desde D56 (v0.1.152), un método sin factor devuelve `fos=None`.
- El casquete drenado hacía `if not math.isfinite(r3.fos): break`, y con
  `None` eso lanza un `TypeError`.
- Ni el envoltorio (`RapidDrawdownError`) ni `_analyse` (`ArithmeticError`) lo
  capturan. `_parallel_grid_run` se lo traga en el hijo y repite la búsqueda
  en serie, así que la corrida muere después de hacer el trabajo dos veces.
- Las etapas 1 y 2 sí comprobaban `None`, pero lo convertían en «el
  procedimiento no aplica», que es una afirmación sobre el talud y no sobre el
  solver.

### La decisión (de la propietaria)

La superficie sale **inválida con la razón de la pasada que falló**, en las
**tres** etapas. «No aplica» queda para las precondiciones: FS1 < 1, una
envolvente que no se puede transportar, una superficie que no se puede
rebanar.

Parar el casquete en la última pasada con factor se descartó: el casquete solo
BAJA resistencias (`cur[i] <= tau_ff`), así que una pasada anterior es una
cota del lado inseguro del factor al que el procedimiento no llegó. La
decisión está escrita en el docstring de `rapid_drawdown_fos`.

### El arreglo

- `DrawdownStageFailed(RapidDrawdownError)` lleva `stage` y la pasada (`result`).
  El mensaje es «Stage k [(drained cap, pass n)] produced no factor of
  safety: <mensaje interior>». Al ser subclase, quien ya la capturaba la sigue
  capturando.
- Las etapas 1, 2 y 3 la lanzan con `fos is None`. Sale el `math.isfinite`
  muerto desde D56.
- `MultiStageDrawdownMethod.compute_fos` la captura antes que
  `RapidDrawdownError` y devuelve:
  - `fos=None`;
  - el `reason` de la pasada, o `REASON_NON_PHYSICAL_FOS` si no trae ninguno
    (D56 solo obliga al mensaje);
  - las dovelas de esa pasada;
  - `details` con `drawdown_stage_failed`.

### Lo que mueve en el banco

Censo del 095–098 en 0.1.210:

- **0 pasadas de etapa 3 sin factor, 0 búsquedas que revientan;**
- **37 de etapa 1 y 19 de etapa 2:**
  - Corps 2 del 096 (`force_balance_diverged`);
  - GLE y Spencer del 096 (`all_lambda_diverged`);
  - Bishop y el Ordinario del 097/098 (`non_physical_fos`, `zero_driving`).

Esas 56 superficies cambian de razón y de mensaje; ningún factor se mueve.
Estaban y siguen inválidas. En el censo de después (0.1.211), las superficies
publicadas como «no aplica» pasan de **336 a 280**: exactamente esas 56. Los
mínimos de las 12 búsquedas y los 4 círculos publicados son idénticos a los de
0.1.210.

---

## 3. D200 — en la rama que cicla, los chequeos juzgan los dos cuernos (motor)

### El defecto

Cuando el casquete drenado no se asienta, el desembalse informa del centro del
ciclo (v0.1.71). Ninguna pasada calculó ese centro. En esa rama, el envoltorio
publicaba las dovelas del LLAMANTE: embalse lleno y materiales drenados,
φ' = 30 en el 096. Los chequeos juzgaban ese par con un factor de etapa 3.

### La decisión (de la propietaria)

Los chequeos juzgan los **dos cuernos**, cada uno como lo resolvió su pasada, y
el centro solo pasa si pasan los dos. Es la regla que D112b escribió para el
veredicto interior, llevada al cribado.

Las otras dos opciones de la ficha se descartaron:

- **Las dovelas de la etapa 3 con el factor del centro:** también es un estado
  que ninguna pasada calculó.
- **Ningún chequeo:** deja la rama sin cribar.

### El arreglo

- `LEMResult.screen_states` (campo nuevo, `()` por defecto, fuera de
  `to_dict`): los estados que el cribado juzga EN LUGAR del resultado.
- `screen_surface` juzga `screen_states or (result,)`:
  - primero la tracción sobre todos los estados, luego el m-alpha, así que
    «falla los dos» sigue leyéndose como tracción;
  - las notas de D177 no cambian ni un carácter.
- En la rama que cicla, el envoltorio publica las dovelas del último cuerno
  (el rebanado de la etapa 3, sin fuerzas). Los dos cuernos van en
  `screen_states`.
- El factor del centro, la rama con pasada final y la regla de D112b no se
  tocan.

### Lo que mueve en el banco

Censo del 095–098 en 0.1.210. Por cada superficie de la rama que cicla, el
veredicto con cuatro criterios:

| criterio | rechazadas de 139 |
|---|---|
| dovelas del llamante (0.1.210) | 3 |
| **los dos cuernos (0.1.211)** | **26** |
| dovelas del último cuerno con el factor del centro | 26 |
| signo invertido sobre las del llamante (el «24 de 27») | 29 |

- **Veredicto que cambia: 23 superficies,** 21 de las 27 de Janbu en el 096 y
  2 de las 5 de Bishop en el 096.
- **Todas fallan en la misma dovela:** la última, en el extremo de
  coronación, con la base a 77,6°–82,4°. En la etapa 3 es no drenada con
  φ = 0, así que m-alpha = cos α. Ahí actúa el techo de 78,46° que D114/D61
  decidieron mantener. Con las dovelas del llamante esa base lleva φ' = 30
  drenado y pasa.
- No es una regla nueva: es el criterio que ya juzgaba las superficies de
  pasada final de esas mismas búsquedas, sobre el estado que la etapa 3
  resolvió.
- **Mínimo de cada búsqueda con cada criterio: idéntico en las 12.** La
  reconstrucción coincide con el crítico de la búsqueda.

El censo de después (0.1.211) lo confirma sobre el código:

- **0 de 139** superficies publican ya las dovelas del llamante;
- los rechazos son los predichos (26);
- 0 filas y 0 mínimos movidos contra 0.1.210.

Las llamadas a `m_alpha_check` suben de 21 619 a 21 732. Las +113 son las 139
superficies que ahora criban dos cuernos, menos las 26 que se rechazan en el
primero: lo que el cribado debe costar.

---

## 4. Lo que se reporta y NO se corrige (regla 6)

- **D202 (P3), ficha nueva.** La etapa 1 del desembalse pide a su pasada tener
  factor y que sea ≥ 1, pero no mira `r1.converged`.
  - El estado de consolidación (σ'_fc y τ_fc = resistencia / F1) se fija con
    una pasada no convergida, sin decirlo.
  - Caso concreto: en el 096 con Corps 1 y el círculo (69,0; 110,0; 89,1595),
    la etapa 1 no encuentra horquilla y devuelve **F = 5,0, el techo de su
    propio muestreo**. Aun así la superficie sale **válida con 1,7093**.
  - En las 12 búsquedas del 095–098 son **796 superficies, 643 válidas**:
    Corps 1 331, Corps 2 358, Lowe-Karafiath 90 y Spencer 17, todas del 096.
  - Ninguna fila publicada: los cuatro círculos publicados convergen en la
    etapa 1.
- **`_parallel_grid_run` se traga cualquier excepción de los hijos**
  (`except Exception: return None`) y repite la búsqueda en serie, y es a
  propósito. El precio queda dicho: un defecto del código en un hijo cuesta la
  búsqueda dos veces antes de salir, y su traza es la del padre. Sin ficha:
  la vuelta atrás es deliberada, y el defecto acaba saliendo igual.

---

## 5. Los tests

Los tres archivos nuevos se midieron copiándolos a un `git worktree` de 0.1.210
(e983574) y ejecutándolos allí. Las cifras son medidas.

| Archivo | Casos | Fallan en 0.1.210 | Por comportamiento | Débiles (nombre o atributo) |
|---|---|---|---|---|
| `test_screen_error_v1211.py` | 12 | 7 | 6 | 1 |
| `test_drawdown_stage_failure_v1211.py` | 10 | 7 | 6 | 1 |
| `test_cycle_horns_screened_v1211.py` | 13 | 7 | 5 | 2 |

Los casos que fallaban por el `ImportError` de un símbolo nuevo se reordenaron:
el símbolo se importa DESPUÉS de comprobar el comportamiento, así que en 0.1.210
fallan por lo que hace el código.

Cabeceras actualizadas: `test_drawdown_passthrough_v1210.py` (qué no afirma, y
la guarda `no_per_slice_key_travels`) y `test_tensile_strength_rock_v1191.py`.

**Suite entera, sin argumentos: 4664 casos, 4664 pasan, 0 fallan** (265
archivos). Tardó 52 min 53 s, de 22:49 a 23:42. No es una medida del coste:
compartió los cuatro núcleos con los dos censos de 0.1.210.

---

## 6. El banco (fuera de git)

- **Herramientas nuevas:**
  - `_tools/censo_cribado_suite_d184.py`: la suite con `sitecustomize` y
    control en un hijo; `--solo-informe` escribe
    `docs/audits/screen_error_v1211.md`;
  - `_tools/censo_p3_desembalse.py`: el 095–098, un árbol por corrida,
    `--comparar` para el A/B entre árboles y `--informe` para
    `docs/audits/drawdown_cycle_v1211.md`.
- **Censos:**
  - `_auditoria/D184_cribado/`: `suite_<v>.json`, `censo_<v>.json`, el
    `sitecustomize` y el control;
  - `_auditoria/D194_D200_casquete/`: `censo_<v>.json`.
- **Cierres nuevos en `verificar_cierres.py`:** `d184`, `d194` y `d200`,
  CUBIERTO POR TEST, con `CIERRE = 0.1.211`.
  - La parte en vivo usa solo símbolos que ya existían en 0.1.210. Contra ese
    árbol las tres dan NO SE SOSTIENE por comportamiento: admitida sin nota;
    «no aplica» y `TypeError`; dovelas del llamante y cuerno rechazado que no
    rechaza.
  - `_discriminacion` acepta el nombre del archivo; las llamadas de 0.1.210
    no cambian.
  - El `verificar_cierres.py` de 0.1.210 queda archivado en
    `_auditoria/D184_cribado/`.
- **Ficha nueva:** D202, con su prompt largo, en P3. El siguiente número libre
  es D203.

### Dos trampas por el camino, las dos de las herramientas y no del motor

- **El registro compartido del censo se pisaba.** La primera versión del
  `sitecustomize` escribía todos los procesos en UN archivo, en modo «a», la
  receta de D94 tal cual.
  - En Windows eso no es atómico entre procesos: se busca el final y luego se
    escribe. Dos hijos que vuelcan a la vez sobrescriben la misma posición, y
    un registro un byte más corto que el otro deja una línea vacía.
  - Medido: **36 registros pisados por corrida de la suite**, idénticos en las
    dos versiones del motor.
  - Las cuentas de llamadas salían por debajo, y una excepción se podía haber
    perdido. En la suite de 0.1.210, la versión mala contó 452 150 llamadas
    al cribado; la buena, 474 488 (−4,7 %).
  - Ahora cada proceso escribe su propio archivo, con pid, hora y azar en el
    nombre, porque Windows reutiliza los pid dentro de una misma corrida. El
    resumen exige 0 líneas ilegibles para ser completo.
  - Las dos corridas malas se conservan en
    `_auditoria/D184_cribado/descartado_registro_compartido/`, y los dos
    censos de la suite se repitieron.
- **La copia del `verificar_cierres.py` viejo tumba `d189` si vive en
  `_tools/`.** Solo se puede ejecutar desde ahí, porque saca `RAIZ` de su
  propia ruta. Pero `d189` recorre `_tools/` buscando quién llama a
  `normalizar_superficie` sin razón declarada, y encontró la copia: la
  regresión dio una «bajada» de D189 que no existe. Sin la copia, D189 vuelve
  a CUBIERTO POR TEST.

---

## 7. Verificación

- **Suite entera, sin argumentos:** 4664 de 4664 (sección 5).
- **Discriminación de los tres tests nuevos**, medida en un worktree de
  0.1.210 y archivada en el banco: D184 7 de 12, D194 7 de 10, D200 7 de 13.
- **Censos antes y después:**
  - suite: 0.1.210 con 0 excepciones del cribado en 474 488 llamadas;
    0.1.211 con solo las 10 del test forzado;
  - 095–098: 0 excepciones, 0 filas y 0 mínimos movidos, sin parejas sueltas;
  - todos los controles ven su caso, y 0 líneas ilegibles en los registros.
- **`d184`, `d194` y `d200`:**
  - contra este árbol, CUBIERTO POR TEST;
  - contra el worktree de 0.1.210 en un proceso aparte, NO SE SOSTIENE por
    comportamiento;
  - con `_SIN_HISTORICO = True` dejan de cerrar;
  - `d175`, `d186` y `d187` siguen cerrando.
- **Regresión de cierres, clave a clave:** el `verificar_cierres.py` de 0.1.210
  contra el nuevo, sobre el mismo motor, da 159 claves comunes con el mismo
  veredicto y el mismo detalle, y solo entran las tres nuevas. Contra los
  veredictos archivados, 0 bajadas: la de D189 era la copia temporal (sección
  6).
- **Banco:**
  - instantánea `Evaluaciones/0.1.211`, antes de retirar y otra vez con
    `--forzar` al final (2632 archivos, comprobados byte a byte);
  - `retirar_cerrados.py --escribir D184 D194 D200`, con las secciones
    guardadas en `ERRORES_Y_DISCREPANCIAS_retiradas.md`;
  - `PAQUETES` podado (P3 queda `D168`, `D169`, `D202`) y la cadena de P3
    tachada;
  - `generar_prompts.py`: 50 prompts, 41 largos, las 9 FALTA previas y 0 sin
    paquete;
  - `generar_comparativa.py` y `balance_evaluaciones.py` contra
    `Evaluaciones/0.1.210`: 559 → 559 filas, todas IGUAL, 0 sin pareja;
  - `auditoria_invariantes.py`: 0 ERROR en el 02 (487 AVISO y 257 INFO, los
    mismos recuentos que en 0.1.210) y 0 ERROR en la raíz.
- **Citas de los prompts largos:** `comprobar_citas_prompts.py` no encuentra
  nada en D202. El único problema que da es el de D135, anterior a esta tanda.

**Lo que falta por probar, dicho:**

- el censo de D184 sobre el resto del banco (fuera del 095–098): se dejó fuera
  por decisión de alcance, y el −120 está apagado en los 194 modelos;
- que una superficie con `screen_error` llegue a la interfaz y a la
  exportación de una corrida real: no hay ninguna en la suite ni en el banco
  fuera del test forzado; lo cubren `error_code` y el test;
- D202, reportada y sin corregir.
