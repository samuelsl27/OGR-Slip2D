# Plan de implementación

## Enfoque

Un tipo de soporte más en el registro que ya existe: `RetainingWallEFP`, cuyo
`force_at(distance_from_head, total_length)` devuelve la **primitiva exacta** del
perfil de presión. La firma del método abstracto ya está parametrizada por
distancia desde la cabeza, así que la clase base no se toca.

Dos piezas del motor sí se tocan, y las dos por la misma razón —**una fuerza
horizontal aplicada a una cota**—: el punto de aplicación de la resultante del
muro, que entra como un **par aditivo de momento**, y la componente horizontal de
las cargas distribuidas, que hoy se descarta entera y es la vía por la que la
referencia escribe su propia verificación.

## Archivos que se tocan

| Archivo | Qué cambia |
|---|---|
| `ogr_core/support/support.py` | **nuevo** tipo `RetainingWallEFP` + registro + flag de coronación |
| `ogr_core/support/__init__.py` | importar y exportar el tipo |
| `ogr_slip2d/support_integration.py` | distancia medida desde el extremo alto; par ΔM del punto de aplicación |
| `ogr_slip2d/moment_balance.py` · `interslice.py` · `methods/bishop.py` · `methods/ordinary.py` | el par ΔM en los cuatro métodos con ecuación de momentos |
| `ogr_slip2d/slicer.py` | `_surface_pressure_at` resuelve el vector; parte horizontal por `add_water_force`; segmento vertical |
| `ogr_slip2d/analysis_runner.py` | avisos: muro horizontal; punto de aplicación no honrado por el método elegido |
| `ogr_gui/dialogs/define_support_dialog.py` | `_CHOICES`, `TABLE_FIELD` declarado, señal del combo, cabeceras, duplicado |
| `ogr_gui/canvas/graphics_items.py` | color del tipo; tooltip condicionado |
| `ogr_gui/i18n/__init__.py` | traducciones |
| `tests/test_i18n_coverage_v141.py` | dos cognados a la lista blanca, con su razón |
| `tests/test_supports_v114.py` | renombrar `test_seven_types_registered` |
| `docs/plugins.md` | tabla declarada y campo fuera de `PARAMETERS` |
| `tests/test_efp_wall_v1122.py` | **nuevo** |
| `docs/changelog/CHANGELOG_v0.1.122.md` | **nuevo** |

## Decisiones de diseño

**La resistencia no es un parámetro nuevo: es la primitiva del perfil.** Las
cuatro formas tienen integral cerrada, así que no se usa cuadratura numérica.
Los dos valores publicados (312,5 y 2000) son exactos y una cuadratura los
convertiría en aproximados sin ninguna ganancia.

**Sin espaciamiento fuera de plano.** Los otros siete tipos dividen por
`out_of_plane_spacing` porque son elementos discretos; un muro es continuo y su
presión ya está por metro de muro. Un parámetro que siempre vale 1 sería un
ajuste inerte — regla 7. Consecuencia asumida: el **patrón** de soportes se
rechaza para este tipo, porque sumaría N veces la misma presión.

**La coronación se decide por geometría, no por el orden de dibujo.** `force_at`
no ve la instancia y no puede saber qué extremo está arriba, así que un muro
dibujado de abajo a arriba invertiría el perfil y devolvería un número plausible
y falso. En vez de avisar —el número seguiría en pantalla—, la distancia se mide
desde el extremo **más alto** para los tipos que lo declaren, y un muro
exactamente horizontal se rechaza por admisibilidad.

**El punto de aplicación entra como fuerza más par, no moviendo el punto.**
Trasladar una fuerza no cambia su resultante, sólo su momento. `x_app`/`y_app` se
leen en un solo sitio del repositorio y sólo desde la rama no circular de
Spencer/GLE, así que moverlos ahí no cambiaría el número en 7 de los 9 métodos ni
en ninguna superficie circular: sería un control inerte. Un término **aditivo**
`ΔM = F × (r_corte − r_centroide)` vale cero para todo soporte existente, deja
intactos el reparto Activo/Pasivo y la descomposición T_S/T_N —y con ellos lo que
v0.1.113 y v0.1.115 midieron—, y mueve el número por el brazo, que es la razón
correcta.

**Y su alcance se declara.** Un par sólo tiene dónde entrar en los métodos con
ecuación de momentos: Ordinary, Bishop, Spencer y GLE. Los dos Janbu y los tres
de marcha resuelven fuerzas y no pueden honrarlo. El diálogo lo dice y el
análisis avisa: un ajuste que calla su alcance es tan malo como uno inerte.

**Descartado meter la resultante por el canal `h_water`**, con cuatro razones:
contaría el momento por tercera vez, ese canal no es sólo momento —entra en N en
Ordinary y en el empuje horizontal en Spencer/GLE—, no tiene bandera
Activo/Pasivo (reintroduciría la anomalía de v0.1.115), y Janbu lo sumaría en
crudo en vez de proyectado, deshaciendo la corrección de v0.1.113.

**El perfil personalizado no puede copiar `UserDefined`, aunque el widget sí.**
`UserDefined` extrapola constante por los dos lados; la referencia pide **cero**
arriba si no hay valor en 0. Su tabla es en distancia absoluta y ésta en relativa
[0,1]. Y lo esencial: aquí `force_at` no interpola, **integra la interpolada**.

**La forma del trapecio la decide la figura, no el razonamiento.** El área
publicada (2000) es compatible con la parte plana arriba, abajo o en medio. Un
análisis intermedio propuso una sola rampa, argumentando continuidad de la
familia; la figura acotada de la ayuda dice **0,2H / 0,6H / 0,2H**, simétrica. Es
la lección de D16/D17: decide la figura.

## Riesgos

- **El arreglo de la carga distribuida toca el motor.** Los seis modelos del
  banco que la usan la ponen sobre un segmento **horizontal**, donde la
  componente horizontal es exactamente cero, así que no pueden moverse. Se
  comprueba corriendo los seis antes y después, no razonándolo.
- **El par ΔM toca los cuatro métodos de momentos.** Es aditivo y nulo para todo
  soporte existente. Si `test_support_projection_v1113.py` o
  `test_support_active_passive_v1115.py` se mueven, el cambio está mal planteado
  y se rehace; **no se ajusta el test**.
- **El presupuesto de traducciones idénticas admite una entrada y hacen falta
  dos** (*Triangular* y *Horizontal* son iguales en castellano). Se resuelve por
  la lista blanca con su razón, nunca subiendo el tope.
- **Que la geometría del problema 110 no se recupere.** El residuo de calibración
  lo dice antes de invertir en el modelo.
