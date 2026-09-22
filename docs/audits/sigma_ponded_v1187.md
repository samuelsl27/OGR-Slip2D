# Censo D113 - envolvente dependiente de sigma x agua embalsada (OGR 0.1.187)

Medido por `_tools/censo_sigma_agua_d113.py`, que SOLO MIDE.

## 1 - Mitad A: los `.ogr` vivos, sin evaluar nada

| | |
|---|---|
| archivos `.ogr` recorridos | 194 |
| problemas con envolvente dependiente de sigma | 040, 041, 044, 045, 061 |
| problemas con lamina embalsada | 010, 042, 065, 066, 069, 076, 092 |
| **interseccion** | **vacia** |

## 2 - Mitad B: las superficies publicadas, con el motor

| | |
|---|---|
| B_filas | 226 |
| B_filas_con_dovelas_con_agua | 46 |
| B_filas_con_dovelas_sigma_dependientes | 10 |
| B_FILAS_QUE_CRUZAN | 0 |
| B_FILAS_MOVIDAS | 0 |
| B_VEREDICTOS_QUE_CAMBIAN | 0 |
| B_saltadas | 21 |

Ninguna fila se mueve, y la mitad A dice por que: no hay un solo problema del banco que tenga a la vez una envolvente dependiente de sigma y agua embalsada. Sobre este banco el cambio es un no-op por IDENTIDAD y no por muestreo, porque para `mohr_coulomb`, `undrained`, `undrained_depth_datum` e `infinite_strength` el par `(c, tan phi)` que devuelve `_local_c_phi` no depende de la estimacion.

