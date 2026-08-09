# Auditoría de Project Settings — v0.1.74

Inventario de los ajustes de **Project Settings**, contrastado con la
documentación de referencia de `docs/reference/`, y —lo que motivó la
auditoría— **qué ajustes llegan de verdad al cálculo**.

> Sin marcas comerciales, según la regla de `docs/reference/`: las
> fórmulas se citan por su fuente científica y el software de referencia
> se menciona solo como «la referencia».

---

## 1. El resultado que motivó todo

Antes de v0.1.74, **diez controles se guardaban, se editaban desde la
interfaz, se serializaban en el `.ogr` y no los leía nadie**:

| Ajuste | Página | Estado antes |
|---|---|---|
| `check_tensile_stresses` | Advanced | sin cablear |
| `min_initial_fs` | Advanced | sin cablear |
| `min_lambda` / `max_lambda` | Advanced | sin cablear |
| `iterate_steffensen` | Advanced | sin cablear |
| `methods.tolerance` | Methods | sin cablear |
| `methods.max_iterations` | Methods | sin cablear |
| `random_numbers.method` | Random Numbers | sin cablear |
| `random_numbers.seed` | Random Numbers | sin cablear |
| `random_numbers.lhs_correlate` | Random Numbers | sin cablear |
| `groundwater.excess_pore_pressure` | Groundwater | sin motor |

La página **Advanced entera** y la página **Random Numbers entera** eran
decorativas. Es el mismo fallo que los coeficientes parciales de la norma
de diseño entre v0.1.52 y v0.1.57, que es el motivo por el que existe la
regla 7 — repetido a mayor escala y durante más tiempo.

Nueve de los diez están cableados en v0.1.74. El décimo,
`excess_pore_pressure`, no tiene motor y se aborda en v0.1.75.

---

## 2. Página por página

### General

| Nuestro | Referencia | Estado |
|---|---|---|
| Sistema de unidades (6 sistemas detallados) | Stress Units (métrico / imperial) | **Superconjunto** deliberado |
| Time Units | igual | Solo afecta con filtración FE, como en la referencia |
| Permeability Units | igual | Idem |
| Failure Direction | igual, con icono | Cableado en **v0.1.73** |
| Max Materials / Max Supports | un solo *Maximum Number of Properties* | **Divergencia deliberada**: la referencia gobierna materiales y sostenimientos con un número; nosotros los separamos |
| — | **Data Output** (Standard / Maximum) | **Nos falta** → backlog |

### Methods

| Nuestro | Referencia | Estado |
|---|---|---|
| 9 casillas de método | 9 métodos | 6 implementados; Corps #1, Corps #2 y Lowe-Karafiath deshabilitados con tooltip |
| Number of slices | igual | Cableado desde siempre |
| Tolerance | igual | **Cableado en v0.1.74** |
| Maximum iterations | igual | **Cableado en v0.1.74** |
| Interslice force function | igual, con editor gráfico | **Añadido en v0.1.74** (4 formas con nombre). Sin editor gráfico ni import `.FN1` → backlog |

### Groundwater

| Nuestro | Referencia | Estado |
|---|---|---|
| Method (9 valores) | Method (6 valores) | Superconjunto |
| Pore Fluid Unit Weight | igual | Cableado |
| **Default Hu / Auto Hu** a nivel de proyecto | Hu es **por material** | **Divergencia**: nosotros tenemos ambos niveles; el del material manda |
| Advanced: 3 opciones excluyentes | igual | **v0.1.74**: pasan de casillas a radios, así que la exclusividad es visible en vez de imponerse por detrás |
| Drawdown method (4 procedimientos) | dentro de la opción avanzada | Equivalente |
| — | **Interpolation Method** para rejillas | **Nos falta** → backlog |
| — | **FEA Options** de régimen permanente | **Nos falta** → backlog |

### Transient

| Nuestro | Referencia | Estado |
|---|---|---|
| Tolerance, Max iterations, Time steps | igual | Cableado |
| Nº de etapas (informativo) | tabla editable con *Define by Date* | La tabla se edita en Groundwater → Transient; sin columna de fecha → backlog |
| Puerta de la página | deshabilitada hasta activar el transitorio | **Añadida en v0.1.74** |

### Statistics

Todo cableado desde v0.1.38. `seed` deja de ser el punto de decisión y
pasa a ser un **override explícito** (§3).

### Random Numbers

| Nuestro | Referencia | Estado |
|---|---|---|
| Pseudo-random / Random | igual | **Cableado en v0.1.74** |
| Seed | igual | **Cableado en v0.1.74** |
| `lhs_correlate` | opción separada | **Cableado en v0.1.74** |
| — | Number Generator (Park-Miller / Rand) | **Divergencia deliberada**: usamos el Mersenne Twister de la biblioteca estándar, mejor que ambos. Ofrecer generadores peores por paridad no tiene sentido |

### Design Standard

Cableado desde v0.1.57 y correcto. Faltan respecto de la referencia:
**BS 8006:1995**, y las normas **con nombre**, importables y exportables
→ backlog.

### Advanced

| Nuestro | Referencia | Estado |
|---|---|---|
| Tensile stress check | igual, **desactivado por defecto** | **Cableado en v0.1.74**, y el defecto corregido (§4) |
| Percentage of slices | igual (95 %) | **Añadido en v0.1.74** |
| Steffensen | igual | **Cableado en v0.1.74** |
| Initial factor of safety | igual | **Cableado y renombrado** en v0.1.74 |
| Min / Max lambda | agrupados en *Iteration Parameters* | **Cableado en v0.1.74**, y los defectos corregidos (§4) |
| `check_m_alpha` | ofrecido | **Excluido a propósito**: rechaza el círculo crítico validado contra la referencia, así que es un diagnóstico y no un criterio de validez. Vive en las opciones de búsqueda, y la página lo explica |
| — | Apply support forces to interslice boundaries | **Nos falta** → backlog |
| — | Discard surfaces with FS above / below | **Nos falta** → backlog |

### Project Summary

Equivalente. `date_created` existe en el modelo y no tiene widget.

---

## 3. Había dos semillas

El modelo llevaba **dos** semillas:

- `RandomNumberSettings.seed`, con una página entera para ella, que **no
  leía nadie**;
- `StatisticsSettings.seed`, **sin ningún widget**, que era la que el
  análisis usaba de verdad.

Además, ninguna de las cuatro búsquedas aleatorias recibía semilla: cada
una llevaba su propio valor arbitrario (42 en una, 1234 en otra, `None`
en dos más). La página prometía que una ejecución pseudoaleatoria «da
exactamente los mismos resultados», y para las búsquedas eso era
sencillamente falso.

`ProjectSettings.analysis_seed()` es ahora la única respuesta. La página
Random Numbers decide; `statistics.seed` se conserva como **override
explícito**, porque honrar un valor que alguien escribió a propósito
cuesta menos que sorprenderle.

---

## 4. Dos valores por defecto que estaban mal *porque* nunca se aplicaron

Este es el hallazgo que conviene recordar: **un ajuste que no hace nada
tampoco tiene forma de estar bien**. Nadie revisa el valor por defecto de
un control que no cambia nada.

1. **`check_tensile_stresses` estaba en `True`** y la referencia tiene la
   comprobación **desactivada**. Cablearlo tal cual habría activado el
   rechazo por tracción en todo proyecto guardado, como efecto colateral.

2. **`min_lambda` / `max_lambda` valían ±1.25** mientras la rejilla λ que
   Spencer y GLE recorren es ±1.5. Medido, no supuesto: en el círculo de
   referencia validado, **GLE converge en λ = 1.4919**, fuera de ±1.25.
   Honrar el rango almacenado habría recortado la búsqueda por debajo de
   lo que un caso validado necesita.

Ambos se migran al leer el fichero, y la migración es **condicional al
valor antiguo**: quien escribió deliberadamente otra cosa la conserva,
porque a partir de v0.1.74 significa algo.

---

## 5. Backlog razonado

Lo que la referencia tiene y nosotros no, en orden de utilidad estimada:

1. **Data Output (Standard / Maximum)** — decide cuántos datos por
   superficie se guardan. Afecta al tamaño de archivo y al tiempo, no al
   resultado.
2. **Editor gráfico de la función entre dovelas** + import/export `.FN1`.
   Las cuatro formas con nombre ya cubren el uso corriente.
3. **Interpolation Method** para rejillas de presión (TIN, Chugh,
   thin-plate spline…). Hoy usamos una sola.
4. **FEA Options de régimen permanente**, separadas de las transitorias.
5. **BS 8006:1995** y normas de diseño con nombre, importables y
   exportables.
6. **Apply support forces to interslice boundaries**.
7. **Discard surfaces with FS above / below**.
8. **Defaults como «guardar como valor por defecto»**: el botón de la
   referencia guarda la configuración actual para los ficheros nuevos; el
   nuestro restaura los valores de fábrica. Son cosas distintas y ahora
   mismo solo tenemos la segunda.
9. **`ogr_cli` no aplica el descenso rápido** — anotado en v0.1.72, sigue
   pendiente.

---

## 6. Ajustes que siguen sin llegar al cálculo

Uno, y con fecha:

- **`groundwater.excess_pore_pressure`**. Solo bloquea interfaz; ningún
  módulo de cálculo lo lee. Es una **feature**, no un cableado: necesita
  Δσv por dovela, campos nuevos en materiales y cargas, y validación
  externa. Va en **v0.1.75**.

© 2026 Samuel Sáez López — UPCT — AGPL-3.0-or-later
