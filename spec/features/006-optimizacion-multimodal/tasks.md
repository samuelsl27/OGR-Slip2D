# Tareas

Pequeñas y verificables. Si una tarea no se puede comprobar, no es una
tarea: es un deseo.

## 0 · Antes de tocar código

- [x] 0.1 Releer los ocho rótulos de la figura 103.3 a alta resolución (QtPdf,
      8×). **Hecho**: MMO 1,215 · **1,290**/1,324 · 1,366/**1,315**; unimodal
      1,216 · 1,290 · 1,366. El negrita es el mínimo global, así que al ratio
      1,6 **la unimodal se queda en 1,366 y la multimodal encuentra 1,315**.
- [x] 0.2 Medir la geometría del panel en píxeles: `H = 18`, `D = 1,989`,
      ancho **5,5 H** (2,27 H tras la coronación, 1,33 H tras el pie) — no los
      13 H del artículo. Medido con rejilla circular y Spencer:

      | extremos | ratio 1,4 | 1,5 | 1,6 |
      |---|---|---|---|
      | manual 5,5 H | 1,3022 profundo | **1,3580** somero | **1,3580** somero |
      | artículo 13 H | 1,3043 profundo | 1,3809 somero | 1,3809 somero |

      Tres cosas de aquí: los extremos **no explican** el hueco con el 1,215
      publicado; la **rama somera no depende de `c_u2`** — mismo círculo, mismo
      número dígito a dígito en 1,5 y 1,6 —, que es la identidad exacta del
      criterio de aceptación, ya cumpliéndose; y los 1,3580 contra 1,3809 del
      mismo mecanismo somero son **resolución de rejilla**, no física (la
      rejilla automática se estira con el modelo), o sea D37 otra vez.
- [x] 0.3 Anotar en `ERRORES_Y_DISCREPANCIAS.md` el defecto del eje de momentos
      **antes** de arreglarlo, con la tabla de convergencia y los 65 m (regla 6).

## A · El eje de momentos

- [x] A.1 Test de la identidad del refinamiento: una poligonal de N cuerdas
      inscrita en un arco converge al factor del arco, para los nueve métodos.
      **Tiene que fallar antes del arreglo** — ésa es la prueba de que el
      defecto era real.
- [x] A.2 Ajuste de círculo por mínimos cuadrados (Kåsa) — escrito, probado y
      **retirado**: la medición A.5 lo rechazó y no queda código muerto.
- [x] A.3 `moment_axis` **no cambia**. El override, el círculo y la compuesta
      siguen contestando antes, como siempre.
- [x] A.4 El docstring recoge la medición: el par impreso **sí** es el eje —
      verificado a seis cifras—, y lo que cuesta ese convenio, con su tabla.
- [x] A.5 Medido contra la tabla publicada de siete métodos sobre las dos
      superficies no circulares dibujadas a mano, que es el contraste
      determinista que existe. **Decidió en contra del cambio**, y por eso el
      cambio se retiró.
- [x] A.6 Ningún modelo se mueve un dígito: producción quedó como estaba.

## B · La optimización multimodal

- [x] B.1 `SearchResult.minima`, vacío para las seis búsquedas actuales.
- [x] B.2 `particle_swarm.py`: partículas circulares en la parametrización de
      Slope Search, actualización unimodal y multimodal con sus fuentes.
      **Con ventana de ángulo propia y más ancha**, medido: con la de Slope
      Search el mecanismo profundo del 103 queda fuera del espacio (pide
      +49,5° donde β−5 da +21,6°) y el enjambre devolvía 1,4167 contra
      1,3036 de la rejilla, sin un solo mínimo profundo. Slope Search sí lo
      alcanza, pero por su refinamiento local, que se sale de esa
      parametrización.
- [x] B.3 Semillas de especie por radio (Li 2004), con el 10 % por defecto.
- [x] B.4 Enjambre mejorado: reubicar las partículas de mayor factor; la
      fracción se declara en el código porque no está publicada.
- [x] B.5 Optimización **por mínimo**: discretizar cada círculo ganador y
      pasear cada uno, guardando todos; hoy sólo sobrevive el mejor y los
      círculos se saltan.
- [x] B.6 `SearchMethod.PARTICLE_SWARM` en ajustes y rama en `build_search`,
      con la semilla del proyecto.
- [x] B.7 Aviso cuando el modo de varios corre sin optimización, con sus tres
      tests: sale con varios mínimos y optimización apagada, y **no** sale ni
      con la optimización encendida ni con un solo mínimo.
- [x] B.8 Panel en *Surface Options*, y las **dos listas de métodos duplicadas
      a mano** en el diálogo, no sólo la de `settings.py`.
- [x] B.9 Casilla del enjambre mejorado en *Advanced*.
- [x] B.10 Los varios mínimos se ven y se eligen desde el menú, por
      `Show GM Surfaces` y `Pick GM Surfaces`, que ya estaban ahí y ahora
      hacen lo que dicen. Un modo de superficie aparte habría sido un segundo
      control para lo mismo.
- [x] B.11 `Show GM Surfaces` dibuja de verdad; `Pick GM Surfaces` selecciona y
      deja de ser modal; las dos cadenas pasan por `tr()`.

## C · La superficie anisótropa

- [x] C.1 `anisotropic_surface.py`: punto más cercano y regla del segmento
      dibujado primero cuando cae en un vértice.
- [x] C.2 `BoundaryType.ANISOTROPIC_SURFACE` y **todos** sus enganches
      (los dos `mapping[self]` sin `.get()`, lienzo, DXF, `convert_boundary`,
      y **fuera** de regiones y del mallador).
- [x] C.3 Campo del ángulo local en `SliceContext`, poblado por el slicer.
- [x] C.4 Los tres modelos anisótropos lo usan cuando el material tiene
      superficie asignada; sin ella, dígito a dígito como hoy.
- [x] C.5 Asignación en el diálogo de materiales; acción *Add Anisotropic
      Surface* en el menú Boundaries; modo de dibujo, color y z-order.
- [x] C.6 Ida y vuelta por el `.ogr` **conservando el orden de los vértices**.

## E · D48, encontrado corriendo el 103 por el banco

- [x] E.1 Reportar antes de tocar: una superficie no circular podia salirse del
      modelo y fuera del modelo el suelo es el material **mas debil** de la
      lista. 1,0902 contra 1,2676 recortada — **16 %** al lado inseguro.
- [x] E.2 La regla ya existia (`leaves_soil_region`, con su codigo de error
      publicado) y se llamaba **solo desde el camino de los circulos**.
- [x] E.3 `polyline_leaves_soil`: envolvente inferior, no una cota; vertices de
      la superficie **y** de la envolvente; tolerancia relativa; tangente al
      firme se conserva.
- [x] E.4 Test con la superficie que devolvio el banco, verbatim.
- [x] E.5 Medido: **suite entera 2745/2745, cero fallos** con el guardia
      puesto — dentro del repositorio no se mueve nada. Y las dos superficies
      del contraste no circular publicado (Ej_1 y Ej_2) no se salen, asi que el
      guardia no las toca.
- [x] E.6 **Corregida una atribucion mia que era falsa**: dije que D48
      explicaba el problema 41 y esta medido que no. Sus dos superficies llegan
      a y = 4,307 y y = 3,952 sobre una base en y = 0: no se salen de nada.
      Aquel minimo por debajo de todas las referencias publicadas sigue sin
      causa.

## D · Cierre

- [x] D.1 Tests con su cabecera explicando qué invariante protegen.
- [x] D.2 Traducciones españolas; «Multimodal» a la lista blanca de cognatos
      con su razón, sin subir el tope de 12.
- [x] D.3 Regla 3: el test que recorre la barra de menús real pasa con la
      acción nueva dentro (suite 2745/2745). Y las dos acciones GM, que estaban
      **atadas a que hubiera análisis probabilístico**, se habilitan también
      cuando el resultado informa mínimos — sin eso los del enjambre habrían
      quedado inalcanzables desde cualquier menú.
- [x] D.4 Regla 7: un test por ajuste que demuestre que mueve el número.
- [x] D.5 Los **siete** sitios de versión a 0.1.126.
- [x] D.6 Suite completa **sin argumentos** en verde.
- [x] D.7 Changelog registrando **qué se encontró**, los caminos equivocados
      incluidos.
- [x] D.8 Banco: `construir_modelo.py` y tres `.ogr` del 103 con la búsqueda
      que el enunciado declara; los tres ratios corridos —**+0,42 %, +0,92 % y
      +0,12 %**, los tres OK—; fichas del 103 (pasa a **REPRODUCIDO**) y del
      105 reescritas; `referencia.json` de los dos; el 103 y el 105 fuera de la
      clase de huecos y el 105 con clase propia («el Tutorial 32 no publica su
      geometría»); comparativa (95/111, 35 con mitad no circular) y auditoría
      regeneradas; **D47** reescrito con la medición que refuta su primera
      redacción, **D48** abierto y cerrado, y **D24** cerrado.
