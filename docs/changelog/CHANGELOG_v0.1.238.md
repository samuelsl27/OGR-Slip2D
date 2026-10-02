# OGR Slip2D v0.1.238

**D89: cuando una muestra contesta por otra masa deslizante del círculo
determinista, se dice.** Cada muestra de Global Minimum y cada punto de la
sensibilidad re-evalúan el círculo determinista sin sus extremos, para que
resuelvan su propia masa (D36, v0.1.131), y el motor se queda con la de menor
factor. Eso es correcto, pero no se decía, y en un círculo con dos masas la
probabilidad de rotura puede ser entera de la otra. Ahora se cuenta y se dice
en Global Minimum, en Overall Slope y en la sensibilidad, sin mover un número.

Segunda versión de la segunda parte de la tanda P5. Al medir la premisa se
abre **D248** (más abajo).

## 0. Lo que se encontró, y dónde

### La premisa se sostiene

Medido con 0.1.237 sobre la muesca de `test_statistical_rebuild_v1154`
(Fredlund y Krahn 1977, problema 22, con una muesca en la coronación) con
Composite Surfaces encendida en las dos corridas, 40 muestras LHS con la
semilla 3 y las 30 dovelas del proyecto. La masa de cada muestra se obtuvo
reproduciéndola fuera del motor, y los factores coinciden bit a bit. La
determinista es la compuesta, x 56,05–158,73, F = 1,3823:

| Cohesión del suelo superior | Muestras | De la otra masa (la muesca, x 45,84–49,70) | Con F < 1 | De ellas, de la otra masa | Notas |
|---|---|---|---|---|---|
| uniforme 50–450 | 40 | 11 | 10 | **10** | ninguna |
| normal 300 ± 150 | 40 | 6 | 6 | **6** | ninguna |
| normal 600 ± 30 | 40 | 0 | 0 | 0 | ninguna |

La PF de 0,25 y la de 0,15 pertenecen enteras a la muesca. En la sensibilidad
de la cohesión (de 50 a 550, 51 puntos) contestan por la muesca 12 puntos, de
c = 50 a 160, también en silencio.

### Lo que el prompt pedía y se ajusta

- **La masa se reconoce por sus extremos exactos.** El prompt pedía comparar
  con la tolerancia de `_surface_key`, que D87 quitó en 0.1.237. No hace
  falta: en una corrida la geometría no cambia, así que la misma masa vuelve
  con los mismos extremos hasta el último dígito, y dos masas de un círculo
  son cuerdas disjuntas. Los extremos se leen del objeto, sin `to_dict()`,
  que en una compuesta redibuja la superficie (0,21 ms por muestra, frente a
  15 ms de la evaluación).
- **El recuento es un campo, no una nota** (`mass_switches`). Un número en
  cada corrida sana no es una frase, por la misma razón por la que
  `surfaces_tracked` no se publica. La frase va en `notes["mass_switch"]`
  solo cuando hay cambios.
- **Overall Slope, en sentido estrecho.** Cuenta solo las muestras cuya
  superficie crítica fue el círculo determinista con otra masa. Que la
  crítica sea otro círculo no es un cambio de masa: es el mínimo que se
  mueve, que es para lo que existe el análisis.
- **La sensibilidad, en una línea y no en `vs.note`.** `vs.note` marca una
  variable que no se barrió y la saca de la clasificación; esta sí se barrió.

### D248: las dovelas por defecto de la llamada directa

La primera reproducción muestra a muestra no coincidía con el motor. La
causa: `run_global_minimum` y `run_sensitivity` evalúan por defecto con 25
dovelas, diga lo que diga el proyecto, y la muesca tiene 30. La puerta de la
interfaz, la API y el MCP pasa las del proyecto, y el script del banco
también. La llamada directa no: es la misma clase que D93. En la muesca el
efecto es de −0,002 % en la media. Se abre como **D248** en P5 y no se toca
(regla 6).

## 1. El motor

- **`_extent`, `_circle_of` y `_MassSwitches`** (`probabilistic.py`).
  - `_extent`: los extremos de una superficie o de su diccionario.
  - `_circle_of`: el círculo de una superficie circular, compuesta o de capa
    débil; para una poligonal, ninguno.
  - `_MassSwitches`: cuenta las muestras contadas que son el círculo
    determinista con otros extremos, las que de ellas tienen F < 1 y a qué
    masa fueron.
  - No vigila una determinista sin extremos (no hay con qué comparar) ni una
    poligonal (conserva sus extremos y no tiene masa que cambiar).
- **Global Minimum.**
  - `MethodProbabilisticResult.mass_switches` y, si es mayor que cero,
    `notes["mass_switch"]`. La frase dice cuántas muestras, a qué masa fueron
    y cuál es la propia, y cuántas de las de factor menor que 1 están entre
    ellas.
  - `_publish_method_warnings` publica esa clave en `note_lines`, como la
    del 20 %, y nunca en el titular.
- **Overall Slope.** `OverallSlopeResult.mass_switches` y la misma frase, en
  sentido estrecho.
- **Sensibilidad.** `VariableSensitivity.mass_switch_values` guarda los
  valores del parámetro cuyo punto contestó por otra masa, y añade una línea
  en `note_lines` con el método, la variable, cuántos puntos y entre qué
  valores.
- Los dos `summary()` llevan `mass_switches`, así que la API y el MCP lo ven.
- **Ningún número se mueve:** el vigilante solo lee resultados.

## 2. La interfaz

Nada nuevo: el panel de notas y la ventana de estadística leen `note_lines`
(el canal de D129), y por ahí llegan las tres frases.

## 3. Tests

**`tests/test_mass_switch_note_v1238.py`**, 13 casos sobre la muesca. Cubre:

- los ayudantes, sobre objetos y diccionarios, y que otro círculo no es un
  cambio de masa;
- en Global Minimum:
  - el recuento es el de una reproducción independiente;
  - la frase nombra las dos masas y cuántas de las que fallan son de la otra;
  - llega al panel y no al titular;
  - los factores son los de la reproducción bit a bit;
  - sin cambios con la cohesión estrecha;
  - una determinista sin extremos no se vigila;
- Overall Slope con una búsqueda que solo evalúa el círculo: el recuento y
  la frase, y nada con la cohesión estrecha;
- en la sensibilidad:
  - los puntos son los de la reproducción;
  - la variable sigue en la clasificación;
  - una sola línea con el número de puntos y la masa;
  - nada con la cohesión estrecha.

Los recuentos se comparan con una reproducción y nunca se escriben a mano.

**Discriminación** contra `git archive` ae00bcc (0.1.237), con el runner de
ese árbol: **11 de 13 fallan**. Dos fallan por comportamiento: la nota no
existe, ni en `notes` ni en el panel. Nueve fallan por símbolo: el recuento,
los ayudantes y los puntos del barrido. Pasan la premisa y «no se mueve
ningún número», a propósito.

`test_partial_method_loss_v1170::test_a_healthy_sensitivity_run_says_nothing`
sigue mudo, y es lo que debe hacer: sin la opción, la determinista es la
propia muesca y no hay cambio.

## 4. El banco

- **`_tools/ejecutar_probabilistico.py`** archiva también los cambios de masa
  de Overall Slope (`mass_switches`). Los de Global Minimum ya los guardaba:
  archiva el `summary()` entero.
- **Base comprobada antes de correr:** los once `resultados_probabilistico*.json`
  vivos eran, byte a byte, los de `Evaluaciones/0.1.237`.
- **Re-corrida del lote** con `correr_probabilistico.py` (2772 s, en paralelo
  con la suite). Comparados con la instantánea, aplanados y sin `version_ogr`,
  `segundos` ni la clave nueva: **198 números, todos iguales**, y ninguna
  clave sin pareja. Es el A/B de «ningún número se mueve» sobre el banco.
- **Cambios de masa archivados: cero en las doce entradas**, las 10 de Global
  Minimum del 028 y Global Minimum y Overall Slope del 036. Ningún círculo
  del banco cambia de masa con sus variables. El defecto se ve en la muesca,
  y por eso el cierre lo mide allí, en vivo.
- **Cierre: `d89()`, CUBIERTO POR TEST.** Comprueba cuatro cosas:
  - en vivo, sobre la muesca escrita dentro del cierre: 11 de 40 muestras,
    dichas, con los mismos factores que una reproducción muestra a muestra;
    con la cohesión estrecha, ni un cambio ni una línea;
  - la fuente;
  - las once corridas, de 0.1.238 en adelante, con los números de 0.1.237 y
    los cambios declarados;
  - la discriminación.

  D89 se retira al índice.

## 5. Lo que se reporta y NO se corrige

- **D248**, arriba.

## 6. Verificación

- **Suite entera:** 5334 de 5334, en 65 min, con el lote del banco y la
  verificación de los cierres en paralelo.
- **Selección** de estadística, sensibilidad, Overall Slope, pérdidas
  parciales, Interpret, clave de superficie, i18n y versiones: 398 de 398.
- **Discriminación:** 11 de 13 contra 0.1.237.
- **Banco:** los once resultados re-corridos (198 números iguales a 0.1.237,
  cero cambios de masa) y `d89()` CUBIERTO POR TEST. Ciclo de cierre:
  - `verificar_cierres.py` entero: 211 cierres y 0 bajadas;
  - instantánea `Evaluaciones/0.1.238`;
  - D89 retirada, podada de `PAQUETES` y tachada en la cadena P5;
  - D248 abierta al final de P5;
  - prompts regenerados (46);
  - auditorías de invariantes con 0 ERROR en el 02 y en la raíz;
  - instantánea rehecha con `--forzar`;
  - `--seco` completo sin ningún NO SE SOSTIENE ni PENDIENTE DE CORRIDA.

**Qué falta por probar:**
- **La nota en la aplicación real:** el panel de notas y la ventana de
  estadística con una corrida que cambie de masa. Leen `note_lines`, que el
  test comprueba, pero nadie lo ha mirado en pantalla.
- **Un caso publicado con cambio de masa:** ningún modelo del banco lo
  tiene. La muesca es sintética.
