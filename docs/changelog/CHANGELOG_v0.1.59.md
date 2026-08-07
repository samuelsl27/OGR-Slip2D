# OGR Slip2D v0.1.59 — Changelog

**Lanzamiento:** 7 de agosto de 2026
**Desarrollador:** Samuel Sáez López — Estudiante de Doctorado, UPCT
**Licencia:** AGPL-3.0-or-later

> **Corrección de nombres** e **infraestructura de casos de validación**.

---

## 🔴 El paquete se llamaba como la suite

`pyproject.toml` declaraba `name = "ogr-suite"` cuando el repositorio
contiene **un solo programa**. Dos problemas: habría colisionado en cuanto
apareciese el segundo, y `pip install ogr-suite` entregaría algo que no es
la suite.

Corregido a **`ogr-slip2d`**, con los dos niveles escritos explícitamente
en `AGENTS.md` y en el README:

| Nivel | Qué es |
|---|---|
| **OpenGeoRock** / OGR Suite | El paraguas: cinco programas planificados, la marca, la web |
| **OGR Slip2D** | Este programa, y lo que contiene este repositorio |

El diálogo Acerca de lee la versión de los metadatos del paquete, así que
el nombre tenía que cambiar en los dos sitios a la vez o la versión habría
caído silenciosamente al valor de reserva. Hay test.

Se corrigieron además **URLs obsoletas** que apuntaban a una cuenta de
GitHub inexistente (`samuelsaez/ogr-suite`).

### Sobre `ogr_core`

Se queda **dentro de Slip2D por ahora**. Extraerlo a su propio paquete
cuesta dos repositorios que versionar y sincronizar, y ese coste solo se
paga cuando existe un **segundo** programa que lo use. Separarlo hoy sería
resolver un problema que aún no existe, pagándolo desde el primer día.

## 🆕 Infraestructura de casos de validación

`validacion/casos/` con plantilla y un runner automático
(`tests/test_validation_cases.py`) que los recorre todos: **añadir un caso
no requiere escribir código**, solo una carpeta con `modelo.ogr`,
`esperado.json` y `caso.md`. Es deliberado — la fricción de escribir un
test es justo lo que impide que se añadan casos, y un motor de cálculo vale
precisamente el conjunto de casos que reproduce.

Tres decisiones:

- **La tolerancia vive en el caso, no en el test.** Un factor leído de una
  figura publicada no merece la misma exigencia que uno tabulado, y solo el
  caso sabe de cuál se trata. El runner rechaza tolerancias por encima del
  10 %: por ahí una "validación" deja de discriminar nada.
- **Un caso sin fuente falla.** Un valor esperado sin cita es una opinión,
  y un test que consagra una opinión es peor que ninguno.
- **Un caso sin modelo se salta, no falla**, para que la plantilla conviva
  con los reales sin ponerse en rojo.

Y una distinción que la plantilla obliga a marcar: **una comparación no es
una validación**. Que dos programas coincidan significa que coinciden, no
que acierten.

## 🗂️ Frontera de publicación

`validacion/README.md` la deja escrita: el `.ogr` y el número esperado
**son tuyos y se versionan**; los archivos nativos e informes de software
comercial **no**. Es una frontera de copyright, no de comodidad.

## 📖 `docs/ORGANIZAR_ESPACIO_TRABAJO.md`

Guía concreta para pasar de la carpeta actual a la estructura definitiva,
con los comandos de PowerShell, qué va a cada sitio y por qué. Incluye el
criterio de qué **no** darle al agente: `historico/` (prompts antiguos y
código sustituido) se queda fuera, porque el agente no tiene forma de saber
qué sigue vigente y leería decisiones ya revisadas como si valieran.

El área de trabajo pasa a montar **tres** carpetas —código, referencias y
web—, con rutas relativas para que funcione igual en cualquier sistema.

## 📊 Tests

**1279 tests, 1279 verdes** (+16 desde v0.1.58).

Nuevos: coherencia de nombres (paquete, diálogo Acerca de, AGENTS.md, sin
URLs obsoletas) e infraestructura de validación (carpeta, plantilla,
frontera de publicación documentada, fuente obligatoria, runner presente).

## ⏳ Siguiente

Poblar `validacion/casos/` con los casos comparados, publicar en GitHub, e
instaladores.

---

© 2026 Samuel Sáez López — UPCT — AGPL-3.0-or-later
