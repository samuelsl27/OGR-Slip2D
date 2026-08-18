# Pendientes abiertos

Lo que quedó sin cerrar y **por qué**, para que no se pierda entre
changelogs. Cada entrada dice qué falta exactamente y qué haría falta para
cerrarla. Se borra la entrada cuando se cierra, no se marca.

Origen: trabajo sobre los ejemplos Ej_1 y Ej_2 de `referencias/Ejemplos/`
(v0.1.84 en adelante).

---

## 1 · La regla de radios del Grid Search — CERRADO en v0.1.88

La medición que faltaba se ejecutó
(`referencias/Ejemplos/00_2026_08_17_Test_Regla_radios`) y la regla quedó
despejada por lectura directa de los `.s01`, sin ajustar nada. Derivación,
comprobación sobre 949 centros y tablas en
`docs/audits/grid_radius_rule_v188.md`.

Queda **una** pieza sin medir, y sólo ésa: en los seis modelos los Slope
Limits están en su posición automática, así que los datos no distinguen si
`d_max` se mide a los *puntos límite* o a los *extremos del perfil*, ni si
`d_min` se mide sobre el perfil recortado o el completo. Se implementó la
lectura documentada.

### CERRADO en v0.1.92

Los modelos con los Slope Limits metidos a x = 20/100 (Ej_1) y −20/85 (Ej_2)
—abscisas que no son vértices del perfil— distinguen por fin las lecturas:
`d_max` se mide **a los puntos límite** (5·10⁻¹⁴), no a los extremos del perfil
(error de 10,0 m y 23,5 m). Lo implementado desde v0.1.88 era lo correcto.

Sigue sin distinguirse, y se dice: si `d_min` se mide sobre el perfil recortado
o el completo. En esas rejillas el punto más cercano cae dentro de los límites
en todos los centros, así que las dos lecturas dan idéntico.

`AutoRefineSearch` **queda arreglado** con esa misma medición: recortaba los
límites filtrando vértices y ahora interpola, como `GridSearch`.

### Decisión tomada en v0.1.88 que conviene revisar: `min_radius = 0`

El predeterminado pasó de 2,0 a **0,0** en `GridSearch` y de 3,0 a 0,0 en
`analysis_runner.build_search`, para que la configuración de fábrica —la que
usan la interfaz y la CLI— muestree **exactamente** la población de la
referencia. La referencia no tiene control de radio mínimo; ofrece *Minimum
Elevation* y *Minimum Depth*.

Está medido que no cambia ningún resultado: con 3,0 y con 0,0 el factor de
seguridad de los cinco casos publicados es idéntico, y sólo se mueven los
recuentos de válidas en unas unidades.

**Lo que queda por decidir es de producto, no de cálculo**: si un usuario de la
interfaz se beneficia de un suelo de 3 m que le ahorre círculos diminutos, o si
vale más que la interfaz reproduzca la referencia sin excepciones. Se eligió lo
segundo. Cambiarlo es una línea en cada sitio; si se cambia, hay que decir en
la documentación que la interfaz **no** reproduce el muestreo de la referencia.

---

## 0a · GLE bajo Simulated Annealing — CERRADO en v0.1.90

No era el rebanador de v0.1.89 y no era el recocido: era el **rango de λ**,
cortado en ±1,5 mientras la raíz de esas superficies está en λ ≈ 3. Medido,
arreglado y validado por tres caminos en v0.1.90. Ver
`docs/audits/spencer_gle_interslice_v179.md`.

---

## 0 · Simulated Annealing converge peor que un círculo

**Estado**: reportado con medidas, sin corregir. Regla 6.

Sobre un talud cuyo mínimo **circular** es 1,1239, SA devuelve **1,6564**. Una
búsqueda no circular no puede hacerlo peor que un círculo: los círculos están,
salvo discretización, en su espacio de búsqueda. Block Search, sobre el mismo
modelo, da 1,13-1,16 — dentro de la discretización. SA se va un 47 %.

### Corrección de lo que decía esta entrada en v0.1.89

Decía que `generation_steps` «deja de hacer nada». **Estaba mal medido**, y el
mecanismo real apunta a otro sitio. Instrumentado (`search.py:2686-2687` y
`:2767`):

```python
K     = max(4,  int(self.generation_steps / 50))   # pasadas externas
Ngen0 = max(20, self.generation_steps // K)        # bucle interno
Ngen  = max(10, Ngen0 // (2 ** (k - 1)))           # se HALVA cada pasada
if no_improve_passes >= 3: break                   # parada
```

| `generation_steps` | K | Ngen0 | Σ Ngen nominal | **evaluadas de verdad** | FoS |
|---|---|---|---|---|---|
| 50 | 4 | 20 | 50 | 151 | 1,7491 |
| 300 | 6 | **50** | 117 | 459 | 2,1854 |
| 1 000 | 20 | **50** | 257 | **462** | 1,6564 |
| 3 000 | 60 | **50** | 657 | **462** | 1,6564 |

Tres cosas, y ninguna es «el ajuste se ignora»:

1. `K = generation_steps/50` hace que `Ngen0 = generation_steps // K` sea
   **50 siempre** para `generation_steps ≥ 200`. El ajuste no controla el
   tamaño del bucle interno; sólo añade pasadas externas.
2. `Ngen` se halva cada pasada hasta un suelo de 10, así que las pasadas de
   temperatura baja —donde el recocido debería explotar el óptimo— exploran
   con diez propuestas.
3. La parada a las 3 pasadas sin mejorar congela el total en 462 evaluaciones,
   así que de 1000 en adelante el ajuste es inerte **por la parada**, no por
   la fórmula.

### Los parámetros de la referencia, que ahora sí se conocen

De sus propios modelos (`simulatedannealing search` en el `.sli`):

| | referencia | OGR |
|---|---|---|
| `ngen` (estados generados por temperatura) | **1000** | 50 (fijo) |
| `nepsilon` (pasadas sin mejora antes de parar) | **5** | 3 |
| `ftol` | **0,0001** | `tolerance` 1e-3 |
| `c` (enfriamiento) | 8 | 8 ✔ |
| `nvertices` | 8 | 9 por defecto |

Eso convierte esta entrada de «investigar» en «cambiar exactamente esto». No
se hizo en v0.1.90 porque cambia coste y resultados en toda la suite y **no
hay referencia externa para el resultado de una búsqueda no circular** — lo
dice `validacion/casos/004-arai-tagyo-1985-ej1/caso.md`. Merece su propia
versión con su propio triaje.

Qué haría falta además: el mínimo **no circular** publicado de Yamagami y Ueta
(1988) o del reanálisis de Greco (1996), cuyo talud ya está en
`validacion/casos/002-yamagami-ueta-1988/` con coordenadas rotuladas. Con ese
número, las búsquedas no circulares tendrían por primera vez una referencia
externa en vez de una identidad interna.

Relacionado: `test_annealing_bootstrap_v139.py` documenta que el arranque de
SA dependía de la suerte (200 rechazos consecutivos con semillas
desafortunadas).

---

## 2 · La geometría degenerada — CERRADO en v0.1.89

Eran **nueve** contornos en siete archivos, no cinco: la lista de aquí estaba
hecha a mano y se había quedado corta. El inventario se toma ahora con
`ogr_core.geometry.zero_thickness_spans()` ejecutando la suite con
`Project.add_boundary` instrumentado, que no se puede quedar obsoleto.

Lo que tapaba está en el changelog de v0.1.89 y en los pendientes 0 y 0a de
este documento.

Queda una limitación dicha: el detector **no impide** que un archivo nuevo
reintroduzca el contorno. Haría falta que todos los modelos de test pasaran por
una fábrica única.

---

## 3 · El panel de dovelas — CERRADO en v0.1.91

Los tres botones (Copy, Zoom Slice, Hide/Show Geometry) y las fuerzas entre
dovelas, dibujadas **sólo** cuando el método publica `boundary_ratios` y
declaradas en palabras cuando no. Detalle en el changelog de v0.1.91.

Se abre uno nuevo de paso: **OGR no tiene «analizar exactamente esta
superficie»**, lo que la referencia llama *Add Surface*. Las superficies no
circulares de referencia sólo se pueden evaluar por programa, no desde la
interfaz. Ver `referencias/Ejemplos/README.md`.

---

## 4 · Diagnóstico fuera del runner — CERRADO en v0.1.89

Explicado, comprobado con un señuelo y con guarda: `pip install -e .` registra
un buscador que resuelve todo `ogr_*` a una ruta absoluta fija, y
`sys.path[0]` es el directorio **del script**, no el de trabajo. El runner
imprime ahora la procedencia y se niega a correr sobre otro árbol. Detalle en
el changelog de v0.1.89.

---

## 5 · Arrastrar un contorno entero rompe — ABIERTO (v0.1.93)

`ogr_gui/canvas/canvas_view.py:1966-1968` asigna sobre un `Vertex`, que es un
`@dataclass(frozen=True, slots=True)`:

```python
for vi, v in enumerate(b.polyline.vertices):
    v.x = ox0 + dx
    v.y = oy0 + dy
```

Reproducido: `FrozenInstanceError: cannot assign to field 'x'`. Es decir, el
arrastre de un contorno completo lanza al primer movimiento del ratón.

Apareció escribiendo el test de invalidación in situ de v0.1.93 —que intentó
editar así porque el comentario del lienzo dice que así se edita— y se dejó
sin tocar según la regla 6. **Falta por averiguar**: desde qué versión, qué
modos de herramienta llegan a ese bloque (`_dragging_boundary` se arma en
algún sitio que hay que localizar), y por qué ningún test de la interfaz lo
cubre. El arreglo previsible es reemplazar la lista
(`b.polyline.vertices[vi] = Vertex(...)`), que es como edita el resto del
código, pero **no se toca sin saber antes por qué nadie lo notó**: si el
bloque fuera inalcanzable, el arreglo sería un parche sobre código muerto.

## 6 · Arranque en caliente de λ en Spencer y GLE — ABIERTO (v0.1.93)

Con el corte del muestreo de v0.1.93, Spencer y GLE siguen costando ~15×
Bishop por círculo. Lo que queda es que cada *inner solve* arranca siempre en
`initial_fos = 1.0`, en vez de en la `F` ya convergida del λ anterior. Es
previsiblemente el mayor ahorro que resta.

No entró en v0.1.93 porque **mueve los números dentro de la tolerancia**, y
esa versión se definió por no mover ninguno. Para cerrarlo hace falta
revalidar Ej_1, Ej_2 y los cinco casos de `validacion/casos/`, y publicar el
desplazamiento de cada uno — no basta con que sigan dentro de tolerancia.
