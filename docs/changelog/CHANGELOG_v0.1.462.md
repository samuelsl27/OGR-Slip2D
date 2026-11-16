# OGR Slip2D v0.1.462

**Una base que corre sobre un contacto entre dos materiales toma el más débil de los dos (D447).** Hasta 0.1.461
tomaba siempre el de encima: el rebanador pregunta su material 0,01 por encima del punto medio (D48r), y nadie miraba
el otro lado.

En el problema 4 del manual de dovelas no verticales del banco (la escombrera sobre un suelo cizallado de Coulthard
1979 y Hoek 1987), la superficie publicada corre por el suelo cizallado. Sus 25 dovelas del pie leían la escombrera
(c = 100, φ = 42°) y no el suelo (c = 10, φ = 6°):
- Bishop daba 3,768 frente al publicado 1,198;
- con el suelo cizallado da 1,199.

El «3,77 es método» de D122, de la ficha D357 y de la spec 009 era, en seco, el material de la base.

Por decisión de la propietaria (2026-11-15):
- D447 se resuelve antes de seguir con Sarma, en esta versión;
- la regla es «el más débil», con el interruptor `BASE_ON_CONTACT` («above» devuelve 0.1.461 bit a bit);
- las seis versiones de Sarma que quedaban pasan a 0.1.463–0.1.468, y la spec 009 se renumera en este commit.

Tras la revisión (decisiones del 2026-11-16):
- solo cuenta una base que **corre** por el contacto, con la resolución del propio modelo;
- el desembalse rápido sigue leyendo el de encima, hasta una ficha propia;
- si el agua del material de abajo no llega a la base, la superficie se rechaza.

En el banco cambian 8 de las 812 superficies, las 8 publicadas del problema 4. No hay ninguna cadena nueva en la
interfaz, ni ajuste ni acción.

## 0. Lo que se encontró

### El defecto

- **El origen:** al empezar las cuñas de Sarma (0.1.462 de entonces), mirando qué material daría el constructor a la
  base del pie del 4. Medido con `_auditoria/P9_D447/medir_d447.py` del banco, con su log:

  | | escombrera en el pie (0.1.461) | suelo cizallado en el pie | publicado |
  |---|---|---|---|
  | seco | Bishop 3,7680 · Janbu s. 3,5033 · Spencer 4,7223 · GLE 4,4767 | 1,1990 · 1,1931 · 1,2110 · 1,2021 | 1,198 / 1,2 (Hoek 1987) |
  | saturado | 1,4158 · 1,2763 · 1,8921 · 1,6247 | 0,2070 · 0,1887 · 0,2099 · 0,2007 | 0,434 / 0,48 |

  En saturado las dovelas verticales quedan un 52 % por debajo del publicado. Eso es el método: las cuñas de Sarma dan
  0,4347 sobre la misma masa (test_sarma_solver_v1461). La regla nueva no lo arregla ni lo pretende.
- **Lo que dice la referencia:** su ayuda no dice qué material lleva una base justo sobre un contacto. Documenta el
  material del centro de la base (indefinido justo en el contacto) y, en superficies compuestas, el de encima del
  borde exterior.
- **Lo que piden los publicados del banco con una superficie sobre un contacto:**
  - James Bay (Duncan, Wright y Brandon 2014, §7.7.6, fig. 7.29), con el tramo llano sobre el till: la arcilla lacustre
    de encima;
  - el 4, la escombrera sobre suelo cizallado: el de abajo;
  - el 3, la escombrera sobre roca: el de encima, según sus figuras.

  En los tres es el más débil, y ninguna regla de un solo lado los cumple todos.

### El censo y el A/B

- **El censo** (`_auditoria/P9_D447/censo_d447.py` y su log). Recorre 230 modelos y 812 superficies guardadas
  (críticas, optimizadas y publicadas), re-rebanadas con su método y su número de dovelas, en 37 s.
  - 40 superficies tienen alguna base con suelos distintos a ±0,01 de su punto medio.
  - «Debajo» habría movido unas 30, hasta +120 %, y roto James Bay y el 3.
  - La primera versión de «el más débil» (un contacto era eso, dos suelos a ±0,01) movía 9: las 8 publicadas del 4 y
    el 028 ej4 modo B del 02 (−0,82 %).
  - El censo emulaba la regla con la σ′ de la regla vieja. El código la calcula con el agua de cada candidato: el A/B
    es la medida que vale.
- **El A/B en el mismo proceso** (`_auditoria/P9_D447/ab_d447.py`, las 812 con `BASE_ON_CONTACT` en «above» y en
  «weaker», repetido con el código final): 804 dan lo mismo al último bit y cambian las 8 publicadas del 4:
  - seco: Bishop 3,7683 → 1,1988, Spencer 4,7036 → 1,2174, GLE 4,4690 → 1,2040, Janbu corregido 3,8122 → 1,3013;
  - saturado: 1,4155 → 0,2083, 1,8720 → 0,2099, 1,6260 → 0,2031, 1,3886 → 0,2086.

### La revisión adversaria (un agente)

1. **La detección.** «Dos suelos a ±0,01» no es «correr por el contacto».
   - Cogía el fondo de un círculo tangente: el 028 eran 2 de sus 50 bases, a entre 0 y 14 mm del contacto, leyendo la
     capa de abajo.
   - Cogía también una base llana 5 mm por encima.
   - Y el 0,01 absoluto decidía distinto en una copia a 1/50 del mismo modelo (una base a 8 mm del contacto).

   Decisión: la base corre por el contacto si sus extremos y su punto medio están a menos de una celda de la
   resolución del modelo (`_model_grid_tol`, 1e-6 de la diagonal) de un mismo contorno de material. La sonda de abajo
   baja 100 celdas, relativa también. El 028 ya no se mueve.
2. **El desembalse rápido.** Sus dos niveles eligen distinto sobre la misma base:
   - bajo el embalse, σ′ = (γ − γw)·z, y gana el de encima;
   - desembalsado, σ′ = γ·z, y gana el de abajo.

   En el talud de la revisión, el factor de los cuatro procedimientos cambiaba de +14 a +25 % frente a «above».
   Decisión: el desembalse pide al rebanador «el de encima» en sus tres llamadas (etapa 1, etapa 2 y B-bar), y se abre
   ficha para tratarlo bien.
3. **El agua del de abajo que no llega a la base.** La primera versión se quedaba en silencio con el de encima.
   Decisión: la superficie se rechaza, como cuando no llega el agua del material de la propia base (v0.1.96).
4. **15 mutantes vivos.** Ningún test miraba los campos del candidato de abajo:
   - su agua (Ru, el material de su agua de un anisótropo generalizado, el exceso de B-bar por las partes de las
     cargas);
   - su estratificación y sus juntas;
   - su succión y su u bruta;
   - el recorte de σ′ en cero y el agua embalsada en σ′;
   - el empate;
   - la distancia de la sonda.
5. **La cabecera del test mentía.** Decía que en el 4 las dovelas verticales y las dos cuñas de Sarma coinciden a 5e-4.
   En seco: Bishop 1,1988 frente a 1,1983. En saturado: 0,21 frente a 0,43.
6. **El coste lo midió la revisión:** +3 a +7 % del rebanado, con las regiones congeladas.
   - La primera versión preguntaba el material de abajo con otra consulta de regiones, y rebanar un modelo de varias
     capas costaba un 10–29 % más (problemas 3, 15 y 24 del 02).
   - Lo caro no es la sonda sino validar la caché de regiones en cada consulta. Ahora las dos sondas van en una sola
     consulta (`materials_at`), como las bandas de `_column_weight`.

### Al escribir los tests nuevos

- **Un fallo mío de esta versión:**
  - `_weaker_on_contact` llamaba a `surface_angles_at` sin importarlo;
  - un material anisótropo generalizado con juntas por superficie sobre un contacto reventaba el rebanado con
    `NameError`;
  - lo encontró el caso nuevo de las juntas. Ahora se importa en el módulo, junto a `anisotropy_angle_at`.
- **Una guarda muerta:** `below.id != mat.id` no decidía nunca. `materials_at` devuelve los objetos de
  `project.materials` (`material_by_id`), y la identidad basta. Quitada.
- **Un mutante equivalente:** «la detección solo en el punto medio» vive.
  - El rebanador corta cada base donde la superficie toca un contacto: un cruce, un roce, y los dos extremos de un
    tramo compartido (medido con crestas en pico y de techo plano). Así que ninguna base tiene el medio sobre un
    contacto y un extremo fuera.
  - Los extremos se quedan porque la definición no debe apoyarse en ese corte, y el constructor de cuñas de Sarma
    tendrá el corte en contactos como opción.
  - El punto medio sí decide: una base que salva un hundimiento de 5 mm del contacto tiene los extremos sobre él y el
    medio fuera.
- **Un fixture que borraba una capa, de antes de D447, sin tocar:**
  - dos contactos paralelos a 0,3 m, con los extremos fuera del modelo, quedaban en uno;
  - el constructor de regiones suelda un extremo que está a menos del 0,8 % de la diagonal de otro contorno
    (`weld_tol`, «imprecisión del ratón»), y la capa fina desaparecía en silencio;
  - con los extremos sobre el contorno exterior no pasa. Es D449, abierta por decisión de la propietaria
    (2026-11-16), sin versión.
- **Un camino equivocado del test:** una superficie que corre justo sobre una capa débil no toma la junta («no se
  adquiere la resistencia de una junta por rozarla», `band_at`). El caso de la capa débil hace pasar la superficie por
  debajo, como v1121, y la junta es más fuerte que los dos lados, para que gane por la regla y no por ser la más débil.

## 1. El cambio

En `ogr_slip2d/slicer.py`:
- **`BASE_ON_CONTACT`,** con «weaker» por defecto y «above», leído en tiempo de llamada.
  - `slice_surface(base_on_contact=...)` lo sustituye en una llamada.
  - Un valor que no es ninguno de los dos es `ValueError`.
- **`_base_material`** gana un argumento opcional `contact`.
  - Si la sonda de encima contesta, se pregunta también `_BELOW_IN_GRID` celdas por debajo, en la misma consulta
    (`_lift_and_below`). Si es otro suelo, se apunta.
  - Lo que devuelve no cambia.
  - Con «above», o con un solo material, no pregunta nada más que antes.
- **`_runs_along_contact`:** los dos extremos y el medio de la base a menos de una celda de un mismo contorno
  `MATERIAL`.
- **`_weaker_on_contact`,** ya construida la dovela, si corre por el contacto y no hay capa débil:
  - construye el candidato de abajo con su agua (`water_material`, `_base_pore_pressure`: la política de no saturado,
    la succión y el exceso de las cargas por sus partes), su estratificación, sus juntas y el techo de su capa, que es
    el contacto;
  - se queda el de menor `_contact_strength`: τ = c + σ′ tan φ a la σ′ estática de Fellenius de la base, la misma para
    todo método (Fellenius 1936), por `local_c_phi` y con el contexto de la dovela;
  - σ′ = max(0, (W + agua embalsada) cos α − u·l)/l;
  - un empate se queda el de encima;
  - si el agua del de abajo no llega a la base, None, y la superficie se rechaza.
- **Las compuestas,** que corren por el borde exterior, no tienen suelo debajo y no cambian. La capa débil sigue
  ganando.

En `ogr_slip2d/rapid_drawdown.py`, las tres llamadas a `slice_surface` (etapa 1, etapa 2 y la de B-bar) piden
`base_on_contact="above"`.

## 2. El test

`tests/test_base_on_contact_v1462.py` (30 casos, 0,5 s), contra referencias de fuera del código:
1. **el 4 publicado** (Coulthard 1979; Hoek 1987), montado desde su geometría publicada:
   - el pie lee el suelo cizallado, en seco y saturado;
   - Bishop da el 1,198 publicado a ±1 % en seco;
   - con «above» lee la escombrera y da 3,77: el interruptor mueve el número;
   - el reflejo da el mismo factor;
2. **James Bay** (Duncan, Wright y Brandon 2014): el tramo llano sobre el till (su = 300, finito) lee la arcilla
   lacustre, con las dos reglas;
3. **el más débil, a mano**, con σ′ escrita en el test:
   - con el contacto profundo, la capa de abajo; somero, la de arriba (las envolventes se cruzan a 211 kPa);
   - cada lado con su agua;
   - el agua embalsada en σ′: 224 kPa con ella y 126 sin ella, a los dos lados del cruce;
   - σ′ recortada en cero bajo una carga artesiana (c = 100 > 74; sin recorte, 72);
   - una base de 35°: con el coseno, 201 kPa; sin él, 246;
   - el empate, el de encima;
   - la regla vieja, por el interruptor y por la llamada;
4. **solo la base que corre por él:**
   - dentro de la resolución del modelo, está sobre él;
   - a 5 mm, aunque sea sobre un nivel freático dibujado allí, no;
   - sobre un hundimiento de 5 mm del contacto, no, y sus vecinas sí;
   - el fondo de un círculo tangente, no, campo a campo y bit a bit;
5. **la resolución es la del modelo:** una capa de 0,3 m bajo el contacto, a escala 1, 1/50 (6 mm) y 1000×. Lee la capa
   en las tres escalas, y Bishop da el mismo factor a 6e-14 (2,6934; con «above», 2,7992);
6. **el candidato es su material:**
   - su Ru (u = Ru·γ·z, Bishop y Morgenstern 1960);
   - el agua del hijo de un anisótropo generalizado, por el peso del padre (D230);
   - su succión (Fredlund, Morgenstern y Widger 1978), con un campo lineal que hace de filtración;
   - su exceso por una carga lineal sobre un corte (Δu = B̄·Δσv, Skempton 1954; la carga, una vez, D427);
   - su estratificación y sus juntas por superficie;
   - y si su agua no llega a la base, el rechazo;
7. **la capa débil gana;**
8. **el desembalse:**
   - en el talud de la revisión, sus dos niveles eligen distinto;
   - sus cuatro procedimientos dan el mismo factor al último bit con las dos reglas;
9. **fuera de un contacto, todo igual al último bit** con las dos reglas, y una regla que no existe es un error.

`tests/test_material_domain_v1143.py` cambia una aserción, con su razón. Fijaba «el de encima» como la regla, una
instantánea del código y no una referencia: ahora la exige bajo «above», y bajo la regla nueva, la capa de abajo (159
frente a 178 kPa).

**Mutantes** (`_auditoria/P9_D447/mutants_d447.py` del banco, con su log): 40, y mueren 39.
- El que vive es el equivalente de la detección (ver §0).
- Los 15 de la revisión mueren.
- Mueren también los de la detección, la sonda, el interruptor, la validación, el rechazo, la capa débil y las tres
  llamadas del desembalse.
- El arnés gana la guarda de `__main__`.
- Restauraba el mutante en vez del original, porque compilaba en el módulo antes de guardarlo. Corregido.

## 3. Lo que no cambia

- Toda superficie sin una base que corra por un contacto, bit a bit (el A/B del banco).
- El desembalse rápido, bit a bit con las dos reglas.
- `test_slide_validation_*` y `test_james_bay_v1158`.
- Las superficies compuestas sobre el borde exterior.
- El 0,01 absoluto de la sonda de encima (deuda de D48r y D64) se queda como está.

## 4. Verificación

- **La suite entera,** `python tests/_runner.py --jobs 4`: 7853 casos, 7852 en verde, 1 saltado (el de siempre) y 0
  fallos, sin fugas ni tramos muertos. La última serie en verde es de hace 40 commits, y no toca hasta 100.
- **Las áreas tocadas,** antes: `base_on_contact`, `material_domain`, `james_bay`, `slice_cuts`, `drawdown`,
  `weak_layer`, `generalized`, `core_messages` y `sarma`, 524 casos en verde.
- **El A/B del banco** con el código final: 812 superficies, 8 distintas, las del 4.
- **Los mutantes:** 40, mueren 39, y vive el equivalente.
- **Los README:** 7852 en verde.
- **Sin probar:**
  - la interfaz: no cambia ninguna cadena ni ningún diálogo;
  - un modelo del usuario con un desembalse sobre un contacto, salvo el talud del test (D448);
  - la CI de Linux, que no se mira tras cada commit (D370).

## 5. Banco

Tras el commit, fuera de git:
- **El 004 re-corrido** (`modelo.ogr` y `modelo_agua.ogr`), y la comparativa del 03 regenerada.
- **D122 re-anclada:** en seco las dovelas verticales dan el publicado, y deja de ser «de método»; en saturado sigue
  siendo de método (0,21 frente a 0,434; las cuñas, 0,4347).
- **Las frases del 3,77** de la ficha D357 y del prompt largo P-D357, corregidas.
- **Las versiones de Sarma** renumeradas en ERRORES, en el prompt largo y en la memoria: 0.1.463–0.1.468.
- **D447 cerrada,** con `d447()` en el VC de la raíz.
- **D448 abierta,** la regla del desembalse sobre un contacto, en P9 y sin versión.
- **D449 abierta,** el soldado de extremos que borra una capa fina, sin versión.
- **Los VC** de la raíz y del 02.
- **El cierre:** instantánea, retirar, PAQUETES, prompts, auditoría y `--forzar`.
