# OGR Slip2D v0.1.141

**D38 estaba mal atribuido, y el ancla para demostrarlo llevaba treinta y cinco
versiones a un paso de distancia.** Esta versión **no toca producción**: cero
líneas de motor. Trae el test que faltaba —la normal en la base de Spencer,
atada a una columna publicada— y la medición que descarta el componente que el
defecto llevaba dieciocho versiones señalando.

---

## 1. El hueco: la identidad I3 pinzaba el factor y no la normal

`tests/test_gle_interslice_v1106.py` sujeta el sistema interdovela con cuatro
identidades analíticas, y la tercera es la más fuerte: la rama de fuerzas de
Spencer a λ **es** la recursión de inclinación prescrita de USACE
EM 1110-2-1902 ec. C-19 a θ = atan λ. Y esa recursión reproduce, dovela a
dovela, la **columna de normales en la base** de la figura G-7b del propio
manual (`tests/test_modified_swedish_v198.py:294`).

La cadena llegaba hasta un eslabón del final: **I3 sólo afirma sobre
`force.fos`**. Las normales por dovela no se comparaban nunca. Y las dos ramas
no calculan N con la misma expresión —

    interslice.solve_branch   N = [W + X_R − X_L − (c'l − u·l·tanφ')·senα/F] / m_α
    modified_swedish          N = (W + dZ_v + k0·senα) / (cosα − a·senα)

que difieren en **tres signos**, inocuos sólo porque la segunda marcha en un
marco espejado. Nada lo decía en números.

`tests/test_spencer_base_normal_v1141.py` lo dice. **I5**: la normal por dovela
de Spencer a λ es la de la marcha a θ = atan λ, en seco, con presión
intersticial, con sismo y sobre una base de −32° a +62°. Peor caso medido:
**|dN|/N_max ≤ 1e-9**, que es la tolerancia del punto fijo, no una diferencia.
Con eso, la normal de Spencer queda atada a un cálculo hecho a mano en un
documento público.

Y lleva su caso de regla 7, porque todo lo anterior también lo cumpliría un
solver cuya N ignorase el cortante entre dovelas: λ **mueve** el pico de la
normal un −5,16 % en el círculo de I3 y un −9,15 % en el inclinado.

## 2. Lo que la medición dice de D38: no es la aritmética de la normal

El defecto señalaba `spencer._base_forces` alimentado por `interslice.py`. Tres
medidas, en orden de dureza:

**(a) El puente pasa.** La normal de Spencer es la columna validada. El
componente señalado calcula bien.

**(b) El valor publicado no es alcanzable a NINGÚN λ.** Barriendo λ de 0 a 3
sobre el círculo publicado de la figura 61.2, σ′max recorre **35,66 → 34,66** y
nunca baja más; el manual publica **31,21**. Lo más cerca que llega es un
+11,1 %. En Mohr-Coulomb, **30,42 → 29,62** contra **26,44**: +12,0 %. No es un
error de la raíz de λ ni de la hipótesis interdovela — **la curva entera pasa
por encima**.

**(c) El factor tampoco.** Sobre ese mismo círculo `F_f` va de 1,32912 a
1,44215 y `F_m` se mueve entre 1,4158 y 1,4259. El publicado es **1,468**, por
encima de las dos ramas a cualquier λ. Es decir: **sobre el círculo publicado
OGR no reproduce ni el factor ni la tensión**, y eso saca el desacuerdo del
método y lo pone en el problema.

La comprobación 2 del encargo descartaba el factor porque «la tensión se desvía
tres veces más y en sentido contrario». Eso no es un argumento: un sistema de
fuerzas distinto mueve F y N en la proporción que dicte el álgebra.

## 3. El criterio de cierre del encargo no comparaba la misma superficie

Pedía llevar el cociente σ′max(Janbu)/σ′max(Spencer) del 61 al 3 % de 1,164.
**Los dos paneles publicados del problema 61 dicen `Method: spencer`**
(`_auditoria/paneles/061.json`, verificado contra la tabla del PDF, que empareja
método, factor y tensión en la misma línea). Así que el 36,33 de Janbu está
medido sobre el círculo crítico **de Janbu**, que el manual no publica:

| | potencia | Mohr-Coulomb |
|---|---|---|
| publicado, cada método sobre SU círculo | 1,164 | 1,137 |
| OGR, los dos sobre el círculo publicado | **1,0243** | **1,0226** |

El primero mezcla cambio de método **y** cambio de superficie; el segundo es
sólo cambio de método. **No son la misma magnitud**, y llevar el segundo al
primero exigiría compensar un error con otro. El criterio queda anulado por
escrito.

## 4. Y «Spencer sobrestima σ′» es falso: lo refuta el problema 45

El encargo afirmaba que el 45 no publica sus círculos. Publica **tres**, y el de
la figura 45.4 es de **Spencer**. Sobre él:

| | OGR 0.1.141 | publicado | Δ |
|---|---|---|---|
| FoS | 2,695564 | 2,696 | **−0,016 %** |
| σ′max | 82,2604 | 82,25 | **+0,013 %** |

Spencer clava la tensión a la cuarta cifra sobre un círculo publicado. Un solo
caso no cierra nada, pero **un solo contraejemplo sí refuta un «siempre»**.

## 5. Y el sobrepasamiento aparece SIN cortante entre dovelas

Los tres paneles del problema 44 son de **Janbu simplificado**, que no tiene
cortante entre dovelas en absoluto:

| figura | material | Δ FoS | Δ σ′max |
|---|---|---|---|
| 44.2 | curva de potencia | −0,98 % | **+8,57 %** |
| 44.3 | Mohr-Coulomb | −18,66 % | +0,91 % |
| 44.4 | M-C iterado | −0,61 % | **+8,49 %** |

Perseguido hasta el fondo, y **descartando cuatro causas con medida**:

1. **No es la fórmula de reporte.** Reconstruyendo σ′ desde
   `base_forces_no_interslice_shear` sale el mismo número, dígito a dígito.
2. **No es el factor.** Al F **publicado** σ′ pasa de 16,7193 a 16,7871
   (+0,4 %) y de 10,4366 a 10,4647 (+0,3 %). El factor explica un vigésimo del
   hueco, no el hueco.
3. **No es el mallado.** De 15 a 120 dovelas: 16,6481 → 16,7333.
4. **No es la geometría.** La dovela del pico se comprueba a mano: α = 38,03°,
   h = 1,407 calculado contra 1,406 que reporta OGR. Y el equilibrio vertical
   global cierra a **4,6e-14** (44.3) y **6,9e-16** (44.4).

Queda un +8,5 % medido, robusto y sin causa. **Lo que sí queda descartado es
que sea de Spencer**, porque aquí no hay Spencer.

## 6. Un defecto nuevo por el camino: la fila Mohr-Coulomb del 44 es imposible

La Tabla 44.1 publica **dos** suelos: #1 (c′ = 0,0, φ′ = 38,0) y #2 (c′ = 5,3,
φ′ = 23,0), los dos con γ = 19,5. El banco modela la fila Mohr-Coulomb con el
Suelo #1. Sobre el círculo publicado da F = 1,1949 contra 1,469 (−18,66 %); con
el Suelo #2 da 0,9674 (−34,15 %). **Ninguno de los dos reproduce el publicado.**

Y con el Suelo #1 el valor publicado no es que no salga: **no puede salir**. El
talud es de 43,02°, así que con c′ = 0 la cota superior del deslizamiento
plano infinito es

    tan 38,02° / tan 43,02° = 0,8373

y el manual publica **1,469** como factor **crítico**. Un crítico no puede estar
por encima de esa cota. La fila no cierra con ninguna lectura de la Tabla 44.1,
y conviene notar que **es justo la fila cuya σ′ coincide (+0,91 %)**: con el
factor a −18,66 %, esa coincidencia es más probablemente casualidad que acuerdo.

## 7. Los dos rechazos «silenciosos» del 45 eran el mismo, y está documentado

La ficha daba por inexplicado que la figura 45.3 no devolviera resultado. Tiene
la misma causa que la 45.2, que sí estaba escrita:

| figura | punto más bajo del arco | |
|---|---|---|
| 45.2 | 51,981 − 52,433 = **−0,452** | por debajo del modelo (y = 0) |
| 45.3 | 43,505 − 44,283 = **−0,778** | por debajo del modelo (y = 0) |
| 45.4 | 62,668 − 62,477 = **+0,191** | dentro — y es la única que evalúa |

Es la guarda que cerró D48 en 0.1.126. No es un fallo de OGR: **es que a los
modelos del 45 les falta fondo**, y por eso el banco pierde dos de sus tres
medidas de σ′ con Janbu sobre círculo publicado. Regenerar esos modelos con
fondo suficiente es trabajo aparte y se reporta antes de tocarlos.

---

## Lo que esta versión NO resuelve, dicho claro

El **+8,5 % del 44 y el +11,5/12,5 % del 61 siguen sin causa.** Lo que ha
cambiado es lo que se sabe de ellos:

- no son de Spencer (el 44 no lo usa);
- no son de la normal en la base (I5);
- no son de la hipótesis interdovela (el barrido de λ);
- no son del mallado, del factor, de la fórmula de reporte ni de la geometría;
- **no son sistemáticos**: el 45 sale exacto.

La única regularidad que queda en pie, y se deja anotada porque es la próxima
pista, es que **los dos taludes empinados de 6 m (44 a 43,02° y 61 a 45°) se
desvían y el tendido de 12 m (45, a 14,04°) no**.

## Verificado

- `tests/test_spencer_base_normal_v1141.py` — 6 de 6.
- Suite entera sin filtro.
- Producción sin tocar: el único archivo nuevo es el test, así que las cuatro
  identidades de D10 y la comparativa del banco no pueden moverse.
