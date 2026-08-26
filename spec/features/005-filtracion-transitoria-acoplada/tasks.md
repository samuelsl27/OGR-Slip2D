# Tareas — filtración transitoria acoplada (D30)

Orden por riesgo: primero lo que toca el camino común de todos los modelos con
agua, para que la suite lo juzgue antes de que llegue nada nuevo encima.

## 1 · El embalse deja de inundar el modelo

- [x] `_fea_ponding_runs`: los nodos mojados agrupados en tramos **contiguos del
      contorno**, no en una lista global ordenada
- [x] `_fea_level_at` no extrapola fuera de un cuerpo de agua ni interpola entre
      dos, y responde `None` como ya hacía el camino dibujado
- [x] Auditados los cuatro consumidores; el del lienzo estaba bien y hereda el
      arreglo

## 2 · La cara de filtración deja de fabricar convergencia

- [x] `DEFAULT_MAX_NODE_SWITCHES` de 3 a 25, con la medición que lo justifica
- [x] `_unsettled_nodes`: la condición unilateral se comprueba sobre el estado
      FINAL, no sobre el bucle
- [x] `frozen_nodes` y `unsettled_nodes` en las notas, y `converged = False`
      cuando queda algo sin asentar

## 2b · Los dos defectos que salieron detrás

- [x] `calculate_sf` viaja también con una etapa de duración cero
- [x] El aviso de campo no convergido deja de ser modal: es un diagnóstico
      sobre el resultado, no una pregunta, y un modal en código que una corrida
      automática alcanza es un bloqueo indefinido
- [x] Coste medido con A/B y controles: sin efecto en el transitorio

## 3 · Decir dónde está el embalse

- [x] `ogr_fem2d/solvers/bc_targets.py`: ciclo del contorno, perímetro mojado y
      `apply_reservoir`. Dos destinos genéricos más —`nodes_below` y
      `nodes_between`— se escribieron y se **retiraron**: no los llamaba nadie
- [x] El paseo nunca entra en la base del modelo
- [x] Exportado en `ogr_fem2d/solvers/__init__.py`
- [x] Destino «Embalse a la cota» en el diálogo de condiciones de contorno, con
      el número de nodos que alcanzó

## 4 · El conductor programático

- [x] `ogr_slip2d/transient_stability.py`: `solve_project_groundwater`,
      `run_transient_stability`, `with_stage_water`
- [x] Cada etapa instala su campo **y** sus condiciones, y las restaura aunque
      el cuerpo levante
- [x] `MainWindow._compute_transient` y `_compute_groundwater`, envoltorios
- [x] `run_analysis` rechaza un proyecto sin configurar, con escape explícito

## 5 · El tope de succión

- [x] `negative_pore_pressure_cutoff` en los ajustes, `None` por defecto
- [x] Aplicado antes de la envolvente, con el signo ignorado
- [x] Leído una vez por corrida, no una vez por dovela
- [x] Casilla y valor en Project Settings → Groundwater, traducidos

## 6 · Validación

- [x] Los dieciséis extremos publicados, en forma cerrada
- [x] Seco 2,455; permanente inicial 1,745 y 1,815; permanente final 2,376
- [x] El cociente de φ_b, libre del sesgo común
- [x] Por qué el quinto valor no es un quinto, con la evidencia publicada
- [x] Cara de filtración ≡ carga prescrita a la misma cota
- [x] El embalse no existe donde no se prescribió; dos cuerpos no se mezclan
- [x] Regla 7: tope, cota del embalse, condiciones por etapa
- [x] La guarda, y su escape

## 7 · Revisión adversarial antes de publicar

Cinco lentes independientes y un refutador por hallazgo. De 26 hallazgos
sobrevivieron 18, que son **seis defectos**, todos de esta versión y cuatro de
ellos a punto de salir a la calle.

- [x] `wetted_nodes` recorría la base: la parada se **dice**, no se deja al agua
- [x] La caché del embalse no veía bajar el nivel: la clave lleva los valores
- [x] `AnalysisNotConfigured` escapaba de un slot de Qt: capturada y dicha
- [x] Los avisos del conductor pasan por `tr()` en el punto de uso
- [x] El tope de succión **sí** mueve el número con φ_b = 0 y AEV > 0: corregido
      el tooltip, el comentario del ajuste y el test que lo afirmaba
- [x] Un test que pasaba por la razón equivocada, partido en dos

## 8 · Publicación

- [x] Siete sitios de versión, 0.1.124 → 0.1.125
- [x] Changelog
- [x] Banco: modelo del 102, ficha, `referencia.json`, auditoría y comparativa
- [x] Suite entera **sin argumentos** — 2701 / 2701
