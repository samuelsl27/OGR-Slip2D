---
description: Revisión de la rama actual contra las siete reglas del proyecto
---
Eres un revisor senior de este proyecto. Para la rama actual:

1. Lista los archivos cambiados (`git diff --name-only`).
2. Para cada uno, comprueba las **siete reglas de AGENTS.md**:
   - validación contra referencia externa
   - todo texto visible en `tr()` con su traducción española
   - toda acción nueva alcanzable desde un menú
   - cabecera SPDX presente
   - sin fugas de estado global en tests
   - anomalías reportadas, no tapadas
   - ningún ajuste que no haga nada
3. Busca además: diálogos modales en rutas que un test recorra, mutación
   del proyecto del usuario dentro de un cálculo, y tolerancias absolutas
   donde deberían ser relativas.

Devuelve markdown con severidad **alta / media / baja** y, en cada punto,
la línea concreta. Si no encuentras nada en una regla, dilo explícitamente
en lugar de omitirla.
