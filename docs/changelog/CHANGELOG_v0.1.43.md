# OGR Suite v0.1.43 — Changelog

**Lanzamiento:** 5 de agosto de 2026
**Desarrollador:** Samuel Sáez López — Estudiante de Doctorado, UPCT
**Licencia:** AGPL-3.0-or-later *(cambio en esta versión)*

> **Cambio de licencia a AGPL-3.0-or-later**, con acuerdo de contribución
> (CLA) para conservar la opción de un servicio alojado comercial.

---

## ⚖️ De GPL-3.0 a AGPL-3.0-or-later

El objetivo declarado era: uso libre y gratuito, **incluido el trabajo de
ingeniería facturable**, sin pagar ni publicar nada; pero quien lo
convierta en un **servicio web público de pago** debe compartir su código.
Eso es exactamente la **sección 13** de la AGPL, que la GPL no cubre: bajo
GPL, ofrecer un servicio en red no cuenta como distribución y no obliga a
publicar nada.

Aplicado en:

- **`LICENSE`** — texto AGPL con explicación práctica de qué permite y qué
  exige, y un **aviso destacado** de que el texto íntegro debe descargarse
  de gnu.org antes de publicar (el entorno de compilación no tenía red).
  Distribuir una obra AGPL **sin** el texto completo incumple su propia
  sección 4, así que el aviso es sustantivo, no cosmético.
- **`pyproject.toml`** — identificador y clasificador OSI.
- **Los 167 archivos `.py`** — cabecera `SPDX-License-Identifier:
  AGPL-3.0-or-later` más línea de copyright, en las primeras líneas, que
  es donde la miran las herramientas automáticas de licencias.
- **`README.md`** — sección que explica el efecto práctico en dos puntos.

Se verificó que **ninguna dependencia lo impide**: PySide6 es LGPL, y
numpy, scipy, shapely, ezdxf, matplotlib y el resto son permisivas.

## 📝 `CLA.md` — la pieza que faltaba

Como titular del copyright, el autor no está vinculado por su propia
licencia y puede ofrecer el código bajo términos comerciales
adicionalmente. **Esa opción desaparece en cuanto llega una contribución
externa sin acuerdo**: el parche es propiedad de quien lo escribe y está
bajo AGPL, de modo que la obra combinada ya no podría ofrecerse con otros
términos.

El CLA lo resuelve sin quitarle nada al contribuyente: concede una
licencia amplia (que incluye relicenciar) **conservando el contribuyente
su copyright** — es una licencia, no una cesión — y garantizando que toda
contribución permanece en la versión libre AGPL. Se documenta también qué
**no** significa, y se ofrece expresamente la vía de contribuir *sin* la
cláusula de relicencia, marcando entonces el límite en el código.

Instrucciones de aceptación vía `CONTRIBUTORS.md` y `git commit -s`
(Developer Certificate of Origin), pensando en el paso a GitHub.

## 🔒 Tests de coherencia de licencia

Los metadatos de licencia se desincronizan en silencio: un archivo nuevo
sin cabecera, o un identificador antiguo olvidado en el empaquetado, y el
proyecto distribuye términos contradictorios. `tests/test_license_v143.py`
lo convierte en fallo de compilación:

- **todo** archivo fuente declara el SPDX, y **en las primeras líneas**;
- **ningún** identificador GPL sobrevive en ninguna parte;
- toda fuente lleva línea de copyright;
- `pyproject.toml` declara AGPL y **no** queda GPL residual;
- el `LICENSE` es AGPL y **el aviso del stub es visible**;
- el CLA contiene los puntos esenciales que un contribuyente debe poder
  encontrar (conserva su copyright, permite otros términos, no es cesión);
- el README explica el efecto práctico.

## 📊 Tests

**803 tests, 803 verdes** (+11 desde v0.1.42; suite 100 % desde v0.1.21).

## ⚠️ Antes de publicar en GitHub

1. **Sustituir el `LICENSE`** por el texto íntegro de
   <https://www.gnu.org/licenses/agpl-3.0.txt>. El test comprueba que el
   aviso siga visible mientras no se haga.
2. Los changelogs anteriores a esta versión mencionan GPL-3.0: se dejan
   **sin tocar a propósito**, porque registran lo que era cierto en cada
   momento. El cambio queda documentado aquí.

## ⏳ Siguiente

**Import DXF** — plan por fases en `docs/PLAN_IMPORT_DXF.md`, con las
decisiones de diseño ya cerradas.

---

© 2026 Samuel Sáez López — UPCT — AGPL-3.0-or-later
