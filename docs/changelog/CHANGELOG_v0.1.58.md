# OGR Suite v0.1.58 — Changelog

**Lanzamiento:** 7 de agosto de 2026
**Desarrollador:** Samuel Sáez López — Estudiante de Doctorado, UPCT
**Licencia:** AGPL-3.0-or-later

> **Preparación para desarrollo en VSCode y publicación en GitHub.** El
> repositorio pasa a llevar el contrato de trabajo con agentes de IA, la
> estructura SDD y un README en español pensado para la comunidad.

---

## 🆕 `AGENTS.md` — el contrato

226 líneas con stack, comandos, estructura, **las siete reglas**, el flujo
de trabajo, una lista explícita de qué no hacer y los convenios de código.

Las siete reglas no son buenas prácticas genéricas: **cada una existe
porque su ausencia causó un problema real en este proyecto**, y el archivo
lo dice en cada caso. Validación contra referencias externas y no
instantáneas; `tr()` en todo texto visible; toda acción alcanzable desde un
menú (doce se publicaron invisibles); cabecera SPDX; tests que no filtran
estado; **anomalías reportadas antes de corregirlas**; y —añadida en esta
versión— **ningún ajuste puede no hacer nada**, que salió de que los
coeficientes parciales estuvieran dos versiones siendo configurables sin
aplicarse.

`CLAUDE.md` **apunta** a AGENTS.md en lugar de duplicarlo: una regla escrita
en dos sitios se queda obsoleta en uno de ellos. Hay un test que lo
mantiene corto.

## 🆕 Comandos y skills

Cinco comandos en `.claude/commands/`: `/test` (resume solo lo que falla,
**sin corregir**), `/validar` (¿referencia externa o instantánea?),
`/revisar` (las siete reglas), `/feature` (obliga a escribir la
especificación antes del código) y `/release`.

Tres skills que el agente carga **solo cuando aplican**, para no gastar
contexto: **geotecnia** (unidades, convenios de signo, fuentes de cada
formulación con autor y año, y las trampas que ya costaron caro: `d` de
Janbu corregido, tan φ frente a φ, la zona saturada en transitorio…),
**gui-pyside6** (diálogos modales que bloquean, `isVisible` frente a
`isHidden`, `Qt.UserRole` = 256) y **tests-numericos**.

## 🆕 Estructura SDD y configuración

`spec/constitution/` con misión, stack y hoja de ruta —el de stack registra
**por qué** se tomó cada decisión, que es lo que impide que alguien la
deshaga sin saber el motivo— y `spec/features/000-plantilla/` como modelo.

`.claude/settings.json` con permisos: lectura y tests permitidos, `pip
install`, `git push` y `rm` preguntan, `.env` y `git push --force`
denegados. `.mcp.json` con Context7 **sin la clave dentro**: una API key en
un repositorio público es una clave filtrada.

`.vscode/` con la variable `QT_QPA_PLATFORM` puesta en el terminal —olvidarla
es lo primero que le falla a alguien nuevo—, extensiones recomendadas y una
tarea para la suite.

## 🗂️ Las dos carpetas

`docs/reference/` queda **en `.gitignore`**, y el área de trabajo de VSCode
monta dos carpetas **hermanas, no anidadas**: si las referencias
estuvieran dentro del repositorio, bastaría un `git add -A` distraído para
publicar material con copyright. El agente accede a ellas por
`additionalDirectories` en un archivo de configuración local que tampoco se
versiona, para que ninguna ruta personal acabe en el repositorio.

## 🧹 Limpieza y README

Los **38 changelogs** sueltos en la raíz pasan a `docs/changelog/`. La raíz
queda con los seis documentos de entrada, y hay un test que lo mantiene
así.

README nuevo **en español**, con las tablas de validación de los siete
métodos y de comportamiento verificado, la hoja de ruta de los cinco
programas, el equipo con la división explícita de autoría, y una sección
para quien desarrolle con agentes. Añade el aviso de que **no hay garantía
y los resultados deben contrastarse**: quien firma un proyecto es una
persona, no un programa.

Al traducirlo falló un test de licencia que buscaba una frase en inglés.
Se actualizó a la redacción realmente publicada, porque **un test que pasa
sobre un texto que nadie lee no vale nada**, y de paso se le añadió la
comprobación del aviso de garantía.

## 📊 Tests

**1263 tests, 1263 verdes** (+29 desde v0.1.57).

`tests/test_agent_scaffolding_v158.py` trata estos archivos por lo que son:
**documentación que se comporta como configuración**, que puede quedarse
obsoleta en silencio igual que el código. Comprueba que las siete reglas
siguen enunciadas, que AGENTS.md no supera las 500 líneas, que CLAUDE.md no
duplica, que los comandos tienen encabezado, que los permisos filtran lo
peligroso, que **la carpeta de referencias sigue fuera del control de
versiones**, que no hay claves en `.mcp.json`, que las plantillas exigen
criterios medibles y referencia de validación, y que la raíz sigue limpia.

## ⏳ Siguiente

Publicar en GitHub, y después instaladores.

---

© 2026 Samuel Sáez López — UPCT — AGPL-3.0-or-later
