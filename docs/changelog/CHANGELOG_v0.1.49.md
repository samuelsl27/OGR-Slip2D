# OGR Suite v0.1.49 — Changelog

**Lanzamiento:** 6 de agosto de 2026
**Desarrollador:** Samuel Sáez López — Estudiante de Doctorado, UPCT
**Licencia:** AGPL-3.0-or-later

> **Auditoría de interfaz** contra el prompt original y la referencia, y
> **fase I1**: la capa de contexto visual que le faltaba a Interpret.

---

## 📋 Auditoría

`docs/AUDITORIA_INTERFAZ_v0.1.48.md` contrasta las 2150 líneas del prompt
inicial y las 194 páginas de documentación de la referencia con el estado
real: 88 acciones, 52 iconos, 92 entradas de menú, 25 diálogos.

**El motor de cálculo excede lo pedido** (18 modelos de resistencia frente
a los 14 del prompt, más agua subterránea con transitorio y probabilístico
completo, que el prompt solo mencionaba de pasada). Lo que falta se
concentra en **utilidades de dibujo, anotación y configuración fina**.

Se documentan además **siete apartamientos deliberados** del prompt —
licencia AGPL, `.ogr` sin HDF5, scipy en lugar de `triangle`, tolerancias
DXF relativas, m-alpha desactivado por defecto, siete métodos LEM y los
añadidos de Interpret— para que no se «corrijan» por error.

`docs/PLAN_INTERFAZ.md` ordena el trabajo restante en tres fases de
Interpret y seis del modelador.

## 🆕 Fase I1 — Contexto visual de Interpret

**Barra de color gráfica** (`ogr_gui/widgets/legend.py`), en sustitución
de una tabla HTML escrita a mano cuyas bandas estaban **fijas en el
código**: decía exactamente lo mismo con independencia de los resultados.
La nueva se genera a partir de **la misma función de color que usa el
lienzo**, así que las dos no pueden discrepar — un test lo comprueba
comparando la función objeto a objeto. Muestrea la función en 32 puntos,
de modo que una paleta no lineal se reproduce fielmente en lugar de
aproximarse con dos colores extremos.

**Factor de seguridad anclado** a la superficie crítica, y **marca en la
barra de color** en el valor crítico.

**Indicador de algoritmo activo**. Se crea **también cuando hay un solo
método**: el selector no tiene sentido con uno, pero saber qué método
produjo los números sí, y es lo primero que necesita quien lee un informe.

**Barra de estado** con las palabras DATA TIPS, SNAP, GRID, ORTHO y OSNAP
**alternables haciendo clic**, como exige la especificación —no solo desde
un diálogo—, con estado legible de un vistazo, y lectura de coordenadas.

**Menú View en Interpret**, que no existía: zoom, mostrar/ocultar leyenda,
opciones de leyenda (decimales, intervalos, notación científica) y modos
de Data Tips.

### Todo sigue al método activo

Cada método tiene **su propia superficie crítica**, así que al cambiar de
método deben moverse con él el rango de la leyenda, su marca y la etiqueta
de algoritmo. La primera versión no lo hacía; hay tres tests que lo fijan.

## 📊 Tests

**962 tests, 962 verdes** (+24 desde v0.1.48; suite 100 % desde v0.1.21).

Cobertura (`tests/test_interpret_i1_v149.py`): leyenda (existe y está
acoplada, rango que cubre los resultados, valor crítico marcado, **misma
función de color que el lienzo**, formato numérico, **rango degenerado**
cuando todas las superficies tienen el mismo factor, y pintado sin error);
algoritmo activo y etiqueta anclada; **los tres elementos siguen el cambio
de método**; indicadores de estado (las cinco palabras, **alternar por
clic**, señal emitida, no-op al repetir estado, estado visualmente
distinto, coordenadas, instantánea de estados); y menú View (existe,
ofrece leyenda, Data Tips y zoom, y la leyenda se puede ocultar).

## ⏳ Siguiente

**Fase I2 — motor de contornos**: Contour Options con mínimo, máximo,
intervalo, modo de relleno y paleta; Legend Options completas; y campos
escalares seleccionables sobre la malla.

---

© 2026 Samuel Sáez López — UPCT — AGPL-3.0-or-later
