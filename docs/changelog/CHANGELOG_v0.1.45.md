# OGR Suite v0.1.45 — Changelog

**Lanzamiento:** 6 de agosto de 2026
**Desarrollador:** Samuel Sáez López — Estudiante de Doctorado, UPCT
**Licencia:** AGPL-3.0-or-later

> **Texto íntegro de la licencia**, **README completo** y **Fase D1 del
> import DXF: el saneador de geometría** — la fase que decide si un plano
> importado es utilizable.

---

## ⚖️ Licencia AGPL completa

`gnu.org` no está entre los dominios accesibles del entorno, así que el
texto se obtuvo del **repositorio canónico de SPDX** vía
`raw.githubusercontent.com`: 34 KB, 235 líneas. Verificado antes de
instalarlo — las 17 secciones numeradas, la **sección 13 íntegra** (la
razón de elegir AGPL sobre GPL), el `END OF TERMS AND CONDITIONS` y el
aviso de copyright de la FSF.

**El stub desaparece**: el repositorio ya puede publicarse sin trámite
pendiente. El test que exigía el banner de aviso se sustituyó por uno que
exige el **texto verbatim**, comprobando las 18 secciones y un tamaño
mínimo de 30 KB.

## 📖 README

311 líneas, con el contexto del proyecto: los cinco programas de la suite
con su estado, la tabla de validación de los siete métodos LEM, una tabla
de **comportamiento verificado** (referencias externas e identidades
analíticas, nunca capturas), el equipo con la división explícita de
autoría, los colaboradores (UPCT e IMGA S.L.P.), la nota sobre el cambio
de licencia y la cita BibTeX.

## 🆕 Fase D1 — Saneador de geometría

`ogr_core/dxf/sanitiser.py`. El *pipeline*, en el orden en que debe
ejecutarse:

1. **Fusión de vértices** coincidentes dentro de tolerancia, cuantizando
   a rejilla para que el resultado **no dependa del orden** de visita.
2. **Cierre del contorno externo** si llega abierto, avisando cuando el
   hueco es grande porque cerrarlo cambia la forma.
3. **Soldado de extremos** al interior de segmentos **con inserción de
   nodo** — el punto crítico.
4. **Partición en cruces** entre todas las polilíneas.
5. **Prolongación** de contornos que se quedan cortos.
6. **Simplificación Douglas-Peucker al final**, protegiendo los vértices
   compartidos para que no pueda deshacer el soldado.

Todas las tolerancias son **relativas a la diagonal del modelo**, con el
porcentaje como parámetro de usuario y rango recomendado.

### La validación decisiva

No es «¿se ejecuta?» sino **¿cierran las regiones?**, comprobado con el
mismo invariante que validó la malla FE: **el área de las regiones
reconstruidas debe igualar la del contorno externo**. Una sola
comprobación que detecta huecos, solapes y fugas a la vez.

| Caso | Resultado |
|---|---|
| Material 0.4 unidades corto en ambos extremos | 2 nodos insertados, 2 regiones, área exacta |
| Material que sobrepasa el contorno | regiones cerradas |
| Dos materiales que se cruzan | **4 regiones**, área exacta |
| Con simplificación activada | regiones intactas |
| El mismo plano en metros y en milímetros | **resultado idéntico** |

## 🔴 Dos hallazgos durante los tests

**1. Nodo degenerado junto a una esquina.** Un extremo que aterriza a 0.2
unidades de una esquina existente insertaba un nodo ahí, creando un
segmento diminuto. Ahora, si la proyección cae dentro de tolerancia de un
**vértice existente**, se ajusta a ese vértice en lugar de insertar uno
nuevo: reutilizar la esquina que ya está es mejor geometría que fabricar
una astilla.

**2. El guardado que saltaba el caso más limpio.** El soldador descartaba
contactos con `d < 1e-15`, un guardado puesto para evitar autocontactos.
Pero eso **saltaba silenciosamente el caso ideal**: geometría dibujada
correctamente en CAD, que toca el interior de un segmento *exactamente*.
Esa unión en T quedaba sin nodo compartido y **la región no cerraba** —
precisamente el fallo que toda esta fase existe para evitar. El
autocontacto se excluye por identidad (`q is p`), no por distancia. Hay
un test de regresión con la explicación escrita.

Un tercer ajuste fue de mis propios tests: comprobaban *qué paso* del
pipeline hacía el trabajo en vez del **resultado**. La fusión de vértices
puede resolver un caso antes de que el soldador lo vea, y ambas rutas son
correctas; la aserción ahora es sobre el estado final.

## 📊 Tests

**859 tests, 859 verdes** (+27 desde v0.1.44; suite 100 % desde v0.1.21).

Cobertura (`tests/test_dxf_sanitiser_v145.py`): cierre de regiones en los
cinco escenarios con el invariante de área; soldado (nodo en contacto
interior, ajuste a vértice cercano, **contacto exacto**, respeto de la
tolerancia, e **independencia del orden** — que era el fallo original del
editor); contorno externo (cierre, aviso de hueco grande, ya cerrado sin
tocar, ausente reportado sin abortar, múltiples quedándose el mayor);
simplificación (extremos preservados, forma real conservada, tolerancia
nula, **nodos compartidos supervivientes**, conteo para la vista previa);
tolerancias relativas escalando con el modelo; e informe de problemas con
coordenadas para centrar la vista.

## ⏳ Siguiente

**Fase D2 — diálogo de importación**: tabla de todas las capas con
desplegable de tipo, unidades, tolerancias con rango recomendado,
densidad de discretización y **vista previa** con el conteo de vértices
antes/después y la lista de problemas.

---

© 2026 Samuel Sáez López — UPCT — AGPL-3.0-or-later
