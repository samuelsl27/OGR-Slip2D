# Plan de implementación

## Enfoque

Un **modo de rotura más** dentro de `PileMicropile`, no un tipo nuevo. Es lo que
hace la referencia —el pilote tiene tres modos: *Shear*, *Ito & Matsui* y
*EFW*— y es lo que evita duplicar orientación, aplicación y espaciamiento, y
tocar las dos tablas que congelan el catálogo de tipos.

La fuerza no es un parámetro: es la **integral de una presión que depende de la
profundidad y del suelo**. Esa dependencia ya tiene camino en este programa
desde v0.1.116 (D19): un tipo declara `NEEDS_BOND_PROFILE`, el motor le construye
un perfil muestreado a lo largo del soporte **una vez por análisis**, y
`force_at` lo integra. Lo que cambia aquí es **qué** transporta el perfil: no una
resistencia de interfaz sino la fuerza lateral por unidad de profundidad.

El punto de aplicación —en el corte o en el centroide del diagrama— entra por la
maquinaria del **par** que D28 construyó, sin tocarla.

## Archivos que se tocan

| Archivo | Qué cambia |
|---|---|
| `ogr_core/support/ito_matsui.py` | **nuevo** — Ecs. (13), (14) y (23), el conmutador y las guardas |
| `ogr_core/support/support.py` | `PileMicropile`: modo, diámetro, punto de aplicación, `interface_tau`, `force_at`, `resultant_arm`, `NEEDS_BOND_PROFILE` por instancia |
| `ogr_core/support/__init__.py` | exportar las funciones puras |
| `ogr_core/support/bond.py` | docstring: qué transporta el perfil cuando no es una interfaz |
| `ogr_slip2d/support_notes.py` | **nuevo** — la nota del punto de aplicación, generalizada |
| `ogr_slip2d/retaining_wall_notes.py` | delega esa nota; se queda con la del muro plano |
| `ogr_slip2d/ito_matsui_notes.py` | **nuevo** — agua, `q < 0`, pilote no vertical, pilotes que se tocan |
| `ogr_slip2d/analysis_runner.py` | engancha las notas nuevas |
| `ogr_gui/dialogs/define_support_dialog.py` | `_CHOICES["failure_mode"]` |
| `ogr_gui/i18n/__init__.py` | traducciones |
| `tests/test_i18n_coverage_v141.py` | «Ito & Matsui» a la lista blanca, con su razón |
| `tests/test_efp_wall_v1122.py` | el texto de la nota generalizada |
| `docs/plugins.md` | los dos renglones caducados de D28 y la declaración nueva |
| `tests/test_ito_matsui_pile_v1123.py` | **nuevo** |
| `docs/changelog/CHANGELOG_v0.1.123.md` | **nuevo** |
| Los **siete** sitios de versión | 0.1.122 → 0.1.123 |

## Decisiones de diseño

**Modo, no tipo.** El encargo pedía «un tipo de soporte más». La referencia lo
resuelve como modo de rotura del pilote, y AGENTS.md dice que su documentación se
lee precisamente para saber **cómo debe comportarse la interfaz**. Como modo, la
orientación por defecto (tangencial) y la aplicación (pasiva) siguen siendo las
del pilote, y las tablas congeladas de `test_support_orientation_v1112.py` y
`test_supports_v114.py` no se mueven.

**La división por `D₁` la deciden las unidades.** `q` es fuerza por unidad de
profundidad **por pilote**; OGR necesita kN por metro de ancho de talud. Sólo
`Q/D₁` tiene esas unidades, y es lo que escribe Cai y Ugai en su Ec. (9). La
página de ayuda de la referencia dice que el espaciamiento «no es un cálculo
aparte», lo que admite las dos lecturas; las unidades no.

**La ecuación general es singular en φ = 0 y hay que conmutar.** Los divisores
`Nφ·tanφ` y `√Nφ·tanφ + Nφ − 1` tienden a cero con φ, y los dos sumandos de
orden `c·D₁/φ` se cancelan: el límite existe y **es** la Ec. (23), pero en coma
flotante es una cancelación catastrófica. Por debajo del umbral se evalúa la
(23), y un test comprueba que el empalme no salta.

**`NEEDS_BOND_PROFILE` pasa a ser por instancia.** Un pilote en modo *Shear* no
puede pagar un perfil de 50 muestras por análisis para un número que nadie lee.
Los tres lectores del programa lo consultan con `getattr` sobre la instancia, así
que una property basta y no hay que tocarlos.

**σ'_v, no γz.** Ito y Matsui escriben γz porque en su artículo no hay agua en
ninguna parte, y la deducción es la presión activa de Rankine, que con parámetros
efectivos se escribe sobre la tensión vertical **efectiva**.
`sigma_v_effective_at` ya la da con la misma descomposición banda a banda que el
peso de dovela. Cuando hay presión intersticial sobre el pilote, el análisis lo
dice.

**c y φ equivalentes salen de la misma linearización que usan los nueve
métodos.** La referencia habla de «la cohesión y el ángulo de rozamiento del
suelo *(o valores equivalentes)*». `BishopSimplified._local_c_phi` es la única
linearización de envolvente del programa; reutilizarla mete los veinte modelos
constitutivos en vez de sólo Mohr-Coulomb, y un test de identidad ata las dos.

**La nota del punto de aplicación se generaliza en vez de duplicarse.** D28 la
dejó dentro del módulo del muro; ahora hay dos tipos que ofrecen el ajuste. Una
regla en dos sitios se queda obsoleta en uno de ellos.

## Orden de trabajo

1. Las tres ecuaciones puras y sus identidades analíticas, **antes** de tocar el
   motor: si la transcripción está mal, todo lo demás mide otra cosa.
2. La **puerta (a)** del banco —el talud sin pilote contra Bishop 1,13—, que
   mide OGR y no Ito-Matsui, y que si falla invalida lo que venga después.
3. El modo dentro del tipo, el perfil y el punto de aplicación.
4. Las notas, el diálogo y las traducciones.
5. La **puerta (b)**, con las dos orientaciones medidas.
6. La suite entera, sin argumentos.
