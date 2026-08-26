# Tareas

Pequeñas y verificables. Si una tarea no se puede comprobar, no es una
tarea: es un deseo.

## 0 · Antes de tocar código

- [x] 0.1 Localizar la fuente del algoritmo. **Hecha**: la ayuda declara que
      su motor «is based on the SLAMMER program» y cita Jibson, Rathje, Jibson
      y Lee (2013), USGS TM 12-B1. El algoritmo paso a paso está publicado en
      Jibson (1993), *TRR* **1411** 9-17, atribuido a Wilson y Keefer (1983)
      «modificado para prohibir el desplazamiento cuesta arriba».
- [x] 0.2 Derivar la forma cerrada del pulso rectangular y contrastarla con una
      forma publicada independiente. **Hecha**: `u = V²/(2gN)(1 − N/A)` con
      `V = A g t₀` es idénticamente `u = (a_p T_p²/2)(a_p/μg − 1)`.
- [x] 0.3 Recuperar la geometría del problema 104. **Hecha**: el tutorial que
      el manual cita declara que su modelo es el problema de verificación #4, y
      las razones 1,359/1,375 = 0,9884 y 0,978/0,991 = 0,9869 lo corroboran con
      dos escenarios independientes.
- [x] 0.4 Anotar en `ERRORES_Y_DISCREPANCIAS.md`, **antes** de arreglar nada,
      la geometría recuperada y la incoherencia interna de la Tabla 104.1 (el
      desplazamiento crece donde Ky crece, y no puede) — regla 6.

## A · El acelerograma

- [x] A.1 `SeismicRecord` con `dt`, serie en g y `pga`; `to_dict`/`from_dict`.
- [x] A.2 Importación de las dos formas de texto, con la unidad declarada.
- [x] A.3 `Project.seismic_records`, serializado y recuperado.
- [x] A.4 Test: un registro sobrevive a `save`/`load` dígito a dígito.

## B · El desplazamiento

- [x] B.1 `rigid_block_displacement`, esquema trapecial, con su fuente.
- [x] B.2 Test: forma cerrada del pulso rectangular, **y su convergencia** al
      refinar `dt`.
- [x] B.3 Test: `a_c = 0` con las dos direcciones da el desplazamiento del
      terreno, exacto.
- [x] B.4 Test: `a_c ≥ PGA` da cero exacto.
- [x] B.5 Test: escala en amplitud (`×s`) y en tiempo (`×τ²`).
- [x] B.6 Test: monotonía no creciente en `a_c`.
- [x] B.7 Las cuatro polaridades, y un test de que cada una mueve el número.

## C · El coeficiente sísmico crítico

- [x] C.1 `critical_seismic_coefficient`: barrido, primer cruce, bisección.
- [x] C.2 `FS(0) ≤ objetivo` ⇒ 0; sin cruce ⇒ sin número, con explicación.
- [x] C.3 Test: `k_y = tan(φ − β)` sobre plano infinito sin cohesión.
- [x] C.4 Test: `k_c` de Loukidis (2003), los dos casos, banda tras medir.
- [x] C.5 Test: aplicar `k_h = Ky` devuelve el factor objetivo.

## D · El objetivo de la búsqueda

- [x] D.1 El objetivo único en `BaseSearch`, y las comparaciones que pasan
      por él.
- [x] D.2 Ky en `_analyse`, en `details["ky"]`, sólo cuando el modo lo pide.
- [x] D.3 `SearchResult.critical` ordena por el objetivo.
- [x] D.4 Test de no regresión **bit a bit** con los modos apagados, en las
      siete búsquedas.
- [x] D.5 Test: con el modo Ky, la superficie informada no es la de factor
      mínimo sobre un modelo donde difieren.
- [x] D.6 Test: máximo desplazamiento ⟺ mínimo Ky.

## E · Ajustes e interfaz

- [x] E.1 `SeismicAnalysisSettings` y su hueco en `ProjectSettings`.
- [x] E.2 Página *Seismic* en Project Settings, con el gateado del selector.
- [x] E.3 Diálogo de registros, **no modal**, y su acción en *Loading*.
- [x] E.4 Interpret informa Ky y desplazamiento.
- [x] E.5 Avisos del `analysis_runner`: modo Newmark sin registro, superficie
      sin cruce, y el modo activo dicho en el resumen.
- [x] E.6 Traducciones y la lista blanca de identidades.
- [x] E.7 Test de alcanzabilidad de menú (regla 3) y de traducción (regla 2).
- [x] E.8 Regla 7, ajuste por ajuste: objetivo, polaridad, sentido, escala,
      registro.

## F · El banco (fuera del repositorio)

- [x] F.1 Construir el modelo del 104 con la geometría del problema 4.
- [x] F.2 Corridos: **1,359481 (+0,04 %) · 0,986856 (+0,91 %) · 0,13835
      (−0,47 %)**. Los tres dentro del 1 %. El escenario 4 no se construye.
- [x] F.3 Recalcular el `k_c` del problema 62 en el sentido en que se usa.
- [x] F.4 Intentada. **No se pudo**: el centro de datos virtual de COSMOS pide
      sesión para descargar y la base NGA-West2 de PEER pide registro. Queda
      `_tools/newmark_tabla_jibson.py`, escrito para medir en cuanto exista un
      archivo, con los tres registros nombrados y el aviso de que la
      digitalización de 1993 no es la de hoy.
- [x] F.5 Reescribir las fichas del 104 y del 62, regenerar comparativa y
      auditoría, anotar el cierre de D25.

## G · Publicación

- [x] G.1 Los siete sitios de versión a 0.1.127.
- [x] G.2 Changelog, con los caminos equivocados incluidos.
- [x] G.3 La suite **entera**, sin argumentos, sin marca `FILTERED RUN`.
