# Empezar a desarrollar en VSCode

Guía de arranque. Diez minutos la primera vez, después son dos comandos.

---

## 1. Las dos carpetas

El problema a resolver: el **código** se publica en GitHub, pero la
**documentación de referencia** (PDF de software comercial, artículos) no
puede publicarse —es material de terceros— y aun así el agente necesita
leerla.

La solución es tener dos carpetas hermanas:

```
~/proyectos/
├── OGR-Slip2D/             ← el repositorio. Esto va a GitHub.
├── ogr-referencias/        ← PDF, HTML, artículos. NUNCA va a GitHub.
└── OGR-Slip2D.code-workspace
```

**Hermanas, no anidadas.** Si `ogr-referencias/` estuviera dentro del
repositorio, bastaría un `git add -A` distraído para publicar material con
copyright. Fuera del repositorio, ese error es imposible.

Crea la estructura:

```bash
mkdir -p ~/proyectos && cd ~/proyectos
git clone https://github.com/samuelsl27/OGR-Slip2D.git
mkdir ogr-referencias
mv OGR-Slip2D/OGR-Slip2D.code-workspace .   # si viene en el ZIP
```

Y mete en `ogr-referencias/` toda la documentación que vienes usando.

---

## 2. Abrir el área de trabajo

En VSCode: **Archivo → Abrir área de trabajo desde archivo** →
`OGR-Slip2D.code-workspace`.

Verás dos carpetas en el explorador: *OGR Slip2D (código)* y *Referencias
(no se publica)*. Los nombres están puestos así a propósito: recuerdan cuál
es cuál cada vez que miras la barra lateral.

VSCode te ofrecerá instalar las extensiones recomendadas. Acepta: Python,
Pylance, Claude Code y el corrector ortográfico español.

---

## 3. Entorno de Python

```bash
cd ~/proyectos/OGR-Slip2D
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -e .
```

Comprueba que funciona:

```bash
QT_QPA_PLATFORM=offscreen python tests/_runner.py
```

Debe terminar con `Failed: 0`. Tarda entre 5 y 7½ minutos. En VSCode tienes
la tarea **Tests: suite completa** (`Ctrl+Shift+P` → *Run Task*) que ya
lleva la variable puesta.

Mientras trabajas en un área concreta no hace falta pagar ese rato entero:

```bash
python tests/_runner.py transient          # solo esos archivos
python tests/_runner.py -k erfc            # solo tests con ese nombre
python tests/_runner.py --list transient   # enseña la selección, no ejecuta
```

La tarea **Tests: selección** hace lo mismo preguntándote el patrón. Antes
de publicar, la suite entera y sin argumentos: una ejecución filtrada
avisa con `FILTERED RUN` porque no sirve como evidencia.

---

## 4. Dar al agente acceso a las referencias

El agente trabaja desde `OGR-Slip2D/`, así que por defecto **no** ve la
carpeta hermana. Hay que dárselo explícitamente.

Copia el ejemplo y ajusta la ruta:

```bash
cp .claude/settings.local.json.example .claude/settings.local.json
```

```json
{
  "permissions": {
    "additionalDirectories": ["/home/tu-usuario/proyectos/ogr-referencias/"]
  }
}
```

Usa **ruta absoluta**. Ese archivo está en `.gitignore`, así que tu ruta
personal no acaba en el repositorio.

Alternativa para una sesión suelta, sin tocar configuración:

```bash
claude --add-dir ../ogr-referencias
```

---

## 5. Los primeros cinco minutos

```bash
cd ~/proyectos/OGR-Slip2D
claude
```

Y dentro:

```
Lee AGENTS.md y resúmeme la arquitectura. Dime qué te falta saber.
```

**No ejecutes `/init`.** Ese comando genera un `CLAUDE.md` analizando el
repositorio, y aquí ya existe algo mejor: un `AGENTS.md` escrito a mano con
las siete reglas y las trampas concretas de este proyecto. Dejar que lo
regenere sería cambiar conocimiento ganado con esfuerzo por un resumen
automático.

Pulsa **Shift+Tab** hasta entrar en **plan mode** antes de cualquier tarea
no trivial.

---

## 6. Los comandos del proyecto

Escritos para este repositorio, en `.claude/commands/`:

| Comando | Para qué |
|---|---|
| `/test` | Ejecuta la suite y resume **solo** lo que falla, sin corregir nada |
| `/validar` | Revisa si los cambios numéricos tienen referencia externa o son instantáneas |
| `/revisar` | Revisión de la rama contra las siete reglas |
| `/feature <nombre>` | Arranca una feature creando su especificación SDD antes de tocar código |
| `/release <versión>` | Sube números, changelog y verificación |

Y tres *skills* que el agente carga solo cuando aplican, en
`.claude/skills/`: **geotecnia** (convenios de signo, unidades, fuentes de
cada formulación y las trampas que ya costaron caro), **gui-pyside6** (lo
que rompe los tests sin avisar) y **tests-numericos** (cómo se valida un
número aquí).

---

## 7. Rutina diaria

```bash
claude -c                    # continúa la sesión anterior
```

- **Shift+Tab** → plan mode antes de nada serio.
- **`@archivo`** para meter contexto: `@ogr_slip2d/methods.py` tokeniza
  mejor que pegar el archivo.
- **`/compact`** cuando la conversación se alarga; **`/clear`** al cambiar
  de tarea. Contexto sucio degrada todo lo que venga después.
- **`/cost`** dos veces al día.
- **Opus** para arquitectura y matemática, **Sonnet** para el día a día,
  **Haiku** para renombrar y formatear.

---

## 8. Antes de cada commit

1. `QT_QPA_PLATFORM=offscreen python tests/_runner.py` en verde.
2. `/revisar` para pasar las siete reglas.
3. Lee el diff **entero**. Lo que no entiendas, pídelo explicado: quien
   firma el proyecto eres tú, no el agente.
4. Comprueba que no se cuela nada de `ogr-referencias/`:
   `git status --porcelain | grep -i refer` no debe devolver nada.

---

## 9. Publicar en GitHub

El repositorio ya está listo: CI en GitHub Actions, plantillas de
incidencia, `CONTRIBUTING.md`, `CLA.md` y la licencia AGPL íntegra.

```bash
cd ~/proyectos/OGR-Slip2D
git add -A
git commit -s -m "OGR Slip2D v0.1.59"
git remote add origin https://github.com/samuelsl27/OGR-Slip2D.git
git push -u origin main
```

Después, en la configuración del repositorio: activa **Issues**, pon la
descripción y el enlace a opengeorock.org, y añade los temas `geotechnical`,
`slope-stability`, `finite-elements`, `python`, `qt`, `open-source`.

Una comprobación que merece la pena hacer **antes** del primer `push`:

```bash
git ls-files | grep -iE "referen|\.pdf$" || echo "limpio"
```

---

© 2026 Samuel Sáez López — UPCT — AGPL-3.0-or-later
