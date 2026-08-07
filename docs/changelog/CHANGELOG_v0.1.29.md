# OGR Suite v0.1.29 — Changelog

**Lanzamiento:** 1 de agosto de 2026
**Desarrollador:** Samuel Sáez López — Estudiante de Doctorado, UPCT
**Licencia:** GPL-3.0

> **Fase 5 del plan de agua subterránea: interfaz del modo Groundwater e
> Interpret de flujo.** Con esto el módulo de agua queda **completo y
> utilizable de principio a fin desde la interfaz gráfica**: propiedades
> hidráulicas → malla → condiciones de contorno → cálculo →
> interpretación → acople con estabilidad.

---

## 🆕 Diálogo *Define Hydraulic Properties*

Sigue la distribución obtenida por ingeniería inversa en
`docs/INTERFAZ_AGUA_SUBTERRANEA.md`:

- Lista de materiales a la izquierda, parámetros a la derecha.
- **Nombres y colores de material en solo lectura**, con nota explícita
  de que se definen en *Define Material Properties*: son dos vistas de la
  **misma** lista de materiales, no dos listas distintas.
- Ks, K2/K1 y ángulo de K1 (desde el eje +X).
- Selector con los **siete modelos**, cada uno con su página de
  parámetros (Soil Type para Simple; λ y presión de burbujeo para
  Brooks-Corey; A, B, C para Fredlund-Xing; a y n para Gardner; α, n y
  **Custom m** para van Genuchten).
- **Ks se deshabilita con *User Defined*** (allí Ks es el primer punto de
  la curva).
- **Pick** — carga parámetros representativos de literatura; habilitado
  **solo** para los cuatro modelos con biblioteca.
- **Plot** — gráfico log-log de la función k(ψ) definida.
- Copias de trabajo internas: *Cancel* realmente cancela.

## 🆕 Diálogo *Set Boundary Conditions*

Con las reglas de habilitación de la referencia, todas verificadas por
test:

| Regla | Comportamiento |
|---|---|
| Campo **Value** | Solo para Total Head, Pressure Head, Nodal Flow e Infiltration |
| **Seepage Face** | Solo para Nodal Flow Rate e Infiltration |
| **Pick by** | Segmentos o nodos, salvo **Infiltración: solo segmentos** (el selector se bloquea) |

Clasifica el contorno automáticamente en lados (izquierdo, derecho,
fondo y superficie del terreno) para asignar sin necesidad de un modo de
selección interactivo, con botón *Restore defaults* que repone los
valores documentados y un resumen en vivo de las condiciones activas.

## 🆕 Ventana *Interpret Groundwater*

Contornos rellenos de **cabeza total H**, **cabeza de presión P** o
**presión intersticial u** (con la succión como valores negativos),
**vectores de flujo**, **superficie freática P = 0**, malla conmutable y
una herramienta de **sección de descarga** que integra el caudal normal e
informa de la convención de signo. La barra de estado resume rangos,
iteraciones, nodos de rezume y cualquier aviso de convergencia.

## 🔒 Dependencias duras del menú

Lo más valioso de la ingeniería inversa no eran los controles sino las
**dependencias** que la interfaz debe hacer cumplir. Implementadas y
verificadas:

| Estado | Habilitado |
|---|---|
| Método de agua ≠ FEA | nada |
| FEA, sin malla | solo *Define Hydraulic Properties* |
| FEA + malla | + *Set Boundary Conditions*, *Compute Groundwater* |
| Con resultado | + *Interpret Groundwater* |

Además, **regenerar o borrar la malla invalida** las condiciones de
contorno y el resultado obsoletos, en vez de dejarlos apuntando a nodos
que ya no existen.

## 🔗 Otros

- **`phi_b` y *Air Entry Value*** añadidos al diálogo de materiales, y
  habilitados **solo con método FEA** (como la referencia, porque solo
  entonces puede haber presiones negativas). El diálogo recibe ahora el
  método de agua como parámetro, ya que trabaja sobre la lista de
  materiales y no sobre el proyecto.
- **Condiciones de contorno serializadas** en el `.ogr`.

## 🔴 Un bloqueo real encontrado por los tests

Dos tests de menú colgaban el proceso indefinidamente. La causa no era
un fallo del código sino **del propio test**: llamaban a
*Compute Groundwater* con las condiciones **por defecto**, que son
Neumann puro y por tanto un problema singular; el handler entonces abre —
correctamente — un `QMessageBox` **modal**, que en un entorno headless
bloquea para siempre. Los tests ahora prescriben cabezas antes de
calcular, mediante un helper documentado con la razón. De colgarse
indefinidamente a **1.7 s para los 23 tests** de la fase.

Es un recordatorio útil para futuras pruebas de GUI: cualquier ruta que
pueda abrir un diálogo modal debe evitarse o simularse en los tests.

## 📊 Tests

**544 tests, 544 verdes** (+23 desde v0.1.28; suite 100 % desde v0.1.21).

Cobertura nueva (`tests/test_gw_gui_v129.py`): dependencias del menú en
los cuatro estados e invalidación al resetear la malla; diálogo
hidráulico (lista completa, Ks deshabilitado en User Defined, Pick solo
con biblioteca, Custom m, guardado en *OK*, **Cancel no modifica nada**,
curva para Plot); diálogo de condiciones (cobertura total de nodos de
contorno, Value y Seepage Face por tipo, infiltración solo por segmentos,
asignación efectiva, restaurar defectos); **flujo de trabajo completo**
de extremo a extremo con los tres campos del Interpret; cálculo sin
propiedades definidas usando defectos; persistencia de las condiciones;
y los campos de resistencia no saturada visibles solo con FEA.

## ⏳ Estado del módulo de agua

Fases 0 a 5 **completas**. La Fase 6 (transitorio: etapas temporales,
almacenamiento, FoS por etapa) queda como ampliación diferible.

Pendiente previo sin resolver: decisión sobre activar `reject_tensile`
por defecto en búsquedas no circulares (anomalía A3, ver
`CHANGELOG_v0.1.24.md`).

---

© 2026 Samuel Sáez López — UPCT — GPL-3.0
