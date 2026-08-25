# Contorno de capa débil

## Qué hace

Añade un tipo de contorno nuevo —la **capa débil**— que es una polilínea con
resistencia propia, distinta de la del material a un lado y a otro, y que la
superficie de deslizamiento recorre en lugar de atravesar.

## Por qué

Hay juntas e interfaces cuyo espesor es despreciable frente al modelo pero cuya
resistencia decide la rotura: las hiladas de un muro de gaviones, una
geomembrana, un plano de estratificación. Hoy sólo se pueden emular con bandas
finas de material, y eso es otro problema: una banda tiene espesor y la
superficie puede cortarla en diagonal, mientras que una junta obliga a la
superficie a **seguir la línea**. Con juntas de 1 m entre gaviones de 1×1 m, esa
diferencia es el problema entero.

Es el único hueco que separa al problema 109 del banco de estar reproducido: su
geometría, sus materiales y su búsqueda están todos publicados, y los problemas
107 y 108 —la misma familia, el mismo método de cohesión equivalente— ya salen.

## Criterios de aceptación

- [x] Existe `BoundaryType.WEAK_LAYER`, se dibuja, se guarda en el `.ogr` y se
      recupera con su material asignado.
- [x] Una superficie que toca una capa débil activa la **recorre**: los tramos
      marcados aparecen en la superficie analizada, no sólo en el dibujo.
- [x] Las dovelas cuya base va sobre la junta usan **la resistencia de la
      junta**; el **peso** sigue saliendo de los materiales de la columna.
- [x] Los extremos de cada tramo sobre la junta son **cortes obligatorios** de
      dovela: ninguna base queda medio dentro y medio fuera.
- [x] Identidad: la trayectoria recortada, entrada **a mano** como superficie
      no circular ordinaria, da el mismo factor **dígito a dígito**.
- [x] Identidad: una junta que aporta una resistencia da el mismo factor que un
      modelo hecho **entero** de ese material sobre el mismo camino, **dígito a
      dígito**, en Ordinary, Bishop y Janbu.
- [x] Forma cerrada: sobre una superficie **plana** de un solo material y sin
      agua, Ordinary da F = (c·L + W·cosα·tanφ)/(W·senα) dentro de 1e-9, y el
      valor no se mueve con el número de dovelas.
- [ ] Problema 109 del banco: los cuatro métodos dentro del **±3 %** de
      Bishop 1,799 · Janbu 1,610 · Spencer 1,803 · GLE 1,804, y la **razón
      Janbu/Bishop** dentro del 1 % del 0,8949 publicado.
- [x] Dos modos de tratamiento, y los dos **mueven el número** sobre un modelo
      con dos juntas donde la crítica es la inferior: *pegar siempre a la capa
      más alta* y *generación automática de casos*.
- [x] `suppressed` excluye la capa del análisis sin borrarla, y **cambia** el
      factor.
- [x] Existe un límite de ángulo de base (θ_max, 80° por defecto) que descarta
      superficies que sin él pasan.
- [x] *Añadir capa débil* es alcanzable desde el menú **Boundaries**, y el modo
      de tratamiento desde *Surface Options*.
- [x] Todo texto nuevo pasa por `tr()` y tiene traducción castellana con la
      terminología geotécnica estándar (*capa débil*, no *capa floja*).
- [ ] La suite entera en verde: ningún modelo sin capas débiles se mueve.

## Validación numérica

Tres anclas externas, ninguna de ellas una captura de lo que el código imprime:

1. **Forma cerrada** — sobre una superficie plana de un solo material y sin
   agua, Ordinary/Fellenius se reduce exactamente a
   F = (c·L + W·cosα·tanφ)/(W·senα), y no depende del número de dovelas.
2. **Identidad de trayectoria** — el camino recortado, escrito a mano como
   superficie no circular, tiene que dar lo mismo. Protege el recorte de
   introducir sesgo por sí solo.
3. **Identidad de los dos modelos** — una junta que aporta una resistencia
   frente a un modelo hecho entero de ese material. Dos descripciones
   independientes del mismo mecanismo.
4. **Caso publicado** — problema 109 del manual de verificación, cuya fuente de
   fondo es Cao et al. (2016) y Grodecki (2017) para la cohesión equivalente del
   gavión. Cuatro métodos publicados y la geometría rotulada punto a punto en su
   figura 109.1, idéntica a la del problema 108 que el banco ya reproduce.

**Corrección de una premisa de esta misma especificación.** La primera
redacción pedía otra identidad —*«una capa débil con el material del entorno
devuelve el factor de siempre dígito a dígito»*— y **es falsa**: la capa sigue
**recortando** aunque su resistencia sea la del suelo, así que el mecanismo
analizado es otro. Medido: 2,651020 → 2,796720, un +5,5 %. Las tres anclas de
arriba son las que sí se sostienen.

El criterio del 109 es del **±3 %** y no del 2 % habitual, y la razón está
medida: el problema 108 —misma geometría, misma cohesión equivalente, sin capas
débiles— reproduce su tabla a **+2,87 %**. Ese sesgo es del método de cohesión
equivalente, no de esta feature, así que el criterio lleva una segunda pieza
—la razón Janbu/Bishop— que lo cancela.

## Fuera de alcance

- El **modo heurístico** de tratamiento de capas débiles. En la referencia sólo
  existe sobre Particle Swarm Optimization, que no está implementado (D24): hoy
  no tendría dónde engancharse.
- Que una capa débil defina **regiones de material** o se interseque con otros
  contornos. Por definición no lo hace: es una entidad independiente.
- Capas débiles **verticales**. Se admiten y se descartan las superficies que
  producen cortes verticales en zona de compresión, pero no se implementa
  ninguna estrategia para rescatarlas.
- El acoplamiento con el mallado de filtración: una capa débil no entra en la
  malla de elementos finitos.
