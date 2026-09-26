# OGR Slip2D v0.1.210

**Las tres fichas del paquete P3 que salieron de cerrar D165/D167 se
resuelven juntas: D112b, D172 y D180 (decisiones de la propietaria,
2026-09-26).** Van en ese orden porque D112b hace que el envoltorio de
desembalse pase lo que dijo el método interior, y así las claves nuevas de
D172 viajan solas.

- **D112b cambia el motor.** El envoltorio de desembalse multietapa pasa los
  `details` enteros de la pasada que dio el factor, `m_alpha_sign` incluido,
  y su veredicto: `converged`, `admissible`, la nota y la razón. Hasta ahora
  re-admitía lo que el método interior había rechazado.
- **D172 cambia el motor.** Los dos chequeos de admisibilidad juzgan cada
  superficie como la resolvió su propio método. El −120 prueba la σ' de la
  PROPIA solución de cada método, y los dos chequeos linealizan la
  envolvente donde lo hizo el solver, soporte incluido. El denominador del
  m-alpha sigue siendo el de Bishop.
- **D180 no cambia el motor: cierre documental.** No hay resistencia a
  tracción por material, y la razón queda escrita donde se lee la
  tolerancia.
- **De las medidas nacen D194–D201**, que se reportan y no se corrigen
  (regla 6). La de más peso es D199: el Ordinario con agua embalsada viola la
  identidad «sumergido = seco».

Lo que cambia en el banco de verificación (`_tools/`, `_auditoria/`, fichas)
no está en git y se describe aquí.

---

## 0. Lo que estaba mal en los encargos

### El criterio de cierre de D172 ya pasaba, y después del arreglo habría fallado

P-D172 pedía «la identidad con `base_normal_force` para Bishop y Janbu a
1e−9, en vivo, sobre un modelo con soporte». Medido en 0.1.209: residuo
**exactamente 0,0**, con un clavo y una curva de potencia. No podía ver el
defecto porque `base_forces_no_interslice_shear`, de donde sale
`base_normal_force` para Bishop y Janbu, deja fuera el soporte por decisión
escrita (`bishop.py`, «support forces do not enter N»), igual que el
chequeo. Tras el arreglo esa identidad falla en cuanto hay soporte. El
criterio se reenuncia: la σ del chequeo tiene que ser la que el solver usó,
reconstruida desde sus primitivas. Lo que queda abierto es D196.

### Un clavo horizontal activo no discrimina nada en Bishop ni en Janbu

Para un soporte activo, `support_vertical_load` vale exactamente `−f_v`, y
un clavo horizontal tiene `f_v = 0`. Todo testigo de Bishop y Janbu con ese
clavo pasa en 0.1.209. Por eso los testigos usan un clavo a −15° y guardan
que las cargas de las dos familias sean grandes en la dovela cruzada. Y
`−f_v` da la identidad cerrada contra la que se comprueba lo que publican
Bishop y Janbu.

### Una sola clave no servía para las dos familias

La propuesta del prompt era una clave con «la carga vertical del soporte por
dovela que usó». Pero las dos familias no suman la misma carga:

- Bishop y Janbu añaden la componente vertical de la parte TANGENCIAL del
  soporte.
- Spencer, GLE y la familia de inclinación prescrita añaden solo la NORMAL
  (`−nf_v`); su parte tangencial es una resistencia en la base, no una carga
  (el reparto de v0.1.115).

En la dovela cruzada medida, 20,43 frente a 33,69 kPa. Por eso cada método
publica su propio número y el −120 lee la N propia de cada método: la forma
de Bishop con `−nf_v` habría quitado a Spencer el término `−t_mob·sin α` de
su normal, y del lado inseguro.

### La pregunta de Fellenius escondía un defecto mayor

La ficha preguntaba si el chequeo debía reproducir la forma del Ordinario o
escribir que aplica la de Bishop a todos. La propietaria pidió investigarlo
en la literatura (sección 2.2). La respuesta afectó a más métodos:

- Con el chequeo de tracción encendido, el círculo de Ej_2 piezométrico daba
  un −120 **falso** en la dovela del pie para el Ordinario, Spencer, GLE y
  Lowe-Karafiath: −0,06, −0,71, −0,73 y −0,61 kPa, frente a +4,48, +33,2,
  +2,47 y +22,7 publicados.
- Todos se juzgaban con la normal de Bishop a su propio factor, un híbrido
  que solo Bishop y Janbu calculan.

### Líneas y nombres desfasados en las fichas y en las herramientas

- P-D172 citaba `interslice.py:668`, que es hoy `:797`.
- `PAQUETES` vive en el `_tools/generar_prompts.py` de la raíz, no en el del
  02.
- `vc.REPO_190` ya no existe; ahora son `REPO_MOTOR` y `TESTS_REPO`.
- Dos comentarios del motor seguían diciendo que los dos Janbu no usan
  `support_vertical_load` o que lo suman crudo. Desde v0.1.142 lo usan dentro
  de su equilibrio vertical, con `sec α` en el lado motor. Corregidos en
  `support_integration.py` y en `ordinary.py`.

### La lista de re-admisiones de la exploración era parcial

Bishop, Janbu y el Ordinario, con un soporte activo mayor que el momento
motor, devuelven `fos=None` y no llegan a re-admitirse. Lo que sí se
re-admitía era Spencer y GLE con el empuje relajado, y cualquier pasada no
convergida que trae factor.

---

## 1. D112b — el envoltorio pasa lo que dijo la pasada que dio el factor (motor)

### El defecto

`MultiStageDrawdownMethod.compute_fos` construía su resultado con un
literal. `kv` se añadió en v0.1.191 (D167) y `m_alpha_sign` no. Con Janbu
dentro, `checks._denominator_sign` volvía a la suma de Bishop: era el caso
de D112 entrando por el envoltorio.

Además, `converged=True` iba escrito a fuego y `admissible` quedaba por
defecto. Una pasada que Spencer o GLE declaraban inadmisible por el empuje
relajado volvía admitida. Una pasada no convergida con factor volvía
convergida. El resultado llegaba a publicar `thrust_admissible: False` junto
a `admissible=True`.

### El arreglo

- Los `details` de la pasada que dio el factor viajan **enteros**
  (`{**inner, <claves del desembalse>, "kv": kv}`). Una lista de claves es
  como se había llegado aquí, clave a clave.
- La constante `"kv"` se queda en el literal, porque `d167` la busca por AST.
- De esa misma pasada se copian `converged`, `error_message`, `reason`,
  `admissible`, `admissibility_note` y `admissibility_reason`.

Cuando **ninguna pasada** dio el factor (el casquete drenado que cicla y se
informa en el centro del ciclo, v0.1.71):

- `DrawdownResult` guarda `invariant_details`. Son `slide_sign`,
  `m_alpha_sign` y `kv`, idénticos en r2 y en cada pasada de etapa 3, porque
  `_undrained_slices` solo cambia material, u y succión (constante
  `PASS_INVARIANT_KEYS`).
- `DrawdownResult` guarda también los dos cuernos del ciclo, en
  `cycle_horns`.
- El centro se admite solo si **los dos cuernos** lo eran.
- No viaja ninguna clave por dovela: en esa rama las dovelas publicadas son
  las del llamante, y eso se reporta como D200.

### La compuerta: medir antes de incluir la admisibilidad

La propietaria pidió incluir la admisibilidad midiendo antes, y parar si se
movía un mínimo publicado. Censo `_tools/censo_desembalse_d112b.py`, A/B en
un solo proceso: el brazo «antes» es el literal de 0.1.209 reconstruido sobre
el mismo `DrawdownResult`, así que el factor es idéntico y solo difiere lo
que el chequeo y la búsqueda leen.

| problema | fila | superficies | rama que cicla | veredictos que cambian | re-admitidas hasta 0.1.209 | mínimo antes = después |
|---|---|---|---|---|---|---|
| 095 | corps_1, círculo publicado | 1 | — | 0 | — | 1,404539 |
| 096 | Bishop, círculo publicado | 1 | — | 0 | — | 1,445254 |
| 096 | búsqueda Janbu | 1380 | 27 | 0 | 0 | 1,263945 |
| 096 | búsqueda Spencer | 1373 | 0 | 0 | 0 | 1,446584 |
| 096 | búsqueda GLE | 1373 | 0 | 0 | 0 | 1,449558 |
| 097 | búsqueda Bishop / Ordinario | 4184 / 4192 | 0 / 1 | 0 | 0 | 0,818404 / 0,627677 |
| 098 | búsqueda Bishop / Ordinario | 1517 / 1520 | 34 / 34 | 0 | 0 | 0,892992 / 0,77765 |

**La compuerta pasa:**

- 0 filas publicadas y 0 mínimos movidos;
- 0 superficies con el signo declarado distinto del de respaldo, sobre
  15 539;
- 0 pasadas que el método interior hubiera rechazado y 0.1.209 re-admitiera.

Todo esto en el 095–098, que es donde el banco usa el desembalse multietapa.
El control positivo, el Janbu de signo contrario sobre la coronación
drenada, sí ve el caso: el veredicto m-alpha cambia.

Dos cosas que el censo enseña y el cierre no esconde:

- **Márgenes mínimos muy pequeños en el 097/098:** 5,7e-5 en la suma de los
  chequeos y 6,0e-5 en la de Janbu. El signo es frágil, pero no discrepa en
  ninguna superficie.
- **Tres signos discrepantes en la rama que cicla del 098:** en 3
  superficies, la suma de Janbu sobre las dovelas del llamante discrepa de la
  de Bishop. No afecta ni a Bishop ni al Ordinario (el signo que se reenvía
  coincide con el de respaldo), pero es el emparejamiento de D200 visto desde
  otro lado.

### Los testigos

El Pilarcitos publicado no discrimina el signo: toda dovela de la pasada
final es no drenada con φ = 0, y ahí `m_alpha = cos α` con cualquier signo.
El fixture le añade una **coronación drenada** (y > 65, φ' = 45°). Sobre sus
bases empinadas los dos signos dan mínimos de 0,85 y 0,23. El signo que
discrepa se sintetiza con un Janbu que declara el contrario del suyo: en el
096 el de respaldo y el de Janbu no discrepan en ninguna de las 1380
superficies válidas.

---

## 2. D172 — cada chequeo juzga la superficie como la resolvió su método (motor)

### 2.1 Los dos portadores

Cada método publica en `details`, por dovela y en orden de dovela, dos
claves.

**`sigma_support_load`**: la carga que sumó a `w_total` para linealizar su
envolvente en la última pasada.

| Método | Valor |
|---|---|
| Bishop, círculo y poligonal | Lista `support_vertical_load` capturada en la pasada |
| Janbu | Lo mismo, a la F sin corregir |
| Spencer, GLE, Corps 1/2 y Lowe-Karafiath | `−nf_v`, del helper nuevo `support_normal_load`, bit a bit lo que restan `prepare_rows` y `modified_swedish` |
| Ordinario | Ninguna: su estimación no lleva soporte |

**`solved_base_normal`**: la N total de la propia solución, que el −120
prueba como `N/l − u`.

| Método | Valor |
|---|---|
| Spencer, GLE y la familia | Su `base_normal_force` |
| Ordinario | `N' + u·l + T_N`, la normal corregida de C-12 más el soporte, sin recortar |
| Bishop y Janbu | No la publican: la forma de respaldo del chequeo ES su normal, con la carga de arriba |

En el chequeo:

- `_base_load_and_sigma(s, *, kv, support_load)` exige `support_load` por
  nombre y sin defecto, como `kv`.
- Los dos lectores nuevos, `_applied_support_load` y `_solved_normals`,
  nunca lanzan. Una clave ausente o mal formada se lee como ausente, porque
  `_is_admissible` admite lo que revienta.
- Sin soporte, todo es bit a bit lo de antes: la identidad de D167 sigue
  dando 0,0.

### 2.2 Qué σ' debe probar el −120: la investigación

La propietaria pidió mirar la documentación y los artículos científicos
antes de decidir. Lo encontrado, con lo leído separado de lo no leído:

- **Leído.** USACE EM 1110-2-1902 (2003), App. C. La Ec. C-12,
  `N' = W cos α − u·Δℓ·cos²α`, es la recomendada. Sobre la Ec. C-13,
  `W cos α − u·Δℓ`: «can lead to unrealistically low or negative stresses
  … and should not be used».
- **Leído.** §C-10.a pide examinar «calculated values of normal forces», es
  decir, las del análisis.
- **Leído.** Krahn (2003, Can. Geotech. J. 40, p. 645): la normal de base
  «is consequently different for the various methods».
- **Leído.** Fredlund & Krahn (1977): misma forma de normal en todos los
  métodos «with the exception of the ordinary method».
- **Documentación de la referencia.** Imprime la σ' por método.
- **No leídos**, y así se dice: Turnbull & Hvorslev (1967), Lambe & Whitman
  (1969), Whitman & Bailey (1967), Duncan, Wright & Brandon (2014),
  Abramson et al. (2002), Chen & Morgenstern (1983) y Ching & Fredlund
  (1983).

**Decisión (propietaria):** el −120 prueba la σ' de la propia solución de
cada método. El m-alpha conserva el denominador de Bishop (D61, D111), y el
Ordinario sigue fuera de él.

### 2.3 La referencia externa (regla 1)

Las columnas publicadas por método del Ej_2 piezométrico:

| Método | σ' propia − publicada | Híbrida − publicada | −120 antes | −120 después |
|---|---|---|---|---|
| Ordinario | 5,3e-4 kPa | 16,77 kPa | sí (falso) | no |
| Spencer | 4,86 | 34,20 | sí (falso) | no |
| GLE | 1,26 | 36,41 | sí (falso) | no |
| Lowe-Karafiath | 4,29 | 36,63 | sí (falso) | no |
| Bishop | 0,19 | 0,19 | sí | **sí**: su columna publicada está en tracción, −0,79 kPa en el pie |

El control de Bishop es lo que dice que el chequeo no se ha vuelto
permisivo. El hueco de 1,3–4,9 kPa de Spencer, GLE y Lowe-Karafiath no tiene
explicación y se reporta como D201.

### 2.4 El censo (`_tools/censo_sigma_propia_d172.py`)

- **Banco.** 194 `.ogr`, 36 con soporte, 5 con envolvente dependiente de σ
  (curva de potencia, b < 1: 040, 041, 044, 045 y 061). **Intersección
  vacía.** Tracción encendida en 0.
- **Sintético.** Clavo a −15°, curva de potencia b = 0,6: el residuo de la
  σ del chequeo contra la del solver pasa de ≥ 0,537 a ≤ 1,7e-16 en los 7
  métodos válidos. Corps 2 no tiene raíz en ese fixture.
- **Suelo de ℓ.** Base mínima de **0,0158 m** sobre 711 superficies
  publicadas y críticas; ninguna por debajo de 1e-9. El suelo (1e-12 en los
  chequeos, 1e-9 en los métodos) se documenta y no se cambia.
- **Superficies archivadas de los modelos con soporte (107).** Δm_alpha
  máximo 1,3e-12 y Δtanφ 1,5e-12 (el ruido de la secante de Mohr-Coulomb),
  contra un margen mínimo al 0,2 de **0,029**: **0 veredictos m-alpha
  cambian**.
- **Alcance, declarado.** No son las poblaciones de búsqueda: el A/B de
  búsquedas enteras de los 36 modelos cuesta 7 h en paralelo.
- **El −120, si alguien lo encendiera** (hoy apagado en los 194): cambiaría
  en 8 de las 107 superficies. En 7 pasa a rechazar (054, 059 dos veces,
  060, 092 tres veces) y en 1 deja de hacerlo (085 activo). Es el chequeo
  viendo el soporte y la N propia de cada método.

### 2.5 La suite

`test_checks_v132.py` usa Spencer para la cuña degenerada que solo debe
marcar las dovelas de más de 70°. Con la N propia de Spencer marca las
mismas, [15, 14], a −218 y −180 kPa (la híbrida daba −269 y −239). No hubo
que tocar el test.

---

## 3. D180 — sin resistencia a tracción por material (cierre documental)

La documentación de la referencia describe el valor por material para un
mecanismo **del solver**: ajustar el factor de seguridad local de la dovela
hasta anular σ' y, en otra página, crear una grieta. No da la fórmula de
ninguno. Además:

- sus páginas del chequeo fijan la tolerancia en cero salvo HB, GHB y la
  función tensión-normal, y no mencionan el valor del usuario;
- sus dos listas de modelos elegibles se contradicen (ocho en una, «todos
  menos cuatro» en otra);
- el ajuste avanzado de tracción para los criterios tensión-normal tampoco
  tiene fórmula.

Un campo solo para el chequeo sería un ajuste cuyo propósito declarado el
análisis no honra (regla 7). Uno en el solver sería una ecuación inventada.
Lo que D60 midió (el recorte N' ≥ 0: +5,01 % en el 015, +22,52 % en el 023)
es otra regla. La decisión está en el docstring de
`checks._material_tensile_strength`, sin nombrar el producto.

---

## 4. Lo que se reporta y NO se corrige (regla 6)

- **D194 (P3).** Una pasada de etapa 3 sin factor tumba la corrida:
  `math.isfinite(None)` en `rapid_drawdown_fos`.
- **D195 (P4).** `AnisotropicStrengthFunction` revienta en todo análisis:
  llama a `_c_phi` con dos argumentos y su `_c_phi` admite uno. Ningún
  material del banco la usa.
- **D196 (P4).** El `base_normal_force` de Bishop y Janbu deja fuera el
  soporte: 12,83 kPa frente a 32,35 de su normal propia en la dovela
  cruzada. Alimenta la etapa 1 del desembalse.
- **D197 (P4).** El `base_normal_force` del Ordinario es la N sin la
  corrección C-12: su `N/l − u` es C-13, con hasta 47,75 kPa de error en
  Ej_2. Corregirla movería el desembalse del Ordinario un +17,7 % en
  Pilarcitos, y el 097/098 lo corren.
- **D198 (P4).** El Ordinario con soporte linealiza sin él, lo suma después,
  y un soporte que levanta puede bajar la resistencia de c·l.
- **D199 (P4).** El Ordinario con agua embalsada suma `Hw·sin α` a N. Su
  factor pasa de 5,33 a 10,60 al subir el agua de 72 a 120, frente a 2,57 de
  Bishop, y viola la identidad cerrada «sumergido = seco». Es lo que imprime
  USACE C-14. Decidirlo exige leer Duncan, Wright & Brandon (2014) cap. 6.
- **D200 (P3).** En la rama del casquete que cicla, los chequeos juzgan las
  dovelas del llamante con un factor de etapa 3.
- **D201 (P2).** La σ' propia de Spencer, GLE y Lowe-Karafiath se separa de
  las columnas publicadas de Ej_2 entre 1,3 y 4,9 kPa, y los márgenes de GLE
  y Lowe-Karafiath son menores que ese hueco.

---

## 5. Los tests

Los tres archivos nuevos se midieron copiándolos a un `git worktree` de
0.1.209 (a6eceda) y ejecutándolos allí. Las cifras son medidas, no
predichas.

| Archivo | Casos | Fallan en 0.1.209 | Por comportamiento o texto | Débiles (clave o parámetro) |
|---|---|---|---|---|
| `test_drawdown_passthrough_v1210.py` | 18 | 8 | 5 | 3 |
| `test_own_base_stress_v1210.py` | 26 | 16 | 11 | 5 |
| `test_tensile_strength_decision_v1210.py` | 6 | 1 (el texto) | 1 | 0 |

Además, la cabecera de `test_sigma_seismic_v1191.py` decía que D172 seguía
abierta, y se ha actualizado.

**Suite entera, sin argumentos: 4629 casos, 4629 pasan, 0 fallan** (262
archivos). Tardó 63 min 35 s, de 19:06 a 20:10. No es una medida del coste:
compartió los cuatro núcleos con el censo de D112b (59 min de búsquedas en
serie) y con la regresión de cierres. Las tres ejecuciones dirigidas del
desarrollo tampoco cuentan como evidencia.

---

## 6. El banco (fuera de git)

- **Censos nuevos, cada uno en su carpeta:**
  - `censo_desembalse_d112b.py` → `_auditoria/D112b_desembalse/`
  - `censo_sigma_propia_d172.py` → `_auditoria/D172_sigma_propia/`

  Las carpetas de D111/D112 y de D165/D167 no se tocan: sus cierres adoptan
  el censo más nuevo que encuentren allí.
- **Cierres nuevos en `verificar_cierres.py`:**
  - `d112b` y `d172` → CUBIERTO POR TEST;
  - `d180` → CIERRE DOCUMENTAL.

  Los tres tienen `CIERRE = 0.1.210` y leen lo histórico con
  `_censo_desde`/`_historico`. Contra un árbol de 0.1.209 dan NO SE
  SOSTIENE, cada uno por comportamiento o por texto.
- El `verificar_cierres.py` de 0.1.209 queda archivado en
  `_auditoria/D172_sigma_propia/` para la comparación clave a clave.
- **Fichas nuevas:** D194–D201, con su prompt largo. El siguiente número
  libre es D202.

---

## 7. Verificación

- **Suite entera, sin argumentos:** 4629 de 4629 (sección 5).
- **Discriminación de los tres tests nuevos**, medida en un worktree de
  0.1.209 y archivada en el banco:
  - D112b: 8 de 18 fallan;
  - D172: 16 de 26 fallan;
  - D180: 1 de 6 falla.
- **`d112b`, `d172` y `d180` contra el árbol de 0.1.209**, en un proceso
  aparte con el worktree delante: NO SE SOSTIENE, por comportamiento o por
  texto. Contra este árbol cierran.
- **Mutación:** con `_SIN_HISTORICO = True` los tres dejan de cerrar.
- **Regresión de cierres, clave a clave:**
  - `verificar_cierres.py` de 0.1.209 contra el nuevo, sobre el mismo motor:
    156 claves comunes con el mismo veredicto y el mismo detalle;
  - contra los veredictos archivados: 0 bajadas y 0 veredictos distintos;
  - solo entran las tres claves nuevas.
- **Banco:**
  - instantánea `Evaluaciones/0.1.210`, antes de retirar y otra vez con
    `--forzar` al final;
  - `retirar_cerrados.py --escribir D172 D180 D112b`, con las secciones
    guardadas en `ERRORES_Y_DISCREPANCIAS_retiradas.md`;
  - `PAQUETES` podado y la cadena de P3 tachada;
  - `generar_prompts.py`: 52 prompts, 43 largos, las 9 FALTA previas y 0 sin
    paquete;
  - `generar_comparativa.py` y `balance_evaluaciones.py` contra
    `Evaluaciones/0.1.209`: 559 → 559 filas, todas IGUAL, 0 sin pareja;
  - `auditoria_invariantes.py`: 0 ERROR en el 02 (487 AVISO y 257 INFO, los
    mismos recuentos que en 0.1.209) y 0 ERROR en la raíz.
- **Citas de los prompts largos:** `comprobar_citas_prompts.py` no encuentra
  ningún problema en las nuevas. El único que da, en D135, es anterior a esta
  tanda.

**Lo que falta por probar, dicho:**

- las poblaciones de búsqueda de los 36 modelos con soporte, para el m-alpha
  de D172; se midieron las superficies archivadas y se publica el margen;
- el −120 encendido sobre el banco entero; está apagado en los 194 modelos;
- que la referencia pruebe la σ' de cada método en su propio chequeo; es una
  inferencia coherente con su documentación y con las columnas que imprime,
  no algo observado, porque ningún informe que tengamos lo lleva encendido.
