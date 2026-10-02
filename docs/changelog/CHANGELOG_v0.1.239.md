# OGR Slip2D v0.1.239

**D88: un cálculo estadístico rechaza el método cuya superficie determinista
no vuelve a ser ella misma en el proyecto de las muestras, en las dos
direcciones.** La guarda de 0.1.154 rechazaba una compuesta cuyas muestras
corren con Composite Surfaces apagada, y solo eso. La dirección contraria, o
un filtro puesto solo en el proyecto de las muestras, publicaba un resultado
cuyo determinista no es el mecanismo de sus muestras. Ahora se pregunta al
mecanismo, en Global Minimum y en la sensibilidad.

Tercera versión de la segunda parte de la tanda P5.

## 0. Lo que se encontró, y dónde

### La premisa se sostiene, y desde 0.1.238 se dice pero se publica

Medido con 0.1.238 sobre la muesca de `test_statistical_rebuild_v1154`
(Fredlund y Krahn 1977, problema 22, con una muesca en la coronación), seis
muestras LHS con la semilla 1, la cohesión del suelo superior entre 420 y
780 psf y las 30 dovelas del proyecto:

| Caso | Global Minimum | Sensibilidad |
|---|---|---|
| A: determinista con la opción APAGADA (la muesca, F = 3,3585), muestras con ella ENCENDIDA | publicado: media 1,3781 (−59 %); el panel dice, por D89, que las 6 muestras cambiaron de masa | publicado, 3 de 3 puntos de otra masa |
| B: al revés | rechazado por la guarda de 0.1.154 | rechazado |
| C: la misma opción, Minimum Elevation de 30 ft solo en las muestras | publicado: media 3,3337 frente a 1,3823 (+141 %), dicho por D89 | publicado |
| D: control, el mismo proyecto | media 1,3781, sin notas | sin notas |

La guarda no puede ver A ni C: tendría que saber con qué ajustes se obtuvo
el determinista, y eso no viaja con él.

### Por qué preguntar al mecanismo

Es la vía (b) del prompt, que el plan aprobado el 2026-10-01 eligió: no
cambia el contrato de `run_global_minimum` y es simétrica por construcción.
Antes de muestrear, la semilla de la superficie determinista se evalúa una
vez en el proyecto de las muestras, preparado como ellas y sin ninguna
muestra aplicada, con su mismo evaluador. Tiene que volver como la misma
superficie: el mismo tipo y los mismos extremos. En una geometría, la misma
masa vuelve hasta el último dígito (D87, D89), así que cualquier diferencia es
otro mecanismo. Cubre cualquier ajuste que decida la masa, no solo Composite
Surfaces.

## 1. El motor

- **`_does_not_reevaluate_to_itself`** (`probabilistic.py`) es la sonda, y
  `_NOT_ITSELF` su frase. La frase dice a qué masa contesta la superficie y
  de qué tipo es, cuál es la suya, y que un ajuste que decide la masa (como
  Composite Surfaces o un filtro de superficies) cambió entre las dos
  corridas. No lleva «: » dentro, porque el panel agrupa por el primero, que
  pone el identificador del método.
- **Va detrás de la guarda de 0.1.154**, que no cambia ni de firma ni de
  docstring. En su dirección la guarda decide primero, con su frase, que es
  más precisa.
- **Global Minimum y la sensibilidad** rechazan el método con la razón en
  `notes[mid]`, lo cuentan entre los perdidos y no lo publican en
  `by_method`. La línea llega al panel por `_publish_method_losses`.
- **Despacho directo, no `_evaluate_on`:** los tests parchean ese global
  para contar y hacer fallar las muestras, y la sonda no es una muestra.
- **No rechaza** si la sonda falla o no devuelve superficie, ni si la
  determinista no trae extremos o es una poligonal (conserva sus extremos):
  en esos casos las muestras dicen lo que encuentran.
- **Overall Slope no lleva sonda:** no vuelve a evaluar la superficie
  determinista, porque busca de nuevo en cada muestra. Su `deterministic_fos`
  es el que recibe, y queda dicho aquí como límite.

## 2. La interfaz

Nada nuevo: la razón llega al panel de notas y, si se pierden todos los
métodos, a la barra de estado, por los canales de D127 y D129.

## 3. Tests

**`tests/test_reevaluation_symmetry_v1239.py`**, 10 casos sobre la muesca:

- la premisa: la guarda deja pasar la dirección apagada → encendida;
- las dos direcciones y el filtro, en Global Minimum y en la sensibilidad:
  rechazados con la razón, la línea en el panel y nada en `by_method`; la
  dirección que ya conocía la guarda conserva su frase;
- la frase no lleva separador interno;
- la sonda no cambia nada más:
  - con el mismo proyecto, las muestras son bit a bit las de una corrida sin
    sonda;
  - no pasa por `_evaluate_on`;
  - una excepción en la sonda no rechaza;
  - una determinista sin extremos no se sondea.

**Discriminación** contra `git archive` e048b98 (0.1.238), con el runner de
ese árbol: **6 de 10 fallan**. Cuatro fallan por comportamiento: el método se
publicaba en la dirección apagada → encendida, con el filtro y en la
sensibilidad, y `prepare` se llamaba una vez menos porque no había sonda.
Dos fallan por símbolo. Pasan la premisa, la dirección de la guarda y los
dos controles, a propósito. El test se reordenó antes de archivar la
discriminación, para que mire primero si el método se publicó, que es el
comportamiento, y luego la frase. En su primera versión, los casos clave
fallaban por el símbolo antes de llegar al comportamiento.

## 4. El banco

- **Base comprobada antes de correr:** los once `resultados_probabilistico*.json`
  vivos eran, byte a byte, los de `Evaluaciones/0.1.238`.
- **Re-corrida del lote** con `correr_probabilistico.py` (3194 s, en paralelo
  con la suite): **210 números iguales a 0.1.238** y ningún método rechazado.
  Ningún modelo del banco cambia de ajustes entre su determinista y sus
  muestras, que es lo que la sonda comprueba. En el banco es el A/B de «la
  sonda no rechaza lo que no debe».
- **Cierre: `d88()`, CUBIERTO POR TEST.** Comprueba:
  - en vivo, sobre la muesca del banco: la dirección apagada → encendida y
    el filtro solo en las muestras, rechazados por la sonda; el mismo
    proyecto, publicado y sin notas;
  - la fuente: la sonda en los dos análisis, por despacho directo;
  - las once corridas;
  - la discriminación.

  D88 se retira al índice.

## 5. Lo que se reporta y NO se corrige

- **Overall Slope** publica el `deterministic_fos` que recibe sin volver a
  evaluarlo (arriba). La sonda no le llega por construcción.
- **D248** sigue abierta (las 25 dovelas por defecto de la llamada directa).
  La sonda usa el evaluador de las muestras, con sus dovelas: un determinista
  de 30 dovelas y unas muestras de 25 pueden elegir masas distintas cerca del
  cruce. Si pasa, la sonda rechaza, y es lo que tiene que hacer.

## 6. Verificación

- **Suite entera:** 5344 de 5344, en 70 min, con el lote del banco y la
  verificación de los cierres en paralelo.
- **Selección** de estadística, sensibilidad, Overall Slope, pérdidas, la
  puerta (`cli_wiring`, `f3b`), API, MCP, i18n y versiones: 572 de 572 en
  31 archivos. Ningún test con un determinista fabricado a mano tropezó con
  la sonda.
- **Discriminación:** 6 de 10 contra 0.1.238.
- **Banco:** las once corridas re-corridas (210 números iguales a 0.1.238 y
  ningún rechazo) y `d88()` CUBIERTO POR TEST. Ciclo de cierre:
  - `verificar_cierres.py` entero: 212 cierres y 0 bajadas;
  - instantánea `Evaluaciones/0.1.239`;
  - D88 retirada, podada de `PAQUETES` y tachada en la cadena P5;
  - prompts regenerados (45);
  - auditorías de invariantes con 0 ERROR en el 02 y en la raíz;
  - instantánea rehecha con `--forzar`;
  - `--seco` completo después de retirar.

**Qué falta por probar:**
- **El rechazo en la aplicación real:** un modelo cuyo determinista se
  calculó con Composite Surfaces apagada y cuya estadística se lanza tras
  encenderla. La razón llega por los canales de D127 y D129, que los tests
  cubren, pero nadie lo ha mirado en pantalla.
