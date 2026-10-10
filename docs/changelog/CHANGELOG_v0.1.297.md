# OGR Slip2D v0.1.297

**El panel de resultados dice cuándo su resultado es de un modelo anterior
(D304).** Tras editar la geometría seguía enseñando el factor del cálculo
anterior como si fuera del modelo en pantalla.

## 0. Lo que se encontró

- **La segunda prueba de la interfaz**
  (`_auditoria/P8_interfaz/INFORME_prueba_GUI_0.1.290.md`, H9):
  1. talud de ejemplo → Calcular: FS = 1,0914 (Bishop);
  2. se mueve el pie con *Mover vértice*;
  3. el lienzo quita las superficies, pero el panel sigue con «1.0914 |
     bishop_simplified …» y la cabecera «FS crítico: 1.091».
- **El API sí lo marca.** Usa la huella de lo que lee un análisis
  (`ogr_api.snapshot.model_hash`: el SHA-256 de `to_dict()` sin las
  anotaciones). La ventana no tenía nada.
- **El coste de la huella,** medido: 0,3 ms sin malla, 5 ms con 2000 elementos
  y 23 ms con 8000. Demasiado para cada evento de un arrastre, así que la
  comprobación se hace cuando las ediciones paran.
- **Decisión de la propietaria:** marcarlo como desfasado con la misma huella que
  el API; recalcular quita la marca.

## 1. Qué cambia

- **`ResultsDock.set_stale(stale)`:** muestra o esconde una franja, «Resultados
  de un modelo anterior: vuelve a calcular.», y pone la tabla en gris.
  - La franja lleva sus propios colores, para leerse con los dos temas.
  - `show_result` la quita: un resultado recién mostrado es del modelo con que
    se calculó.
- **`MainWindow`:**
  - guarda la huella del modelo al llenar el panel: al terminar el cálculo y
    tras la pasada de optimización;
  - en cada evento del proyecto, si hay huella, programa una comprobación
    diferida (un `QTimer` de 300 ms que se reinicia con cada evento) y marca el
    panel si la huella ya no coincide;
  - abrir o crear un proyecto la olvida.
- **Lo que esto implica:**
  - deshacer la edición devuelve la misma huella, y la marca se va;
  - una anotación no marca nada, porque el análisis no la lee;
  - como en el API, la huella incluye el campo de agua calculado, así que
    recalcular el agua después de un cálculo de estabilidad marca ese resultado
    como desfasado.

## 2. Tests

`tests/test_results_stale_v1297.py`, 5 casos, por el camino real del cálculo
(`_ComputeWorker.run` + `_on_compute_done`):
- un resultado recién calculado no está desfasado;
- mover el pie lo marca (franja visible, tabla en gris), y deshacer lo quita;
- volver a calcular lo quita;
- una anotación no lo marca;
- un evento del proyecto arranca la comprobación diferida.

Con el código de 0.1.296 fallan los cinco.

## 3. Verificación

- **Suite entera:** 5932 / 5932, con código de salida del proceso 0.
- **`verificar_cierres.py` de la raíz:** `d304()` da CUBIERTO POR TEST;
  41 comprobaciones, ninguna bajada.

## 4. Lo que no se ha probado

- **A mano:** talud de ejemplo → Calcular → mover un vértice → la franja.
  Deshacer → se va.
- **Las ventanas de *Interpretar* ya abiertas** siguen enseñando el cálculo con
  que se abrieron. No forman parte de esta ficha.
