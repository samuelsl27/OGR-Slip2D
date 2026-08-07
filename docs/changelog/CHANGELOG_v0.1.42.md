# OGR Suite v0.1.42 — Changelog

**Lanzamiento:** 2 de agosto de 2026
**Desarrollador:** Samuel Sáez López — Estudiante de Doctorado, UPCT

> 🔴 **Corrección importante: módulos completos pero inalcanzables.** Los
> menús de agua subterránea, estadística y retroanálisis existían por
> entero y estaban probados, pero **no se habían añadido a la barra de
> menús**, así que no había forma de llegar a ellos.

---

## 🔴 El fallo

Samuel señaló que no veía la interfaz del módulo de agua. Al comprobarlo,
la interfaz **existía completa** — cinco diálogos y una ventana de
interpretación, unas 1.400 líneas — y sus acciones estaban registradas…
pero **ninguna se había añadido a un menú visible**:

```
ACCIONES REGISTRADAS PERO NO EN NINGÚN MENÚ:
gw_hydraulic, gw_bcs, gw_compute, gw_interpret, gw_transient,
stat_vars, stat_compute, stat_show, back_analysis, wp_grid,
gen_mesh, reset_mesh
```

Doce acciones inalcanzables: **todo el módulo de agua (Fases 0–6), todo
el probabilístico (P0–P5) y el retroanálisis de soporte**. Implementados,
validados, con 792 tests verdes… y sin puerta de entrada. Un fallo de
integración por mi parte, no del código de cada módulo.

Al añadir la comprobación apareció una decimotercera: `assign_material`,
la herramienta de asignar material haciendo clic en una región.

## 🔧 La corrección

Dos menús nuevos de primer nivel, siguiendo la disposición de la
referencia, con **Groundwater ordenado por el flujo de trabajo real**:

```
Groundwater
  Define Hydraulic Properties...
  Water Pressure Grid...
  Mesh ▸ Generate FE Mesh... / Reset FE Mesh
  Set Boundary Conditions...
  Transient Groundwater...
  Compute Groundwater
  Interpret Groundwater

Statistics
  Random Variables...
  Compute Statistics
  Show Statistics
```

**Back Analysis of Support Force** va al menú *Support*, donde la sitúa la
referencia, y **Assign Material** al menú *Properties*.

## 🔒 Lo que impide que se repita

`tests/test_menu_reachability_v142.py` **recorre la barra de menús real**
(submenús incluidos) y exige que toda acción registrada sea alcanzable.
Un módulo nuevo sin punto de entrada hace fallar la suite en vez de
pasar desapercibido. Se verifica además el **orden** del menú
Groundwater (propiedades → condiciones → calcular → interpretar), que
Back Analysis esté en Support, y que los nombres de menú sean traducibles.

## 🔴 Fuga de estado entre tests, detectada de paso

Los tests de menú pasaban aislados y fallaban en la suite completa: el
test de i18n dejaba el idioma en **español**, con lo que los menús se
llamaban «Soporte» y «Agua subterránea» y las búsquedas por nombre no
encontraban nada. Corregido por ambos lados: el test de i18n **restaura
el inglés** al terminar, y el de menús **fija el idioma explícitamente**
en lugar de heredarlo. Es el tipo de acoplamiento que solo aparece al
ejecutar todo junto.

## 📊 Tests

**792 tests, 792 verdes** (+6 desde v0.1.41; suite 100 % desde v0.1.21).

---

© 2026 Samuel Sáez López — UPCT
