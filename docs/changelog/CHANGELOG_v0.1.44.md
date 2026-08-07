# OGR Suite v0.1.44 — Changelog

**Lanzamiento:** 5 de agosto de 2026
**Desarrollador:** Samuel Sáez López — Estudiante de Doctorado, UPCT
**Licencia:** AGPL-3.0-or-later

> **Andamiaje para Git/GitHub** y **Fase D0 del import DXF**: lector y
> catálogo de capas.

---

## 🔧 Andamiaje de repositorio

Pensando en el paso a VSCode y GitHub:

- **`.github/workflows/tests.yml`** — CI en GitHub Actions con dos
  trabajos: la suite completa en Python 3.11 y 3.12 (instalando las
  librerías de sistema que PySide6 necesita incluso en modo *offscreen*,
  porque los tests construyen widgets reales aunque no lleguen a
  pantalla), y una comprobación **independiente de coherencia de
  licencia** que no requiere dependencias y da respuesta rápida.
- **`CONTRIBUTING.md`** — con las seis condiciones que debe cumplir un
  cambio. No son burocracia: cada una existe porque su ausencia causó un
  problema real en este proyecto, y el documento lo dice explícitamente
  (validación contra referencias externas y no capturas; `tr()` en todo
  texto visible; toda acción alcanzable desde un menú; cabecera de
  licencia; tests que no filtren estado; y **anomalías reportadas antes de
  corregirlas**, con los dos casos que lo justifican).
- **Plantillas de *issue***: informe de fallo y **caso de validación**
  (con origen del valor de referencia), que es el tipo de aportación más
  valiosa para un programa de cálculo.
- `.gitignore` ya existía y se mantiene.

## 🆕 Fase D0 — Lector DXF y catálogo de capas

`ogr_core/dxf/reader.py`. **Solo lee e inventaría**: no toca el modelo.

**Entidades soportadas**: `LINE`, `LWPOLYLINE`, `POLYLINE`, `ARC`,
`CIRCLE`, `SPLINE`. Las no soportadas se **cuentan**, no se descartan en
silencio, para que el informe de problemas pueda mencionarlas. Una entidad
malformada **no aborta la importación**: se contabiliza y se sigue.

**Bulges.** Una polilínea puede llevar arcos codificados como valor de
*bulge* (la tangente de un cuarto del ángulo incluido). Ignorarlos
convierte silenciosamente los arcos en cuerdas — un nivel freático curvo
se leería como recto **sin ningún error**. Se discretizan correctamente y
se conservan los extremos exactos. Hay un test dedicado: la polilínea de
prueba tiene tres puntos, así que una lectura por cuerdas daría exactamente
tres vértices.

**Densidad de discretización expresada por círculo completo**, que es el
parámetro que se comporta igual para un pequeño acuerdo y para un arco
grande: un arco de 90° recibe la cuarta parte. Verificado: con 64
segmentos por círculo, el círculo da ~64 vértices y el arco de 90° ~16, y
todos los puntos caen sobre la circunferencia con error < 1e-6.

**Unidades.** `$INSUNITS` se lee pero se trata **solo como sugerencia**,
porque falta o es incorrecto con frecuencia en ficheros exportados de CAD.
Se pregunta al usuario, por defecto metros. Un test comprueba justamente
que la sugerencia del encabezado **no manda** sobre la elección del
usuario.

**Reconocimiento de capas** insensible a mayúsculas y separadores, con
**alias en español** (`FREATICO`, `GRIETA`, `ANCLAJES`, `DESEMBALSE`,
`MATERIALES`). La coincidencia exacta gana sobre la parcial. Y —importante—
las capas no reconocidas, incluida la ubicua `0`, quedan como *ignorar*
para que **el usuario decida**, nunca adivinadas.

Se expone además `diagonal()`, que es la longitud contra la que se medirán
las **tolerancias relativas** de la Fase D1.

## 📊 Tests

**832 tests, 832 verdes** (+29 desde v0.1.43; suite 100 % desde v0.1.21).

Cobertura (`tests/test_dxf_reader_v144.py`): reconocimiento de capas
(nombres por defecto, insensibilidad, alias españoles, capas arbitrarias
sin adivinar, exacta sobre parcial); lectura (todas las capas
catalogadas, recuentos por entidad, tipos propuestos, líneas como
polilíneas de dos puntos, **contorno externo leído como abierto** —
fielmente, sin cerrarlo, porque eso es D1—, splines aplanados, entidades
no soportadas contadas sin ser fatales, *handles* registrados);
**bulges** convertidos en arco y no en cuerda; densidad de
discretización; unidades y todos los factores; y errores (archivo
inexistente, archivo que no es DXF).

## ⏳ Siguiente

**Fase D1 — el saneador de geometría**, el núcleo del riesgo: fusión de
vértices, **soldado de extremos al interior de segmentos con inserción de
nodo** (la lección que costó resolver en el editor), partición en
intersecciones, cierre del contorno externo, prolongaciones y
simplificación Douglas-Peucker. Se validará con el mismo invariante que
usé para la malla FE: **el área de las regiones reconstruidas debe igualar
la del contorno externo**.

---

© 2026 Samuel Sáez López — UPCT — AGPL-3.0-or-later
