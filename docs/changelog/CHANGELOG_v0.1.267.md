# OGR Slip2D v0.1.267

**La curva *Simple* queda declarada como convenio de OGR (D190).** La
referencia no publica su función, y ningún problema del banco la distingue
de otra. El 004 del manual de agua se rehace con el modelo de sus figuras:
el banco tenía un dren material que el manual no tiene (D272). El motor no
cambia ningún número.

## 0. Lo que se encontró

### La función *Simple* de la referencia no está publicada

Se buscó en las ayudas de Slide2, RS2 y RS3, en la knowledge base, en los
manuales de teoría y de verificación de agua de los dos programas, en los
tutoriales y en un póster de terceros (Turkson, VandenBerge y Boeglin, Dam
Safety 2020).

- **Lo que sí hay:** palabras. La curva se construye «a partir de la magnitud
  de Ks y del tipo de suelo». *General* baja un orden de magnitud en «el rango
  inicial de succión» y luego es constante. Las texturas son «curvas medias de
  valores típicos de la literatura». Su knowledge base la presenta como un
  modelo tosco, solo para situar la freática en régimen permanente.
- **Lo que no hay:** el rango, cómo entra Ks y las curvas.
- **La física, con fuente.** La escala de succión va como Ks^(−1/2): es la
  capilaridad de Young–Laplace con Kozeny–Carman; Guarracino (2007) lo escribe
  como Ks = 4,65·10⁴·φ·α², con Ks en cm/día y α en 1/cm. Pero esa ley es para
  la α de van Genuchten, no para este rango, y ataría el resultado a la unidad
  de K.

### La puerta de medida (en `_auditoria/P6_0267/` del banco)

**Cuatro lecturas del rango:**
- la de hoy, (100 kPa, 1 década);
- la de antes de D121, con la succión en metros;
- escalada con Ks según Guarracino;
- una empinada, seis décadas en 0,5 kPa.

**Lo que sale en cada problema:**

| Problema | Por la malla | Por la lectura |
|---|---|---|
| 004 rehecho, y1 | 0,440 (2307 T3) → 0,480 (9417 T3) | 0,40–0,50 |
| 001, x_a | 4,23 (manual) → 4,03 (fina) | 4,23 frente a 4,15 |
| 005, P(15, 8) | 0,38 → 0,42 | 0,31–0,38 |

- **El efecto de la malla es tan grande como el de la lectura:** ningún
  problema del banco distingue la función de la referencia.
- **Las lecturas empinadas no convergen en el 001 ni en el 005.** La cara de
  rezume no asienta (1 nodo), aunque el rescate de 0.1.266 sí converge las
  cargas.
- **Decisión de la propietaria:** declarar el convenio.

### El 004 del banco no era el del manual (D272)

**Lo que dicen las figuras 4.2 y 4.5**, rasterizadas y medidas en píxeles
(67 px/m en los dos ejes):

- **la geometría:** un solo material y un polígono (0, 0)–(22, 0)–(23,5;
  1,5)–(12,5; 5)–(10, 5). Tres nodos del talud caen sobre la recta
  (12,5; 5)–(23,5; 1,5) a 0,02 m;
- **las condiciones:** la cara del dren va a 45° hasta el foco (22, 0), con
  H = 0 en el foco, y las demás caras son indefinidas;
- **las medidas:** y1 es la cota de la superficie libre sobre la vertical del
  foco, y x1 la distancia hasta el punto por donde sale por la cara del dren.

**El banco, en cambio**, tenía desde su creación un triángulo de dren con Ks
×1000 a la derecha de x = 19,15:

- **La causa.** Con *Simple/General* (kr ≥ 0,1) el dren conducía sin saturar, y
  la superficie libre caía a la base: P = +0,008 m en y = 0 sobre x = 19,15,
  medido.
- **Los números de antes.** y1 = 0,0101 en todas las versiones. x1 = 2,685 y
  x_fin = 21,835 eran el corte de la rejilla de muestreo de `superficie_libre`.
- **Rehecho:**
  - y1 = 0,4395 con 2400 elementos y 0,480 con la ×4, frente a 0,442 de Slide
    y 0,481 de Kozeny;
  - con 600 elementos la malla no resuelve el pie e y1 sale 0;
  - la malla de 2400 la eligió la propietaria.

### Lo que queda abierto

- **D274.** En el 004 rehecho, x1 = 0,375–0,469 frente a 0,227. La cara de
  rezume es física (los nodos retenidos dan agua saliendo), pero la superficie
  libre sale más alta. Puede ser la curva, o la definición: la ec. 4.2 es el
  vértice de la parábola sobre un dren horizontal, no la salida sobre una cara
  a 45°.
- **D273.** Las bibliotecas Brooks-Corey, Fredlund-Xing y Gardner del botón
  *Pick* no citan tabla de origen. Es la misma clase que D190; la propietaria
  la sacó a ficha propia.
- **`d190()` daba la curva por citada con cualquier año** de los 900
  caracteres anteriores al diccionario (anomalía 16 de la tanda). Corregido en
  el banco: ahora lee el comentario pegado al diccionario y exige una cita
  «Autor (año)». La vía documental exige además que el código declare el
  convenio.

## 1. Lo que cambia

- **`ogr_core/hydraulic/permeability_models.py`** cambia en tres sitios. El
  docstring del módulo, el comentario de `_SIMPLE_PARAMS` y el docstring de
  `kr_simple` dicen que la curva es un **convenio de OGR**, sin fuente:
  - que la referencia no publica la suya;
  - la razón de cada par: *General* (100 kPa, 1 década) pone la caída donde
    están las succiones de los taludes; las texturas mantienen el orden de
    las curvas medias publicadas;
  - que son más suaves que las de Mualem–van Genuchten con las medias de
    Carsel y Parrish (1988), comprobado: Sand −7,7 décadas a 10 kPa, Silt
    −3,8 a 50, Loam −6,2 a 100 y Clay −6,8 a 1500, frente a 4, 3, 3 y 2;
  - y que no depende de Ks, con el porqué.
- **El diálogo de propiedades hidráulicas.** La página *Simple* lleva una nota
  con `tr()` que dice lo mismo, en castellano en la traducción.
- **Ningún número del motor cambia.** El diccionario y la función son los
  mismos.

## 2. Tests

**`tests/test_simple_convention_v1267.py`**, 7 casos:

- **Columna de Gardner (1958) por tipo de suelo.** Por debajo de ψ_ref, el
  convenio **es** la exponencial de Gardner, con
  a = d·ln10·γw/ψ_ref. Hay solución cerrada para la infiltración estacionaria
  sobre un freático: P(z) = ln[r + (1 − r)e^(−az)]/a.
  - Cada tipo tiene su columna, en unidades de su longitud de decaimiento.
  - La tolerancia es de 0,5 % de |P∞|; hoy el error es de 1·10⁻⁵ a 5·10⁻⁵.
- **Ks no cambia la curva:** con Ks de 10⁻³ y de 10⁻⁹ las cargas coinciden a
  10⁻⁶.
- **La succión se lee en kPa:** la de metros pondría el campo lejano 9,81
  veces más hondo.
- **Discriminación.** Con la lectura en metros el error sube a 0,7–3,6; con el
  rango escalado con Ks, a 0,99; cambiando el par de Sand de 10 a 12 kPa, a
  0,18. Es una **guarda del convenio**, no una prueba de que sea el de la
  referencia, y la cabecera lo dice.

## 3. Banco

- **El 004, rehecho** como en el manual (D272), con 2400 elementos y la medida
  de y1 y x1 sobre la isolínea exacta: bisección sobre los T3 en x = 22 y los
  nodos de rezume de la cara del dren. El viejo, en `_auditoria/P6_0267/antes/`.
- **`referencia.json` del 1, el 4 y el 5** con la clave `simple` {fuente,
  razon}. El 4 lleva además la nota del modelo y la de la geometría.
- **Comparativa de la raíz:**
  - y1 del 4: de −97,9 % a −8,6 % frente a la cerrada (−0,6 % frente a Slide;
    la malla fina, 0,480, es la cerrada);
  - x1: de +1017 % a +56 %;
  - **ningún recuento de estado cambia:** las dos filas siguen en
    DISCREPANCIA.
- **Cierres.** `d190()`: CIERRE DOCUMENTAL. `d272()`, nueva: CUBIERTO POR
  CÓDIGO.
- **Fichas.** D272 abierta y cerrada en esta versión; D273 y D274 abiertas en
  P6.

## 4. Verificación

- **Suite entera, sin argumentos: 5721/5721** (los 5714 de 0.1.266 más los 7
  nuevos).
- **Comprobación de cierres de la raíz completa:** 10 claves, 0 bajadas (D121,
  D124, D131 y D250 se sostienen).
- **Auditorías de invariantes:** 0 ERROR en la raíz (82 avisos; los 4 nuevos,
  «ficha abierta sin prompt largo» de D273 y D274) y en el 02.
- **Instantánea `Evaluaciones/0.1.267`,** forzada tras retirar.
- **Lo que queda sin probar:** la nota de la página *Simple* en la aplicación
  real. Se verá al probar a mano D191, que rehace el diálogo.
