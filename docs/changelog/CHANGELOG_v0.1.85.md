# OGR Slip2D v0.1.85 — el lienzo no se podía mover, y la regla viajaba con el dibujo

Dos quejas del informe del Ejemplo 2, y las dos con la misma forma: algo
que **parecía** de dibujo y era de arquitectura.

**Ningún cálculo cambia.** Esta versión no toca el motor.

---

## 1 · El arrastre no llevaba a ninguna parte

El pan mueve las **barras de desplazamiento**, y las barras no pueden
salirse del `sceneRect`. Ese rectángulo era fijo: la caja del modelo más la
mitad de sí misma, o un `(-5, -5, 60, 40)` clavado cuando no había nada
abierto. Medido antes del arreglo:

```
sin ningún archivo abierto : sceneRect = (-5,-5,60,40)   recorrido h = 0   v = 0
Ej_2 en zoom de ajuste     : sceneRect = bbox + 50 %     recorrido agotado
Ej_2 tras acercar el zoom  : recorrido h = 7164  v = 5891
```

Es decir: **con el programa recién abierto las dos barras tenían recorrido
cero** y el dibujo no se movía en absoluto. Y con un modelo cargado, al
nivel de zoom con el que el programa lo abre, el arrastre se paraba en
seco. Acercar el zoom generaba recorrido y tapaba el problema, que es por
qué se leía como «solo me deja moverme si estoy con zoom».

Eso convertía en imposible lo más elemental: empezar a dibujar en la
coordenada `y = 200` obligaba a teclearla, porque hasta allí no se podía
llegar.

### No es un rectángulo más grande

Un `sceneRect` enorme y constante habría cambiado el problema por otro
—barras sin resolución, y el tamaño de las cruces de la rejilla de centros
se calculaba a partir de él—. Lo que hace ahora `_grow_scene_rect` es
mantener **un viewport de holgura alrededor de lo que se ve**, en las
cuatro direcciones. Siempre hay adónde desplazarse, el área alcanzable es
ilimitada en la práctica, y el rectángulo sigue siendo del tamaño de lo que
el usuario está mirando.

Crece durante la navegación y **solo Zoom All lo devuelve al modelo**, que
es lo que mantiene las barras con significado. Y un redibujado ya no
arrastra la vista de vuelta encima del modelo: quien se ha desplazado se
queda donde estaba.

Medido después, con la misma ventana de 900×600:

| | antes | ahora |
|---|---|---|
| recorrido sin proyecto | 0 , 0 | 39122 , 26056 |
| `sceneRect` tras Zoom All (Ej_2) | bbox + 50 % | 542 × 361 |
| paso por arrastre, 5 arrastres seguidos | se agota | 60,40 constante |

### El fallo que me comí por el camino

La primera versión de esto no encogía nunca. `_grow_scene_rect` llamaba a
`self.setSceneRect(...)` —el de la **vista**— y `_reset_scene_rect` a
`self.scene().setSceneRect(...)` —el de la **escena**—. No son lo mismo:
**en cuanto una vista tiene su propio `sceneRect`, ignora el de la
escena**, así que el reset parecía funcionar y no hacía nada. Zoom All
devolvía la vista al modelo pero dejaba el rectángulo a 2694 de ancho.
Queda escrito en el docstring porque el síntoma (una llamada que no falla y
no hace nada) no se parece a la causa.

El cursor de mano durante el arrastre ya estaba puesto desde antes; lo que
faltaba era sitio adonde arrastrar.

## 2 · Las coordenadas «hacían cosas raras»

La regla se dibujaba desde `drawBackground`, que pinta en la capa de la
**escena**. Dentro hacía `resetTransform()` y escribía las etiquetas en
coordenadas de **viewport**: texto que pertenece a la ventana, viviendo en
la capa que Qt desplaza.

Con el `viewportUpdateMode` por defecto (`MinimalViewportUpdate`), al hacer
scroll Qt **desplaza los píxeles ya pintados** y repinta solo la banda
recién descubierta. Resultado: las etiquetas viejas viajaban con el dibujo
mientras la banda nueva recibía otro juego en su sitio correcto — varias
columnas de números apiladas y desplazadas por el medio del modelo, que es
exactamente la captura del informe.

Una superposición hay que pintarla **después** de la escena, **sobre todo
el viewport**, y **cada vez**. Así que la regla se mudó a `paintEvent` y el
lienzo pasa a `FullViewportUpdate`.

`_draw_ruler` ya no recibe un rectángulo de escena. No es cosmética: el
parámetro era la invitación al error, porque sugería que las coordenadas
del dibujo tenían algo que decir sobre dónde va una etiqueta de la ventana.
Hay un test que comprueba su firma por eso mismo.

## 3 · Las cruces de la rejilla dependían del `sceneRect`

Efecto colateral del punto 1: el tamaño de las cruces de los centros de
giro se estimaba como `sceneRect.width() / ancho_viewport * 4`. Con un
`sceneRect` que ahora crece al desplazarse, las cruces habrían **engordado
al pasear**. La magnitud que se quería siempre era píxeles por unidad, que
no depende de hasta dónde haya llegado nadie desplazándose.

---

## Verificación

`tests/test_canvas_pan_ruler_v185.py`, nuevo, 12 casos. Los que importan:

- las dos barras tienen recorrido **sin ningún proyecto abierto** y al zoom
  de ajuste del modelo — los dos casos que estaban a cero;
- **cinco arrastres seguidos en la misma dirección avanzan lo mismo**. No
  basta con que el primero funcione: un rectángulo que solo creciera una
  vez dejaría pasar el primero y pararía el tercero;
- ida y vuelta devuelve la vista al punto exacto de partida;
- Zoom All vuelve al modelo **y** encoge el rectángulo — el caso que
  destapó el fallo de vista-contra-escena;
- un redibujado no mueve al usuario de donde estaba;
- la regla no se pinta en la capa de la escena, su firma no admite
  rectángulo de escena, y el lienzo repinta el viewport entero.

Suite completa, sin argumentos.
