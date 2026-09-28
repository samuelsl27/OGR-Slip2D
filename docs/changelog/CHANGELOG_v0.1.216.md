# OGR Slip2D v0.1.216

Segunda de las tres versiones que cierran el paquete P4 del banco de
verificación. Tres cambios de motor, decididos **después de medir** (punto de
parada de la propietaria, 2026-09-28):

- **D196 — `base_normal_force` es la normal del equilibrio propio del método,
  soporte incluido, también en Bishop y en los dos Janbu.** Es la que leen los
  chequeos desde 0.1.210; la columna la dejaba fuera. Posproceso: no mueve
  ningún factor fuera del desembalse.
- **D197 — el Ordinario publica su propia normal, `N′ + u·l + T_N` (forma C-12),
  y no la N sin corregir.** El desembalse multietapa la lee, así que el
  Ordinario dentro del desembalse sí se mueve: en el 097 del banco pasa de
  0,627677 a 0,805392 y en el 098 de 0,77765 a 0,821665. Ninguna de las dos
  filas tiene valor publicado.
- **D198 — en el Ordinario la fuerza normal del soporte entra en la normal
  efectiva antes del recorte y de linealizar.** Un soporte que levanta la base
  ya no baja la resistencia de `c·l`. Sin movimiento en el banco.

Se abre **D212**, reportada y no corregida: la marcha de fuerzas entre dovelas no
lleva el soporte (sección 3).

Lo que cambia en el banco de verificación (`_tools/`, `_auditoria/`, fichas)
está fuera de git.

---

## 0. Cómo se decidió

La propietaria pidió medir antes de decidir qué es la columna. La fase A se hizo
con los tres interruptores ya escritos y un censo nuevo del banco
(`_tools/censo_p4_0216.py`), que **no escribe ningún `.ogr` ni ningún
`resultados*.json`**:

- las superficies archivadas de Bishop, Janbu, Janbu corregido y el Ordinario
  de los 194 modelos, con cada interruptor apagado y encendido por separado;
- las búsquedas enteras del 059, 060, 097 y 098 **en serie**, con
  `parallel_search = False`, para que el interruptor en memoria llegue a todos
  los círculos (en paralelo los procesos hijos no lo heredan, y el resultado
  en serie es el mismo byte a byte). Así el A/B no tuvo que parchear el motor
  en disco;
- el círculo dado del Apéndice G del EM 1110-2-1902 con el Ordinario, Bishop y
  los dos Janbu, sin refuerzo y con un clavo, porque el banco no tiene ningún
  desembalse con refuerzo.

| | resultado |
|---|---|
| D196, 332 superficies de Bishop/Janbu | 0 factores; 41 columnas y 12 `sigma_n_max` (049, 059, 085, 086, 092), ninguno con publicado |
| D196, Apéndice G con clavo | Bishop y los Janbu +0,45 a +0,66 %; sin clavo, bit a bit igual |
| D197, Apéndice G, Ordinario | Corps 2 etapas 1,1456 → 1,2357; Duncan-Wright 1,1098 → 1,2799 (publicado, con otros métodos, 1,35 y 1,44) |
| D197, búsquedas | 097: 0,627677 → 0,805392 (+28,3 %; Bishop 0,818); 098: 0,77765 → 0,821665 (+5,7 %; Bishop 0,893) |
| D198, 059 y 060 | 0 filas; el 059 cambia 1,5·10⁻¹³ |
| identidad columna = chequeo, lado encendido | 100 % de las filas |

**Decisiones.**

- **La columna**: la normal propia con soporte, en los nueve métodos
  (propietaria).
- **El desembalse del Ordinario lee C-12**: la propietaria pidió decidirlo con
  fundamento. El estado de la etapa 1 es UNA solución. Duncan, Wright & Brandon
  (2014) escriben su cortante como `(c′ + σ′_fc·tan φ′)/F` (Ec. 9.3) o como la
  cortante movilizada `S/Δℓ` de esa misma solución (Ec. 9.4), con
  `σ′_fc = N/Δℓ − u` (Ec. 9.2). Las dos coinciden solo si N es la normal con la
  que el método construyó su resistencia. El Ordinario la construye con
  `N′ = W cos α − u·l·cos²α` (EM C-12; DW&B Ec. 6.59, «the preferred
  equation»), así que su normal total es `N′ + u·l`. Leer la N sin corregir
  daba la forma C-13, que los dos textos desaconsejan porque produce tensiones
  efectivas irreales o negativas. El test nuevo fija esa coherencia dovela a
  dovela.

## 1. Los tres arreglos (motor)

Cada uno con su interruptor de módulo, todos encendidos. La tabla
`INTERRUPTORES` del banco pasa a 20:

- `methods.bishop.SUPPORT_IN_PUBLISHED_NORMAL` (D196):
  `base_forces_no_interslice_shear` recibe la lista `sigma_support_load` de la
  última pasada del método. No se recalcula, porque la carga pasiva depende de
  F. La lista entra en la estimación de σ y en N; la columna motora sigue con
  el peso del suelo.
- `methods.ordinary.PUBLISH_OWN_NORMAL` (D197): solo cambia lo **publicado**.
  En el camino general la lista `normals` es también la normal cuyo momento
  toma `moment_terms`, así que esa lista no se toca. Un test comprueba que el
  factor no se mueve ni en el círculo ni en una poligonal mojada. Esa era la
  trampa.
- `methods.ordinary.SUPPORT_IN_EFFECTIVE_NORMAL` (D198): `n_eff = N′ + T_N`,
  `σ′ = max(0, n_eff)/l`, y `(c, tan φ)` se leen ahí. Desaparece el
  `+ T_N·tan φ` suelto. El contador `negative_effective_normal` y
  `_zero_strength` miran `n_eff`. Ni el EM ni DW&B presentan el Ordinario con
  refuerzo (DW&B, p. 93: «not presented here»); la forma sale de la misma
  derivación que ya citaba el código («N = W·cos α + T_N is exact»).

Docstrings al día en `checks.py`, `bishop.py` y `rapid_drawdown._stage1_state`
(el porqué de C-12 en la etapa 1).

## 2. Tests

- `test_published_normal_v1216.py`, 12 casos:
  - columna = chequeo en los nueve métodos, clavo activo y pasivo,
    Mohr-Coulomb y curva de potencia, círculo y poligonal;
  - el Ordinario reproduce la «Base Normal Stress» publicada de Ej_2 desde la
    columna (antes 47,75 kPa fuera) y la σ′ publicada a través de la tabla de
    la interpretación;
  - en la etapa 1 del desembalse, `τ_fc = S/(l·F)` dovela a dovela (DW&B Ec.
    9.3 = 9.4);
  - regla 7: el interruptor de D196 mueve la N de la dovela cruzada (6,686 →
    15,607 kN/m) y el de D197 el factor del desembalse del Apéndice G;
  - ningún factor se mueve fuera del desembalse; sin soporte, la columna de
    Bishop y Janbu es bit a bit la de antes.
- `test_ordinary_support_v1216.py`, 9 casos, con el clavo de v0.1.137 como
  testigo en dos variantes:
  - a 90° en seco levanta la base (N′ = 4,17, T_N = −18,71);
  - a 0° con ru = 1,3 la saca de la tracción (N′ = −1,25, T_N = +23,45).

  En las dos ramas se comprueba:
  - la resistencia escrita a mano desde `resolve_support_terms`, con
    Mohr-Coulomb y con curva de potencia;
  - que un soporte que levanta no baja de `c·l`;
  - el contador;
  - sin soporte, bit a bit igual;
  - el interruptor mueve el factor.
- `test_own_base_stress_v1210.py`: el caso que saltaba las dovelas con N′ < 0
  «por D198» las comprueba ahora todas, con la razón escrita.

**Contra 0.1.215 fallan 13 de los 21 casos nuevos, todos por comportamiento**,
medido copiándolos a un árbol de fbc5d67 extraído con `git archive`:

- D198: 6 de 9;
- D196/D197: 7 de 12.

Pasan allí las guardas y los controles de «nada más se mueve».

## 3. Lo que se reporta y NO se corrige (regla 6)

- **D212 — la marcha de fuerzas entre dovelas (`postprocess._march`) no lleva
  el soporte.** Hasta 0.1.215 su N coincidía con la columna de Bishop y Janbu
  porque las dos lo dejaban fuera, y las dos se separaban del equilibrio del
  método. Ahora la columna lo lleva y la marcha no: en la dovela cruzada por el
  clavo, 6,686 frente a 15,607 kN/m (Bishop) y 6,565 frente a 15,381 (Janbu).
  La identidad de D173 (A4, «la N de la marcha es la columna a 1e-9») solo está
  probada sin soporte, y sin soporte sigue valiendo.
- **Los `sigma_n_max` archivados** del 049, 059, 085, 086 y 092 (Bishop/Janbu con
  soporte) y del 051, 052, 057, 059, 100 y 101 (Ordinario con agua) son de la
  columna vieja. Ninguno se compara con un publicado (la comparativa solo los
  usa en el 44, 45 y 61, que no se mueven). Se renuevan cuando esos modelos se
  vuelvan a correr.
- De paso, visto al leer el 060: su crítica es un círculo casi tangente al
  suelo, donde el Ordinario coincide con Bishop (1,583108 los dos, frente a
  0,997 publicado para el Ordinario). La diferencia con el publicado es
  anterior y no es de esta tanda.

## 4. Verificación

- Suite entera: **4819 de 4819** (30 min 31 s).
- Selección dirigida antes de escribir los tests (desembalse, soporte,
  Ordinario, columnas de Bishop, marcha con agua, validación de los ejemplos):
  587 de 587 con los tres interruptores.
- Banco, después del commit: el 097 y el 098 re-corridos con 0.1.216, el
  censo repetido con la versión publicada, y los cierres `d196()`, `d197()`
  y `d198()`.
