# OGR Slip2D v0.1.484

**D203: una etapa 2 del desembalse multietapa que no converge solo siembra el casquete drenado.**
Ya no entra en la comparación `fos_stage3 < fos_stage2` ni se publica como factor de la etapa 2.
En el banco no mueve ningún mínimo ni ningún recuento de superficies válidas: lo que cambia es lo
que el resultado dice de la etapa 2.

## 0. Lo que se encontró

Ficha D203, abierta el 2026-09-27 al cerrar D202 (0.1.212), en el paquete P3. Se midió con una
sonda nueva del banco, `02_.../_tools/sonda_d203.py` (fuera de git), sobre 0.1.483. Resultados en
`_auditoria/D203_etapa2/sonda_0.1.483.json`.

- **El prompt estaba desfasado en lo accesorio y vigente en lo esencial.** Las líneas citadas se
  habían movido. La ruta del banco era la de un PC anterior. El mínimo de Lowe-Karafiath del 096 ya
  no es 1,449929 sino 1,450217. Pero el defecto seguía: `rapid_drawdown_fos` solo rechazaba una
  etapa 2 sin factor, no una no convergida.
- **(a) Se reproduce.** En el círculo crítico del 096, (207,25; 183,333333; 110,79583), con
  50 dovelas y el procedimiento de Duncan, Wright y Wong:
  - Corps 1, Corps 2 y Lowe-Karafiath devuelven en la etapa 2 **F2 = 5,0** (`no_force_bracket`,
    el techo de su rejilla de F), y 16 pasadas del casquete convergen a 1,4627, 1,462929 y
    1,450217.
  - Bishop, Spencer y GLE convergen en la etapa 2 a F2 ≈ 5,44.
- **(b) El punto fijo del casquete no depende de la semilla.** En ese círculo, para los tres, se
  sembró el casquete con cinco juegos de normales:
  - las de la etapa 2 no convergida (lo de hoy);
  - las de la etapa 2 convergida de Bishop;
  - las de su propia etapa 2 resuelta con la rejilla de F extendida hasta 20;
  - las propias multiplicadas por 0,8;
  - las propias multiplicadas por 1,2.

  F3 varía como mucho 9·10⁻⁶ (por debajo de `CAP_TOL` = 10⁻⁴), siempre en 16 pasadas.
- **(c) La raíz de la etapa 2 existe, y está por encima de 5,0.** Con la rejilla extendida
  (5; 6; 7,5; 10; 15; 20), **1061 de las 1149** etapas 2 `no_force_bracket` de Corps 1, Corps 2 y
  Lowe-Karafiath convergen. En el círculo crítico, a 6,40, 6,41 y 6,19. Por eso la comparación que
  se quita no podía salir al revés: un casquete que converge dentro de la rejilla queda por debajo
  de una raíz que está por encima de ella.
- **(d) Lo que haría cada opción, en las 16 búsquedas del 095–098.** Con el código de hoy hay
  **1193** etapas 2 no convergidas con factor (en 0.1.212 eran 1190):
  - **530** superficies acaban válidas porque gana el casquete;
  - **663** acaban inválidas porque la reserva «ganó» la comparación;
  - en **ninguna** el casquete deja de morder.

  | Mínimo | Hoy | Op. 1 (invalidar) | Op. 2 (solo semilla) | Rejilla extendida |
  |---|---|---|---|---|
  | 095 Corps 1 | 1,425939 | 1,425939 | 1,425939 | 1,425939 |
  | 096 Corps 1 | 1,4627 | **1,539782** | 1,4627 | **1,388062** |
  | 096 Corps 2 | 1,462929 | **1,539782** | 1,462929 | **1,388062** |
  | 096 Lowe-Karafiath | 1,450217 | **1,501687** | 1,450217 | **1,43794** |
  | los otros 12 | — | iguales | iguales | iguales |

  - La opción 2 no mueve ni un mínimo ni un recuento de válidas. Las 663 ya eran inválidas y lo
    siguen siendo, ahora por el veredicto de su propia pasada del casquete, que tampoco encuentra
    raíz por debajo de 5,0.
  - La opción 1 sube tres mínimos del 096, de un 3,5 a un 5,3 %, para factores que el casquete sí
    resuelve.
  - Ninguna fila publicada se mueve con ninguna opción. El 096 publica solo Bishop (1,443), y el
    Corps 1 del 095 no cambia.
- **De paso, lo que mueve la rejilla extendida no es de D203.** Con la rejilla extendida, 1581
  superficies más pasan a válidas en esas cuatro búsquedas. Los mínimos de Corps y Lowe-Karafiath
  del 096 bajan a otro círculo, (69; 124,67; 98,75). También se resuelven 964 de las 1127 etapas 1
  `no_force_bracket` que hoy invalida D202. Es
  un cambio de la familia de inclinación prescrita entera, fuera del desembalse. Va a una ficha
  propia (§5).
- **Una trampa que se vio al escribir el test.** El primer paso del casquete se mide contra el
  factor de la pasada que lo siembra. Con un factor de reserva inventado, 1,0 con las normales de
  F = 5,0, el detector de inversiones partió la relajación a la mitad en la segunda pasada. El
  casquete no convergió en 20 pasadas: centro del ciclo 1,509, contra 1,5003 sin marcar. Ningún
  solver devuelve ese par, porque la reserva de la familia trae el estado de su propio F. Por eso no
  se toca, y el test comprueba la regla y no el número de ese caso.

## 1. Decisión de la propietaria (2026-11-23)

De las tres opciones de la ficha: **la etapa 2 no convergida solo siembra el casquete** (op. 2). Se
descartaron invalidar la superficie (op. 1) y aceptarla con una nota (op. 3).

## 2. Lo que cambia

`ogr_slip2d/rapid_drawdown.py`:

- **Si la pasada de la etapa 2 vuelve con factor y `converged=False`:**
  - `DrawdownResult.fos_stage2` es `None`;
  - `stage2_converged` es `False`;
  - el número en que se paró va en `stage2_unconverged_fos` (campos nuevos);
  - no hay comparación: la respuesta es la del casquete, `fos = fos_stage3`, con el veredicto de la
    pasada que la produjo (D112b);
  - si el casquete no muerde, esa pasada es la propia etapa 2, y la superficie sigue inválida.
- **Sin casquete** (procedimiento de Lowe-Karafiath), la respuesta sigue siendo la etapa 2 no
  convergida, inválida con su razón, como antes.
- **`MultiStageDrawdownMethod`** publica `stage2_converged` y `stage2_unconverged_fos` en `details`,
  en todas las ramas, como `stage1_admissible` (D202).
- **Una etapa 2 convergida** sigue exactamente igual.
- **Docstrings:** el de `rapid_drawdown_fos` cambia el párrafo de «D203, abierto» por la regla y sus
  medidas. El de `DrawdownStageUnconverged` cambia su frase de «D203, abierto» por la regla.
- **Versión** en los siete sitios.

## 3. Tests

`tests/test_drawdown_stage2_v1484.py`, 12 casos en ~1 s. El testigo es natural: el círculo crítico
del 096 sobre la sección del Apéndice G de la EM 1110-2-1902 (la del `test_drawdown_usace_v169`).
Allí la familia no encuentra raíz en la etapa 2 y el casquete converge en 16 pasadas. Los números no
son los del banco de §0, porque el fixture no es el `modelo.ogr` del 096:
- el casquete da 1,5003, 1,5005 y 1,4893, frente a 1,4627, 1,462929 y 1,450217;
- Bishop da F2 = 5,54, frente a 5,44.

La forma es la misma: F2 = 5,0 sin horquilla, y el casquete convergido.

- **Cuatro guardas** del testigo:
  - la etapa 2 da F2 = 5,0 sin convergir;
  - Bishop sí converge por encima;
  - el casquete converge;
  - sembrado con las normales × 0,8 y × 1,2, aterriza a menos de `CAP_TOL`.
- **Cinco casos de la regla:**
  - `fos_stage2` es `None`, con la reserva aparte;
  - la respuesta es la del casquete;
  - el envoltorio publica los tres campos;
  - una búsqueda la cuenta válida;
  - una reserva sintética de 1,0, por debajo del punto fijo, ya no gana.
- **El caso sin casquete**, Lowe-Karafiath.
- **Dos controles:** una etapa 2 convergida conserva su factor y la comparación (Bishop en el
  testigo, y Pilarcitos, Duncan, Wright y Wong 1990).

**Discriminación, medida:** el archivo, copiado a un `git worktree` de cc6c2c0 (0.1.483), da
**4 fallos y 8 pasan**. Los dos casos de la regla que pasan allí lo hacen porque la decisión no
mueve números naturales. Un mutante que conserva la comparación contra la reserva hace fallar solo
el caso de la reserva sintética.

`tests/test_drawdown_passthrough_v1210.py`: su guarda «ninguna clave por dovela viaja con el centro
de un ciclo» admite las dos claves nuevas del envoltorio, igual que admitía `stage1_admissible`.

## 4. En el banco (fuera de git)

- `02_.../_tools/sonda_d203.py`, nueva: las medidas (a)–(d) de §0.
- `02_.../_tools/censo_p3_desembalse.py`: su guarda exigía que también `ogr_core` saliera del árbol
  medido. Desde la spec 010 es una dependencia del `.venv`, y en un worktree abortaba. Ahora la
  exige solo a `ogr_slip2d`.

- **Censo P3 del 095–098, antes y después.** Un worktree de 0.1.483 y el árbol de 0.1.484, los dos
  con `--salida D203_etapa2 --con-095`, y el segundo con `--comparar 0.1.483`:
  - **ninguna fila publicada cambia** (`B_FILAS_QUE_CAMBIAN`, vacío);
  - **ningún mínimo cambia** (`C_MINIMOS_QUE_CAMBIAN`, vacío);
  - **todas las búsquedas tienen pareja** (`sin_pareja`, vacío);
  - siguen 1193 etapas 2 no convergidas con factor, y 530 superficies válidas.

  El censo aún cuenta 663 en que «gana la etapa 2». Las reconoce porque la superficie es inválida
  con el factor de la etapa 2 (5,0). Hoy ese factor es el de la pasada del casquete, que también se
  queda en 5,0, no una comparación ganada.
- **`d203()` en el `verificar_cierres.py` del 02.** Comprueba cinco cosas:
  - en vivo, el testigo sobre el Apéndice G con los tres métodos, y el caso sin casquete;
  - que el código lea `r2.converged` y que el docstring tenga la decisión;
  - la sonda: la dispersión por la semilla y que la opción 2 no mueva ningún mínimo;
  - los dos censos;
  - la discriminación archivada (4 de 12 fallan en 0.1.483).

  Sale **CUBIERTO POR TEST**. Con 0.1.483 importado da **NO SE SOSTIENE** por comportamiento
  (`fos_stage2` = 5,0 y sin las claves nuevas).
- **Ciclo de cierre:** instantánea `Evaluaciones/0.1.484`, D203 retirada al índice de CERRADOS,
  tachada en la cadena de P3 y podada de `PAQUETES`, prompts regenerados y `auditoria_invariantes.py`
  con 0 ERROR. El único aviso nuevo es la falta de prompt largo de D464. Después, la instantánea con
  `--forzar`.

## 5. Abierto

**D464**, nueva, en P3, detrás de D374 y sin versión. La rejilla de F de Corps 1, Corps 2 y
Lowe-Karafiath termina en 5,0 sin extensión perezosa (la de λ sí la tiene). Con la extensión, los
tres mínimos del 096 bajarían a 1,388062, 1,388062 y 1,43794, y se resolverían 964 de las 1127
etapas 1 que D202 invalida. Va en ficha propia porque mueve toda la familia, también fuera del
desembalse, y puede dejar sin testigo a D202.
