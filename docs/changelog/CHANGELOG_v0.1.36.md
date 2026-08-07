# OGR Suite v0.1.36 — Changelog

**Lanzamiento:** 2 de agosto de 2026
**Desarrollador:** Samuel Sáez López — Estudiante de Doctorado, UPCT
**Licencia:** GPL-3.0

> **Fase P4: análisis de sensibilidad.** Identifica qué parámetros de
> entrada gobiernan realmente la estabilidad del talud, variando cada uno
> a lo largo de su rango mientras los demás permanecen en su media.

---

## 🆕 `ogr_core/statistics/sensitivity.py`

Fiel a la especificación de la referencia:

- el rango entre el mínimo y el máximo **reales** (derivados de los
  valores *relativos*: `media − rel_min` a `media + rel_max`) se divide
  en **50 intervalos iguales**, evaluándose 51 valores;
- el factor de seguridad se recalcula sobre la **superficie de mínimo
  global**;
- mientras se barre una variable, **todas las demás se mantienen en su
  valor medio (determinista)**;
- se repite para cada variable seleccionada, **de una en una**, aunque se
  hayan seleccionado varias.

Un análisis de sensibilidad **no** es un análisis probabilístico: solo se
usan el mínimo y el máximo, la forma de la distribución no interviene y
no se obtiene ninguna probabilidad de fallo.

### Añadidos sobre la especificación

Dos conveniencias que hacen los resultados directamente utilizables:

- **Porcentaje de rango** como eje x, que es como se comparan en una
  misma gráfica variables con unidades distintas.
- **Cruce con un factor objetivo**: el valor del parámetro en el que el
  talud alcanza el umbral de diseño (FS = 1 por defecto), por
  interpolación lineal.

Y **`ranking()`**, que ordena las variables de más a menos influyente por
el rango de factor de seguridad que producen.

## ✔️ Validación

Caso de referencia (determinista FoS = 0.8955), 4 variables × 51 puntos
en 0.4 s:

| Variable | Rango FoS | Sentido | FS = 1 en |
|---|---|---|---|
| Ángulo de rozamiento Mat1 | **0.5451** | creciente | 28.78° |
| Cohesión Mat1 | 0.4080 | creciente | 20.13 kPa |
| Coeficiente sísmico kh | 0.2261 | decreciente | nunca |
| Peso específico Mat1 | 0.0940 | decreciente | nunca |

Todos los sentidos son físicamente correctos y el orden de influencia es
el esperado: los parámetros de resistencia dominan sobre el peso
específico.

### La comprobación decisiva

Cuando la variable barrida pasa por **su propia media**, el modelo vuelve
a su estado determinista, así que el factor de seguridad calculado debe
**coincidir con el determinista**. Cualquier fuga entre barridos rompería
esa identidad. Hay un test que lo verifica con una sola variable y otro
que lo verifica con **tres variables seleccionadas a la vez**, que es
donde una implementación descuidada fallaría.

## 📊 Tests

**688 tests, 688 verdes** (+23 desde v0.1.35; suite 100 % desde v0.1.21).

Cobertura: 50 intervalos por defecto y número configurable; rango
derivado de los límites relativos, incluidos asimétricos; espaciado
uniforme; **identidad con el determinista en el punto medio**, con una y
con varias variables; proyecto sin modificar (comparación de la
serialización completa); sentidos físicos de cohesión, rozamiento y
sísmico, y monotonía de la respuesta a la resistencia; ranking ordenado y
coherente con el rango de FoS; porcentaje de rango de 0 a 100 y monótono;
cruce que efectivamente encierra FS = 1 y `None` cuando no se alcanza;
varios métodos a la vez; y errores (sin rango, sin determinista, progreso
completado, barrido vacío seguro).

## ⏳ Siguiente

**Fase P3 — Overall Slope**: repetición de la búsqueda completa N veces,
una por muestra, agrupando los distintos mínimos globales y determinando
la **superficie probabilística crítica** (la de máxima probabilidad de
fallo, que no tiene por qué coincidir con la crítica determinista).
Después P5 (interfaz).

---

© 2026 Samuel Sáez López — UPCT — GPL-3.0
