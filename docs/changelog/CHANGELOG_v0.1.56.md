# OGR Suite v0.1.56 — Changelog

**Lanzamiento:** 7 de agosto de 2026
**Desarrollador:** Samuel Sáez López — Estudiante de Doctorado, UPCT
**Licencia:** AGPL-3.0-or-later

> **Fase M5: menús menores**, y con ella **desaparece el último
> marcador** del programa. Además, tres correcciones que la fase sacó a
> la luz.

---

## 🔴 Cero marcadores

Cinco entradas seguían mostrando un mensaje de «no implementado» pese a
que la maquinaria detrás ya existía de fases anteriores:

- **Add Text**, **Measure**, **Dimension Length** y **Dimension Angle**
  ahora escriben en la **capa de anotación** construida en v0.1.54.
- **Define Limits** usa los **límites de talud** añadidos en v0.1.55.

Hay un test que comprueba que la cadena `_tool_msg(` **ya no aparece** en
el código fuente.

## 🔴 El About decía GPL-3.0

Incorrecto desde v0.1.43, cuando el proyecto pasó a AGPL. **Una licencia
mal indicada en la interfaz es peor que no indicarla**, porque un usuario
podría confiar en ella. Corregida la constante y el texto, que ahora
explica en qué consiste la AGPL en la práctica y advierte de que **no hay
garantía y los resultados deben contrastarse** con cálculos
independientes antes de basarse en ellos. Un test exige que coincida con
`pyproject.toml`.

## 🔴 El About mostraba la versión 0.1.16

Cuarenta versiones desactualizado. **Una versión duplicada a mano se
queda obsoleta en silencio**, y el diálogo Acerca de es justo donde un
usuario mira qué compilación está ejecutando. Ahora se lee de los
metadatos del paquete, con reserva al `pyproject.toml`. Hay test.

## 🔴 Un bug encontrado por su propio test

`Vertex` es **inmutable**, así que la primera versión de *Move Support*,
que hacía `pt.x += dx`, habría fallado en ejecución. El test lo detectó
antes de que llegara a nadie. Ahora los extremos se sustituyen en lugar de
mutarse, y hay un test que fija la inmutabilidad de la que depende el
arreglo.

## 🆕 Entradas nuevas

**File**: Import Properties (numera los nombres duplicados en lugar de
sobrescribir, porque reemplazar en silencio un material que una región ya
referencia cambiaría resultados sin que se vea), Export Image (fondo
**blanco, no transparente**: una figura transparente pegada en un informe
muestra lo que haya detrás), Page Setup y Print Preview.

**Edit**: submenú **Picture Format** con mapa de bits y vectorial. El
vectorial merece estar porque un mapa de bits ampliado en un informe se
desdibuja, y una sección es justo la figura en la que un lector amplía.
Los dos formatos son mutuamente excluyentes.

**Loading**: Modify Load. **Support**: Modify, Move y Ungroup Pattern. Al
mover un soporte **ambos extremos se desplazan igual**, porque uno que
cambiara de longitud o inclinación al moverse alteraría en silencio la
fuerza que aporta.

**Help**: Check for Updates, que **deliberadamente no contacta con ningún
servidor** — una herramienta geotécnica llamando a casa sin avisar no es
algo que añadir sin preguntar, y una máquina sin red es un sitio normal
donde ejecutar esto. Hay un test que verifica que no aparecen `urlopen`,
`requests`, `socket` ni `httpx` en ese método.

## 📊 Tests

**1197 tests, 1197 verdes** (+21 desde v0.1.55; suite 100 % desde
v0.1.21).

Cobertura (`tests/test_minor_menus_m5_v156.py`): ausencia de marcadores;
File, Edit (formatos excluyentes, mapa de bits por defecto), Loading y
Support (**traslación que conserva la longitud**, **inmutabilidad de
Vertex**); Help y About (**AGPL y no GPL**, coincidencia con
`pyproject.toml`, **versión no literal**, aviso de ausencia de garantía,
y **sin contacto con servidores**); y **toda acción nueva alcanzable desde
un menú**, que es la lección de v0.1.42.

## ⏳ Siguiente

**Fase M6 — MDI y utilidades avanzadas**: registro dinámico de sesiones
con marca de activa y asterisco de no guardado, Parameter Calculator, y
la aplicación efectiva de los coeficientes parciales de la norma de
diseño.

---

© 2026 Samuel Sáez López — UPCT — AGPL-3.0-or-later
