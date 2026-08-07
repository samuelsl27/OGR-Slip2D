# OGR Suite v0.1.47 — Changelog

**Lanzamiento:** 6 de agosto de 2026
**Desarrollador:** Samuel Sáez López — Estudiante de Doctorado, UPCT
**Licencia:** AGPL-3.0-or-later

> **Fase D3: informe de problemas y corrección asistida.** Con esto el
> **importador de DXF queda completo**: las cuatro fases terminadas.

---

## 🆕 Panel de problemas

Un import que anuncia «3 problemas encontrados» y se cierra no ha dicho
casi nada: **un hueco de unos milímetros en un modelo de cien metros no se
encuentra desplazando la vista**. Esta fase convierte cada problema en algo
sobre lo que se puede actuar.

- **Agrupados por tipo** y ordenados con los **errores primero**, porque
  «falta el contorno externo» y «un material queda colgando» exigen
  respuestas muy distintas.
- **Seleccionar uno centra el lienzo en él**; con doble clic o *Ir al
  problema* se acerca todavía más. Recorrer la lista con las flechas del
  teclado va paseando el modelo por los puntos conflictivos.
- **Consejo específico por tipo**, que nombra **qué ajuste cambiar y en
  qué sentido** — la información que si no habría que deducir. Hay un test
  que exige que los consejos de los problemas de cierre mencionen
  explícitamente la tolerancia de soldadura.
- **No modal**: permanece abierto mientras se edita el modelo, así los
  problemas se resuelven uno a uno.

El texto de los consejos vive en el panel y no en el saneador: **el motor
registra hechos, la interfaz los explica**.

## 🎯 El desajuste de áreas, inyectado como problema principal

El saneador **no puede** conocerlo: solo emerge cuando se construyen las
regiones, después de que él haya terminado. Pero es lo más importante que
se le puede decir al usuario —significa que alguna región no cerró—, así
que el panel lo inserta como **primer problema y con severidad de error**,
con el consejo de aumentar la tolerancia de soldadura.

## 🆕 `zoom_to_point` en el lienzo

Centra la vista en una coordenada del modelo con un margen proporcional,
para que el entorno siga siendo reconocible en lugar de llenar la pantalla
con un solo vértice. **Preserva el volteo vertical** de la transformación:
el modelo tiene la y hacia arriba y dejar que `fitInView` lo reinicie
pondría el dibujo del revés — hay un test dedicado a ello.

## 🔗 Integración

Tras importar, si algo quedó sin resolver el panel se abre solo. Si ya
estaba abierto, se **refresca** en lugar de duplicarse.

## 📊 Tests

**908 tests, 908 verdes** (+21 desde v0.1.46; suite 100 % desde v0.1.21).

Cobertura (`tests/test_dxf_problems_v147.py`): contenido del panel
(todos los problemas listados, agrupados por tipo, extremos colgantes en
un solo grupo, **errores primero**, coordenadas mostradas, cabecera que
cuenta errores aparte, e importación limpia que lo dice en lugar de
mostrar una lista vacía); consejos (todos los tipos conocidos tienen uno,
**nombran el ajuste a cambiar**, se muestran al seleccionar, y un tipo
desconocido no rompe); navegación (seleccionar centra, *Ir al problema*
acerca, **el volteo vertical se preserva**, *Ver todo* restaura, una fila
de grupo no tiene ubicación, y el panel sin lienzo no falla); inyección
del desajuste de áreas (aparece el primero y con severidad de error;
áreas coincidentes no añaden nada); y `zoom_to_point` (centra, conserva
orientación, y el margen controla el acercamiento).

## 🏁 Importador DXF completo

| Fase | Contenido | Versión |
|---|---|---|
| D0 | Lector y catálogo de capas | v0.1.44 |
| D1 | Saneador de geometría | v0.1.45 |
| D2 | Diálogo de importación | v0.1.46 |
| D3 | **Informe de problemas** | **v0.1.47** |

Con esto se cierra **el último punto pendiente de la auditoría**: agua
subterránea, probabilístico, retroanálisis, i18n, A3, A5 e import DXF,
todos terminados.

## ⏳ Posibles siguientes pasos

Export DXF, base de datos de materiales (OGR Data), instaladores, o
profundizar en la validación con casos de referencia adicionales.

---

© 2026 Samuel Sáez López — UPCT — AGPL-3.0-or-later
