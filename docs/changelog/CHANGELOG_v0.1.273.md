# OGR Slip2D v0.1.273

**Los avisos de no convergencia de la filtración ya no recomiendan lo que el
usuario no puede hacer (D266).** El permanente aconsejaba «a smaller
relaxation factor or a finer mesh», y una etapa transitoria «a smaller
relaxation factor». La relajación no es un ajuste en ningún sitio al que
llegue el usuario, y refinar la malla es justo lo que provoca el ciclo que
resuelve el rescate de D124. Se midió sobre el banco si ω importa, y no
importa. Queda escrito por qué no se expone. Ningún número cambia.

## 0. Lo que se encontró (puerta de medida D, `_auditoria/P6_0273/` del banco)

Se barrió ω ∈ {0,2; 0,3; 0,4; 0,6; 0,8} sobre las 53 filas permanentes no
saturadas del banco: el 05 entero en las dos mallas, el 02-010 y el 02-038.
Las mallas ya eran las reparadas de D270, y el criterio el de D267.

- **La convergencia no depende de ω en ninguna fila.** Las 53 convergen con
  las cinco ω; donde el bucle solo no llega, llega el rescate. Ningún caso que
  falla converge con otra ω: el consejo del aviso nunca fue cierto en el
  banco.
- **En 49 filas** el resultado coincide con el de ω = 0,4 dentro de unas 2
  tolerancias de la fila (mediana 0,55).
- **En 4 filas, una ω llega a OTRO conjunto de nodos de la cara de rezume.**
  Son el 05-001 x1 con ω = 0,2 y el Gardner seco del 02-038 con ω = 0,6 y 0,8
  (tras el rescate de Anderson) y con 0,2 en h63.
  - La diferencia es de uno a cinco nodos de cara y de 0,2 a 2,4 cm de carga.
  - Siempre queda en un nodo de la cara y **siempre por debajo de p_tol**, la
    banda de presión de la conmutación (1,43 y 4,16 cm en esas mallas).
  - La conmutación acepta varios estados de la cara dentro de sus bandas. Es
    la precisión del algoritmo (punto de salida a un nodo, presiones a p_tol),
    no un error de convergencia. Va a la ficha nueva **D280**.
- **La lectura.** El único efecto medido de ω es elegir otro estado admisible
  de la cara dentro de su banda, y eso no lo controla quien sube o baja ω. Un
  ajuste así no sirve de nada (regla 7), así que no se expone.

**Decisión de la propietaria:** cierre documental, y ficha D280 para la no
unicidad de la cara.

## 1. Qué cambia

- **Aviso del permanente con el rescate apagado** (la única rama que llegaba
  al consejo viejo): «Picard iteration did not converge in N steps (last
  change X m), and the rescue is switched off».
- **Aviso de una etapa transitoria**: «try more time steps or more Picard
  iterations per step». Los dos son ajustes del proyecto, en el diálogo de
  ajustes.
- **El docstring de `solve_project_groundwater`** explica por qué la
  relajación no es un ajuste del proyecto, con la tabla del barrido.
- **El docstring de `solve_unsaturated`** gana «How precisely the seepage face
  is resolved»: el estado único de la presa de Gardner (D267) no es la regla,
  y en el banco 4 de 53 filas aterrizan en otra cara dentro de p_tol.

## 2. Tests

`tests/test_no_convergence_advice_v1273.py`, 3 casos (los 3 fallan con
0.1.272):

- el aviso del permanente con el rescate apagado, sobre la reproducción del
  prompt (la presa con van Genuchten α = 5, n = 3), nombra la causa y ningún
  remedio imposible;
- una etapa transitoria que no converge remite a sus propios ajustes;
- ninguna cadena del módulo que no sea un docstring (las partes de los
  f-strings incluidas) menciona «relaxation factor» ni «finer mesh». Los
  comentarios y docstrings sí pueden explicar por qué no.

Suite entera: **5778 de 5778**.

## 3. Cierre en el banco

`d266()` en el `verificar_cierres.py` de la raíz lee las cadenas de aviso de
`seepage.py` con el árbol sintáctico, sin docstrings, y exige además el
docstring de `solve_project_groundwater`, la medida archivada y el test.
Veredicto: **CIERRE DOCUMENTAL**.
