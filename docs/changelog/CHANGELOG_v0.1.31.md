# OGR Suite v0.1.31 — Changelog

**Lanzamiento:** 2 de agosto de 2026
**Desarrollador:** Samuel Sáez López — Estudiante de Doctorado, UPCT
**Licencia:** GPL-3.0

> Cierre funcional del transitorio: **factor de seguridad por etapa** y
> **navegación temporal en el Interpret**. El motor de v0.1.30 era
> correcto y estaba validado, pero el usuario no podía convertir las
> presiones transitorias en la información que realmente busca.

---

## 🔴 El transitorio no transitaba

Al conectar el FoS por etapa apareció un fallo de fondo que el motor por
sí solo no revelaba: **la interfaz aplicaba las mismas condiciones de
contorno al estado inicial y a todas las etapas**. Con condiciones
idénticas el campo ya parte en equilibrio con ellas, así que no
evolucionaba: las tres etapas devolvían presiones y factores de seguridad
**exactamente iguales**.

Un análisis transitorio necesita por definición que el estado inicial
difiera del de las etapas — en un desembalse, nivel alto al principio y
bajo después. Se añade por tanto:

- **`transient_initial_bcs`** en los ajustes: condiciones que definen el
  estado inicial (el campo estacionario del que arranca el transitorio).
- **Condiciones por etapa**: cada etapa puede llevar su propio juego
  capturado; las que no lo llevan usan el actual.
- Dos botones en el diálogo de etapas: **Capture current BCs** (a la
  etapa seleccionada, marcada con `[BC]`) y **Capture as initial state**.

## 🆕 Factor de seguridad por etapa

La casilla *Calculate SF* ya hace lo que promete. En cada etapa marcada,
el campo de presiones de esa etapa pasa a ser temporalmente el activo del
proyecto, se lanza la búsqueda configurada y el FoS crítico se guarda en
`notes["fos"]` (por método) y `notes["fos_min"]`.

Detalles de implementación:

- **Sin duplicar la construcción de búsqueda**: se reutiliza
  `_ComputeWorker` invocándolo de forma síncrona, de modo que las
  corridas por etapa honran exactamente el mismo método de búsqueda y
  ajustes que un *Compute* normal.
- **Restauración garantizada**: el campo activo del proyecto se repone en
  un `finally`, así que el cálculo por etapas no deja el proyecto
  apuntando a una etapa intermedia.
- **Aviso en lugar de silencio**: si ningún material usa el tipo de
  presión `FEM_SEEPAGE`, los factores ignorarían el agua calculada; en
  vez de reportar un FoS "seco" como si fuera válido, se guarda
  `fos_warning` y la interfaz lo muestra.

### ✔️ Validación física: desembalse rápido

Nivel inicial 45 m que baja a 28 m, con materiales acoplados:

| Tiempo | u máx. | Agua almacenada | FoS (Bishop) |
|---|---|---|---|
| 1e4 | 320.6 | 1791.50 | **0.8528** |
| 1e5 | 288.5 | 1782.32 | 0.8973 |
| 1e6 | 274.7 | 1764.07 | 0.9006 |
| 1e7 | 274.7 | 1736.80 | 0.9006 |

Es el comportamiento clásico del **desembalse rápido**: el factor de
seguridad es **mínimo justo después de la bajada**, cuando las presiones
intersticiales aún no se han disipado, y **se recupera** conforme drenan.
El agua almacenada desciende monótonamente. Que este patrón salga solo,
sin ajustar nada, es la mejor comprobación de que el acople
flujo-tiempo-estabilidad está bien montado.

## 👁️ Interpret: navegación temporal

- **Selector de etapa** que lista todas con su tiempo, etiqueta y marca
  `[SF]` en las que tienen factor calculado; cambiar de etapa redibuja
  campos, vectores y freática de ese instante.
- **Botón *FoS vs time***: gráfico del factor de seguridad crítico frente
  al tiempo, con una curva por método. Si no hay ninguno calculado,
  explica qué hacer (marcar *Calculate SF* y recalcular) o muestra el
  aviso de `FEM_SEEPAGE`.
- La barra de estado incluye ahora el tiempo de la etapa y sus factores.

## 📊 Tests

**579 tests, 579 verdes** (+10 desde v0.1.30; suite 100 % desde v0.1.21).

Cobertura nueva: FoS calculado solo en las etapas marcadas; **las
condiciones por etapa hacen evolucionar el campo** (el fallo que este
release corrige); **recuperación del FoS con el tiempo** en un
desembalse; aviso cuando los materiales ignoran la filtración;
restauración del campo activo tras el cálculo; y en el Interpret, selector
con todas las etapas, cambio efectivo de campo al navegar, resumen con
tiempo y FoS, y ausencia de selector en corridas estacionarias.

## 🏁 Módulo de agua subterránea

Las siete fases (0–6) completas **y funcionalmente cerradas**: de la
malla al transitorio, con acople bidireccional a la estabilidad y una
historia de factores de seguridad navegable.

## ⏳ Siguiente

1. **Anomalía A3** — `reject_tensile` como post-filtro al seleccionar la
   superficie crítica, en vez de filtro durante la búsqueda.
2. **Análisis probabilístico y de sensibilidad** — el mayor ausente
   frente a la referencia.
3. Back analysis de soportes, import DXF, cobertura i18n.

---

© 2026 Samuel Sáez López — UPCT — GPL-3.0
