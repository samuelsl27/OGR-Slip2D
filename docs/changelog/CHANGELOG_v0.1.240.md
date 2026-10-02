# OGR Slip2D v0.1.240

**D90: la pared de una grieta de tracción se deduce del modelo con que se
rebana, no se guarda ni se arrastra.** El rebanador aceptaba la pared que una
superficie ya traía con solo que su abscisa coincidiera con la coronación, sin
mirar la grieta ni el terreno actuales. Una superficie rebanada en un modelo y
vuelta a rebanar tras editar la grieta o el terreno conservaba la pared vieja
y su empuje, del lado inseguro. Ahora la pared que trae solo vale si es la del
modelo actual. Y, como decidió la propietaria tras pedir que se razonara, la
pared no se serializa: es un dato derivado.

Última versión de la segunda parte de la tanda P5.

## 0. Lo que se encontró, y dónde

### La premisa de la ficha no se sostiene desde 0.1.208

El prompt pedía serializar `tension_crack_wall` porque una crítica poligonal
con grieta llena volvía del ida y vuelta `to_dict`/`from_dict` sin su pared.
Desde 0.1.208, D189 (`CRACK_WALL_ON_LINE`) deduce la pared de una coronación
que llega sobre la línea de la grieta. Medido con 0.1.239 sobre el talud φ = 0
de `test_tension_crack_truncation_v1109` (caja de 0 a 100 por 0 a 40, grieta
horizontal llena de agua), la poligonal de 60 cuerdas del círculo del fixture,
Bishop a 1e-10 y 60 dovelas:

| Caso | Pared | Empuje (kN/m) | F | Diferencia |
|---|---|---|---|---|
| poligonal evaluada en sitio, grieta en y = 34 | (79,08; 34; 40) | 176,58 | 0,975074 | — |
| ida y vuelta | la misma, deducida otra vez | 176,58 | 0,975074 | 0 % |
| ida y vuelta con `CRACK_WALL_ON_LINE` apagado | ninguna | 0 | 1,053427 | +8,04 % |

### Lo que sí estaba vivo: la pared arrastrada

| Caso | Pared | Empuje | F | Diferencia |
|---|---|---|---|---|
| grieta bajada a y = 32: la MISMA poligonal ya cortada en 34, re-rebanada | (79,08; 34; 40), la vieja | 176,58 | 0,975074 | **+1,19 %**, inseguro |
| grieta bajada a y = 32: evaluada de nuevo | (76,90; 32; 40) | 313,92 | 0,963586 | — |
| meseta subida a y = 41: la poligonal ya cortada, re-rebanada | (79,08; 34; 40), la vieja | 176,58 | 0,903066 | **+2,39 %**, inseguro |
| meseta subida a y = 41: evaluada de nuevo | (79,08; 34; 41) | 240,35 | 0,881964 | — |

Lo alcanza la API pública (`slice_surface`, y `python_exec` del MCP). Ningún
camino del programa: Interpret no vuelve a rebanar, las variables aleatorias
no mueven ni la grieta ni el terreno, y las búsquedas crean superficies
nuevas.

### Por qué no se serializa

La pared es la cara vertical de la masa en su coronación, desde la línea de
la grieta hasta el terreno, y el agua de la grieta la empuja con ½·γw·h²
(Terzaghi 1943; Duncan, Wright y Brandon 2014, *Soil Strength and Slope
Stability*, 2.ª ed., §14.3.2, ec. 14.4). Matemáticamente es una función de
(superficie, grieta, terreno): W = (x_c, y_grieta(x_c), y_terreno(x_c)).

Guardarla junto a la superficie sería guardar un valor derivado:
- **redundante** mientras el modelo no cambia: el ida y vuelta de doubles por
  JSON es exacto y D189 la deduce de nuevo, con el mismo factor;
- **falso** en cuanto cambia: grieta o terreno editados, o, en la referencia,
  la posición y el agua de la grieta como variables aleatorias de cada
  muestra.

Serializarla crearía dos fuentes para un mismo dato, y en la vuelta temprana
del rebanador ganaba la vieja. Por eso la decisión es atar esa vuelta al
modelo y no guardar nada.

## 1. El motor

- **`slicer._wall_is_the_models(project, tc, ground, wall)`** responde si la
  base de la pared está sobre la línea de la grieta, y su techo sobre el
  terreno, en su abscisa, a la tolerancia geométrica del modelo
  (`_model_grid_tol`).
- **La vuelta temprana de `apply_tension_crack_truncation`** solo acepta la
  pared que el objeto trae si pasa esa prueba. Si no, la olvida (también del
  dibujo, `tension_cracks`) y decide la regla general como para cualquier
  superficie: truncar en la grieta actual, pared sobre la línea o nada. En un
  modelo sin cambios, la pared que trae pasa siempre: la misma aritmética da
  los mismos números.
- **`SlipSurface.to_dict` y `CompositeSurface.to_dict`** dicen en su
  docstring por qué no llevan la pared.
- **Sin interruptor:** el A/B del banco no mueve nada (más abajo).

## 2. La interfaz

Nada. Interpret dibuja la pared que trae el resultado y no vuelve a rebanar.

## 3. Tests

**`tests/test_tension_crack_wall_roundtrip_v1240.py`**, 9 casos:

- ningún `to_dict` de los cuatro tipos lleva la pared;
- la poligonal reconstruida la obtiene del modelo, con el mismo factor
  (1e-12);
- de punta a punta por `run_global_minimum`: con una variable que no mueve
  el talud (la cohesión de un material que ninguna región usa), cada muestra
  da el factor determinista a 1e-12; con `CRACK_WALL_ON_LINE` apagado, pierde
  el empuje del lado inseguro (regla 7);
- la pared arrastrada no decide: con la grieta bajada y con el terreno
  subido, la superficie ya cortada recibe la pared del modelo nuevo y el
  factor de la misma superficie evaluada de nuevo, y la pared vieja sale del
  dibujo;
- la prueba de la pared, por separado;
- en un modelo sin cambios, la misma pared, el mismo factor y una sola pared
  dibujada.

El test es autosuficiente (no importa el de v1208), para poder correrlo en
árboles anteriores.

**Discriminación**, con el runner de cada árbol:
- contra `git archive` fdf82ab (0.1.239): **4 de 9 fallan**, tres por
  comportamiento (las dos paredes arrastradas y la pared vieja que se seguía
  dibujando) y una por símbolo. Pasan los cinco controles, que D189 ya hizo
  ciertos en 0.1.208;
- contra 365d79b (0.1.207): **6 de 9**. Además fallan la reconstrucción
  estadística, cuyas muestras daban 1,0535 frente al determinista 0,9750, y
  el ida y vuelta.

## 4. El banco

- **A/B** (`_auditoria/P5_0240/ab_d90.py`, con la maquinaria de
  `ab_pared_grieta_d189.py`), espalda con espalda en el mismo proceso: la
  regla nueva, la vieja (la prueba sustituida por una que siempre dice que
  sí) y la nueva como control. Sobre los **19 modelos del banco con grieta**,
  **205 comparaciones**: 80 círculos publicados como los evalúa el banco, 45
  con su masa nombrada y 80 críticas archivadas reconstruidas como las
  reconstruye el probabilístico. **0 movidas** y los controles iguales. La
  vuelta temprana solo la alcanza un objeto que se vuelve a rebanar, y en el
  banco nunca cambia de modelo entre las dos pasadas.
- No hace falta re-correr nada: los modelos sin grieta no llegan a ese
  código, y los que la tienen no se mueven.
- **Cierre: `d90()`, CUBIERTO POR TEST.** El criterio del prompt
  (serializar la pared y un `grep` de cuatro líneas) no aplica, porque se
  decidió no serializar. Comprueba:
  - en vivo, sobre el talud φ = 0 escrito dentro del cierre: ningún
    `to_dict` lleva la pared; el ida y vuelta da la misma pared y el mismo
    factor; la pared arrastrada (grieta a 32, meseta a 41) da lo mismo que
    evaluar de nuevo;
  - que `d13()` sigue en SE SOSTIENE;
  - el A/B archivado;
  - las dos discriminaciones.

  D90 se retira al índice.

## 5. Lo que se reporta y NO se corrige

- **Sin número:** OGR no tiene la posición ni el agua de la grieta como
  variables aleatorias. `VariableKind` cubre resistencia, material,
  hidráulica, soporte, cargas, sismo y nivel freático. Con el modo «nivel
  freático» el agua de la grieta sí cambia con la muestra, y se calcula bien
  porque el empuje se evalúa en cada rebanado. Si algún día se añade la
  posición aleatoria, la semilla poligonal no bastará, porque se guarda ya
  truncada: habrá que sembrar la superficie sin truncar.

## 6. Verificación

- **Suite entera:** 5353 de 5353, en 43 min, sin nada en paralelo.
- **Selección** de grietas, superficies, estadística, rebanador,
  sensibilidad, la sonda de D88, el cambio de masa de D89, Interpret y
  versiones: 486 de 486 en 27 archivos.
- **Discriminación:** 4 de 9 contra 0.1.239 y 6 de 9 contra 0.1.207.
- **Banco:** el A/B de los 19 modelos con grieta (0 movidas en 205
  comparaciones) y `d90()` CUBIERTO POR TEST. Ciclo de cierre:
  - `verificar_cierres.py` entero: 213 cierres y 0 bajadas;
  - instantánea `Evaluaciones/0.1.240`;
  - D90 retirada, podada de `PAQUETES` y tachada en la cadena P5;
  - prompts regenerados (44);
  - auditorías de invariantes con 0 ERROR en el 02 y en la raíz;
  - instantánea rehecha con `--forzar`;
  - `--seco` completo sin ningún NO SE SOSTIENE ni PENDIENTE DE CORRIDA.

**Qué falta por probar:**
- **Un caso publicado con grieta llena y crítica poligonal:** el banco no
  tiene ninguno. El efecto está medido en el talud sintético del test.
