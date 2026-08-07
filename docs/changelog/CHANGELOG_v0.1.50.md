# OGR Suite v0.1.50 — Changelog

**Lanzamiento:** 6 de agosto de 2026
**Desarrollador:** Samuel Sáez López — Estudiante de Doctorado, UPCT
**Licencia:** AGPL-3.0-or-later

> **Fase I2: motor de contornos.** Paletas, rangos, intervalos y modos de
> dibujo, con leyenda y lienzo compartiendo una sola fuente de verdad.
> **Primera versión con más de mil tests.**

---

## 🆕 `ogr_gui/contours.py`

Deliberadamente **libre de Qt** —devuelve cadenas `#rrggbb`— para que el
mapeo valor→color pueda probarse, y reutilizarse en informes o
exportaciones, sin necesidad de pantalla.

**Seis paletas**: Stability (convención roja = inseguro), Hot to cold,
Viridis, Blue to red, Greyscale y **Accessible** (derivada de Okabe-Ito),
estas dos últimas porque una figura de informe puede tener que seguir
siendo legible impresa en blanco y negro o para lectores con deficiencia
en la visión del color.

**Cinco modos**: relleno, relleno con líneas, líneas, degradado continuo y
desactivado.

### Tres decisiones de diseño

**Bandeado por defecto, no continuo.** Un gráfico de contornos de
ingeniería se lee como intervalos discretos porque así es como se saca un
número de una escala de color. Un degradado continuo queda más bonito y se
usa peor, así que el modo relleno **ajusta cada valor al centro de su
banda** y el degradado se ofrece aparte para quien lo quiera.

**Recorte, no descarte.** Un valor fuera del rango conserva el color del
extremo, de modo que estrechar el rango para estudiar un detalle no deja
el resto del modelo en blanco.

**El rango automático ignora los extremos.** Una sola superficie con
factor 40 aplastaría todo lo demás en una banda, así que el límite
superior sale de un percentil. El **límite inferior se toma tal cual**:
en estabilidad, el extremo bajo es precisamente lo que importa.

## 🆕 Diálogo de opciones de contorno

Campo escalar, rango (automático o manual), número de intervalos con el
tamaño de intervalo calculado en vivo, modo, paleta, inversión de colores
y formato numérico.

- **La vista previa es real**: una tira con los colores de banda
  efectivos, dibujada con la misma función que el gráfico. Una lista de
  nombres de paleta no dice nada.
- **El rango automático es una casilla, no un botón.** Activado sigue a
  los datos según cambian los resultados; un botón de «ajustar» de un solo
  disparo quedaría obsoleto en silencio al cambiar de método.

## 🔗 Una sola fuente de verdad

El lienzo acepta ahora una **función de color inyectada**
(`set_contour_colour_fn`), y tanto él como la leyenda reciben **el mismo
`ContourSettings.colour_for`**. Cambiar la paleta, el rango o el número de
intervalos llega a los dos sin más fontanería, y no pueden discrepar.

Se actualizó en consecuencia un test de v0.1.49 que comprobaba la función
antigua del lienzo: **el invariante no cambia** —una sola fuente de
verdad— solo se movió el objeto que la proporciona, y así queda escrito
en el test.

## 🔴 Una trampa de la edición automática

Al insertar `set_contour_colour_fn` justo antes de `_fos_to_color`, el
`@staticmethod` que decoraba a esta última acabó decorando al método
nuevo, que dejó de recibir `self`. Se detectó al primer uso. Merece
mención porque es el tipo de fallo que una inserción por texto produce y
la sintaxis no delata.

## 📊 Tests

**1001 tests, 1001 verdes** (+39 desde v0.1.49; suite 100 % desde
v0.1.21).

Cobertura (`tests/test_contours_i2_v150.py`): paletas (todas con topes
válidos, muestreo en los extremos, interpolación, recorte fuera de rango,
paleta desconocida con reserva, y disponibilidad de las accesibles);
bandeado (**valores de una banda comparten color**, el modo continuo no
bandea, límites de nivel, número de colores, índices acotados); rango
(recorte, rango degenerado sin división por cero, valores no finitos,
inversión); rango automático (**ignora los extremos**, conserva el extremo
bajo exacto, datos constantes, datos vacíos); formato y serialización;
campos disponibles (solo los que tienen datos detrás); diálogo (modos y
paletas, casilla que deshabilita los límites, ajuste a los datos, tamaño
de intervalo, vista previa que sigue a los ajustes, recogida al aceptar,
restaurar valores); e integración (**leyenda y lienzo comparten la misma
función**, la paleta se propaga, el rango sigue a los resultados, el modo
desactivado limpia la sobrescritura, y la entrada está en el menú View).

## ⏳ Siguiente

**Fase M1 — Data Tips y Snap**: las propiedades al pasar el cursor sobre
materiales, soportes y cargas —pedidas en el párrafo de apertura del
prompt— y Snap / Ortho / OSnap con barra de estado sincronizada.

---

© 2026 Samuel Sáez López — UPCT — AGPL-3.0-or-later
