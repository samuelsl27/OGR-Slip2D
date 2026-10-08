# OGR Slip2D v0.1.274

**La cara de rezume del transitorio sigue la misma regla que la del permanente
(D269).** `TransientSeepageSolver.step` llevaba su propia copia del bucle de
conmutación, que liberaba un nodo retenido a P = 0 cuando su reacción pasaba
de 1e-12. Es un caudal ABSOLUTO, mientras que el permanente usa
q_tol = 1e-3 × el mayor caudal nodal. Con permeabilidades de 1e-13 a
1e-4 m/s en el banco, el resultado dependía de las **unidades** de la
permeabilidad.

## 0. Lo que se encontró (puerta de medida B, `_auditoria/P6_0274/` del banco)

**El A/B en el mismo proceso, con el interruptor apagado y encendido, no mueve
nada del banco:**
- 05-015, 016 y 021 no tienen cara: idénticos al bit por construcción;
- 05-018, 019 y 020 tienen 22–28 nodos de cara y salen idénticos al bit, con
  las mismas liberaciones y retenciones;
- en el caso a largo plazo de `test_transient_v130` la diferencia frente al
  permanente es la misma, 2,85e-7;
- en el desembalse del 102 cambia una liberación, en un paso que no converge
  en ninguno de los dos lados. Las cargas se mueven 2,8e-7 m y los factores
  menos de 1e-9.

Ningún estado de convergencia cambia.

**Lo que sí distingue las dos reglas es una identidad dimensional.** Si se
multiplican todas las permeabilidades por λ y todos los tiempos por 1/λ, el
sistema de cada paso queda multiplicado por λ y las cargas no pueden cambiar.
Con λ = 2⁻²⁰ el escalado es exacto en coma flotante, así que tienen que salir
iguales al bit.

El caso es un desembalse de la presa rectangular de Gardner (la cabeza aguas
arriba baja de 10 a 4 m):
- con la regla absoluta, la cara toma otro nodo (5 frente a 6) y las cargas
  se mueven 2,47 cm a la hora y 0,82 cm a las 10 horas;
- con la relativa, son **iguales al bit**.

**La escala de q_tol.** El plan consideró tomarla de un permanente saturado
con las condiciones de la etapa, y se descartó: su caudal vale cero en un
desembalse a nivel uniforme, justo cuando el flujo transitorio es mayor, y eso
devolvería q_tol = 1e-14. Se toma de la primera solución lineal de cada paso,
que ya lleva el flujo de almacenamiento y escala con el paso de tiempo.

**Decisión de la propietaria:** adoptar.

## 1. Qué cambia (`ogr_fem2d/solvers/seepage.py`)

- **El interruptor `TRANSIENT_FACE_RULE`** (encendido; alta en
  `INTERRUPTORES` del banco, (0, 1, 274)). Encendido, `step()`:
  - toma q_tol de las reacciones de su primera solución lineal;
  - conmuta con `_switch_seepage_face`, la regla del permanente;
  - al final pregunta a su estado final con `_unsettled_nodes`. Un paso que
    deja nodos que violan la condición de la cara no está convergido, y la
    etapa lo cuenta en `notes["unsettled_nodes"]`.
- **Sin nodos de cara, `step()` no calcula nada nuevo.** Erfc, Terzaghi,
  capas, Ferris y Celia hacen la misma aritmética.
- **Apagado**, reconstruye el transitorio de 0.1.273.
- **Se corrige el comentario de `q_tol` del permanente**, que hablaba del
  «caudal de Dirichlet total» cuando el código toma el mayor caudal nodal.

## 2. Tests

`tests/test_transient_face_rule_v1274.py`, 4 casos (los 4 fallan con
0.1.273):

- **La identidad de escala:** al bit con la regla relativa, y con la absoluta
  (interruptor apagado) las cargas se separan más de 1 mm (2,5 cm medidos).
- **Sin cara, nada cambia:** las mismas cargas e iteraciones al bit, con el
  interruptor apagado y encendido, y sin nota nueva.
- **Una etapa con cara** informa de sus nodos sin asentar.

Suite entera: **5782 de 5782**.

## 3. Cierre en el banco

`d269()` en el `verificar_cierres.py` de la raíz exige:
- que `step()` use `_switch_seepage_face` y `_unsettled_nodes`;
- el interruptor encendido;
- el test de la identidad de escala;
- el A/B archivado.

Veredicto: **CUBIERTO POR TEST**. El banco no se re-corre: el A/B da cero
filas.
