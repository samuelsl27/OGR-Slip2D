<!-- SPDX-License-Identifier: AGPL-3.0-or-later -->
# Los dos techos de angulo de base bajo phi = 0 — v0.1.190

Medida de D114 (la amplificacion de la rama no circular) y estado de
D61 (el 75). La escribe `_tools/censo_techos_d114_d61.py`, que SOLO
MIDE. Arbol medido: `c:\Samuel\OpenGeoRock_Slip2d\OGR-Slip2D`.

## Lo que no se cancela

| familia | alpha cohesiva max | m_alpha min | share de esa dovela | F | F sin ella | delta |
|---|---|---|---|---|---|---|
| F1_james_bay | 43.7 deg | 0.7230 | -0.036595152 | 1.127936 | 1.088066423 | -3.534716 |
| F2_beta_40 | 40.0 deg | 0.7660 | 0.075250306 | 0.579661 | 0.627011962 | 8.168819 |
| F2_beta_45 | 45.0 deg | 0.7071 | 0.028000578 | 0.493247 | 0.507681836 | 2.926507 |
| F2_beta_50 | 50.0 deg | 0.6428 | 0.026759314 | 0.459215 | 0.472062168 | 2.797748 |
| F2_beta_55 | 55.0 deg | 0.5736 | -0.011404492 | 0.459577 | 0.454559342 | -1.091852 |
| F2_beta_60 | 60.0 deg | 0.5000 | -0.019301724 | 0.486507 | 0.477623076 | -1.826041 |
| F2_beta_65 | 65.0 deg | 0.4226 | 0.307185745 | 0.541727 | 0.782735684 | 44.488927 |
| F2_beta_70 | 70.0 deg | 0.3420 | 0.057789828 | 0.624625 | 0.663578398 | 6.23622 |
| F2_beta_72 | 72.0 deg | 0.3090 | -0.064328453 | 0.671281 | 0.630835113 | -6.025238 |
| F2_beta_74 | 74.0 deg | 0.2756 | -0.080283848 | 0.727205 | 0.673255443 | -7.418709 |
| F2_beta_75 | 75.0 deg | 0.2588 | -0.072095767 | 0.763799 | 0.712378898 | -6.732108 |
| F2_beta_76 | 76.0 deg | 0.2419 | -0.083890689 | 0.801688 | 0.739808542 | -7.718614 |
| F2_beta_77 | 77.0 deg | 0.2250 | 0.316066195 | 0.003667 | 0.004257038 | 16.09735 |
| F2_beta_78 | 78.0 deg | 0.2079 | 0.264202401 | 0.002303 | 0.002281896 | -0.926291 |

## El control circular, con su margen

| familia | dovelas | terms.normal | residuo relativo |
|---|---|---|---|
| F3_circulo_55_20 | 20 | -9.732e-11 | 1.991e-16 |
| F3_circulo_55_40 | 40 | -3.454e-10 | 2.918e-16 |
| F3_circulo_68_20 | 20 | 9.777e-11 | 1.406e-16 |
| F3_circulo_68_40 | 40 | -3.706e-10 | 2.607e-16 |

## El 75 (D61), leido de su archivo

`version_ogr` del archivo: **0.1.190**; motor de hoy: **0.1.190**.

| metodo | fos | validas | inadmisibles | min m_alpha de la critica |
|---|---|---|---|---|
| bishop_simplified | 1.412451 | 4036 | 0 | 0.749731348 |
| gle_morgenstern_price | 1.600922 | 3449 | 0 | 0.857422153 |
| spencer | 1.571399 | 3586 | 0 | 0.834702165 |

