# OGR Slip2D v0.1.122

**Muro de contención por presión fluida equivalente** — y la carga
distribuida que llevaba desde siempre tirando media fuerza a la basura.

---

## Lo que se añade

Un octavo tipo de soporte, `RetainingWallEFP`, en su propio módulo
`ogr_core/support/retaining_wall.py`. Un muro cuya capacidad no es un
número sino un **perfil de presión sobre su altura**, que se **integra
desde la coronación hasta el punto donde la superficie de rotura lo
corta**:

```
force_at(d) = ∫₀ᵈ p(x) dx
```

Esa dependencia de **dónde** corta la superficie es lo único que separa un
muro de un ancla de capacidad fija, y es la razón de que sea un tipo de
soporte y no una carga. Cuatro formas de perfil —uniforme, triangular,
trapecial y una tabla de puntos—, cada una con su **primitiva cerrada**: no
hay cuadratura, porque los dos valores publicados contra los que se valida
son exactos y una cuadratura los volvería aproximados sin ganar nada.

Es el defecto **D28** del banco de verificación.

## Un área no fija una forma, y esta feature vive de la integral parcial

El manual publica **312,5** (5 × 125 / 2) y la ayuda publica **2000**
((10 + 6)/2 × 250). Los dos son áreas **totales**, y por tanto validan
`force_at(L, L)` y nada más: el 2000 sería el mismo con la parte plana del
trapecio arriba, abajo o en medio, y toda la máquina depende de la integral
**parcial**, que no.

Lo que sí fija la forma son las figuras **acotadas** de la ayuda:
**0,2H / 0,6H / 0,2H** con EFP·H en el plano para el trapecio, y 0 arriba /
200 abajo para el triángulo de EFP 20 sobre 10 unidades. Un análisis
intermedio propuso un trapecio de **una sola rampa**, razonando que sólo así
la familia es continua —con *repartido sobre* → 0 % daría el perfil
triangular, mientras que el simétrico da un triángulo isósceles con el pico
a media altura—. El argumento es elegante y **no vale**: son cuatro opciones
distintas con parámetros distintos, no una familia de un parámetro, y la
figura está acotada. **Decide la figura, no el razonamiento** — la misma
lección que D16/D17.

## LA IDENTIDAD QUE EL MANUAL ESCRIBE NO SE SOSTIENE, Y NO POR EL MURO

El manual verifica este tipo contra una **carga distribuida triangular**
sobre el trasdós y dice que deben salir idénticos. En OGR no salen, y la
causa es anterior a esta versión: **la misma fuerza horizontal da dos
factores de seguridad distintos según por qué canal entre**. Medido sobre
una fixture común, misma fuerza y mismo punto:

| Métodos | Acuerdo | Por qué |
|---|---|---|
| Corps #1, Corps #2, Lowe-Karafiath | **3e-15** | reconstruyen la resultante cartesiana |
| Ordinary, Spencer, GLE | en el límite | el residuo es **discretización**: −0,009 % con 25 dovelas, +0,0006 % con 400 |
| **Bishop** | **−0,276 %**, y no se encoge | el soporte suma `T_N·tanφ'` al numerador; la carga no |
| **Janbu simplificado y corregido** | **−0,096 %**, y no se encoge | la carga entra en crudo donde el soporte entra proyectado sobre la base: un factor `cos α` |

Los dos comportamientos están justificados por separado en el código desde
v0.1.113 y v0.1.115. **El desacuerdo entre ellos no lo había medido nadie.**
Se mide, se publica y **no se corrige aquí**: elegir uno de los dos es una
decisión con su propia validación, y meterla dentro de una feature sería
exactamente cómo se cuelan los cambios que nadie revisa.

Lo que sí es exacto, y es de lo que esta feature responde: **la resultante y
su punto de aplicación coinciden dígito a dígito**, 5,290232870 kN/m en
y = 7,214710102 por los dos caminos.

La identidad que **sí** se sostiene sustituye a la falsa: lo único que
separa un muro EFP de un `EndAnchored` de la misma capacidad es `force_at`,
así que sobre la misma geometría dan **bit a bit el mismo número en los
nueve métodos** — y el valor de referencia lo produce un tipo ya validado
contra los problemas 48 y 85, no una captura de lo que este código imprime.

## El punto de aplicación: fuerza más par, y su alcance declarado

La referencia deja elegir dónde actúa la resultante: en el corte con la
superficie o en el **centroide** del diagrama por encima del corte.

El camino evidente estaba medido y no valía. `SupportTerms.x_app`/`y_app` se
leen **en un solo sitio de todo el repositorio** y sólo desde la rama no
circular de Spencer/GLE; sobre un círculo el momento de la parte normal es
exactamente cero. Mover ahí el punto no habría cambiado el número en 7 de
los 9 métodos ni en ninguna superficie circular: un combo de dos opciones
que devuelven lo mismo en el 100 % de los casos de validación del proyecto.
Y no lo habría detectado nada, porque **no hay ni un test que fije
`x_app`/`y_app`**.

Lo que se implementa es lo que la mecánica dice: trasladar una fuerza no
cambia la fuerza, deja un **par**. Así que el reparto Activo/Pasivo y la
descomposición T_S / T_N se quedan intactos —y con ellos los tests de
v0.1.113 y v0.1.115, que no se mueven un bit—, y el punto de aplicación
entra como un término **aditivo** `ΔM = F × (r_corte − r_centroide)`, que
vale **cero** para los siete tipos anteriores porque en todos ellos los dos
puntos coinciden.

**Y su límite se declara en vez de esconderse.** Un par sólo tiene dónde
entrar en un método con ecuación de momentos: Ordinary, Bishop, Spencer y
GLE. Los dos Janbu y los tres de marcha resuelven fuerzas y **no pueden
honrarlo**. Medido: los cuatro se mueven un 0,09 %, los cinco restantes
salen **bit a bit iguales**, y el análisis lo dice con un aviso que nombra
los métodos ciegos. Un ajuste que calla su alcance es el mismo defecto que
uno inerte.

## La carga distribuida tiraba media fuerza, y no por una razón sino por dos

1. `_surface_pressure_at` se quedaba **sólo con la componente vertical**,
   `abs(p·dy)`. Con `LoadOrientation.HORIZONTAL`, `dy = 0`: **la carga no
   hacía absolutamente nada**. Un ajuste configurable que no movía el
   número.
2. Muestreaba en la abscisa central de la dovela y exigía `lo ≤ xc ≤ hi`.
   Sobre una cara **vertical** `lo == hi`, así que ninguna dovela caía
   dentro: la carga de la figura 110.2 del manual no la habría visto **ni
   con el signo arreglado**.

Ahora la componente horizontal entra por `add_water_force(f_h, y)`, que es
el canal que la carga lineal usa desde v0.1.75 y cuyo comentario ya decía
con todas las letras lo que modela: *«una fuerza horizontal a una altura»*.
Y una carga sobre un segmento vertical se comporta como una carga lineal de
magnitud la integral, aplicada en el centroide — que es lo que una presión
sobre una cara de anchura nula es.

**No mueve ninguno de los seis modelos del banco que usan carga
distribuida** (9, 25, 26, 37, 60, 107), y el argumento no es de esperanza:
los seis la ponen sobre un segmento **horizontal**, donde
`NORMAL_TO_BOUNDARY` da dirección (0, −1) y la componente horizontal es
exactamente cero. Comprobado midiendo pesos y momentos dovela a dovela
antes y después: **idénticos bit a bit en los seis**.

## La coronación se decide por geometría, no por el orden de dibujo

`force_at` no ve la instancia y no puede saber qué extremo del muro está más
alto. Un muro dibujado de abajo a arriba habría puesto la presión máxima en
la coronación y devuelto **un número plausible y falso**, que es el fallo que
v0.1.112 y v0.1.113 se pasaron dos versiones persiguiendo con la
orientación. Un aviso no lo arregla: el número seguiría en pantalla. Así que
el motor mide desde el extremo **más alto** para los tipos que lo declaran,
y un muro exactamente horizontal —que no tiene coronación— se **excluye**
del análisis con su motivo escrito, en vez de responder desde el orden de
dibujo.

## El problema 110 sigue sin cerrar, y su motivo ha cambiado DOS veces

La ficha del banco decía dos cosas y **las dos eran falsas**:

- *«OGR no tiene presión fluida equivalente»* — cierto hasta esta versión.
- *«El manual no publica ningún factor de seguridad»* — **falso**: la figura
  110.3 publica **2,566** con Spencer, y lo publica **dos veces**, en el
  panel del muro y en el de la carga. Es el mismo patrón del 59 y del 48, la
  figura publica lo que el texto calla. La misma figura publica el **312,5**
  al pie del diagrama de fuerza, que confirma que su superficie sale por el
  pie del muro y moviliza el diagrama entero.

El motivo verdadero es un tercero y es más simple: **el manual no publica
ninguna propiedad del suelo**. Su apartado se titula «Geometry and Material
Properties» y contiene la altura del muro y la tabla de presiones, nada más;
las palabras *unit weight*, *cohesion*, *friction*, *soil* y *strength* no
aparecen en el enunciado. La geometría **sí** es recuperable —la figura está
graduada, el muro va de y = 7 a y = 12, cinco pies exactos, la coronación en
(10 · 20,4)— pero sin γ, c′ y φ′ el 2,566 no se puede recomputar. También su
`referencia.json` declara unidades métricas cuando el problema está en
**imperiales**.

## Además, cuatro defectos encontrados por el camino y **no** corregidos

1. **Los parámetros de un soporte desaparecen al recargar el proyecto.**
   Cuatro consumidores hacen `getattr(s, "support_type", None) or s`, y
   `support_type` no es un campo de `SupportInstance`: lo asigna a mano la
   ventana principal al colocar el soporte y `to_dict`/`from_dict` guardan
   `type_id`. La tabla de propiedades, los data tips, las variables
   aleatorias y el análisis de fuerzas funcionan con el soporte recién
   puesto y se quedan en blanco después de guardar y abrir. **El motor no
   tiene este problema**: resuelve el tipo desde `project.support_types`.
2. **`shear_capacity` es editable, se serializa y el motor no lo consume**
   en los tres tipos que lo declaran. `SUPPORTS_SHEAR` y `shear_at` no los
   lee nadie fuera de `ogr_core/support/support.py`.
3. **`LoadDistribution.TRIANGULAR` y `TRAPEZOIDAL` recorren el mismo
   código**: `pressure_at` es la misma rampa lineal. Tres valores, dos
   comportamientos.
4. **`creates_excess_pore_pressure` se lee del diálogo y nunca llega al
   constructor**, ni en la carga distribuida ni en la lineal. Y
   `SupportForceArrow` no la instancia nadie, con
   `show_selected_support_force` sin consumidor: la flecha de la fuerza del
   soporte no se dibuja nunca.

## Interfaz

El tipo aparece solo en *Properties → Define Support…*, porque ese diálogo
se construye recorriendo el registro. Lo que sí hubo que arreglar allí:

- el caso de la tabla estaba **cableado** a `TYPE_ID == "user_defined"`; ahora
  la clase declara `TABLE_FIELD`, sus columnas y su título, así que la tabla
  del muro dice *distancia relativa* y *presión* en vez de metros y kN;
- **el combo de forma no conectaba ninguna señal**, así que los cuatro
  parámetros convivían siempre y dos o tres no hacían nada según la forma
  elegida — regla 7 dentro del propio diálogo. Ahora se deshabilitan los que
  la forma no lee, y la tabla sólo aparece con el perfil personalizado;
- **duplicar una fila compartía la lista** entre original y copia
  (`cls(**src.support.__dict__)`); era un defecto latente del tipo
  definido por el usuario y con el muro habría sido alcanzable;
- el tooltip del lienzo decía *«Force at head»*, y para un tipo cuyo perfil
  se integra desde la coronación ahí vale **cero por definición**.

## Pruebas

`tests/test_efp_wall_v1122.py`, 41 tests. Los dos valores publicados a la
última cifra, las cotas de las dos figuras acotadas, la forma del diagrama
de fuerza, la identidad contra `EndAnchored` bit a bit en los nueve métodos,
la forma cerrada con φ′ = 0, la regla 7 de cada parámetro **y las dos
mitades** de la afirmación sobre el punto de aplicación —mueve cuatro
métodos y **no puede** mover cinco—, el muro dibujado del revés, la carga
horizontal que deja de ser inerte y la carga sobre cara vertical.

Un test congela además el desacuerdo entre canales **como hecho medido**:
si algún día se cierra, ese test falla y obliga a reescribir lo que este
changelog afirma, que es exactamente para lo que está.

Dos tests existentes se tocaron, ninguno para hacerle sitio a un cambio:
`test_support_orientation_v1112` congela el catálogo a propósito —*«a new
plugin should make this fail rather than slip through untested»*— y recibe
la entrada del muro con su razón; y `test_seven_types_registered` pasa a
llamarse `test_the_known_types_are_registered`, porque comprueba inclusión y
su nombre había empezado a mentir.

## Suite

2560 / 2560, sin argumentos.
