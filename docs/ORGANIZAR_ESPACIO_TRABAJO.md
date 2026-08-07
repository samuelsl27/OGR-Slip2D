# Organizar tu carpeta de trabajo

Partiendo de lo que tienes hoy en `C:\Samuel\OpenGeoRock_slip2d\`.

---

## 1. El nombre: dos niveles, no uno

Tienes razón en la distinción, y el proyecto la tenía mal puesta: el
paquete se llamaba `ogr-suite` cuando contiene un solo programa. Corregido
en v0.1.59.

| Nivel | Qué es | Nombre |
|---|---|---|
| **Suite** | El paraguas: cinco programas planificados, la marca, la web | **OpenGeoRock** / OGR Suite |
| **Programa** | Lo que estás construyendo ahora | **OGR Slip2D** |

Por tanto:

- Carpeta raíz de trabajo: `C:\Samuel\OpenGeoRock\`
- Repositorio del programa: `OGR-Slip2D`
- Paquete Python instalable: `ogr-slip2d`
- Repositorio de la web: `web-OGR`, **separado**

### ¿Un repositorio por programa o un monorepo?

Recomiendo **un repositorio por programa**, empezando por `OGR-Slip2D`, y
que el núcleo compartido (`ogr_core`) viva **dentro de Slip2D por ahora**.

El motivo es que extraer `ogr-core` a su propio paquete tiene un coste real
—dos repositorios que versionar, publicar y mantener sincronizados— y ese
coste solo se paga cuando existe un **segundo** programa que lo use. Hoy no
existe. Separarlo ahora sería resolver un problema que aún no tienes,
pagando desde el primer día.

Cuando arranque OGR Data o OGR FEM2D, entonces sí: se extrae `ogr-core` a
su repositorio y los dos programas lo declaran como dependencia. Es un
movimiento mecánico si el código ya respeta la separación motor/interfaz,
que la respeta.

---

## 2. Estructura propuesta

```
C:\Samuel\OpenGeoRock\
│
├── OGR-Slip2D\                    ← REPOSITORIO GIT → GitHub público
│   ├── ogr_core\  ogr_slip2d\  ogr_fem2d\  ogr_gui\  ogr_cli\
│   ├── tests\
│   ├── validacion\casos\          ← casos de validación (SÍ se versiona)
│   ├── spec\  docs\  .claude\  .vscode\
│   ├── AGENTS.md  README.md  LICENSE
│   └── .venv\                     (ignorado)
│
├── web-OGR\                       ← REPOSITORIO GIT SEPARADO → GitHub Pages
│
├── referencias\                   ← NO se versiona nunca
│   ├── documentacion-guia\        ← tu Documentacion_Guia
│   ├── articulos\                 ← papers (Bishop, Spencer, Hoek…)
│   └── comparaciones\             ← salidas crudas de software comercial
│
├── historico\                     ← NO se versiona
│   ├── versiones-claude-desktop\  ← tu Versiones_Claude_Desktop
│   └── prompts\                   ← tu Pronts
│
└── OGR-Slip2D.code-workspace
```

### Qué cambia respecto a lo que tienes

| Carpeta actual | Destino | Por qué |
|---|---|---|
| `Documentacion_Guia` | `referencias/documentacion-guia/` | Material de terceros: nunca al repositorio |
| `Ejemplos` | **se parte en dos** — ver abajo | Es lo más valioso que tienes y merece tratamiento aparte |
| `Pronts` | `historico/prompts/` | Histórico. No hace falta que el agente lo lea |
| `Versiones_Claude_Desktop` | `historico/versiones-claude-desktop/` | Referencia arqueológica; el repositorio ya es la versión viva |
| `web_OGR` | `web-OGR/`, repositorio propio | Ciclo de vida distinto: la web cambia sin que cambie el motor |

---

## 3. `Ejemplos` se parte en dos, y esto es lo importante

Los casos comparados son **lo más valioso del proyecto**, más que cualquier
función nueva. Pero no todo puede ir al repositorio:

**Al repositorio** (`OGR-Slip2D/validacion/casos/NNN-nombre/`):
- `modelo.ogr` — tu modelo. Es tuyo.
- `esperado.json` — los valores de referencia con su fuente. Un número es
  un hecho citable.
- `caso.md` — geometría, materiales y de dónde sale el valor.

**Fuera** (`referencias/comparaciones/`):
- Los archivos nativos del software comercial.
- Sus informes PDF y capturas.

La frontera es de copyright: el `.ogr` y el número son tuyos; el archivo
nativo y el informe de otro programa son material de terceros.

Y una distinción que conviene tener clara desde el principio: **una
comparación no es una validación**. Que Slip2D y otro programa den 1.372
significa que coinciden, no que acierten — dos programas pueden equivocarse
igual. Solo un valor publicado o una solución analítica es referencia de
verdad. La plantilla de `caso.md` te obliga a marcar de qué tipo es cada
uno.

El test `tests/test_validation_cases.py` recorre todos los casos
automáticamente: **añadir uno no requiere escribir código**. Eso es
deliberado, porque la fricción de escribir un test es justo lo que impide
que se añadan casos.

---

## 4. Los comandos para montarlo

En PowerShell, desde `C:\Samuel\`:

```powershell
# Carpeta raíz con el nombre de la suite
New-Item -ItemType Directory OpenGeoRock
cd OpenGeoRock

# Referencias e histórico (fuera del repositorio)
New-Item -ItemType Directory referencias\documentacion-guia
New-Item -ItemType Directory referencias\articulos
New-Item -ItemType Directory referencias\comparaciones
New-Item -ItemType Directory historico\prompts
New-Item -ItemType Directory historico\versiones-claude-desktop

# Mover lo que ya tienes
Move-Item ..\OpenGeoRock_slip2d\Documentacion_Guia\*      referencias\documentacion-guia\
Move-Item ..\OpenGeoRock_slip2d\Pronts\*                  historico\prompts\
Move-Item ..\OpenGeoRock_slip2d\Versiones_Claude_Desktop\* historico\versiones-claude-desktop\
Move-Item ..\OpenGeoRock_slip2d\Ejemplos\*                referencias\comparaciones\
Move-Item ..\OpenGeoRock_slip2d\web_OGR                   web-OGR
```

Después descomprime el ZIP de la versión como `OGR-Slip2D\` y coloca
`OGR-Slip2D.code-workspace` en `C:\Samuel\OpenGeoRock\`.

---

## 5. Dar acceso al agente

`OGR-Slip2D\.claude\settings.local.json` (no se versiona):

```json
{
  "permissions": {
    "additionalDirectories": [
      "C:\\Samuel\\OpenGeoRock\\referencias\\",
      "C:\\Samuel\\OpenGeoRock\\web-OGR\\"
    ]
  }
}
```

**Referencias sí; `historico/` no.** Los prompts antiguos y las versiones
previas confundirían más que ayudarían: el agente leería decisiones ya
revisadas y código ya sustituido, y no tiene forma de saber qué sigue
vigente. Si algún día necesitas consultar algo de ahí, añádelo para esa
sesión con `claude --add-dir`.

La web sí conviene, para que pueda mantener coherentes el README y el sitio.

---

## 6. Los dos repositorios en GitHub

| Repositorio | Contenido | Por qué separado |
|---|---|---|
| `OGR-Slip2D` | El programa | Es lo que se instala y lo que se audita |
| `web-OGR` | El sitio | Cambia de forma independiente, y un `git log` mezclado hace ilegible la historia de ambos |

Cuando llegue el segundo programa, `OGR-Data` será un tercer repositorio y
`ogr-core` un cuarto. La cuenta de GitHub actúa entonces como la suite, con
un repositorio `.github` o `OpenGeoRock` que sirva de índice.

---

## 7. Comprobación antes del primer push

```powershell
cd OGR-Slip2D
git ls-files | Select-String -Pattern "referen|\.pdf$|Documentacion"
```

Si devuelve algo, **no publiques**: hay material de terceros en el índice.

---

© 2026 Samuel Sáez López — UPCT — AGPL-3.0-or-later
