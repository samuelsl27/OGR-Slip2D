# Plan de implementación

El plan detallado, revisado por un revisor adversario contra el código (25 objeciones incorporadas), está
aprobado. Aquí van el enfoque, la derivación que sustituye a la fuente que falta, los archivos, las decisiones
y los riesgos.

## Enfoque

Son ocho versiones, una por commit, y cada una se publica con la suite entera en verde. **Desde el 2026-11-06 las
siete del método van de 0.1.444 a 0.1.450:** la propietaria decidió arreglar antes los once defectos que encontró
la revisión de 0.1.427 (tanda P10, D396–D404), y esta spec se renumeró +9 en el commit de 0.1.428. La revisión de
0.1.429 añadió a la tanda dos fichas más, D405 en 0.1.430 y D406, y la spec se renumeró +2 en el commit de 0.1.429.
La de 0.1.430 añadió D408 (el informe PDF de una corrida Ky) y D409 (a qué kh es el factor que Interpretar llama
FS(0)); la spec se renumeró +2 en el commit de 0.1.430. La de 0.1.432 añadió D411 (el inglés en pantalla que ningún
censo veía) en 0.1.433, detrás de D399; la spec se renumeró +1 en el commit de 0.1.432. Al planificar D411, la
propietaria la partió en dos (D411 y D412, en 0.1.434), y en la revisión de 0.1.433 abrió D413 (cinco cuestiones de
diseño de la estadística y de los nombres por defecto) en 0.1.435; la spec se renumeró +2 en el commit de 0.1.433: la
tanda P10 va de 0.1.428 a 0.1.443.

| Versión | Qué |
|---|---|
| 0.1.427 | Superficies no circulares del usuario. No depende del método |
| 0.1.444 | El solver, puro y sin registrar |
| 0.1.445 | Las cuñas: rebanado no vertical y cargas |
| 0.1.446 | El método registrado, con sus ajustes y una ventana que no engaña |
| 0.1.447 | Los datos por vértice, de punta a punta |
| 0.1.448 | Interpret con cuñas |
| 0.1.449 | La herramienta de ángulos con el ratón |
| 0.1.450 | Los ángulos optimizados |

Después, el banco cierra D357.

## La derivación (sustituye a Sarma 1979, no consultado)

**Convenio.**
- Se desliza hacia −x; una masa que desliza hacia +x se refleja (x → −x y θ → 180° − θ).
- Cuñas i = 1…n desde el pie, entre la cara i (la del pie) y la cara i+1.
- Base de la cuña: α positivo subiendo hacia +x, longitud l. Vectores t = (cos α, sen α) y n = (−sen α, cos α).
- Cara: δ desde la vertical, positivo si su tope se inclina hacia +x, longitud d, empuje de agua PW. Vectores
  s = (sen δ, cos δ) y m = (cos δ, −sen δ).
- Resistencias reducidas: c′ = c/F, tan φ′ = tan φ/F, y lo mismo en las caras (c̄′, φ̄′). Que F reduzca
  también las caras lo fijan los publicados.

**Fuerzas sobre la cuña i:**
- el peso: Wᵛ = W_suelo(1 + kv) + W_cargas, hacia abajo;
- el sismo: −kh·W_suelo en x (D170, D206);
- la fuerza exterior del tope: P (agua libre y cargas);
- la base: N′(n + tan φ′ t) + U n + c′ l t;
- la cara i: Eᵢ mᵢ + Xᵢ sᵢ;
- la cara i+1: −Eᵢ₊₁ mᵢ₊₁ − Xᵢ₊₁ sᵢ₊₁;
- con X = σ[(E − PW) tan φ̄′ + c̄′ d].
  - σ = +1 es el sentido fijo: la cuña de arriba baja respecto a la de abajo.
  - El cinemático lo da la compatibilidad de velocidades: Vᵢ = vᵢ(−tᵢ), con la componente normal común a
    cada cara.

**Proyección.** Se proyecta sobre v = (cos(φ′ − α), −sen(φ′ − α)), que es perpendicular a n + tan φ′ t, y así
desaparece N′. Queda:

```
Eᵢ₊₁ = aᵢ − pᵢ K + eᵢ Eᵢ
qᵢ    = cos(φ′ᵢ − αᵢ + φ̄′ᵢ₊₁ − δᵢ₊₁) / cos φ̄′ᵢ₊₁
aᵢ qᵢ = Wᵛᵢ sen(φ′ᵢ − αᵢ) + Pᵢ·vᵢ + Rᵢ cos φ′ᵢ + Sᵢ₊₁ sen(φ′ᵢ − αᵢ − δᵢ₊₁) − Sᵢ sen(φ′ᵢ − αᵢ − δᵢ)
pᵢ qᵢ = W_suelo,ᵢ cos(φ′ᵢ − αᵢ)
eᵢ qᵢ = cos(φ′ᵢ − αᵢ + φ̄′ᵢ − δᵢ) / cos φ̄′ᵢ
Rᵢ    = c′ᵢ lᵢ − Uᵢ tan φ′ᵢ
Sᵢ    = c̄′ᵢ dᵢ − PWᵢ tan φ̄′ᵢ
```

(con φ̄′ y c̄′ firmados por σ).

**Kc y F.**
- Con E₁ = 0 y Eₙ₊₁ = 0, o el empuje del agua de la grieta en la cara de cabeza:
  Kc(F) = Σ aᵢ ∏ⱼ₍ⱼ>ᵢ₎ eⱼ / Σ pᵢ ∏ⱼ₍ⱼ>ᵢ₎ eⱼ.
- F es la raíz MAYOR de Kc(F) = kh.
  - Se busca con H(F) = (N − kh·D)·∏qᵢ, que no tiene polos: barrido descendente y Brent.
  - Por encima de esa raíz Kc < kh, así que es la mínima reducción que lleva al equilibrio límite.
- Kc(F = 1) es la aceleración crítica de Sarma (1973).

**Comprobado en la planificación:**
- reproduce `cunas_sarma.py` al dígito en el 4;
- reproduce el 5 con el mismo sentido;
- da Janbu simplificado con δ = 0 y caras sin resistencia (≤ 5·10⁻¹³).

## Archivos que se tocan

| Versión | Archivo | Qué cambia |
|---|---|---|
| 0.1.427 | `ogr_core/geometry/user_polyline.py` | nuevo: `UserPolylineSurface` |
| 0.1.427 | `ogr_core/project/project.py`, `commands.py` | `user_polylines`, `.ogr` condicional, deshacer |
| 0.1.427 | `ogr_slip2d/search.py`, `surface.py` | evaluación en corridas no circulares; el ajuste de extremos baja del API |
| 0.1.427 | `ogr_api/ops/search_objects.py`, `ops/analysis.py`, `ogr_mcp/server.py`, `docs/mcp/herramientas.md` | `user_surface_add/delete` con polilíneas |
| 0.1.427 | `ogr_gui/main_window.py`, `canvas/canvas_view.py`, `canvas/tool_mode.py`, `i18n/__init__.py` | acciones, modo de dibujo, gestor y español |
| 0.1.444 | `ogr_slip2d/sarma/solver.py` | nuevo: recurrencia, raíz, sentido cinemático y motivos |
| 0.1.445 | `ogr_slip2d/sarma/wedges.py`, `angles.py` | nuevos: cuñas, cargas, factores de acción y resistencias de cara |
| 0.1.446 | `ogr_slip2d/methods/sarma.py`, `analysis_runner.py`, `search.py`, `checks.py`, `rapid_drawdown.py`, `slice_store.py`, `yield_acceleration.py` | registro y puertas del motor |
| 0.1.446 | `ogr_core/project/settings.py`, `ogr_api/settings_schema.py`, `ogr_api/results.py`, `ogr_cli/__main__.py` | `settings.sarma`, esquema, resultados y CLI |
| 0.1.446 | `ogr_gui/dialogs/project_settings_dialog.py`, `labels.py`, `ogr_api/render.py`, `report_generator.py` | casilla, grupo, tooltips y guardas |
| 0.1.447 | `user_polyline.py`, `ogr_api/ops/*`, `ogr_mcp`, `ogr_gui/dialogs/` | datos por vértice, `user_surface_edit` y tabla |
| 0.1.448 | `ogr_gui/interpret_window.py`, `report_generator.py` | cuñas en Interpret y en el informe |
| 0.1.449 | `ogr_gui/canvas/*`, `main_window.py` | herramienta de ángulos |
| 0.1.450 | `ogr_slip2d/sarma/optimize_angles.py` | nuevo: optimizador de ángulos |

## Decisiones de diseño

- **Recurrencia de Kc frente a resolver el sistema de 2n ecuaciones.**
  - La recurrencia es O(n) por evaluación (4,8 µs por cuña, medido).
  - El sistema directo es la forma de la herramienta del banco. Implementar el otro camino mantiene la
    herramienta como contraste independiente.
- **Dos entradas de `compute_fos`, frente a eximir a Sarma de la suite.**
  - `Wedges` usan el método completo.
  - Unas `Slices` verticales se leen como cuñas de δ = 0, con sus propios W, U y fuerzas.
  - Así se cumplen sin exención las identidades de la suite (W de las dovelas dadas, F/γ). Eximir habría dejado
    a Sarma fuera de los guardas de la regla 7.
- **Rebanar en vertical primero, frente a extraer la resolución de `slice_surface`.**
  - Se rebana en vertical primero: misma superficie resuelta, mismos motivos, mismos filtros y el mínimo de 3
    dovelas, y las cuñas se construyen después.
  - Extraer la resolución arriesgaría los números de los nueve métodos.
- **Sección `settings.sarma`, frente a campos planos `methods.sarma_*`.**
  - `MethodsSettings(**data)` revienta en versiones anteriores con una clave nueva; una sección desconocida se
    ignora.
  - Se escribe solo si se usa, para no mover `model_hash` ni la huella del banco.
- **Desembalse y B-bar: salto a nivel de corrida con una nota, frente a N superficies inválidas.**
  - Una condición de toda la corrida no se informa superficie por superficie (`search.py:1094-1097`).
  - El envoltorio de desembalse queda solo como red.
- **Raíz mayor, frente a marchar desde F = 1.** La marcha salta el 0,434 publicado del 4 saturado, que está
  junto a un polo, y devuelve 0,1467.
- **Normales efectivas negativas: se calculan y se avisa, sin rechazar.** El publicado del 4 saturado lleva la
  escarpa en tracción (N′ = −20 012 kN/m). Sarma (1973) pide comprobar la aceptabilidad física, y la nota la
  enseña sin quitar el número.

- **El ajuste de extremos al contorno se hace al ANALIZAR, no al dibujar** (0.1.427, desviación del plan
  aprobado, que lo ponía también en «la herramienta de la ventana»).
  - La ventana guarda la polilínea como se dibujó, y el motor la ajusta en cada corrida, como a una que llega por
    el API. Así una polilínea guardada sigue valiendo si después se edita el terreno, y un solo sitio decide
    dónde empieza una superficie.
  - Lo dice la nota `search.user_polyline_end_moved` de la corrida.
- **Una sola regla para decidir si una polilínea es una superficie** (0.1.427, `checked_points`). La preguntan la
  ventana, el lienzo, `user_surface_add`, `surface_evaluate` y la corrida. `SlipSurface` ordena sus vértices
  por x, así que una puerta que no la pregunte evalúa otra superficie sin decirlo (medido en `surface_evaluate`
  y, en la revisión de esta versión, en la corrida).

## Riesgos

- **Coste de las cuñas (Shapely más integrales) en búsquedas grandes y en los bucles de la suite.**
  - Se mide con un A/B en el mismo proceso.
  - Un test de más de 1 s lo dice en su cabecera.
- **Datos por vértice desalineados** tras ordenar en x, recortar por la grieta o partir en masas. Se mitiga
  guardándolos por coordenadas.
- **El banco usa tolerancia 0,005.** Re-ejecutar un `construir_modelo.py` sin fijarla mueve los otros
  métodos.
- **Un convenio mal fijado**, si un caso publicado se ajusta por casualidad. Se mitiga con tres casos
  independientes (4 seco, 4 saturado y 5) y con la medida de «solo bases».
