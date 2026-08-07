# OGR Suite v0.1.51 — Changelog

**Lanzamiento:** 6 de agosto de 2026
**Desarrollador:** Samuel Sáez López — Estudiante de Doctorado, UPCT
**Licencia:** AGPL-3.0-or-later

> **Fase M1: Data Tips y configuración de forzado.** Incluye una
> **corrección de la auditoría anterior**, que daba por ausente algo que
> ya estaba implementado.

---

## 🔴 Corrección de la auditoría: el forzado ya existía

La auditoría de v0.1.48 listaba **Snap / Ortho / OSnap como no
implementado**, y era falso. Al ir a construirlo apareció
`ogr_gui/canvas/snap_engine.py` — **355 líneas** — con más alcance del
planificado: vértice, línea, rejilla, ortogonal separado en horizontal y
vertical, y **forzado a extensiones de segmento**, que ni siquiera estaba
previsto. La barra de estado ya llevaba las palabras SNAP / GRID / ORTHO /
OSNAP conectadas al motor.

**Por qué falló la auditoría**: buscó la funcionalidad por su nombre sobre
el árbol de archivos y contó coincidencias, **sin leer qué hacía** el
código encontrado. Un recuento de archivos no es una auditoría.

Se había escrito además un motor nuevo que lo duplicaba;
**descartado**, y el plan corregido en consecuencia.

Lo que faltaba de verdad, y es lo que añade esta versión: el **diálogo de
configuración**, las teclas **F3 / F8 / F9**, y los **Data Tips**.

## 🆕 Data Tips

Pedidos en el **párrafo de apertura** del prompt inicial —«al pasar el
cursor por encima de los materiales salgan las principales propiedades, en
los soportes igual, y las fuerzas también»— y hasta ahora inexistentes.

Tres modos: **ninguno**, **mínimo** (solo la identidad: bastante para
distinguir dos objetos mientras se dibuja, sin un muro de texto siguiendo
al cursor) y **máximo** (lista completa).

El texto se construye en `ogr_gui/data_tips.py`, **fuera del lienzo**,
para poder probarlo sin pantalla y reutilizar la redacción en informes.

Detalles que cambian su utilidad:

- **Los valores llevan unidades**: una cohesión sin kPa no es información.
- **Magnitudes pequeñas en notación científica**: una permeabilidad
  escrita `0.0000010` no dice nada.
- **Precedencia deliberada**: cargas primero, luego soportes, luego la
  región de material, y por último el contorno más cercano. Una flecha de
  carga sobre una región debe describir la flecha — el material está en
  todas partes, la flecha solo ahí.
- **Una región sin material asignado también se reporta** («region 2 — no
  material assigned»), porque el silencio parecería que el tip está roto.
- El radio de captura es un número constante de **píxeles** convertido a
  unidades del modelo, así que un tip cuesta lo mismo acertar a cualquier
  zoom.

## 🆕 Diálogo *Snap*

Expone lo que el motor ya soportaba y no se podía tocar: las tres
restricciones, el **espaciado de rejilla**, las **tolerancias de captura
por tipo** (vértice, línea, nodo de rejilla, extensión), la **ventana
angular del modo ortogonal** y el modo de Data Tips.

Las tolerancias van **en píxeles de pantalla, y el diálogo lo dice**: el
lienzo las convierte a unidades del modelo, que es lo que mantiene el
forzado igual de cómodo a cualquier zoom. Etiquetarlo evita que alguien
las «corrija» a metros y empeore el comportamiento al alejar la vista.

## ⌨️ F3 / F8 / F9, con una sola fuente de verdad

Solo la rejilla tenía tecla (F7). Ahora F9 fuerza a rejilla, F8 ortogonal
y F3 a objeto — y las teclas **actúan a través de las palabras de la barra
de estado**, no del motor directamente, de modo que pulsar la tecla mueve
la palabra y hacer clic en la palabra mueve el motor: **un solo sitio
sostiene el estado**. Hay un test que lo comprueba en ambos sentidos.

La barra de estado gana un método `add_toggle`, porque venía con sus
cuatro palabras fijas en el constructor y las fases siguientes querrán
más.

## 📊 Tests

**1035 tests, 1035 verdes** (+34 desde v0.1.50; suite 100 % desde
v0.1.21).

Cobertura (`tests/test_m1_datatips_snap_v151.py`): tips de material
(propiedades, **unidades**, modo mínimo de una sola línea, modo ninguno,
modelo de resistencia nombrado, material ausente, **notación científica**);
tips de contorno, carga y soporte; `tip_at` (contorno bajo el cursor,
**región sin material reportada**, **la carga gana sobre la región**, vacío
lejos de todo, cortocircuito en modo ninguno); barra de estado (indicador
añadido, controla el modo, `add_toggle` idempotente, tooltip puesto y
limpiado); **teclas y motor sincronizados en ambos sentidos**; y diálogo
(muestra los ajustes, los escribe de vuelta, recoge el modo de tips,
ofrece los tres modos, **tolerancias etiquetadas en píxeles**, restaurar
valores, y las palabras se actualizan al aceptar).

## ⏳ Siguiente

**Fase M2 — Project Settings**: las cinco páginas que faltan (Transient,
Statistics, Random Numbers, Design Standard, Advanced). Después **I3**,
las 21 entradas de menú de Interpret pendientes.

---

© 2026 Samuel Sáez López — UPCT — AGPL-3.0-or-later
