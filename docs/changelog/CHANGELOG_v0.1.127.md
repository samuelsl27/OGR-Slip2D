# OGR Slip2D v0.1.127

**Análisis de Newmark**: el desplazamiento sísmico permanente, el
coeficiente sísmico crítico que lo alimenta, y el acelerograma que hasta
ahora no era un tipo de dato de este programa.

Cierra **D25**, el último de los siete huecos de funcionalidad (D24–D30)
del banco de verificación.

---

## Qué se añade

### El acelerograma

`ogr_core/loads/seismic_record.py`. Un registro se guarda **dentro del
`.ogr`**, no como ruta a un archivo de fuera: ésa es la trampa que este
programa ya pagó una vez con los campos de filtración por elementos
finitos, que no se serializaban hasta v0.1.78 y se analizaban como `u = 0`
sin decirlo. Unos 60 kB por registro de 5000 muestras.

Dentro las aceleraciones están **siempre en g**; la unidad del archivo se
convierte al entrar y se recuerda sólo para poder decir de dónde vienen.
Importación de las dos disposiciones que Jibson (1993) nombra —pares
tiempo-aceleración, y una columna a intervalo constante—, decidida por lo
que el archivo contiene y no por una opción que el usuario tenga que
acertar.

### El coeficiente sísmico crítico Ky

`ogr_slip2d/yield_acceleration.py`. Resuelve `FS(k_h) = objetivo` con un
barrido ascendente desde cero —con predicción secante limitada a dos
pasos, para que el primer cruce siga siendo el primero— y refinamiento por
el método de Illinois. **Nueve evaluaciones** sobre una superficie real,
donde una bisección a 1e-4 costaba catorce.

Tres desenlaces, y son respuestas distintas y no grados de la misma:
`FS(0) ≤ objetivo` da **Ky = 0**, que es lo que la referencia documenta;
un cruce da el número **y el factor que el solver obtiene ahí**, que es la
verificación que la propia referencia se hace; y sin cruce por debajo del
techo **no hay número**, se explica, y esa superficie queda fuera de la
ordenación en vez de contar como fuerte.

Las dovelas se reaprovechan tal cual entre pruebas. No es una optimización
con salvedad: **el dovelador no lee el coeficiente sísmico**, así que son
las dovelas correctas para cualquier `k_h`.

### El desplazamiento de Newmark

`ogr_slip2d/newmark.py`. El esquema de Wilson y Keefer (1983) tal como
Jibson (1993) lo publica paso a paso, con la modificación que prohíbe el
movimiento talud arriba. Tres detalles no son elecciones libres y se
reproducen a propósito: la resistencia se toma **en el sentido del
deslizamiento** mientras el bloque desliza, el deslizamiento **para**
cuando la velocidad relativa deja de ser positiva, y las dos integraciones
son **trapeciales**. La aritmética se hace en cm/s² y cm, que es lo que el
programa publicado usa, para que su umbral de reposo signifique aquí lo
que significa allí; `g = 980,665 cm/s²` exactamente.

Cuatro polaridades de las cinco que la referencia ofrece. La quinta, *All
Accelerations*, **no se implementa**: su ayuda no la define y se solapa
con el ajuste de sentido, así que ponerla sería adivinar. El **bloque
flexible (acoplado y desacoplado) queda fuera**, dicho por escrito: pide
velocidad de onda de corte por encima y por debajo, amortiguamiento y una
respuesta de sitio 1-D que este programa no tiene, y ofrecerlo
deshabilitado sería anunciar algo que no existe.

### El objetivo de la búsqueda, que es el cambio de fondo

Preguntado por el coeficiente crítico, la referencia informa de «la
superficie que requiere el valor MÁS BAJO de Ky», y avisa de que es «quite
different from the critical surface». Así que lo que una búsqueda
minimiza deja de ser el factor de seguridad, y las comparaciones
`a.fos < b.fos` repartidas por las siete búsquedas pasan a ser **una
función, en un solo sitio**: diez en `search.py`, una en el enjambre, dos
en `SearchResult` y cinco en el paseo de optimización.

Por defecto esa función **es el factor de seguridad**, y ahí está la
prueba de que el cambio se podía hacer: con los modos apagados, una
búsqueda a la que se le pasa el objeto de ajustes tiene que devolver
salida **bit a bit** idéntica a otra que nunca supo de él. Es un test.

**Y hay un regalo que ahorra casi todo el coste del modo Newmark**: el
desplazamiento de un bloque rígido es monótono no creciente en la
aceleración crítica, porque el integrando `(a − a_c)₊` lo es punto a
punto. Luego **máximo desplazamiento ⟺ mínimo Ky**, y el modo Newmark
reutiliza el objetivo de Ky sin integrar el registro dentro de la
búsqueda: el registro se integra una vez por superficie al final, para
informar.

---

## Lo que dice la validación, y de dónde sale cada número

**Nada de instantáneas.** No hay ningún acelerograma en este repositorio y
no va a haberlo, así que todo lo que sujeta el integrador es forma cerrada
o identidad — y para este cálculo eso es evidencia **más fuerte** que un
registro, porque clava el resultado en vez de atarlo a la digitalización
de un acelerograma de 1979.

### La forma cerrada de Newmark (1965) sale a precisión de máquina

Pulso rectangular de amplitud `A·g` durante `t₀` contra una crítica
`N·g`: `u = V²/(2gN)·(1 − N/A)` con `V = A·g·t₀`. Derivada aquí y
contrastada con una forma publicada independiente,
`u = (a_p T_p²/2)(a_p/μg − 1)`: son la misma expresión.

**Cuando el instante de parada `t_m = (A/N)·t₀` cae en una muestra, el
esquema trapecial la reproduce a 1e-15, con cualquier paso** entre 20 ms y
0,6 ms. No era lo esperado —el esquema arrastra medio paso de déficit en
la velocidad al arrancar el pulso— y se cumple porque ese mismo medio paso
reaparece con signo contrario al terminarlo. Cuando la parada cae entre
muestras se pierde el resto del triángulo de velocidad, y ese residuo es
≤ 3,7e-4 relativo con dt = 20 ms y baja a 4e-8 al refinar.

**Un error de banco de pruebas que costó media hora y merece quedar
escrito**: el primer barrido de veinte combinaciones daba **26 %** de
error. No era el integrador: la cola de registro en calma era de 20 s y
con `A/N = 60` el bloque desliza **42 s**. La medición estaba truncando la
respuesta. Con la cola dimensionada por `t_m` las veinte salen a 1e-13.

### Tres identidades más, todas exactas

- **`a_c = 0` con los dos sentidos permitidos ⇒ el desplazamiento relativo
  ES el del terreno**, dígito a dígito. Es la que caza un desfase de
  índice, una unidad o un factor `g` perdido, ninguno de los cuales vería
  la forma cerrada, que tiene un solo número dentro.
- **`a_c ≥ PGA ⇒ cero exacto**. Daba 1,7e-16 hasta que la rama que Jibson
  escribe como `N = A/T` se escribió como el cero que significa: `(a/t)*t`
  no es `a` en coma flotante. El programa publicado arrastra el mismo
  residuo y en centímetros nadie lo ve.
- **Semejanza**: escalar registro y crítica por `s` multiplica el
  desplazamiento por `s`; estirar el eje de tiempos por `τ` lo multiplica
  por `τ²`. Las dos exactas.

### Ky contra forma cerrada y contra un valor publicado

- **`k_y = tan(φ − β)`** sobre un plano sin cohesión: **2,7e-8** con los
  dos Corps of Engineers y Lowe-Karafiath, y 3,9e-8 con Janbu
  simplificado. Son los métodos cuyas hipótesis **son** la cuña única
  sobre un plano; no es una tolerancia elegida para que pase una lista.
- **Ordinary y Bishop NO la reproducen**: +6,2 % y +7,1 %. Está medido, no
  tolerado: sobre superficie no circular un método de sólo momentos
  depende de dónde se tomen, que es la anomalía **D47** que
  `test_moment_axis_v1126.py` mide sobre el propio factor de seguridad.
  Aquí aparece en Ky, sobre la misma superficie y con el mismo signo.
- **Loukidis, Bandini y Salgado (2003), ejemplo 1**, que publica el
  coeficiente crítico: **0,432** en seco y **0,132** con `ru = 0,5`. Hasta
  ahora este programa sólo podía comprobarlo **al revés** —meter el valor
  publicado y mirar si el factor sale 1—. Ahora lo calcula **en el sentido
  en que se usa**: Spencer da **0,4330 (+0,23 %)** y **0,13297 (+0,73 %)**,
  y GLE +0,09 % y +0,35 %. El cociente publicado 0,132/0,432 = 0,3056
  también sale, y ése cancela el sesgo común.

---

### El problema 104 del banco cierra en tres de sus cuatro escenarios

Con la búsqueda que el enunciado declara —enjambre multimodal con
optimización—, Spencer, 25 dovelas y el filtro de área de 1:

| escenario | magnitud | **OGR** | publicado | Δ |
|---|---|---|---|---|
| sin sismo | factor de seguridad | **1,359481** | 1,359 | **+0,04 %** |
| k = 0,15 | factor de seguridad | **0,986856** | 0,978 | **+0,91 %** |
| aceleración crítica | Ky | **0,13835** | 0,139 | **−0,47 %** |
| desplazamiento | cm | no reproducible | 5,042 | — |

**Y su geometría, que la ficha del banco daba por perdida, estaba.** El
manual dice que el problema sale de un tutorial; ese tutorial declara que
su modelo es el **problema de verificación #4**, que el banco ya tenía
construido con confianza alta. Lo corroboran tres cosas más: las razones
1,359/1,375 y 0,978/0,991 coinciden en el 0,15 %; los ejes de la figura
104.2 encajan; y —esto no lo buscaba nadie— **las superficies optimizadas
afloran en x = 29,69 y 50,91**, contra los **29,702 y 50,991** del círculo
crítico publicado. Una búsqueda no circular vuelve por su cuenta a los dos
puntos por los que sale el círculo del manual.

**El escenario 3 confirma además el aviso de la referencia**: la superficie
de Ky mínimo aflora en 29,993 … 51,647 y tiene un factor de **1,368506**,
un 0,66 % por encima del mínimo estático de 1,359481. **No es la misma
superficie.** Buscar una y publicar la otra habría dado un Ky plausible y
equivocado, que es exactamente por qué el objetivo de la búsqueda tenía que
cambiar y no bastaba con calcular Ky al final.

Y la verificación que el propio manual se hace —aplicar el Ky encontrado a
su superficie y obtener 1,000— sale **exacta**.

## Tres defectos que salieron de releer lo escrito, no de un test en rojo

Ninguno de los tres lo destapó una prueba en rojo: los tres salieron de
volver sobre el código ya escrito preguntando «¿y esto qué lee?».

### 1 · El factor de partida del solve de Ky era el factor CON el sismo

`_analyse` le pasaba al solver el factor de seguridad que acababa de
calcular, como punto de partida del barrido sobre `k_h`. Ese valor es
`FS(0)` **sólo si el proyecto no aplica coeficiente propio**. Un modelo con
`k_h = 0,15` guardado habría anclado el barrido en el factor CON terremoto y
luego caminado `k_h` desde cero: todos los intervalos mal, y un Ky
perfectamente plausible de vuelta. Ahora, cuando el proyecto aplica
coeficiente, el solver evalúa `FS(0)` él mismo —una evaluación más y la
pregunta correcta— y **el análisis avisa** de que el coeficiente crítico
sustituye al guardado en vez de sumarse a él.

### 2 · La optimización descendía el factor de seguridad, no el objetivo

`optimize_surface` minimizaba `res.fos` mientras la búsqueda que lo rodea
ordenaba por Ky. Con el modo sísmico encendido el paseo arrastraba los
vértices hacia un factor de seguridad bajo y la corrida informaba después
el Ky de donde hubieran ido a parar: **una optimización optimizando algo que
nadie ha pedido**. Y es justo la configuración del problema 104. Ahora el
paseo lee el objetivo del evaluador, y su criterio de parada también —una
regla de parada que vigila una magnitud distinta de la que se desciende
puede parar mientras esa magnitud sigue bajando.

**Coste declarado**: con un modo sísmico encendido, la Tolerancia del
usuario pasa a ser una tolerancia sobre Ky, cuya escala es un orden de
magnitud menor que la de un factor de seguridad.

### 3 · La terminal habría dicho «Critical FoS» sobre una columna de Ky

El mismo fallo que se corrigió en la ventana de Interpret estaba en la
línea de órdenes, y no se habría visto desde la ventana. Las dos son
puertas al mismo resultado y las dos leen ahora el objetivo **del
resultado** y no de los ajustes: una ventana que lee los ajustes puede
contradecir los resultados que está enseñando.

Aparte, el archivo `.h5` de resultados guarda ahora el objetivo y los dos
extras sísmicos, porque un archivo que sólo registra factores de seguridad
no puede decir cuál era la superficie respuesta cuando la respuesta era un
coeficiente.

Y hay un aviso nuevo para una combinación que nadie pedirá a propósito: un
análisis **probabilístico** con un modo sísmico encendido toma estadística
de `critical.fos`, que bajo el objetivo Ky es el factor de la superficie de
**Ky mínimo** y no el factor mínimo de la muestra.

## Lo que se encontró por el camino

### El factor de seguridad de Spencer da un salto en el coeficiente sísmico

Medido sobre el círculo de Loukidis, entre `k = 0,4325` y `k = 0,4330`:

    k        FS         lambda
    0.4325   1.001017   0.58043
    0.4330   0.996266   0.55162      <- salto
    0.4350   0.993402   0.55310
    0.4355   0.995900   0.57381      <- y no es monótono

`FS(k)` **no es continua** ahí: la búsqueda de λ cambia de raíz. El
intervalo se encuentra igual y el Ky sale bien a un cuarto de por ciento,
pero **el factor EN Ky se queda en 0,9963 en vez de 1,0000**. Lo destapó
precisamente esta feature, porque es la primera cosa que evalúa el mismo
círculo en muchos coeficientes seguidos. Queda medido y con su test, que
falla si algún día deja de pasar — no ensanchado hasta que la
discontinuidad quepa dentro.

Es familia conocida: las raíces espurias de λ que v0.1.106 documentó.

### Spencer y GLE no convergen sobre un plano de dos vértices con sismo

Sobre la cuña plana usada para `tan(φ − β)`, Spencer devuelve NaN desde
`k = 0,05` y GLE desde `k = 0,10`, mientras los otros siete responden.
Es una superficie degenerada —una recta, sin cuña de pie— y no es un
defecto que esta versión introduzca, pero conviene que esté escrito: los
dos métodos que resuelven fuerzas **y** momentos son los que se caen en el
caso más simple que existe.

### Una lista de páginas escrita a mano, otra vez

`test_project_settings_wiring_v174.py` afirmaba `d.nav.count() == 9`, y la
página *Seismic* la hizo fallar. El test venía del defecto de v0.1.74, que
fue exactamente **una segunda lista de páginas escrita a mano**; el número
9 escrito en el test era una tercera. Ahora lo toma de `_PAGES`.

---

## El coste, medido y declarado

El modo Ky cuesta **nueve evaluaciones por superficie donde había una**, y
eso no es el precio de esta implementación sino el de la pregunta: el
coeficiente está definido por una ecuación que hay que correr el solver
para evaluar.

Donde se nota de verdad es en la **optimización de superficie**, porque su
paseo evalúa hasta 4000 candidatas por superficie y ahora cada una lleva su
solve de Ky. En la corrida del problema 104, con el mismo modelo, el mismo
enjambre y la misma semilla:

| escenario | objetivo | tiempo |
|---|---|---|
| 1 · sin sismo | factor de seguridad | **133,7 s** |
| 2 · k = 0,15 | factor de seguridad | **119,6 s** |
| 3 · aceleración crítica | Ky | **397,9 s** |

Los dos primeros son los **controles**, y se separan un 12 % entre sí: eso
acota el ruido de la medida. El efecto es **3,1×**, muy por encima de ese
ruido, así que la medición sí resuelve — es un A/B en el mismo proceso,
espalda con espalda, que es la única forma de medir que este proyecto
acepta.

Menos de los 9× que el recuento de evaluaciones sugeriría, y la razón es
que el paseo converge antes de agotar sus 4000 iteraciones y que el
rebanado, los filtros y la generación no se multiplican por nada.

Es un modo que se pide, no el camino por defecto: con los dos interruptores
apagados no hay ni una evaluación de más, y la salida es bit a bit la de
siempre.

## Interfaz

- **`Cargas → Registros sísmicos...`**, acción nueva en la barra de menús
  (regla 3), con su diálogo de definición e importación. Edita una
  **copia** de la lista, así que Cancelar cancela de verdad; y si se borra
  el registro que la página de ajustes tenía elegido, la elección se
  vacía en vez de apuntar a nada.
- **Página *Seismic* en Project Settings**, con los dos interruptores, el
  factor objetivo, el registro, la polaridad, el sentido y el factor de
  escala. Los controles que la opción elegida no lee se deshabilitan.
- **Interpret informa la magnitud que el análisis minimizó**, y no
  «FoS» sobre una corrida de Ky. El desplazamiento se imprime por la
  magnitud `SMALL_LENGTH` que la página de unidades ya reserva para
  asientos y desplazamientos, así que un modelo métrico lee centímetros y
  uno imperial pulgadas.
- Traducciones al español de las 37 cadenas nuevas. **«Ky:» entra en la
  lista blanca de identidades** como símbolo, junto a «Cr:», «d:» y «mi:»,
  sin subir el tope de 12: quedan 10 de 12.
- Y una de esas 37 la cazó el test de cobertura y no yo: `Critical surface`
  va dentro de una f-string con **comillas simples**, que es justo la forma
  que un rastreador ingenuo de `tr("...")` no ve. El test sí la ve, y por
  eso existe.

---

## Lo que NO se ha hecho, y por qué

- **El escenario 4 del problema 104 no se cierra.** Los 5,042 cm
  publicados se calcularon con un registro concreto —Mammoth Lakes-1 1980,
  estación CVK, componente 090, PGA 0,416 g— que no está en el banco.
  Cualquier número en esa casilla sería el de otro cálculo con otro
  nombre.
- Y la propia Tabla 104.1 **es internamente incoherente** en ese punto: el
  desplazamiento de un bloque rígido decrece con la aceleración crítica,
  así que `Ky = 0,139` tendría que dar **más** que `Ky = 0,140`, y publica
  5,042 contra 5,081. La explicación es que los cuatro escenarios son
  cuatro búsquedas estocásticas distintas, pero es una razón más para no
  tratar ese número como reproducible.
- **Análisis acoplado y desacoplado**: fuera, por falta de respuesta de
  sitio 1-D.
- **Resistencia pseudoestática por etapas**: fuera.
