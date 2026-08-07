# OGR Suite v0.1.53 — Changelog

**Lanzamiento:** 6 de agosto de 2026
**Desarrollador:** Samuel Sáez López — Estudiante de Doctorado, UPCT
**Licencia:** AGPL-3.0-or-later

> **Fase I3: menús de Interpret completos.** Las 21 entradas que faltaban,
> con funcionalidad real y no como marcadores.

---

## 🆕 Los cuatro menús al 100 %

| Menú | Antes | Ahora |
|---|---|---|
| Data | 6/10 | **10/10** |
| Query | 3/8 | **8/8** |
| Groundwater | 5/11 | **11/11** |
| Statistics | 3/9 | **9/9** |

**Data**: gráfico de FoS frente al tiempo (a partir de las etapas
transitorias), análisis de fuerza en soportes, retroanálisis interactivo
con factor objetivo y cota, y contornos suplementarios.

**Query**: puntos de consulta (añadir, graficar, eliminar), consulta de
superficies inválidas y rótulo durante la consulta.

**Groundwater**: opciones de contorno y de leyenda propias, consulta
nodal, datos de usuario definidos por expresión, historial de iteraciones,
gráfico de convergencia y exportación de todos los valores nodales a CSV.

**Statistics**: gráfico de sensibilidad, gráfico de convergencia,
exportación de datos estadísticos, mostrar y elegir superficies de mínimo
global, y superficie probabilística crítica.

## 🎯 Cinco decisiones de diseño

**Deshabilitado con explicación, no oculto.** Una entrada que necesita un
transitorio, un soporte o un resultado probabilístico aparece en gris **con
un tooltip diciendo qué ejecutar primero**. Ocultarla dejaría al usuario
sin poder descubrir que la capacidad existe. Hay un test que exige que
**toda entrada deshabilitada tenga tooltip**: una entrada gris sin
explicación es un callejón sin salida.

**Los puntos de consulta son una lista**, no una inspección de un solo
uso, para poder comparar varias ubicaciones en lugar de mirarlas y
olvidarlas.

**Las superficies inválidas se agrupan por motivo.** Doscientos mensajes
idénticos no son un diagnóstico; agrupados por causa y ordenados por
frecuencia, sí.

**El agua subterránea tiene sus propios contornos**, separados de los de
estabilidad: una cabeza en metros y un factor de seguridad son escalares
distintos con rangos distintos, y compartir un rango los haría inútiles a
los dos.

**Las expresiones de usuario se evalúan sin *builtins***, para que un
archivo de proyecto no pueda ejecutar código arbitrario por ese campo. Un
test lo verifica intentando `__import__`.

## 🔧 Dos correcciones de camino

**Los gráficos eran modales.** `_plot_xy` usaba `exec()`, lo que además de
bloquear en pruebas headless es peor experiencia: un gráfico modal impide
compararlo con el modelo al lado y tener dos abiertos a la vez. Ahora es
**no modal**, conservando la referencia para que Qt no lo recoja.

**La trampa del `QMessageBox` modal, otra vez.** Varias entradas informan
a través de `_info`, que abre un cuadro modal y bloquea indefinidamente en
un entorno sin pantalla — el mismo problema que apareció en la Fase 5 del
agua subterránea. Los tests se reescribieron para verificar los guardas y
los datos sobre los que actúan esos métodos, en lugar de disparar el
mensaje. Queda anotado en la cabecera del archivo de tests, porque es un
patrón que volverá a aparecer.

## 🌐 i18n

**73 claves nuevas** traducidas. Se amplió además la lista de excepciones
del test de «traducciones perezosas» con doce entradas legítimamente
idénticas en español: nombres propios (Monte Carlo), cognados (Horizontal,
Error, Color), siglas de la barra de estado mantenidas para que ambos
idiomas ocupen el mismo ancho, y cadenas que son puro formato.

## 📊 Tests

**1092 tests, 1092 verdes** (+26 desde v0.1.52; suite 100 % desde
v0.1.21).

Cobertura (`tests/test_interpret_i3_v153.py`): completitud de los cuatro
menús contra la especificación; habilitación condicional (transitorio,
soportes, agua, estadística) y **toda entrada deshabilitada con tooltip**;
puntos de consulta (lista que acumula, guardas, eliminación); agrupación
de superficies inválidas; entradas de agua subterránea con y sin
resultado, **expresión de usuario aislada**, y contornos separados;
contornos suplementarios que cambian el modo; y entradas de estadística
con sus guardas.

## ⚠️ Nota sobre la ejecución de la suite

La suite completa tarda ya unos **290 s**, justo en el límite de 300 s del
entorno de desarrollo usado en esta sesión, así que se verificó **en dos
mitades** (554 + 538 = 1092, cero fallos). En una máquina local o en el
CI de GitHub Actions no existe ese tope y se ejecuta de una pasada. Es una
señal de que conviene vigilar el coste de los tests nuevos: los que mallan
y resuelven filtración son los caros.

## ⏳ Siguiente

**Fase M3 — menú Tools y capa de anotación**: primitivas de dibujo,
tablas de propiedades de soportes e hidráulicas, cotas X/Y, ejes, imagen
de fondo, gestión de objetos, y la separación explícita entre capa de
anotación y capa física con *Convert Tool to Boundary* como único puente.

---

© 2026 Samuel Sáez López — UPCT — AGPL-3.0-or-later
