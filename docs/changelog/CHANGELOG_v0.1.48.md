# OGR Suite v0.1.48 — Changelog

**Lanzamiento:** 6 de agosto de 2026
**Desarrollador:** Samuel Sáez López — Estudiante de Doctorado, UPCT
**Licencia:** AGPL-3.0-or-later

> **Exportación a DXF**, construida como espejo del importador y validada
> con el mismo criterio: un invariante, no una captura.

---

## 🆕 `ogr_core/dxf/exporter.py`

Motor separado del diálogo, igual que en la importación, para que una
exportación completa pueda automatizarse por script.

### El contrato de capas

Es lo que hace útil al dibujo, no solo bonito:

- **La geometría del modelo** se escribe en **las mismas capas que
  reconoce el importador**, de modo que un plano exportado puede editarse
  en CAD y volver a importarse.
- **Los resultados** —cargas, malla, superficie de rotura y anotaciones—
  van a capas con prefijo **`OGR_X_`** que el importador **ignora**. Son
  dibujos *de resultados*, no entradas del modelo: reimportarlos como
  geometría convertiría una flecha de carga en un contorno de material,
  una corrupción silenciosa. El diálogo lo explica en lugar de dejar que
  el usuario lo descubra.

El mapeo tipo→capa **se deriva del propio mapeo del importador**, así que
las dos mitades no pueden divergir: añadir un tipo de geometría le da capa
de exportación automáticamente. Hay un test que lo comprueba.

### Contenido

Contornos, soportes, cargas **como flechas** (dibujadas con líneas
sencillas para que se vean igual en cualquier CAD), malla de elementos
finitos (**desactivada por defecto**: escribe una línea por arista y
pueden ser miles), superficie de rotura crítica y anotaciones con el
factor de seguridad. Capas coloreadas para que el plano se lea al abrirlo,
y unidades registradas en `$INSUNITS`.

**La superficie de rotura se dibuja con los puntos de base de las
dovelas**, que *son* la superficie analizada. Dibujar el círculo completo
sería engañoso —solo el arco bajo el terreno es la rotura— y rederivar la
geometría permitiría que el dibujo se separase del cálculo.

## ✔️ El invariante: el viaje de ida y vuelta

Exportar y reimportar debe devolver la misma geometría. Pero conviene
enunciarlo con precisión, porque el resultado **no es idéntico vértice a
vértice, ni debe serlo**: el saneador del importador parte los contornos
en sus cruces, así que el contorno externo gana nodos donde lo encuentra
un contorno de material. Lo que debe conservarse es la **forma**:

| Comprobación | Resultado |
|---|---|
| Área encerrada | **idéntica** (diferencia relativa 0.0e+00) |
| Vértices originales presentes | **todos** |
| Vértices añadidos | **sobre segmentos originales** (< 1e-6) |
| Contornos de material (sin cruces) | **exactos** |
| Indicador de cerrado | conservado |
| Ida y vuelta en milímetros | área idéntica |
| Regiones tras el viaje | siguen construyéndose |

Esa formulación es **más fuerte** que exigir listas idénticas, porque
detecta igualmente una coordenada movida, perdida o redondeada, y además
no da por incorrecto un comportamiento que sí es correcto.

## 📊 Tests

**938 tests, 938 verdes** (+30 desde v0.1.47; suite 100 % desde v0.1.21).

Cobertura (`tests/test_dxf_export_v148.py`): viaje de ida y vuelta (tipos
y recuentos, **área idéntica**, todos los vértices originales, **los
añadidos sobre segmentos originales**, materiales exactos, indicador de
cerrado, milímetros, y regiones que siguen construyéndose); contrato de
capas (geometría en capas del importador, **mapeo derivado del importador**,
capas de resultados ignoradas, reimportación que no las convierte en
geometría, colores, unidades en el encabezado); contenido (superficie
escrita y **siguiendo las dovelas analizadas**, FoS anotado, opciones que
desactivan contenido, malla desactivada por defecto y escrita al pedirla,
informe y resumen, proyecto sin modificar, ruta no escribible reportada);
y diálogo (contenido no disponible deshabilitado, superficie con
resultados, malla cuando existe, opciones recogidas, **contrato de capas
explicado**, y acción de menú sin el stub).

## ⏳ Siguientes pasos posibles

Base de datos de materiales (OGR Data), instaladores, o ampliar la
validación con más casos de referencia.

---

© 2026 Samuel Sáez López — UPCT — AGPL-3.0-or-later
