# Censo de la tolerancia a traccion (D165) y del sismo vertical de los chequeos (D167)

Generado por `_tools/censo_traccion_kv_d165_d167.py` (banco de verificacion) con OGR 0.1.191. SOLO MIDE.

## Resumen

| clave | valor |
|---|---|
| `version` | 0.1.191 |
| `arbol_medido` | c:\Samuel\OpenGeoRock_Slip2d\OGR-Slip2D |
| `modulo_medido` | C:\Samuel\OpenGeoRock_Slip2d\OGR-Slip2D\ogr_slip2d\__init__.py |
| `A_archivos_ogr` | 194 |
| `A_materiales` | 400 |
| `A_por_modelo` | {'infinite_strength': 1, 'mohr_coulomb': 362, 'power_curve': 5, 'undrained': 19, 'undrained_depth_datum': 13} |
| `A_CON_TOLERANCIA_NO_NULA` | 0 |
| `A_con_tolerancia_no_nula` | [] |
| `A_traccion_encendida_en_el_json` | 0 |
| `A_traccion_encendida_tras_cargar` | 0 |
| `A_CONTROL_HB_SINTETICO` | {'hoek_brown': 68.82352941176471, 'hoek_brown_classic': 80.0} |
| `A_forma_cerrada_del_control` | {'hoek_brown': 68.82352941176471, 'hoek_brown_classic': 80.0} |
| `A_CONTROL_VE_EL_CASO` | True |
| `A_saltadas` | 0 |
| `B_archivos_ogr` | 194 |
| `B_con_sismo_activo` | ['004/modelo.ogr', '051/modelo.ogr', '062/modelo_ru05.ogr', '062/modelo_ru05_path.ogr', '062/modelo_seco.ogr', '062/modelo_seco_path.ogr', '104/modelo_k015.ogr', '104/modelo_ky.ogr'] |
| `B_con_kh_aplicado` | 7 |
| `B_CON_KV_APLICADO` | 0 |
| `B_con_kv_aplicado` | [] |
| `B_con_kv_guardado_no_nulo` | 0 |
| `B_con_exceso_de_presion_sismica` | 0 |
| `B_CONTROL_004_KH` | 0.15 |
| `B_CONTROL_VE_EL_CASO` | True |
| `B_D174_settings_seismic_con_kh_o_kv` | 0 |
| `B_saltadas` | 0 |
| `C_filas` | 12 |
| `C_sin_resultado` | 0 |
| `C_CONTROL_KV_CERO_DELTA_M_ALPHA` | 0.0 |
| `C_CONTROL_KV_CERO_RESIDUO` | 0.0 |
| `C_max_delta_sigma_estimada_rel` | 0.20000000000000018 |
| `C_MAX_DELTA_M_ALPHA` | {'potencia': 0.034711803477035286, 'mohr_coulomb': 3.0142555118573e-13, 'undrained': 0.0} |
| `C_MAX_DELTA_SIGMA_EFECTIVA` | {'potencia': 0.25717372733238203, 'mohr_coulomb': 0.2423984799337231, 'undrained': 0.7948080543988262} |
| `C_DOVELAS_QUE_CRUZAN_0_2` | 0 |
| `C_min_m_alpha` | 0.5064345977841075 |
| `C_RESIDUO_IDENTIDAD_CON_KV` | 0.0 |
| `C_residuo_identidad_ciego` | 0.6642560348870137 |
| `FUERA_de_poblacion` | {'copias_en__auditoria': ['_auditoria/D54_CIERRE/056_modelo_pasoA.ogr', '_auditoria/ab_d132/antes/057_modelo.ogr', '_auditoria/ab_d132/antes/057_modelo_compuesto.ogr', '_auditoria/ab_d132/antes/064_modelo.ogr', '_auditoria/ab_d132/antes/065_modelo.ogr', '_auditoria/ab_d132/antes/066_modelo.ogr', '_auditoria/ab_d132/antes/067_modelo.ogr', '_auditoria/ab_d132/antes/068_modelo.ogr', '_auditoria/ab_d132/antes/069_modelo.ogr', '_auditoria/ab_d132/antes/075_modelo.ogr'], 'en_Evaluaciones': 4827} |
| `CLAVES_QUE_PUEDEN_DIFERIR` | ['version', 'arbol_medido', 'modulo_medido', 'A_CONTROL_HB_SINTETICO', 'A_CONTROL_VE_EL_CASO', 'C_MAX_DELTA_M_ALPHA', 'C_MAX_DELTA_SIGMA_EFECTIVA', 'C_DOVELAS_QUE_CRUZAN_0_2', 'C_RESIDUO_IDENTIDAD_CON_KV'] |

## Mitad B - los modelos con sismo activo

| n | archivo | kh aplicado | kv aplicado |
|---|---|---|---|
| 004 | modelo.ogr | 0.15 | 0 |
| 051 | modelo.ogr | 0.1 | 0 |
| 062 | modelo_ru05.ogr | 0.132 | 0 |
| 062 | modelo_ru05_path.ogr | 0.132 | 0 |
| 062 | modelo_seco.ogr | 0.432 | 0 |
| 062 | modelo_seco_path.ogr | 0.432 | 0 |
| 104 | modelo_k015.ogr | 0.15 | 0 |
| 104 | modelo_ky.ogr | 0 | 0 |

## Mitad C - un resultado por fila, variando solo `details["kv"]`

| envolvente | kv | FoS | max d(m_alpha) | max d(sigma')/sigma' | cruzan 0,2 | min m_alpha | residuo con kv | residuo ciego |
|---|---|---|---|---|---|---|---|---|
| potencia | +0.0 | 1.587957 | 0.000e+00 | 0.000e+00 | 0 | 0.7027 | 0.0e+00 | 0.0e+00 |
| potencia | -0.2 | 1.476179 | 3.087e-02 | 2.572e-01 | 0 | 0.6892 | 0.0e+00 | 2.0e-01 |
| potencia | -0.1 | 1.528505 | 1.585e-02 | 1.268e-01 | 0 | 0.6958 | 0.0e+00 | 1.1e-01 |
| potencia | +0.1 | 1.656380 | 1.680e-02 | 1.230e-01 | 0 | 0.7028 | 0.0e+00 | 1.4e-01 |
| potencia | +0.2 | 1.736376 | 3.471e-02 | 2.419e-01 | 0 | 0.7028 | 0.0e+00 | 3.2e-01 |
| mohr_coulomb | +0.0 | 2.604448 | 0.000e+00 | 0.000e+00 | 0 | 0.6825 | 0.0e+00 | 0.0e+00 |
| mohr_coulomb | -0.2 | 2.570444 | 1.703e-13 | 2.424e-01 | 0 | 0.6848 | 0.0e+00 | 2.0e-01 |
| mohr_coulomb | -0.1 | 2.585900 | 2.146e-13 | 1.210e-01 | 0 | 0.6837 | 0.0e+00 | 1.1e-01 |
| mohr_coulomb | +0.1 | 2.627119 | 1.668e-13 | 1.206e-01 | 0 | 0.6810 | 0.0e+00 | 1.4e-01 |
| mohr_coulomb | +0.2 | 2.655461 | 3.014e-13 | 2.408e-01 | 0 | 0.6791 | 0.0e+00 | 3.2e-01 |
| undrained | +0.0 | 0.686906 | 0.000e+00 | 0.000e+00 | 0 | 0.5064 | 0.0e+00 | 0.0e+00 |
| undrained | -0.2 | 0.572421 | 0.000e+00 | 7.948e-01 | 0 | 0.5064 | 0.0e+00 | 4.4e-01 |
| undrained | -0.1 | 0.624460 | 0.000e+00 | 3.185e-01 | 0 | 0.5064 | 0.0e+00 | 2.4e-01 |
| undrained | +0.1 | 0.763229 | 0.000e+00 | 2.279e-01 | 0 | 0.5064 | 0.0e+00 | 3.0e-01 |
| undrained | +0.2 | 0.858632 | 0.000e+00 | 3.991e-01 | 0 | 0.5064 | 0.0e+00 | 6.6e-01 |

