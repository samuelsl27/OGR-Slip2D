# OGR Slip2D v0.1.245

**D226d: γγ divide, el sismo tiene su factor y la tensión efectiva de los
anclajes lleva γG solo si se pide. Se cierra D226.** Cuarta y última versión
de la ficha D226, la de las acciones de la norma de diseño, que empezó en
0.1.242.

## 0. Lo que se encontró, y dónde

Medido con 0.1.244 en el talud φ = 0 de `test_tension_crack_truncation_v1109`
(c 40, γ 19, seco), círculo (55; 58) R 34, Bishop a 1e-12:

- **γγ multiplicaba.** Con una norma personalizada de γγ = 1,25 y todo lo
  demás en 1, el factor era 0,888742, el del modelo con γ × 1,25. γγ es un
  coeficiente de material (EN 1997-1, Anejo A, Tabla A.4), y el valor de
  cálculo de una propiedad de material es el característico dividido por su
  coeficiente (EN 1997-1, 2.4.6.2, ec. 2.2: X_d = X_k/γ_M). Así lo aplica
  también la referencia, que divide todos los de material. Dividido, el factor
  es 1,388659. El comentario del código decía que un suelo más pesado es el
  sentido desfavorable para un peso que empuja, pero eso es tarea de γG, la
  acción, que desde 0.1.242 multiplica el peso de cada dovela. En todos los
  presets γγ = 1, así que solo mordía una norma personalizada.
- **El sismo no tenía factor.** kh = 0,1 daba 0,830616 con o sin norma.
- **La tensión efectiva de un anclaje no llevaba γG.** Con DA1-C1, la σ′v en
  (80; 30) era 190,0, igual que sin norma. Es lo que la referencia hace por
  defecto, porque una columna más pesada hace un anclaje más resistente; pero
  la referencia deja pedirlo y OGR no tenía cómo.

## 1. El motor y los ajustes

- **γγ divide** (`design_factors.UNIT_WEIGHT_DIVIDES`, el 37.º de
  `INTERRUPTORES`). Apagado, multiplica, como hasta 0.1.244.
- **Migración.** Un archivo personalizado escrito antes de esta versión (sin
  `factor_seismic`) lee su γγ invertido: dividir por 1/f es multiplicar por f,
  así que su número no se mueve.
- **`factor_seismic`** (undécima columna de los presets, 1 en todos).
  - Frank et al. (2004, §11.5) remiten la situación sísmica a la EN 1998-5,
    cuyo coeficiente sobre la acción sísmica es 1.
  - Multiplica kh y kv en la copia de análisis, con una nota.
  - Con una búsqueda del coeficiente crítico (Ky, Newmark) no hay coeficiente
    que factorizar: no se aplica y una nota lo dice.
  - El análisis rechaza un kh·f o kv·f que ya no sea un coeficiente (|k| < 1,
    y kh no negativo).
- **`anchor_permanent_factor`**, desmarcado por defecto.
  - Marcado, `bond.sigma_v_effective_at` multiplica por γG la columna de suelo,
    las cargas permanentes y la u de Ru que lee esa columna: un solo peso.
  - Las cargas variables y el agua embalsada, nunca.
  - Lo lleva el sello de la copia (`ActionFactors.anchor_permanent`,
    `anchor_factor()`).

## 2. La interfaz

En el diálogo de la norma:

- «Coeficientes sísmicos»;
- la casilla de anclajes, abierta con cualquier norma activada;
- una pista en «Peso específico» que dice que divide.

## 3. Tests

**`tests/test_design_anchors_seismic_v1245.py`** (14 casos):

- **Anclajes, contra la forma cerrada.** En la meseta, σ′v = γ·8 = 152:
  - sin la casilla, 152;
  - con ella, 1,35 × 152;
  - con una carga permanente, 1,35·(152 + 20); con una variable,
    1,35·152 + 20;
  - con Ru, 1,35·152·(1 − ru);
  - con una ley de arrancamiento lineal sin adhesión, cada muestra del perfil
    de adherencia es 1,35 veces la de sin casilla.
- **γγ:**
  - en los nueve métodos, γγ = 1,25 es el modelo con γ/1,25;
  - un archivo personalizado viejo da su número de 0.1.244 (0,888742);
  - con el interruptor apagado, otra vez la multiplicación.
- **Sismo:**
  - en los nueve métodos, el factor 1,2 es el modelo con kh·1,2;
  - con Ky, nota y kh intacto;
  - kh·f fuera de rango se rechaza;
  - los presets llevan 1.
- **Regla 7 y el diálogo:** las tres opciones mueven el número, y el diálogo
  las escribe.

**Discriminación** contra `git archive` a29c097 (0.1.244), con el runner de ese
árbol: **14 de 14 fallan**, 10 por comportamiento y 4 por símbolo.

## 4. El banco, y el cierre de D226

- **Censo:** 0 de 230 modelos con norma.
- **A/B árbol contra árbol de todo el 02**
  (`_auditoria/P4_0245/ab_d226d.py`): 194 modelos, **0 de 1821 números
  distintos**. Los 21 con soporte pasan por la σ′v de la adherencia.
- **`d226()`, CUBIERTO POR TEST.** Comprueba en vivo:
  - el Tutorial 21: F 1,36028, DA1-C1 por dovela 1,20419 y DA1-C2 1,08822,
    frente a 1,37, 1,207 y 1,096, a menos del 1 %;
  - las identidades de las cuatro versiones: F/1,35 y F/1,485 con cu, la carga
    que resiste fuera, Γ = F con Ru y c′ = 0, y γγ dividiendo.

  Comprueba además el censo, los tres A/B árbol contra árbol (13, 194 y 194
  modelos, iguales) y las cuatro discriminaciones. Contra el motor de 0.1.244
  dice NO SE SOSTIENE, por γγ.
- **D226 se retira al índice.** La cadena P4 queda con D229 → D230 → D231.
- **Ciclo de cierre:**
  - `verificar_cierres.py` entero: 215 cierres (D226 nuevo) y 0 bajadas;
  - instantánea `Evaluaciones/0.1.245`;
  - `retirar_cerrados.py --escribir D226`: la sección queda en la historia de
    la instantánea y el renglón del índice cita 0.1.245;
  - D226 podada de `PAQUETES` y tachada en la cadena P4;
  - prompts regenerados (43);
  - auditorías de invariantes con 0 ERROR en el 02 y en la raíz;
  - instantánea rehecha con `--forzar`;
  - `--seco` completo después de retirar.

## 5. Lo que se reporta y NO se corrige

Lo declarado en las cuatro versiones sigue siendo cierto:

- **El desembalse con Ru y norma** lee su u inicial sin el factor (0.1.244).
- **Una carga que cruza el punto bajo** lleva un solo factor (0.1.243).
- **La copia de análisis pasa por el formato de archivo**, que guarda la
  filtración con 9 cifras (0.1.242; ya reportado en 0.1.194).

## 6. Verificación

- **Suite entera:** 5443 de 5443, en 54,6 min. La primera corrida se cortó
  a mitad por un reinicio del equipo (3398 casos en verde hasta ahí) y se
  repitió entera.
- **Selección** de normas, m2, soportes, adherencia, arrancamiento, anclajes
  helicoidales, Ito-Matsui, σ′v, sismo, API de ajustes, acciones de las
  cargas, presiones, Tutorial 21 e i18n: 792 de 792 en 42 archivos.
- **Test nuevo:** 14 de 14. Discriminación: 14 de 14 contra 0.1.244.
- **Banco:** censo, A/B (0 de 1821), `d226()` CUBIERTO POR TEST y el ciclo
  de cierre con D226 retirada (215 cierres, 0 bajadas).

**Qué falta por probar:**
- **Un anclaje real del banco con norma:** ningún modelo la usa.
- **El factor sísmico en un caso publicado.**
