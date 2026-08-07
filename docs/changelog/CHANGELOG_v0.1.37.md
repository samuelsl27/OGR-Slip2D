# OGR Suite v0.1.37 — Changelog

**Lanzamiento:** 2 de agosto de 2026
**Desarrollador:** Samuel Sáez López — Estudiante de Doctorado, UPCT
**Licencia:** GPL-3.0

> **Fase P3: análisis Overall Slope y superficie probabilística
> crítica.** Con esto el **motor probabilístico queda completo**: solo
> falta la interfaz (P5) para cerrar el módulo.

---

## 🆕 Overall Slope

La **búsqueda completa se repite N veces**, cargando una muestra distinta
de las variables aleatorias en cada iteración, de modo que **no se supone
fija la posición del mínimo global** — que es precisamente lo que
distingue este tipo de análisis del Global Minimum, y lo que la
referencia describe como «un enfoque más racional».

La probabilidad de fallo mantiene la **misma definición**: número de
análisis con FS < 1 dividido entre el número de muestras.

La referencia advierte que este tipo es **sustancialmente más caro** (una
búsqueda completa por muestra, con corridas que pueden durar horas), así
que el motor acepta un `search_factory` que construye la búsqueda ya
configurada, informa del progreso muestra a muestra y contabiliza —sin
abortar— las búsquedas que fallen.

## 🎯 Superficie probabilística crítica

La superficie individual con **máxima probabilidad de fallo** (y por
tanto mínimo índice de fiabilidad). Como subraya la referencia, **no
tiene por qué coincidir con la crítica determinista**.

Para calcularla hay que seguir cada superficie *a través de las
muestras*: se acumulan estadísticos por superficie usando una clave
geométrica cuantizada, de forma que la misma candidata generada en
iteraciones distintas se agrupe (una búsqueda en malla regenera el mismo
conjunto de círculos cada vez, así que la agrupación es exacta; la
tolerancia cubre además búsquedas aleatorias).

**Filtro `min_evaluations`**: solo compiten las superficies evaluadas un
número mínimo de veces, de modo que una superficie vista una sola vez no
pueda ganar el título por una única muestra desafortunada.

## ✔️ Validación

Caso de referencia, 40 muestras LHS con c y φ de dispersión amplia
(4.5 s):

| | |
|---|---|
| Media FoS | 0.8948 |
| Desviación | 0.1605 |
| Probabilidad de fallo | 0.775 |
| Índice de fiabilidad | −0.655 |
| **Mínimos globales distintos** | **3** |
| Superficies seguidas | 139 |
| Superficie probabilística crítica | PF = 0.775, fue mínimo global 27 de 40 veces |

Que aparezcan **tres localizaciones distintas** del mínimo global es
exactamente el fenómeno que este tipo de análisis existe para capturar.

### Un invariante físico entre los dos tipos de análisis

Rebuscar en cada muestra solo puede encontrar una superficie **igual o
más crítica** que reutilizar la determinista. Por tanto la media de
Overall Slope **no puede superar** la de Global Minimum, y su
probabilidad de fallo no puede ser menor. Ambas desigualdades se
comprueban en tests, y atraparían una búsqueda que silenciosamente no se
estuviera re-ejecutando.

## 📊 Tests

**710 tests, 710 verdes** (+22 desde v0.1.36; suite 100 % desde v0.1.21).

Cobertura: estadísticos y tipo de análisis registrados; PF como fracción
contada e índice de fiabilidad por fórmula; proyecto sin modificar;
**los dos invariantes frente a Global Minimum**; varios mínimos distintos
con variables amplias y uno solo con variables estrechas; identificación
de la superficie probabilística crítica, filtro por número mínimo de
evaluaciones, umbral imposible que no devuelve superficie, recuento de
veces que fue mínimo global y número de superficies seguidas; campos del
resumen; y errores (sin variables, sin método, progreso completado y
**búsquedas que lanzan excepción contabilizadas sin abortar la corrida**).

## 🏁 Estado del módulo probabilístico

| Fase | Contenido | Versión |
|---|---|---|
| P0 | Núcleo estadístico | v0.1.33 |
| P1 | Variables aleatorias | v0.1.34 |
| P2 | Motor Global Minimum | v0.1.35 |
| P4 | Análisis de sensibilidad | v0.1.36 |
| P3 | **Overall Slope** | **v0.1.37** |
| P5 | Interfaz | pendiente |

**Motor completo.** Queda únicamente la interfaz.

## ⏳ Siguiente

**Fase P5 — interfaz**: página *Statistics* en Project Settings (tipo de
análisis, método de muestreo, número de muestras), menú *Statistics* con
el asistente de definición de variables, y en Interpret el histograma de
factores de seguridad, el gráfico de convergencia, los diagramas de
dispersión y las curvas de sensibilidad.

---

© 2026 Samuel Sáez López — UPCT — GPL-3.0
